"""The figures file and the cube of a public version, which the site and the
kit read (rule 3).

    python3 -m research.release.figures --version v2.1          write them
    python3 -m research.release.figures --version v2.1 --check  rebuild and compare

It reads the version's release record and its `universe` file, held to the
record's sha256 before it is read, and writes 2 files under
`research/release/figures/<version>/`:

- `figures.json`: every headline figure as `{id, value, what, source}`.
  An id is stable across versions; a value is an integer count; `source`
  is the file it was counted from. The site, the kit, and the blog post
  quote a figure by its id and never type it.
- `cube.json`: the count of rows for every combination of the dimensions in
  `DIMENSIONS`, over all rows of the version. A filter on those dimensions
  ("compose a list") is answered by summing cells. A cell is 1 index into
  each dimension's values, in order, then the count.

Counts only: no string of the universe is written or printed. The figure
check (`check_release_figures` in research/verify_doc_numbers.py) holds both
files: where data/ exists it rebuilds them from the release file and
compares; in a clone it runs the ties to the record and declares the rebuild
a deferral.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.release import build_release as B
from research.release import withholding as W

REPO = B.REPO

#: the cube's dimensions, in the order of a cell's indices
DIMENSIONS = ("intake_layer", "intake_kind", "provenance_class", "eol",
              "panel_sets", "class_explicit", "token_count", "length",
              "gb_type", "wordfreq_scored", "wikt_title_any",
              "model_or_engine")
#: lengths and token counts at or above these are 1 value ("25+", "4+")
LENGTH_CAP = 25
TOKEN_CAP = 4

INHERITED_LAYERS = ("eol_valid", "eol_invalid")


def out_dir(version: str) -> Path:
    return REPO / "research" / "release" / "figures" / version


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO.parent).as_posix()
    except ValueError:
        return path.as_posix()


def _universe(spec: B.VersionSpec, record: dict):
    import pyarrow.parquet as pq
    files = {f["config"]: f for f in record["files"]}
    path = spec.out_dir / "universe.parquet"
    if sha256_file(path) != files["universe"]["sha256"]:
        raise B.ReleaseError(f"{_rel(path)} is not the file the release record "
                             "names")
    return pq.read_table(path)


def cube_of(table) -> tuple[list[dict], list[list[int]]]:
    """The cube's dimensions (name and values, in order) and its cells."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    def tri(column):
        nulls = column.is_null().to_numpy(zero_copy_only=False)
        values = column.fill_null(False).to_numpy(zero_copy_only=False)
        return pa.array(np.where(nulls, "null",
                                 np.where(values, "true", "false")))

    length = pc.utf8_length(table["word"]).to_numpy(zero_copy_only=False)
    tokens = table["token_count"].to_numpy(zero_copy_only=False)
    frame = pa.table({
        "intake_layer": table["intake_layer"],
        "intake_kind": table["intake_kind"],
        "provenance_class": table["provenance_class"],
        "eol": tri(table["eol"]),
        "panel_sets": table["panel_sets"],
        "class_explicit": table["class_explicit"],
        "token_count": pa.array(np.where(tokens >= TOKEN_CAP, f"{TOKEN_CAP}+",
                                         tokens.astype(str))),
        "length": pa.array(np.where(length >= LENGTH_CAP, f"{LENGTH_CAP}+",
                                    length.astype(str))),
        "gb_type": tri(table["gb_type"]),
        "wordfreq_scored": tri(table["wordfreq_scored"]),
        "wikt_title_any": tri(table["wikt_title_any"]),
        "model_or_engine": table["model_or_engine"],
    })
    raw = frame.group_by(list(DIMENSIONS)).aggregate(
        [([], "count_all")]).to_pylist()

    def order(name: str, values: set[str]) -> list[str]:
        if name in ("token_count", "length"):
            return sorted(values, key=lambda v: int(v.rstrip("+")))
        if name == "provenance_class":
            return [c for c in W.CLASSES if c in values]
        return sorted(values)

    dims = [{"name": name, "values": order(name, {c[name] for c in raw})}
            for name in DIMENSIONS]
    position = [{v: i for i, v in enumerate(d["values"])} for d in dims]
    cells = sorted([position[k][c[name]] for k, name in enumerate(DIMENSIONS)]
                   + [c["count_all"]] for c in raw)
    if sum(c[-1] for c in cells) != table.num_rows:
        raise B.ReleaseError("the cube's cells do not sum to the rows")
    return dims, cells


