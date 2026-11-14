"""The public projection (research/release/withholding.py; D-010, D-011)
and the vetted example list's rule (safeguards/examples.py), on rows built
here. Every test runs in a clone."""

from __future__ import annotations

import hashlib

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from research.provenance import build_provenance
from research.release import columns, withholding
from safeguards import examples

#: stand-ins, assembled so that this file never spells one whole
TERM = "zq" + "vex"
PHRASE = "zqa" + " " + "zqb"
WORD = "zq" + "wab"


def _row(**changes) -> dict:
    row = {name: None for name in columns.UNIVERSE_COLUMNS}
    row.update(word="stand-in", sources="eol_universe@08ae92b8",
               intake_channels="eol:wikipedia", panel_sets="", panel_count=0,
               provenance_class="channel_only", gb_type=False,
               wordfreq_scored=False)
    row.update(changes)
    return row


def test_the_published_panel_is_the_panel_without_the_withheld_lists():
    assert set(withholding.WITHHELD_SETS) == {
        "nwl2023", "csw21", "sowpods_legacy", "web2", "web2a"}
    assert set(withholding.PUBLISHED_SETS) | set(withholding.WITHHELD_SETS) \
        == set(columns.PANEL_SETS)
    assert not set(withholding.PUBLISHED_UNIVERSE_COLUMNS) & set(withholding.WITHHELD_SETS)
    assert [c for c in columns.UNIVERSE_COLUMNS if c not in withholding.WITHHELD_SETS] \
        == list(withholding.PUBLISHED_UNIVERSE_COLUMNS)


def test_a_published_row_names_no_withheld_list():
    row = _row(
        sources="eol:csw21;wiktionary_english;web2;eol:nwl2023",
        intake_channels="audit:csw21;audit:wiktionary_english;census:web2a",
        panel_sets="wiktionary_english;web2;enable1;sowpods_legacy;nwl2023;csw21;scowl",
        panel_count=7, provenance_class="channel_and_containment")
    out = withholding.published_row(row)
    assert list(out) == list(withholding.PUBLISHED_UNIVERSE_COLUMNS)
    assert out["sources"] == "wiktionary_english"
    assert out["intake_channels"] == "audit:wiktionary_english"
    assert out["panel_sets"] == "wiktionary_english;enable1;scowl"
    assert out["panel_count"] == 3
    assert withholding.reveals_a_withheld_list(out) == []
    assert withholding.reveals_a_withheld_list(row) != []


def test_the_class_is_recomputed_over_the_published_fields():
    # listed only by withheld lists, first seen only through them: the
    # channel is withheld, and the row keeps evidence only where a corpus
    # holds the string; with none left it is held back (D-011 line 1)
    only = dict(sources="eol:csw21;eol:sowpods_legacy",
                intake_channels="audit:csw21;audit:sowpods_legacy",
                panel_sets="sowpods_legacy;csw21", panel_count=2,
                provenance_class="channel_and_containment")
    assert withholding.published_row(_row(**only)) is None
    out = withholding.published_row(_row(**only, gb_type=True))
    assert (out["panel_sets"], out["panel_count"]) == ("", 0)
    assert out["intake_channels"] == withholding.CHANNEL_WITHHELD
    assert out["provenance_class"] == "containment_only"
    # a row no withheld list touches keeps its class
    kept = _row(panel_sets="wordnet;scowl", panel_count=2,
                provenance_class="channel_and_containment")
    assert withholding.published_row(kept)["provenance_class"] == "channel_and_containment"
    # the unrecorded label is no channel; a null corpus field is no containment
    assert withholding.provenance_class(withholding.UNRECORDED, 0, None, None) == "neither"
    assert withholding.provenance_class("spaced:wordnet", 1, None, None) \
        == "channel_and_containment"


