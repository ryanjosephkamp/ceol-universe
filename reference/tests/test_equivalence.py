"""
The C2 filter-equivalence proof, as a permanent member of the suite.

Filtering the shipped merged artifact on `eol` must regenerate both pinned
EOL files byte-for-byte. sha256 equality accounts for both directions at
once: a missing word, an extra word, or a duplicate all change the hash.

Skips cleanly when the merged artifact or the read-only EOL snapshot is not
present (a fresh clone before `python -m research.merge.build_merge`).
"""

import hashlib
from pathlib import Path

import pytest

from research.merge.build_merge import (DATA_DIR, EOL_INVALID_TXT,
                                        EOL_VALID_TXT, PIN_INVALID, PIN_VALID)

MERGED = DATA_DIR / "merged.parquet"

pytestmark = pytest.mark.skipif(
    not (MERGED.exists() and EOL_VALID_TXT.exists()
         and EOL_INVALID_TXT.exists()),
    reason="merged.parquet or the pinned EOL snapshot not present")


def _sha256_lines(words):
    h = hashlib.sha256()
    for w in words:
        h.update(w.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def test_filter_equivalence_is_byte_exact():
    import pyarrow.parquet as pq
    t = pq.read_table(MERGED, columns=["word", "eol", "eol_universe"])
    words = t.column("word").to_pylist()
    eol = t.column("eol").to_pylist()
    uni = t.column("eol_universe").to_pylist()

    regen_valid = sorted(w for w, e in zip(words, eol) if e)
    regen_invalid = sorted(
        w for w, e, u in zip(words, eol, uni) if u and not e)

    assert _sha256_lines(regen_valid) == PIN_VALID
    assert _sha256_lines(regen_invalid) == PIN_INVALID

    # And the non-universe remainder is exactly the exceptions inventory —
    # no row is unaccounted for in either direction.
    exceptions = [w for w, u in zip(words, uni) if not u]
    assert len(words) == len(regen_valid) + len(regen_invalid) \
        + len(exceptions)
    assert len(set(words)) == len(words)
