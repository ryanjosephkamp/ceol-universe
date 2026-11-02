"""Version 1.0 holds v2.1's rows (research/release/rename_check.py):
the column comparison catches a changed value
and grants a NaN its own value, the record covers every config of both
versions, and the record re-derives where the release files are."""

import json
import math

import pyarrow as pa
import pytest

from research.release import build_release as B
from research.release import rename_check as R

RECORD = json.loads(R.OUT.read_text(encoding="utf-8"))


def _col(values, kind=pa.float32()):
    return pa.chunked_array([pa.array(values, type=kind)])


def test_a_nan_equals_the_same_nan_and_nothing_else():
    nan = math.nan
    assert R._same_column(_col([1.0, nan, 2.5]), _col([1.0, nan, 2.5]))
    assert not R._same_column(_col([1.0, nan, 2.5]), _col([1.0, nan, 2.25]))
    assert not R._same_column(_col([1.0, nan]), _col([1.0, 0.0]))
    assert not R._same_column(_col([1.0, None]), _col([1.0, 0.0]))
    assert R._same_column(_col([1.0, None]), _col([1.0, None]))
    assert not R._same_column(_col([1.0], pa.float32()), _col([1.0], pa.float64()))


def test_other_columns_must_be_equal():
    assert R._same_column(_col(["a", "b"], pa.string()), _col(["a", "b"], pa.string()))
    assert not R._same_column(_col(["a", "b"], pa.string()), _col(["a", "c"], pa.string()))
    assert not R._same_column(_col([1, 2], pa.int32()), _col([1, 3], pa.int32()))


def test_the_record_covers_every_config_of_both_versions():
    old, new = (json.loads(B.resolve(v).record_out.read_text(encoding="utf-8")) for v in (R.OLD, R.NEW))
    configs = [f["config"] for f in RECORD["files"]]
    assert configs == [f["config"] for f in old["files"]] == [f["config"] for f in new["files"]]
    for row, a, b in zip(RECORD["files"], old["files"], new["files"]):
        assert row[f"sha256_{R.OLD}"] == a["sha256"] and row[f"sha256_{R.NEW}"] == b["sha256"]
        assert row["rows"] == a["rows"] == b["rows"]
        assert row["values_equal"] is True and row["metadata_differing"] == ["ceol.version"]
    assert set(RECORD["record_fields_differing"]) <= set(R.VARYING)


@pytest.mark.skipif(not B.resolve(R.NEW).out_dir.exists() or not B.resolve(R.OLD).out_dir.exists(),
                    reason="needs both versions' release files under data/release/")
def test_the_record_re_derives():
    assert R.main(["--check"]) == 0


def test_floats_are_compared_bit_for_bit_before_arrow_equality():
    """Arrow's equality takes -0.0 for 0.0; the check does not (the G4
    audit's F14), and a NaN still equals the same NaN."""
    import pyarrow as pa
    from research.release import rename_check as R
    col = lambda *v: pa.chunked_array([pa.array(v, pa.float32())])
    assert pa.array([0.0], pa.float32()).equals(pa.array([-0.0], pa.float32()))
    assert not R._same_column(col(0.0), col(-0.0))
    assert R._same_column(col(float("nan"), 1.5, None), col(float("nan"), 1.5, None))
    assert not R._same_column(col(1.0), pa.chunked_array([pa.array([1.0], pa.float64())]))
