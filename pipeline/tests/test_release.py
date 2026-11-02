"""UR-1, the release package of the CEOL Universe (C-078;
research/release/PACKAGE_UR1.md §9): AT-UR1-1 to AT-UR1-11.

Each test runs the pipeline's own functions on a constructed fixture whose
"words" are digit tokens, never candidates (C-053's fixture rule; the
C-013 wall), built end to end by `build_release.build` into a temporary
directory; each guard is shown able to fail (C-032 R7-e). Where data/
exists (the repository environment the census routes), the tests also
run on the release files under data/release/, and a missing release file
fails the test rather than passing it; in a fresh clone that half does
not apply, so no test skips in either environment.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest

import research.verify_doc_numbers as verify
from research.release import build_release as B
from research.release import columns as C
from research.release import release_calcs as R
from research.release import upload_release as U
from research.release.profile import png_plot as P
from research.release.profile import pos_estimate as PE
from research.release.profile import universe_profile as UP

REPO = Path(__file__).resolve().parents[1]
IN_REPO = (REPO / "data" / "evidence.parquet").exists()

# ---------------------------------------------------------------------------
# The digit fixture: 7 pin rows, 1 restricted, 2 spaced
# ---------------------------------------------------------------------------

#: word, eol, eol_universe, classes, sources, date, c4, restricted, tokens
PIN_ROWS = (
    ("10", True, True, "", "eol_universe@c1139698", "2026-08-17", False,
     False, 1),
    ("11", False, True, "", "eol_universe@c1139698", "2026-08-17", False,
     False, 1),
    ("12", False, False, "apostrophe-form;s-final", "hunspell_en_GB;scowl",
     "2026-08-20", False, False, 1),
    ("13 14", False, False, "spaced", "wiktionary_english;wordnet",
     "2026-08-26", False, False, 2),
    ("15-16", False, False, "hyphenated", "web2a", "2026-08-20", False,
     False, 1),
    ("17", False, False, "", "eol:nwl2023", "2026-08-20", True, True, 1),
    ("18-20 19", False, False, "hyphenated;spaced", "wordnet", "2026-08-26",
     False, False, 2),
)
#: the 12 detectors in C.DETECTORS' order, then scowl_tier, title screen
EVIDENCE_ROWS = {
    "10": ([1, 0, 0, -1, 0, 1, 0, 0, 0, 0, 0, 0], 50, 1),
    "11": ([0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
    "12": ([0, 1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1], 35, 0),
    "15-16": ([0, 0, 0, 1, -1, 0, -1, -1, -1, -1, -1, -1], -1, 0),
    "17": ([0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1, 0], 0, 0),
}
#: what the release layer must derive (AT-UR1-10)
EXPECTED = {
    "10": ("plain", "wordnet;hunspell_en_GB;scowl", 3, True, False),
    "11": ("plain", "", 0, False, False),
    "12": ("apostrophe-form;s-final",
           "wiktionary_english;hunspell_en_GB;scowl", 3, None, None),
    "13 14": ("spaced", "wordnet;wiktionary_english", 2, None, None),
    "15-16": ("hyphenated", "web2a", 1, None, None),
    "18-20 19": ("hyphenated;spaced", "wordnet", 1, None, None),
}
CONTROLS = {"91"}
LEDGER_OUTSIDE = "90"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(root: Path, *, panel_count_of_11: int = 0) -> B.VersionSpec:
    """The digit fixture's layers, records, restricted split, and ledger."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    data, rec = root / "data", root / "records"
    data.mkdir(parents=True)
    rec.mkdir()
    cols = list(zip(*PIN_ROWS))
    spaced = [t > 1 for t in cols[8]]
    nulls = [None] * len(PIN_ROWS)
    pin = pa.table({
        "word": list(cols[0]), "eol": list(cols[1]),
        "eol_universe": list(cols[2]), "classes": list(cols[3]),
        "sources": list(cols[4]), "intake_date": list(cols[5]),
        "c4_addition": list(cols[6]), "is_restricted": list(cols[7]),
        "token_count": pa.array(cols[8], pa.int32()),
        "c015_addition": spaced,
        "wn_instance": pa.array([False if s else None for s in spaced],
                                pa.bool_()),
        "wn_capitalized": pa.array([False if s else None for s in spaced],
                                   pa.bool_()),
        "wk_proper_noun": pa.array(nulls, pa.bool_()),
        "wk_flags": pa.array(nulls, pa.string())})
    pq.write_table(pin, data / "pin.parquet")
    counts = {w: EXPECTED.get(w, (None, None, 1))[2] for w in cols[0]}
    counts["11"] = panel_count_of_11
    prov = pa.table({
        "word": list(cols[0]),
        "intake_layer": ["eol_valid", "eol_invalid", "c1_exceptions",
                         "spaced_c015", "c1_exceptions", "c4_additions",
                         "spaced_c015"],
        "intake_kind": ["obtained", "generated", "derived", "derived",
                        "derived", "derived", "derived"],
        "intake_channels": ["eol:wordnet", "eol:synthetic-engine",
                            "census:scowl", "spaced:wordnet",
                            "census:web2a", "audit:nwl2023",
                            "spaced:wordnet"],
        "eol_phase1_tier": ["valid", "none", "none", "none", "none", "none",
                            "none"],
        "eol_record": ["valid-dict", "invalid-dict", "none", "none", "none",
                       "none", "none"],
        "eol_synthetic_category": [None, "General", None, None, None, None,
                                   None],
        "eol_synthetic_engine_inferred": [None, "affixation/plural", None,
                                          None, None, None, None],
        "panel_count": pa.array([counts[w] for w in cols[0]], pa.int16()),
        "gb_type": pa.array([None if s else True for s in spaced],
                            pa.bool_()),
        "wordfreq_scored": pa.array([None if s else False for s in spaced],
                                    pa.bool_()),
        "wikt_title_any": pa.array([None if s else False for s in spaced],
                                   pa.bool_()),
        "provenance_class": ["channel_and_containment"] * len(PIN_ROWS)})
    pq.write_table(prov, data / "provenance.parquet")
    singles = [w for w in cols[0] if w in EVIDENCE_ROWS]
    ev = {"word": singles, "is_restricted": [w == "17" for w in singles]}
    for i, name in enumerate(C.DETECTORS):
        ev[name] = pa.array([EVIDENCE_ROWS[w][0][i] for w in singles],
                            pa.int8())
    ev["scowl_tier"] = pa.array([EVIDENCE_ROWS[w][1] for w in singles],
                                pa.int16())
    ev["wikt_title_screen"] = pa.array([EVIDENCE_ROWS[w][2] for w in singles],
                                       pa.int8())
    pq.write_table(pa.table(ev), data / "evidence.parquet")
    feats = {"word": singles}
    for k, (name, kind, _m, _n) in enumerate(C.FEATURES):
        values = [float(k + i) / 4 for i in range(len(singles))]
        feats[name] = (pa.array([v > 1 for v in values]) if kind == "bool"
                       else pa.array([int(v) for v in values], pa.int8())
                       if kind == "int8" else
                       pa.array([int(v) for v in values], pa.int16())
                       if kind == "int16" else pa.array(values, pa.float32()))
    pq.write_table(pa.table(feats), data / "features.parquet")
    pin_record = rec / "pin.json"
    pin_record.write_text(json.dumps({
        "counts": {"v2_rows": len(PIN_ROWS), "restricted_rows": 1,
                   "spaced_additions": sum(spaced), "eol_valid": 1},
        "schema_columns": list(C.PIN_LAYER_COLUMNS),
        "artifacts": {"universe_v2_parquet_sha256":
                      _sha(data / "pin.parquet")}}))
    (rec / "provenance.json").write_text(json.dumps({
        "artifact": {"sha256": _sha(data / "provenance.parquet")},
        "inputs": {"features_parquet_sha256":
                   _sha(data / "features.parquet")}}))
    (rec / "evidence.json").write_text(json.dumps({
        "artifacts": {"evidence_parquet_sha256":
                      _sha(data / "evidence.parquet")}}))
    with open(root / "restricted.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["word"], ["17"]])
    with open(root / "ledger.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([[LEDGER_OUTSIDE, "obtained"],
                                 ["10", "obtained"]])
    (rec / "ledger_manifest.json").write_text(
        json.dumps({"columns": ["word", "kind"]}))
    return B.VersionSpec(
        version="v0.1", pin_entry="the fixture", pin_record=pin_record,
        layers=(B.Layer("pin", data / "pin.parquet", pin_record,
                        ("artifacts", "universe_v2_parquet_sha256")),
                B.Layer("provenance", data / "provenance.parquet",
                        rec / "provenance.json", ("artifact", "sha256")),
                B.Layer("evidence", data / "evidence.parquet",
                        rec / "evidence.json",
                        ("artifacts", "evidence_parquet_sha256")),
                B.Layer("features", data / "features.parquet",
                        rec / "provenance.json",
                        ("inputs", "features_parquet_sha256"))),
        restricted_csv=root / "restricted.csv", ledger_csv=root / "ledger.csv",
        ledger_manifest=rec / "ledger_manifest.json",
        out_dir=root / "release" / "v0.1", record_out=root / "release.json",
        projection="full")


def build_fixture(root: Path, **kw) -> tuple[B.VersionSpec, dict]:
    spec = make_fixture(root, **kw)
    record = B.build(spec, controls=CONTROLS, today="2026-09-26",
                     log=lambda *a: None)
    return spec, record


