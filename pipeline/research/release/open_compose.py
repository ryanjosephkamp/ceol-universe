"""The open subset's cube and layout, for the site's Compose from the open
subset (/compose/open/).

    python3 -m research.release.open_compose
        writes research/release/open_cube_v1.0.json and
        research/release/layout_open_v1.0.json from the subset's file
    python3 -m research.release.open_compose --check
        compares the committed files with fresh ones
    python3 -m research.release.open_compose --file PATH
        reads the `open-lists` file at PATH instead of the build's folder

It reads 1 file, the open subset's own `data/open-lists.parquet`, held first
to the sha256 that the subset's record and its upload's record both name, so
it is the file at the hub commit the site reads. Nothing of the full universe
is read. It writes 2 files:

- `open_cube_v1.0.json`: the count of rows for every combination of the
  dimensions in `DIMENSIONS`, over every row of `open-lists`. The page counts
  a selection by summing the cells that pass it, so no row is fetched to
  count. A cell is 1 index into each dimension's values, in order, then the
  count. Its values are list names, class names, sizes, and counts; no string
  of a row is written.
- `layout_open_v1.0.json`: where the strings and each criterion's column lie
  in each row group, so the list download reads only those, by byte range,
  with the file's license and attribution from its own metadata.

The site derives `list_count` from `listed_by` and the SCOWL criterion from
`scowl_size`; the build asserts both agree with the file's own columns on
every row.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.release import layout as L
from research.release import open_subset as O

REPO = O.REPO
VERSION = O.VERSION
DATASET = O.DATASET
CONFIG = "open-lists"
HUB_PATH = "data/open-lists.parquet"
UPLOAD_RECORD = O.RELEASE_DIR / f"hf_upload_open_{VERSION}.json"
CUBE_OUT = O.RELEASE_DIR / f"open_cube_{VERSION}.json"
LAYOUT_OUT = O.RELEASE_DIR / f"layout_open_{VERSION}.json"

#: the cube's dimensions, in the order of a cell's indices
DIMENSIONS = ("listed_by", "scowl_size", "token_count", "length", "classes",
              "gb_type", "wn_instance", "wk_proper_noun")
#: lengths and token counts at or above these are 1 value ("25+", "4+"), as
#: in the universe's cube
LENGTH_CAP = 25
TOKEN_CAP = 4
#: the values of `scowl_size`, in order; null on multiword rows
SCOWL_VALUES = ("null", "-1", "0", *(str(s) for s in O.SCOWL_SIZES))

#: the columns a download may read: the strings, and the column of each
#: criterion of the page (site/src/lib/open-filter.ts reads no other)
READ_COLUMNS = ("word", "token_count", "classes", "scowl_size", "gb_type",
                "list_count", "listed_by", "wn_instance", "wk_proper_noun")
#: the file's own metadata the download's datasheet quotes
METADATA_KEYS = ("ceol.version", "ceol.license", "ceol.attribution", "ceol.notices")


class OpenComposeError(Exception):
    pass


def default_file() -> Path:
    return O.default_out() / HUB_PATH


def hub_url(commit: str) -> str:
    return f"https://huggingface.co/datasets/{DATASET}/resolve/{commit}/{HUB_PATH}"


def pinned() -> dict:
    """The file the site reads, as both records name it: its rows, bytes,
    sha256, and the hub commit that holds it."""
    record = json.loads(O.RECORD.read_text(encoding="utf-8"))
    entry = next((c for c in record["configs"] if c["config"] == CONFIG), None)
    if entry is None or entry["path"] != HUB_PATH:
        raise OpenComposeError(f"the subset's record names no {HUB_PATH}")
    upload = json.loads(UPLOAD_RECORD.read_text(encoding="utf-8"))
    uploaded = next((f for f in upload["files"] if f["path"] == HUB_PATH), None)
    if upload["repo_id"] != DATASET or uploaded is None:
        raise OpenComposeError(f"the upload's record names no {HUB_PATH} of {DATASET}")
    if uploaded["sha256"] != entry["sha256"]:
        raise OpenComposeError("the upload's record and the subset's record name different files")
    return {"rows": entry["rows"], "bytes": entry["bytes"], "sha256": entry["sha256"],
            "commit": upload["commit"]}


def _tri(column):
    import numpy as np
    import pyarrow as pa
    nulls = column.is_null().to_numpy(zero_copy_only=False)
    values = column.fill_null(False).to_numpy(zero_copy_only=False)
    return pa.array(np.where(nulls, "null", np.where(values, "true", "false")))


def check_columns(table) -> None:
    """The 2 derivations the site makes hold on every row: `list_count` is
    the number of names in `listed_by`, and `listed_by` names `scowl`
    exactly where `scowl_size` is above 0."""
    import numpy as np
    names = table["listed_by"].to_pylist()
    parts = [n.split(";") if n else [] for n in names]
    count = np.array([len(p) for p in parts])
    if np.any(count != table["list_count"].to_numpy(zero_copy_only=False)):
        raise OpenComposeError("list_count is not the number of names in listed_by")
    scowl = np.array(["scowl" in p for p in parts])
    size = table["scowl_size"].fill_null(0).to_numpy(zero_copy_only=False)
    if np.any(scowl != (size > 0)):
        raise OpenComposeError("listed_by names scowl where scowl_size is not above 0, or the reverse")


def cube_of(table) -> tuple[list[dict], list[list[int]]]:
    """The cube's dimensions (name and values, in order) and its cells."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    check_columns(table)
    length = pc.utf8_length(table["word"]).to_numpy(zero_copy_only=False)
    tokens = table["token_count"].to_numpy(zero_copy_only=False)
    sizes = table["scowl_size"]
    frame = pa.table({
        "listed_by": table["listed_by"],
        "scowl_size": pa.array(np.where(sizes.is_null().to_numpy(zero_copy_only=False), "null",
                                        sizes.fill_null(0).to_numpy(zero_copy_only=False).astype(str))),
        "token_count": pa.array(np.where(tokens >= TOKEN_CAP, f"{TOKEN_CAP}+", tokens.astype(str))),
        "length": pa.array(np.where(length >= LENGTH_CAP, f"{LENGTH_CAP}+", length.astype(str))),
        "classes": table["classes"],
        "gb_type": _tri(table["gb_type"]),
        "wn_instance": _tri(table["wn_instance"]),
        "wk_proper_noun": _tri(table["wk_proper_noun"]),
    })
    raw = frame.group_by(list(DIMENSIONS)).aggregate([([], "count_all")]).to_pylist()

    def order(name: str, values: set[str]) -> list[str]:
        if name in ("token_count", "length"):
            return sorted(values, key=lambda v: int(v.rstrip("+")))
        if name == "scowl_size":
            unknown = values - set(SCOWL_VALUES)
            if unknown:
                raise OpenComposeError(f"scowl_size holds {sorted(unknown)}, outside the sizes the subset names")
            return [v for v in SCOWL_VALUES if v in values]
        if name in ("gb_type", "wn_instance", "wk_proper_noun"):
            return [v for v in ("true", "false", "null") if v in values]
        return sorted(values)

    dims = [{"name": name, "values": order(name, {c[name] for c in raw})} for name in DIMENSIONS]
    position = [{v: i for i, v in enumerate(d["values"])} for d in dims]
    cells = sorted([position[k][c[name]] for k, name in enumerate(DIMENSIONS)] + [c["count_all"]]
                   for c in raw)
    if sum(c[-1] for c in cells) != table.num_rows:
        raise OpenComposeError("the cube's cells do not sum to the rows")
    return dims, cells


