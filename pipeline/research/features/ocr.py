"""
The typed OCR-confusion channel under the wider alphabet — C-011.

The six D-012 pairs carry over verbatim. Four wider-alphabet families are
PROPOSED and individually gated (AUC lower-95 >= 0.60 against matched
corruptions AND corruption fire rate >= 5x real fire rate); a family
failing its gate ships nothing and the failure is reported. Directions
follow the physical error:

    diacritic-strip     café  -> cafe    (the scan loses the mark)
    hyphen-junction     wx    -> w-x     (line-wrap hyphenation invents -)
    hyphen-drop         w-x   -> wx      (the scan loses the hyphen)
    apostrophe-loss     don't -> dont    (the scan loses the apostrophe)
    ligature-expansion  æon   -> aeon    (æ reads as ae; VARIANT-CONFOUNDED
                                          by design — the gate decides)

Detection is always artifact -> source back-substitution against a
reference the source class can live in: the base reference (WordNet ∪
web2) for a-z sources, the declared class-capable reference for accented,
apostrophe and ligature sources.
"""

from __future__ import annotations

#: (source_glyph, artifact_glyph) — the scan turns source into artifact.
CONFUSIONS = [
    ("m", "in"),
    ("rn", "m"),
    ("l", "i"),
    ("e", "c"),
    ("c", "e"),
    ("li", "h"),
]

#: accent -> stripped base, the diacritic-strip family's glyph map.
STRIP = {"á": "a", "à": "a", "â": "a", "ä": "a", "é": "e", "è": "e",
         "ê": "e", "ë": "e", "í": "i", "î": "i", "ï": "i", "ñ": "n",
         "ó": "o", "ô": "o", "ö": "o", "ú": "u", "û": "u", "ü": "u",
         "ç": "c"}
LIGATURE_EXPANSION = {"æ": "ae", "œ": "oe"}
BASE_TO_ACCENTS: dict[str, list[str]] = {}
for _acc, _base in STRIP.items():
    BASE_TO_ACCENTS.setdefault(_base, []).append(_acc)


def detect_neighbors(word: str, reference: set[str]):
    """The six typed pairs: yield (source_word, (src, art)) for every
    single-site back-substitution landing in the reference."""
    seen = set()
    for src, art in CONFUSIONS:
        start = 0
        while True:
            i = word.find(art, start)
            if i < 0:
                break
            cand = word[:i] + src + word[i + len(art):]
            if cand != word and cand in reference and cand not in seen:
                seen.add(cand)
                yield cand, (src, art)
            start = i + 1


def corrupt(word: str, site_unit: float):
    """One typed corruption source->artifact, site chosen by hash unit."""
    sites = []
    for src, art in CONFUSIONS:
        start = 0
        while True:
            i = word.find(src, start)
            if i < 0:
                break
            sites.append((i, src, art))
            start = i + 1
    if not sites:
        return None
    i, src, art = sites[int(site_unit * len(sites)) % len(sites)]
    return word[:i] + art + word[i + len(src):]


# -- the proposed families: detection (artifact -> source) ------------------

def detect_diacritic_source(word: str, accent_reference: set[str]):
    """Plain candidate -> accented restorations found in the reference."""
    out = []
    for i, c in enumerate(word):
        for acc in BASE_TO_ACCENTS.get(c, ()):
            cand = word[:i] + acc + word[i + 1:]
            if cand in accent_reference:
                out.append(cand)
    return out


def detect_hyphen_junction_source(word: str, reference: set[str]):
    """Hyphenated candidate -> its concatenation, if attested plain."""
    if "-" not in word:
        return []
    concat = word.replace("-", "")
    return [concat] if concat in reference else []


def detect_hyphen_drop_source(word: str, hyphen_reference: set[str]):
    """Plain candidate -> attested hyphenated restorations."""
    out = []
    for i in range(1, len(word)):
        cand = word[:i] + "-" + word[i:]
        if cand in hyphen_reference:
            out.append(cand)
    return out


def detect_apostrophe_source(word: str, apostrophe_reference: set[str]):
    """Plain candidate -> attested apostrophe restorations."""
    out = []
    for i in range(1, len(word) + 1):
        cand = word[:i] + "'" + word[i:]
        if cand in apostrophe_reference:
            out.append(cand)
    return out


def detect_ligature_source(word: str, ligature_reference: set[str]):
    """Plain candidate -> attested ligature restorations (ae->æ, oe->œ)."""
    out = []
    for lig, exp in LIGATURE_EXPANSION.items():
        start = 0
        while True:
            i = word.find(exp, start)
            if i < 0:
                break
            cand = word[:i] + lig + word[i + len(exp):]
            if cand in ligature_reference:
                out.append(cand)
            start = i + 1
    return out


#: family name -> (corruption fn: source word -> artifact, or None when the
#: family manufactures corruptions by stripping)
def corrupt_diacritic(word: str) -> str | None:
    """café -> cafe; None when the word carries no accent."""
    if not any(c in STRIP for c in word):
        return None
    return "".join(STRIP.get(c, c) for c in word)


def corrupt_hyphen_junction(word: str, site_unit: float) -> str | None:
    """Insert a line-wrap hyphen into a plain word at a hash-chosen site."""
    if "-" in word or len(word) < 4:
        return None
    site = 1 + int(site_unit * (len(word) - 2)) % (len(word) - 1)
    return word[:site] + "-" + word[site:]


def corrupt_hyphen_drop(word: str) -> str | None:
    """well-being -> wellbeing; None for non-hyphenated words."""
    return word.replace("-", "") if "-" in word else None


def corrupt_apostrophe_loss(word: str) -> str | None:
    """don't -> dont; None for words without apostrophes."""
    return word.replace("'", "") if "'" in word else None


def corrupt_ligature(word: str) -> str | None:
    """æon -> aeon; None for words without ligatures."""
    if not any(c in LIGATURE_EXPANSION for c in word):
        return None
    out = word
    for lig, exp in LIGATURE_EXPANSION.items():
        out = out.replace(lig, exp)
    return out
