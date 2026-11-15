"""The basis of each row of the EOL's valid list, where a model decided it
(the project plan, item 4).

The EOL's valid dictionary at the pinned revision records, on each entry,
why the EOL lists the string. Its own card and scripts say what the fields
mean (the EOL at 496bf1f, read-only):

- `validation_source: "verification_pipeline"`: the entry passed the EOL's
  Phase 2 verification pipeline, a multi-stage validation that used a
  language model (Google Gemini; the card's Phase 2), and its
  `manual_validation` block names the model;
- `unverified_llm_verdict` with a `manual_validation` block and no
  `validation_source`: the entry rests on a language model's verdict alone
  (the card: "what a single LLM pass ... thought of the word"; the block
  names the model and the revalidation run);
- every other entry rests on a list, a dictionary API, the EOL's domain
  extracts, or its synthetic engine, and a model did not decide it.

At the revision the pin reads (research/universe/repin.py), the
dictionary's entries carry only `word`, `length`, `attested_by`, and, for
the intakes the EOL publishes, `source` and `added_date`: no entry records a
model decision, so the layer is empty and every row of the valid list is
`engine_generated` or `none`.

This module reads that dictionary, the pinned file held to its sha256, and
writes the private layer data/eol_valid_model_basis.parquet (a row per
model-decided entry: the word and its basis) and the committed record
research/provenance/model_basis.json (its sha256 and its counts, and no
string). It cross-checks the counts against the provenance package's
intake extract of the same dictionary. The release build joins the layer
by word and marks every generated row (the provenance layer's
`intake_kind`) as engine-generated.

Run:  python3 -m research.provenance.model_basis
"""

from __future__ import annotations

import collections
import hashlib
import json
import sys
from pathlib import Path

from .extract_eol_intake import REVISION, VALID

REPO = Path(__file__).resolve().parents[2]
OUT_PARQUET = REPO / "data" / "eol_valid_model_basis.parquet"
OUT_JSON = REPO / "research" / "provenance" / "model_basis.json"
INTAKE = REPO / ".cache" / "provenance" / "eol_valid_intake.parquet"
MANIFEST = REPO / "research" / "provenance" / "eol_dictionaries_manifest.json"

PIPELINE = "model_pipeline"
ALONE = "model_alone"
#: the values of the release column, in order (columns.MODEL)
VALUES = ("engine_generated", PIPELINE, ALONE, "none")


def basis(entry: dict) -> str | None:
    """The model basis of a valid-dictionary entry, or None where a model
    did not decide it."""
    manual = entry.get("manual_validation")
    if not isinstance(manual, dict) or not manual.get("manual_validation_llm"):
        return None
    if entry.get("validation_source") == "verification_pipeline":
        return PIPELINE
    if "unverified_llm_verdict" in entry and "validation_source" not in entry:
        return ALONE
    return None


def derive(entries: dict[str, dict]) -> tuple[dict[str, str], dict]:
    """Each model-decided word's basis, and the counts the record states."""
    out: dict[str, str] = {}
    models = collections.Counter()
    for word, entry in entries.items():
        b = basis(entry)
        if b:
            out[word] = b
            models[(b, entry["manual_validation"]["manual_validation_llm"])] += 1
    counts = collections.Counter(out.values())
    return out, {
        "entries": len(entries),
        "by_basis": {PIPELINE: counts[PIPELINE], ALONE: counts[ALONE]},
        "not_model_decided": len(entries) - len(out),
        "model_named_by_basis": {f"{b}: {m}": n for (b, m), n in sorted(models.items())},
    }


def main() -> int:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    data = VALID["local"].read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != VALID["sha256"]:
        raise SystemExit(f"{VALID['name']}: sha256 {sha} is not the pinned file")
    entries = json.loads(data)
    del data
    words, counts = derive(entries)
    del entries

    # the cross-check: the intake extract of the same dictionary, by the
    # committed hash the provenance package records for it
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["dictionaries"]["valid"]
    intake_sha = hashlib.sha256(INTAKE.read_bytes()).hexdigest()
    if intake_sha != manifest["intake_parquet_sha256"]:
        raise SystemExit("the valid intake extract is not the file the manifest records")
    intake = pq.read_table(INTAKE, columns=["word", "validation_source",
                                            "manual_validation_llm"])
    named = pc.is_valid(intake["manual_validation_llm"])
    pipeline = pc.and_(pc.fill_null(pc.equal(intake["validation_source"],
                                             "verification_pipeline"), False), named)
    check = {PIPELINE: int(pc.sum(pipeline).as_py() or 0),
             "named": int(pc.sum(named).as_py() or 0)}
    if check[PIPELINE] != counts["by_basis"][PIPELINE] \
            or check["named"] < sum(counts["by_basis"].values()) \
            or len(intake) != counts["entries"]:
        raise SystemExit(f"the counts {counts['by_basis']} do not agree with the "
                         f"intake extract's {check}")

    table = pa.table({"word": pa.array(sorted(words), pa.string())})
    table = table.append_column("model_basis", pa.array(
        [words[w] for w in table["word"].to_pylist()], pa.string()))
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, OUT_PARQUET, compression="zstd")
    record = {
        "generated_by": "research/provenance/model_basis.py",
        "decision": "the project plan, item 4",
        "input": {"dictionary": VALID["name"], "sha256": VALID["sha256"],
                  "revision": REVISION,
                  "read_as": "the local pinned file (data/eol), "
                             "parsed whole from the bytes that were hashed"},
        "cross_check": {"intake_parquet_sha256": intake_sha,
                        "pipeline_rows": check[PIPELINE],
                        "rows_whose_record_names_a_model": check["named"]},
        "rule": {
            PIPELINE: "validation_source is verification_pipeline, and the "
                      "manual_validation block names a model",
            ALONE: "an unverified_llm_verdict and a manual_validation block "
                   "naming a model, and no validation_source",
        },
        "counts": counts,
        "artifact": {"path": "data/eol_valid_model_basis.parquet",
                     "rows": table.num_rows,
                     "sha256": hashlib.sha256(OUT_PARQUET.read_bytes()).hexdigest()},
    }
    OUT_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"model basis: {table.num_rows:,} rows "
          f"({counts['by_basis'][PIPELINE]:,} pipeline, {counts['by_basis'][ALONE]:,} alone); "
          f"record {OUT_JSON.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
