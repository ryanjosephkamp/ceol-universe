"""
Google Books 2020 English 1-grams under the CEOL grammar — streamed,
aggregated, deleted (C4 step 2).

The EOL's aggregate is a-z-only by its grammar; the CEOL re-stream keeps
every grammar-valid key, so hyphenated, accented, apostrophe and ligature
tokens survive for the first time — and the per-class key counts double
as the TOKENIZATION PROBE that rules Google Books' per-class
applicability (C-010: measured, never assumed).

Every shard download is verified against the EOL manifest's pinned
sha256 before parsing — same artifacts, one authority. Disk discipline
unchanged: one ~265 MB shard on disk at a time.

Parity property (asserted at merge): the plain a-z subset of this
aggregate is CONTAINED in the EOL's pinned aggregate. Containment rather
than equality is the C-001 divergence made visible: the EOL's casefold
laundered ß/ligature raws into a-z keys (straße → strasse) that lower()
refuses to invent; those keys' counts differ by exactly that laundered
mass, and the delta is reported, not hidden.

Run:  python -m research.features.google_books
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from ceol.grammar import classes as class_flags
from ceol.grammar import normalize
from ceol.ingest.common import (CACHE, DERIVED_DIR, EOL_REPO, RAW_DIR,
                                USER_AGENT, sha256_file)

SHARDS = 24
URL = ("http://storage.googleapis.com/books/ngrams/books/20200217/eng/"
       "1-{i:05d}-of-00024.gz")
GB_DIR = CACHE / "gb"
AGGREGATE = DERIVED_DIR / "google_books_1grams_ceol.parquet"
EOL_AGGREGATE = (EOL_REPO / ".cache" / "sources" / "derived"
                 / "google_books_1grams.parquet")
EOL_MANIFEST = EOL_REPO / "sources" / "MANIFEST.toml"


def shard_pins() -> dict[int, str]:
    """The 24 per-shard sha256 pins, parsed from the EOL manifest."""
    text = EOL_MANIFEST.read_text(encoding="utf-8")
    pins = {int(m.group(1)): m.group(2) for m in re.finditer(
        r"\[\[source\.shard\]\]\s*\nshard\s*=\s*(\d+)\s*\n"
        r"sha256\s*=\s*\"([0-9a-f]{64})\"", text)}
    if len(pins) != SHARDS:
        raise RuntimeError(f"parsed {len(pins)} shard pins, wanted {SHARDS}")
    return pins


def download(url: str, dest: Path, pin: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    got = sha256_file(dest)
    if got != pin:
        dest.unlink()
        raise RuntimeError(f"{url}: sha256 {got} != manifest pin {pin}")
    return got


def aggregate_shard(path: Path) -> dict[str, list]:
    agg: dict[str, list] = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            tab = line.find("\t")
            if tab <= 0:
                continue
            key = normalize(line[:tab])
            if key is None:
                continue
            tm = tv = ny = 0
            fy, ly = 9999, 0
            for triple in line[tab + 1:].split("\t"):
                parts = triple.split(",")
                if len(parts) != 3:
                    continue
                try:
                    y, m, v = int(parts[0]), int(parts[1]), int(parts[2])
                except ValueError:
                    continue
                tm += m
                tv += v
                ny += 1
                if y < fy:
                    fy = y
                if y > ly:
                    ly = y
            if tm == 0:
                continue
            row = agg.get(key)
            if row is None:
                agg[key] = [tm, tv, fy, ly, ny]
            else:
                row[0] += tm
                row[1] += tv
                if fy < row[2]:
                    row[2] = fy
                if ly > row[3]:
                    row[3] = ly
                row[4] += ny
    return agg


def class_counts(words) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in words:
        flags = class_flags(w)
        if not flags:
            counts["plain"] = counts.get("plain", 0) + 1
        else:
            for f in flags:
                counts[f] = counts.get(f, 0) + 1
    return counts


def write_shard_parquet(agg: dict[str, list], out: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    schema = pa.schema([
        ("word", pa.string()), ("total_match", pa.int64()),
        ("total_volume", pa.int64()), ("first_year", pa.int16()),
        ("last_year", pa.int16()), ("year_count", pa.int16())])
    words = sorted(agg)
    table = pa.table({
        "word": words,
        "total_match": [agg[w][0] for w in words],
        "total_volume": [agg[w][1] for w in words],
        "first_year": [agg[w][2] for w in words],
        "last_year": [agg[w][3] for w in words],
        "year_count": [agg[w][4] for w in words]}, schema=schema)
    pq.write_table(table, out, compression="zstd")


def merge_shards() -> Path:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    frames = [pq.read_table(GB_DIR / f"shard-{i:05d}.parquet").to_pandas()
              for i in range(SHARDS)]
    df = pd.concat(frames, ignore_index=True)
    del frames
    g = df.groupby("word", sort=True).agg(
        total_match=("total_match", "sum"),
        total_volume=("total_volume", "sum"),
        first_year=("first_year", "min"),
        last_year=("last_year", "max"),
        year_count=("year_count", "sum"),
    ).reset_index()
    span = (g["last_year"] - g["first_year"] + 1).clip(lower=1)
    g["year_count"] = g["year_count"].clip(upper=span)
    pq.write_table(pa.Table.from_pandas(g, preserve_index=False), AGGREGATE,
                   compression="zstd")
    return AGGREGATE


def parity_and_probe() -> dict:
    import pyarrow.parquet as pq
    words = pq.read_table(AGGREGATE, columns=["word"]).column("word") \
        .to_pylist()
    probe = class_counts(words)
    plain = {w for w in words if not class_flags(w)}
    del words
    eol_words = set(pq.read_table(EOL_AGGREGATE, columns=["word"])
                    .column("word").to_pylist())
    outside = plain - eol_words
    if outside:
        raise RuntimeError(
            f"parity FAILED: {len(outside):,} plain CEOL keys missing from "
            f"the EOL aggregate: {sorted(outside)[:5]}")
    return {
        "class_key_counts": dict(sorted(probe.items())),
        "parity": {
            "ceol_plain_keys": len(plain),
            "eol_keys": len(eol_words),
            "ceol_plain_subset_of_eol": True,
            "eol_only_keys": len(eol_words) - len(plain),
            "note": ("EOL-only keys are the casefold-laundered mass "
                     "(ss/ligature folds) the CEOL grammar refuses to "
                     "invent (C-001)"),
        },
    }


def main() -> int:
    GB_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pins = shard_pins()
    t0 = time.time()
    for i in range(SHARDS):
        out = GB_DIR / f"shard-{i:05d}.parquet"
        if out.exists():
            print(f"[gb] shard {i:02d}: parquet exists, skipping", flush=True)
            continue
        raw = RAW_DIR / f"gb-1-{i:05d}.gz"
        t1 = time.time()
        try:
            sha = download(URL.format(i=i), raw, pins[i])
        except Exception as e:
            print(f"[gb] shard {i:02d}: download failed ({e}); retrying once",
                  flush=True)
            time.sleep(10)
            sha = download(URL.format(i=i), raw, pins[i])
        t2 = time.time()
        agg = aggregate_shard(raw)
        write_shard_parquet(agg, out)
        raw.unlink()
        counts = class_counts(agg)
        with open(GB_DIR / "shards.jsonl", "a", encoding="utf-8") as mf:
            mf.write(json.dumps({"shard": i, "sha256": sha,
                                 "types": len(agg),
                                 "classes": dict(sorted(counts.items()))})
                     + "\n")
        print(f"[gb] shard {i:02d}: {len(agg):>9,} CEOL types | "
              f"dl {t2-t1:5.0f}s parse {time.time()-t2:5.0f}s | "
              f"elapsed {(time.time()-t0)/60:5.1f}m", flush=True)
        del agg

    out = merge_shards()
    import pyarrow.parquet as pq
    n = pq.read_metadata(out).num_rows
    summary = parity_and_probe()
    with open(GB_DIR / "shards.jsonl", encoding="utf-8") as mf:
        seen = {}
        for line in mf:
            rec = json.loads(line)
            seen[rec["shard"]] = rec
    meta = {
        "source": "google_books_1gram_eng_2020 (CEOL grammar)",
        "record_count": n,
        "aggregate_sha256": sha256_file(out),
        "shards": [seen[k] for k in sorted(seen)],
        **summary,
    }
    with open(DERIVED_DIR / "google_books_ceol.meta.json", "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[gb] DONE: {n:,} CEOL types in {(time.time()-t0)/60:.1f}m; "
          f"probe {summary['class_key_counts']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
