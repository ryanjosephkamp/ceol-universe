"""
C4 step 0: the pinned universe re-checked from the shipped artifact.

Skips cleanly when data/universe.parquet has not been built (fresh clone
before `python -m research.universe.build_universe`).
"""

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
UNIVERSE = REPO / "data" / "universe.parquet"
UNIVERSE_JSON = REPO / "research" / "universe" / "universe.json"
AUDIT_JSON = REPO / "research" / "audit" / "audit.json"

pytestmark = pytest.mark.skipif(
    not (UNIVERSE.exists() and UNIVERSE_JSON.exists()),
    reason="universe.parquet not built")


def test_universe_matches_pin_and_json():
    import pyarrow.parquet as pq
    figures = json.loads(UNIVERSE_JSON.read_text())["doc_figures"]
    audit = json.loads(AUDIT_JSON.read_text())["doc_figures"]
    t = pq.read_table(
        UNIVERSE, columns=["word", "eol", "eol_universe", "c4_addition",
                           "is_restricted"])
    assert t.num_rows == figures["universe_rows"] \
        == audit["c4_recommended_pin"]

    words = t.column("word").to_pylist()
    eol = t.column("eol").to_pylist()
    uni = t.column("eol_universe").to_pylist()
    c4 = t.column("c4_addition").to_pylist()
    restr = t.column("is_restricted").to_pylist()

    assert sum(restr) == figures["restricted_rows"] \
        == audit["miss_restricted"]
    assert sum(c4) == figures["c4_additions"]
    assert sum(1 for u, c in zip(uni, c4) if not u and not c) \
        == figures["exceptions"]
    # restricted rows are additions, never merged rows
    assert all(c for c, r in zip(c4, restr) if r)

    # sorted with no duplicates — one pass over the shipped order
    assert all(a < b for a, b in zip(words, words[1:]))

    # the filter-equivalence pins survive the pin additions
    h = hashlib.sha256()
    for w, e in zip(words, eol):
        if e:
            h.update(w.encode() + b"\n")
    assert h.hexdigest() == ("aa8df4c5d4358b67119462a27accf29c9193098"
                             "14d8b33377b03c4bf0244f6e0")
