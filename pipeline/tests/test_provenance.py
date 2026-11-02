"""The intake-provenance layer's committed guards (C-064;
research/provenance/PACKAGE.md §5).

`data/universe_v2_provenance.parquet` is a gitignored sibling of the
C-016 pin: one row per candidate, in the pin's order, carrying the
intake channel and the measured containment as separate columns and one
of four provenance classes. The tests that read it skip where it is
absent (a fresh clone), as tests/test_universe_v2.py does. The committed
record — the report, the counts, the manifest, the contract — prints no
candidate word: the licence scan (tests/test_licence.py) covers every
committable file, and the walled-term scan here covers the package's own
documents and records. Each guard carries a fixture showing it can fail
(C-032 R7-e). The forms the engine rules are tried on are constructed
for the test and are not candidates.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

import research.verify_doc_numbers as verify
from research.inthewild.walled_terms import find_hits, walled_terms
from research.provenance import build_provenance as bp
from research.provenance.extract_eol_intake import LayoutError, LineParser
from research.provenance.synthetic_engine import RULES, infer_engine

REPO = Path(__file__).resolve().parents[1]
PDIR = REPO / "research" / "provenance"
PIN = REPO / "data" / "universe_v2.parquet"
RESTRICTED_CSV = REPO / ".cache" / "audit" / "universe_miss_restricted.csv"

needs_layer = pytest.mark.skipif(
    not bp.OUT_PARQUET.exists(),
    reason="universe_v2_provenance.parquet not built")


@pytest.fixture(scope="module")
def layer():
    import pyarrow.parquet as pq
    return pq.read_table(bp.OUT_PARQUET)


@pytest.fixture(scope="module")
def body() -> dict:
    return json.loads((PDIR / "provenance.json").read_text(encoding="utf-8"))


@needs_layer
def test_the_layer_has_every_row_of_the_pin_in_the_pins_order(layer, body):
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    pin_words = pq.read_table(PIN, columns=["word"])["word"]
    assert layer.num_rows == pin_words.length() == body["pin"]["v2_rows"]
    assert tuple(layer.column_names) == bp.COLUMNS
    assert pc.all(pc.equal(layer["word"], pin_words)).as_py()
    # the join is complete: only the declared nullable columns hold nulls
    nullable = {"eol_synthetic_category", "eol_synthetic_engine_inferred",
                "gb_type", "wordfreq_scored", "wikt_title_any"}
    for name in bp.COLUMNS:
        if name not in nullable:
            assert layer[name].null_count == 0, name
    spaced = pc.sum(pc.equal(layer["intake_layer"], "spaced_c015")).as_py()
    for name in ("gb_type", "wordfreq_scored", "wikt_title_any"):
        assert layer[name].null_count == spaced, name


@needs_layer
def test_the_classes_partition_the_rows(layer, body):
    import pyarrow.compute as pc

    has_channel = pc.not_equal(layer["intake_channels"], bp.UNRECORDED)
    has_containment = pc.or_(
        pc.or_(pc.greater_equal(layer["panel_count"], 1),
               pc.fill_null(layer["gb_type"], False)),
        pc.fill_null(layer["wordfreq_scored"], False))
    want = pc.if_else(
        has_channel,
        pc.if_else(has_containment, bp.CLASSES[0], bp.CLASSES[1]),
        pc.if_else(has_containment, bp.CLASSES[2], bp.CLASSES[3]))
    assert pc.all(pc.equal(layer["provenance_class"], want)).as_py()
    counts = {row["values"]: row["counts"] for row in
              pc.value_counts(layer["provenance_class"]).to_pylist()}
    assert set(counts) <= set(bp.CLASSES)
    assert sum(counts.values()) == layer.num_rows
    assert counts == body["measured"]["rows_by_class"]
    assert bp.provenance_class(True, False) == "channel_only"
    assert bp.provenance_class(False, False) == "neither"


@needs_layer
def test_every_channel_label_is_in_the_vocabulary(layer):
    combos = layer.group_by(["intake_layer", "intake_channels"]) \
        .aggregate([]).to_pylist()
    namespaces = {"eol_valid": {"eol"}, "eol_invalid": {"eol"},
                  "c1_exceptions": {"census", "ledger"},
                  "c4_additions": {"audit"}, "spaced_c015": {"spaced"}}
    for row in combos:
        labels = row["intake_channels"].split(";")
        assert labels == sorted(set(labels))
        assert bp.labels_outside_vocabulary(labels) == []
        assert {x.split(":")[0] for x in labels} \
            <= namespaces[row["intake_layer"]]
        # the unrecorded label stands alone
        assert bp.UNRECORDED not in labels or labels == [bp.UNRECORDED]


@needs_layer
def test_a_generated_row_is_never_derived(layer, body):
    import pyarrow.compute as pc

    kinds = layer.group_by(["intake_layer", "intake_kind"]) \
        .aggregate([([], "count_all")]).to_pylist()
    for row in kinds:
        ceol = row["intake_layer"] in ("c1_exceptions", "c4_additions",
                                       "spaced_c015")
        assert (row["intake_kind"] == "derived") == ceol, row
    generated = layer.filter(pc.equal(layer["intake_kind"], "generated"))
    others = layer.filter(pc.not_equal(layer["intake_kind"], "generated"))
    assert generated.num_rows == body["measured"]["generated"]["rows"]
    assert pc.all(pc.match_substring(generated["intake_channels"],
                                     "eol:synthetic-engine")).as_py()
    assert not pc.any(pc.match_substring(others["intake_channels"],
                                         "eol:synthetic-engine")).as_py()
    # the engine is inferred for every generated row and for no other
    assert generated["eol_synthetic_engine_inferred"].null_count == 0
    assert set(pc.unique(
        generated["eol_synthetic_engine_inferred"]).to_pylist()) <= set(RULES)
    assert others["eol_synthetic_engine_inferred"].null_count \
        == others.num_rows
    assert others["eol_synthetic_category"].null_count == others.num_rows


@needs_layer
@pytest.mark.skipif(not RESTRICTED_CSV.exists(),
                    reason="restricted split not present (clean clone)")
def test_the_restricted_rows_are_in_the_parquet_and_in_no_committed_file(
        layer, body):
    import pyarrow as pa
    import pyarrow.compute as pc

    with open(RESTRICTED_CSV, encoding="utf-8") as f:
        restricted = {row["word"] for row in csv.DictReader(f)}
    assert len(restricted) == body["pin"]["restricted_rows"]
    present = pc.sum(pc.is_in(layer["word"],
                              value_set=pa.array(sorted(restricted))))
    assert present.as_py() == len(restricted)
    for path in sorted(PDIR.iterdir()) + [Path(__file__)]:
        if path.is_file():
            tokens = set(re.split(r"[^a-z]+",
                                  path.read_text(encoding="utf-8").lower()))
            assert not tokens & restricted, path.name


def test_the_report_and_the_records_print_no_walled_term():
    terms = walled_terms()
    for name in ("PROVENANCE.md", "PROVENANCE.template.md",
                 "provenance.json", "eol_dictionaries_manifest.json"):
        text = (PDIR / name).read_text(encoding="utf-8")
        for group, words in terms.items():
            assert find_hits(text, words) == set(), (
                f"{group}: walled terms printed in {name}")


def test_the_line_parser_refuses_a_line_outside_the_layout():
    good = (b'{\n  "k1": {"status": "s", "candidate_source": ["a_valid"]},\n'
            b'  "k2": {"candidate_source": null}\n}\n')
    for step in (1, 5, len(good)):
        parser, pairs = LineParser(), []
        for i in range(0, len(good), step):
            pairs += parser.feed(good[i:i + step])
        pairs += parser.close()
        assert [key for key, _ in pairs] == ["k1", "k2"]
        assert (parser.lines, parser.entries) == (4, 2)
        assert parser.sha256.hexdigest() == hashlib.sha256(good).hexdigest()
    malformed = {
        "no opening brace": b'  "k1": {}\n}\n',
        "a one-space indent": b'{\n "k1": {}\n}\n',
        "a pretty-printed entry": b'{\n  "k1": {\n    "a": 1\n  }\n}\n',
        "a missing comma": b'{\n  "k1": {}\n  "k2": {}\n}\n',
        "a comma before the close": b'{\n  "k1": {},\n}\n',
        "a repeated key": b'{\n  "k1": {},\n  "k1": {}\n}\n',
        "content after the close": b'{\n  "k1": {}\n}\n  "k2": {}\n',
        "no closing brace": b'{\n  "k1": {}\n',
        "a value that is no object": b'{\n  "k1": [1]\n}\n',
    }
    for why, data in malformed.items():
        parser = LineParser()
        with pytest.raises(LayoutError) as caught:
            parser.feed(data)
            parser.close()
        # the error names a line and an offset, never the line's content
        assert "k1" not in str(caught.value), why


#: Constructed for the test over a constructed base set; checked at
#: authoring time, and below where the pin exists, to be no candidate.
BASE = {"zqorvex", "xqimbly", "zqathe", "zqonkum", "zqextus", "zqindy"}
FORMS = {
    "zqorvexes": "affixation/plural",
    "zqindies": "affixation/plural",
    "zqonka": "affixation/plural",
    "zqexti": "affixation/plural",
    "zqathed": "affixation/verb-form",
    "zqorvexing": "affixation/verb-form",
    "xqimblier": "affixation/comparative-or-agent",
    "zqathest": "affixation/superlative",
    "zqorvexings": "affixation/gerund-plural",
    "zqorvexers": "affixation/agent-plural",
    "fluorozqorvex": "chemical-variation/substituent-prefix",
    "dichlorozqorvexes": "chemical-variation/substituent-prefix",
    "iodoheptynoates": "chemical-variation/root-chain",
    "hepatozqorvex": "medical-scientific-prefixing/domain-prefix",
    "nonzqorvex": "affixation/general-prefix",
    "zqorvexoses": "greek-plural/-ses",
    "xqimblides": "greek-plural/-des",
    "zzqrvq": "unresolved/none",
}


def test_the_engine_rules_on_constructed_forms():
    for form, rule in FORMS.items():
        assert rule in RULES
        assert infer_engine(form, BASE.__contains__) == rule, form
    # a form is never its own base
    assert infer_engine("zqorvex", BASE.__contains__) == "unresolved/none"
    if PIN.exists():
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        words = pq.read_table(PIN, columns=["word"])["word"]
        constructed = pa.array(sorted(BASE | set(FORMS)))
        assert not pc.any(pc.is_in(constructed, value_set=words)).as_py()


def test_the_guards_can_fail():
    body = json.loads((PDIR / "provenance.json").read_text(encoding="utf-8"))
    report = (PDIR / "PROVENANCE.md").read_text(encoding="utf-8")
    template = (PDIR / "PROVENANCE.template.md").read_text(encoding="utf-8")
    check = verify._provenance_report_failures
    assert check(report, template, body, bp.render_report) == []
    # a changed figure in the report
    residual = f"{body['measured']['rows_by_class']['neither']:,}"
    assert residual in report
    assert check(report.replace(residual, "16,374", 1), template, body,
                 bp.render_report)
    # a literal figure, or a literal percentage, in the template
    assert check(report, template + "\nA stray 1,234 rows.\n", body,
                 bp.render_report)
    assert check(report, template + "\nA stray 12.5% share.\n", body,
                 bp.render_report)
    # a changed row of the JSON, and a row the JSON does not hold
    moved = json.loads(json.dumps(body))
    moved["measured"]["rows_by_class"]["neither"] += 1
    assert check(report, template, moved, bp.render_report)
    assert check(report, template + "\n{{measured.no_such_row}}\n", body,
                 bp.render_report)
    # the vocabulary guard
    assert bp.labels_outside_vocabulary(["eol:wordnet", "spaced:wordnet"]) \
        == []
    assert bp.labels_outside_vocabulary(["eol:wordnet", "eol:planted"]) \
        == ["eol:planted"]
    with pytest.raises(ValueError):
        bp.split_label("planted_valid")
    with pytest.raises(ValueError):
        bp.inherited_channels(None, "planted_source")
    with pytest.raises(ValueError):
        bp.ceol_channels("spaced_c015", "planted")
    # the walled-term scan
    ledger_word = sorted(walled_terms()["ledger"])[0]
    assert find_hits(f"a sentence with {ledger_word} in it",
                     walled_terms()["ledger"]) == {ledger_word}
