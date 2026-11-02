#!/usr/bin/env python3
"""Build `site/fixtures/` and `kit/fixtures/` from v1.0's release files.

    python3 tools/build_fixtures.py            build both folders
    python3 tools/build_fixtures.py --check    rebuild in memory and compare

The fixtures are samples of v1.0's rows for building the site's lookup and
the kit's notebooks and tests. Every row is a row of v1.0's `universe`
config, which the public projection already shaped
(`research.release.withholding`; D-010, D-011), and every feature row a row
of its `features` config. The figures and the cube the site and the kit read
are not fixtures: the pipeline writes them, to
`pipeline/research/release/figures/v1.0/` (`research.release.figures`).

What is built:

- **A sample of rows by hash ranking.** A stratum is an intake layer. Within
  a stratum the rows are ranked by `sha256(key:stratum:word)` in ascending
  order, and the first N are taken. The key is random and private
  (`safeguards.keys`, in `private/keys/`; D-012 line 5): with a public key,
  anyone could recompute the ranking and find the rows the scan passed over. The kit's sample holds `KIT_PER_STRATUM`
  rows per stratum and the site's holds the first `SITE_PER_STRATUM` of the
  same ranking, so the site's sample is a subset of the kit's. A row in
  which the scan finds a study item or a restricted word is passed over,
  and the manifests do not count those rows (D-012 line 5).
- **The features config's rows** for the single-token rows of the kit's
  sample, in the same order.

The builder prints counts and never a string of the universe.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import _paths
from _paths import REPO

from research.release import withholding  # noqa: E402
from safeguards import keys, locations, restricted, wall  # noqa: E402
from safeguards.examples import clean_mask  # noqa: E402

VERSION = "v1.0"
#: the stated rule; the key itself is private (D-012 line 5)
RULE = ("within a stratum, rows ranked by sha256(key:stratum:word) in "
        "ascending order, with a random key kept privately; the first N taken; "
        "a row in which the scan finds a study item or a restricted word "
        "passed over")
SITE_PER_STRATUM = 1_000
KIT_PER_STRATUM = 4_000
#: rows ranked beyond the sample, so that rows the scan passes over are replaced
MARGIN = 200

SITE = REPO / "site" / "fixtures"
KIT = REPO / "kit" / "fixtures"
FIGURES = f"pipeline/research/release/figures/{VERSION}/"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _remap(column, fn):
    """A low-cardinality string column through `fn`, value by distinct value."""
    import pyarrow.compute as pc
    encoded = pc.dictionary_encode(column).combine_chunks()
    values = [fn(v) for v in encoded.dictionary.to_pylist()]
    return values, encoded.indices.to_numpy(zero_copy_only=False)


def _read(release: Path, files: dict, config: str, **kw):
    import pyarrow.parquet as pq
    path = release / f"{config}.parquet"
    if sha256_bytes(path.read_bytes()) != files[config]["sha256"]:
        raise SystemExit(f"data/release: {config}.parquet is not the file the "
                         "release record names")
    return pq.read_table(path, **kw)


def build() -> dict[str, bytes]:
    """Every fixture file as bytes, keyed by its path under the repository."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    release = locations.data_dir() / "release" / f"ceol-universe-{VERSION}"
    record = json.loads((REPO / "pipeline" / "research" / "release" /
                         f"release_{VERSION}.json").read_text(encoding="utf-8"))
    files = {f["config"]: f for f in record["files"]}
    table = _read(release, files, "universe")
    n = table.num_rows
    if n != files["universe"]["rows"] or \
            table.column_names != files["universe"]["columns"]:
        raise SystemExit("the universe config is not the file the record names")
    # the class rule, held to the file's own column on its published fields
    own = withholding.classes_of(table["intake_channels"], table["panel_count"],
                                 table["gb_type"], table["wordfreq_scored"])
    if not pc.all(pc.equal(own, table["provenance_class"])).as_py():
        raise SystemExit("provenance_class does not re-derive from the "
                         "published fields")

    # ---- the sample -------------------------------------------------------
    # every row's digest, as 4 big-endian 64-bit integers: their order is
    # the order of the digests' bytes, which is the order of their hex forms
    key = keys.key("fixtures")
    strata, stratum_index = _remap(table["intake_layer"], str)
    digests = bytearray(n * 32)
    at = 0
    for chunk in table["word"].chunks:
        for word in chunk.to_pylist():
            stratum = strata[stratum_index[at]]
            digests[at * 32:(at + 1) * 32] = hashlib.sha256(
                f"{key}:{stratum}:{word}".encode("utf-8")).digest()
            at += 1
    ranks = np.frombuffer(bytes(digests), dtype=">u8").reshape(n, 4)
    del digests
    terms, restricted_words = wall.all_terms(), restricted.restricted_words()
    kit_index: list[int] = []
    site_index: list[int] = []
    for code in sorted(range(len(strata)), key=lambda c: strata[c]):
        members = np.flatnonzero(stratum_index == code)
        k = ranks[members]
        ranked = members[np.lexsort((k[:, 3], k[:, 2], k[:, 1], k[:, 0]))][
            :KIT_PER_STRATUM + MARGIN].tolist()
        candidates = table["word"].take(pa.array(ranked)).to_pylist()
        mask = clean_mask(candidates, terms, restricted_words)
        clean = [i for i, ok in zip(ranked, mask) if ok]
        if len(clean) < KIT_PER_STRATUM:
            raise SystemExit(f"stratum {strata[code]}: the margin is too small")
        kit_index.extend(clean[:KIT_PER_STRATUM])
        site_index.extend(clean[:SITE_PER_STRATUM])
    del ranks

    def published(indices: list[int]) -> list[dict]:
        out = table.take(pa.array(indices)).to_pylist()
        for row in out:
            if withholding.reveals_a_withheld_list(row):
                raise SystemExit("a published row names a withheld list")
        return out

    kit_rows, site_rows = published(kit_index), published(site_index)
    kit_table = pa.Table.from_pylist(kit_rows, schema=table.schema)
    sink = io.BytesIO()
    pq.write_table(kit_table, sink, compression="zstd")
    kit_parquet = sink.getvalue()

    features = _read(release, files, "features", filters=[
        ("id", "in", [r["id"] for r in kit_rows if r["token_count"] == 1])])
    withheld = set(features.column_names) & set(withholding.WITHHELD_FEATURES)
    if withheld:
        raise SystemExit(f"the features file carries withheld columns {sorted(withheld)}")
    position_of = {row["id"]: k for k, row in enumerate(kit_rows)}
    features = features.take(pc.sort_indices(pa.array(
        [position_of[i] for i in features["id"].to_pylist()])))
    sink = io.BytesIO()
    pq.write_table(features, sink, compression="zstd")
    features_parquet = sink.getvalue()

    site_jsonl = "".join(json.dumps(row, ensure_ascii=False) + "\n"
                         for row in site_rows).encode("utf-8")

    common = {
        "source": {"version": VERSION, "config": "universe",
                   "sha256": files["universe"]["sha256"],
                   "rows": files["universe"]["rows"]},
        "projection": "pipeline/research/release/withholding.py, applied by "
                      "the release build (D-010, D-011)",
        "figures_and_cube": FIGURES,
        "published_sets": list(withholding.PUBLISHED_SETS),
    }
    sampling = {"rule": RULE, "key": "private (D-012 line 5)",
                "stratum": "intake_layer", "strata": sorted(strata)}
    out = {
        "site/fixtures/rows.jsonl": site_jsonl,
        "kit/fixtures/universe_sample.parquet": kit_parquet,
        "kit/fixtures/features_sample.parquet": features_parquet,
    }

    def manifest(folder: str, sample: dict) -> bytes:
        return json.dumps({
            "what": f"the fixtures of {folder}/, built by tools/build_fixtures.py",
            **common,
            "columns": list(table.column_names),
            "sampling": {**sampling, **sample},
            "files": {Path(path).name: {"sha256": sha256_bytes(data),
                                        "bytes": len(data)}
                      for path, data in sorted(out.items())
                      if path.startswith(folder + "/")},
        }, indent=1).encode("utf-8") + b"\n"

    out["site/fixtures/MANIFEST.json"] = manifest("site/fixtures", {
        "rows_per_stratum": SITE_PER_STRATUM, "rows": len(site_rows)})
    out["kit/fixtures/MANIFEST.json"] = manifest("kit/fixtures", {
        "rows_per_stratum": KIT_PER_STRATUM, "rows": len(kit_rows),
        "feature_rows": features.num_rows,
        "feature_columns": list(features.column_names)})
    return out


#: the files earlier builds wrote that the pipeline's figures folder replaces
RETIRED = ("site/fixtures/cube.json", "site/fixtures/figures.json",
           "kit/fixtures/cube.json", "kit/fixtures/figures.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the files")
    args = ap.parse_args(argv)
    built = build()
    differing = []
    for rel, data in sorted(built.items()):
        path = REPO / rel
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                differing.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(f"{len(data):>10,} bytes  {rel}")
    for rel in RETIRED:
        path = REPO / rel
        if path.exists():
            if args.check:
                differing.append(rel)
            else:
                path.unlink()
                print(f"   removed  {rel}")
    for rel in differing:
        print(f"DIFFERS {rel}")
    return 1 if differing else 0


if __name__ == "__main__":
    raise SystemExit(main())
