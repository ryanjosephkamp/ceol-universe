"""
C4 step 0: the pinned measurement universe (C-009).

data/universe.parquet — 10,001,741 rows: merged v0 (data/merged.parquet,
C2, hash-verified against merge.json) plus the 133,875 pin additions
re-derived word-for-word from the two miss lists —
research/audit/universe_miss_candidates.csv united with the gitignored
.cache/audit/universe_miss_restricted.csv, minus the 7,099 wordfreq-only
rows held at the D-030 corpus boundary. Every row carries `c4_addition`
and `is_restricted`, so downstream artifacts enforce the licence split
mechanically (C-009: words attested only by NWL2023/CSW21 are measured
locally, never committed, pushed, or published).

The build REQUIRES the local restricted split: the pin cannot be
assembled without it, by design. The artifact stays in gitignored data/.

Everything here remains a CANDIDATE inventory (the project's rules): no word is
validated by being pinned.

Run:  python -m research.universe.build_universe
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from ceol.grammar import classes as class_flags
from ceol.grammar import normalize
from ceol.ingest.common import sha256_file

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
UNIVERSE_DIR = REPO / "research" / "universe"
MERGE_JSON = REPO / "research" / "merge" / "merge.json"
AUDIT_JSON = REPO / "research" / "audit" / "audit.json"
SHIPPABLE_CSV = REPO / "research" / "audit" / "universe_miss_candidates.csv"
RESTRICTED_CSV = REPO / ".cache" / "audit" / "universe_miss_restricted.csv"

#: The C-009 pin date — additions carry it as intake_date (deterministic).
C4_PIN_DATE = "2026-08-20"

#: The pins the filter-equivalence proof re-asserts (C2).
PIN_VALID = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
PIN_INVALID = "23701bd85e9be2aad94c10628cb257cb08d1db9494b01b8672e46270a6cd5672"

SCHEMA_COLUMNS = ("word", "eol", "eol_universe", "classes", "sources",
                  "intake_date", "c4_addition", "is_restricted")


def _load_additions() -> list[tuple[str, str, bool]]:
    """(word, sources, is_restricted) for every pin addition, sorted.

    The pin additions are the union of the two miss lists minus the rows
    whose only attesting source is wordfreq (C-009 / D-030).
    """
    if not RESTRICTED_CSV.exists():
        raise RuntimeError(
            f"{RESTRICTED_CSV} is required: the C-009 pin includes the "
            "1,985 restricted words, which exist only in the local split")
    rows: dict[str, tuple[str, bool]] = {}
    for path, restricted in ((SHIPPABLE_CSV, False), (RESTRICTED_CSV, True)):
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                w, sources = row["word"], row["sources"]
                if w in rows:
                    raise RuntimeError(f"duplicate miss-list word {w!r}")
                if set(sources.split(";")) == {"wordfreq"}:
                    continue                     # D-030 corpus boundary
                rows[w] = (sources, restricted)
    for w in rows:
        if normalize(w) != w:
            raise RuntimeError(f"addition {w!r} is not grammar-canonical")
        if class_flags(w):
            raise RuntimeError(f"addition {w!r} is not plain a-z")
    return sorted((w, s, r) for w, (s, r) in rows.items())


def build() -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    merge = json.loads(MERGE_JSON.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))["doc_figures"]

    merged_path = DATA_DIR / "merged.parquet"
    got = sha256_file(merged_path)
    want = merge["artifacts"]["merged_parquet_sha256"]
    if got != want:
        raise RuntimeError(f"merged.parquet sha256 {got} != merge.json {want}")

    additions = _load_additions()
    expected_additions = (audit["eol_frame_additions"]
                          + audit["beyond_frame_other"])
    if len(additions) != expected_additions:
        raise RuntimeError(f"additions {len(additions):,} != "
                           f"{expected_additions:,} from audit.json")
    n_restricted = sum(1 for _, _, r in additions if r)
    if n_restricted != audit["miss_restricted"]:
        raise RuntimeError(f"restricted {n_restricted:,} != "
                           f"{audit['miss_restricted']:,} from audit.json")

    merged = pq.read_table(merged_path)
    n_merged = merged.num_rows
    merged = merged.append_column(
        "c4_addition", pa.array([False] * n_merged, pa.bool_()))
    merged = merged.append_column(
        "is_restricted", pa.array([False] * n_merged, pa.bool_()))

    add_table = pa.table({
        "word": [w for w, _, _ in additions],
        "eol": [False] * len(additions),
        "eol_universe": [False] * len(additions),
        "classes": [""] * len(additions),
        "sources": [s for _, s, _ in additions],
        "intake_date": [C4_PIN_DATE] * len(additions),
        "c4_addition": [True] * len(additions),
        "is_restricted": [r for _, _, r in additions],
    }, schema=merged.schema)

    combined = pa.concat_tables([merged, add_table])
    combined = combined.take(
        pc.sort_indices(combined, sort_keys=[("word", "ascending")]))

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "universe.parquet"
    pq.write_table(combined, out_path, compression="zstd")

    # ---- proofs, from the SHIPPED artifact --------------------------------
    shipped = pq.read_table(out_path)
    counts = {"valid": 0, "invalid": 0, "exceptions": 0, "additions": 0,
              "restricted": 0}
    h_valid, h_invalid = hashlib.sha256(), hashlib.sha256()
    canonical = hashlib.sha256()
    prev = None
    for batch in shipped.to_batches():
        cols = [batch.column(i).to_pylist()
                for i in range(len(SCHEMA_COLUMNS))]
        for row in zip(*cols):
            w, eol, uni, _, _, _, c4, restr = row
            if prev is not None and w <= prev:
                raise RuntimeError(f"order/duplicate violation at {w!r}")
            prev = w
            canonical.update(
                ("\t".join(str(x) for x in row) + "\n").encode("utf-8"))
            if eol:
                counts["valid"] += 1
                h_valid.update(w.encode("utf-8") + b"\n")
            elif uni:
                counts["invalid"] += 1
                h_invalid.update(w.encode("utf-8") + b"\n")
            elif c4:
                counts["additions"] += 1
            else:
                counts["exceptions"] += 1
            if restr:
                counts["restricted"] += 1

    proof = {
        "regenerated_valid_sha256": h_valid.hexdigest(),
        "regenerated_invalid_sha256": h_invalid.hexdigest(),
        "valid_matches_pin": h_valid.hexdigest() == PIN_VALID,
        "invalid_matches_pin": h_invalid.hexdigest() == PIN_INVALID,
    }
    if not (proof["valid_matches_pin"] and proof["invalid_matches_pin"]):
        raise RuntimeError(f"FILTER-EQUIVALENCE FAILED over universe: {proof}")
    if counts["restricted"] != audit["miss_restricted"]:
        raise RuntimeError("restricted flag count drifted in shipped artifact")
    if shipped.num_rows != audit["c4_recommended_pin"]:
        raise RuntimeError(f"universe rows {shipped.num_rows:,} != "
                           f"C-009 pin {audit['c4_recommended_pin']:,}")

    universe = {
        "generated_by": "research/universe/build_universe.py",
        "pin_decision": "C-009",
        "counts": {
            "universe_rows": shipped.num_rows,
            "merged_rows": n_merged,
            "c4_additions": counts["additions"],
            "restricted_rows": counts["restricted"],
            "eol_valid": counts["valid"],
            "eol_invalid": counts["invalid"],
            "exceptions": counts["exceptions"],
        },
        "filter_equivalence": proof,
        "artifacts": {
            "universe_parquet_sha256": sha256_file(out_path),
            "canonical_content_sha256": canonical.hexdigest(),
            "merged_parquet_sha256": want,
        },
    }
    universe["doc_figures"] = {
        "universe_rows": shipped.num_rows,
        "merged_rows": n_merged,
        "c4_additions": counts["additions"],
        "restricted_rows": counts["restricted"],
        "exceptions": counts["exceptions"],
    }
    (UNIVERSE_DIR / "universe.json").write_text(
        json.dumps(universe, indent=2) + "\n", encoding="utf-8")
    return universe


def main() -> int:
    u = build()
    c = u["counts"]
    print(f"[universe] {c['universe_rows']:,} rows = {c['merged_rows']:,} "
          f"merged + {c['c4_additions']:,} additions "
          f"({c['restricted_rows']:,} restricted, local-only)")
    print(f"[universe] filter-equivalence re-asserted: valid "
          f"{u['filter_equivalence']['valid_matches_pin']}, invalid "
          f"{u['filter_equivalence']['invalid_matches_pin']}")
    print(f"[universe] sha256 {u['artifacts']['universe_parquet_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
