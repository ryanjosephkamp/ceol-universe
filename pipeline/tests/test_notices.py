"""The NOTICES file of v1.0 (research/release/notices.py; the archive's
C-079 line 2(d)): it carries a section
for every published source, the texts that must travel verbatim, and,
where the pinned inputs are on this machine, it is the generator's output
byte for byte."""

from __future__ import annotations

import pytest

from research.release import notices

COMMITTED = notices.OUT_DIR / "NOTICES_v1.0.md"


def test_every_published_source_has_its_section():
    text = COMMITTED.read_text(encoding="utf-8")
    for heading in ("## The English Wiktionary", "## WordNet 3.0",
                    "## SCOWL 2020.12.07", "## The en_GB hunspell dictionary",
                    "## ENABLE", "## wordfreq 3.1.1", "## The Google Books Ngram corpus",
                    "## The English OpenList"):
        assert heading in text, heading
    # the conditions the review names: WordNet's notice on all copies, UKACD's
    # verbatim notice, the SUBTLEX conditions, the credit to Robyn Speer
    for phrase in ("appear on ALL copies", "must be included",
                   "freely available data", "Robyn Speer",
                   "eol:dictionary-api:free-dictionary"):
        assert phrase in text, phrase
    # no withheld list's notice, name, or label, and no withheld channel label
    import re
    from research.release import withholding as W
    # a name at a sentence's end keeps no trailing period (N-3)
    tokens = {t.rstrip(".:-") for t in re.findall(r"[A-Za-z0-9_:.\-]+", text)}
    for name in sorted(W.WITHHELD_CHANNEL_LABELS | W.WITHHELD_LABELS):
        assert name not in tokens, name
    for name in ("NWL2023", "CSW21", "SOWPODS"):
        assert name.lower() not in text.lower(), name


def test_the_committed_file_is_the_generator_s_output():
    try:
        text = notices.render("v1.0", notices.inputs())
    except notices.InputAbsent as exc:
        pytest.skip(f"the pinned input {exc} is absent here (a declared deferral)")
    assert COMMITTED.read_text(encoding="utf-8") == text


def test_an_excerpt_marks_what_it_omits():
    text = "\n".join(f"l{i}" for i in range(1, 11))
    assert notices._lines(text, ((1, 2), (5, 5))) == "l1\nl2\n[lines 3 to 4 omitted]\nl5"