def test_the_withheld_channel_labels_go_and_the_marker_stands_alone():
    # D-010 line 1's 4, and D-012 line 2's 2
    assert withholding.WITHHELD_CHANNEL_LABELS == {
        "eol:withheld-list", "eol:collins", "eol:coca_frequency",
        "eol:dictionary-api:merriam-webster", "eol:linux", "eol:nltk"}
    pc = withholding.published_channels
    assert pc("eol:withheld-list") == withholding.CHANNEL_WITHHELD
    assert pc("eol:coca_frequency;audit:csw21") == withholding.CHANNEL_WITHHELD
    assert pc("eol:coca_frequency;eol:wikipedia") == "eol:wikipedia"
    assert pc("eol:dictionary-api:free-dictionary") == "eol:dictionary-api:free-dictionary"
    assert pc(withholding.UNRECORDED) == withholding.UNRECORDED
    assert pc(None) is None and pc("") == ""
    # neither the marker nor the unrecorded label is a channel
    assert not withholding.has_channel(withholding.CHANNEL_WITHHELD)
    assert not withholding.has_channel(withholding.UNRECORDED)
    assert withholding.has_channel("eol:wikipedia")


def test_a_row_is_held_back_exactly_when_withholding_leaves_it_no_evidence():
    def held(full_class, sets, public_class, channels, layer="eol_valid",
             sources="eol_universe@08ae92b8"):
        return withholding.held_back_reason(full_class, sets, public_class,
                                            channels, layer, sources)
    # tier 2: every listing withheld, nothing public left
    assert held("channel_and_containment", "web2a", "neither", "census:web2a") == "tier_2"
    assert held("containment_only", "nwl2023;csw21", "neither",
                withholding.UNRECORDED) == "tier_2"
    # a withheld channel its only evidence, nothing public left
    assert held("channel_only", "", "neither", "eol:coca_frequency") == "withheld_channel"
    # no evidence in v2.0 either: the row ships as it did
    assert held("neither", "", "neither", withholding.UNRECORDED) is None
    # some public evidence left: it ships
    assert held("channel_and_containment", "web2a", "containment_only",
                "census:web2a") is None
    # D-012 line 1: a census or audit row whose every source is withheld is
    # held back though it keeps public evidence; a published source keeps it
    assert held("channel_and_containment", "web2a", "containment_only",
                "census:web2a", "c1_exceptions", "web2a") == "withheld_sources"
    assert held("channel_and_containment", "csw21", "containment_only",
                "audit:csw21", "c4_additions", "csw21;sowpods_legacy") == "withheld_sources"
    assert held("channel_and_containment", "csw21;scowl", "channel_and_containment",
                "audit:scowl", "c4_additions", "csw21;scowl") is None
    # N-1: a census row whose only channel is a withheld list's census label,
    # with no listing and no corpus, is D-012 line 1's, not uncovered
    assert held("channel_only", "", "neither", "census:web2",
                "c1_exceptions", "web2") == "withheld_sources"
    # the inherited rows' tag and the spaced layer's sources are never emptied
    assert held("channel_and_containment", "web2", "containment_only",
                "eol:wikipedia", "eol_valid", "eol_universe@08ae92b8") is None
    # a row neither line of D-011 covers (its only channel names a withheld
    # list, and no listing): the projection refuses rather than guess
    with pytest.raises(withholding.UncoveredRow):
        held("channel_only", "", "neither", "census:web2")
    with pytest.raises(withholding.UncoveredRow):
        withholding.published_row(_row(intake_channels="census:web2",
                                       provenance_class="channel_only"))
    coca = _row(intake_channels="eol:coca_frequency", provenance_class="channel_only")
    assert withholding.published_row(coca) is None
    corpus = _row(intake_channels="eol:coca_frequency", provenance_class="channel_and_containment",
                  wordfreq_scored=True)
    assert withholding.published_row(corpus)["provenance_class"] == "containment_only"