def figures_of(table, record: dict, dims: list[dict], cells: list[list[int]],
               universe: str, record_path: str) -> list[dict]:
    """The headline figures, each with its id, value, meaning, and source."""
    import pyarrow as pa
    import pyarrow.compute as pc
    out: list[dict] = []

    def add(id_: str, value: int, what: str, source: str = universe) -> None:
        out.append({"id": id_, "value": int(value), "what": what,
                    "source": source})

    def marginal(name: str) -> dict[str, int]:
        k = DIMENSIONS.index(name)
        totals = {v: 0 for v in dims[k]["values"]}
        for cell in cells:
            totals[dims[k]["values"][cell[k]]] += cell[-1]
        return totals

    # the record's counts
    pin = record["pin_counts"]
    add("pin.rows", pin["rows"], "candidates in the pin (C-016)", record_path)
    add("pin.restricted_rows", pin["restricted_rows"],
        "rows of the pin attested only by restricted lists, in no version",
        record_path)
    add("pin.shippable_rows", pin["shippable_rows"],
        "rows of the pin that a version may carry", record_path)
    held = record["projection"]["held_back"]
    add("held_back.rows", held["rows"],
        "shippable rows held back by the public projection (D-011)",
        record_path)
    for reason, n in held["by_reason"].items():
        add(f"held_back.{reason}", n, W.HELD_BACK_REASONS[reason], record_path)
    for f in record["files"]:
        add(f"config.{f['config']}.rows", f["rows"],
            f"rows of the {f['config']} config ({f['predicate']})",
            record_path)

    # counted from the universe file
    n = table.num_rows
    add("rows", n, "rows of the universe config, 1 per candidate string")
    for name in ("intake_layer", "intake_kind", "provenance_class",
                 "model_or_engine", "token_count", "class_explicit"):
        for value, count in marginal(name).items():
            add(f"rows.by_{name}.{value}", count,
                f"rows whose {name} is {value}")
    # the EOL's pinned revision, as its dictionaries' manifest records it,
    # held to the inherited rows' tag (note 5)
    manifest = json.loads((REPO / "research" / "provenance" /
                           "eol_dictionaries_manifest.json").read_text(encoding="utf-8"))
    revision = manifest["revision"][:8]
    if W.INHERITED_SOURCES_TAG != f"eol_universe@{revision}":
        raise B.ReleaseError("the inherited tag is not the manifest's revision")
    add("rows.eol", marginal("eol")["true"],
        f"rows in the EOL's valid list at its pinned revision {revision}")
    sets = marginal("panel_sets")
    add("rows.listed_by_no_published_set", sets.get("", 0),
        "rows that no published panel set lists")
    add("rows.listed_by_a_published_set", n - sets.get("", 0),
        "rows that 1 or more published panel sets list")
    for name in W.PUBLISHED_SETS:
        count = sum(c for combo, c in sets.items()
                    if name in combo.split(";"))
        add(f"rows.listed_by.{name}", count, f"rows that {name} lists")
    for name in ("gb_type", "wordfreq_scored", "wikt_title_any"):
        add(f"rows.{name}", marginal(name)["true"], f"rows whose {name} is true")
    add("rows.channel_withheld", int(pc.sum(pc.equal(
        table["intake_channels"], W.CHANNEL_WITHHELD)).as_py() or 0),
        f"rows whose every intake channel is withheld ({W.CHANNEL_WITHHELD})")
    inherited = pc.is_in(table["intake_layer"],
                         value_set=pa.array(list(INHERITED_LAYERS)))
    none = pc.equal(table["panel_count"], 0)
    gb = pc.fill_null(table["gb_type"], False)
    wf = pc.fill_null(table["wordfreq_scored"], False)
    single = pc.equal(table["token_count"], 1)

    def count(mask) -> int:
        return int(pc.sum(mask).as_py() or 0)
    add("rows.inherited_google_books_no_published_set",
        count(pc.and_(pc.and_(inherited, none), gb)),
        "rows inherited from the EOL that no published panel set lists and "
        "that are Google Books 1-gram types")
    add("rows.inherited_google_books_only",
        count(pc.and_(pc.and_(pc.and_(inherited, none), gb), pc.invert(wf))),
        "of those, the rows whose only published containment is Google Books")
    add("rows.single_token_no_published_set_no_corpus",
        count(pc.and_(pc.and_(single, none),
                      pc.invert(pc.or_(gb, wf)))),
        "single-token rows that no published panel set lists and that "
        "neither corpus holds")

    # the projection's sizes, from the code
    code = "pipeline/research/release/withholding.py"
    add("projection.published_sets", len(W.PUBLISHED_SETS),
        "panel sets published", code)
    add("projection.withheld_lists", len(W.WITHHELD_SETS),
        "lists whose columns and labels are withheld", code)
    add("projection.withheld_feature_columns", len(W.WITHHELD_FEATURES),
        "feature columns withheld", code)
    files = {f["config"]: f for f in record["files"]}
    for config in ("universe", "features"):
        add(f"columns.{config}", len(files[config]["columns"]),
            f"columns of the {config} config", record_path)
    ids = [x["id"] for x in out]
    if len(set(ids)) != len(ids):
        raise B.ReleaseError("a figure id repeats")
    return out


