"""The ready strata: each one's definition on rows, its handling of -1
("cannot hold") and null ("not measured"), and its agreement with the
fixtures' own columns. Synthetic rows use strings of 'x' only; no test
prints a candidate."""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd
import pytest

from ceolkit import join_features, strata
from ceolkit.strata import (FAMILIES, STRATA, family_cell, family_cells,
                            is_null)

NAN = float("nan")

#: a single-token row that no family lists and no corpus holds
BASE = {"token_count": 1, "wordnet": 0, "wiktionary_english": 0,
        "hunspell_en_US": 0, "hunspell_en_GB": 0, "hunspell_en_CA": 0,
        "hunspell_en_AU": 0, "enable1": 0, "scowl_tier": 0,
        "gb_type": False, "wordfreq_scored": False}


def row(**changes) -> dict:
    return {**BASE, **changes}


def tier(**changes) -> str:
    return strata.evidence_tier(row(**changes))


@pytest.fixture()
def with_features(universe_table, features_table):
    return join_features(universe_table, features_table, ["wordfreq_zipf"])


# ---- the registry --------------------------------------------------------

def test_every_ready_stratum_states_its_definition_and_columns(universe_table, features_table):
    assert set(STRATA) == {"evidence_tier", "spelling_class", "length_band",
                           "frequency_band", "intake_layer", "model_or_engine"}
    known = set(universe_table.column_names) | set(features_table.column_names)
    for name, stratum in STRATA.items():
        assert stratum.name == name
        assert len(stratum.definition) > 40 and stratum.labels
        assert set(stratum.columns) <= known


def test_each_stratum_labels_the_fixtures_within_its_labels(with_features):
    for name, stratum in STRATA.items():
        labels = stratum.label_frame(with_features)
        assert len(labels) == len(with_features)
        assert set(labels) <= set(stratum.labels), name


def test_the_frame_form_of_each_stratum_equals_its_row_form(with_features):
    rows = with_features.to_dict("records")
    for name, stratum in STRATA.items():
        by_row = [stratum.label_of(r) for r in rows]
        assert stratum.label_frame(with_features).tolist() == by_row, name


def test_a_missing_column_is_named(universe_table):
    with pytest.raises(KeyError, match="join_features"):
        strata.frequency_band.label_frame(universe_table.to_pandas())
    with pytest.raises(KeyError, match="class_explicit"):
        strata.spelling_class.label_frame(universe_table.to_pandas().drop(columns=["class_explicit"]))


# ---- the evidence tier ---------------------------------------------------

def test_the_five_families_are_the_published_lists():
    assert list(FAMILIES) == ["wordnet", "wiktionary_english", "hunspell", "enable1", "scowl"]
    assert FAMILIES["hunspell"] == ("hunspell_en_US", "hunspell_en_GB",
                                    "hunspell_en_CA", "hunspell_en_AU")


def test_a_row_no_family_lists_is_none_by_its_corpora():
    assert tier() == "none_no_corpus"
    assert tier(gb_type=True) == "none_with_corpus"
    assert tier(wordfreq_scored=True) == "none_with_corpus"
    assert tier(gb_type=True, wordfreq_scored=True) == "none_with_corpus"


def test_the_four_hunspell_columns_are_one_family():
    assert tier(hunspell_en_US=1) == "listed_by_1"
    assert tier(hunspell_en_US=1, hunspell_en_GB=1, hunspell_en_CA=1, hunspell_en_AU=1) == "listed_by_1"
    assert tier(hunspell_en_GB=1, wordnet=1) == "listed_by_2_or_more"


def test_scowl_is_a_family_when_its_tier_is_above_zero():
    assert tier(scowl_tier=10) == "listed_by_1"
    assert tier(scowl_tier=95, enable1=1) == "listed_by_2_or_more"
    assert tier(scowl_tier=0) == "none_no_corpus"
    assert tier(scowl_tier=40, hunspell_en_US=1) == "listed_by_2_or_more"


def test_the_other_families_each_count_once():
    assert tier(wordnet=1) == "listed_by_1"
    assert tier(wiktionary_english=1) == "listed_by_1"
    assert tier(enable1=1) == "listed_by_1"
    assert tier(wordnet=1, wiktionary_english=1, enable1=1) == "listed_by_2_or_more"


