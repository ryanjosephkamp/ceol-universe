"""The sampler: its rule, determinism, order independence, per-stratum counts,
seed sensitivity, and manifest. Every assertion is on counts, ids, and
hashes; none prints a candidate."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

from ceolkit import RULE, draw, label_text, rank_key, strata
from ceolkit.sample import RANK_COLUMN, STRATUM_COLUMN

SEED = "kit-test-seed"
MANIFEST_KEYS = {"kit", "kit_version", "rule", "seed", "stratum",
                 "stratum_definition", "n", "input_rows", "strata",
                 "short_strata", "selected_rows", "selected_ids_sha256"}


def reference(frame: pd.DataFrame, column: str, n: int, seed: str) -> list[str]:
    """The rule written out plainly, independent of the sampler's code: the
    ids of the sample in order of stratum label, then rank."""
    by_label: dict[str, list[tuple[str, str]]] = {}
    for id_, word, label in zip(frame["id"], frame["word"], frame[column]):
        key = hashlib.sha256(f"{seed}:{label}:{word}".encode("utf-8")).hexdigest()
        by_label.setdefault(label, []).append((key, id_))
    out: list[str] = []
    for label in sorted(by_label):
        out.extend(i for _, i in sorted(by_label[label])[:n])
    return out


def sha_of_ids(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def test_the_sample_follows_the_stated_rule(universe_frame):
    sample, _ = draw(universe_frame, "intake_layer", 40, SEED)
    assert sample["id"].tolist() == reference(universe_frame, "intake_layer", 40, SEED)


def test_rank_key_is_the_hex_digest_of_the_stated_string():
    assert rank_key("s", "a", "b") == hashlib.sha256(b"s:a:b").hexdigest()
    assert rank_key("s", "a", "\u00e9") == hashlib.sha256("s:a:\u00e9".encode("utf-8")).hexdigest()


def test_the_rule_text_names_the_hash_and_the_order():
    assert "sha256" in RULE and "ascending" in RULE and "{seed}:{stratum}:{word}" in RULE


def test_the_same_input_gives_the_same_sample_and_manifest(universe_frame):
    first = draw(universe_frame, strata.evidence_tier, 30, SEED)
    second = draw(universe_frame, strata.evidence_tier, 30, SEED)
    assert first[0]["id"].tolist() == second[0]["id"].tolist()
    assert json.dumps(first[1], sort_keys=True) == json.dumps(second[1], sort_keys=True)


@pytest.mark.parametrize("permutation_seed", [0, 1, 2])
def test_the_sample_does_not_depend_on_the_order_of_the_rows(universe_frame, permutation_seed):
    base, base_manifest = draw(universe_frame, strata.length_band, 25, SEED)
    order = np.random.RandomState(permutation_seed).permutation(len(universe_frame))
    shuffled = universe_frame.iloc[order].reset_index(drop=True)
    again, again_manifest = draw(shuffled, strata.length_band, 25, SEED)
    assert again["id"].tolist() == base["id"].tolist()
    assert again[RANK_COLUMN].tolist() == base[RANK_COLUMN].tolist()
    assert json.dumps(again_manifest, sort_keys=True) == json.dumps(base_manifest, sort_keys=True)


def test_an_arrow_table_and_a_pandas_frame_give_the_same_sample(universe_table):
    from_arrow, arrow_manifest = draw(universe_table, strata.evidence_tier, 20, SEED)
    from_pandas, pandas_manifest = draw(universe_table.to_pandas(), strata.evidence_tier, 20, SEED)
    assert isinstance(from_arrow, pa.Table)
    assert isinstance(from_pandas, pd.DataFrame)
    assert from_arrow["id"].to_pylist() == from_pandas["id"].tolist()
    assert arrow_manifest == pandas_manifest


def test_each_stratum_gives_n_rows(universe_frame, fixtures_manifest):
    layers = fixtures_manifest["sampling"]["strata"]
    sample, manifest = draw(universe_frame, "intake_layer", 50, SEED)
    counts = sample[STRATUM_COLUMN].value_counts().to_dict()
    assert counts == {layer: 50 for layer in layers}
    assert len(sample) == 50 * len(layers) == manifest["selected_rows"]
    assert {k: v["selected"] for k, v in manifest["strata"].items()} == counts
    assert manifest["short_strata"] == []


def test_ranks_run_from_1_within_each_stratum(universe_frame):
    sample, _ = draw(universe_frame, "intake_layer", 12, SEED)
    for _, group in sample.groupby(STRATUM_COLUMN):
        assert group[RANK_COLUMN].tolist() == list(range(1, 13))
    assert sample[STRATUM_COLUMN].is_monotonic_increasing


def test_a_per_stratum_count_samples_only_the_named_strata(universe_frame):
    sample, manifest = draw(universe_frame, "intake_layer",
                            {"eol_valid": 7, "c1_exceptions": 3}, SEED)
    assert sample[STRATUM_COLUMN].value_counts().to_dict() == {"eol_valid": 7, "c1_exceptions": 3}
    assert manifest["n"] == {"eol_valid": 7, "c1_exceptions": 3}
    assert manifest["strata"]["eol_invalid"]["selected"] == 0
    assert manifest["short_strata"] == []


def test_a_label_the_table_does_not_have_is_an_error(universe_frame):
    with pytest.raises(ValueError, match="does not have"):
        draw(universe_frame, "intake_layer", {"no_such_layer": 3}, SEED)


def test_a_short_stratum_gives_all_its_rows_and_the_manifest_says_so(universe_frame, fixtures_manifest):
    per_stratum = fixtures_manifest["sampling"]["rows_per_stratum"]
    sample, manifest = draw(universe_frame, "intake_layer", per_stratum + 1, SEED)
    assert len(sample) == len(universe_frame)
    assert sorted(manifest["short_strata"]) == sorted(fixtures_manifest["sampling"]["strata"])
    for counts in manifest["strata"].values():
        assert counts == {"available": per_stratum, "selected": per_stratum}
    assert manifest["selected_ids_sha256"] == sha_of_ids(universe_frame["id"])


def test_a_smaller_sample_is_the_head_of_a_larger_one(universe_frame):
    small, _ = draw(universe_frame, strata.spelling_class, 10, SEED)
    large, _ = draw(universe_frame, strata.spelling_class, 20, SEED)
    for label, group in small.groupby(STRATUM_COLUMN):
        head = large[large[STRATUM_COLUMN] == label][:len(group)]
        assert group["id"].tolist() == head["id"].tolist()


def test_a_changed_seed_changes_the_sample(universe_frame):
    one, one_manifest = draw(universe_frame, "intake_layer", 100, SEED)
    two, two_manifest = draw(universe_frame, "intake_layer", 100, SEED + "-2")
    assert set(one["id"]) != set(two["id"])
    assert len(set(one["id"]) & set(two["id"])) < len(one) // 2
    assert one_manifest["selected_ids_sha256"] != two_manifest["selected_ids_sha256"]
    assert (one_manifest["seed"], two_manifest["seed"]) == (SEED, SEED + "-2")


def test_the_stratum_label_enters_the_ranking(universe_frame):
    """The same rows labeled differently rank differently."""
    by_layer, _ = draw(universe_frame, "intake_layer", 30, SEED)
    renamed, _ = draw(universe_frame, lambda row: "x-" + row["intake_layer"], 30, SEED)
    assert set(by_layer["id"]) != set(renamed["id"])


def test_a_column_a_stratum_object_and_a_function_agree(universe_frame):
    by_column, _ = draw(universe_frame, "intake_layer", 20, SEED)
    by_stratum, _ = draw(universe_frame, strata.intake_layer, 20, SEED)
    by_function, _ = draw(universe_frame, lambda row: row["intake_layer"], 20, SEED)
    assert by_column["id"].tolist() == by_stratum["id"].tolist() == by_function["id"].tolist()


def test_combined_strata_make_one_stratum_for_each_pair(universe_frame):
    both = strata.combine(strata.model_or_engine, strata.intake_layer)
    sample, manifest = draw(universe_frame, both, 5, SEED)
    expected = (universe_frame["model_or_engine"] + "|" + universe_frame["intake_layer"]).nunique()
    assert len(manifest["strata"]) == expected
    assert set(sample[STRATUM_COLUMN]) == set(manifest["strata"])
    assert manifest["stratum"] == "model_or_engine+intake_layer"


def test_the_manifest_has_the_fields_that_fix_the_sample(universe_frame):
    source = {"version": "v1.0", "config": "universe"}
    sample, manifest = draw(universe_frame, strata.evidence_tier, 15, SEED, source=source)
    assert set(manifest) == MANIFEST_KEYS | {"source"}
    assert manifest["rule"] == RULE
    assert manifest["seed"] == SEED
    assert manifest["stratum"] == "evidence_tier"
    assert manifest["stratum_definition"] == strata.evidence_tier.definition
    assert manifest["n"] == 15
    assert manifest["input_rows"] == len(universe_frame)
    assert manifest["selected_rows"] == len(sample)
    assert manifest["selected_ids_sha256"] == sha_of_ids(sample["id"])
    assert sum(c["available"] for c in manifest["strata"].values()) == len(universe_frame)
    assert manifest["source"] == source
    assert json.loads(json.dumps(manifest)) == manifest


def test_the_manifest_without_a_source_has_no_source_field(universe_frame):
    _, manifest = draw(universe_frame, "intake_layer", 3, SEED)
    assert set(manifest) == MANIFEST_KEYS


def test_the_manifest_holds_no_candidate_string(universe_frame):
    """The words are replaced by markers; a marker in the manifest would be
    a candidate in it."""
    marked = universe_frame.assign(word=[f"qzx{i}qzx" for i in range(len(universe_frame))])
    sample, manifest = draw(marked, "intake_layer", 20, SEED)
    assert "qzx" not in json.dumps(manifest)
    assert sample["word"].str.contains("qzx").all()


def test_the_sampler_prints_nothing(universe_frame, capsys):
    draw(universe_frame, strata.evidence_tier, 10, SEED)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_the_input_is_not_changed(universe_frame, universe_table):
    before = universe_frame.copy()
    draw(universe_frame, strata.evidence_tier, 10, SEED)
    assert universe_frame.equals(before)
    columns_before = universe_table.column_names
    draw(universe_table, strata.evidence_tier, 10, SEED)
    assert universe_table.column_names == columns_before


def test_the_sample_keeps_every_input_column_and_adds_two(universe_frame):
    sample, _ = draw(universe_frame, "intake_layer", 5, SEED)
    assert list(sample.columns) == list(universe_frame.columns) + [STRATUM_COLUMN, RANK_COLUMN]


def test_an_id_is_computed_from_the_word_when_the_table_has_none(universe_frame):
    with_ids, with_manifest = draw(universe_frame, "intake_layer", 25, SEED)
    without = universe_frame.drop(columns=["id"])
    computed, computed_manifest = draw(without, "intake_layer", 25, SEED)
    assert "id" not in computed.columns
    assert computed[STRATUM_COLUMN].tolist() == with_ids[STRATUM_COLUMN].tolist()
    assert computed_manifest["selected_ids_sha256"] == with_manifest["selected_ids_sha256"]


def test_a_stratum_function_sees_null_as_none_or_nan(universe_table):
    seen = {"null": 0, "value": 0}

    def by_scowl(row):
        """whether the SCOWL tier is measured"""
        seen["null" if row["scowl_tier"] != row["scowl_tier"] else "value"] += 1
        return "measured" if row["scowl_tier"] == row["scowl_tier"] else "not measured"

    sample, manifest = draw(universe_table, by_scowl, 5, SEED)
    assert seen["null"] > 0 and seen["value"] > 0
    assert manifest["stratum"] == "by_scowl"
    assert manifest["stratum_definition"] == "whether the SCOWL tier is measured"
    assert sorted(manifest["strata"]) == ["measured", "not measured"]


@pytest.mark.parametrize("value, text", [
    (True, "true"), (False, "false"), (None, "null"), (float("nan"), "null"),
    (1, "1"), (-1, "-1"), (1.0, "1"), (np.int8(0), "0"), (np.float32(2.5), "2.5"),
    ("plain", "plain")])
def test_label_text(value, text):
    assert label_text(value) == text


def test_a_column_with_nulls_makes_a_null_stratum(universe_table):
    sample, manifest = draw(universe_table, "enable1", 4, SEED)
    assert set(manifest["strata"]) == {"-1", "0", "1", "null"}
    assert set(sample[STRATUM_COLUMN].to_pylist()) == {"-1", "0", "1", "null"}


@pytest.mark.parametrize("seed", ["", None, 7])
def test_the_seed_must_be_a_non_empty_string(universe_frame, seed):
    with pytest.raises(ValueError, match="seed"):
        draw(universe_frame, "intake_layer", 5, seed)


@pytest.mark.parametrize("n", [-1, 2.5, True, "5", None])
def test_n_must_be_a_non_negative_integer(universe_frame, n):
    with pytest.raises(ValueError, match="non-negative integer"):
        draw(universe_frame, "intake_layer", n, SEED)


def test_bad_inputs_are_refused(universe_frame):
    with pytest.raises(TypeError, match="pyarrow.Table or a pandas.DataFrame"):
        draw([{"word": "x"}], "word", 1, SEED)
    with pytest.raises(KeyError, match="no column"):
        draw(universe_frame, "no_such_column", 1, SEED)
    with pytest.raises(KeyError, match="no column"):
        draw(universe_frame.drop(columns=["word"]), "intake_layer", 1, SEED)
    with pytest.raises(TypeError, match="column name, a Stratum"):
        draw(universe_frame, 3, 1, SEED)
    with pytest.raises(ValueError, match="already has"):
        draw(universe_frame.assign(sample_rank=1), "intake_layer", 1, SEED)


def test_the_same_id_twice_is_refused(universe_frame):
    doubled = pd.concat([universe_frame.head(3), universe_frame.head(1)], ignore_index=True)
    with pytest.raises(ValueError, match="same id twice"):
        draw(doubled, "intake_layer", 1, SEED)


def test_an_empty_table_gives_an_empty_sample(universe_frame):
    sample, manifest = draw(universe_frame.head(0), strata.evidence_tier, 5, SEED)
    assert len(sample) == 0
    assert manifest["input_rows"] == 0 and manifest["strata"] == {}
    assert manifest["selected_ids_sha256"] == hashlib.sha256(b"").hexdigest()


def test_a_filtered_frame_with_gaps_in_its_index_gives_the_same_sample(universe_frame):
    filtered = universe_frame[universe_frame["intake_layer"] != "c4_additions"]
    assert filtered.index.max() >= len(filtered)  # the index has gaps
    gapped, gapped_manifest = draw(filtered, strata.evidence_tier, 12, SEED)
    reset, reset_manifest = draw(filtered.reset_index(drop=True), strata.evidence_tier, 12, SEED)
    assert gapped["id"].tolist() == reset["id"].tolist()
    assert gapped_manifest == reset_manifest
    assert gapped.index.tolist() == list(range(len(gapped)))


def test_a_stratum_that_needs_a_missing_column_says_how_to_get_it(universe_table):
    with pytest.raises(KeyError, match="join_features"):
        draw(universe_table, strata.frequency_band, 5, SEED)