#: rows for the 2 forms of the projection, each case among them
ROWS = [
    _row(word="a", panel_sets="wordnet;web2;scowl", panel_count=3,
         sources="eol_universe@08ae92b8", intake_channels="eol:withheld-list",
         provenance_class="channel_and_containment"),
    _row(word="b", panel_sets="web2a", panel_count=1, intake_channels="census:web2a",
         sources="web2a", provenance_class="channel_and_containment"),
    _row(word="c", intake_channels="eol:coca_frequency", provenance_class="channel_only"),
    _row(word="d", intake_channels=withholding.UNRECORDED, provenance_class="neither"),
    _row(word="e", panel_sets="csw21", panel_count=1, intake_channels="eol:wikipedia",
         sources="eol_universe@08ae92b8", provenance_class="channel_and_containment"),
    _row(word="f", panel_sets="nwl2023", panel_count=1, intake_channels="eol:coca_frequency",
         sources="eol_universe@08ae92b8", provenance_class="channel_and_containment",
         gb_type=True),
    # wordfreq alone keeps a row whose channel is withheld
    _row(word="g", intake_channels="eol:coca_frequency", wordfreq_scored=True,
         provenance_class="channel_and_containment"),
    # a spaced row: its corpus cells are null, which is no containment
    _row(word="h i", intake_channels="eol:coca_frequency", gb_type=None,
         wordfreq_scored=None, provenance_class="channel_only"),
    _row(word="j k", panel_sets="wordnet", panel_count=1, sources="wordnet",
         intake_channels="spaced:wordnet", gb_type=None, wordfreq_scored=None,
         provenance_class="channel_and_containment"),
    # tier 2 with an unrecorded channel
    _row(word="l", panel_sets="web2", panel_count=1, intake_channels=withholding.UNRECORDED,
         provenance_class="containment_only"),
    # the published free-dictionary label alone
    _row(word="m", intake_channels="eol:dictionary-api:free-dictionary",
         provenance_class="channel_only"),
    # listed only by 2 withheld sets, a channel left / none left
    _row(word="n", panel_sets="nwl2023;csw21", panel_count=2, intake_channels="eol:wikipedia",
         provenance_class="channel_and_containment"),
    _row(word="o", panel_sets="sowpods_legacy;csw21", panel_count=2,
         intake_channels="eol:collins", provenance_class="channel_and_containment"),
    # D-012 line 1: census and audit rows whose every source is withheld
    _row(word="q-r", intake_layer="c1_exceptions", sources="web2a", panel_sets="web2a",
         panel_count=1, intake_channels="census:web2a", gb_type=True,
         provenance_class="channel_and_containment"),
    _row(word="s", intake_layer="c4_additions", sources="csw21;sowpods_legacy",
         panel_sets="sowpods_legacy;csw21", panel_count=2,
         intake_channels="audit:csw21;audit:sowpods_legacy", wordfreq_scored=True,
         provenance_class="channel_and_containment"),
    _row(word="t", intake_layer="c4_additions", sources="csw21;scowl",
         panel_sets="csw21;scowl", panel_count=2, intake_channels="audit:csw21;audit:scowl",
         provenance_class="channel_and_containment"),
    # N-1: no listing, no corpus, its only channel a withheld list's census label
    _row(word="v-w", intake_layer="c1_exceptions", sources="web2", intake_channels="census:web2",
         provenance_class="channel_only"),
    # D-012 line 2's 2 labels
    _row(word="u", panel_sets="wordnet;web2", panel_count=2,
         intake_channels="eol:linux;eol:nltk;eol:wikipedia",
         provenance_class="channel_and_containment"),
]


def _table(rows):
    schema = pa.schema([(n, pa.int16() if n == "panel_count" else
                         pa.bool_() if n in ("gb_type", "wordfreq_scored") else pa.string())
                        for n in ("word", "intake_layer", "sources", "intake_channels",
                                  "panel_sets", "panel_count", "gb_type",
                                  "wordfreq_scored", "provenance_class")])
    table = pa.Table.from_pylist([{k: r[k] for k in schema.names} for r in rows], schema)
    return pa.table({name: table[name] if name in schema.names else pa.nulls(len(rows))
                     for name in columns.UNIVERSE_COLUMNS})


def test_the_projection_of_a_table_is_the_projection_of_its_rows():
    # 2 tables concatenated: the table form reads more than 1 chunk
    full = pa.concat_tables([_table(ROWS[:7]), _table(ROWS[7:])])
    assert full["word"].num_chunks == 2
    public, held = withholding.project(full)
    assert public.column_names == list(withholding.PUBLISHED_UNIVERSE_COLUMNS)
    by_row = [withholding.published_row(r) for r in ROWS]
    # the held rows and their reasons are the per-row form's, row by row
    assert held.select(["word", "reason"]).to_pylist() == [
        {"word": r["word"], "reason": withholding.held_back_reason(
            r["provenance_class"], r["panel_sets"],
            withholding.provenance_class(
                withholding.published_channels(r["intake_channels"]),
                len([x for x in withholding.published_panel_sets(r["panel_sets"]).split(";") if x]),
                r["gb_type"], r["wordfreq_scored"]),
            r["intake_channels"], r["intake_layer"], r["sources"])}
        for r, out in zip(ROWS, by_row) if out is None]
    assert [h["word"] for h in held.to_pylist()] == ["b", "c", "h i", "l", "o", "q-r", "s", "v-w"]
    reasons = {h["word"]: h["reason"] for h in held.to_pylist()}
    assert reasons["s"] == reasons["v-w"] == "withheld_sources"
    assert {r["word"]: r["intake_channels"] for r in by_row if r}["u"] == "eol:wikipedia"
    assert public["word"].to_pylist() == [r["word"] for r in by_row if r]
    for name in ("sources", "intake_channels", "panel_sets", "panel_count",
                 "provenance_class"):
        assert public[name].to_pylist() == [r[name] for r in by_row if r], name
    # wordfreq alone is containment, in both forms
    assert {r["word"]: r["provenance_class"] for r in by_row if r}["g"] == "containment_only"
    # a classes_of that ignored wordfreq_scored would fail here
    assert withholding.classes_of(
        pa.array(["eol:channel-withheld"]), pa.array([0], pa.int16()),
        pa.array([False]), pa.array([True])).to_pylist() == ["containment_only"]


