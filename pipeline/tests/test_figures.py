"""The figures file and the cube of v1.0 (research/release/figures.py): each
figure is named once and says where it was counted; the cube sums to the
release; the figures agree with the cube's marginals, the release record,
and the profile. Every test but the last runs in a clone, on the committed
files. No word is read or printed."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from research.release import figures as F
from research.release import public_card as P
from research.release import withholding as W

REPO = Path(__file__).resolve().parents[1]
VERSION = "v1.0"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def files():
    d = F.out_dir(VERSION)
    return (_json(d / "figures.json"), _json(d / "cube.json"),
            _json(P.RECORD), _json(P.PROFILE))


def test_each_figure_has_an_id_a_value_a_meaning_and_a_source(files):
    figures, _cube, record, _profile = files
    assert figures["version"] == record["version"] == VERSION
    ids = [f["id"] for f in figures["figures"]]
    assert len(ids) == len(set(ids))
    for f in figures["figures"]:
        assert set(f) == {"id", "value", "what", "source"}
        assert isinstance(f["value"], int) and f["value"] >= 0
        assert f["source"] in (figures["source"]["path"], figures["record"],
                               "pipeline/research/release/withholding.py")


def test_the_cube_sums_to_the_release_and_its_figures_agree(files):
    figures, cube, record, profile = files
    value = {f["id"]: f["value"] for f in figures["figures"]}
    dims = cube["dimensions"]
    assert [d["name"] for d in dims] == list(F.DIMENSIONS)
    for cell in cube["cells"]:
        assert len(cell) == len(dims) + 1 and cell[-1] > 0
        assert all(0 <= i < len(d["values"]) for i, d in zip(cell, dims))
    assert len({tuple(c[:-1]) for c in cube["cells"]}) == len(cube["cells"])
    total = sum(c[-1] for c in cube["cells"])
    rows = record["rows_by_config"]
    assert total == value["rows"] == rows["universe"] == cube["source"]["rows"]
    assert cube["source"]["sha256"] == record["files"][0]["sha256"]

    def marginal(name: str) -> dict[str, int]:
        k = [d["name"] for d in dims].index(name)
        out: Counter = Counter()
        for cell in cube["cells"]:
            out[dims[k]["values"][cell[k]]] += cell[-1]
        return dict(out)

    for name in ("intake_layer", "intake_kind", "provenance_class",
                 "model_or_engine", "token_count", "class_explicit"):
        for v, n in marginal(name).items():
            assert value[f"rows.by_{name}.{v}"] == n, (name, v)
    # the record's and the profile's counts
    assert {v: value[f"rows.by_model_or_engine.{v}"]
            for v in marginal("model_or_engine")} == \
        record["assertions"]["universe"]["AT-UR1-13"]["rows_by_value"]
    assert {v: value[f"rows.by_provenance_class.{v}"] for v in W.CLASSES} == \
        profile["universe"]["provenance"]["provenance_class"]
    for config, n in rows.items():
        assert value[f"config.{config}.rows"] == n
    held = record["projection"]["held_back"]
    assert value["held_back.rows"] == held["rows"]
    assert value["pin.shippable_rows"] - held["rows"] == total
    limits = profile["universe"]["limits"]
    assert value["rows.inherited_google_books_no_published_set"] == \
        limits["gb_type_inherited_no_panel_set"]
    assert value["rows.inherited_google_books_only"] == \
        limits["gb_type_inherited_no_panel_set_no_wordfreq"]
    assert value["rows.single_token_no_published_set_no_corpus"] == \
        limits["single_token_no_panel_set_no_corpus"]
    assert value["rows.channel_withheld"] == profile["universe"]["provenance"][
        "intake_channels_per_label"][W.CHANNEL_WITHHELD]
    # every combination of panel sets names published sets only
    sets = marginal("panel_sets")
    for combination in sets:
        assert set(filter(None, combination.split(";"))) <= set(W.PUBLISHED_SETS)
    assert value["rows.listed_by_no_published_set"] == sets[""]
    assert value["config.panel-listed.rows"] == total - sets[""]
    # the spaced rows are the rows of 2 tokens or more, and the corpora do
    # not measure them
    assert total - marginal("token_count")["1"] == marginal("gb_type")["null"] \
        == rows["spaced"]
    assert marginal("eol")["true"] == value["rows.eol"] == rows["eol-valid"]


@pytest.mark.skipif(not (REPO / "data" / "release").exists(),
                    reason="data/ is absent in this environment")
def test_the_pipeline_reproduces_the_committed_figures():
    run = subprocess.run([sys.executable, "-m", "research.release.figures",
                          "--version", VERSION, "--check"],
                         capture_output=True, text=True, cwd=REPO)
    assert run.returncode == 0, run.stderr[-600:]



#: the card's rows that are figures of the figures file, by the figure's id
#: the card and the figures file cannot diverge
CARD_FIGURES = {
    "rows_universe": "rows", "rows_features": "config.features.rows",
    "rows_panel_listed": "config.panel-listed.rows",
    "rows_eol_valid": "config.eol-valid.rows", "rows_spaced": "config.spaced.rows",
    "rows_exceptions": "config.exceptions.rows", "rows_sample": "config.sample.rows",
    "rows_pin": "pin.rows", "rows_restricted": "pin.restricted_rows",
    "rows_shippable": "pin.shippable_rows", "held_back_rows": "held_back.rows",
    "held_tier_2": "held_back.tier_2", "held_withheld_channel": "held_back.withheld_channel",
    "held_withheld_sources": "held_back.withheld_sources",
    "columns_universe": "columns.universe", "columns_features": "columns.features",
    "published_set_count": "projection.published_sets",
    "withheld_list_count": "projection.withheld_lists",
    "withheld_feature_count": "projection.withheld_feature_columns",
    "channel_withheld_rows": "rows.channel_withheld",
    "prov_neither": "rows.by_provenance_class.neither",
    "prov_channel_only": "rows.by_provenance_class.channel_only",
    "prov_containment_only": "rows.by_provenance_class.containment_only",
    "prov_channel_and_containment": "rows.by_provenance_class.channel_and_containment",
    "generated_rows": "rows.by_intake_kind.generated",
    "model_pipeline": "rows.by_model_or_engine.model_pipeline",
    "model_alone": "rows.by_model_or_engine.model_alone",
    "limit_gb_inherited_no_panel": "rows.inherited_google_books_no_published_set",
    "limit_gb_only": "rows.inherited_google_books_only",
    "limit_gb_all": "rows.gb_type",
    "limit_no_panel_no_corpus": "rows.single_token_no_published_set_no_corpus",
    "wordfreq_scored": "rows.wordfreq_scored",
    "wordnet_listed": "rows.listed_by.wordnet",
}


def test_the_card_s_counts_are_the_figures(files):
    figures, _cube, _record, _profile = files
    value = {f["id"]: f["value"] for f in figures["figures"]}
    rows = P.rows()
    for row, figure in CARD_FIGURES.items():
        assert int(rows[row].replace(",", "")) == value[figure], (row, figure)
    assert int(rows["model_rows"].replace(",", "")) == \
        value["rows.by_model_or_engine.model_pipeline"] + value["rows.by_model_or_engine.model_alone"]


def test_the_figures_tie_to_the_profile_and_the_record(files):
    """T5: the figures and the cube's dimensions that the cube alone held
    are tied to the profile (computed by other code from the same file) and
    to the record."""
    figures, cube, record, profile = files
    value = {f["id"]: f["value"] for f in figures["figures"]}
    U = profile["universe"]
    V = U["provenance"]
    for name in W.PUBLISHED_SETS:
        assert value[f"rows.listed_by.{name}"] == U["panel_sets_per_label"].get(name, 0), name
    for name in ("gb_type", "wordfreq_scored", "wikt_title_any"):
        assert value[f"rows.{name}"] == U[name]["true"], name
    assert value["rows.eol"] == U["eol"]["true"]
    for name in ("intake_layer", "intake_kind"):
        for v, n in V[name].items():
            assert value[f"rows.by_{name}.{v}"] == n, (name, v)
    for v, n in U["class_explicit"].items():
        assert value[f"rows.by_class_explicit.{v}"] == n, v
    tokens = {k: n for k, n in U["token_count"].items()}
    capped = {str(k): n for k, n in tokens.items() if int(k) < F.TOKEN_CAP}
    capped[f"{F.TOKEN_CAP}+"] = sum(n for k, n in tokens.items() if int(k) >= F.TOKEN_CAP)
    for v, n in capped.items():
        if n:
            assert value[f"rows.by_token_count.{v}"] == n, v
    assert value["rows.listed_by_a_published_set"] == value["config.panel-listed.rows"]
    assert value["projection.published_sets"] == len(W.PUBLISHED_SETS)
    assert value["projection.withheld_lists"] == len(W.WITHHELD_SETS)
    assert value["projection.withheld_feature_columns"] == len(W.WITHHELD_FEATURES)
    files_ = {f["config"]: f for f in record["files"]}
    assert value["columns.universe"] == len(files_["universe"]["columns"])
    assert value["columns.features"] == len(files_["features"]["columns"])

    # the cube's length, wordfreq_scored, and wikt_title_any dimensions
    dims = cube["dimensions"]

    def marginal(name):
        k = [d["name"] for d in dims].index(name)
        out = Counter()
        for cell in cube["cells"]:
            out[dims[k]["values"][cell[k]]] += cell[-1]
        return dict(out)
    hist = U["length"]["hist"]
    by_length = dict(zip(hist["edges"][:-1], hist["counts"]))
    lengths = marginal("length")
    for length in range(1, F.LENGTH_CAP):
        assert lengths.get(str(length), 0) == by_length.get(float(length), 0), length
    assert sum(lengths.values()) == record["rows_by_config"]["universe"]
    for name in ("wordfreq_scored", "wikt_title_any", "gb_type"):
        assert marginal(name) == {k: n for k, n in U[name].items() if n}, name
