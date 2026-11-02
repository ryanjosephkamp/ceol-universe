"""Version 1.0 holds v2.1's rows: the check that
the first public release, built under its public name, differs from v2.1
in that name alone. It compares the 2 release records and the 2 sets of
Parquet files, and writes research/release/rename_v1.0.json. Counts and
hashes only: no word is printed or written.

For each config it holds the 2 files to their records' sha256, then
compares their schemas without metadata, their row groups one at a time,
and every value in them, and their key-value metadata, which may differ
only in `ceol.version`. A floating-point column is compared bit for bit,
so a NaN equals the same NaN, which Arrow's own equality never grants. The 2 records must agree on every source layer,
every count, the projection, and each file's columns; they may differ only
in the fields a build's date, code, version, and file hashes set.

    python3 -m research.release.rename_check            write the record
    python3 -m research.release.rename_check --check    compare with it
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ceol.ingest.common import sha256_file
from research.release import build_release as B

OLD, NEW = "v2.1", "v1.0"
OUT = B.REPO / "research" / "release" / f"rename_{NEW}.json"
#: the record fields a rebuild under another name may change
VARYING = ("version", "built_on", "code", "files", "documents", "software",
           "documents_rewritten_on")


class Differs(Exception):
    pass


def _same_column(a: pa.ChunkedArray, b: pa.ChunkedArray) -> bool:
    """Whether 2 columns hold the same values; floats bit for bit, before
    any equality of Arrow's, which takes -0.0 for 0.0 (the G4 audit's F14)."""
    if a.type != b.type:
        return False
    if not pa.types.is_floating(a.type):
        return a.equals(b)
    if not pc.is_null(a).equals(pc.is_null(b)):
        return False
    x = pc.fill_null(a, 0).to_numpy()
    y = pc.fill_null(b, 0).to_numpy()
    width = {2: np.uint16, 4: np.uint32, 8: np.uint64}[x.dtype.itemsize]
    return bool(np.array_equal(x.view(width), y.view(width)))


def _records() -> tuple[dict, dict]:
    old, new = (json.loads(B.resolve(v).record_out.read_text(encoding="utf-8")) for v in (OLD, NEW))
    for key in sorted(set(old) | set(new)):
        if key not in VARYING and old.get(key) != new.get(key):
            raise Differs(f"the records differ in {key!r}")
    if [f["config"] for f in old["files"]] != [f["config"] for f in new["files"]]:
        raise Differs("the records name different configs")
    for a, b in zip(old["files"], new["files"]):
        for key in ("path", "rows", "columns", "predicate", "row_group_rows"):
            if a.get(key) != b.get(key):
                raise Differs(f"{a['config']}: the records differ in {key!r}")
    return old, new


def _compare(config: str, a: dict, b: dict) -> dict:
    paths = []
    for v, f in ((OLD, a), (NEW, b)):
        path = B.resolve(v).out_dir / f["path"]
        if sha256_file(path) != f["sha256"]:
            raise Differs(f"{config}: {path.name} of {v} is not the file its record names")
        paths.append(path)
    pa_, pb = (pq.ParquetFile(p) for p in paths)
    if pa_.metadata.num_rows != pb.metadata.num_rows or pa_.num_row_groups != pb.num_row_groups:
        raise Differs(f"{config}: the files' rows or row groups differ")
    sa, sb = pa_.schema_arrow.remove_metadata(), pb.schema_arrow.remove_metadata()
    if not sa.equals(sb):
        raise Differs(f"{config}: the files' schemas differ")
    for i in range(pa_.num_row_groups):
        ta, tb = pa_.read_row_group(i), pb.read_row_group(i)
        for name in ta.column_names:
            if not _same_column(ta[name], tb[name]):
                raise Differs(f"{config}: row group {i}, column {name} differs")
    ma = {k.decode(): v.decode() for k, v in (pa_.schema_arrow.metadata or {}).items()}
    mb = {k.decode(): v.decode() for k, v in (pb.schema_arrow.metadata or {}).items()}
    differing = sorted(k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k))
    if differing != ["ceol.version"] or ma["ceol.version"] != OLD or mb["ceol.version"] != NEW:
        raise Differs(f"{config}: the files' metadata differ in {differing}")
    return {
        "config": config,
        "rows": pb.metadata.num_rows,
        "row_groups": pb.num_row_groups,
        "columns": len(sb),
        f"sha256_{OLD}": a["sha256"],
        f"sha256_{NEW}": b["sha256"],
        "values_equal": True,
        "metadata_differing": differing,
    }


def compute() -> dict:
    old, new = _records()
    return {
        "generated_by": "research/release/rename_check.py",
        "decision": "D-014 line 2",
        "what": f"{NEW} against {OLD}: the same rows, values, schemas, and row groups; only the version name differs",
        "records": {OLD: B.resolve(OLD).record_out.name, NEW: B.resolve(NEW).record_out.name},
        "record_fields_differing": sorted(k for k in VARYING if old.get(k) != new.get(k)),
        "files": [_compare(a["config"], a, b) for a, b in zip(old["files"], new["files"])],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare the committed record with a fresh one")
    args = ap.parse_args(argv)
    try:
        text = json.dumps(compute(), indent=1) + "\n"
    except Differs as exc:
        print(f"[rename] {NEW} is not {OLD} renamed: {exc}", file=sys.stderr)
        return 1
    rel = OUT.relative_to(B.REPO)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"[rename] {rel} does not re-derive", file=sys.stderr)
            return 1
        print(f"[rename] {rel} re-derives")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"[rename] {rel} written: every file of {NEW} holds {OLD}'s rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
