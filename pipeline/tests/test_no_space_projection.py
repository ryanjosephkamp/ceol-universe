"""
The C-015 gating invariant, part (1): the no-space projection of the
extended grammar is byte-identical to the pre-C-015 grammar.

Claim, stated over inputs: for any string containing neither U+0020 nor
U+00A0 (the two code points C-015 gave meaning to), the extended
`ceol.grammar.normalize` returns exactly what the pre-C-015 normalize
returned — the same key or the same rejection. Strings containing either
code point are outside the projection domain by definition.

The proof here runs the claim over the full pinned universe
(data/universe.parquet, 10,001,409 rows, every row spaceless) against a
frozen verbatim copy of the pre-C-015 implementation, plus an adversarial
spaceless set covering every rejection class. AGENDA S2: this test gates
everything after it — no census runs unless it passes.

Skips cleanly when data/universe.parquet has not been built.
"""

import json
import unicodedata
from pathlib import Path

import pytest

from ceol import grammar

REPO = Path(__file__).resolve().parents[1]
UNIVERSE = REPO / "data" / "universe.parquet"
#: universe v1, re-pinned to the EOL's revision (research/universe/repin.py)
UNIVERSE_JSON = REPO / "research" / "universe" / "repin.json"


# ---------------------------------------------------------------------------
# The frozen reference: ceol/grammar.py as of commit 0b06ed2 (pre-C-015),
# constants inlined, logic verbatim. Never edit this copy — it exists so the
# projection claim is checked against the real prior behaviour, not against
# a re-derivation that could share a bug with the extension.
# ---------------------------------------------------------------------------

_LETTERS = (frozenset("abcdefghijklmnopqrstuvwxyz")
            | frozenset("áàâäéèêëíîïñóôöúûüç") | frozenset("æœ"))
_HYPHEN = "-"
_APOSTROPHE = "'"
_CHARSET = _LETTERS | {_HYPHEN, _APOSTROPHE}


def _c001_well_formed(s: str) -> bool:
    if not s:
        return False
    if any(c not in _CHARSET for c in s):
        return False
    if not any(c in _LETTERS for c in s):
        return False
    if s[0] == _HYPHEN or s[-1] == _HYPHEN:
        return False
    for segment in s.split(_HYPHEN):
        if not segment or not any(c in _LETTERS for c in segment):
            return False
    if s[-1] == _APOSTROPHE:
        return False
    if _APOSTROPHE + _APOSTROPHE in s:
        return False
    return True


def _c001_normalize(raw: str) -> str | None:
    s = unicodedata.normalize("NFC", raw)
    if "’" in s:
        s = s.replace("’", _APOSTROPHE)
    s = s.lower()
    s = unicodedata.normalize("NFC", s)
    return s if _c001_well_formed(s) else None


# ---------------------------------------------------------------------------
# Adversarial spaceless inputs: one representative per rejection class, plus
# accepted forms of every class. Every string here is inside the projection
# domain (no U+0020, no U+00A0).
# ---------------------------------------------------------------------------

SPACELESS_CASES = [
    # accepted, one per census class
    "word", "runner-up", "café", "naïve", "æon", "can't", "o'clock",
    "'tis", "robin's", "jack-o'-lantern", "fo'c's'le", "naïveté",
    # rejected: structure
    "", "-up", "self-", "a--b", "-", "'", "dogs'", "a''b", "a-'-b",
    # rejected: charset
    "mp3", "straße", "İzmir", "smörgåsbord", "don‘t", "donʼt", "don`t",
    "runner–up", "runner—up", "run­ner", "eﬃcient", "ａpple",
    "ad_hoc", "_",
    # rejected: non-space whitespace
    "ad\thoc", "ad\nhoc", "ad\u2003hoc", "ad\u200bhoc", "ad\u3000hoc",
    # canonicalization inputs
    "don’t", "’tis", "Café", "RÉSUMÉ", "café",
]


def test_spaceless_cases_agree():
    for s in SPACELESS_CASES:
        assert " " not in s and "\u00a0" not in s, repr(s)
        assert grammar.normalize(s) == _c001_normalize(s), repr(s)


def test_frozen_reference_rejects_spaced_forms():
    # The reference is genuinely pre-C-015: spaced and NBSP forms reject.
    assert _c001_normalize("ice cream") is None
    assert _c001_normalize("ad\u00a0hoc") is None
    # The extension accepts them — the two grammars differ ONLY outside
    # the projection domain.
    assert grammar.normalize("ice cream") == "ice cream"
    assert grammar.normalize("ad\u00a0hoc") == "ad hoc"


# ---------------------------------------------------------------------------
# The full-universe proof
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not (UNIVERSE.exists() and UNIVERSE_JSON.exists()),
                    reason="universe.parquet not built")
def test_projection_byte_identical_over_full_universe():
    import pyarrow.parquet as pq

    expected_rows = json.loads(
        UNIVERSE_JSON.read_text(encoding="utf-8"))["counts"]["universe_rows"]
    rows = 0
    new_normalize = grammar.normalize
    for batch in pq.ParquetFile(UNIVERSE).iter_batches(
            batch_size=1_000_000, columns=["word"]):
        for w in batch.column("word").to_pylist():
            assert " " not in w and "\u00a0" not in w, repr(w)
            old = _c001_normalize(w)
            assert new_normalize(w) == old, repr(w)
            # universe keys are fixed points of their own grammar
            assert old == w, repr(w)
            rows += 1
    assert rows == expected_rows
