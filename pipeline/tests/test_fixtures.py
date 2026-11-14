"""The fixtures of the site and the kit (tools/build_fixtures.py): they are
what their manifests say, they are rows of v1.0's files and carry nothing a
public version withholds, and their sample follows the stated ranking. The
figures and the cube are the pipeline's (tests/test_figures.py). Every test
but the last runs in a clone, on the committed files."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from ceol import grammar
from research.release import build_release, withholding
from safeguards import keys

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site" / "fixtures"
KIT = ROOT / "kit" / "fixtures"
RELEASE_RECORD = ROOT / "pipeline" / "research" / "release" / "release_v1.0.json"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _site_rows() -> list[dict]:
    return [json.loads(line) for line in
            (SITE / "rows.jsonl").read_text(encoding="utf-8").splitlines()]


def _kit_rows() -> list[dict]:
    return pq.read_table(KIT / "universe_sample.parquet").to_pylist()


@pytest.mark.parametrize("folder", [SITE, KIT])
def test_each_file_is_the_file_its_manifest_names(folder):
    manifest = _json(folder / "MANIFEST.json")
    present = {p.name for p in folder.iterdir()} - {"MANIFEST.json", "README.md"}
    assert present == set(manifest["files"])
    for name, meta in manifest["files"].items():
        data = (folder / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta["sha256"], name
        assert len(data) == meta["bytes"], name


def test_a_row_carries_the_published_columns_and_names_no_withheld_list():
    site, kit = _site_rows(), _kit_rows()
    assert pq.read_schema(KIT / "universe_sample.parquet").names \
        == list(build_release.PUBLIC.columns)
    for row in site + kit:
        assert list(row) == list(build_release.PUBLIC.columns)
        assert not withholding.reveals_a_withheld_list(row), row["id"]
        # a row whose every channel is withheld keeps public evidence, or
        # the projection would hold it back
        assert not (row["intake_channels"] == withholding.CHANNEL_WITHHELD
                    and row["provenance_class"] == "neither"), row["id"]
        assert set(filter(None, row["intake_channels"].split(";"))) \
            <= withholding.PUBLISHED_CHANNEL_LABELS, row["id"]
        assert set(filter(None, row["sources"].split(";"))) \
            <= withholding.PUBLISHED_SOURCE_LABELS, row["id"]
        # D-012 line 1: no census or audit row with empty sources (NS-1)
        assert not (row["intake_layer"] in withholding.SOURCE_LISTING_LAYERS
                    and row["sources"] == ""), row["id"]
        sets = [s for s in row["panel_sets"].split(";") if s]
        assert set(sets) <= set(withholding.PUBLISHED_SETS)
        assert row["panel_count"] == len(sets)
        assert row["provenance_class"] == withholding.provenance_class(
            row["intake_channels"], row["panel_count"], row["gb_type"],
            row["wordfreq_scored"])
        assert row["is_restricted"] is False


def test_a_row_is_a_string_of_the_grammar_with_its_own_id():
    for row in _kit_rows():
        word = row["word"]
        ok = grammar.normalize(word) == word
        assert ok, row["id"]
        assert row["id"] == hashlib.sha256(word.encode("utf-8")).hexdigest()[:16]
        assert row["token_count"] == grammar.token_count(word)


def test_the_manifests_state_the_rule_and_never_the_key():
    """D-012 line 5: the rule is published, the key is not, and the rows the
    scan passed over are not counted."""
    for folder in (SITE, KIT):
        text = (folder / "MANIFEST.json").read_text(encoding="utf-8")
        sampling = json.loads(text)["sampling"]
        assert "seed" not in sampling and "rows_passed_over_by_the_scan" not in sampling
        assert "key" in sampling["rule"] and sampling["key"].startswith("private")
        if keys.available("fixtures"):
            # a boolean, so that a failure never prints the key (N-4)
            assert (keys.key("fixtures") in text) is False, "the key is in a manifest"


@pytest.mark.skipif(not keys.available("fixtures"),
                    reason="the fixtures' ranking key is in private/, absent here")
def test_the_sample_follows_the_stated_ranking():
    site_manifest, kit_manifest = _json(SITE / "MANIFEST.json"), _json(KIT / "MANIFEST.json")
    sampling = kit_manifest["sampling"]
    assert sampling["stratum"] == "intake_layer"
    key = keys.key("fixtures")
    site, kit = _site_rows(), _kit_rows()
    assert len({r["id"] for r in kit}) == len(kit) == sampling["rows"]
    assert len(site) == site_manifest["sampling"]["rows"]

    def by_stratum(rows):
        out: dict[str, list[str]] = {}
        for row in rows:
            out.setdefault(row["intake_layer"], []).append(row["word"])
        return out

    kit_by, site_by = by_stratum(kit), by_stratum(site)
    assert sorted(kit_by) == sampling["strata"] == sorted(site_by)
    for stratum, words in kit_by.items():
        assert len(words) == sampling["rows_per_stratum"]
        ranks = [hashlib.sha256(f"{key}:{stratum}:{w}".encode("utf-8"))
                 .hexdigest() for w in words]
        assert ranks == sorted(ranks), stratum
        # the site's sample is the head of the same ranking
        n = site_manifest["sampling"]["rows_per_stratum"]
        same_head = site_by[stratum] == words[:n]
        assert same_head, stratum


def test_the_feature_rows_are_the_single_token_rows_of_the_sample():
    features = pq.read_table(KIT / "features_sample.parquet")
    assert features.column_names == ["id", "word", *withholding.PUBLISHED_FEATURE_COLUMNS]
    single = [r["id"] for r in _kit_rows() if r["token_count"] == 1]
    assert features["id"].to_pylist() == single
    assert features.num_rows == _json(KIT / "MANIFEST.json")["sampling"]["feature_rows"]


def test_the_manifests_name_the_release_file_and_the_figures_folder():
    files = {f["config"]: f for f in _json(RELEASE_RECORD)["files"]}
    for folder in (SITE, KIT):
        manifest = _json(folder / "MANIFEST.json")
        assert manifest["source"]["sha256"] == files["universe"]["sha256"]
        assert manifest["source"]["rows"] == files["universe"]["rows"]
        assert manifest["columns"] == files["universe"]["columns"]
        assert (ROOT / manifest["figures_and_cube"]).is_dir()
        assert not (folder / "cube.json").exists()


@pytest.mark.skipif(not (ROOT / "data" / "release").exists(),
                    reason="data/ is absent in this environment")
def test_the_builder_reproduces_the_committed_fixtures():
    run = subprocess.run([sys.executable, str(ROOT / "tools" / "build_fixtures.py"),
                          "--check"], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout[-600:]



def test_the_builder_s_module_names_are_not_shadowed():
    """NB-1: a local name in build() that shadows an imported module makes
    the module unreadable in the whole function; the builder must never
    assign `keys`, `withholding`, `locations`, `restricted`, or `wall`."""
    import symtable
    source = (ROOT / "tools" / "build_fixtures.py").read_text(encoding="utf-8")
    table = symtable.symtable(source, "build_fixtures.py", "exec")
    build = next(t for t in table.get_children() if t.get_name() == "build")
    for name in ("keys", "withholding", "locations", "restricted", "wall"):
        if name in build.get_identifiers():
            assert not build.lookup(name).is_local(), name