def test_a_cell_of_minus_1_is_not_a_listing_and_not_a_no():
    cannot = dict(wordnet=-1, hunspell_en_US=-1, hunspell_en_GB=-1,
                  hunspell_en_CA=-1, hunspell_en_AU=-1, enable1=-1, scowl_tier=-1)
    assert family_cells(row(**cannot)) == {
        "wordnet": -1, "wiktionary_english": 0, "hunspell": -1, "enable1": -1, "scowl": -1}
    assert tier(**cannot) == "none_no_corpus"
    assert tier(**cannot, wiktionary_english=1) == "listed_by_1"
    assert tier(**cannot, gb_type=True) == "none_with_corpus"
    # when no family can hold the row, no family said no
    assert tier(**cannot, wiktionary_english=-1) == "no_family_can_hold"
    # -1 beside a listing does not hide the listing
    assert tier(wordnet=-1, enable1=-1, hunspell_en_US=1, scowl_tier=-1) == "listed_by_1"
    assert tier(wordnet=-1, hunspell_en_US=1, wiktionary_english=1) == "listed_by_2_or_more"


def test_a_family_cell_keeps_minus_1_zero_and_null_apart():
    assert family_cell(row(hunspell_en_US=-1, hunspell_en_GB=-1, hunspell_en_CA=-1,
                           hunspell_en_AU=-1), "hunspell") == -1
    assert family_cell(row(hunspell_en_US=-1, hunspell_en_GB=0, hunspell_en_CA=-1,
                           hunspell_en_AU=-1), "hunspell") == 0
    assert family_cell(row(hunspell_en_US=-1, hunspell_en_GB=NAN, hunspell_en_CA=-1,
                           hunspell_en_AU=-1), "hunspell") is None
    assert family_cell(row(hunspell_en_US=NAN, hunspell_en_GB=1), "hunspell") == 1
    assert family_cell(row(scowl_tier=-1), "scowl") == -1
    assert family_cell(row(scowl_tier=0), "scowl") == 0
    assert family_cell(row(scowl_tier=NAN), "scowl") is None


@pytest.mark.parametrize("null", [None, NAN, pd.NA])
def test_a_null_cell_is_not_measured_and_never_not_listed(null):
    assert tier(wordnet=null) == "not_measured"
    assert tier(hunspell_en_GB=null) == "not_measured"
    assert tier(scowl_tier=null) == "not_measured"
    assert tier(wordnet=null, wiktionary_english=1) == "not_measured"
    # 2 listings decide the tier whatever else is unmeasured
    assert tier(wordnet=null, wiktionary_english=1, enable1=1) == "listed_by_2_or_more"
    assert tier(gb_type=null, wordfreq_scored=null) == "not_measured"
    assert tier(gb_type=null, wordfreq_scored=False) == "not_measured"
    assert tier(gb_type=null, wordfreq_scored=True) == "none_with_corpus"
    assert tier(gb_type=True, wordfreq_scored=null) == "none_with_corpus"


def test_a_row_of_more_than_one_token_is_outside_the_tiers():
    spaced = {k: NAN for k in BASE if k not in ("token_count", "gb_type", "wordfreq_scored")}
    assert strata.evidence_tier({**spaced, "token_count": 2, "gb_type": None,
                                 "wordfreq_scored": None}) == "not_single_token"


def test_an_evidence_value_outside_the_card_is_refused():
    with pytest.raises(ValueError, match="wordnet holds 2"):
        tier(wordnet=2)


def test_the_tier_agrees_with_the_fixtures_own_panel_sets(universe_frame):
    """panel_sets lists the published sets that list a row; the tier counts
    their families, so it can be re-derived from that column alone."""
    single = universe_frame[universe_frame["token_count"] == 1]
    listed = single["panel_sets"].map(lambda sets: len({
        "hunspell" if name.startswith("hunspell") else name
        for name in sets.split(";") if name}))
    corpus = single["gb_type"].eq(True) | single["wordfreq_scored"].eq(True)
    expected = np.select(
        [listed >= 2, listed == 1, corpus], ["listed_by_2_or_more", "listed_by_1", "none_with_corpus"],
        default="none_no_corpus")
    assert strata.evidence_tier.label_frame(single).tolist() == expected.tolist()


