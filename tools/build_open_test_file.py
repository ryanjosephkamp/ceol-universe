#!/usr/bin/env python3
"""Build the small Parquet file the site's tests read the list download from.

    python3 tools/build_open_test_file.py            write the 2 files
    python3 tools/build_open_test_file.py --check    rebuild in memory and compare

It writes `site/test-files/open-test/open-lists.parquet`, a file in the open
subset's `open-lists` columns, and `layout.json`, its layout as
`research.release.open_compose` writes the subset's. The rows are made up
here: synthetic strings like "s017-b" that no list holds, with every
column's coding as the subset's card gives it (nulls on multiword rows,
`scowl_size` 0, -1, or 10 to 70, and so on). Nothing is read from the
dataset. The file has 2 row groups, and its strings column has 2 data
pages in the first, so a test reads it by range a row group at a time and
crosses a page boundary within a row group, with no data folder. Build it
with the repository's pinned pyarrow (requirements.txt): another version
writes other bytes, and --check then differs.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys

import _paths  # noqa: F401  (puts pipeline/ on the path)
import pyarrow as pa
import pyarrow.parquet as pq

from research.release import layout as L
from research.release import open_compose as C

OUT = _paths.REPO / "site" / "test-files" / "open-test"
LISTS = ("wordnet", "wiktionary_english", "hunspell_en_US", "hunspell_en_CA", "hunspell_en_AU", "scowl")
SIZES = (-1, 0, 10, 20, 35, 40, 50, 55, 60, 70)
METADATA = {"ceol.version": "open-test", "ceol.license": "CC-BY-SA-4.0",
            "ceol.attribution": "A made-up file for the site's tests.", "ceol.notices": "NOTICES.md"}
ROWS = 90
ROW_GROUP = 60

SCHEMA = pa.schema([("id", pa.string()), ("word", pa.string()), ("token_count", pa.int32()),
                    ("classes", pa.string()), ("scowl_size", pa.int16()), ("gb_type", pa.bool_()),
                    ("list_count", pa.int8()), ("listed_by", pa.string()), ("wn_instance", pa.bool_()),
                    ("wk_proper_noun", pa.bool_())])


def rows() -> list[dict]:
    out = []
    for i in range(ROWS):
        multi = i % 5 == 4
        stem = f"s{i:03d}"
        word = f"{stem} b" if multi else (f"{stem}-b" if i % 7 == 3 else (f"{stem}'s" if i % 11 == 6 else stem))
        classes = ";".join(c for c, on in (("apostrophe-form", "'" in word), ("hyphenated", "-" in word),
                                            ("s-final", word.endswith("'s")), ("spaced", multi)) if on)
        if multi:
            names = [n for n, on in (("wordnet", i % 3 != 2), ("wiktionary_english", i % 3 != 0)) if on]
        else:
            names = [n for k, n in enumerate(LISTS) if (i + k) % (k + 2) == 0] or ["wiktionary_english"]
        size = None if multi else (SIZES[i % len(SIZES)] if "scowl" in names else (-1 if i % 13 == 0 else 0))
        if not multi and "scowl" in names and size <= 0:
            size = 35
        out.append({
            "id": hashlib.sha256(word.encode()).hexdigest()[:16], "word": word, "token_count": 2 if multi else 1,
            "classes": classes, "scowl_size": size, "gb_type": None if multi else i % 4 != 1,
            "list_count": len(names), "listed_by": ";".join(names),
            "wn_instance": (i % 2 == 0) if multi and "wordnet" in names else None,
            "wk_proper_noun": (i % 3 == 1) if multi and "wiktionary_english" in names else None,
        })
    return sorted(out, key=lambda r: r["word"])


def build() -> dict[str, bytes]:
    table = pa.Table.from_pylist(rows(), schema=SCHEMA).replace_schema_metadata(METADATA)
    buf = io.BytesIO()
    # 4-row write batches let the writer cut a page every few rows, and the
    # strings are not dictionary-encoded, so their column has 2 data pages
    # in the first row group, as the subset's own strings have several
    pq.write_table(table, buf, compression="zstd", row_group_size=ROW_GROUP, data_page_size=256,
                   write_batch_size=4, use_dictionary=[c for c in SCHEMA.names if c != "word"],
                   write_page_index=False)
    data = buf.getvalue()
    tmp = OUT / ".layout.parquet"
    OUT.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    try:
        found = L.layout_of(tmp, columns=C.READ_COLUMNS)
    finally:
        tmp.unlink()
    layout = {"generated_by": "tools/build_open_test_file.py", "version": "open-test", "dataset": "test",
              "hub_path": "data/open-lists.parquet", "url": "https://hub.test/data/open-lists.parquet",
              "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "metadata": METADATA, **found}
    return {"open-lists.parquet": data, "layout.json": (json.dumps(layout, indent=1) + "\n").encode()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    built = build()
    for name, data in built.items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                print(f"[open-test] {path.relative_to(_paths.REPO)} differs from what the script writes", file=sys.stderr)
                return 1
        else:
            path.write_bytes(data)
        print(f"[open-test] {len(data):>6,} bytes  {path.relative_to(_paths.REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
