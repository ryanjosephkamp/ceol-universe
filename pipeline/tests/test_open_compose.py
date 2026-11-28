"""The open subset's cube and layout for the site (research/release/
open_compose.py): the cube's coding on a small table, the 2 derivations the
site makes, the committed cube against the subset's own record, the layout
against the subset's and the upload's records, and, where the subset's file
is present, both re-derived from it."""

import collections
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from research.release import open_compose as C
from research.release import open_subset as O

CUBE = json.loads(C.CUBE_OUT.read_text(encoding="utf-8"))
LAYOUT = json.loads(C.LAYOUT_OUT.read_text(encoding="utf-8"))
RECORD = json.loads(O.RECORD.read_text(encoding="utf-8"))
COUNTS = {c["config"]: c for c in RECORD["configs"]}["open-lists"]["counts"]
UPLOAD = json.loads(C.UPLOAD_RECORD.read_text(encoding="utf-8"))

SCHEMA = pa.schema([("word", pa.string()), ("token_count", pa.int32()), ("classes", pa.string()),
                    ("scowl_size", pa.int16()), ("gb_type", pa.bool_()), ("list_count", pa.int8()),
                    ("listed_by", pa.string()), ("wn_instance", pa.bool_()),
                    ("wk_proper_noun", pa.bool_())])


def _row(word, listed, tc=1, size=0, gb=True, classes="", inst=None, proper=None):
    multi = tc > 1
    return {"word": word, "token_count": tc, "classes": classes,
            "scowl_size": None if multi else size, "gb_type": None if multi else gb,
            "list_count": len(listed.split(";")), "listed_by": listed,
            "wn_instance": inst, "wk_proper_noun": proper}


TINY = pa.Table.from_pylist([
    _row("alpha", "wordnet;wiktionary_english;scowl", size=10),
    _row("beta", "wiktionary_english", gb=False),
    _row("zeta", "wiktionary_english", gb=False),
    _row("de-lta", "hunspell_en_US;scowl", size=70, classes="hyphenated"),
    _row("x" * 30, "wiktionary_english", size=-1),
    _row("iota kappa", "wordnet", tc=2, classes="spaced", inst=True),
    _row("lambda mu nu xi omicron", "wiktionary_english", tc=5, classes="spaced", proper=False),
], schema=SCHEMA)


def _cells(dims, cells):
    """Each cell as {dimension: value}, with its count."""
    names = [d["name"] for d in dims]
    return [({n: dims[k]["values"][c[k]] for k, n in enumerate(names)}, c[-1]) for c in cells]


def test_the_cube_codes_each_dimension():
    dims, cells = C.cube_of(TINY)
    assert [d["name"] for d in dims] == list(C.DIMENSIONS)
    values = {d["name"]: d["values"] for d in dims}
    assert values["scowl_size"] == ["null", "-1", "0", "10", "70"]
    assert values["token_count"] == ["1", "2", "4+"]
    assert values["length"][-1] == "25+" and values["length"][0] == "4"
    assert values["classes"] == ["", "hyphenated", "spaced"]
    assert values["gb_type"] == ["true", "false", "null"]
    assert values["wn_instance"] == ["true", "null"]
    assert sum(c[-1] for c in cells) == TINY.num_rows
    by = _cells(dims, cells)
    # beta and zeta differ only in their strings: 1 cell of 2
    assert max(n for _, n in by) == 2
    multi = [v for v, _ in by if v["token_count"] != "1"]
    assert all(v["scowl_size"] == "null" and v["gb_type"] == "null" for v in multi)


def test_the_cube_holds_no_string_of_a_row():
    dims, _ = C.cube_of(TINY)
    held = {v for d in dims for v in d["values"]}
    assert not held & set(TINY["word"].to_pylist())


def test_a_list_count_that_is_not_listed_by_is_refused():
    rows = TINY.to_pylist()
    rows[1]["list_count"] = 2
    with pytest.raises(C.OpenComposeError, match="list_count"):
        C.cube_of(pa.Table.from_pylist(rows, schema=SCHEMA))


