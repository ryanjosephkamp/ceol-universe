"""
P2 of the intake-provenance package (C-064 rulings 1 and 2): the EOL's
two dictionaries at the pinned revision, read as pinned inputs, hashed,
and reduced to their intake fields.

The invalid dictionary (12,237,976,092 bytes on the hub, not held
locally) is STREAMED ONCE with the standard library's HTTP client and is
never written to disk: every chunk that arrives is fed to one sha256 and
to the line parser, in that order, so the hash is over the bytes that
were parsed. The file's layout is one entry per line under a two-space
indent between an opening `{` line and a closing `}` line; a line
outside that layout is a hard error naming its line number and byte
offset, never its content. Only the intake fields leave the parser, in
row-group chunks, to .cache/provenance/eol_invalid_intake.parquet.

Hard stops, all before the output is given its final name: under 5 GiB
of free disk; the hub's revision, size, or ETag differing from the
values pinned here; the stream's length or sha256 differing from the
hub's. The valid dictionary (local, pretty-printed, so parsed whole from
the bytes that are hashed) must hash to the checksum ritual's value.

The EOL is read and never written: the one remote file is fetched by
GET from the hub at an immutable revision, the one local file is opened
for reading.

Run:  python3 -m research.provenance.extract_eol_intake [valid|invalid|both]
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ceol.ingest.common import EOL_REPO, sha256_file

REPO = Path(__file__).resolve().parents[2]
WORK_DIR = REPO / ".cache" / "provenance"

DATASET = "ryanjosephkamp/english-openlist"
REVISION = "c113969807f3045f5ddd8cc919d0189d54ba368b"
_RESOLVE = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}"

INVALID = {
    "name": "merged_invalid_dict.json",
    "url": f"{_RESOLVE}/data/merged_invalid_dict.json",
    "bytes": 12_237_976_092,
    #: the hub's ETag and LFS object id, read 2026-09-17 (PACKAGE.md §0)
    "sha256": "8ccfccdf16c39f87ea091a46e27c0b746260bf4cd019a9b5ae9e9faea3aba703",
    #: the hub's Xet hash — the value C-064 ruling 2 quotes; not a sha256
    "xet_hash": "1c921f6b1436898611731ad1e6a69c442c634363db4bd897c373ab4b25260642",
    "out": WORK_DIR / "eol_invalid_intake.parquet",
}
VALID = {
    "name": "merged_valid_dict.json",
    "url": f"{_RESOLVE}/data/merged_valid_dict.json",
    "local": EOL_REPO / ".cache" / "hf" / "merged_valid_dict.json",
    "bytes": 282_080_828,
    #: the checksum ritual's value, equal to the hub's LFS object id
    "sha256": "20e5baedf4ac7731e3d2c51d5d3e357c14680a5b493c68eeaf4503484b46af2a",
    "out": WORK_DIR / "eol_valid_intake.parquet",
}

MIN_FREE_BYTES = 5 * (1 << 30)
CHUNK_BYTES = 1 << 22
ROW_GROUP = 250_000
MAX_RESUMES = 40

#: The intake fields, and nothing else, leave the parser (PACKAGE.md §1).
INTAKE_COLUMNS = (
    "word", "has_candidate_source", "candidate_source", "source", "status",
    "candidate_date", "has_validation_source", "validation_source",
    "manual_validation_status", "manual_validation_llm", "category")

#: Fields whose VALUES are counted for the manifest: small categorical
#: vocabularies of the EOL's schema, never free text and never a key.
CATEGORICAL = ("source", "status", "validation_source", "category",
               "generation_method")
CATEGORICAL_NESTED = (
    ("manual_validation", "manual_validation_status"),
    ("manual_validation", "manual_validation_llm"),
    ("manual_validation", "manual_validation_source"))


class LayoutError(ValueError):
    """A line outside the one-entry-per-line layout. Carries the line
    number and the byte offset of the line's first byte, never the line:
    a line holds a candidate string."""


_ENTRY = re.compile(rb'^  ("(?:[^"\\]|\\.)*"): (\{.*\})(,?)$', re.S)


class LineParser:
    """Bytes in, (key, record) pairs out, the layout enforced and the
    sha256 accumulated on the same bytes.

    The layout: line 1 is `{`; every following line is
    `  "<key>": {<object>}` with a trailing comma on every entry but the
    last; the line after the last entry is `}`; nothing follows it but
    the final newline. A repeated key is a layout error too — a
    whole-file JSON parse would have silently kept the last one.
    """

    def __init__(self) -> None:
        self.sha256 = hashlib.sha256()
        self.bytes = 0
        self.lines = 0
        self.entries = 0
        self._buf = b""
        self._line_start = 0
        self._state = "open"        # open -> entries -> last -> closed
        self._seen: set[str] = set()

    def _fail(self, why: str) -> None:
        raise LayoutError(f"line {self.lines} (byte offset "
                          f"{self._line_start:,}): {why}")

    def _line(self, line: bytes) -> tuple[str, dict] | None:
        self.lines += 1
        if self._state == "open":
            if line != b"{":
                self._fail("the first line is not the opening brace")
            self._state = "entries"
            return None
        if self._state == "closed":
            self._fail("content after the closing brace")
        if line == b"}":
            if self._state != "last":
                self._fail("the closing brace follows an entry that "
                           "ends in a comma, or no entry at all")
            self._state = "closed"
            return None
        if self._state == "last":
            self._fail("an entry follows an entry that carried no comma")
        m = _ENTRY.match(line)
        if m is None:
            self._fail("not an entry of the one-entry-per-line layout")
        try:
            key = json.loads(m.group(1))
            record = json.loads(m.group(2))
        except ValueError:
            self._fail("the entry is not valid JSON")
        if not isinstance(record, dict):
            self._fail("the entry's value is not an object")
        if key in self._seen:
            self._fail("a repeated key")
        self._seen.add(key)
        if not m.group(3):
            self._state = "last"
        self.entries += 1
        return key, record

    def feed(self, chunk: bytes) -> list[tuple[str, dict]]:
        self.sha256.update(chunk)
        self.bytes += len(chunk)
        data = self._buf + chunk
        lines = data.split(b"\n")
        self._buf = lines.pop()
        out = []
        for line in lines:
            pair = self._line(line)
            if pair is not None:
                out.append(pair)
            self._line_start += len(line) + 1
        return out

    def close(self) -> list[tuple[str, dict]]:
        """End of input. A final line without its newline is still a
        line; an input that never closed its brace is an error."""
        out = []
        if self._buf:
            pair = self._line(self._buf)
            if pair is not None:
                out.append(pair)
            self._buf = b""
        if self._state != "closed":
            self._fail("the input ended before the closing brace")
        return out


def reduce_entry(key: str, record: dict) -> dict:
    """The intake fields of one dictionary entry."""
    labels = record.get("candidate_source")
    if labels is None:
        joined = None
    elif isinstance(labels, list) and all(isinstance(x, str) for x in labels):
        if any(";" in x for x in labels):
            raise ValueError("a candidate_source label carries a semicolon")
        joined = ";".join(labels)
    else:
        raise ValueError("candidate_source is neither null nor a list of "
                         "strings")
    manual = record.get("manual_validation")
    if not isinstance(manual, dict):
        manual = {}

    def text(value):
        return None if value is None else str(value)

    return {
        "word": key,
        "has_candidate_source": "candidate_source" in record,
        "candidate_source": joined,
        "source": text(record.get("source")),
        "status": text(record.get("status")),
        "candidate_date": text(record.get("candidate_date")),
        "has_validation_source": "validation_source" in record,
        "validation_source": text(record.get("validation_source")),
        "manual_validation_status":
            text(manual.get("manual_validation_status")),
        "manual_validation_llm": text(manual.get("manual_validation_llm")),
        "category": text(record.get("category")),
    }


class _Census:
    """Counts for the manifest: field names, categorical values, the
    state of the channel list, and the discovery-log labels. No key and
    no free text is counted."""

    def __init__(self) -> None:
        self.fields: Counter = Counter()
        self.values: dict[str, Counter] = {
            name: Counter() for name in CATEGORICAL}
        for _, name in CATEGORICAL_NESTED:
            self.values[name] = Counter()
        self.channel_list: Counter = Counter()
        self.labels: Counter = Counter()
        self.inner_word_mismatch = 0

    def add(self, key: str, record: dict) -> None:
        self.fields.update(record.keys())
        for name in CATEGORICAL:
            if name in record:
                self.values[name][_label(record[name])] += 1
        for outer, name in CATEGORICAL_NESTED:
            inner = record.get(outer)
            if isinstance(inner, dict) and name in inner:
                self.values[name][_label(inner[name])] += 1
        if "candidate_source" not in record:
            self.channel_list["absent"] += 1
        elif record["candidate_source"] is None:
            self.channel_list["null"] += 1
        elif not record["candidate_source"]:
            self.channel_list["empty"] += 1
        else:
            self.channel_list["non_empty"] += 1
            self.labels.update(record["candidate_source"])
        if "word" in record and record["word"] != key:
            self.inner_word_mismatch += 1

    def as_dict(self) -> dict:
        def ordered(counter: Counter) -> dict:
            return {k: counter[k] for k in sorted(counter)}
        return {
            "field_name_counts": ordered(self.fields),
            "categorical_value_counts": {
                name: ordered(c) for name, c in sorted(self.values.items())},
            "candidate_source_state": ordered(self.channel_list),
            "candidate_source_label_counts": ordered(self.labels),
            "entries_whose_inner_word_differs_from_the_key":
                self.inner_word_mismatch,
        }


def _label(value) -> str:
    return "null" if value is None else str(value)


class _Writer:
    """Row-group chunks to a .partial file; renamed only on success."""

    def __init__(self, out: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq
        self._pa, self._pq = pa, pq
        self.out = out
        self.partial = out.with_suffix(out.suffix + ".partial")
        self.schema = pa.schema([
            ("word", pa.string()),
            ("has_candidate_source", pa.bool_()),
            ("candidate_source", pa.string()),
            ("source", pa.string()),
            ("status", pa.string()),
            ("candidate_date", pa.string()),
            ("has_validation_source", pa.bool_()),
            ("validation_source", pa.string()),
            ("manual_validation_status", pa.string()),
            ("manual_validation_llm", pa.string()),
            ("category", pa.string()),
        ])
        assert tuple(self.schema.names) == INTAKE_COLUMNS
        out.parent.mkdir(parents=True, exist_ok=True)
        self._writer = pq.ParquetWriter(self.partial, self.schema,
                                        compression="zstd")
        self._rows: list[dict] = []
        self.rows_written = 0

    def add(self, row: dict) -> None:
        self._rows.append(row)
        if len(self._rows) >= ROW_GROUP:
            self._flush()

    def _flush(self) -> None:
        if not self._rows:
            return
        table = self._pa.table(
            {c: [r[c] for r in self._rows] for c in INTAKE_COLUMNS},
            schema=self.schema)
        self._writer.write_table(table)
        self.rows_written += len(self._rows)
        self._rows = []

    def finish(self) -> None:
        self._flush()
        self._writer.close()
        self.partial.replace(self.out)

    def abandon(self) -> None:
        self._writer.close()
        if self.partial.exists():
            self.partial.unlink()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def hub_headers(url: str) -> dict:
    """The hub's own record of the file, read from the resolve endpoint
    without following its redirect."""
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        response = opener.open(urllib.request.Request(url, method="HEAD"),
                               timeout=60)
        headers = response.headers
    except urllib.error.HTTPError as exc:       # the 302 itself
        headers = exc.headers
    return {
        "revision": headers.get("X-Repo-Commit"),
        "bytes": int(headers.get("X-Linked-Size") or -1),
        "etag": (headers.get("X-Linked-ETag") or "").strip('"'),
        "xet_hash": headers.get("X-Xet-Hash"),
    }


def _open_from(url: str, offset: int):
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    response = urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=120)
    if offset:
        want = f"bytes {offset}-"
        got = response.headers.get("Content-Range", "")
        if response.status != 206 or not got.startswith(want):
            raise RuntimeError(f"the resumed response is not the range "
                               f"asked for (status {response.status})")
    return response


def extract_invalid() -> dict:
    spec = INVALID
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(WORK_DIR).free
    if free < MIN_FREE_BYTES:
        raise SystemExit(f"STOP: {free:,} bytes free, under the 5 GiB floor")
    hub = hub_headers(spec["url"])
    for key, want in (("revision", REVISION), ("bytes", spec["bytes"]),
                      ("etag", spec["sha256"]),
                      ("xet_hash", spec["xet_hash"])):
        if hub[key] != want:
            raise SystemExit(f"STOP: the hub's {key} is {hub[key]!r}, not "
                             f"the pinned {want!r}")

    parser, census, writer = LineParser(), _Census(), _Writer(spec["out"])
    started, t0 = _utc(), time.time()
    resumes: list[dict] = []
    next_report = 500_000

    def take(pairs) -> None:
        for key, record in pairs:
            census.add(key, record)
            writer.add(reduce_entry(key, record))

    try:
        response = _open_from(spec["url"], 0)
        while True:
            error = None
            try:
                chunk = response.read(CHUNK_BYTES)
            except (OSError, urllib.error.URLError,
                    http.client.HTTPException) as exc:
                chunk, error = None, type(exc).__name__
            if chunk is None:
                if len(resumes) >= MAX_RESUMES:
                    raise SystemExit("STOP: the stream failed more than "
                                     f"{MAX_RESUMES} times")
                resumes.append({"at_byte": parser.bytes, "error": error,
                                "utc": _utc()})
                time.sleep(min(60, 5 * len(resumes)))
                try:
                    response.close()
                except OSError:
                    pass
                response = _open_from(spec["url"], parser.bytes)
                continue
            if not chunk:
                if parser.bytes < spec["bytes"]:
                    # a short read that ended cleanly: resume, not finish
                    if len(resumes) >= MAX_RESUMES:
                        raise SystemExit("STOP: the stream ended early "
                                         "too many times")
                    resumes.append({"at_byte": parser.bytes,
                                    "error": "early end of stream",
                                    "utc": _utc()})
                    response = _open_from(spec["url"], parser.bytes)
                    continue
                break
            take(parser.feed(chunk))
            if parser.entries >= next_report:
                rate = parser.bytes / (time.time() - t0) / 1e6
                print(f"[invalid] {parser.entries:,} entries, "
                      f"{parser.bytes:,} bytes, {rate:.1f} MB/s, "
                      f"{len(resumes)} resume(s)", flush=True)
                next_report += 500_000
        take(parser.close())
    except BaseException:
        writer.abandon()
        raise

    got = parser.sha256.hexdigest()
    if parser.bytes != spec["bytes"] or got != spec["sha256"]:
        writer.abandon()
        raise SystemExit(f"STOP: the stream is {parser.bytes:,} bytes with "
                         f"sha256 {got}; the hub's record is "
                         f"{spec['bytes']:,} bytes and {spec['sha256']}")
    writer.finish()
    meta = {
        "dictionary": spec["name"],
        "url": spec["url"],
        "revision": REVISION,
        "bytes": parser.bytes,
        "sha256": got,
        "hub_etag_as_read": hub["etag"],
        "hub_xet_hash_as_read": hub["xet_hash"],
        "read_as": "streamed once from the hub, hashed on the bytes "
                   "parsed, never written to disk",
        "retrieved_utc": {"start": started, "end": _utc()},
        "resume_events": resumes,
        "lines": parser.lines,
        "entries": parser.entries,
        "intake_parquet": spec["out"].name,
        "intake_parquet_sha256": sha256_file(spec["out"]),
        "intake_parquet_rows": writer.rows_written,
        **census.as_dict(),
    }
    _write_meta(spec["out"], meta)
    return meta


def extract_valid() -> dict:
    spec = VALID
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    started = _utc()
    raw = spec["local"].read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if len(raw) != spec["bytes"] or got != spec["sha256"]:
        raise SystemExit(f"STOP: the local valid dictionary is {len(raw):,} "
                         f"bytes with sha256 {got}; the ritual's value is "
                         f"{spec['sha256']}")
    pairs = json.loads(raw, object_pairs_hook=list)
    del raw
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise SystemExit("STOP: a repeated key in the valid dictionary")
    census, writer = _Census(), _Writer(spec["out"])
    try:
        for key, fields in pairs:
            record = dict(fields)
            census.add(key, record)
            writer.add(reduce_entry(key, record))
    except BaseException:
        writer.abandon()
        raise
    writer.finish()
    meta = {
        "dictionary": spec["name"],
        "url": spec["url"],
        "revision": REVISION,
        "bytes": spec["bytes"],
        "sha256": got,
        "read_as": "the local pinned file (EOL .cache/hf), parsed whole "
                   "from the bytes that were hashed; equal to the "
                   "checksum ritual's value",
        "retrieved_utc": {"start": started, "end": _utc()},
        "entries": len(keys),
        "intake_parquet": spec["out"].name,
        "intake_parquet_sha256": sha256_file(spec["out"]),
        "intake_parquet_rows": writer.rows_written,
        **census.as_dict(),
    }
    _write_meta(spec["out"], meta)
    return meta


def _write_meta(out: Path, meta: dict) -> None:
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def main(argv: list[str]) -> int:
    which = argv[1] if len(argv) > 1 else "both"
    if which not in ("valid", "invalid", "both"):
        raise SystemExit(__doc__)
    if which in ("valid", "both"):
        m = extract_valid()
        print(f"[valid] {m['entries']:,} entries, sha256 {m['sha256']}")
    if which in ("invalid", "both"):
        m = extract_invalid()
        print(f"[invalid] {m['entries']:,} entries over {m['lines']:,} "
              f"lines, {m['bytes']:,} bytes, sha256 {m['sha256']}, "
              f"{len(m['resume_events'])} resume(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