@pytest.fixture(scope="module")
def fixture_release(tmp_path_factory):
    import pyarrow.parquet as pq
    spec, record = build_fixture(tmp_path_factory.mktemp("release"))
    tables = {f["config"]: pq.read_table(spec.out_dir / f["path"])
              for f in record["files"]}
    return spec, record, tables


@pytest.fixture(scope="module")
def real_release():
    """The v2.0 release files, where data/ exists; None in a clone."""
    import pyarrow.parquet as pq
    if not IN_REPO:
        return None
    spec = B.resolve("v2.0")
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    missing = [f["path"] for f in record["files"]
               if not (spec.out_dir / f["path"]).exists()]
    if missing:
        pytest.fail(f"data/ exists but the release files {missing} do not; "
                    "build them (python3 -m research.release.build_release "
                    "--version v2.0)")
    for f in record["files"]:
        assert _sha(spec.out_dir / f["path"]) == f["sha256"], f["path"]
    tables = {f["config"]: pq.read_table(spec.out_dir / f["path"])
              for f in record["files"]}
    return spec, record, tables


def _restricted(spec: B.VersionSpec, record: dict) -> set[str]:
    return B.read_restricted(spec, record["pin_counts"]["restricted_rows"])


def _nothing_left(spec: B.VersionSpec) -> None:
    """A failed build leaves no staging directory, no output directory,
    and no record (C-079 line 1, F1)."""
    assert not (spec.out_dir.parent / f".staging-{spec.out_dir.name}"
                ).exists()
    assert not spec.out_dir.exists() and not spec.record_out.exists()


def _at_write(monkeypatch, name: str, change) -> None:
    """Patch build_release.write_file at the serialization boundary: the
    table written to `name` is `change(table)`; every other file is
    written as the build hands it over."""
    write = B.write_file

    def patched(table, path, *args, **kwargs):
        return write(change(table) if path.name == name else table, path,
                     *args, **kwargs)
    monkeypatch.setattr(B, "write_file", patched)


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

def test_at_ur1_1_no_restricted_row_or_word_in_any_file(fixture_release,
                                                        real_release):
    import pyarrow as pa
    spec, record, tables = fixture_release
    for config, table in tables.items():
        assert "17" not in table["word"].to_pylist(), config
        B.assert_shippable(table, {"17"}, config)
    leaked = tables["universe"]
    with pytest.raises(B.ReleaseError, match="restricted word"):
        B.assert_shippable(leaked, {"10"}, "the guard")
    flagged = leaked.set_column(
        leaked.column_names.index("is_restricted"), "is_restricted",
        pa.array([True] + [False] * (leaked.num_rows - 1)))
    with pytest.raises(B.ReleaseError, match="is_restricted true"):
        B.assert_shippable(flagged, set(), "the guard")
    if real_release:
        rspec, rrecord, rtables = real_release
        restricted = _restricted(rspec, rrecord)
        for config, table in rtables.items():
            B.assert_shippable(table, restricted, config)


