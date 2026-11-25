"""The open subset (research/release/open_subset.py): its rule on small
tables, its NOTICES against the version's, its record's counts against
each other and the release's, and, where the files are present, the record
re-derived."""

import hashlib
import json

import pyarrow as pa
import pytest

from research.release import open_subset as O

RECORD = json.loads(O.RECORD.read_text(encoding="utf-8"))
CONFIGS = {c["config"]: c for c in RECORD["configs"]}
RELEASE = json.loads((O.RELEASE_DIR / f"release_{O.VERSION}.json").read_text(encoding="utf-8"))


def _row(word, tc=1, wn=0, wk=0, us=0, ca=0, au=0, tier=0, gb=True, panel="",
         classes=""):
    multi = tc > 1
    return {"id": hashlib.sha256(word.encode()).hexdigest()[:16], "word": word,
            "token_count": tc, "classes": classes,
            "wordnet": None if multi else wn,
            "wiktionary_english": None if multi else wk,
            "hunspell_en_US": None if multi else us,
            "hunspell_en_CA": None if multi else ca,
            "hunspell_en_AU": None if multi else au,
            "scowl_tier": None if multi else tier,
            "gb_type": None if multi else gb, "panel_sets": panel,
            "wn_instance": (False if "wordnet" in panel else None) if multi else None,
            "wn_capitalized": (False if "wordnet" in panel else None) if multi else None,
            "wk_proper_noun": (False if "wiktionary_english" in panel else None) if multi else None,
            "wk_flags": ("" if "wiktionary_english" in panel else None) if multi else None}


SCHEMA = pa.schema([("id", pa.string()), ("word", pa.string()),
                    ("token_count", pa.int32()), ("classes", pa.string()),
                    ("wordnet", pa.int8()), ("wiktionary_english", pa.int8()),
                    ("hunspell_en_US", pa.int8()), ("hunspell_en_CA", pa.int8()),
                    ("hunspell_en_AU", pa.int8()), ("scowl_tier", pa.int16()),
                    ("gb_type", pa.bool_()), ("panel_sets", pa.string()),
                    ("wn_instance", pa.bool_()), ("wn_capitalized", pa.bool_()),
                    ("wk_proper_noun", pa.bool_()), ("wk_flags", pa.string())])

TINY = pa.Table.from_pylist([
    _row("alpha", wn=1, wk=1, us=1, ca=1, au=1, tier=10),
    _row("beta", wk=1, tier=95),                      # Wiktionary; SCOWL 95 hidden
    _row("gamma", tier=80),                           # only SCOWL 80: left out
    _row("delta", us=1),                              # hunspell alone
    _row("epsilon", tier=70),                         # SCOWL 70 alone
    _row("zeta"),                                     # no list: left out
    _row("eta-theta", wn=-1, us=-1, ca=-1, au=-1, tier=-1, wk=1, classes="hyphenated"),
    _row("iota kappa", tc=2, panel="wordnet"),
    _row("lambda mu", tc=2, panel="wordnet;wiktionary_english"),
    _row("nu xi", tc=2, panel="wiktionary_english"),
], schema=SCHEMA)


def _cfg(name):
    return [c for c in O.CONFIGS if c["config"] == name][0]


def test_scowl_size_never_names_a_size_above_70():
    got = O.scowl_size(pa.array([None, -1, 0, 10, 70, 80, 95], pa.int16())).to_pylist()
    assert got == [None, -1, 0, 10, 70, 0, 0]