def test_the_projection_refuses_a_row_d_011_does_not_cover():
    uncovered = _row(word="p", intake_channels="census:web2", provenance_class="channel_only")
    with pytest.raises(withholding.UncoveredRow):
        withholding.project(_table(ROWS + [uncovered]))


def test_the_allow_lists_hold_no_withheld_label():
    assert not withholding.PUBLISHED_CHANNEL_LABELS & withholding.WITHHELD_LABELS
    assert not withholding.PUBLISHED_CHANNEL_LABELS & withholding.WITHHELD_CHANNEL_LABELS
    assert not withholding.PUBLISHED_SOURCE_LABELS & withholding.WITHHELD_LABELS
    assert withholding.CHANNEL_WITHHELD in withholding.PUBLISHED_CHANNEL_LABELS
    assert withholding.INHERITED_SOURCES_TAG in withholding.PUBLISHED_SOURCE_LABELS
    # every published row of the cases names allowed labels only
    for out in filter(None, (withholding.published_row(r) for r in ROWS)):
        assert set(filter(None, out["intake_channels"].split(";"))) \
            <= withholding.PUBLISHED_CHANNEL_LABELS
        assert set(filter(None, out["sources"].split(";"))) \
            <= withholding.PUBLISHED_SOURCE_LABELS


def test_the_class_rule_is_the_provenance_layer_rule():
    assert withholding.CLASSES == build_provenance.CLASSES
    assert withholding.UNRECORDED == build_provenance.UNRECORDED
    for has_channel in (True, False):
        for contained in (True, False):
            channels = "eol:wikipedia" if has_channel else withholding.UNRECORDED
            assert withholding.provenance_class(channels, int(contained), False, False) \
                == build_provenance.provenance_class(has_channel, contained)


def test_the_scan_of_a_list_of_strings_does_not_match_across_rows():
    first, second = PHRASE.split()
    strings = ["plain", TERM, f"x{TERM}", first, second, PHRASE, f"a {WORD}", "last"]
    assert examples.clean_mask(strings, {TERM, PHRASE}, {WORD}) == [
        True, False, True, True, True, False, False, True]


def test_the_example_rule_on_a_small_release(tmp_path):
    hunspell = "hunspell_en_US;hunspell_en_GB;hunspell_en_CA;hunspell_en_AU"
    rows = [
        ("pair listed", "wordnet;scowl", False),
        ("solo listed", "wordnet", False),
        ("withheld only", "web2;nwl2023;csw21", False),
        ("solo published", "enable1;sowpods_legacy;csw21", False),
        (TERM, "wordnet;wiktionary_english;scowl", False),
        (f"a {WORD}", "wordnet;wiktionary_english", False),
        # SCOWL and the en_US, en_CA, en_AU editions are 1 family; en_GB is
        # its own (D-010 line 6)
        ("scowl and its editions", "hunspell_en_US;hunspell_en_CA;scowl", False),
        ("hunspell only", hunspell, False),
        ("hunspell and one", "hunspell_en_US;hunspell_en_GB;enable1;nwl2023", False),
        ("not shippable", "wordnet;scowl", True),
    ]
    pq.write_table(pa.table({
        "word": [w for w, _s, _r in rows], "panel_sets": [s for _w, s, _r in rows],
        "token_count": pa.array([len(w.split()) for w, _s, _r in rows], pa.int32()),
        "class_explicit": ["spaced" if " " in w else "plain" for w, _s, _r in rows],
        "is_restricted": [r for _w, _s, r in rows]}), tmp_path / "universe.parquet")
    kept, counts = examples.eligible(tmp_path, {TERM}, {WORD})
    assert [r["word"] for r in kept] == ["pair listed", "hunspell only", "hunspell and one"]
    assert counts == {"rows_of_the_universe_config": 10, "restricted_rows": 1,
                      "listed_by_at_least_2_source_families": 5,
                      "removed_by_the_scan": 2, "eligible": 3}
    body = examples.summary(kept, counts, "v0")
    assert body["strings"] == 3 and body["by_class"] == {"spaced": 3}
    assert body["by_source_family_count"] == {"2": 2, "3": 1}
    assert body["by_source_families"] == {"enable1;hunspell_en_GB;scowl": 1,
                                          "hunspell_en_GB;scowl": 1, "scowl;wordnet": 1}
    assert TERM not in str(body) and WORD not in str(body)