def test_at_ur1_2_the_joins_are_one_row_per_word_and_lose_no_row(
        fixture_release, real_release, tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    spec, record, tables = fixture_release
    u = tables["universe"]
    assert u["word"].to_pylist() == [r[0] for r in PIN_ROWS if not r[7]]
    assert tables["features"]["word"].to_pylist() == ["10", "11", "12",
                                                      "15-16"]
    B.assert_nulls(u, C.UNIVERSE_NULLABLE, "fixture")
    assert record["assertions"]["universe"]["AT-UR1-2"][
        "rows_in_pin_order"] == u.num_rows
    assert record["assertions"]["features"]["AT-UR1-2"][
        "columns_without_nulls"] == len(C.FEATURES_COLUMNS)
    pin = pq.read_table(spec.layers[0].path)
    prov = pq.read_table(spec.layers[1].path)
    ev = pq.read_table(spec.layers[2].path)
    with pytest.raises(B.ReleaseError, match="not unique"):
        B.assemble_universe(pin, pa.concat_tables([prov, prov.slice(0, 1)]),
                            ev, 6)
    with pytest.raises(B.ReleaseError, match="without a provenance row"):
        B.assemble_universe(pin, prov.slice(1), ev, 6)
    with pytest.raises(B.ReleaseError, match="nulls in"):
        B.assert_nulls(u, frozenset(), "the guard")
    # F1, through build() with write_file patched at the serialization
    # boundary: the universe reversed at write fails the order assertion
    _at_write(monkeypatch, "universe.parquet", lambda t: t.take(
        pa.array(range(t.num_rows - 1, -1, -1))))
    reversed_spec = make_fixture(tmp_path / "reversed")
    with pytest.raises(B.ReleaseError, match="shippable words in order"):
        B.build(reversed_spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(reversed_spec)
    monkeypatch.undo()
    # the id half alone: the words in order, 2 ids exchanged at write
    def ids_exchanged(t):
        ids = t["id"].to_pylist()
        ids[0], ids[1] = ids[1], ids[0]
        return t.set_column(0, "id", pa.array(ids, pa.string()))
    _at_write(monkeypatch, "universe.parquet", ids_exchanged)
    ids_spec = make_fixture(tmp_path / "ids")
    with pytest.raises(B.ReleaseError, match="not the assembled ids"):
        B.build(ids_spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(ids_spec)
    monkeypatch.undo()

    # a null written into a never-null feature column fails the null
    # assertion (the feature layer's NaN is a value, never a null)
    def null_first(t):
        at = t.column_names.index("orthotactic_logp_total")
        values = t.column(at).to_pylist()
        values[0] = None
        return t.set_column(at, "orthotactic_logp_total",
                            pa.array(values, t.schema.field(at).type))
    _at_write(monkeypatch, "features.parquet", null_first)
    null_spec = make_fixture(tmp_path / "null")
    with pytest.raises(B.ReleaseError,
                       match="features: nulls in orthotactic_logp_total"):
        B.build(null_spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(null_spec)
    monkeypatch.undo()
    if real_release:
        rspec, rrecord, rtables = real_release
        pin = pq.read_table(rspec.layers[0].path,
                            columns=["word", "is_restricted"])
        ship = pin.filter(pc.invert(pin["is_restricted"]))
        ru = rtables["universe"]
        assert ru.num_rows == rrecord["pin_counts"]["shippable_rows"]
        assert pc.all(pc.equal(ru["word"], ship["word"])).as_py()
        B.assert_nulls(ru, C.UNIVERSE_NULLABLE, "universe")
        single = ru.filter(pc.equal(ru["token_count"], 1))
        assert pc.all(pc.equal(rtables["features"]["word"],
                               single["word"])).as_py()


def test_at_ur1_3_the_identifier_is_the_sha256_prefix_and_unique(
        fixture_release, real_release):
    import pyarrow as pa
    _spec, _record, tables = fixture_release
    for config, table in tables.items():
        B.assert_identifiers(table, config)
    assert B.word_id("10") == hashlib.sha256(b"10").hexdigest()[:16]
    u = tables["universe"]
    ids = u["id"].to_pylist()
    ids[0] = ids[1]
    with pytest.raises(B.ReleaseError, match="sha256 prefix"):
        B.assert_identifiers(u.set_column(0, "id", pa.array(ids)), "guard")
    # F2: a complete duplicated row, whose id is its own word's prefix,
    # passes the prefix check and reaches the uniqueness guard alone
    duplicated = pa.concat_tables([u, u.slice(0, 1)])
    with pytest.raises(B.ReleaseError, match="ids are not unique"):
        B.assert_identifiers(duplicated, "guard")
    if real_release:
        _rs, _rr, rtables = real_release
        for config in ("universe", "features"):
            B.assert_identifiers(rtables[config], config)


def test_at_ur1_4_spaced_rows_carry_null_where_the_layers_do_not_measure(
        fixture_release, real_release):
    import pyarrow as pa
    _spec, _record, tables = fixture_release
    u = tables["universe"]
    assert B.assert_spaced_na(u, "fixture")["spaced_rows"] == 2
    assert " " not in "".join(tables["features"]["word"].to_pylist())
    at = u.column_names.index("wordnet")
    values = u["wordnet"].to_pylist()
    values[u["word"].to_pylist().index("13 14")] = 1
    with pytest.raises(B.ReleaseError, match="null exactly"):
        B.assert_spaced_na(u.set_column(at, "wordnet",
                                        pa.array(values, pa.int8())), "guard")
    if real_release:
        _rs, rrecord, rtables = real_release
        got = B.assert_spaced_na(rtables["universe"], "universe")
        assert got["spaced_rows"] == rrecord["pin_counts"]["spaced_rows"]


def test_at_ur1_5_every_config_is_a_filter_of_the_same_rows(
        fixture_release, real_release):
    _spec, record, tables = fixture_release
    want = {"panel-listed": ["10", "12", "13 14", "15-16", "18-20 19"],
            "eol-valid": ["10"], "spaced": ["13 14", "18-20 19"],
            "exceptions": ["12", "15-16", "18-20 19"]}
    predicates = dict(B.FILTER_CONFIGS)
    stated = {f["config"]: f["predicate"] for f in record["files"]}
    for name, words in want.items():
        assert tables[name]["word"].to_pylist() == words, name
        assert stated[name] == predicates[name]
        B.assert_config(tables[name], tables["universe"], name)
    with pytest.raises(B.ReleaseError, match="filtered by its predicate"):
        B.assert_config(tables["spaced"].slice(1), tables["universe"],
                        "spaced")
    if real_release:
        _rs, _rr, rtables = real_release
        for name, _p in B.FILTER_CONFIGS:
            B.assert_config(rtables[name], rtables["universe"], name)


def test_at_ur1_6_no_study_material_posterior_or_ledger_row(
        fixture_release, real_release, tmp_path):
    import pyarrow as pa
    _spec, _record, tables = fixture_release
    for config, table in tables.items():
        want = C.FEATURES_COLUMNS if config == "features" \
            else C.UNIVERSE_COLUMNS
        B.assert_columns(table, want, config)
        B.assert_exclusions(table, CONTROLS, {LEDGER_OUTSIDE}, config)
    u = tables["universe"]
    with pytest.raises(B.ReleaseError, match="columns differ"):
        B.assert_columns(u.append_column(
            "p_word", pa.array([0.5] * u.num_rows)), C.UNIVERSE_COLUMNS, "g")
    with pytest.raises(B.ReleaseError, match="intake-ledger"):
        B.assert_exclusions(u, set(), {"10"}, "the guard")
    spec = make_fixture(tmp_path / "control")
    with pytest.raises(B.ReleaseError, match="synthetic control"):
        B.build(spec, controls={"11"}, log=lambda *a: None)
    assert not spec.record_out.exists() and not spec.out_dir.exists()
    _nothing_left(spec)          # and no staging directory (F1)
    if real_release:
        from research.inthewild.walled_terms import walled_terms
        rspec, _rr, rtables = real_release
        pin_words = set(rtables["universe"]["word"].to_pylist())
        outside = B.read_ledger_words(rspec) - pin_words
        controls = walled_terms()["controls"]
        for config, table in rtables.items():
            want = C.FEATURES_COLUMNS if config == "features" \
                else C.UNIVERSE_COLUMNS
            B.assert_columns(table, want, config)
            B.assert_exclusions(table, controls, outside, config)


def test_at_ur1_7_the_cards_every_figure_is_a_calculator_row():
    card = R.CARD.read_text(encoding="utf-8")
    template = R.TEMPLATE.read_text(encoding="utf-8")
    rows, tables = R.rows(), R.tables()
    assert R.template_literals(template) == []
    assert R.render(template, rows, tables) == card
    assert R.template_literals("rows 1,234 and 12.5% and 10294621 in 2026") \
        == ["1,234", "12.5%", "10294621"]
    # F3: the probes the audit found unguarded are caught, and the tokens
    # the stated rule excepts pass (C-079 line 1)
    for probe, want in (("123.", ["123"]), ("rows:123", ["123"]),
                        ("0.16 of", ["0.16"]), ("a ratio of 1.5", ["1.5"])):
        assert R.template_literals(probe) == want, probe
    for token in ("CC-BY-SA 4.0", "WordNet 3.0", "LGPL-2.1", "MPL-1.1",
                  "wordfreq 3.1.1", "Apache-2.0", "CC-BY-3.0",
                  "its record v3.0.2", "doi:10.5281/zenodo.7199437",
                  "PACKAGE_UR1.md §4.5", "the 2020 release."):
        assert R.template_literals(token) == [], token
    # F3 and F12: the audit's remainder is a row, rendered as a numeral
    audit = json.loads(R.AUDIT_RECONCILE_JSON.read_text(encoding="utf-8"))
    assert rows["audit_remainder"] == f"{audit['miss_union'] - audit['miss_in_frame_additions'] - audit['miss_beyond_frame']:,}"
    assert "a remainder of {{audit_remainder}};" in template
    assert f"a remainder of {rows['audit_remainder']};" in card
    record = json.loads(R.RECORD.read_text(encoding="utf-8"))
    upload = json.loads(R.UPLOAD.read_text(encoding="utf-8"))
    fails = verify._release_failures(
        card + "x", template.replace("{{rows_universe}}", "10,294,621"),
        rows, tables, R.render, R.template_literals,
        record,
        {"version": "v2.0", "dataset": B.DATASET, "canary": B.CANARY,
         "card_sha256": "", "record_sha256": "", "sources": {},
         "predicates": {}, "shippable_rows": 0, "spaced_rows": 0,
         "eol_valid": 0, "single_token_shippable": 0, "universe_columns": [],
         "features_columns": [], "assertion_fields": {},
         "restricted_rows": 0, "controls": 0, "ledger_outside": None},
        {}, {}, upload)
    assert any("literal figure" in f for f in fails)
    assert any("is not the rendering" in f for f in fails)
    assert any("does not tie" in f for f in fails)
    # F8: against the inputs check_release reads, which pass, a missing
    # assertion field and an altered upload inventory each fail alone, and
    # so does each tie of a count
    inputs = verify._release_inputs()
    assert verify._release_failures(**inputs) == []
    lacking = copy.deepcopy(inputs["record"])
    del lacking["assertions"]["universe"]["AT-UR1-6"]["control_hits"]
    assert verify._release_failures(**{**inputs, "record": lacking}) == [
        "release record: universe AT-UR1-6 lacks control_hits"]
    altered = {**inputs["upload"], "files": inputs["upload"]["files"][:3]}
    fails = verify._release_failures(**{**inputs, "upload": altered})
    assert len(fails) == 1 and "the upload's files does not tie" in fails[0]
    absent = {**inputs, "expected": {**inputs["expected"],
                                     "ledger_outside": None}}
    assert verify._release_failures(**absent) == []
    for config, at, key, change in (
            ("universe", "AT-UR1-1", "restricted_words_checked", 1),
            ("features", "AT-UR1-6", "controls_checked", 1),
            ("features", "AT-UR1-6", "ledger_words_outside_the_pin_checked", 1),
            ("universe", "AT-UR1-2", "rows_in_pin_order", -1),
            ("features", "AT-UR1-2", "columns_without_nulls", -1),
            ("eol-valid", "AT-UR1-1", "restricted_hits", 1),
            ("spaced", "AT-UR1-5", "undeclared", 0)):
        changed = copy.deepcopy(inputs["record"])
        block = changed["assertions"][config][at]
        block[key] = block.get(key, 0) + change
        for case in (inputs, absent):
            fails = verify._release_failures(**{**case, "record": changed})
            assert len(fails) == 1 and key in fails[0], (key, fails)
    # where the ledger and the pin are here the ledger's count is
    # recomputed, so a count the record repeats consistently but wrongly
    # fails in both blocks; in a clone it is the record's own count
    recount = inputs["expected"]["ledger_outside"]
    consistent = copy.deepcopy(inputs["record"])
    for config in ("universe", "features"):
        consistent["assertions"][config]["AT-UR1-6"][
            "ledger_words_outside_the_pin_checked"] += 1
    fails = verify._release_failures(**{**inputs, "record": consistent})
    if IN_REPO:
        assert recount == inputs["record"]["assertions"]["universe"][
            "AT-UR1-6"]["ledger_words_outside_the_pin_checked"]
        assert len(fails) == 2 and all(
            "ledger_words_outside_the_pin_checked" in f for f in fails)
    else:
        assert recount is None and fails == []
    # the build holds its own blocks to the same schema
    B.assert_schema(inputs["record"]["assertions"])
    with pytest.raises(B.ReleaseError, match="ASSERTION_FIELDS"):
        B.assert_schema(lacking["assertions"])
    assert verify.check_release() == []


class _Info:
    def __init__(self, private: bool, sha: str = "0" * 40):
        self.private, self.sha = private, sha


@pytest.fixture(autouse=True, scope="module")
def _data_is_the_temporary_root(tmp_path_factory):
    """N-6: a public build writes its private files only under data/ or
    private/; the digit fixtures build under the run's temporary root, which
    stands in for data/ in this module."""
    import os
    before = os.environ.get("CEOL_DATA")
    os.environ["CEOL_DATA"] = str(tmp_path_factory.getbasetemp())
    yield
    if before is None:
        del os.environ["CEOL_DATA"]
    else:
        os.environ["CEOL_DATA"] = before


class _FakeHub:
    """A stand-in hub client: records what would be sent."""

    def __init__(self, user="ryanjosephkamp", exists=True, private=True):
        self.user, self.exists, self.private = user, exists, private
        self.commits: list = []
        self.whoami_calls = 0

    def whoami(self):
        self.whoami_calls += 1
        return {"name": self.user}

    def repo_info(self, repo_id, repo_type=None):
        if not self.exists:
            from huggingface_hub.errors import RepositoryNotFoundError
            err = RepositoryNotFoundError.__new__(RepositoryNotFoundError)
            Exception.__init__(err, "not found")
            raise err
        return _Info(self.private)

    def list_repo_refs(self, repo_id, repo_type=None):
        return type("Refs", (), {"tags": [type("T", (), {"name": n})()
                                          for n in getattr(self, "tags", ())]})()

    def create_commit(self, *args, **kwargs):
        self.commits.append((args, kwargs))
        raise AssertionError("the stand-in hub must never be sent a commit")


def test_at_ur1_8_the_upload_refuses_a_public_dataset_and_a_wrong_account(
        monkeypatch):
    for hub, message in ((_FakeHub(private=False), "PUBLIC"),
                         (_FakeHub(user="someone-else"), "not 'ryanjosephkamp'"),
                         (_FakeHub(exists=False), "does not exist")):
        with pytest.raises(U.UploadRefused, match=message):
            U.check_hub(hub)
        assert hub.commits == []
    assert U.check_hub(_FakeHub()) == "0" * 40
    # the order: the hub is checked before anything is sent
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())
    monkeypatch.setattr(U, "preflight", lambda *a: [])
    # without the owner's word, v2.0 is never sent again
    hub = _FakeHub()
    with pytest.raises(U.UploadRefused, match="--owner-word"):
        U.upload("v2.0", hub, record_out=Path("/nonexistent/never.json"))
    assert hub.commits == [] and hub.whoami_calls == 0
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    hub = _FakeHub(private=False)
    with pytest.raises(U.UploadRefused, match="PUBLIC"):
        U.upload("v2.0", hub, record_out=Path("/nonexistent/never.json"))
    assert hub.commits == []



def test_the_upload_of_a_public_version_takes_its_card_and_refuses_as_v2_0_does(
        monkeypatch, tmp_path):
    """A public version's upload (gate G3 only) uses its own card and record,
    and checks the hub before anything is sent; the git object id it checks
    the text files by is git's."""
    import subprocess
    from research.release import public_card as Pc
    spec = B.resolve("v2.1")
    assert U.calculator(spec) is Pc and U.calculator(B.resolve("v2.0")) is R
    assert U.upload_record(spec).name == "hf_upload_v2.1.json"
    assert U.upload_record(B.resolve("v2.0")) == U.UPLOAD_RECORD
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())
    monkeypatch.setattr(U, "preflight", lambda *a: [])
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    for hub, message in ((_FakeHub(private=False), "PUBLIC"),
                         (_FakeHub(user="someone-else"), "not 'ryanjosephkamp'")):
        with pytest.raises(U.UploadRefused, match=message):
            U.upload("v2.1", hub, record_out=tmp_path / "never.json")
        assert hub.commits == [] and not (tmp_path / "never.json").exists()
    sample = tmp_path / "notice.md"
    sample.write_text("# NOTICES: a fixture\n", encoding="utf-8")
    git = subprocess.run(["git", "hash-object", str(sample)], capture_output=True,
                         text=True, check=True).stdout.strip()
    assert U.git_blob_id(sample) == git

def test_at_ur1_9_the_profile_regenerates_from_the_release_files(
        fixture_release, real_release, tmp_path):
    spec, _record, _tables = fixture_release
    first, plots = UP.compute(spec.out_dir, "v0.1")
    second, _ = UP.compute(spec.out_dir, "v0.1")
    assert UP.dumps(first) == UP.dumps(second)
    for name, (_title, cv) in plots.items():
        assert (P.decode_pixels(cv.png()) == cv.pixels).all(), name
        assert first["plots"][name]["pixels_sha256"] == cv.pixels_sha256()
    assert first["universe"]["rows"] == 6
    with pytest.raises(ValueError, match="no glyph"):
        P.text_mask("ß")
    # F2: the profile comparison check_release runs, reached by stand-ins
    plots_dir = tmp_path / "plots"
    plots_dir.mkdir()
    for name, (_title, cv) in plots.items():
        (plots_dir / name).write_bytes(cv.png())
    text = UP.dumps(first)
    assert verify._profile_failures(text, text, plots_dir,
                                    P.decode_pixels) == []
    stand_in = UP.dumps({**first, "version": "v0.2"})
    fails = verify._profile_failures(text, stand_in, plots_dir,
                                     P.decode_pixels)
    assert len(fails) == 1 and "does not re-derive" in fails[0] \
        and "version" in fails[0]
    name, (_title, cv) = sorted(plots.items())[0]
    cv.pixels[0, 0] = 255 - cv.pixels[0, 0]
    (plots_dir / name).write_bytes(cv.png())
    assert verify._profile_failures(text, text, plots_dir,
                                    P.decode_pixels) == [
        f"plots/{name} is not the plot profile.json records"]
    if real_release:
        rspec, _rr, _rt = real_release
        fresh, _p = UP.compute(rspec.out_dir, "v2.0")
        assert UP.dumps(fresh) == UP.PROFILE_JSON.read_text(encoding="utf-8")
        assert PE.dumps(PE.compute(rspec.out_dir, "v2.0")) == \
            PE.POS_JSON.read_text(encoding="utf-8")
        for name, meta in fresh["plots"].items():
            pixels = P.decode_pixels((UP.PLOTS_DIR / name).read_bytes())
            assert hashlib.sha256(pixels.tobytes()).hexdigest() == \
                meta["pixels_sha256"], name


def test_at_ur1_10_the_release_layer_re_derives_on_a_digit_fixture(
        fixture_release, real_release, tmp_path, monkeypatch):
    import pyarrow as pa
    _spec, _record, tables = fixture_release
    u = tables["universe"]
    got = {w: (c, s, n, g, us) for w, c, s, n, g, us in zip(
        *(u[k].to_pylist() for k in ("word", "class_explicit", "panel_sets",
                                     "panel_count", "variety_gb_not_us",
                                     "variety_us_not_gb")))}
    assert got == EXPECTED
    B.assert_release_layer(u, "fixture")
    with pytest.raises(B.ReleaseError, match="panel_count"):
        build_fixture(tmp_path / "count", panel_count_of_11=1)

    # F2: class_explicit mutated at write reaches assert_release_layer on
    # the written file inside build(), every earlier assertion passing
    def plain_everywhere(t):
        at = t.column_names.index("class_explicit")
        return t.set_column(at, "class_explicit",
                            pa.array(["plain"] * t.num_rows, pa.string()))
    _at_write(monkeypatch, "universe.parquet", plain_everywhere)
    class_spec = make_fixture(tmp_path / "class")
    with pytest.raises(B.ReleaseError,
                       match="universe: class_explicit does not re-derive"):
        B.build(class_spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(class_spec)
    monkeypatch.undo()
    if real_release:
        _rs, _rr, rtables = real_release
        B.assert_release_layer(rtables["universe"], "universe")


def test_at_ur1_11_the_version_parameter_and_its_refusals(tmp_path):
    assert B.resolve("v2.0").version == "v2.0"
    with pytest.raises(B.ReleaseError, match="pin record .* is absent"):
        B.resolve("v3.0")
    with pytest.raises(B.ReleaseError, match="unknown version"):
        B.resolve("v9.9")
    assert B.main(["--version", "v3.0"]) == 1
    assert B.main(["--version", "v9.9"]) == 1
    assert B.main(["--version", "v3.0", "--record-only"]) == 1
    # F4: the record states the size policy and each file's measured
    # uncompressed sizes; --record-only rewrites the record of files
    # already built, re-running the assertions, and writes no file
    spec, record = build_fixture(tmp_path / "record")
    assert record["bounds"] == B.bounds()
    for f in record["files"]:
        assert f["measured_uncompressed_bytes"] >= \
            f["largest_row_group_uncompressed_bytes"] > 0
    hashes = {f["path"]: _sha(spec.out_dir / f["path"])
              for f in record["files"]}
    older = json.loads(spec.record_out.read_text(encoding="utf-8"))
    for f in older["files"]:
        del f["measured_uncompressed_bytes"]
        del f["largest_row_group_uncompressed_bytes"]
    del older["bounds"]["policy"]
    del older["assertions"]["universe"]["AT-UR1-2"]["rows_in_pin_order"]
    spec.record_out.write_text(json.dumps(older, indent=2) + "\n",
                               encoding="utf-8")
    rewritten = B.record_only(spec, controls=CONTROLS, today="2026-09-27",
                              log=lambda *a: None)
    assert {k: v for k, v in rewritten.items()
            if k != "record_rewritten_on"} == record
    assert rewritten["record_rewritten_on"] == "2026-09-27"
    assert json.loads(spec.record_out.read_text(encoding="utf-8")) == \
        rewritten
    assert {f["path"]: _sha(spec.out_dir / f["path"])
            for f in record["files"]} == hashes
    # a recorded count that does not re-derive: refused, nothing written
    wrong = copy.deepcopy(record)
    wrong["assertions"]["spaced"]["AT-UR1-5"]["rows"] += 1
    spec.record_out.write_text(json.dumps(wrong, indent=2) + "\n",
                               encoding="utf-8")
    before = spec.record_out.read_bytes()
    with pytest.raises(B.ReleaseError, match="do not re-derive"):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    assert spec.record_out.read_bytes() == before
    # a file whose bytes differ from the record's: refused, the record and
    # the files left as they were
    target = spec.out_dir / "eol-valid.parquet"
    target.write_bytes(target.read_bytes() + b"\0")
    before = spec.record_out.read_bytes()
    with pytest.raises(B.ReleaseError, match="not the file the record names"):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    assert spec.record_out.read_bytes() == before


# ---------------------------------------------------------------------------
# AT-UR1-12: the public projection (D-010, D-011), on the digit fixture
# ---------------------------------------------------------------------------

def make_public_fixture(root: Path) -> B.VersionSpec:
    """The digit fixture as a public version, its provenance layer changed
    so that the projection holds 2 rows back and withholds 1 row's channel:
    "15-16", listed only by web2a and seen only through census:web2a, held
    by no corpus (tier 2); "11", seen only through the withheld COCA label
    and held by nothing (a withheld channel its only evidence); and "10",
    seen only through the tournament list and listed by published sets."""
    import dataclasses
    import pyarrow as pa
    import pyarrow.parquet as pq
    spec = make_fixture(root)
    path = root / "data" / "provenance.parquet"
    prov = pq.read_table(path).to_pylist()
    for row in prov:
        if row["word"] == "15-16":
            row["gb_type"] = False
        if row["word"] == "11":
            row.update(intake_channels="eol:coca_frequency", gb_type=False,
                       provenance_class="channel_only")
        if row["word"] == "10":
            row["intake_channels"] = "eol:tournament-list"
    pq.write_table(pa.Table.from_pylist(prov, schema=pq.read_schema(path)), path)
    record = root / "records" / "provenance.json"
    body = json.loads(record.read_text())
    body["artifact"]["sha256"] = _sha(path)
    record.write_text(json.dumps(body))
    notices = root / "NOTICES.md"
    notices.write_text("# NOTICES: the digit fixture\n", encoding="utf-8")
    # the model-basis layer: "10", a row of the EOL's valid list, decided
    # through the verification pipeline
    basis = root / "data" / "model_basis.parquet"
    pq.write_table(pa.table({"word": ["10"], "model_basis": ["model_pipeline"]}), basis)
    basis_record = root / "records" / "model_basis.json"
    basis_record.write_text(json.dumps({"artifact": {"sha256": _sha(basis)}}))
    layers = spec.layers + (B.Layer("model_basis", basis, basis_record,
                                    ("artifact", "sha256")),)
    # the digit fixture's held-back reasons count 1 row each, so its floor
    # is 1; a release's is 10 (docs/ANALYSIS_PLAN.md §9 rule 2). Its labels
    # hold 1 or 2 rows each, so the reach guard is off here and tested on its
    # own case below
    return dataclasses.replace(spec, projection="public", notices=notices, layers=layers,
                               suppression_floor=1, reach_threshold=1.01)


def test_at_ur1_12_the_public_projection_on_the_digit_fixture(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    from research.release import withholding as W
    spec = make_public_fixture(tmp_path / "ok")
    record = B.build(spec, controls=CONTROLS, today="2026-10-19", log=lambda *a: None)
    universe = pq.read_table(spec.out_dir / "universe.parquet")
    # 6 shippable rows, 2 held back
    assert universe.num_rows == 4 and record["rows_by_config"]["universe"] == 4
    assert universe.column_names == list(W.PUBLISHED_UNIVERSE_COLUMNS) + ["model_or_engine"]
    assert sorted(universe["word"].to_pylist()) == ["10", "12", "13 14", "18-20 19"]
    by_word = {r["word"]: r for r in universe.to_pylist()}
    assert by_word["10"]["intake_channels"] == W.CHANNEL_WITHHELD
    assert by_word["10"]["provenance_class"] == "containment_only"
    assert by_word["12"]["panel_sets"] == "wiktionary_english;hunspell_en_GB;scowl"
    # the model-or-engine column (AT-UR1-13): "10" decided through the
    # pipeline; "11", the generated row, is held back; the rest none
    assert {w: r["model_or_engine"] for w, r in by_word.items()} == {
        "10": "model_pipeline", "12": "none", "13 14": "none", "18-20 19": "none"}
    assert record["assertions"]["universe"]["AT-UR1-13"]["rows_by_value"] == {
        "engine_generated": 0, "model_pipeline": 1, "model_alone": 0, "none": 3}
    # the held-back rows are in the private file beside the release, never in it
    held = pq.read_table(spec.out_dir.parent / f"{spec.out_dir.name}.held-back.parquet")
    assert sorted((r["word"], r["reason"]) for r in held.to_pylist()) == [
        ("11", "withheld_channel"), ("15-16", "tier_2")]
    block = record["projection"]["held_back"]
    assert block["rows"] == 2 and block["by_reason"] == {
        "tier_2": 1, "withheld_channel": 1, "withheld_sources": 0}
    # every file carries the version's metadata; NOTICES.md ships beside them
    for f in record["files"]:
        meta = pq.read_schema(spec.out_dir / f["path"]).metadata
        assert {k: meta[k] for k in B.file_metadata(spec.version)} \
            == B.file_metadata(spec.version), f["path"]
        assert set(record["assertions"][f["config"]]) >= {"AT-UR1-12"}
    assert (spec.out_dir / "NOTICES.md").read_text(encoding="utf-8").startswith("# NOTICES")
    assert record["documents"][0]["sha256"] == _sha(spec.out_dir / "NOTICES.md")
    assert record["visibility"].startswith("private until the owner's word")
    # the record-only path re-derives the same record
    again = B.record_only(spec, controls=CONTROLS, today="2026-10-20", log=lambda *a: None)
    assert {k: v for k, v in again.items() if k != "record_rewritten_on"} == record

    # a withheld label that reaches a written file fails AT-UR1-12, and the
    # failed build leaves nothing
    import pyarrow as pa
    bad = make_public_fixture(tmp_path / "bad")

    def leak(table):
        values = table["intake_channels"].to_pylist()
        values[0] = "eol:wikipedia;eol:collins"
        return table.set_column(table.column_names.index("intake_channels"),
                                "intake_channels", pa.array(values))
    _at_write(monkeypatch, "universe.parquet", leak)
    with pytest.raises(B.ReleaseError, match="withheld list or label"):
        B.build(bad, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(bad)
    assert not (bad.out_dir.parent / f"{bad.out_dir.name}.held-back.parquet").exists()
    monkeypatch.undo()

    # a file without the version's metadata fails AT-UR1-12 (a filter
    # config inherits the universe file's, so it is stripped here)
    plain = make_public_fixture(tmp_path / "plain")
    _at_write(monkeypatch, "spaced.parquet",
              lambda table: table.replace_schema_metadata(None))
    write = B.write_file
    monkeypatch.setattr(B, "write_file", lambda table, path, metadata=None:
                        write(table, path, None if path.name == "spaced.parquet" else metadata))
    with pytest.raises(B.ReleaseError, match="key-value metadata"):
        B.build(plain, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(plain)
    monkeypatch.undo()

    # a public version without its NOTICES file is refused before anything is written
    import dataclasses
    missing = dataclasses.replace(make_public_fixture(tmp_path / "missing"),
                                  notices=tmp_path / "absent.md")
    with pytest.raises(B.ReleaseError, match="absent"):
        B.build(missing, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(missing)


def test_the_v2_1_spec_is_v2_0_s_layers_and_the_model_basis_put_through_the_projection():
    v20, v21 = B.resolve("v2.0"), B.resolve("v2.1")
    assert not v20.public and v21.public
    # v2.0's 4 layers, then the model-basis layer of step 3
    assert v21.layers[:4] == v20.layers and v21.pin_record == v20.pin_record
    assert [x.name for x in v21.layers[4:]] == ["model_basis"]
    assert v21.out_dir.name == "ceol-universe-v2.1"
    assert B.profile(v21).columns == B.PUBLIC.columns
    # v2.0, a released version, is built as it always was (rule 4)
    assert B.profile(v20) is B.FULL and B.assertion_fields("universe") \
        == B.ASSERTION_FIELDS["universe"]



# ---------------------------------------------------------------------------
# The lead's review of PR 4 (S1 to S6, S8, S10, N2, N6)
# ---------------------------------------------------------------------------

def test_every_known_version_but_v2_0_is_public():
    """S3: a version is public unless it says otherwise, and only v2.0 does."""
    for name, spec in B.versions().items():
        assert spec.public == (name != "v2.0"), name
    import dataclasses
    fields = {f.name: f.default for f in dataclasses.fields(B.VersionSpec)}
    assert fields["projection"] == "public"


def test_a_public_record_names_no_held_row_and_no_hash_of_the_private_file(tmp_path):
    """S1 and S10: the record counts the held-back rows and never lists them,
    by word or by id, and holds no hash of their file; the private sidecar
    beside the file does; the release directory holds the record's files and
    NOTICES.md and nothing else."""
    spec = make_public_fixture(tmp_path)
    record = B.build(spec, controls=CONTROLS, log=lambda *a: None)
    text = spec.record_out.read_text(encoding="utf-8")
    held_file = spec.out_dir.parent / f"{spec.out_dir.name}.held-back.parquet"
    sidecar = json.loads((spec.out_dir.parent / f"{spec.out_dir.name}.held-back.json")
                         .read_text(encoding="utf-8"))
    import pyarrow.parquet as pq
    for word in pq.read_table(held_file)["word"].to_pylist():
        assert f'"{word}"' not in text and B.word_id(word) not in text
    assert sidecar["sha256"] == _sha(held_file) and sidecar["sha256"] not in text
    import re
    assert re.search(r"[0-9a-f]{64}", json.dumps(record["projection"])) is None
    assert {p.name for p in spec.out_dir.iterdir()} == \
        {f["path"] for f in record["files"]} | {"NOTICES.md"}


def test_a_held_back_row_d_011_does_not_cover_refuses_the_build(tmp_path):
    """S2: "11", seen only through census:web2 and listed by nothing, would be
    held back for no reason D-011 rules; the build refuses."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    spec = make_public_fixture(tmp_path)
    path = tmp_path / "data" / "provenance.parquet"
    prov = pq.read_table(path).to_pylist()
    for row in prov:
        if row["word"] == "11":
            row["intake_channels"] = "census:web2"
    pq.write_table(pa.Table.from_pylist(prov, schema=pq.read_schema(path)), path)
    rec = tmp_path / "records" / "provenance.json"
    body = json.loads(rec.read_text())
    body["artifact"]["sha256"] = _sha(path)
    rec.write_text(json.dumps(body))
    with pytest.raises(B.ReleaseError, match="D-011 and D-012 do not rule"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def _public_table(version: str, **columns):
    import pyarrow as pa
    base = {"word": ["10"], "sources": ["eol_universe@c1139698"],
            "intake_channels": ["eol:wikipedia"], "panel_sets": ["wordnet"],
            "provenance_class": ["channel_and_containment"]}
    base.update(columns)
    return pa.table(base).replace_schema_metadata(B.file_metadata(version))


@pytest.mark.parametrize("case, columns, metadata, message", [
    ("a held-back row present", {"word": ["11"]}, None, "held-back row"),
    ("the marker beside another label",
     {"intake_channels": ["eol:channel-withheld;eol:wikipedia"]}, None, "withheld list or label"),
    ("a withheld column present", {"web2": [1]}, None, "withheld columns"),
    ("a label form outside the vocabulary", {"sources": ["sowpods"]}, None, "vocabulary"),
    ("a new channel label", {"intake_channels": ["eol:new-source"]}, None, "vocabulary"),
    ("a withheld channel with no public evidence",
     {"intake_channels": ["eol:channel-withheld"], "provenance_class": ["neither"]},
     None, "should be held back"),
    ("an extra metadata key", {}, {b"stale.key": b"1"}, "key-value metadata"),
    ("a census row with empty sources",
     {"intake_layer": ["c1_exceptions"], "sources": [""]}, None, "empty sources"),
    ("an audit row with empty sources",
     {"intake_layer": ["c4_additions"], "sources": [""]}, None, "empty sources"),
])
def test_each_failure_of_at_ur1_12(case, columns, metadata, message):
    """S4 and S10: AT-UR1-12 is an allow list and holds the row invariant and
    the exact metadata."""
    table = _public_table("v2.1", **columns)
    if metadata:
        table = table.replace_schema_metadata({**table.schema.metadata, **metadata})
    assert B.assert_public(_public_table("v2.1"), "universe", {"11"}, "v2.1")
    with pytest.raises(B.ReleaseError, match=message):
        B.assert_public(table, "universe", {"11"}, "v2.1")


def test_a_held_back_reason_under_the_floor_refuses_the_build(tmp_path):
    """N2: a reason counting fewer rows than the floor cannot be published."""
    import dataclasses
    spec = dataclasses.replace(make_public_fixture(tmp_path), suppression_floor=10)
    with pytest.raises(B.ReleaseError, match="fewer than 10"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_record_only_re_derives_the_projection_and_checks_the_private_file(tmp_path):
    """S6: a recorded projection that does not re-derive, or a held-back file
    its sidecar does not name, is refused, and the record is left as it was."""
    spec = make_public_fixture(tmp_path)
    B.build(spec, controls=CONTROLS, log=lambda *a: None)
    before = spec.record_out.read_text(encoding="utf-8")
    body = json.loads(before)
    body["projection"]["held_back"]["by_reason"] = {"tier_2": 2, "withheld_channel": 0}
    spec.record_out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(B.ReleaseError, match="projection does not re-derive"):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    spec.record_out.write_text(before, encoding="utf-8")
    sidecar = spec.out_dir.parent / f"{spec.out_dir.name}.held-back.json"
    side = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar.write_text(json.dumps({**side, "sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(B.ReleaseError, match="sidecar"):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    assert spec.record_out.read_text(encoding="utf-8") == before


def test_the_held_back_file_never_lands_in_a_committed_tree(tmp_path):
    """N6 and N-6: only data/ or private/ may hold the private files."""
    from safeguards import locations
    root = B.REPO.parent
    for elsewhere in (root / "docs", root, Path("/private/tmp/ceol-elsewhere"),
                      root.parent / "another-checkout" / "data"):
        with pytest.raises(B.ReleaseError, match="outside data/"):
            B.refuse_a_committed_tree(elsewhere / "x.held-back.parquet")
    B.refuse_a_committed_tree(locations.data_dir() / "release" / "x.held-back.parquet")
    B.refuse_a_committed_tree(locations.private_dir() / "x.held-back.parquet")
    B.refuse_a_committed_tree(tmp_path / "x.held-back.parquet")  # data/ here


def test_the_shipped_notices_is_held_to_its_generator(monkeypatch):
    """S8: the generated NOTICES ships only as notices.py prints it, and an
    input absent from the build machine refuses the build."""
    from research.release import notices as N
    spec = B.resolve("v2.1")
    monkeypatch.setattr(N, "inputs", lambda: {})
    monkeypatch.setattr(N, "render", lambda version, texts: "# NOTICES: another text\n")
    with pytest.raises(B.ReleaseError, match="not what notices.py prints"):
        B.notices_source(spec)

    def absent():
        raise N.InputAbsent("wordnet.zip is not on this machine")
    monkeypatch.setattr(N, "inputs", absent)
    with pytest.raises(B.ReleaseError, match="cannot be checked"):
        B.notices_source(spec)
# ---------------------------------------------------------------------------
# The carried code items
# ---------------------------------------------------------------------------

def _rewrite(spec: B.VersionSpec, change) -> bytes:
    body = json.loads(spec.record_out.read_text(encoding="utf-8"))
    change(body)
    spec.record_out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return spec.record_out.read_bytes()


@pytest.mark.parametrize("case, change, message", [
    ("a config missing from the inventory",
     lambda r: r["files"].pop(), "file inventory"),
    ("a config the build does not make",
     lambda r: r["files"].append({**r["files"][0], "config": "extra"}), "file inventory"),
    ("a file named for another config",
     lambda r: r["files"][1].update(path="universe.parquet"), "names the file"),
    ("pin_counts that drifted",
     lambda r: r["pin_counts"].update(eol_valid=r["pin_counts"]["eol_valid"] + 1),
     "pin_counts do not re-derive"),
    ("rows_by_config that drifted",
     lambda r: r["rows_by_config"].update(spaced=r["rows_by_config"]["spaced"] + 1),
     "rows_by_config do not re-derive"),
])
def test_record_only_validates_the_inventory_and_re_derives_its_counts(
        tmp_path, case, change, message):
    """F1: each refusal isolated, the record left as it was."""
    spec, _record = build_fixture(tmp_path)
    before = _rewrite(spec, change)
    with pytest.raises(B.ReleaseError, match=message):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    assert spec.record_out.read_bytes() == before, case


def test_a_failed_promotion_leaves_nothing(tmp_path, monkeypatch):
    """F2: the promotion is inside the protected block, so a rename that
    fails removes the staging directory and leaves no file and no record."""
    spec = make_fixture(tmp_path)
    rename = Path.rename

    def refuse(self, target):
        if Path(target) == spec.out_dir:
            raise OSError("the promotion is refused here")
        return rename(self, target)
    monkeypatch.setattr(Path, "rename", refuse)
    with pytest.raises(OSError, match="promotion is refused"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_a_removal_that_fails_is_reported(tmp_path, monkeypatch):
    """F2: a failed build whose staging cannot be removed says so; the
    failure is never ignored."""
    spec = make_fixture(tmp_path)
    _at_write(monkeypatch, "spaced.parquet", lambda table: table.slice(1))
    rmtree = B.shutil.rmtree

    def failing(path, onerror=None, **kw):
        if onerror is not None:
            onerror(None, str(path), (OSError, OSError("held open"), None))
            return None
        return rmtree(path, **kw)
    monkeypatch.setattr(B.shutil, "rmtree", failing)
    with pytest.raises(B.ReleaseError, match="could not be removed") as err:
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    assert "held open" in str(err.value)
    assert isinstance(err.value.__cause__, B.ReleaseError)
    monkeypatch.undo()
    B.shutil.rmtree(spec.out_dir.parent / f".staging-{spec.out_dir.name}")
    _nothing_left(spec)


def test_a_failure_at_write_that_is_not_a_release_error_leaves_nothing(tmp_path, monkeypatch):
    """F5, the first negative: an OSError at write propagates as itself."""
    spec = make_fixture(tmp_path)
    write = B.write_file

    def broken(table, path, *args, **kwargs):
        if path.name == "features.parquet":
            raise OSError("the disk refused the write")
        return write(table, path, *args, **kwargs)
    monkeypatch.setattr(B, "write_file", broken)
    with pytest.raises(OSError, match="disk refused"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_a_file_that_changes_between_the_record_only_hashes_is_refused(tmp_path, monkeypatch):
    """F5, the second negative: the files are hashed again before the
    record is rewritten, and a change refuses the rewrite."""
    spec, _record = build_fixture(tmp_path)
    before = spec.record_out.read_bytes()
    bounds = B.bounds

    def touch_then_bound():
        target = spec.out_dir / "eol-valid.parquet"
        target.write_bytes(target.read_bytes() + b"\0")
        return bounds()
    monkeypatch.setattr(B, "bounds", touch_then_bound)
    with pytest.raises(B.ReleaseError, match="changed while its record was rewritten"):
        B.record_only(spec, controls=CONTROLS, log=lambda *a: None)
    assert spec.record_out.read_bytes() == before


def test_an_undeclared_field_reaching_the_schema_check_fails_the_build(tmp_path, monkeypatch):
    """F5, the third negative: the build's own schema check refuses a block
    with a field ASSERTION_FIELDS does not declare, and nothing is kept."""
    spec = make_fixture(tmp_path)
    universe = B.universe_assertions

    def with_extra(*args, **kwargs):
        out = universe(*args, **kwargs)
        out["AT-UR1-3"]["undeclared"] = 0
        return out
    monkeypatch.setattr(B, "universe_assertions", with_extra)
    with pytest.raises(B.ReleaseError, match="ASSERTION_FIELDS"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_a_failure_after_the_promotion_leaves_nothing(tmp_path, monkeypatch):
    """F2: a public build that fails after its directory is promoted (the
    held-back file refused its place) removes the promoted directory and
    the staged held-back file, and writes no record."""
    spec = make_public_fixture(tmp_path)
    held_out = spec.out_dir.parent / f"{spec.out_dir.name}.held-back.parquet"
    replace = Path.replace

    def refuse(self, target):
        if Path(target) == held_out:
            raise OSError("the held-back file is refused its place")
        return replace(self, target)
    monkeypatch.setattr(Path, "replace", refuse)
    with pytest.raises(OSError, match="refused its place"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)
    assert not held_out.exists()
    assert not (spec.out_dir.parent / f".staging-{held_out.name}").exists()


# ---------------------------------------------------------------------------
# v2.1's build: the sample config, the withheld features,
# the code's identity
# ---------------------------------------------------------------------------

def test_a_public_build_adds_the_sample_config_and_withholds_the_reference_features(
        tmp_path, monkeypatch):
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from research.release import withholding as W
    spec = make_public_fixture(tmp_path)
    # the digit fixture is too small for a 2-digit prefix: take the first
    # hexadecimal digit of a shipping row's id
    prefix = B.word_id("12")[0]
    monkeypatch.setattr(B, "SAMPLE_PREFIX", prefix)
    record = B.build(spec, controls=CONTROLS, today="2026-10-19", log=lambda *a: None)
    assert [f["config"] for f in record["files"]] == B.PUBLIC.configs
    assert B.PUBLIC.configs[-1] == "sample"
    universe = pq.read_table(spec.out_dir / "universe.parquet")
    sample = pq.read_table(spec.out_dir / "sample.parquet")
    assert sample.num_rows >= 1 and "12" in sample["word"].to_pylist()
    assert sample.equals(universe.filter(pc.starts_with(universe["id"], prefix)))
    assert set(record["assertions"]["sample"]) == set(B.assertion_fields("sample", True))
    # the features config carries the published feature columns only
    features = pq.read_table(spec.out_dir / "features.parquet")
    assert features.column_names == ["id", "word", *W.PUBLISHED_FEATURE_COLUMNS]
    assert not set(W.WITHHELD_FEATURES) & set(features.column_names)
    assert record["projection"]["withheld_feature_columns"] == list(W.WITHHELD_FEATURES)
    # the record names the code that built it
    assert set(record["code"]) == {"commit", "tracked_files_changed"}
    # v2.0's profile is unchanged: no sample, every feature column
    assert B.FULL.configs == ["universe", "features"] + [n for n, _ in B.FILTER_CONFIGS]
    assert B.FULL.features == C.FEATURE_LAYER_COLUMNS


def test_a_withheld_feature_reaching_the_features_file_fails_the_build(tmp_path, monkeypatch):
    import pyarrow as pa
    from research.release import withholding as W
    spec = make_public_fixture(tmp_path)
    _at_write(monkeypatch, "features.parquet", lambda table: table.append_column(
        W.WITHHELD_FEATURES[0], pa.array([0] * table.num_rows, pa.int8())))
    with pytest.raises(B.ReleaseError, match="features"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_a_model_column_altered_at_write_fails_at_ur1_13(tmp_path, monkeypatch):
    import pyarrow as pa
    spec = make_public_fixture(tmp_path)

    def alter(table):
        values = ["none"] * table.num_rows
        return table.set_column(table.column_names.index("model_or_engine"),
                                "model_or_engine", pa.array(values))
    _at_write(monkeypatch, "universe.parquet", alter)
    with pytest.raises(B.ReleaseError, match="model_or_engine does not re-derive"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)



def test_the_reach_guard_refuses_the_build_before_anything_is_written(tmp_path, monkeypatch):
    """A published label or a layer's emptied sources that a withheld list
    copies refuses the build; the
    error names the label and the list and no count."""
    spec = make_public_fixture(tmp_path)
    monkeypatch.setattr(B.W, "reach_breaches", lambda reach, threshold: ["eol:wikipedia: web2"])
    with pytest.raises(B.ReleaseError, match="reach guard.*eol:wikipedia: web2"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)
    assert not (spec.out_dir.parent / f"{spec.out_dir.name}.reach.json").exists()


def test_the_reach_counts_stay_in_a_private_receipt(tmp_path):
    """The record states the guard's rule and threshold; its counts are in a
    receipt beside the held-back file, outside the release directory."""
    spec = make_public_fixture(tmp_path)
    record = B.build(spec, controls=CONTROLS, log=lambda *a: None)
    receipt = json.loads((spec.out_dir.parent / f"{spec.out_dir.name}.reach.json")
                         .read_text(encoding="utf-8"))
    assert set(receipt) == {"version", "threshold", "labels", "empty_sources"}
    guard = record["projection"]["reach_guard"]
    assert set(guard) == {"rule", "threshold", "counts"}
    assert guard["threshold"] == spec.reach_threshold



# ---------------------------------------------------------------------------
# The lead's review of pull requests 8 and 9: the upload's gate and checks
# ---------------------------------------------------------------------------

def test_a_plain_upload_refuses_and_never_makes_a_hub_client(monkeypatch):
    """B3: without the owner's word nothing is read and no client is made."""
    import huggingface_hub

    def no_client(*a, **k):
        raise AssertionError("a hub client was made")
    monkeypatch.setattr(huggingface_hub, "HfApi", no_client)
    monkeypatch.setattr(B, "read_restricted", lambda *a: (_ for _ in ()).throw(
        AssertionError("the restricted list was read")))
    assert U.main(["--version", "v2.1"]) == 1
    assert U.main(["--version", "v2.1", "--owner-word", "D-012"]) == 1
    assert U.main(["--version", "v2.0", "--owner-word", "D-011"]) == 1


_SHA = "a" * 64
_WORD = ('**The owner\'s word for this upload:** "upload v2.1 privately" (upload v2.1 '
         'to the private dataset ryanjosephkamp/ceol-universe; release record sha256 '
         + _SHA + ")")


def _entry(body: str, name: str = "D-013") -> str:
    return f"# Decisions\n\n## {name} · 2026-10-20 · A title\n\n{body}\n\n## D-099 · x\n\nnothing\n"


@pytest.mark.parametrize("body", [
    # 4 made-up bodies: none grants the upload
    "**Decided by the owner on 2026-10-20.** v2.1 is not uploaded until the consumer test passes.",
    "**Decided by the owner on 2026-10-20.** The upload of v2.1 waits for gate G3.",
    "**Decided by the owner on 2026-10-20: lines 1 and 2.** 1. A ruling. 2. **Decided by "
    "another session:** prepare the upload of v2.1 for a later word.",
    "**Decided by another session.** It quotes \"Decided by the owner\" and says: Do not "
    "upload v2.1.",
])
def test_an_entry_that_grants_nothing_refuses(body):
    with pytest.raises(U.UploadRefused, match="no line of the owner's word"):
        U.owner_word("D-013", "v2.1", _SHA, _entry(body))


def test_the_owners_word_is_1_fixed_line_for_this_build_of_this_version():
    assert U.owner_word("D-013", "v2.1", _SHA, _entry(_WORD)) == "D-013"
    for entry, sha, text, message in (
            (None, _SHA, _entry(_WORD), "--owner-word"),
            ("13", _SHA, _entry(_WORD), "not a decision"),
            ("D-014", _SHA, _entry(_WORD), "not in the decision record"),
            ("D-013", "b" * 64, _entry(_WORD), "another build"),
            ("D-013", _SHA, _entry(_WORD.replace("upload v2.1 to", "upload v3.0 to")),
             "not v2.1"),
            ("D-013", _SHA, _entry(_WORD.replace("ryanjosephkamp/ceol-universe",
                                                 "someone/else")), "not v2.1"),
            ("D-013", _SHA, _entry(_WORD + "\n" + _WORD), "more than 1")):
        with pytest.raises(U.UploadRefused, match=message):
            U.owner_word(entry, "v2.1", sha, text)


def test_the_word_is_read_from_the_named_record_and_refused_without_one(tmp_path, monkeypatch):
    monkeypatch.delenv(U.DECISIONS_ENV, raising=False)
    with pytest.raises(U.UploadRefused, match="must name the owner's decision record"):
        U.committed_decisions()
    record = tmp_path / "record.md"
    record.write_text(_entry("named"), encoding="utf-8")
    monkeypatch.setenv(U.DECISIONS_ENV, str(record))
    assert "named" in U.committed_decisions()
    monkeypatch.setenv(U.DECISIONS_ENV, str(tmp_path / "absent.md"))
    with pytest.raises(U.UploadRefused, match="cannot be read"):
        U.committed_decisions()


def _preflight_case(tmp_path, monkeypatch):
    """A public digit release, the real card and template, and the staged
    files with a Croissant file of its own."""
    from research.release import consumer_test as T
    from research.release import public_card as Pc
    spec = make_public_fixture(tmp_path)
    record = B.build(spec, controls=CONTROLS, log=lambda *a: None)
    croissant = tmp_path / "croissant.json"
    croissant.write_text('{"name": "a stand-in"}\n', encoding="utf-8")
    real = T.hub_files
    monkeypatch.setattr(T, "hub_files", lambda s: real(s, croissant=croissant))
    return spec, record, Pc.CARD.read_text(encoding="utf-8"), \
        Pc.TEMPLATE.read_text(encoding="utf-8"), croissant


def test_each_preflight_refusal_comes_before_the_hub(tmp_path, monkeypatch):
    """T2: a card that does not re-derive, a restricted word in a Parquet
    file or in a text document, and a file the record does not name are each
    refused by the preflight; and the preflight runs before the hub is
    asked anything."""
    spec, record, card, template, croissant = _preflight_case(tmp_path, monkeypatch)
    assert U.preflight(spec, record, card, template, set())
    with pytest.raises(U.UploadRefused, match="not the rendering"):
        U.preflight(spec, record, card + "\nan edit\n", template, set())
    with pytest.raises(U.UploadRefused, match="universe.parquet holds 1 restricted"):
        U.preflight(spec, record, card, template, {"12"})
    croissant.write_text('{"name": "zqvexw"}\n', encoding="utf-8")
    with pytest.raises(U.UploadRefused, match="croissant.json holds 1 restricted"):
        U.preflight(spec, record, card, template, {"zqvexw"})
    target = spec.out_dir / "spaced.parquet"
    target.write_bytes(target.read_bytes() + b"\0")
    with pytest.raises(B.ReleaseError, match="not the file the record names"):
        U.preflight(spec, record, card, template, set())
    # the order: a refused preflight leaves the hub untouched
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())

    def refuse(*a):
        raise U.UploadRefused("the preflight refused")
    monkeypatch.setattr(U, "preflight", refuse)
    hub = _FakeHub()
    with pytest.raises(U.UploadRefused, match="preflight refused"):
        U.upload("v2.1", hub, record_out=tmp_path / "never.json")
    assert hub.whoami_calls == 0 and hub.commits == []


class _File:
    def __init__(self, path, blob_id=None, lfs=None):
        self.path, self.blob_id = path, blob_id
        self.lfs = type("L", (), {"sha256": lfs})() if lfs else None


class _AfterHub:
    """A stand-in hub after a commit: what it reports of each path."""

    def __init__(self, infos, tree, private=True):
        self.infos, self.tree, self.private = infos, tree, private

    def repo_info(self, repo_id, repo_type=None):
        return _Info(self.private)

    def get_paths_info(self, repo_id, paths, revision=None, repo_type=None):
        return [self.infos[p] for p in paths if p in self.infos]

    def list_repo_files(self, repo_id, revision=None, repo_type=None):
        return list(self.tree)


def test_the_checks_after_the_commit(tmp_path):
    """T7: the card is checked; a text file the hub keeps in LFS is held by
    its sha256; a path beyond the files sent is refused."""
    from research.release import public_card as Pc
    card, notice = Pc.CARD, tmp_path / "NOTICES.md"
    notice.write_text("# NOTICES\n", encoding="utf-8")
    data = tmp_path / "u.parquet"
    data.write_bytes(b"PAR1")
    record = {"files": [{"path": "universe.parquet", "sha256": _sha(data)}]}
    pairs = [(data, "data/universe.parquet"), (notice, "NOTICES.md")]
    calcs = type("Calcs", (), {"CARD": card})
    spec = B.resolve("v2.1")
    ok = {"data/universe.parquet": _File("data/universe.parquet", lfs=_sha(data)),
          "NOTICES.md": _File("NOTICES.md", lfs=_sha(notice)),
          "README.md": _File("README.md", blob_id=U.git_blob_id(card))}
    tree = list(ok) + [".gitattributes"]
    final, hub, blobs = U.after_commit(_AfterHub(ok, tree), spec, calcs, pairs, record, "c")
    assert hub == {"data/universe.parquet": _sha(data)}
    assert blobs["NOTICES.md"].startswith("lfs sha256") and blobs["README.md"]
    bad_card = {**ok, "README.md": _File("README.md", blob_id="0" * 40)}
    with pytest.raises(U.UploadRefused, match="README.md"):
        U.after_commit(_AfterHub(bad_card, tree), spec, calcs, pairs, record, "c")
    with pytest.raises(U.UploadRefused, match="beyond the files sent"):
        U.after_commit(_AfterHub(ok, tree + ["data/old.parquet"]), spec, calcs,
                       pairs, record, "c")
    with pytest.raises(U.UploadRefused, match="not private"):
        U.after_commit(_AfterHub(ok, tree, private=False), spec, calcs, pairs, record, "c")


def test_a_failure_after_the_commit_writes_a_partial_record(tmp_path, monkeypatch):
    """T7: the commit landed, so the record keeps it, marked incomplete."""
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())
    monkeypatch.setattr(U, "preflight", lambda *a: [])

    class Hub(_FakeHub):
        def create_commit(self, *a, **k):
            self.commits.append(a)
            return type("C", (), {"oid": "1" * 40})()

    def failing(*a):
        raise U.UploadRefused("a check after the commit failed")
    monkeypatch.setattr(U, "after_commit", failing)
    out = tmp_path / "hf_upload_v2.1.json"
    with pytest.raises(U.UploadRefused, match="after the commit failed"):
        U.upload("v2.1", Hub(), record_out=out)
    partial = json.loads(out.read_text(encoding="utf-8"))
    assert partial["complete"] is False and partial["commit"] == "1" * 40
    assert partial["decision"] == "D-999"



def test_an_existing_tag_refuses_before_anything_is_sent(monkeypatch, tmp_path):
    """NS-2: the version's tag is never moved silently."""
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())
    monkeypatch.setattr(U, "preflight", lambda *a: [])
    hub = _FakeHub()
    hub.tags = ("v2.1",)
    with pytest.raises(U.UploadRefused, match="tag v2.1 exists"):
        U.upload("v2.1", hub, record_out=tmp_path / "never.json")
    assert hub.commits == []


@pytest.mark.parametrize("where", ["after_commit", "create_tag"])
def test_any_failure_after_the_commit_writes_a_partial_record(where, monkeypatch, tmp_path):
    """NS-2: a RuntimeError in the checks, or a refused tag, after the commit
    landed still leaves a record of the commit."""
    monkeypatch.setattr(U, "owner_word", lambda *a, **k: "D-999")
    monkeypatch.setattr(B, "read_restricted", lambda spec, n: set())
    monkeypatch.setattr(U, "preflight", lambda *a: [])

    class Hub(_FakeHub):
        def create_commit(self, *a, **k):
            self.commits.append(a)
            return type("C", (), {"oid": "2" * 40})()

        def create_tag(self, *a, **k):
            raise RuntimeError("a 409 from the hub")
    if where == "after_commit":
        monkeypatch.setattr(U, "after_commit", lambda *a: (_ for _ in ()).throw(
            RuntimeError("a timeout from the hub")))
    else:
        monkeypatch.setattr(U, "after_commit", lambda *a: (_Info(True), {}, {}))
    out = tmp_path / "hf_upload_v2.1.json"
    with pytest.raises(RuntimeError):
        U.upload("v2.1", Hub(), record_out=out)
    partial = json.loads(out.read_text(encoding="utf-8"))
    assert partial["complete"] is False and partial["commit"] == "2" * 40
    assert "RuntimeError" in partial["failed_check"]


def test_the_history_the_hub_keeps_is_recorded_with_its_tag():
    """Note 4 and N-7: the upload record says what the history holds, and
    that the tag keeps it reachable."""
    assert "v2.0's files" in U.HISTORY_HOLDS and "tag" in U.HISTORY_HOLDS
    assert "squash" in U.HISTORY_HOLDS


def test_v2_1_s_reach_threshold_is_the_projection_s():
    """NS-3: the threshold v2.1 is built with is pinned."""
    assert B.resolve("v2.1").reach_threshold == B.W.REACH_THRESHOLD == 0.99


def test_the_live_reach_guard_refuses_a_label_a_withheld_list_copies(tmp_path):
    """NS-3: with v2.1's threshold, the real guard refuses a digit build in
    which every row of a published label is listed by a withheld list."""
    import dataclasses
    import pyarrow as pa
    import pyarrow.parquet as pq
    spec = dataclasses.replace(make_public_fixture(tmp_path),
                               reach_threshold=B.W.REACH_THRESHOLD)

    def rewrite(name: str, change, record: str, key: tuple[str, ...]):
        path = tmp_path / "data" / f"{name}.parquet"
        rows = pq.read_table(path).to_pylist()
        for row in rows:
            if row["word"] == "10":
                change(row)
        pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(path)), path)
        rec = tmp_path / "records" / f"{record}.json"
        body = json.loads(rec.read_text())
        node = body
        for k in key[:-1]:
            node = node[k]
        node[key[-1]] = _sha(path)
        rec.write_text(json.dumps(body))
    # "10" listed by web2 too, and the only row of the label eol:wikipedia
    rewrite("evidence", lambda r: r.update(web2=1), "evidence",
            ("artifacts", "evidence_parquet_sha256"))
    rewrite("provenance", lambda r: r.update(intake_channels="eol:wikipedia",
                                             panel_count=r["panel_count"] + 1),
            "provenance", ("artifact", "sha256"))
    with pytest.raises(B.ReleaseError, match="reach guard.*eol:wikipedia: web2"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    _nothing_left(spec)


def test_the_floor_holds_the_differenced_counts():
    """N-12: a layer, kind, or class with more than 0 and fewer than 10
    held-back rows refuses; 0 or 10 or more passes."""
    import pyarrow as pa
    held = pa.table({"word": [f"w{i}" for i in range(13)],
                     "reason": ["tier_2"] * 13,
                     "intake_layer": ["eol_valid"] * 10 + ["c1_exceptions"] * 3,
                     "intake_kind": ["obtained"] * 13,
                     "class_explicit": ["plain"] * 13})
    assert B.differenced_cells(held, 10) == ["intake_layer=c1_exceptions"]
    with pytest.raises(B.ReleaseError, match="intake_layer=c1_exceptions"):
        B.projection_block(held, 10)
    assert B.differenced_cells(held.slice(0, 10), 10) == []


def test_a_failed_record_write_leaves_no_file(tmp_path, monkeypatch):
    """The record is written inside the protected block, atomically: when its
    write fails, the promoted files are removed and no partial record stays
    (the G4 audit's F7)."""
    spec = make_fixture(tmp_path / "late")
    real = Path.write_text

    def fail_record(self, *a, **k):
        if self.name.startswith(spec.record_out.name):
            raise OSError(28, "No space left on device")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", fail_record)
    with pytest.raises(OSError, match="No space left"):
        B.build(spec, controls=CONTROLS, log=lambda *a: None)
    monkeypatch.undo()
    _nothing_left(spec)
    assert not spec.record_out.with_name(spec.record_out.name + ".tmp").exists()