def test_open_lists_keeps_the_rows_an_open_list_lists():
    t = O.project(TINY, _cfg("open-lists"))
    assert t.column_names == list(O.OPEN_COLUMNS)
    assert t["word"].to_pylist() == ["alpha", "beta", "delta", "epsilon",
                                     "eta-theta", "iota kappa", "lambda mu", "nu xi"]
    by = dict(zip(t["word"].to_pylist(), t["listed_by"].to_pylist()))
    assert by["alpha"] == ";".join(O.OPEN_LISTS)
    assert by["beta"] == "wiktionary_english"
    assert by["epsilon"] == "scowl"
    assert by["lambda mu"] == "wordnet;wiktionary_english"
    sizes = dict(zip(t["word"].to_pylist(), t["scowl_size"].to_pylist()))
    assert sizes["beta"] == 0 and sizes["alpha"] == 10 and sizes["eta-theta"] == -1
    counts = dict(zip(t["word"].to_pylist(), t["list_count"].to_pylist()))
    assert counts["alpha"] == 6 and counts["lambda mu"] == 2 and min(counts.values()) == 1


def test_wordnet_wiktionary_counts_those_2_lists_alone():
    t = O.project(TINY, _cfg("wordnet-wiktionary"))
    assert t.column_names == list(O.WN_WK_COLUMNS)
    assert t["word"].to_pylist() == ["alpha", "beta", "eta-theta", "iota kappa",
                                     "lambda mu", "nu xi"]
    assert dict(zip(t["word"].to_pylist(), t["listed_by"].to_pylist()))["alpha"] == \
        "wordnet;wiktionary_english"


def test_the_independent_rule_agrees_with_the_projection():
    for name in ("open-lists", "wordnet-wiktionary", "sample"):
        pos = O.expected_positions(TINY, _cfg(name))
        assert TINY["id"].take(pa.array(pos)).to_pylist() == \
            O.project(TINY, _cfg(name))["id"].to_pylist()


def test_notices_carry_the_versions_texts_unchanged():
    version = (O.RELEASE_DIR / "NOTICES_v1.0.md").read_text(encoding="utf-8")
    text, carried = O.notices(version)
    assert [c["section"] for c in carried] == [s["heading"][3:] for s in O.NOTICE_SECTIONS]
    blocks = O.verbatim_blocks(version)
    assert all(b in blocks for b in O.verbatim_blocks(text))
    for field in ("wikt_title_screen", "wikt_title_any", "scowl_tier", "zipf_resid", "eol:"):
        assert field not in text
    assert text == O.NOTICES_OUT.read_text(encoding="utf-8")


def test_the_committed_card_and_notices_are_the_records():
    for name, path in (("README.md", O.CARD_OUT), ("NOTICES.md", O.NOTICES_OUT)):
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == RECORD["documents"][name]["sha256"]
        assert len(data) == RECORD["documents"][name]["bytes"]


def test_the_card_renders_from_the_record():
    assert O.render_card(RECORD) == O.CARD_OUT.read_text(encoding="utf-8")


def test_the_records_counts_account_for_each_other():
    o, w, s = (CONFIGS[k]["counts"] for k in ("open-lists", "wordnet-wiktionary", "sample"))
    for c in (o, w, s):
        assert c["single"] + c["multiword"] == c["rows"]
        assert sum(c["single_by_list_count"].values()) == c["single"]
        assert sum(c["multiword_by_listing"].values()) == c["multiword"]
    assert w["multiword"] == o["multiword"] == RELEASE_ROWS["spaced"]
    assert w["single"] <= o["single"] and s["rows"] < o["rows"]
    assert w["single_by_list"] == {k: o["single_by_list"][k] for k in O.WN_WK_LISTS}
    # the version's panel-listed rows are the subset's and the rows the card
    # counts as left out (the record's figure; which lists hold those is
    # checked outside this test)
    assert o["rows"] + RECORD["version"]["listed_not_open"] == RELEASE_ROWS["panel-listed"]
    assert sum(o["single_by_scowl_size"].values()) == o["single_by_list"]["scowl"]
    assert RECORD["version"]["universe_rows"] == RELEASE_ROWS["universe"]
    assert RECORD["version"]["universe_sha256"] == {
        f["path"]: f["sha256"] for f in RELEASE["files"]}["universe.parquet"]


RELEASE_ROWS = {f["config"]: f["rows"] for f in RELEASE["files"]}


