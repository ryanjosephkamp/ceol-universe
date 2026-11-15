"""
One unit test per Unicode trap, written BEFORE any word list exists (C0).

Every trap here is a way a wordlist ingest silently corrupts data: two code
points that look identical, a normal form that transforms instead of
canonicalizing, a case mapping that invents letters. Each test documents the
grammar's ruling on one of them. If a ruling ever changes, it changes here
and in a documented change — never silently.

Confusable literals are guarded by assertions on their own shape (a length
check for the decomposed forms, an is-None for every rejected look-alike, an
NFC check on the file's own literals), so a re-encoding of this file cannot
silently turn a trap test into a tautology.
"""

import unicodedata

from ceol import grammar
from ceol.grammar import classes, is_contraction, normalize


# ---------------------------------------------------------------------------
# Composition: NFD input must compose, not duplicate
# ---------------------------------------------------------------------------

def test_nfd_cafe_composes_to_single_form():
    decomposed = "café"            # e + COMBINING ACUTE ACCENT
    composed = "café"               # precomposed e-acute
    assert len(decomposed) == 5 and len(composed) == 4
    assert normalize(decomposed) == normalize(composed) == composed
    assert len(normalize(decomposed)) == 4


def test_nfd_combining_diaeresis_composes():
    assert normalize("naïve") == normalize("naïve") == "naïve"


def test_nfd_combining_tilde_composes():
    assert normalize("piñata") == normalize("piñata") == "piñata"


def test_source_literals_in_this_file_are_nfc():
    # The remaining tests use precomposed literals; this guards the file
    # itself against being re-saved in a decomposed encoding.
    for w in ("café", "naïve", "piñata", "résumé", "señor"):
        assert unicodedata.is_normalized("NFC", w), repr(w)


def test_output_is_nfc_and_idempotent():
    for w in ("café", "naïve", "jack-o'-lantern", "æon", "'tis", "word"):
        out = normalize(w)
        assert out is not None
        assert unicodedata.is_normalized("NFC", out)
        assert normalize(out) == out


# ---------------------------------------------------------------------------
# The apostrophe: one canonicalization, everything else rejected
# ---------------------------------------------------------------------------

def test_u2019_right_single_quote_canonicalizes():
    assert normalize("don’t") == "don't"


def test_u2019_leading_canonicalizes():
    assert normalize("’tis") == "'tis"


def test_u2018_left_single_quote_rejected():
    assert normalize("don‘t") is None


def test_u02bc_modifier_letter_apostrophe_rejected():
    assert normalize("donʼt") is None


def test_backtick_rejected():
    assert normalize("don`t") is None


def test_u00b4_acute_accent_character_rejected():
    assert normalize("don´t") is None


# ---------------------------------------------------------------------------
# The hyphen: U+002D only
# ---------------------------------------------------------------------------

def test_en_dash_rejected():
    assert normalize("runner–up") is None


def test_em_dash_rejected():
    assert normalize("runner—up") is None


def test_u2010_typographic_hyphen_rejected():
    # A "real" Unicode hyphen is still not the declared one; only U+2019 has
    # a declared fold. Rejection, not silent folding, is the ruling.
    assert normalize("runner‐up") is None


def test_u00ad_soft_hyphen_rejected():
    assert normalize("run­ner") is None


# ---------------------------------------------------------------------------
# Case: lower(), never casefold()
# ---------------------------------------------------------------------------

def test_eszett_is_not_laundered_to_ss():
    # casefold() would turn straße into strasse — donor-language orthography
    # masquerading as English. lower() leaves ß to fail the charset.
    assert normalize("straße") is None
    assert normalize("Straße") is None
    # The genuinely all-Latin spelling is a fine candidate string.
    assert normalize("STRASSE") == "strasse"


def test_turkish_dotted_capital_i_rejected_not_mangled():
    # "İ".lower() is "i" + U+0307 COMBINING DOT ABOVE, which composes with
    # nothing — the second NFC pass leaves it and the charset rejects it.
    assert normalize("İzmir") is None


def test_titlecase_digraph_rejected():
    assert normalize("ǅungla") is None


def test_uppercase_accents_lower_cleanly():
    assert normalize("Café") == "café"
    assert normalize("RÉSUMÉ") == "résumé"
    assert normalize("Æon") == "æon"
    assert normalize("ŒSOPHAGUS") == "œsophagus"


# ---------------------------------------------------------------------------
# NFC vs NFKC: real ligatures live, presentation ligatures die
# ---------------------------------------------------------------------------

def test_ash_and_ethel_are_letters_and_survive():
    assert normalize("æon") == "æon"
    assert normalize("œsophagus") == "œsophagus"
    assert normalize("encyclopædia") == "encyclopædia"


