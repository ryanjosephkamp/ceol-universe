"""
S5a: universe v2 — the C-009 universe plus the C-015 spaced candidates.

data/universe_v2.parquet — 10,296,606 rows: the pinned v1 universe
(data/universe.parquet, 10,001,741 rows, hash-verified against
universe.json) plus the 294,865 spaced candidates the owner admitted at
the S4 gate (full measured union, no filter at intake). Every spaced row
carries:

  - the v1 columns unchanged in meaning: eol=False, eol_universe=False
    (no spaced candidate is an EOL string), classes (the census flags,
    re-derived from ceol.grammar and cross-checked against the census
    records), sources (C-008 per-candidate provenance: "wordnet",
    "wiktionary_english", or both, semicolon-joined sorted),
    intake_date, c4_addition=False, is_restricted=False (the census
    measured zero space-bearing game-list entries);
  - token_count (ceol.grammar.token_count; 1 for every v1 row);
  - c015_addition=True (False for every v1 row);
  - the properness signal columns, nullable and null where the signal's
    source did not attest the row (never False-for-unmeasured):
    wn_instance, wn_capitalized (WordNet instance-synset membership and
    data-file capitalization), wk_proper_noun (Wiktionary Proper-noun
    heading);
  - wk_flags: the J3 category flags for Wiktionary-attested spaced rows
    (semicolon-joined sorted subset of idiomatic / phrasal-verb /
    phrasebook / proverb, by the census's declared mechanical rules;
    empty string when none apply; null for rows Wiktionary does not
    attest).

The build verifies, from the SHIPPED artifact, streaming:

  - strict ascending order, no duplicates;
  - the eol==true and eol_universe subsets byte-exact against the EOL
    manifest pins (filter-equivalence proof a);
  - the no-space projection (token_count == 1, the eight v1 columns)
    canonically serialized to sha256 equal to universe v1's
    canonical_content_sha256 (filter-equivalence proof b — the v1
    universe is reproduced byte-exact, columns and all);
  - every count against space_census.json's enforcer-checked figures.

Everything here remains a CANDIDATE inventory: no word is
validated by being pinned. The artifact contains the 1,985 restricted
rows and stays in gitignored data/, like its predecessor.

Run:  python -m research.universe_v2.build_universe_v2
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from ceol.grammar import SPACE, classes as class_flags, normalize, token_count
from ceol.ingest.common import sha256_file
from research import archival

#: the declared particle set of the census, read from the archival module
PHRASAL_PARTICLES = archival.load(
    "research/space_census/analyze_space_census.py").PHRASAL_PARTICLES

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
OUT_DIR = REPO / "research" / "universe_v2"
V1_PARQUET = DATA_DIR / "universe.parquet"
V1_JSON = archival.REFERENCE / "research" / "universe" / "universe.json"
CENSUS_JSON = (archival.REFERENCE / "research" / "space_census"
               / "space_census.json")
WN_JSONL = REPO / ".cache" / "space_census" / "wordnet_spaced.jsonl"
WK_JSONL = REPO / ".cache" / "space_census" / "wiktionary_spaced.jsonl"

#: The v2 pin date — the S4 ruling date; spaced additions carry it as
#: intake_date (deterministic).
C015_PIN_DATE = "2026-08-26"

#: The pins the filter-equivalence proof re-asserts (C2 lineage).
PIN_VALID = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
PIN_INVALID = "23701bd85e9be2aad94c10628cb257cb08d1db9494b01b8672e46270a6cd5672"

#: v1's schema, in v1's order — the projection serializes exactly these.
V1_COLUMNS = ("word", "eol", "eol_universe", "classes", "sources",
              "intake_date", "c4_addition", "is_restricted")

#: v2 = v1's columns plus the C-015 columns, in this order.
V2_COLUMNS = V1_COLUMNS + ("token_count", "c015_addition", "wn_instance",
                           "wn_capitalized", "wk_proper_noun", "wk_flags")


def _wk_flag_string(rec: dict) -> str:
    """The J3 category flags, by the census's declared mechanical rules
    (research/space_census/analyze_space_census.py)."""
    flags = []
    if rec.get("idiomatic", False):
        flags.append("idiomatic")
    if "Verb" in rec["pos"] and rec["key"].split(SPACE)[-1] in PHRASAL_PARTICLES:
        flags.append("phrasal-verb")
    if rec.get("phrasebook", False):
        flags.append("phrasebook")
    if "Proverb" in rec["pos"] or "English proverbs" in rec["cats"]:
        flags.append("proverb")
    return ";".join(flags)      # already sorted by construction


def _load_spaced() -> tuple[list[dict], dict]:
    """The admitted spaced candidates, one merged record per key, sorted.

    Re-derives classes and token_count from ceol.grammar and cross-checks
    both against the census records; any disagreement is a build failure,
    never a silent preference.
    """
    wn: dict[str, dict] = {}
    with open(WN_JSONL, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            wn[r["key"]] = r
    wk: dict[str, dict] = {}
    with open(WK_JSONL, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            wk[r["key"]] = r

    rows = []
    for key in sorted(set(wn) | set(wk)):
        if normalize(key) != key:
            raise RuntimeError(f"spaced candidate {key!r} not canonical")
        flags = class_flags(key)
        if "spaced" not in flags or SPACE not in key:
            raise RuntimeError(f"spaced candidate {key!r} carries no space")
        tc = token_count(key)
        for rec in (wn.get(key), wk.get(key)):
            if rec is None:
                continue
            if sorted(rec["classes"]) != sorted(flags):
                raise RuntimeError(f"class drift at {key!r}: census "
                                   f"{rec['classes']} vs grammar {flags}")
            if rec["token_count"] != tc:
                raise RuntimeError(f"token_count drift at {key!r}")
        w, k = wn.get(key), wk.get(key)
        sources = ";".join(sorted(
            (["wordnet"] if w else []) + (["wiktionary_english"] if k else [])))
        rows.append({
            "word": key,
            "eol": False,
            "eol_universe": False,
            "classes": ";".join(sorted(flags)),
            "sources": sources,
            "intake_date": C015_PIN_DATE,
            "c4_addition": False,
            "is_restricted": False,
            "token_count": tc,
            "c015_addition": True,
            "wn_instance": w["instance"] if w else None,
            "wn_capitalized": w["capitalized"] if w else None,
            "wk_proper_noun": ("Proper noun" in k["pos"]) if k else None,
            "wk_flags": _wk_flag_string(k) if k else None,
        })
    counts = {
        "wn_only": sum(1 for k in wn if k not in wk),
        "wk_only": sum(1 for k in wk if k not in wn),
        "both": sum(1 for k in wn if k in wk),
    }
    return rows, counts


def build() -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    v1_meta = json.loads(V1_JSON.read_text(encoding="utf-8"))
    got = sha256_file(V1_PARQUET)
    want = v1_meta["artifacts"]["universe_parquet_sha256"]
    if got != want:
        raise RuntimeError(f"universe.parquet sha256 {got} != {want}")
    v1_canonical = v1_meta["artifacts"]["canonical_content_sha256"]
    census = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))["doc_figures"]

    spaced, src_counts = _load_spaced()
    checks = (
        (len(spaced), census["union_total"], "union"),
        (src_counts["wn_only"], census["wn_only"], "wn_only"),
        (src_counts["wk_only"], census["wk_only"], "wk_only"),
        (src_counts["both"], census["overlap_both"], "overlap"),
    )
    for got_n, want_n, label in checks:
        if got_n != want_n:
            raise RuntimeError(f"{label}: {got_n:,} != census {want_n:,}")

    v1 = pq.read_table(V1_PARQUET)
    n_v1 = v1.num_rows
    if n_v1 != v1_meta["counts"]["universe_rows"]:
        raise RuntimeError("v1 row count drifted")
    v1 = v1.append_column("token_count",
                          pa.array([1] * n_v1, pa.int32()))
    v1 = v1.append_column("c015_addition",
                          pa.array([False] * n_v1, pa.bool_()))
    for col in ("wn_instance", "wn_capitalized", "wk_proper_noun"):
        v1 = v1.append_column(col, pa.array([None] * n_v1, pa.bool_()))
    v1 = v1.append_column("wk_flags",
                          pa.array([None] * n_v1, pa.string()))

    add = pa.table(
        {c: [r[c] for r in spaced] for c in V2_COLUMNS},
        schema=pa.schema([v1.schema.field(c) for c in V2_COLUMNS]))
    combined = pa.concat_tables([v1, add])
    combined = combined.take(
        pc.sort_indices(combined, sort_keys=[("word", "ascending")]))

    out_path = DATA_DIR / "universe_v2.parquet"
    pq.write_table(combined, out_path, compression="zstd")

    # ---- proofs, from the SHIPPED artifact --------------------------------
    shipped_file = pq.ParquetFile(out_path)
    counts = {"valid": 0, "invalid": 0, "spaced": 0, "restricted": 0,
              "wn_only": 0, "wk_only": 0, "both": 0, "rows": 0}
    h_valid, h_invalid = hashlib.sha256(), hashlib.sha256()
    canonical_v2 = hashlib.sha256()
    projection = hashlib.sha256()
    prev = None
    n_v1_cols = len(V1_COLUMNS)
    for batch in shipped_file.iter_batches(batch_size=1 << 16):
        cols = [batch.column(i).to_pylist() for i in range(len(V2_COLUMNS))]
        for row in zip(*cols):
            w, eol, uni, _, sources, _, _, restr = row[:n_v1_cols]
            tc, c015 = row[n_v1_cols], row[n_v1_cols + 1]
            if prev is not None and w <= prev:
                raise RuntimeError(f"order/duplicate violation at {w!r}")
            prev = w
            counts["rows"] += 1
            canonical_v2.update(
                ("\t".join(str(x) for x in row) + "\n").encode("utf-8"))
            if tc == 1:
                if c015 or SPACE in w:
                    raise RuntimeError(f"projection violation at {w!r}")
                projection.update(
                    ("\t".join(str(x) for x in row[:n_v1_cols]) + "\n")
                    .encode("utf-8"))
            else:
                if not c015 or SPACE not in w:
                    raise RuntimeError(f"spaced-flag violation at {w!r}")
                if eol or uni or restr:
                    raise RuntimeError(f"spaced row {w!r} claims EOL or "
                                       "restricted status")
                counts["spaced"] += 1
                srcs = set(sources.split(";"))
                if srcs == {"wordnet"}:
                    counts["wn_only"] += 1
                elif srcs == {"wiktionary_english"}:
                    counts["wk_only"] += 1
                elif srcs == {"wordnet", "wiktionary_english"}:
                    counts["both"] += 1
                else:
                    raise RuntimeError(f"unknown provenance {sources!r}")
            if eol:
                counts["valid"] += 1
                h_valid.update(w.encode("utf-8") + b"\n")
            elif uni:
                counts["invalid"] += 1
                h_invalid.update(w.encode("utf-8") + b"\n")
            if restr:
                counts["restricted"] += 1

    proof = {
        "regenerated_valid_sha256": h_valid.hexdigest(),
        "regenerated_invalid_sha256": h_invalid.hexdigest(),
        "valid_matches_pin": h_valid.hexdigest() == PIN_VALID,
        "invalid_matches_pin": h_invalid.hexdigest() == PIN_INVALID,
        "no_space_projection_sha256": projection.hexdigest(),
        "projection_matches_v1_canonical":
            projection.hexdigest() == v1_canonical,
        "v1_canonical_content_sha256": v1_canonical,
    }
    if not (proof["valid_matches_pin"] and proof["invalid_matches_pin"]):
        raise RuntimeError(f"FILTER-EQUIVALENCE (a) FAILED: {proof}")
    if not proof["projection_matches_v1_canonical"]:
        raise RuntimeError(f"FILTER-EQUIVALENCE (b) FAILED: {proof}")
    expected = {
        "rows": v1_meta["counts"]["universe_rows"] + census["union_total"],
        "spaced": census["union_total"],
        "wn_only": census["wn_only"],
        "wk_only": census["wk_only"],
        "both": census["overlap_both"],
        "restricted": v1_meta["counts"]["restricted_rows"],
    }
    for key, want_n in expected.items():
        if counts[key] != want_n:
            raise RuntimeError(f"shipped {key} {counts[key]:,} != "
                               f"{want_n:,}")

    meta = {
        "generated_by": "research/universe_v2/build_universe_v2.py",
        "pin_decision": "C-016",
        "supersedes": "C-009",
        "counts": {
            "v2_rows": counts["rows"],
            "v1_rows": n_v1,
            "spaced_additions": counts["spaced"],
            "wn_only": counts["wn_only"],
            "wk_only": counts["wk_only"],
            "both_sources": counts["both"],
            "restricted_rows": counts["restricted"],
            "eol_valid": counts["valid"],
            "eol_invalid": counts["invalid"],
        },
        "filter_equivalence": proof,
        "artifacts": {
            "universe_v2_parquet_sha256": sha256_file(out_path),
            "canonical_content_sha256_v2": canonical_v2.hexdigest(),
            "v1_parquet_sha256": want,
        },
        "schema_columns": list(V2_COLUMNS),
        "intake_date_spaced": C015_PIN_DATE,
    }
    meta["doc_figures"] = {
        "v2_rows": counts["rows"],
        "v1_rows": n_v1,
        "spaced_additions": counts["spaced"],
        "wn_only": counts["wn_only"],
        "wk_only": counts["wk_only"],
        "both_sources": counts["both"],
        "restricted_rows": counts["restricted"],
    }
    (OUT_DIR / "universe_v2.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    m = build()
    c = m["counts"]
    print(f"[universe_v2] {c['v2_rows']:,} rows = {c['v1_rows']:,} v1 + "
          f"{c['spaced_additions']:,} spaced "
          f"(wn-only {c['wn_only']:,} · wk-only {c['wk_only']:,} · "
          f"both {c['both_sources']:,})")
    fe = m["filter_equivalence"]
    print(f"[universe_v2] proof a (EOL pins): valid "
          f"{fe['valid_matches_pin']}, invalid {fe['invalid_matches_pin']}")
    print(f"[universe_v2] proof b (no-space projection == v1 canonical): "
          f"{fe['projection_matches_v1_canonical']}")
    print(f"[universe_v2] sha256 {m['artifacts']['universe_v2_parquet_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