def test_no_file_carries_a_column_outside_the_open_set():
    never = set(RECORD["version"]["columns_never_read"]) | set(O.NEVER_WRITTEN) \
        | set(RECORD["version"]["columns_read_for_a_count"])
    for c in RECORD["configs"]:
        assert not set(c["columns"]) & never
        assert c["columns"] == list(_cfg(c["config"])["columns"])


@pytest.mark.skipif(not (O.default_out() / "data" / "open-lists.parquet").exists()
                    or not (O.DATA_RELEASE / f"ceol-universe-{O.VERSION}" / "universe.parquet").exists(),
                    reason="needs the release's files under data/ and the built subset beside it")
def test_the_record_re_derives():
    assert O.main(["--check"]) == 0


@pytest.mark.skipif(not (O.default_out() / "data" / "open-lists.parquet").exists(),
                    reason="needs the built subset beside the data folder")
def test_the_upload_preflight_passes_and_refuses_without_the_owners_word():
    from research.release import upload_open_subset as U
    assert U.main(["--dry-run"]) == 0
    with pytest.raises(U.UploadRefused):
        U.upload("", O.default_out())


def _written(tmp_path, name="open-lists", mutate=None, extra_md=None):
    import pyarrow.parquet as pq
    cfg = _cfg(name)
    t = O.project(TINY, cfg)
    if mutate:
        t = mutate(t)
    path = tmp_path / "f.parquet"
    md = O.file_metadata()
    if extra_md:
        md = {**md, **extra_md}
    pq.write_table(t.replace_schema_metadata(md), path)
    return path, cfg


def _check(path, cfg):
    return O.check_file(path, cfg, TINY, O.expected_positions(TINY, cfg),
                        list(TINY.column_names) + ["eol", "sources"])


def _set_col(t, name, values):
    i = t.column_names.index(name)
    return t.set_column(i, name, pa.array(values, t.schema.field(name).type))


def test_the_file_check_passes_a_true_file(tmp_path):
    path, cfg = _written(tmp_path)
    assert _check(path, cfg)["rows"] == 8


def test_the_file_check_refuses_a_wrong_multiword_listing(tmp_path):
    def swap(t):
        names = t["listed_by"].to_pylist()
        names[t["word"].to_pylist().index("iota kappa")] = "wiktionary_english"
        return _set_col(t, "listed_by", names)
    path, cfg = _written(tmp_path, mutate=swap)
    with pytest.raises(O.OpenSubsetError):
        _check(path, cfg)


def test_the_file_check_refuses_a_list_named_twice(tmp_path):
    def dup(t):
        names = t["listed_by"].to_pylist()
        names[t["word"].to_pylist().index("beta")] = "wiktionary_english;wiktionary_english"
        return _set_col(t, "listed_by", names)
    path, cfg = _written(tmp_path, mutate=dup)
    with pytest.raises(O.OpenSubsetError):
        _check(path, cfg)


def test_the_file_check_refuses_extra_metadata(tmp_path):
    path, cfg = _written(tmp_path, extra_md={b"ceol.extra": b"x"})
    with pytest.raises(O.OpenSubsetError):
        _check(path, cfg)


def test_the_notices_check_refuses_a_missing_license_block():
    version = (O.RELEASE_DIR / "NOTICES_v1.0.md").read_text(encoding="utf-8")
    text, _ = O.notices(version)
    O.check_notices(version, text)
    block = O.verbatim_blocks(O.sections(text)["## WordNet 3.0 (Princeton University)"])[0]
    with pytest.raises(O.OpenSubsetError):
        O.check_notices(version, text.replace(block, ""))


@pytest.mark.skipif(not (O.DATA_RELEASE / f"ceol-universe-{O.VERSION}" / "universe.parquet").exists(),
                    reason="needs the release's files under data/")
def test_the_check_fails_on_an_empty_folder(tmp_path):
    assert O.main(["--check", "--out", str(tmp_path)]) == 1
