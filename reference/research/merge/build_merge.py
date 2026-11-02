"""
C2: the merged CEOL v0 and the byte-exact filter-equivalence proof.

Builds the two dataset configs (C-002):

  data/exceptions.parquet — the census's 213,867 candidates, with classes
      and per-word source containment (C-008).
  data/merged.parquet — the EOL universe at pinned revision c1139698 plus
      the exceptions, every entry carrying eol / eol_universe / classes /
      sources / intake_date.

The proof: filtering the SHIPPED merged artifact must regenerate both
pinned EOL files byte-for-byte — sha256 equality against the manifest
pins, which simultaneously accounts for both directions (no missing word,
no extra word, no duplicate). The same proof lives permanently in
tests/test_equivalence.py.

Everything here remains a CANDIDATE inventory (the project's rules): `eol` records
the pinned EOL split as historical fact, not a CEOL verdict.

Run:  python -m research.merge.build_merge
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from ceol.grammar import classes as class_flags
from ceol.ingest.common import EOL_REPO, sha256_file

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
MERGE_DIR = REPO / "research" / "merge"
CANDIDATES_CSV = REPO / "research" / "census" / "candidates.csv"

#: The pin (EOL sources/MANIFEST.toml, revision c1139698…).
EOL_REVISION = "c113969807f3045f5ddd8cc919d0189d54ba368b"
PIN_VALID = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
PIN_INVALID = "23701bd85e9be2aad94c10628cb257cb08d1db9494b01b8672e46270a6cd5672"
EOL_VALID_TXT = EOL_REPO / ".cache" / "hf" / "merged_valid_words.txt"
EOL_INVALID_TXT = EOL_REPO / ".cache" / "hf" / "merged_invalid_words.txt"

#: Provenance labels (C-008). EOL-universe words carry dataset-level
#: provenance — their per-source attestation is C4's job to measure.
EOL_PROVENANCE = f"eol_universe@{EOL_REVISION[:8]}"
EOL_PIN_DATE = "2026-08-17"          # the pinned revision's publish date
CENSUS_INTAKE_DATE = "2026-08-20"    # the C1 census date

SCHEMA_COLUMNS = ("word", "eol", "eol_universe", "classes", "sources",
                  "intake_date")


def _read_pinned(path: Path, pin: str) -> list[str]:
    got = sha256_file(path)
    if got != pin:
        raise RuntimeError(f"{path.name}: sha256 {got} != pin {pin}")
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def _sha256_lines(words: list[str]) -> str:
    h = hashlib.sha256()
    for w in words:
        h.update(w.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def build() -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    valid = _read_pinned(EOL_VALID_TXT, PIN_VALID)
    invalid = _read_pinned(EOL_INVALID_TXT, PIN_INVALID)
    valid_set = set(valid)
    universe = valid_set | set(invalid)
    if len(universe) != len(valid) + len(invalid):
        raise RuntimeError("valid and invalid lists overlap — not the pin")

    exceptions: list[tuple[str, str, str]] = []
    with open(CANDIDATES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            exceptions.append((row["word"], row["classes"], row["sources"]))
    exc_words = {w for w, _, _ in exceptions}
    if len(exc_words) != len(exceptions):
        raise RuntimeError("duplicate words in candidates.csv")
    overlap = exc_words & universe
    if overlap:
        raise RuntimeError(f"exceptions overlap the EOL universe: "
                           f"{sorted(overlap)[:5]} …")
    for w, flags, _ in exceptions:
        if ";".join(sorted(class_flags(w))) != flags:
            raise RuntimeError(f"class flags for {w!r} do not re-derive")

    rows = [(w, True, True, "", EOL_PROVENANCE, EOL_PIN_DATE)
            for w in valid]
    rows += [(w, False, True, "", EOL_PROVENANCE, EOL_PIN_DATE)
             for w in invalid]
    rows += [(w, False, False, c, s, CENSUS_INTAKE_DATE)
             for w, c, s in exceptions]
    rows.sort(key=lambda r: r[0])

    DATA_DIR.mkdir(exist_ok=True)
    table = pa.table(
        {col: [r[i] for r in rows] for i, col in enumerate(SCHEMA_COLUMNS)},
        schema=pa.schema([("word", pa.string()), ("eol", pa.bool_()),
                          ("eol_universe", pa.bool_()),
                          ("classes", pa.string()), ("sources", pa.string()),
                          ("intake_date", pa.string())]))
    pq.write_table(table, DATA_DIR / "merged.parquet", compression="zstd")

    exc_rows = sorted(exceptions)
    exc_table = pa.table({
        "word": [r[0] for r in exc_rows],
        "classes": [r[1] for r in exc_rows],
        "sources": [r[2] for r in exc_rows],
        "intake_date": [CENSUS_INTAKE_DATE] * len(exc_rows)})
    pq.write_table(exc_table, DATA_DIR / "exceptions.parquet",
                   compression="zstd")

    # ---- the proof, from the SHIPPED artifact -----------------------------
    shipped = pq.read_table(DATA_DIR / "merged.parquet")
    words = shipped.column("word").to_pylist()
    eol = shipped.column("eol").to_pylist()
    eol_universe = shipped.column("eol_universe").to_pylist()

    regen_valid = sorted(w for w, e in zip(words, eol) if e)
    regen_invalid = sorted(w for w, e, u in zip(words, eol, eol_universe)
                           if u and not e)
    proof = {
        "regenerated_valid_sha256": _sha256_lines(regen_valid),
        "regenerated_invalid_sha256": _sha256_lines(regen_invalid),
        "pin_valid": PIN_VALID, "pin_invalid": PIN_INVALID,
        "valid_matches_pin": _sha256_lines(regen_valid) == PIN_VALID,
        "invalid_matches_pin": _sha256_lines(regen_invalid) == PIN_INVALID,
    }
    if not (proof["valid_matches_pin"] and proof["invalid_matches_pin"]):
        raise RuntimeError(f"FILTER-EQUIVALENCE FAILED: {proof}")

    canonical = hashlib.sha256()
    for r in rows:
        canonical.update(("\t".join(str(x) for x in r) + "\n").encode())

    merge = {
        "generated_by": "research/merge/build_merge.py",
        "eol_revision": EOL_REVISION,
        "counts": {
            "merged_total": len(rows),
            "eol_universe": len(valid) + len(invalid),
            "eol_valid": len(valid),
            "eol_invalid": len(invalid),
            "exceptions": len(exceptions),
            "overlap": 0,
        },
        "filter_equivalence": proof,
        "artifacts": {
            "merged_parquet_sha256": sha256_file(DATA_DIR / "merged.parquet"),
            "exceptions_parquet_sha256":
                sha256_file(DATA_DIR / "exceptions.parquet"),
            "canonical_content_sha256": canonical.hexdigest(),
        },
    }
    merge["doc_figures"] = {
        "merged_total": merge["counts"]["merged_total"],
        "eol_universe": merge["counts"]["eol_universe"],
        "eol_valid": merge["counts"]["eol_valid"],
        "eol_invalid": merge["counts"]["eol_invalid"],
        "exceptions": merge["counts"]["exceptions"],
    }
    MERGE_DIR.mkdir(exist_ok=True)
    (MERGE_DIR / "merge.json").write_text(
        json.dumps(merge, indent=2) + "\n", encoding="utf-8")
    return merge


def main() -> int:
    merge = build()
    print(f"[merge] merged {merge['counts']['merged_total']:,} rows "
          f"({merge['counts']['eol_universe']:,} EOL universe + "
          f"{merge['counts']['exceptions']:,} exceptions)")
    print(f"[merge] filter-equivalence: valid "
          f"{merge['filter_equivalence']['valid_matches_pin']}, invalid "
          f"{merge['filter_equivalence']['invalid_matches_pin']} — "
          "both byte-exact against the pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