def file_metadata(path: Path) -> dict[str, str]:
    import pyarrow.parquet as pq
    kv = pq.ParquetFile(path).metadata.metadata or {}
    out = {}
    for key in METADATA_KEYS:
        value = kv.get(key.encode())
        if value is None:
            raise OpenComposeError(f"{path.name} has no {key} in its metadata")
        out[key] = value.decode("utf-8")
    return out


def build(path: Path) -> dict[Path, str]:
    """The 2 files as text, keyed by path."""
    import pyarrow.parquet as pq
    pin = pinned()
    if not path.exists():
        raise OpenComposeError(f"{path} is absent; the cube and the layout are read from the subset's file "
                               f"(python3 -m research.release.open_subset --out DIR rebuilds it)")
    if sha256_file(path) != pin["sha256"]:
        raise OpenComposeError(f"{path.name} is not the file the subset's record names")
    meta = file_metadata(path)
    if meta["ceol.attribution"] != O.ATTRIBUTION or meta["ceol.license"] != O.LICENSE:
        raise OpenComposeError(f"{path.name}'s license or attribution is not the subset's")
    table = pq.read_table(path, columns=list(READ_COLUMNS))
    if table.num_rows != pin["rows"]:
        raise OpenComposeError(f"{path.name} holds {table.num_rows} rows; the record says {pin['rows']}")
    dims, cells = cube_of(table)
    found = L.layout_of(path, columns=READ_COLUMNS)
    head = {"version": VERSION, "dataset": DATASET, "commit": pin["commit"],
            "generated_by": "pipeline/research/release/open_compose.py"}
    source = {"config": CONFIG, "path": HUB_PATH, "sha256": pin["sha256"], "rows": table.num_rows}
    cube = {**head,
            "what": ("the count of rows of the open subset's open-lists config for every combination "
                     "of the dimensions; a cell is 1 index into each dimension's values, in order, "
                     "then the count"),
            "source": source,
            "caps": {"length": LENGTH_CAP, "token_count": TOKEN_CAP},
            "dimensions": dims, "cells": cells}
    layout = {**head,
              "what": ("where the strings and the criteria's columns lie in each row group of the "
                       "open subset's open-lists file, for the site's list download; offsets and "
                       "sizes in bytes"),
              "hub_path": HUB_PATH, "url": hub_url(pin["commit"]),
              "bytes": pin["bytes"], "sha256": pin["sha256"],
              "metadata": meta, **found}
    return {
        CUBE_OUT: json.dumps(cube, ensure_ascii=False, separators=(",", ":")) + "\n",
        LAYOUT_OUT: json.dumps(layout, indent=1, ensure_ascii=False) + "\n",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", type=Path, default=None, help="the open-lists file (default: the build's folder)")
    ap.add_argument("--check", action="store_true", help="compare the committed files with fresh ones")
    args = ap.parse_args(argv)
    try:
        built = build((args.file or default_file()).resolve())
    except (OpenComposeError, L.LayoutError, FileNotFoundError) as exc:
        print(f"[open-compose] {exc}", file=sys.stderr)
        return 1
    stale = []
    for path, text in built.items():
        rel = path.relative_to(O.REPO)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(rel)
            else:
                print(f"[open-compose] {rel} re-derives")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"[open-compose] {len(text.encode('utf-8')):>8,} bytes  {rel}")
    for rel in stale:
        print(f"[open-compose] {rel} does not re-derive", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
