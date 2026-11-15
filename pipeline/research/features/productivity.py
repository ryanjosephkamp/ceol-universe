"""
Morphological productivity under the CEOL grammar — the EOL module
(english-openlist@496bf1f research/features/productivity.py) ported with
one extension: the SEGMENT-ATTESTATION measure for hyphenated words
(C-011), the compound analogue of stem attestation. Realized productivity
V/N per affix stays the shipped measure; Baayen's potential P remains
non-computable (the GB 2020 floor of 40 holds in the CEOL re-stream too,
and the zero hapax columns stay visible in the table).
"""

from __future__ import annotations

SUFFIXES = [
    "s", "es", "ed", "ing", "ings", "er", "ers", "est", "ly", "ness",
    "nesses", "ish", "able", "ible", "ation", "ations", "ize", "ise",
    "ized", "ised", "izes", "ises", "izing", "ising", "ic", "al", "ous",
    "ment", "ments", "ity", "ities", "less", "ful", "dom", "hood", "ship",
    "like", "oses", "osis", "ette", "ism", "isms", "ist", "ists",
]
PREFIXES = [
    "un", "non", "re", "de", "anti", "pre", "over", "under", "out",
    "micro", "pseudo", "quasi", "super", "sub", "inter", "intra", "multi",
]
MIN_STEM = 3


def stem_variants(stem: str):
    yield stem
    yield stem + "e"
    if len(stem) >= 2 and stem[-1] == stem[-2]:
        yield stem[:-1]
    if stem.endswith("i"):
        yield stem[:-1] + "y"


def parse_suffix(word: str, reference: set[str]):
    for suf in sorted(SUFFIXES, key=len, reverse=True):
        if word.endswith(suf) and len(word) - len(suf) >= MIN_STEM:
            stem = word[: len(word) - len(suf)]
            for v in stem_variants(stem):
                if v in reference:
                    return suf, v
    return None


def parse_prefix(word: str, reference: set[str]):
    for pre in sorted(PREFIXES, key=len, reverse=True):
        if word.startswith(pre) and len(word) - len(pre) >= MIN_STEM:
            rest = word[len(pre):]
            if rest in reference:
                return pre, rest
    return None


def segment_attestation(word: str, reference: set[str]) -> float | None:
    """Fraction of a hyphenated word's segments attested plain in the
    reference — day-to-day: day✓ to✓ day✓ = 1.0. None for non-hyphenated
    words (the measure is the compound analogue of stem attestation and
    means nothing off the class)."""
    if "-" not in word:
        return None
    segments = word.split("-")
    return sum(1 for s in segments if s in reference) / len(segments)


def affix_table(gb_words, gb_match, gb_volume, reference: set[str]) -> dict:
    stats = {("suffix", s): [0, 0, 0, float("inf")] for s in SUFFIXES}
    stats.update({("prefix", p): [0, 0, 0, float("inf")] for p in PREFIXES})
    for w, tm, tv in zip(gb_words, gb_match, gb_volume):
        ps = parse_suffix(w, reference)
        if ps:
            row = stats[("suffix", ps[0])]
            row[0] += int(tm)
            row[1] += 1
            if tv == 1:
                row[2] += 1
            if tm < row[3]:
                row[3] = tm
        pp = parse_prefix(w, reference)
        if pp:
            row = stats[("prefix", pp[0])]
            row[0] += int(tm)
            row[1] += 1
            if tv == 1:
                row[2] += 1
            if tm < row[3]:
                row[3] = tm
    out = {}
    for key, (N, V, n1_vol, min_match) in stats.items():
        out[key] = {
            "N_tokens": N, "V_types": V, "n1_volume": n1_vol,
            "min_match_seen": None if min_match == float("inf")
            else int(min_match),
            "P_vol": (n1_vol / N) if N else None,
            "P_vn": (V / N) if N else None,
        }
    return out
