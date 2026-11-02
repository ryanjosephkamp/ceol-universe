"""The evidence record of the license review (kept outside the repository) (`docs/licenses/EVIDENCE.csv`,
`tools/license_evidence.py`): every row is complete, every file the review
cites has a row, and, where the folder of saved texts is present, every row
matches its file byte for byte."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import license_evidence  # noqa: E402

REVIEW = Path(os.environ["CEOL_LICENSE_REVIEW"]) if os.environ.get("CEOL_LICENSE_REVIEW") else None
_SHA256 = re.compile(r"[0-9a-f]{64}")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}Z)?")


def test_every_row_is_complete():
    rows = license_evidence.read_rows()
    assert rows
    for row in rows:
        assert row["file"] and row["question"] and row["source"], row["file"]
        assert _UTC.fullmatch(row["read_utc"]), row["file"]
        assert row["bytes"].isdigit(), row["file"]
        assert _SHA256.fullmatch(row["sha256"]), row["file"]


@pytest.mark.skipif(REVIEW is None or not REVIEW.is_file(),
                    reason="the license review is kept outside the repository (CEOL_LICENSE_REVIEW)")
def test_every_cited_file_has_a_row():
    files = {row["file"] for row in license_evidence.read_rows()}
    cited = set(re.findall(r"`evidence/([^`]+)`", REVIEW.read_text(encoding="utf-8")))
    assert cited, "the review cites no saved text"
    assert cited <= files, sorted(cited - files)


@pytest.mark.skipif(not license_evidence.EVIDENCE_DIR.is_dir(),
                    reason="the folder of saved texts is outside the repository")
def test_every_row_matches_its_file():
    rows = license_evidence.read_rows()
    assert license_evidence.check(rows, license_evidence.EVIDENCE_DIR) == []


def test_a_changed_file_is_caught(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"one")
    size, digest = license_evidence.measure(tmp_path / "a.txt")
    rows = [{"file": "a.txt", "question": "Q", "source": "s", "read_utc": "2026-10-18",
             "bytes": str(size), "sha256": digest}]
    assert license_evidence.check(rows, tmp_path) == []
    (tmp_path / "a.txt").write_bytes(b"two")
    assert license_evidence.check(rows, tmp_path) == ["a.txt: the size or the hash differs from the row"]
    (tmp_path / "b.txt").write_bytes(b"x")
    assert "b.txt: a saved file with no row" in license_evidence.check(rows, tmp_path)
    (tmp_path / "a.txt").unlink()
    assert "a.txt: no such file" in license_evidence.check(rows, tmp_path)