def test_the_fixtures_exercise_minus_1_and_every_tier(universe_frame):
    evidence = ["wordnet", "wiktionary_english", "hunspell_en_US", "hunspell_en_GB",
                "hunspell_en_CA", "hunspell_en_AU", "enable1", "scowl_tier"]
    single = universe_frame[universe_frame["token_count"] == 1]
    assert (single[evidence] == -1).any(axis=1).sum() > 0
    spaced = universe_frame[universe_frame["token_count"] > 1]
    assert spaced[evidence].isna().all().all()
    labels = strata.evidence_tier.label_frame(universe_frame)
    assert (labels == "not_single_token").sum() == len(spaced)
    assert set(labels) == {"listed_by_2_or_more", "listed_by_1", "none_with_corpus",
                           "none_no_corpus", "not_single_token"}


# ---- the spelling class --------------------------------------------------

@pytest.mark.parametrize("flags, label", [
    ("plain", "plain"), ("", "plain"), ("spaced", "spaced"),
    ("hyphenated;spaced", "spaced"), ("apostrophe-form;s-final;spaced", "spaced"),
    ("apostrophe-form;s-final", "apostrophe-form"), ("s-final", "apostrophe-form"),
    ("apostrophe-form;contraction", "contraction"),
    ("apostrophe-form;contraction;hyphenated", "contraction"),
    ("accented;hyphenated", "accented"), ("hyphenated;ligature", "ligature"),
    ("accented;diaeresis", "diaeresis"), ("accented;apostrophe-form;s-final", "accented"),
    ("hyphenated", "hyphenated"), ("apostrophe-form;hyphenated;s-final", "hyphenated")])
def test_spelling_class_takes_the_first_flag_in_its_order(flags, label):
    assert strata.spelling_class({"class_explicit": flags}) == label


def test_spelling_class_refuses_what_the_release_never_holds():
    with pytest.raises(ValueError, match="unknown flag"):
        strata.spelling_class({"class_explicit": "cyrillic"})
    for null in (None, NAN):
        with pytest.raises(ValueError, match="null"):
            strata.spelling_class({"class_explicit": null})


def test_spelling_class_on_the_fixtures(universe_frame):
    labels = pd.Series(strata.spelling_class.label_frame(universe_frame))
    assert (labels[universe_frame["class_explicit"] == "plain"] == "plain").all()
    assert (labels[universe_frame["token_count"] > 1] == "spaced").all()
    assert (labels[universe_frame["token_count"] == 1] != "spaced").all()


# ---- the length band -----------------------------------------------------

@pytest.mark.parametrize("length, band", [
    (1, "01-04"), (4, "01-04"), (5, "05-06"), (6, "05-06"), (7, "07-08"),
    (8, "07-08"), (9, "09-10"), (10, "09-10"), (11, "11-12"), (12, "11-12"),
    (13, "13-16"), (16, "13-16"), (17, "17+"), (200, "17+")])
def test_length_band_edges(length, band):
    assert strata.length_band({"word": "x" * length}) == band
    frame = pd.DataFrame({"word": ["x" * length]})
    assert strata.length_band.label_frame(frame).tolist() == [band]


def test_length_counts_characters_not_bytes():
    assert strata.length_band({"word": "é" * 4}) == "01-04"
    assert strata.length_band({"word": "é" * 5}) == "05-06"


def test_length_band_refuses_a_null_or_empty_word():
    for word in (None, NAN, ""):
        with pytest.raises(ValueError):
            strata.length_band({"word": word})
    with pytest.raises(ValueError):
        strata.length_band.label_frame(pd.DataFrame({"word": ["xx", ""]}))


def test_length_band_on_the_fixtures_follows_an_independent_rule(universe_frame):
    upper, names = [4, 6, 8, 10, 12, 16], list(strata.LENGTH_BANDS)
    expected = [names[bisect.bisect_left(upper, len(w))] for w in universe_frame["word"]]
    assert strata.length_band.label_frame(universe_frame).tolist() == expected


# ---- the frequency band --------------------------------------------------

@pytest.mark.parametrize("value, band", [
    (1.01, "zipf_below_2"), (1.99, "zipf_below_2"), (2.0, "zipf_2_to_3"),
    (2.99, "zipf_2_to_3"), (3.0, "zipf_3_to_4"), (3.5, "zipf_3_to_4"),
    (4.0, "zipf_4_to_5"), (4.99, "zipf_4_to_5"), (5.0, "zipf_5_or_more"),
    (7.5, "zipf_5_or_more"), (np.float32(2.5), "zipf_2_to_3")])
