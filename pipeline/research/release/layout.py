"""The layout of a public version's universe file, for the site's list download.

    python3 -m research.release.layout --version v1.0
        writes research/release/layout_<version>.json from the release file
    python3 -m research.release.layout --version v1.0 --check
        compares the committed record with a fresh one

The site's "Download the list" reads a composed list in the visitor's browser,
straight from the version's universe file on the Hugging Face hub, by byte
range: the strings and the columns its criteria use, never the whole file. The
record says where each of those column chunks lies in each row group, so the
page can state before it starts how much it will read, and request the chunks
in a few ranges. It holds offsets, sizes, and counts, and no value of any row.
The file is held to the sha256 its release record names first.
"""

from __future__ import annotations

import argparse
import json
import sys

import pyarrow.parquet as pq

from ceol.ingest.common import sha256_file
from research.release import build_release as B

CONFIG = "universe"

# the columns a download may read: the strings, and the column of each
# criterion of Compose a list (site/src/lib/list-filter.ts reads no other)
READ_COLUMNS = (
    "word",
    "eol",
    "token_count",
    "class_explicit",
    "panel_sets",
    "intake_layer",
    "intake_kind",
    "panel_count",
    "gb_type",
    "wordfreq_scored",
    "wikt_title_any",
    "provenance_class",
    "model_or_engine",
)


class LayoutError(Exception):
    pass


def out_path(version: str):
    return B.resolve(version).record_out.with_name(f"layout_{version}.json")


def chunk_span(column) -> tuple[int, int]:
    """The byte offset and length of a column chunk: its dictionary page, if
    it has one, and its data pages."""
    start = column.data_page_offset
    if column.has_dictionary_page and column.dictionary_page_offset is not None:
        start = min(start, column.dictionary_page_offset)
    return int(start), int(column.total_compressed_size)


def layout_of(path, columns=READ_COLUMNS) -> dict:
    """The row groups of the Parquet file at `path`, each with the span of
    every column of `columns`."""
    meta = pq.ParquetFile(path).metadata
    groups = []
    for g in range(meta.num_row_groups):
        rg = meta.row_group(g)
        names = [rg.column(c).path_in_schema for c in range(rg.num_columns)]
        missing = [c for c in columns if c not in names]
        if missing:
            raise LayoutError(f"row group {g} has no column {', '.join(missing)}")
        groups.append({
            "rows": rg.num_rows,
            "columns": {c: list(chunk_span(rg.column(names.index(c)))) for c in columns},
        })
    return {"rows": meta.num_rows, "row_groups": groups}


def compute(version: str) -> dict:
    spec = B.resolve(version)
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    entry = next((f for f in record["files"] if f["config"] == CONFIG), None)
    if entry is None:
        raise LayoutError(f"the record of {version} names no {CONFIG} file")
    path = spec.out_dir / entry["path"]
    if not path.exists():
        raise LayoutError(f"{path} is absent; the layout is read from the release file")
    if sha256_file(path) != entry["sha256"]:
        raise LayoutError(f"{path.name} is not the file the record of {version} names")
    found = layout_of(path)
    if found["rows"] != entry["rows"]:
        raise LayoutError(f"{path.name} holds {found['rows']} rows; the record says {entry['rows']}")
    return {
        "generated_by": "research/release/layout.py",
        "what": ("where the strings and the criteria's columns lie in each row group of the "
                 "universe file, for the site's list download; offsets and sizes in bytes"),
        "version": version,
        "dataset": B.DATASET,
        "hub_path": f"data/{entry['path']}",
        "bytes": entry["bytes"],
        "sha256": entry["sha256"],
        **found,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--check", action="store_true", help="compare the committed record with a fresh one")
    args = ap.parse_args(argv)
    try:
        text = json.dumps(compute(args.version), indent=1) + "\n"
    except (LayoutError, B.ReleaseError) as exc:
        print(f"[layout] {exc}", file=sys.stderr)
        return 1
    out = out_path(args.version)
    rel = out.relative_to(B.REPO)
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print(f"[layout] {rel} does not re-derive", file=sys.stderr)
            return 1
        print(f"[layout] {rel} re-derives")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"[layout] {rel} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