def test_presentation_ligature_ffi_rejected():
    # U+FB03 LATIN SMALL LIGATURE FFI. NFKC would launder it into "ffi";
    # the grammar uses NFC and rejects it instead.
    assert normalize("eﬃcient") is None


def test_fullwidth_letters_rejected():
    # U+FF41 FULLWIDTH LATIN SMALL LETTER A — an NFKC-only equivalence.
    assert normalize("ａpple") is None


# ---------------------------------------------------------------------------
# The closed accent inventory
# ---------------------------------------------------------------------------

def test_declared_accents_accepted():
    for w in ("café", "résumé", "señor", "façade", "naïve", "coöperate",
              "reëlect", "belovèd", "learnèd", "crème", "crêpe", "naïveté",
              "jalapeño", "über"):
        assert normalize(w) == w, w


def test_undeclared_accents_rejected():
    assert normalize("smörgåsbord") is None   # å not declared
    assert normalize("søster") is None             # ø not declared
    assert normalize("ćevapi") is None             # ć not declared
    assert normalize("škoda") is None              # š not declared


def test_inventory_counts_are_what_the_docs_claim():
    assert len(grammar.ACCENTED) == 19
    assert len(grammar.LIGATURES) == 2
    assert len(grammar.LETTERS) == 47
    assert len(grammar.CHARSET) == 50     # 49 + the space (C-015)
    assert grammar.DIAERESIS < grammar.ACCENTED
    assert len(grammar.DIAERESIS) == 5


# ---------------------------------------------------------------------------
# Hyphen structure
# ---------------------------------------------------------------------------

def test_interior_hyphens_accepted():
    for w in ("runner-up", "mother-in-law", "jack-of-all-trades",
              "across-the-board", "day-to-day", "cat-o'-nine-tails"):
        assert normalize(w) == w, w


def test_leading_hyphen_rejected():
    assert normalize("-up") is None


def test_trailing_hyphen_rejected():
    # The truncated fragments (self-, high-) deleted by the EOL's form-rule
    # audit stay out of the CEOL too.
    assert normalize("self-") is None


def test_doubled_hyphen_rejected():
    assert normalize("a--b") is None


def test_bare_hyphen_rejected():
    assert normalize("-") is None


def test_hyphen_segment_must_carry_a_letter():
    assert normalize("a-'-b") is None


# ---------------------------------------------------------------------------
# Apostrophe structure
# ---------------------------------------------------------------------------

def test_interior_apostrophes_accepted():
    for w in ("can't", "won't", "o'clock", "ma'am", "y'all", "o'er",
              "ne'er-do-well", "jack-o'-lantern", "will-o'-the-wisp",
              "fo'c's'le"):
        assert normalize(w) == w, w


def test_leading_apostrophe_accepted_the_tis_class():
    for w in ("'tis", "'twas", "'em", "'gainst"):
        assert normalize(w) == w, w


def test_trailing_apostrophe_rejected_pending_possessive_gate():
    # Plural possessives (dogs') arrive only if the C1 gate admits the
    # possessive class, via a recorded grammar extension.
    assert normalize("dogs'") is None
    assert normalize("tis'") is None


def test_doubled_apostrophe_rejected():
    assert normalize("''tis") is None


def test_bare_apostrophe_rejected():
    assert normalize("'") is None
    assert normalize("''") is None


# ---------------------------------------------------------------------------
# Degenerate input
# ---------------------------------------------------------------------------

def test_empty_and_whitespace_rejected():
    assert normalize("") is None
    assert normalize(" ") is None       # a bare space carries no letter
    assert normalize("\t") is None


def test_digits_rejected():
    # "ice cream" left this test at C-015: spaced terms are candidates now
    # (see the spaced-form section below). Digits remain out.
    assert normalize("mp3") is None
    assert normalize("7up") is None
    assert normalize("mp 3") is None    # a space does not launder a digit


def test_plain_words_pass_unchanged():
    assert normalize("word") == "word"
    assert normalize("a") == "a"          # D-025 heritage: no length bound
    assert normalize("i") == "i"


def test_every_declared_letter_roundtrips():
    for c in sorted(grammar.LETTERS):
        assert normalize(c) == c, repr(c)


# ---------------------------------------------------------------------------
# Census classes
# ---------------------------------------------------------------------------

def test_class_flags():
    assert classes("runner-up") == {"hyphenated"}
    assert classes("café") == {"accented"}
    assert classes("naïve") == {"diaeresis"}
    assert classes("naïveté") == {"accented", "diaeresis"}
    assert classes("æon") == {"ligature"}
    assert classes("word") == set()


def test_contraction_vs_apostrophe_form():
    assert classes("can't") == {"apostrophe-form", "contraction"}
    assert classes("she'll") == {"apostrophe-form", "contraction"}
    assert classes("'tis") == {"apostrophe-form", "contraction"}
    assert classes("o'clock") == {"apostrophe-form"}
    assert classes("o'er") == {"apostrophe-form"}       # medial elision
    assert classes("ma'am") == {"apostrophe-form"}