def test_frequency_band_edges(value, band):
    assert strata.frequency_band({"wordfreq_zipf": value}) == band


@pytest.mark.parametrize("null", [None, NAN, np.float32("nan"), pd.NA])
def test_no_value_is_its_own_band(null):
    assert strata.frequency_band({"wordfreq_zipf": null}) == "no_value"


def test_frequency_band_on_the_fixtures(with_features, features_table):
    labels = pd.Series(strata.frequency_band.label_frame(with_features))
    single = with_features["token_count"] == 1
    # a multiword row has no features row, so it has no value
    assert (labels[~single] == "no_value").all()
    # wordfreq scores a string exactly where the features config has a value
    scored = with_features["wordfreq_scored"].eq(True)
    assert ((labels != "no_value") == scored).all()
    assert (labels != "no_value").sum() == features_table["wordfreq_zipf"].to_pandas().notna().sum()


def test_join_features_keeps_the_universe_rows_and_their_order(universe_table, features_table):
    joined = join_features(universe_table, features_table)
    assert joined["id"].tolist() == universe_table["id"].to_pylist()
    assert {"wordfreq_zipf", "gb_log10_match"} <= set(joined.columns)
    assert joined["word"].tolist() == universe_table["word"].to_pylist()
    spaced = joined["token_count"] > 1
    assert joined.loc[spaced, "wordfreq_zipf"].isna().all()
    with pytest.raises(ValueError, match="already has"):
        join_features(joined, features_table, ["wordfreq_zipf"])


# ---- the columns used as they are ----------------------------------------

def test_intake_layer_and_model_or_engine_are_the_columns_values(universe_frame, fixtures_manifest):
    assert set(strata.intake_layer.label_frame(universe_frame)) == set(
        fixtures_manifest["sampling"]["strata"])
    assert strata.intake_layer.label_frame(universe_frame).tolist() == universe_frame["intake_layer"].tolist()
    assert strata.model_or_engine.label_frame(universe_frame).tolist() == universe_frame["model_or_engine"].tolist()
    assert set(strata.model_or_engine.labels) == set(universe_frame["model_or_engine"])


def test_a_column_stratum_refuses_null():
    for stratum in (strata.intake_layer, strata.model_or_engine):
        with pytest.raises(ValueError, match="null"):
            stratum({stratum.columns[0]: None})


# ---- combined strata and null handling -----------------------------------

def test_combine_joins_the_labels_and_agrees_by_row_and_by_frame(with_features):
    both = strata.combine(strata.evidence_tier, strata.length_band)
    assert set(both.columns) == set(strata.evidence_tier.columns) | {"word"}
    rows = with_features.to_dict("records")
    by_row = [both.label_of(r) for r in rows]
    assert both.label_frame(with_features).tolist() == by_row
    assert all("|" in label for label in by_row)
    with pytest.raises(ValueError, match="2 or more"):
        strata.combine(strata.length_band)


def test_is_null_reads_none_nan_and_na_as_null():
    assert all(is_null(v) for v in (None, NAN, np.float32("nan"), pd.NA, np.nan))
    assert not any(is_null(v) for v in (0, -1, 1, 0.0, "", "x", False))


def test_label_distinct_falls_back_to_rows_when_the_combined_code_would_overflow():
    rng = np.random.RandomState(0)
    frame = pd.DataFrame({f"c{i}": rng.randint(0, 300, size=400) for i in range(8)})
    columns = list(frame.columns)

    def label_of(row):
        return str(sum(row.values()) % 7)

    labels = strata.label_distinct(frame, columns, label_of)
    assert labels.tolist() == [label_of(r) for r in frame.to_dict("records")]
    assert strata.label_distinct(frame.head(0), columns, label_of).tolist() == []


def test_label_distinct_reads_null_as_one_value():
    frame = pd.DataFrame({"a": [1.0, np.nan, np.nan, 1.0, None]})
    labels = strata.label_distinct(frame, ["a"], lambda r: "null" if r["a"] != r["a"] else "one")
    assert labels.tolist() == ["one", "null", "null", "one", "null"]

