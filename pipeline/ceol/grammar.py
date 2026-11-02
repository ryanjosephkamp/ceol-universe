"""
The CEOL grammar: the normalization as executable specification.

This module IS the grammar. GRAMMAR.md describes it; where prose
and code could ever disagree, this file is the specification and the prose is
the defect — and `research/verify_doc_numbers.py` exists to keep them from
disagreeing silently.

Design decisions:

* NFC, never NFKC. Compatibility decomposition would launder presentation
  ligatures (U+FB03 ffi) into letter sequences; the CEOL rejects them instead.
  The declared ligatures ae/oe (U+00E6, U+0153) are ordinary letters to
  Unicode, untouched by either normal form.
* lower(), never casefold(). casefold() maps German eszett to "ss", silently
  turning donor-language orthography into an English-looking string. lower()
  leaves undeclared letters in place to fail the charset check, which is the
  honest outcome.
* Exactly two canonicalizations, each carried by its own decision: U+2019
  RIGHT SINGLE QUOTATION MARK -> U+0027 APOSTROPHE (C-001), and U+00A0
  NO-BREAK SPACE -> U+0020 SPACE (C-015). Every other look-alike (U+2018,
  U+02BC, U+0060, U+00B4, the dashes U+2010/U+2013/U+2014, every other
  whitespace character) is rejected, not folded. Folding an undeclared
  character would invent data.
* The accent inventory is a CLOSED set, extended only by a decision-log entry.
* The space (C-015; J1 details ruled at the S4 gate, C-016): U+0020 is a
  declared character; spaces are single and interior only; every
  space-separated token must itself satisfy the single-token structural
  rules. The no-space projection of this grammar is byte-identical to the
  pre-C-015 grammar (tests/test_no_space_projection.py proves it over the
  full pinned universe). The underscore is NEVER a grammar character: it
  decodes to space at the parse layer of any source that documents
  underscore-as-space (today: MediaWiki titles, WordNet lemma fields),
  before this module sees the string (C-016's J1 amendment).
"""

from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------------
# The declared character inventory (C-001). CLOSED sets: extension happens
# through a documented change, never through an edit that "just adds one".
# ---------------------------------------------------------------------------

#: The base alphabet.
BASE = frozenset("abcdefghijklmnopqrstuvwxyz")

#: The declared accent inventory, exactly as ruled by the owner:
#: a-acute a-grave a-circumflex a-diaeresis, e-acute e-grave e-circumflex
#: e-diaeresis, i-acute i-circumflex i-diaeresis, n-tilde, o-acute
#: o-circumflex o-diaeresis, u-acute u-circumflex u-diaeresis, c-cedilla.
ACCENTED = frozenset("áàâäéèêëíîïñóôöúûüç")

#: The declared ligatures: ash and ethel.
LIGATURES = frozenset("æœ")

#: Diaeresis subset of the accent inventory — a census class of its own
#: (naïve, kümmel, zoöphagy).
DIAERESIS = frozenset("äëïöü")

#: The accent inventory minus the diaeresis letters — the census "accented"
#: class (début, glacé, señora, soufflé, torchère).
NON_DIAERESIS_ACCENTS = ACCENTED - DIAERESIS

LETTERS = BASE | ACCENTED | LIGATURES

HYPHEN = "-"      # U+002D HYPHEN-MINUS, the only admitted hyphen
APOSTROPHE = "'"  # U+0027 APOSTROPHE, the only admitted apostrophe
SPACE = " "       # U+0020 SPACE, the only admitted word-space (C-015)

CHARSET = LETTERS | {HYPHEN, APOSTROPHE, SPACE}

#: The two declared canonicalizations. U+2019 is the typographic rendering
#: of the apostrophe (C-001); U+00A0 is the non-breaking rendering of the
#: space (C-015) — treating either as distinct from its plain form would
#: make the affected words silently exist twice. Everything else that looks
#: like a space or an apostrophe is rejected, not folded.
CANONICALIZE = {"’": APOSTROPHE, "\u00a0": SPACE}

#: Ingest integrity flag inherited from the EOL (its D-025): NOT a form rule.
#: Candidates longer than this are recorded for a reason before intake.
LENGTH_FLAG_OVER = 100


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize(raw: str) -> str | None:
    """
    The CEOL normalization. Returns the normalized key, or None when the
    string is not form-valid under the CEOL grammar.

    Pipeline: NFC -> canonicalize U+2019 and U+00A0 -> lower() -> NFC again
    (lower() can decompose: Turkish dotted capital I lowers to i + combining
    dot above) -> structural validation.
    """
    s = unicodedata.normalize("NFC", raw)
    if "’" in s:
        s = s.replace("’", APOSTROPHE)
    if " " in s:
        s = s.replace(" ", SPACE)
    s = s.lower()
    s = unicodedata.normalize("NFC", s)
    return s if _well_formed(s) else None