def test_s_final_is_a_diagnostic_not_a_contraction():
    # robin's is "robin is" AND "of robin" in one surface form; the census
    # counts it s-final and lets the possessive gate rule on the class.
    assert classes("robin's") == {"apostrophe-form", "s-final"}
    assert not is_contraction("robin's")


def test_mixed_classes_compose():
    assert classes("jack-o'-lantern") == {"hyphenated", "apostrophe-form"}
    assert classes("ne'er-do-well") == {"hyphenated", "apostrophe-form"}


# ---------------------------------------------------------------------------
# Spaced forms (C-015; space rules provisional under J1 until the S4 gate)
# ---------------------------------------------------------------------------

def test_spaced_terms_accepted():
    assert normalize("ice cream") == "ice cream"
    assert normalize("ad hominem") == "ad hominem"
    assert normalize("kick the bucket") == "kick the bucket"
    assert normalize("carte blanche") == "carte blanche"


def test_spaced_normalization_lowercases_and_composes():
    assert normalize("Ad Hominem") == "ad hominem"
    # NFD input with combining marks composes on both sides of the space;
    # built programmatically so no editor can silently re-compose the literal
    composed = "crème brûlée"
    decomposed = unicodedata.normalize("NFD", composed)
    assert len(composed) == 12 and len(decomposed) == 15
    assert normalize(decomposed) == composed


def test_spaced_output_is_nfc_and_idempotent():
    for w in ("ice cream", "crème brûlée", "jack-in-the-box surprise",
              "'tis the season"):
        out = normalize(w)
        assert out is not None
        assert unicodedata.is_normalized("NFC", out)
        assert normalize(out) == out


def test_leading_trailing_consecutive_spaces_rejected():
    assert normalize(" ice cream") is None
    assert normalize("ice cream ") is None
    assert normalize("ice  cream") is None
    assert normalize("   ") is None


def test_nbsp_folds_to_space():
    # U+00A0 is the second declared canonicalization (C-015); the literal
    # is escape-built so no editor can silently swap it for a plain space
    s = "ad\u00a0hoc"
    assert " " not in s and len(s) == 6
    assert normalize(s) == "ad hoc"
    assert normalize("ad \u00a0hoc") is None   # fold, then doubled space
    assert normalize("\u00a0adhoc") is None    # fold, then leading space


def test_other_whitespace_rejected_not_folded():
    # every whitespace look-alike except U+00A0 is rejected, not folded:
    # tab, LF, CR, ogham space, en/em quads and spaces, thin/hair space,
    # line/para separators, narrow no-break, math space, ideographic space
    for ws in ("\t", "\n", "\r", "\u1680", "\u2000", "\u2001", "\u2002",
               "\u2003", "\u2004", "\u2005", "\u2006", "\u2007",
               "\u2008", "\u2009", "\u200a", "\u2028", "\u2029",
               "\u202f", "\u205f", "\u3000"):
        assert normalize(f"ad{ws}hoc") is None, repr(ws)
    # zero-width characters are not spaces and are equally rejected
    for zw in ("\u200b", "\u2060", "\ufeff"):
        assert normalize(f"ad{zw}hoc") is None, repr(zw)


def test_underscore_never_admitted():
    # MediaWiki titles decode "_" to space at ingest parse; the grammar
    # itself never sees or admits an underscore.
    assert normalize("ad_hoc") is None
    assert normalize("_") is None


def test_lower_not_casefold_across_spaced_forms():
    # eszett must not launder to ss inside a spaced term either
    assert normalize("straße haus") is None


def test_each_token_carries_the_single_token_rules():
    assert normalize("foo- bar") is None       # token-trailing hyphen
    assert normalize("foo -bar") is None       # token-leading hyphen
    assert normalize("foo bar'") is None       # token-trailing apostrophe
    assert normalize("rock 'n' roll") is None  # J1 provisional: 'n' is
    #                                            apostrophe-final; the S3
    #                                            census counts this class
    assert normalize("o' clock") is None
    assert normalize("'tis the season") == "'tis the season"


def test_spaced_class_flags_compose():
    assert classes("ice cream") == {"spaced"}
    assert classes("crème brûlée") == {"spaced", "accented"}
    assert classes("jack-in-the-box surprise") == {"spaced", "hyphenated"}
    assert classes("can't stand") == {"spaced", "apostrophe-form",
                                      "contraction"}
    assert classes("no man's land") == {"spaced", "apostrophe-form",
                                        "s-final"}
    assert classes("word") == set()


def test_token_count():
    assert grammar.token_count("word") == 1
    assert grammar.token_count("ice cream") == 2
    assert grammar.token_count("kick the bucket") == 3