def test_the_source_families_of_the_published_panel():
    assert examples.MIN_FAMILIES == 2
    grouped = examples.published_families()
    assert sorted(s for sets in grouped.values() for s in sets) \
        == sorted(withholding.PUBLISHED_SETS)
    assert grouped["scowl"] == ["hunspell_en_US", "hunspell_en_CA",
                                "hunspell_en_AU", "scowl"]
    assert grouped["hunspell_en_GB"] == ["hunspell_en_GB"]
    assert all(sets == [name] for name, sets in grouped.items() if name != "scowl")
    assert examples.families("hunspell_en_US;hunspell_en_AU") == {"scowl"}
    assert examples.families("hunspell_en_GB;hunspell_en_US;scowl") == {"hunspell_en_GB", "scowl"}
    assert examples.families("") == set()


def test_the_ranking_is_ascending_in_the_stated_key(monkeypatch):
    """D-012 line 3: sha256(key:stratum:string), here under a stand-in key, so
    that the test runs where private/ is absent and never reads the real key."""
    stand_in = "0" * 63 + "1"

    def key(name):
        assert name == "examples"
        return stand_in

    monkeypatch.setattr(examples.keys, "key", key)
    rows = [{"word": w} for w in ("stand-in b", "stand-in a", "stand-in c")]
    ranks = [hashlib.sha256(
        f"{stand_in}:{examples.STRATUM}:{r['word']}".encode("utf-8")).hexdigest()
        for r in examples.ranked(rows)]
    assert ranks == sorted(ranks) and len(set(ranks)) == 3


def test_the_draw_passes_over_a_phrase_spelled_across_2_lines():
    first, second = PHRASE.split()
    ranking = ["plain", first, second, "other", "last"]
    # each string is clean by itself; the 2nd and 3rd lines spell the phrase
    assert examples.clean_mask(ranking, {PHRASE}, set()) == [True] * 5
    assert examples.draw(ranking, 2, {PHRASE}) == ([0, 1], 0)
    assert examples.draw(ranking, 3, {PHRASE}) == ([0, 2, 3], 1)
    assert examples.draw(ranking, 4, {PHRASE}) == ([0, 2, 3, 4], 1)
    with pytest.raises(ValueError):
        examples.draw(ranking, 5, {PHRASE})
    # the scan reads the file's path as the line before the first
    assert examples.draw([second, "plain", "other"], 2, {PHRASE},
                         path=f"x/{first}") == ([1, 2], 1)
    # a term inside 1 line is not the draw's to pass over
    with pytest.raises(ValueError):
        examples.draw(["plain", TERM], 2, {TERM})


def _ranked_rows(spec: str) -> list[dict]:
    """Rows in ranking order from a string of class letters: a for plain, b
    for hyphenated, c for spaced; each row's string is unique."""
    names = {"a": "plain", "b": "hyphenated", "c": "spaced"}
    return [{"word": f"stand-in {n}", "class_explicit": names[k]}
            for n, k in enumerate(spec)]


