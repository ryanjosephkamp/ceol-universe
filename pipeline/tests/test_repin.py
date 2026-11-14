"""Universe v1 re-pinned to the EOL's revision (research/universe/repin.py):
the record's counts account for each other and name the pinned files, and,
where data/ holds the files, the written pin is the file the record names
and the strings the re-pin removed are the record's count."""

import json

import pytest

from ceol.ingest.common import sha256_file
from research.universe import repin as R

RECORD = json.loads(R.OUT_JSON.read_text(encoding="utf-8"))
N = RECORD["counts"]


def test_the_counts_account_for_each_other():
    assert N["inherited_rows"] == N["eol_valid"] + N["eol_invalid"]
    assert N["eol_valid"] == RECORD["eol"]["valid_rows"]
    assert N["eol_invalid"] == RECORD["eol"]["invalid_rows"]
    assert N["universe_rows"] == (N["inherited_rows"] + N["exceptions"]
                                  + N["c4_additions"])
    assert RECORD["archival"]["rows"] - N["left_in_neither_list"] == N["universe_rows"]
    assert N["valid_at_archival_pin_not_now"] == 0
    proof = RECORD["filter_equivalence"]
    assert proof["valid_matches_pin"] and proof["invalid_matches_pin"]
    assert proof["regenerated_valid_sha256"] == R.EOL_FILES["valid_words"]["sha256"]
    assert proof["regenerated_invalid_sha256"] == R.EOL_FILES["invalid_words"]["sha256"]


def test_the_record_names_the_pinned_revision():
    assert RECORD["eol"]["revision"] == R.EOL_REVISION
    assert RECORD["eol"]["files"] == R.EOL_FILES
    assert RECORD["tag"] == R.TAG == f"eol_universe@{R.EOL_REVISION[:8]}"
    archival = json.loads(R.ARCHIVAL_JSON.read_text(encoding="utf-8"))
    assert RECORD["archival"]["universe_parquet_sha256"] == \
        archival["artifacts"]["universe_parquet_sha256"]
    assert RECORD["archival"]["rows"] == archival["counts"]["universe_rows"]


@pytest.mark.skipif(
    not (R.OUT_PARQUET.exists() and R.ARCHIVAL_PARQUET.exists()
         and (R.EOL_DIR / "merged_invalid_words.txt").exists()),
    reason="needs the archival pin, the re-pinned pin, and the EOL's lists under data/")
def test_the_written_pin_is_the_recorded_file():
    assert sha256_file(R.OUT_PARQUET) == RECORD["artifacts"]["universe_parquet_sha256"]
    assert len(R.left_strings()) == N["left_in_neither_list"]
