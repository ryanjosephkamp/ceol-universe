"""The model-or-engine column:
the basis rule on entries built here, the column's derivation and its
refusals, and, where data/ holds the layer, the layer against its record."""

from __future__ import annotations

import collections
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from research.provenance import model_basis as M
from research.release import build_release as B

MODEL = {"manual_validation_llm": "a model", "manual_validation_source": "a run"}


def test_the_basis_of_an_entry():
    assert M.basis({"validation_source": "verification_pipeline",
                    "unverified_llm_verdict": "valid", "manual_validation": MODEL}) == M.PIPELINE
    assert M.basis({"unverified_llm_verdict": "invalid", "manual_validation": MODEL}) == M.ALONE
    # a list, a dictionary API, the synthetic engine: no model decided it
    assert M.basis({"source": "twl_scrabble_dictionary"}) is None
    assert M.basis({"source": "free-dictionary", "dictionary_verdict": "valid"}) is None
    assert M.basis({"source": "synthetic_generation", "generation_method": None}) is None
    # a verdict without the block that names a model is not counted
    assert M.basis({"unverified_llm_verdict": "valid"}) is None
    words, counts = M.derive({"a": {"unverified_llm_verdict": "valid", "manual_validation": MODEL},
                              "b": {"source": "twl_scrabble_dictionary"}})
    assert words == {"a": M.ALONE}
    assert counts["by_basis"] == {M.PIPELINE: 0, M.ALONE: 1} and counts["not_model_decided"] == 1


def _universe(rows):
    return pa.table({"word": [r[0] for r in rows],
                     "intake_kind": [r[1] for r in rows],
                     "eol": [r[2] for r in rows]})


def test_the_column_marks_generated_rows_and_joins_the_basis():
    universe = _universe([("a", "obtained", True), ("b", "generated", False),
                          ("c", "obtained", True), ("d", "derived", False)])
    basis = pa.table({"word": ["c"], "model_basis": [M.ALONE]})
    assert B.model_or_engine(universe, basis).to_pylist() == [
        "none", "engine_generated", M.ALONE, "none"]
    # a generated row with a model basis, a basis outside the valid list, or a
    # layer row the universe lacks is refused
    with pytest.raises(B.ReleaseError, match="generated row"):
        B.model_or_engine(universe, pa.table({"word": ["b"], "model_basis": [M.ALONE]}))
    with pytest.raises(B.ReleaseError, match="outside the EOL's valid list"):
        B.model_or_engine(universe, pa.table({"word": ["d"], "model_basis": [M.ALONE]}))
    with pytest.raises(B.ReleaseError, match="matches no row"):
        B.model_or_engine(universe, pa.table({"word": ["z"], "model_basis": [M.ALONE]}))


@pytest.mark.skipif(not M.OUT_PARQUET.exists(), reason="data/ is absent in this environment")
def test_the_layer_is_the_file_its_record_names():
    record = json.loads(M.OUT_JSON.read_text(encoding="utf-8"))
    assert hashlib.sha256(M.OUT_PARQUET.read_bytes()).hexdigest() == record["artifact"]["sha256"]
    layer = pq.read_table(M.OUT_PARQUET)
    assert layer.num_rows == record["artifact"]["rows"]
    assert dict(collections.Counter(layer["model_basis"].to_pylist())) == record["counts"]["by_basis"]
    assert record["counts"]["by_basis"] == {
        M.PIPELINE: record["cross_check"]["pipeline_rows"],
        M.ALONE: record["cross_check"]["rows_with_no_source_and_no_validation_source"]}