def test_the_floor_fills_each_short_class_from_the_rest_of_the_ranking():
    order = _ranked_rows("aaab" "abcab" "bcacb" "c")
    drawn = [0, 1, 2, 3]                 # 3 plain, 1 hyphenated
    added, passed_over = examples.floor_additions(order, drawn, set(), floor=3)
    # plain already holds 3; hyphenated takes 2 more and spaced 3, in order
    assert added == [5, 6, 8, 10, 12] and passed_over == 0
    assert [order[i]["class_explicit"] for i in added] == [
        "hyphenated", "spaced", "hyphenated", "spaced", "spaced"]
    # a class with fewer strings than the floor gets every one of them
    added, _ = examples.floor_additions(_ranked_rows("aac"), [0, 1], set(), floor=5)
    assert added == [2]
    # the draw's lines never change, and nothing is added where none is short
    assert examples.floor_additions(order, list(range(len(order))), set()) == ([], 0)


def test_the_floor_passes_over_its_own_string_where_a_phrase_crosses_into_it():
    first, second = PHRASE.split()
    order = [{"word": "plain", "class_explicit": "plain"},
             {"word": first, "class_explicit": "plain"},
             {"word": second, "class_explicit": "spaced"},
             {"word": "other", "class_explicit": "spaced"},
             {"word": "another", "class_explicit": "spaced"}]
    # the draw ends with the phrase's 1st word; the floor's 1st string would
    # finish it, so that string, not a later one, is passed over, and the
    # next of its class is taken
    added, passed_over = examples.floor_additions(order, [0, 1], {PHRASE}, floor=2)
    assert added == [3, 4] and passed_over == 1
    added, passed_over = examples.floor_additions(order, [0, 1], {PHRASE}, floor=1)
    assert added == [3] and passed_over == 1
    # a class the floor cannot fill once a string is passed over is an error
    with pytest.raises(ValueError):
        examples.floor_additions(order[:3], [0, 1], {PHRASE}, floor=1)


def test_the_reach_guard_names_a_label_a_withheld_list_copies():
    """The guard's counts: a label all of whose rows web2 lists is a breach;
    the same label with a row web2 does not list, at 99%, is not."""
    rows = [_row(word=f"w{i}", panel_sets="wordnet;web2", panel_count=2,
                 intake_channels="eol:opensource", provenance_class="channel_and_containment")
            for i in range(99)]
    _public, _held, reach = withholding.project_and_measure(_table(rows))
    assert reach["labels"]["eol:opensource"] == {"rows": 99, "web2": 99}
    assert withholding.reach_breaches(reach) == ["eol:opensource: web2"]
    rows.append(_row(word="w99", panel_sets="wordnet", panel_count=1,
                     intake_channels="eol:opensource", provenance_class="channel_and_containment"))
    _public, _held, reach = withholding.project_and_measure(_table(rows))
    assert withholding.reach_breaches(reach) == ["eol:opensource: web2"]  # 99 of 100
    rows.append(_row(word="w100", panel_sets="wordnet", panel_count=1,
                     intake_channels="eol:opensource", provenance_class="channel_and_containment"))
    _public, _held, reach = withholding.project_and_measure(_table(rows))
    assert withholding.reach_breaches(reach) == []  # 99 of 101
    # a layer's emptied sources: the held rows are not counted, the shipped are
    assert reach["empty_sources"] == {}



def test_the_reach_guard_counts_and_breaches_a_layer_s_emptied_sources():
    """NS-3: shipped rows of a layer outside the census and the audit whose
    published sources come out empty are counted by layer, and a withheld
    list that lists all of them is a breach."""
    rows = [_row(word=f"e{i}", intake_layer="eol_valid", sources="web2",
                 panel_sets="wordnet;web2", panel_count=2, intake_channels="eol:wikipedia",
                 provenance_class="channel_and_containment") for i in range(12)]
    public, held, reach = withholding.project_and_measure(_table(rows))
    assert held.num_rows == 0 and public.num_rows == 12
    assert reach["empty_sources"] == {"eol_valid with empty sources": {"rows": 12, "web2": 12}}
    assert "eol_valid with empty sources: web2" in withholding.reach_breaches(reach)
    # the same rows with a published source: no emptied cell
    for r in rows:
        r["sources"] = "web2;wordnet"
    _public, _held, reach = withholding.project_and_measure(_table(rows))
    assert reach["empty_sources"] == {}


def test_the_held_back_table_carries_the_differenced_fields():
    """N-12: the private file names each held row's layer, kind, and class,
    which the build's floor counts."""
    full = _table(ROWS)
    _public, held = withholding.project(full)
    assert set(withholding.DIFFERENCED) <= set(held.column_names)