def test_scowl_in_listed_by_is_scowl_size_above_0():
    rows = TINY.to_pylist()
    rows[1]["scowl_size"] = 35
    with pytest.raises(C.OpenComposeError, match="scowl"):
        C.cube_of(pa.Table.from_pylist(rows, schema=SCHEMA))


def test_the_committed_cube_states_the_subsets_counts():
    """Every marginal the subset's record states, from the cube's cells."""
    assert CUBE["source"]["sha256"] == LAYOUT["sha256"]
    by = _cells(CUBE["dimensions"], CUBE["cells"])
    assert sum(n for _, n in by) == COUNTS["rows"] == CUBE["source"]["rows"]
    single = [(v, n) for v, n in by if v["token_count"] == "1"]
    multi = [(v, n) for v, n in by if v["token_count"] != "1"]
    assert sum(n for _, n in single) == COUNTS["single"]
    assert sum(n for _, n in multi) == COUNTS["multiword"]

    lists = collections.Counter()
    count = collections.Counter()
    for v, n in single:
        names = v["listed_by"].split(";")
        for name in names:
            lists[name] += n
        count[str(len(names))] += n
    assert dict(lists) == {k: v for k, v in COUNTS["single_by_list"].items() if v}
    assert {k: count[k] for k in COUNTS["single_by_list_count"]} == COUNTS["single_by_list_count"]
    combos = collections.Counter()
    for v, n in multi:
        combos[v["listed_by"]] += n
    assert dict(combos) == COUNTS["multiword_by_listing"]

    sizes = collections.Counter()
    for v, n in single:
        sizes[v["scowl_size"]] += n
    assert {s: sizes[s] for s in COUNTS["single_by_scowl_size"]} == COUNTS["single_by_scowl_size"]
    assert sum(n for v, n in single if v["gb_type"] == "true") == COUNTS["single_gb_type"]
    classes = collections.Counter()
    for v, n in single:
        for f in v["classes"].split(";") if v["classes"] else ["plain"]:
            classes[f] += n
    assert dict(classes) == COUNTS["single_by_class"]
    for dim in ("wn_instance", "wk_proper_noun"):
        assert sum(n for v, n in by if v[dim] == "true") == COUNTS["multiword_true"][dim]


def test_the_layout_is_the_file_at_the_upload_commit():
    uploaded = next(f for f in UPLOAD["files"] if f["path"] == C.HUB_PATH)
    entry = next(c for c in RECORD["configs"] if c["config"] == C.CONFIG)
    assert LAYOUT["sha256"] == uploaded["sha256"] == entry["sha256"]
    assert LAYOUT["bytes"] == entry["bytes"] and LAYOUT["rows"] == entry["rows"]
    assert LAYOUT["commit"] == UPLOAD["commit"] == CUBE["commit"]
    assert LAYOUT["url"] == C.hub_url(UPLOAD["commit"])
    assert C.UPLOAD_RECORD.exists() and UPLOAD["repo_id"] == C.DATASET == LAYOUT["dataset"]
    assert LAYOUT["metadata"]["ceol.attribution"] == O.ATTRIBUTION
    assert LAYOUT["metadata"]["ceol.license"] == O.LICENSE
    assert LAYOUT["rows"] == sum(g["rows"] for g in LAYOUT["row_groups"])
    for group in LAYOUT["row_groups"]:
        assert list(group["columns"]) == list(C.READ_COLUMNS)
        for start, size in group["columns"].values():
            assert 0 < start and start + size <= LAYOUT["bytes"]


def test_the_notices_the_site_ships_are_the_subsets():
    want = next(f for f in UPLOAD["files"] if f["path"] == "NOTICES.md")["sha256"]
    assert hashlib.sha256(O.NOTICES_OUT.read_bytes()).hexdigest() == want
    assert RECORD["documents"]["NOTICES.md"]["sha256"] == want


def test_a_file_that_is_not_the_subsets_is_refused(tmp_path):
    path = tmp_path / "open-lists.parquet"
    pq.write_table(TINY, path)
    with pytest.raises(C.OpenComposeError, match="not the file"):
        C.build(path)


@pytest.mark.skipif(not C.default_file().exists(), reason="needs the open subset's files (open_subset.py --out)")
def test_the_cube_and_the_layout_re_derive():
    assert C.main(["--check"]) == 0
