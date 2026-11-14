"""The repository's vetted example list (`examples/`, built by
safeguards/examples.py): the file is the file
its manifest names, it follows the stated ranking, its first lines are the
draw and the rest meet the floor per class, its strings are strings of the
grammar, and the manifest's sizes are the file's. Every test but the last 2
runs in a clone, on the committed files.

A failing assertion here names line numbers and counts, never a string."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from ceol import grammar
from research.release import withholding
from safeguards import examples, keys, restricted, wall

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / examples.LIST_REL
MANIFEST = ROOT / examples.MANIFEST_REL
RELEASE_RECORD = ROOT / "pipeline" / "research" / "release" / f"release_{examples.VERSION}.json"

needs_private = pytest.mark.skipif(
    not (wall.available() and restricted.available()),
    reason="private/ is absent in this environment (make link)")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _strings() -> list[str]:
    text = LIST.read_text(encoding="utf-8")
    assert text.endswith("\n")
    return text[:-1].split("\n")


def test_the_file_is_the_file_its_manifest_names():
    manifest = _json(MANIFEST)
    present = {p.name for p in LIST.parent.iterdir() if not p.name.startswith(".")}
    assert present == {"MANIFEST.json", "README.md", manifest["file"]["name"]}
    data = LIST.read_bytes()
    assert hashlib.sha256(data).hexdigest() == manifest["file"]["sha256"]
    assert len(data) == manifest["file"]["bytes"]
    assert data.count(b"\n") == manifest["file"]["lines"] \
        == manifest["sampling"]["strings"] + manifest["floor"]["strings_added"]
    assert manifest["sampling"]["strings"] == examples.SUBSET


def test_the_manifest_states_the_rule_and_never_the_key():
    """D-012 line 3: the rule is published, the key is not."""
    text = MANIFEST.read_text(encoding="utf-8")
    sampling = json.loads(text)["sampling"]
    assert "seed" not in sampling and sampling["key"].startswith("private")
    assert sampling["rule"] == examples.RULE and sampling["stratum"] == examples.STRATUM
    if keys.available("examples"):
        # a boolean, so that a failure never prints the key
        assert (keys.key("examples") in text) is False, "the key is in the manifest"


@pytest.mark.skipif(not keys.available("examples"),
                    reason="the example list's ranking key is in private/, absent here")
def test_the_list_follows_the_stated_ranking():
    sampling = _json(MANIFEST)["sampling"]
    key = keys.key("examples")
    strings = _strings()
    assert len(set(strings)) == len(strings) == _json(MANIFEST)["file"]["lines"]
    ranks = [hashlib.sha256(
        f"{key}:{sampling['stratum']}:{s}".encode("utf-8")).hexdigest()
        for s in strings]
    out_of_order = [n for n in range(1, len(ranks)) if ranks[n - 1] >= ranks[n]]
    assert out_of_order == []
    assert [examples.ranking_key(s).hex() for s in strings[:3]] == ranks[:3]


def _class(string: str) -> str:
    return ";".join(sorted(grammar.classes(string))) or "plain"


def test_the_first_lines_are_the_draw_and_every_class_meets_the_floor():
    manifest = _json(MANIFEST)
    strings = _strings()
    drawn, floor = strings[:examples.SUBSET], strings[examples.SUBSET:]
    assert manifest["floor"]["per_class"] == examples.FLOOR == 20
    assert manifest["drawn"]["strings"] == examples.SUBSET
    assert dict(Counter(map(_class, drawn))) == manifest["drawn"]["by_class"]
    assert dict(Counter(map(_class, floor))) == manifest["floor"]["by_class_added"]
    assert len(floor) == manifest["floor"]["strings_added"]
    whole, have = manifest["whole_list"]["by_class"], manifest["drawn"]["by_class"]
    listed = manifest["list"]["by_class"]
    # every class holds the floor, or every string the whole list holds
    # where it holds fewer; no class gets more than it needs
    wrong = {c: (listed.get(c, 0), have.get(c, 0), n) for c, n in whole.items()
             if listed.get(c, 0) != max(have.get(c, 0), min(examples.FLOOR, n))}
    assert wrong == {}
    # only a class the draw left short gets floor strings
    assert all(have.get(c, 0) < examples.FLOOR for c in manifest["floor"]["by_class_added"])


def test_a_string_is_a_string_of_the_grammar_and_the_sizes_are_the_file_s():
    strings, sizes = _strings(), _json(MANIFEST)["list"]
    not_normal = [n for n, s in enumerate(strings, 1) if grammar.normalize(s) != s]
    assert not_normal == []
    by_class = Counter(map(_class, strings))
    assert dict(by_class) == sizes["by_class"]
    by_tokens = Counter(
        str(grammar.token_count(s)) if grammar.token_count(s) < 3 else "3 or more"
        for s in strings)
    assert dict(by_tokens) == sizes["by_token_count"]
    assert sizes["strings"] == len(strings)


def test_the_manifest_states_the_rule_its_source_and_sizes_that_add_up():
    manifest = _json(MANIFEST)
    universe = {f["config"]: f for f in _json(RELEASE_RECORD)["files"]}["universe"]
    assert manifest["source"] == {"version": examples.VERSION, "config": "universe",
                                  "sha256": universe["sha256"], "rows": universe["rows"]}
    rule = manifest["rule"]
    assert rule["min_source_families"] == examples.MIN_FAMILIES == 2
    assert rule["source_families"] == examples.published_families()
    assert sorted(rule["not_counted"]) == sorted(withholding.WITHHELD_SETS)
    counts = manifest["counts"]
    assert counts["rows_of_the_universe_config"] == universe["rows"]
    assert counts["restricted_rows"] == 0
    assert counts["eligible"] == manifest["whole_list"]["strings"] \
        == counts["listed_by_at_least_2_source_families"] - counts["removed_by_the_scan"]
    named = set(rule["source_families"])
    for sizes in (manifest["whole_list"], manifest["drawn"], manifest["list"]):
        for key in ("by_class", "by_token_count", "by_source_family_count",
                    "by_source_families"):
            assert sum(sizes[key].values()) == sizes["strings"], key
        # no string of either list rests on fewer than 2 source families
        assert min(map(int, sizes["by_source_family_count"])) >= examples.MIN_FAMILIES
        for combination in sizes["by_source_families"]:
            members = combination.split(";")
            assert len(members) >= examples.MIN_FAMILIES and set(members) <= named
    assert manifest["list"]["strings"] <= manifest["whole_list"]["strings"]
    for key in ("by_class", "by_source_families"):
        assert set(manifest["list"][key]) <= set(manifest["whole_list"][key])


@needs_private
def test_the_scan_finds_nothing_in_the_list():
    terms, words = wall.all_terms(), restricted.restricted_words()
    strings = _strings()
    dirty = examples.clean_mask(strings, terms, words).count(False)
    assert dirty == 0
    # the file as the scan reads it: its path, then its text
    text = examples.LIST_REL + "\n" + LIST.read_text(encoding="utf-8")
    hits = len(wall.Matcher(terms).hits(text)) + len(restricted.find_hits(text, words))
    assert hits == 0


@needs_private
@pytest.mark.skipif(not (ROOT / "data" / "release").exists(),
                    reason="data/ is absent in this environment")
def test_the_builder_reproduces_the_committed_list():
    run = subprocess.run([sys.executable, "-m", "safeguards.examples", "--check"],
                         cwd=ROOT / "pipeline", capture_output=True, text=True)
    assert run.returncode == 0, run.stdout[-300:] + run.stderr[-300:]
