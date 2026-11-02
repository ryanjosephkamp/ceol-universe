"""Profile a version of the CEOL Universe from its release files alone
(C-078 line 10; research/release/PACKAGE_UR1.md §5).

An earlier profile (September 25, 2026) read the pinned layers; this
profile reads only what the version ships (`data/release/ceol-universe-<v>/`),
so every figure describes the release and nothing else. It computes every
distribution the profile page and the card quote and writes them to
`profile.json` (counts and labels only: value counts are taken over
label-valued columns, never over `word` or `id`), and draws the plots under
`plots/` with png_plot.py. The output is deterministic: no timestamp, no
timing, floats rounded to 9 significant digits, the plots recorded by
the hash of their pixels. The earlier profile's posterior, intake-ledger,
and walled-term sections are not computed, because no release file holds
that material (C-078 lines 4 and 5). No word is printed.

Run:  python3 -m research.release.profile.universe_profile --version v2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from ceol.ingest.common import sha256_file
from research.release import build_release as B
from research.release import columns as C

from . import png_plot as P

HERE = Path(__file__).resolve().parent
PROFILE_JSON = HERE / "profile.json"
PLOTS_DIR = HERE / "plots"

FILE_ORDER = ("universe", "features", "panel-listed", "eol-valid", "spaced",
              "exceptions", "sample")
BOOL_COLUMNS = ("eol", "eol_universe", "c4_addition", "is_restricted",
                "c015_addition", "wn_instance", "wn_capitalized",
                "wk_proper_noun", "variety_gb_not_us", "variety_us_not_gb",
                "gb_type", "wordfreq_scored", "wikt_title_any")
LABEL_COLUMNS = ("intake_layer", "intake_kind", "provenance_class",
                 "eol_phase1_tier", "eol_record", "eol_synthetic_category",
                 "eol_synthetic_engine_inferred", "model_or_engine")
HIST_FEATURES = ("wordfreq_zipf", "gb_log10_match",
                 "orthotactic_logp_per_char", "zipf_log10_rank",
                 "morph_productivity_vn", "segment_attested_fraction")
LENGTH_BINS = list(range(0, 41)) + [60, 100, 200]
ACCENTED = "áàâäéèêëíîïñóôöúûüç"
LIGATURES = "æœ"


def _num(x: float) -> float:
    return float(f"{x:.9g}")


def _key(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def vc(arr) -> dict[str, int]:
    """Value counts of a label-valued column, nulls under "null"."""
    import pyarrow.compute as pc
    out = {_key(r["values"]): int(r["counts"])
           for r in pc.value_counts(arr).to_pylist()}
    return dict(sorted(out.items()))


def split_counts(arr) -> tuple[dict[str, int], dict[str, int]]:
    """Per-label counts and the labels-per-row distribution of a
    ';'-joined column (the empty string holds no label; nulls skipped)."""
    import pyarrow.compute as pc
    arr = pc.drop_null(arr)
    lists = pc.split_pattern(arr, ";")
    lens = pc.list_value_length(lists).to_numpy(zero_copy_only=False)
    empty = pc.equal(arr, "").to_numpy(zero_copy_only=False)
    lens = np.where(empty, 0, lens)
    per_label = vc(pc.list_flatten(lists))
    per_label.pop("", None)
    values, counts = np.unique(lens, return_counts=True)
    per_row = {str(int(v)): int(c) for v, c in zip(values, counts)}
    return per_label, per_row


def quantiles(values: np.ndarray) -> dict | None:
    v = values[~np.isnan(values)]
    if v.size == 0:
        return None
    names = ("min", "p1", "p5", "p25", "p50", "p75", "p95", "p99", "max")
    qs = np.quantile(v, [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1])
    return {"n": int(v.size), "nan": int(values.size - v.size),
            "mean": _num(float(v.mean())),
            "q": {k: _num(float(x)) for k, x in zip(names, qs)}}


def hist(values: np.ndarray, bins) -> dict:
    counts, edges = np.histogram(values, bins=bins)
    return {"edges": [_num(float(e)) for e in edges],
            "counts": [int(c) for c in counts]}


def group_count(table, key: str, flag: str) -> dict[str, dict[str, int]]:
    """Rows and rows with `flag` true, per value of `key`."""
    import pyarrow.compute as pc
    t = table.select([key, flag])
    t = t.append_column("_one", pc.cast(t[flag], "int64"))
    agg = t.group_by(key).aggregate([("_one", "count"), ("_one", "sum")])
    return dict(sorted((_key(k), {"rows": int(n), flag: int(s or 0)})
                       for k, n, s in zip(agg[key].to_pylist(),
                                          agg["_one_count"].to_pylist(),
                                          agg["_one_sum"].to_pylist())))


def profile_universe(u) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    U: dict = {"rows": u.num_rows,
               "distinct_words": int(pc.count_distinct(u["word"]).as_py()),
               "distinct_ids": int(pc.count_distinct(u["id"]).as_py()),
               "columns": len(u.column_names),
               "nulls": {c: int(u[c].null_count) for c in u.column_names}}
    for c in BOOL_COLUMNS:
        U[c] = vc(u[c])
    U["token_count"] = vc(u["token_count"])
    U["intake_date"] = vc(u["intake_date"])
    U["class_explicit"] = vc(u["class_explicit"])
    U["classes_per_label"], U["classes_per_row"] = split_counts(u["classes"])
    U["sources_per_label"], U["sources_per_row"] = split_counts(u["sources"])
    U["wk_flags_per_label"], U["wk_flags_per_row"] = split_counts(
        u["wk_flags"])
    words = u["word"]
    eol = u["eol"].to_numpy(zero_copy_only=False)
    lengths = pc.utf8_length(words).to_numpy(zero_copy_only=False)
    bins = sorted(set(LENGTH_BINS + [int(lengths.max()) + 1]))
    U["length"] = {"quantiles": quantiles(lengths.astype(float)),
                   "max": int(lengths.max()),
                   "hist": hist(lengths, bins),
                   "hist_eol": hist(lengths[eol], bins)}
    first = pc.utf8_slice_codeunits(words, 0, 1)
    U["first_char"] = vc(first)
    U["first_char_eol"] = vc(pc.filter(first, pa.array(eol)))

    def has(pattern: str) -> int:
        return int(pc.sum(pc.match_substring_regex(words, pattern)).as_py()
                   or 0)
    U["character_use"] = {
        "hyphen": has("-"), "apostrophe": has("'"), "space": has(" "),
        "accented_letter": has(f"[{ACCENTED}]"),
        "ligature": has(f"[{LIGATURES}]"),
        "ascii_letters_only": has("^[a-z]+$")}
    U["eol_by_token_count"] = group_count(u, "token_count", "eol")
    U["eol_by_class_explicit"] = group_count(u, "class_explicit", "eol")
    U["panel_count"] = vc(u["panel_count"])
    U["eol_by_panel_count"] = group_count(u, "panel_count", "eol")
    U["panel_sets_per_label"], _ = split_counts(u["panel_sets"])

    # a public version carries the published evidence columns only
    single = u.filter(pc.equal(u["token_count"], 1))
    E = {"rows": single.num_rows,
         "values": {c: vc(u[c]) for c in C.EVIDENCE_LAYER_COLUMNS
                    if c in u.column_names},
         "listed": {name: int(pc.sum(pc.equal(u[name], 1)).as_py() or 0)
                    for name in C.DETECTORS if name in u.column_names}}
    E["listed"]["scowl"] = int(pc.sum(pc.greater(u["scowl_tier"], 0))
                               .as_py() or 0)
    E["single_token_panel_count"] = vc(single["panel_count"])
    U["evidence"] = E

    V = {c: vc(u[c]) for c in LABEL_COLUMNS if c in u.column_names}
    V["intake_channels_per_label"], V["intake_channels_per_row"] = \
        split_counts(u["intake_channels"])
    t = u.select(["intake_layer", "intake_kind"])
    agg = t.group_by(["intake_layer", "intake_kind"]).aggregate(
        [([], "count_all")]).to_pylist()
    V["layer_by_kind"] = {}
    for row in sorted(agg, key=lambda r: (r["intake_layer"],
                                          r["intake_kind"])):
        V["layer_by_kind"].setdefault(row["intake_layer"], {})[
            row["intake_kind"]] = int(row["count_all"])
    U["provenance"] = V

    # the limitations the card states first (reading R13)
    inherited = pc.is_in(u["intake_layer"], value_set=pa.array(
        ["eol_valid", "eol_invalid"])).to_numpy(zero_copy_only=False)
    gb = pc.fill_null(u["gb_type"], False).to_numpy(zero_copy_only=False)
    wf = pc.fill_null(u["wordfreq_scored"], False).to_numpy(
        zero_copy_only=False)
    none = (u["panel_count"].to_numpy(zero_copy_only=False) == 0)
    tok1 = (u["token_count"].to_numpy(zero_copy_only=False) == 1)
    U["limits"] = {
        "gb_type_rows": int(gb.sum()),
        "gb_type_inherited_rows": int((gb & inherited).sum()),
        "gb_type_inherited_no_panel_set": int((gb & inherited & none)
                                              .sum()),
        "gb_type_no_panel_set": int((gb & none).sum()),
        "single_token_no_panel_set": int((tok1 & none).sum()),
        "single_token_no_panel_set_no_corpus": int(
            (tok1 & none & ~gb & ~wf).sum()),
        "inherited_rows": int(inherited.sum()),
    }
    if "model_or_engine" in u.column_names:
        # a public version's card (v2.1 on) states, of those rows, how many
        # Google Books alone contains (no wordfreq score); v2.0's profile
        # does not carry the key
        U["limits"]["gb_type_inherited_no_panel_set_no_wordfreq"] = int(
            (gb & inherited & none & ~wf).sum())
    return U


def profile_features(f) -> dict:
    import pyarrow as pa
    F: dict = {"rows": f.num_rows, "columns": {}}
    for name in (c for c in C.FEATURE_LAYER_COLUMNS if c in f.column_names):
        col = f[name]
        if pa.types.is_boolean(col.type):
            F["columns"][name] = {"type": "bool", "values": vc(col)}
            continue
        arr = col.to_numpy(zero_copy_only=False).astype(float)
        entry = {"type": str(col.type), "nulls": int(col.null_count),
                 "quantiles": quantiles(arr)}
        if name == "ocr_neighbor_hits":
            entry["values"] = vc(col)
        if name in HIST_FEATURES and entry["quantiles"]:
            entry["hist"] = hist(arr[~np.isnan(arr)], 40)
        F["columns"][name] = entry
    return F


def _sorted_numeric(d: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(d.items(), key=lambda kv: float(kv[0]))


def charts(U: dict, F: dict) -> dict[str, tuple[str, P.Canvas]]:
    """The plots, name to (title, canvas)."""
    out: dict[str, tuple[str, P.Canvas]] = {}

    def plot(name, title, xlabel, items, **kw):
        labels = [k for k, _ in items]
        values = [float(v) for _, v in items]
        out[name] = (title, P.bar_chart(labels, [("rows", values, P.ACCENT)],
                                        title, xlabel, **kw))

    plot("token_count.png", "Rows by tokens per row", "tokens",
        _sorted_numeric(U["token_count"]))
    plot("intake_date.png", "Rows by intake date", "intake date",
        sorted(U["intake_date"].items()))
    top = sorted(U["class_explicit"].items(), key=lambda kv: (-kv[1],
                                                              kv[0]))[:20]
    plot("classes.png", "Rows by class_explicit, the 20 largest values",
        "class", top)
    plot("sources_per_label.png", "Rows by label of the pin's sources column",
        "source label", sorted(U["sources_per_label"].items(),
                               key=lambda kv: (-kv[1], kv[0])))
    plot("sources_per_row.png", "Rows by the number of source labels",
        "labels on the row", _sorted_numeric(U["sources_per_row"]))
    h, he = U["length"]["hist"], U["length"]["hist_eol"]
    labels = [str(int(e)) for e in h["edges"][:40]]
    out["length_by_eol.png"] = (
        "Rows by length in characters, up to 40",
        P.bar_chart(labels, [("all rows", [float(c) for c in h["counts"][:40]],
                              P.SECOND),
                             ("in the EOL valid list at the pin",
                              [float(c) for c in he["counts"][:40]],
                              P.ACCENT)],
                    "Rows by length in characters, up to 40",
                    "characters", label_every=5))
    plot("first_char.png", "Rows by first character", "first character",
        sorted(U["first_char"].items()))
    listed = U["evidence"]["listed"]
    plot("per_detector.png", "Single-token rows listed, by panel set",
        "panel set", [(k, listed[k]) for k in C.PANEL_SETS if k in listed])
    plot("panel_sets.png", "Rows by the number of panel sets listing them",
        "panel sets", _sorted_numeric(U["panel_count"]))
    V = U["provenance"]
    for name, col, title in (
            ("prov_layer.png", "intake_layer", "Rows by intake layer"),
            ("prov_kind.png", "intake_kind", "Rows by intake kind"),
            ("prov_class.png", "provenance_class",
             "Rows by provenance class")):
        plot(name, title, col, sorted(V[col].items(),
                                     key=lambda kv: (-kv[1], kv[0])))
    for col, title in (
            ("wordfreq_zipf", "wordfreq Zipf frequency, rows with a score"),
            ("gb_log10_match",
             "Google Books log10 match count, the 1-gram types"),
            ("orthotactic_logp_per_char",
             "Orthotactic log-probability per character")):
        if col not in F["columns"]:
            continue         # withheld from a public version (D-013)
        hh = F["columns"][col]["hist"]
        labels = [f"{e:.1f}" for e in hh["edges"][:-1]]
        out[f"feature_{col}.png"] = (title, P.bar_chart(
            labels, [("rows", [float(c) for c in hh["counts"]], P.ACCENT)],
            title, col, label_every=5))
    return out


def compute(release_dir: Path, version: str
            ) -> tuple[dict, dict[str, tuple[str, P.Canvas]]]:
    """The profile of the release in `release_dir`, and its plots."""
    import pyarrow.parquet as pq
    files = {}
    # the configs the version ships (a public version adds `sample`)
    for name in (n for n in FILE_ORDER
                 if (release_dir / f"{n}.parquet").exists()):
        path = release_dir / f"{name}.parquet"
        meta = pq.ParquetFile(path).metadata
        files[name] = {"rows": meta.num_rows, "columns": meta.num_columns,
                       "bytes": path.stat().st_size,
                       "sha256": sha256_file(path)}
    U = profile_universe(pq.read_table(release_dir / "universe.parquet"))
    F = profile_features(pq.read_table(release_dir / "features.parquet"))
    plots = charts(U, F)
    profile = {
        "generated_by": "research/release/profile/universe_profile.py",
        "version": version,
        "files": files,
        "configs": {k: v["rows"] for k, v in files.items()},
        "universe": U,
        "features": F,
        "plots": {name: {"title": title, "width": cv.width,
                         "height": cv.height,
                         "pixels_sha256": cv.pixels_sha256()}
                  for name, (title, cv) in sorted(plots.items())},
    }
    return profile, plots


def dumps(profile: dict) -> str:
    return json.dumps(profile, indent=1, sort_keys=True,
                      ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", type=Path, default=HERE,
                    help="write profile.json and plots/ here")
    args = ap.parse_args(argv)
    try:
        spec = B.resolve(args.version)
    except B.ReleaseError as exc:
        print(f"[profile] refused: {exc}", file=sys.stderr)
        return 1
    profile, plots = compute(spec.out_dir, args.version)
    out = args.out
    (out / "plots").mkdir(parents=True, exist_ok=True)
    for name, (_title, cv) in plots.items():
        (out / "plots" / name).write_bytes(cv.png())
    (out / "profile.json").write_text(dumps(profile), encoding="utf-8")
    print(f"[profile] {args.version}: profile.json and {len(plots)} plots "
          f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