def build(version: str) -> dict[Path, str]:
    """The 2 files as text, keyed by path."""
    spec = B.resolve(version)
    if not spec.public:
        raise B.ReleaseError(f"{version} is not a public version")
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    table = _universe(spec, record)
    dims, cells = cube_of(table)
    # the file as a reader finds it: its path in the dataset, at the
    # version's tag (the upload creates it), with its sha256
    universe = f"data/universe.parquet at {record['dataset']}@{version}"
    head = {"version": version, "dataset": record["dataset"],
            "built_on": record["built_on"],
            "generated_by": "pipeline/research/release/figures.py",
            "record": _rel(spec.record_out),
            "source": {"path": universe,
                       "sha256": next(f["sha256"] for f in record["files"]
                                      if f["config"] == "universe"),
                       "rows": table.num_rows}}
    figures = figures_of(table, record, dims, cells, universe,
                         head["record"])
    d = out_dir(version)
    return {
        d / "figures.json": json.dumps(
            {**head, "what": "headline counts, each with its id, meaning, and "
                             "the file it was counted from",
             "figures": figures}, indent=1, ensure_ascii=False) + "\n",
        d / "cube.json": json.dumps(
            {**head, "what": "the count of rows for every combination of the "
                             "dimensions; a cell is 1 index into each "
                             "dimension's values, in order, then the count",
             "caps": {"length": LENGTH_CAP, "token_count": TOKEN_CAP},
             "dimensions": dims, "cells": cells},
            ensure_ascii=False, separators=(",", ":")) + "\n",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the files")
    args = ap.parse_args(argv)
    try:
        built = build(args.version)
    except (B.ReleaseError, FileNotFoundError) as exc:
        print(f"[figures] refused: {exc}", file=sys.stderr)
        return 1
    stale = []
    for path, text in built.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        print(f"[figures] {len(text.encode('utf-8')):>9,} bytes  {_rel(path)}")
    for path in stale:
        print(f"[figures] {_rel(path)} differs from what the code prints",
              file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
