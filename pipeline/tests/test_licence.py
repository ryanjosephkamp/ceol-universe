"""
The licence rule (C-009), enforced mechanically and permanently: no word
attested only by NWL2023/CSW21 (redistributable = false) may appear in
any file this repository commits or would commit.

Scans every tracked file plus untracked-but-not-ignored files — the set
a commit could capture — tokenized on non-letter boundaries. Skips
cleanly where the gitignored restricted split is absent (fresh clones),
because the scan's reference set is itself unshippable.
"""

import csv
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESTRICTED_CSV = REPO / ".cache" / "audit" / "universe_miss_restricted.csv"

pytestmark = pytest.mark.skipif(
    not RESTRICTED_CSV.exists(),
    reason="restricted split not present (clean clone)")


def test_no_restricted_word_in_committable_files():
    with open(RESTRICTED_CSV, encoding="utf-8") as f:
        restricted = {row["word"] for row in csv.DictReader(f)}
    assert len(restricted) > 0

    listed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--cached", "--others",
         "--exclude-standard"],
        capture_output=True, text=True, check=True).stdout.split("\n")
    offenders = {}
    for rel in filter(None, listed):
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue                      # binary: parquet etc. never commit
        hits = set(re.split(r"[^a-z]+", text.lower())) & restricted
        if hits:
            offenders[rel] = sorted(hits)[:5]
    assert not offenders, (
        f"restricted (NWL/CSW-only) words in committable files: {offenders}")
