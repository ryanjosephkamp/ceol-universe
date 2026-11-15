"""
C4 step 2: the feature artifact re-checked from the shipped bytes.
Skips cleanly when features.parquet has not been built.
"""

import json
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
FEATURES = REPO / "data" / "features.parquet"
MANIFEST = REPO / "research" / "features" / "features_manifest.json"
GATE = REPO / "research" / "features" / "features_gate.json"

pytestmark = pytest.mark.skipif(
    not (FEATURES.exists() and MANIFEST.exists()),
    reason="features.parquet not built")


def test_columns_and_counts_match_manifest():
    import pyarrow.parquet as pq
    manifest = json.loads(MANIFEST.read_text())
    t = pq.read_table(FEATURES)
    assert t.num_rows == manifest["universe_rows"]
    for fam in manifest["proposed_families"]:
        assert fam in t.schema.names
    wf = t.column("wordfreq_zipf").to_numpy(zero_copy_only=False)
    assert int(np.isfinite(wf).sum()) == manifest["wordfreq"]["scored"]
    # every row is orthotactically scored (no NA fallback fired)
    assert manifest["charmodel"]["class_na_fallback"] == []
    lp = t.column("orthotactic_logp_per_char").to_numpy(
        zero_copy_only=False)
    assert int(np.isfinite(lp).sum()) == manifest["universe_rows"]


def test_admitted_families_meet_the_declared_gate():
    gate = json.loads(GATE.read_text())
    for fam, row in gate["family_admission"].items():
        sep = row["auc_oriented"]
        if row["admitted"]:
            assert sep is not None and sep["lo"] >= 0.60, fam
            assert row["fire_ratio"] is None or row["fire_ratio"] >= 5, fam
        else:
            assert (sep is None or sep["lo"] < 0.60
                    or (row["fire_ratio"] is not None
                        and row["fire_ratio"] < 5)), fam


def test_sr2_reading_b_re_derives():
    import pyarrow.parquet as pq
    from research import archival
    DETECTORS = archival.load("research/contest/data.py").DETECTORS
    manifest = json.loads(MANIFEST.read_text())
    ev = pq.read_table(REPO / "data" / "evidence.parquet")
    n = ev.num_rows
    fires = np.zeros(n, dtype=np.int8)
    for c in DETECTORS:
        fires += (ev.column(c).to_numpy(zero_copy_only=False) == 1)
    fires += (ev.column("scowl_tier").to_numpy(
        zero_copy_only=False) > 0).astype(np.int8)
    ft = pq.read_table(FEATURES, columns=["gb_log10_match",
                                          "wordfreq_zipf"])
    has_gb = np.isfinite(ft.column("gb_log10_match").to_numpy(
        zero_copy_only=False))
    has_wf = np.isfinite(ft.column("wordfreq_zipf").to_numpy(
        zero_copy_only=False))
    rows = int(((fires == 0) & ~has_gb & ~has_wf).sum())
    assert rows == manifest["sr2_reading_b"]["rows"]
    assert manifest["sr2_reading_b"]["pass"] is True