def _well_formed(s: str) -> bool:
    """
    Structural rules (C-001; the space rule C-015, its J1 details ruled
    at the S4 gate, C-016),
    applied to an already-normalized string:

    * every character in the declared charset;
    * spaces interior only — no leading, no trailing, no doubling — so
      every space-separated token is non-empty;
    * every token satisfies the single-token rules (_token_well_formed).

    For a spaceless string the token list is [s] and this function is
    exactly the pre-C-015 grammar — the no-space projection invariant that
    tests/test_no_space_projection.py proves over the full pinned universe.
    """
    if not s:
        return False
    if any(c not in CHARSET for c in s):
        return False
    tokens = s.split(SPACE)
    if any(not t for t in tokens):
        return False
    return all(_token_well_formed(t) for t in tokens)


def _token_well_formed(t: str) -> bool:
    """
    The single-token structural rules — C-001 verbatim:

    * at least one letter;
    * hyphens interior only — no leading, no trailing, no doubling — and
      every hyphen-separated segment non-empty and carrying a letter;
    * apostrophes interior or leading (the 'tis class), never the final
      character, never doubled.

    A trailing apostrophe (plural possessive: dogs') is deliberately NOT
    admitted by this grammar. Possessives are a pending class awaiting the
    C1 gate; if admitted, the extension lands as a decision-log entry.
    Under C-015 these rules apply to every space-separated token, so
    "rock 'n' roll" (token 'n' apostrophe-final) is rejected — confirmed
    at the S4 gate with the census counts in hand (C-016), the
    token-trailing-apostrophe class folded into the pending possessive
    gate. One-directionality holds: those candidates wait.
    """
    if not any(c in LETTERS for c in t):
        return False
    if t[0] == HYPHEN or t[-1] == HYPHEN:
        return False
    for segment in t.split(HYPHEN):
        if not segment or not any(c in LETTERS for c in segment):
            return False
    if t[-1] == APOSTROPHE:
        return False
    if APOSTROPHE + APOSTROPHE in t:
        return False
    return True


# ---------------------------------------------------------------------------
# Census classes (C1). Non-exclusive flags: naïveté is both accented and
# diaeresis; can't is both apostrophe-form and contraction.
# ---------------------------------------------------------------------------

#: Enclitic endings counted as contractions. "'s" is deliberately absent:
#: robin's is "robin is" and "of robin" in the same surface form, and a
#: surface-form census cannot disambiguate — s-final forms are counted
#: separately (S_FINAL) as the possessive-relevant diagnostic.
CONTRACTION_ENCLITICS = ("'ll", "'ve", "'re", "'d", "'m")


def is_contraction(word: str) -> bool:
    """
    The census's operational contraction rule — declared, mechanical, and
    deliberately narrower than a linguist's: negative contractions (can't),
    enclitic contractions (she'll, would've), and initial elision ('tis,
    'twas, 'em). Medial elision (o'er, ne'er) and lexicalized apostrophe
    forms (o'clock, ma'am, y'all) count as apostrophe-form, not contraction.
    """
    if word.endswith("n't"):
        return True
    if word.endswith(CONTRACTION_ENCLITICS):
        return True
    if word.startswith(APOSTROPHE):
        return True
    return False


def token_count(word: str) -> int:
    """Space-separated token count of a grammar-valid word (C-015). 1 for
    every spaceless word; the census records the distribution for spaced
    candidates."""
    return word.count(SPACE) + 1


def classes(word: str) -> set[str]:
    """Census classes for a grammar-valid word. Empty set == plain [a-z]+.

    Flags compose (C-015): a spaced word carries "spaced" beside whatever
    its characters and tokens earn. Character-presence flags (hyphenated,
    accented, diaeresis, ligature, apostrophe-form) read the whole string;
    positional flags (contraction, s-final) are evaluated per token, which
    for a spaceless word is exactly the pre-C-015 behavior.
    """
    out: set[str] = set()
    if HYPHEN in word:
        out.add("hyphenated")
    if any(c in NON_DIAERESIS_ACCENTS for c in word):
        out.add("accented")
    if any(c in DIAERESIS for c in word):
        out.add("diaeresis")
    if any(c in LIGATURES for c in word):
        out.add("ligature")
    if SPACE in word:
        out.add("spaced")
    if APOSTROPHE in word:
        out.add("apostrophe-form")
        tokens = word.split(SPACE)
        if any(is_contraction(t) for t in tokens):
            out.add("contraction")
        if any(t.endswith("'s") for t in tokens):
            out.add("s-final")
    return out


#: The census classes reported in the class x source table, in report order.
#: "s-final" is a diagnostic subclass of apostrophe-form kept for the
#: possessive gate, not a class of its own. "spaced" (C-015) is a class
#: flag but deliberately NOT a member of this tuple: the C1 census and the
#: C4 artifacts are six-class over the spaceless universe, and the spaced
#: class's per-source applicability is established by the S3 space census
#: and enters the evidence semantics at the S5 merge, not retroactively.
CENSUS_CLASSES = ("hyphenated", "accented", "contraction", "apostrophe-form",
                  "ligature", "diaeresis")
