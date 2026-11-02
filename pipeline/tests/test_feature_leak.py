"""The orthotactic columns' test (research/release/feature_leak.py):
its rule, its record, and the projection it decided."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from research.release import feature_leak as L
from research.release import withholding as W

REPO = Path(__file__).resolve().parents[1]
RECORD = json.loads(L.RECORD.read_text(encoding="utf-8"))


def test_the_rule_needs_the_whole_interval_above_chance():
    assert not L.reveals(None)
    assert not L.reveals({"auc": 0.56, "lo": 0.50, "hi": 0.62})
    assert not L.reveals({"auc": 0.50, "lo": 0.45, "hi": 0.55})
    assert L.reveals({"auc": 0.56, "lo": 0.501, "hi": 0.62})


def test_the_record_tests_the_projection_s_panel():
    assert sorted(RECORD["published_sets"]) == sorted(W.PUBLISHED_SETS)
    assert RECORD["withheld_sets"] == list(W.WITHHELD_SETS)
    assert set(RECORD["reveals"]) == set(L.COLUMNS) == set(W.WITHHELD_MODEL_FEATURES)


def test_a_column_the_test_finds_revealing_is_withheld():
    for column, reveals in RECORD["reveals"].items():
        assert reveals == L.reveals_any(RECORD["residual_auc"][column])
        if reveals:
            assert column in W.WITHHELD_FEATURES
            assert column not in W.PUBLISHED_FEATURE_COLUMNS


def test_the_record_s_quoted_figures_are_its_measurements():
    figs = RECORD["doc_figures"]
    per_char = L.COLUMNS[1]
    for k in L.STRATA:
        assert figs[f"residual_{k}"] == f"{RECORD['residual_auc'][per_char][str(k)]['auc']:.4f}"
        assert figs[f"residual_held_out_{k}"] == \
            f"{RECORD['residual_auc_held_out'][per_char][str(k)]['auc']:.4f}"
    assert figs["memorization_per_char"] == f"{RECORD['memorization_auc'][per_char]['auc']:.4f}"
    assert figs["withheld_feature_columns"] == len(W.WITHHELD_FEATURES)
    assert figs["published_feature_columns"] == len(W.PUBLISHED_FEATURE_COLUMNS)
    lows = [RECORD["residual_auc"][per_char][str(k)]["auc"] for k in L.STRATA]
    assert RECORD["decision_figures"]["residual_low"] == f"{min(lows):.2f}"
    assert RECORD["decision_figures"]["residual_high"] == f"{max(lows):.2f}"


def test_the_record_holds_no_count_crossed_with_the_pool():
    """Only AUCs and the pool sizes the feature manifest already publishes
    (docs/ANALYSIS_PLAN.md §9 rule 3): no stratum carries a row count."""
    for block in ("memorization_auc", "residual_auc", "residual_auc_held_out"):
        text = json.dumps(RECORD[block])
        assert '"n_pos"' not in text and '"n_neg"' not in text
    manifest = json.loads((REPO / "research" / "features" /
                           "features_manifest.json").read_text())["partitions"]
    assert RECORD["pool"] == manifest["pool"]
    assert RECORD["pool_train"] == manifest["train"]


@pytest.mark.skipif(not (REPO / "data" / "evidence.parquet").exists(),
                    reason="data/ is absent in this environment")
def test_the_record_re_derives_from_the_layers():
    run = subprocess.run([sys.executable, "-m", "research.release.feature_leak",
                          "--check"], capture_output=True, text=True, cwd=REPO)
    assert run.returncode == 0, run.stderr[-600:]
