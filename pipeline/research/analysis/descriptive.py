"""The descriptive analysis of a public version (docs/ANALYSIS_PLAN.md,
adopted by D-007): counts, shares, and distributions over the release files
alone, for the technical report and the site's Research section.

    python3 -m research.analysis.descriptive --version v1.0          write it
    python3 -m research.analysis.descriptive --version v1.0 --check  compare

It reads the version's `universe` and `features` files, each held to the
release record's sha256 before it is read, and writes
`research/release/figures/<version>/analysis.json`: 1 entry per question of
the plan it answers, under the plan's id (F1, S2, U5, ...), each with its
unit, the rows it counts, and whether it is exact. Every count is exact: it
is a count of the release's rows, with no sampling and no estimate. The
file is deterministic, so the check rebuilds it and compares byte for byte;
the runtime is printed, never written.

Counts only: no string of the universe is written or printed, and a figure
names a list, a class, or a band, never a row.

The populations follow the plan (§2). The public panel is the 8 published
lists in 5 families: WordNet, Wiktionary's English pages, hunspell (its 4
dictionaries counted as 1 family), ENABLE, and SCOWL. A single-token row
holds each list's evidence (1 listed, 0 not listed, -1 the list cannot hold
the row's class); a spaced row is measured by WordNet and Wiktionary only,
through `panel_sets`. A family lists a row when any of its lists does, and
cannot hold it when none of its lists can. The evidence tier of a
single-token row is the number of families that list it: 2 or more, 1, or
none, and a row no family lists is "corpus only" when Google Books or
wordfreq holds it and "no evidence" otherwise.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from ceol.ingest.common import sha256_file
from research.release import build_release as B

REPO = B.REPO

#: the published lists, in the order of a listing code's digits
LISTS = ("wordnet", "wiktionary_english", "hunspell_en_US", "hunspell_en_GB",
         "hunspell_en_CA", "hunspell_en_AU", "enable1", "scowl")
LIST_NAMES = {"wordnet": "WordNet", "wiktionary_english": "Wiktionary (English)",
              "hunspell_en_US": "hunspell en_US", "hunspell_en_GB": "hunspell en_GB",
              "hunspell_en_CA": "hunspell en_CA", "hunspell_en_AU": "hunspell en_AU",
              "enable1": "ENABLE", "scowl": "SCOWL"}
#: the families and the indices of their lists in LISTS
FAMILIES = (("WordNet", (0,)), ("Wiktionary", (1,)), ("hunspell", (2, 3, 4, 5)),
            ("ENABLE", (6,)), ("SCOWL", (7,)))
TIERS = ("2+ families", "1 family", "corpus only", "no evidence")
GROUPS = TIERS + ("multiword",)
#: the class flags of `class_explicit`; a row with none is plain
FLAGS = ("accented", "apostrophe-form", "contraction", "diaeresis",
         "hyphenated", "ligature", "s-final", "spaced")
#: wordfreq's Zipf value in bands; a row with no value is its own band
ZIPF_EDGES = (1.0, 2.0, 3.0, 4.0, 5.0)
ZIPF_BANDS = ("no value", "under 1", "1 to 2", "2 to 3", "3 to 4", "4 to 5", "5 and over")
LENGTH_CAP = 40
#: the Zipf value at or above which an unlisted row counts as frequent (S14)
FREQUENT = (3.0, 4.0)
#: the most intake channels listed by name in P4; the rest are summed
CHANNELS_SHOWN = 40


class AnalysisError(Exception):
    pass


def out_path(version: str) -> Path:
    return REPO / "research" / "release" / "figures" / version / "analysis.json"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO.parent).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

def share(part: int, whole: int) -> float | None:
    return None if not whole else round(part / whole, 6)


def wilson(part: int, whole: int, z: float = 1.959964) -> list[float] | None:
    """The 95% Wilson interval of a share, or None for an empty band."""
    if not whole:
        return None
    p = part / whole
    d = 1 + z * z / whole
    c = (p + z * z / (2 * whole)) / d
    h = z * math.sqrt(p * (1 - p) / whole + z * z / (4 * whole * whole)) / d
    return [round(max(0.0, c - h), 6), round(min(1.0, c + h), 6)]


def quantiles(values: np.ndarray, qs=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99)) -> dict:
    """Quantiles by the nearest-rank rule, so integer data stays integer."""
    if values.size == 0:
        return {"n": 0}
    s = np.sort(values)
    out = {"n": int(s.size), "min": _num(s[0]), "max": _num(s[-1])}
    for q in qs:
        out[f"p{round(q * 100):d}"] = _num(s[max(0, math.ceil(q * s.size) - 1)])
    return out


def _num(x):
    x = x.item() if hasattr(x, "item") else x
    return round(x, 6) if isinstance(x, float) else x


def histogram(values: np.ndarray, edges: list[float]) -> list[int]:
    """Counts in [edges[i], edges[i+1]); the last bin is closed."""
    counts, _ = np.histogram(values, bins=np.asarray(edges, dtype=float))
    return [int(c) for c in counts]



def tier_histograms(values: np.ndarray, tier: np.ndarray, edges: list[float]) -> dict:
    """Per evidence tier: the rows, the rows with a value, the histogram of
    the values over `edges`, and their quantiles. Every measured value must
    fall inside the edges, so that each histogram accounts for its rows."""
    res = {}
    for t, name in enumerate(TIERS):
        v = values[tier == t]
        has = ~np.isnan(v)
        counts = histogram(v[has], edges)
        if sum(counts) != int(has.sum()):
            raise ValueError(f"{name}: {int(has.sum()) - sum(counts)} measured values "
                             f"fall outside the edges {edges[0]} to {edges[-1]}")
        res[name] = {"rows": int(v.size), "with_value": int(has.sum()),
                     "counts": counts, "quantiles": quantiles(v[has])}
    return res

def family_codes(lists: np.ndarray) -> np.ndarray:
    """The 5 families' evidence from the 8 lists' (n x 8, values 1, 0, -1):
    1 where any list of the family lists the row, -1 where none can hold
    it, else 0."""
    out = np.empty((lists.shape[0], len(FAMILIES)), dtype=np.int8)
    for j, (_name, idx) in enumerate(FAMILIES):
        block = lists[:, idx]
        listed = (block == 1).any(axis=1)
        blind = (block == -1).all(axis=1)
        out[:, j] = np.where(listed, 1, np.where(blind, -1, 0))
    return out


def tiers(families: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """The evidence tier of each single-token row, as an index into TIERS."""
    k = (families == 1).sum(axis=1)
    return np.where(k >= 2, 0, np.where(k == 1, 1, np.where(corpus, 2, 3))).astype(np.int8)


def encode(codes: np.ndarray) -> np.ndarray:
    """Each row's listing as 1 number: the codes' digits in base 3, with 0
    for not listed, 1 for listed, and 2 for cannot hold."""
    digit = np.where(codes == -1, 2, codes).astype(np.int64)
    out = np.zeros(codes.shape[0], dtype=np.int64)
    for j in range(codes.shape[1]):
        out = out * 3 + digit[:, j]
    return out


def decode(code: int, width: int) -> list[int]:
    digits = []
    for _ in range(width):
        code, d = divmod(code, 3)
        digits.append(-1 if d == 2 else d)
    return digits[::-1]


def combos(codes: np.ndarray, *keys: np.ndarray) -> dict[tuple, int]:
    """The rows per listing code, optionally crossed with small integer keys."""
    enc = encode(codes)
    parts = [enc]
    for k in keys:
        parts.append(k.astype(np.int64))
    stacked = np.stack(parts, axis=1)
    uniq, counts = np.unique(stacked, axis=0, return_counts=True)
    return {tuple(int(x) for x in u): int(c) for u, c in zip(uniq, counts)}


# ---------------------------------------------------------------------------
# The analyses over the listing histogram (the plan's level 3)
# ---------------------------------------------------------------------------

def containment(hist: dict[tuple, int], width: int) -> dict:
    """S2: for each ordered pair (A, B), of A's rows that B can hold, the
    rows B lists; A's rows B cannot hold; and the Jaccard index over the rows
    both can hold."""
    rows = [(decode(k[0], width), n) for k, n in hist.items()]
    out = {"contained": [], "eligible": [], "blind": [], "a_listed": [],
           "both": [], "either": []}
    for a in range(width):
        r = {key: [] for key in out}
        for b in range(width):
            a_listed = sum(n for d, n in rows if d[a] == 1)
            eligible = sum(n for d, n in rows if d[a] == 1 and d[b] != -1)
            contained = sum(n for d, n in rows if d[a] == 1 and d[b] == 1)
            blind = sum(n for d, n in rows if d[a] == 1 and d[b] == -1)
            both_hold = [(d, n) for d, n in rows if d[a] != -1 and d[b] != -1]
            both = sum(n for d, n in both_hold if d[a] == 1 and d[b] == 1)
            either = sum(n for d, n in both_hold if d[a] == 1 or d[b] == 1)
            for key, v in (("contained", contained), ("eligible", eligible),
                           ("blind", blind), ("a_listed", a_listed),
                           ("both", both), ("either", either)):
                r[key].append(v)
        for key in out:
            out[key].append(r[key])
    return out


def k_of_m(hist: dict[tuple, int], width: int, n_keys: int = 0) -> dict[tuple, int]:
    """S5: rows by (m, k): m the families that can hold the row, k those
    that list it, crossed with any keys the histogram carries."""
    out: dict[tuple, int] = {}
    for key, n in hist.items():
        d = decode(key[0], width)
        m = sum(1 for x in d if x != -1)
        k = sum(1 for x in d if x == 1)
        kk = (m, k) + tuple(key[1:1 + n_keys])
        out[kk] = out.get(kk, 0) + n
    return out


def unions(hist: dict[tuple, int], width: int) -> list[int]:
    """The rows listed by at least 1 list of each subset of the lists, by the
    subset's bitmask (bit j for list j)."""
    listed_masks: dict[int, int] = {}
    for key, n in hist.items():
        d = decode(key[0], width)
        mask = sum(1 << j for j, x in enumerate(d) if x == 1)
        listed_masks[mask] = listed_masks.get(mask, 0) + n
    return [sum(n for m, n in listed_masks.items() if m & s) for s in range(1 << width)]


def accumulation(union: list[int], width: int) -> list[dict]:
    """S13: the union's size as lists are added in every order. For a random
    order the first k lists are a uniform k-subset, so the mean curve is the
    mean over k-subsets, and its range is their minimum and maximum."""
    out = []
    for k in range(width + 1):
        sizes = [union[s] for s in range(1 << width) if bin(s).count("1") == k]
        out.append({"lists": k, "mean": round(sum(sizes) / len(sizes), 3),
                    "min": min(sizes), "max": max(sizes), "subsets": len(sizes)})
    return out


# ---------------------------------------------------------------------------
# Reading the release
# ---------------------------------------------------------------------------

UNIVERSE_COLUMNS = ("id", "word", "token_count", "class_explicit", "panel_sets",
                    "provenance_class", "intake_layer", "intake_kind",
                    "intake_channels", "eol", "gb_type", "wordfreq_scored",
                    "eol_synthetic_engine_inferred", "model_or_engine",
                    "variety_gb_not_us", "variety_us_not_gb", "scowl_tier",
                    *LISTS[:-1])
FEATURE_COLUMNS = ("id", "wordfreq_zipf", "gb_log10_match", "gb_year_span",
                   "gb_span_fill", "zipf_resid")


def _read(spec: B.VersionSpec, record: dict, config: str, columns) -> "object":
    import pyarrow.parquet as pq
    files = {f["config"]: f for f in record["files"]}
    path = spec.out_dir / files[config]["path"]
    if sha256_file(path) != files[config]["sha256"]:
        raise AnalysisError(f"{_rel(path)} is not the file the release record names")
    return pq.read_table(path, columns=list(columns))


class Release:
    """The columns the analysis reads, as numpy arrays, single-token rows
    and spaced rows apart, the features aligned to the single-token rows."""

    def __init__(self, universe, features):
        import pyarrow.compute as pc
        self.n = universe.num_rows
        tok = universe["token_count"].to_numpy()
        self.single = tok == 1
        self.spaced = ~self.single
        self.token_count = tok
        lists = np.empty((self.n, len(LISTS)), dtype=np.int8)
        for j, name in enumerate(LISTS[:-1]):
            lists[:, j] = universe[name].fill_null(0).to_numpy()
        scowl = universe["scowl_tier"].fill_null(0).to_numpy()
        lists[:, 7] = np.where(scowl > 0, 1, np.where(scowl == -1, -1, 0))
        self.lists = lists[self.single]
        self.families = family_codes(self.lists)
        gb = universe["gb_type"].fill_null(False).to_numpy(zero_copy_only=False)
        wf = universe["wordfreq_scored"].fill_null(False).to_numpy(zero_copy_only=False)
        self.corpus = (gb | wf)[self.single]
        self.gb = gb[self.single]
        self.tier = tiers(self.families, self.corpus)
        # the group of every row: its tier, or multiword
        group = np.full(self.n, 4, dtype=np.int8)
        group[self.single] = self.tier
        self.group = group
        self.word = universe["word"]
        self.length = pc.utf8_length(self.word).to_numpy()
        self.flag = {f: pc.match_substring(universe["class_explicit"], f).to_numpy(zero_copy_only=False)
                     for f in FLAGS}
        ps = universe["panel_sets"]
        self.spaced_wordnet = pc.match_substring(ps, "wordnet").to_numpy(zero_copy_only=False)[self.spaced]
        self.spaced_wiktionary = pc.match_substring(ps, "wiktionary_english").to_numpy(zero_copy_only=False)[self.spaced]
        self.universe = universe
        # the features config holds the single-token rows in the universe's order
        ids_u = universe["id"].filter(pc.equal(universe["token_count"], 1))
        if not ids_u.equals(features["id"]):
            raise AnalysisError("the features config is not the universe's single-token rows in order")
        self.zipf = features["wordfreq_zipf"].to_numpy(zero_copy_only=False).astype(np.float64)
        self.gb_match = features["gb_log10_match"].to_numpy(zero_copy_only=False).astype(np.float64)
        self.gb_span = features["gb_year_span"].to_numpy(zero_copy_only=False)
        self.gb_fill = features["gb_span_fill"].to_numpy(zero_copy_only=False).astype(np.float64)
        self.zipf_resid = features["zipf_resid"].to_numpy(zero_copy_only=False).astype(np.float64)

    def zipf_band(self) -> np.ndarray:
        z = self.zipf
        band = np.zeros(z.size, dtype=np.int8)
        has = ~np.isnan(z)
        band[has] = 1 + np.searchsorted(np.asarray(ZIPF_EDGES), z[has], side="right")
        return band


# ---------------------------------------------------------------------------
# The analyses
# ---------------------------------------------------------------------------

def _entry(eid: str, question: str, unit: str, population: str, data: dict,
           note: str | None = None) -> dict:
    out = {"id": eid, "question": question, "unit": unit, "population": population,
           "exact": True, "data": data}
    if note:
        out["note"] = note
    return out


def level_1(r: Release) -> list[dict]:
    import pyarrow.compute as pc
    from ceol import grammar as G
    out = []
    # F1: length and tokens
    by_group = {}
    for g, name in enumerate(GROUPS):
        sel = r.group == g
        lengths = r.length[sel]
        capped = np.minimum(lengths, LENGTH_CAP)
        counts = np.bincount(capped, minlength=LENGTH_CAP + 1)[1:]
        by_group[name] = {"rows": int(sel.sum()), "quantiles": quantiles(lengths),
                          "counts": [int(c) for c in counts]}
    toks = np.bincount(np.minimum(r.token_count, 10), minlength=11)[1:]
    out.append(_entry(
        "F1", "How long are the candidates?", "rows",
        "every row, by evidence tier and multiword",
        {"length_unit": "characters (code points)", "length_cap": LENGTH_CAP,
         "length_bins": [str(i) for i in range(1, LENGTH_CAP)] + [f"{LENGTH_CAP}+"],
         "by_group": by_group,
         "tokens": {"bins": [str(i) for i in range(1, 10)] + ["10+"],
                    "counts": [int(c) for c in toks]}}))
    # F2: characters
    chars = sorted(G.LETTERS) + [G.HYPHEN, G.APOSTROPHE, G.SPACE]
    use = {}
    for ch in chars:
        hit = pc.match_substring(r.word, ch).to_numpy(zero_copy_only=False)
        use[ch] = [int((hit & (r.group == g)).sum()) for g in range(len(GROUPS))]
    out.append(_entry(
        "F2", "Which characters do the candidates use?", "rows that use the character at least once",
        "every row, by evidence tier and multiword",
        {"groups": list(GROUPS), "characters": [
            {"character": ch, "name": _char_name(ch), "rows": use[ch]} for ch in chars]}))
    # F3: first and last characters, and the first 2 letters
    import pyarrow as pa
    first = pc.utf8_slice_codeunits(r.word, 0, 1)
    last = pc.utf8_slice_codeunits(r.word, -1)
    two = pc.utf8_slice_codeunits(r.word, 0, 2)
    base = sorted(G.BASE)
    groups = pa.array(r.group)
    def counts_of(values, keys):
        t = pa.table({"v": values, "g": groups}).group_by(["v", "g"]).aggregate([("v", "count")])
        m = {(v, g): n for v, g, n in zip(t["v"].to_pylist(), t["g"].to_pylist(), t["v_count"].to_pylist())}
        return {GROUPS[g]: [int(m.get((k, g), 0)) for k in keys] for g in range(len(GROUPS))}
    grid_keys = [a + b for a in base for b in base]
    out.append(_entry(
        "F3", "How do the candidates begin and end?", "rows",
        "every row, by evidence tier and multiword; the grid counts rows whose first 2 characters are both letters a to z",
        {"characters": chars, "first": counts_of(first, chars), "last": counts_of(last, chars),
         "grid_letters": base, "first_two": counts_of(two, grid_keys)}))
    # F4: the class flags and their combinations
    flag_rows = {f: [int((r.flag[f] & (r.group == g)).sum()) for g in range(len(GROUPS))] for f in FLAGS}
    co = [[int((r.flag[a] & r.flag[b]).sum()) for b in FLAGS] for a in FLAGS]
    vc = pc.value_counts(r.universe["class_explicit"]).to_pylist()
    inter = sorted(({"classes": d["values"], "rows": int(d["counts"])} for d in vc),
                   key=lambda d: (-d["rows"], d["classes"]))
    out.append(_entry(
        "F4", "How common is each spelling class, and which combine?", "rows",
        "every row; a row with no flag is plain",
        {"flags": list(FLAGS), "groups": list(GROUPS), "rows_by_flag": flag_rows,
         "co_occurrence": co, "combinations": inter}))
    # F6: the multiword terms
    tc = r.token_count[r.spaced]
    ln = r.length[r.spaced]
    wn, wk = r.spaced_wordnet, r.spaced_wiktionary
    out.append(_entry(
        "F6", "What do the multiword terms look like?", "rows",
        "the multiword rows, which WordNet and Wiktionary alone measure",
        {"rows": int(r.spaced.sum()),
         "tokens": {"bins": [str(i) for i in range(2, 10)] + ["10+"],
                    "counts": [int(x) for x in np.bincount(np.minimum(tc, 10), minlength=11)[2:]]},
         "length_quantiles": quantiles(ln),
         "sources": {"WordNet and Wiktionary": int((wn & wk).sum()), "WordNet only": int((wn & ~wk).sum()),
                     "Wiktionary only": int((~wn & wk).sum()), "neither": int((~wn & ~wk).sum())}}))
    # F8: the apostrophe forms
    ap = r.flag["apostrophe-form"]
    forms = {
        "contraction": r.flag["contraction"],
        "ends in 's": r.flag["s-final"],
        "other apostrophe form": ap & ~r.flag["contraction"] & ~r.flag["s-final"],
    }
    out.append(_entry(
        "F8", "Which apostrophe forms occur?", "rows",
        "the rows with an apostrophe, by evidence tier and multiword",
        {"groups": list(GROUPS), "rows": int(ap.sum()),
         "forms": {k: [int((v & (r.group == g)).sum()) for g in range(len(GROUPS))] for k, v in forms.items()}}))
    out.append(_variants(r))
    return out


def _char_name(ch: str) -> str:
    import unicodedata
    return {"-": "hyphen", "'": "apostrophe", " ": "space"}.get(ch, unicodedata.name(ch).lower())


def _variants(r: Release) -> dict:
    """F9: the groups of rows that differ only by hyphens, spaces,
    apostrophes, or accents (a diaeresis is an accent), and how many members
    of each group a published list holds."""
    import pyarrow as pa
    import pyarrow.compute as pc
    key = pc.replace_substring_regex(pc.utf8_normalize(r.word, "NFD"), r"[\p{Mn}\-' ]", "")
    listed = np.zeros(r.n, dtype=bool)
    listed[r.single] = (r.families == 1).any(axis=1)
    listed[r.spaced] = r.spaced_wordnet | r.spaced_wiktionary
    word = r.word
    has = {
        "hyphen": pc.match_substring(word, "-"),
        "space": pc.match_substring(word, " "),
        "apostrophe": pc.match_substring(word, "'"),
        "accent": pc.not_equal(pc.utf8_length(pc.utf8_normalize(word, "NFD")), pc.utf8_length(word)),
    }
    t = pa.table({"key": key, "listed": pa.array(listed), **has})
    g = t.group_by("key").aggregate(
        [("key", "count"), ("listed", "sum")]
        + [(k, "any") for k in has] + [(k, "all") for k in has])
    size = g["key_count"].to_numpy()
    multi = size >= 2
    sizes, size_counts = np.unique(size[multi], return_counts=True)
    pattern = np.zeros(g.num_rows, dtype=np.int64)
    names = list(has)
    for j, k in enumerate(names):
        varies = (g[f"{k}_any"].to_numpy(zero_copy_only=False)
                  & ~g[f"{k}_all"].to_numpy(zero_copy_only=False))
        pattern |= varies.astype(np.int64) << j
    pats, pat_counts = np.unique(pattern[multi], return_counts=True)
    listed_members = g["listed_sum"].to_numpy()[multi]
    two = size[multi] == 2
    return _entry(
        "F9", "How many candidates are variants of each other?", "groups of rows",
        "every row; a group is the rows that are equal once hyphens, spaces, apostrophes, and accents are removed",
        {"groups_of_2_or_more": int(multi.sum()), "rows_in_them": int(size[multi].sum()),
         "group_sizes": [{"size": int(s), "groups": int(c)} for s, c in zip(sizes, size_counts)],
         "patterns": sorted(({"varies_by": [names[j] for j in range(len(names)) if p >> j & 1],
                              "groups": int(c)} for p, c in zip(pats, pat_counts)),
                            key=lambda d: (-d["groups"], d["varies_by"])),
         "pairs_by_members_listed": {str(k): int(((listed_members == k) & two).sum()) for k in (0, 1, 2)}})


def level_3(r: Release) -> list[dict]:
    out = []
    width = len(LISTS)
    hist = combos(r.lists)
    # S1: each list's rows, by class, and its blind classes
    by_list = []
    for j, name in enumerate(LISTS):
        col = r.lists[:, j]
        row = {"list": LIST_NAMES[name], "listed": int((col == 1).sum()),
               "not_listed": int((col == 0).sum()), "cannot_hold": int((col == -1).sum()), "by_flag": {}}
        for f in FLAGS[:-1]:
            fl = r.flag[f][r.single]
            row["by_flag"][f] = {"listed": int(((col == 1) & fl).sum()), "cannot_hold": int(((col == -1) & fl).sum()),
                                 "rows": int(fl.sum())}
        plain = np.ones(int(r.single.sum()), dtype=bool)
        for f in FLAGS[:-1]:
            plain &= ~r.flag[f][r.single]
        row["by_flag"]["plain"] = {"listed": int(((col == 1) & plain).sum()),
                                   "cannot_hold": int(((col == -1) & plain).sum()), "rows": int(plain.sum())}
        by_list.append(row)
    spaced = {"rows": int(r.spaced.sum()), "WordNet": int(r.spaced_wordnet.sum()),
              "Wiktionary (English)": int(r.spaced_wiktionary.sum())}
    out.append(_entry("S1", "How large is each list inside the universe, and which classes can it hold?", "rows",
                      "the single-token rows; the multiword rows apart", {"lists": by_list, "multiword": spaced}))
    # S2: directed containment and Jaccard
    c = containment(hist, width)
    out.append(_entry(
        "S2", "How much does each pair of lists overlap?", "rows",
        "the single-token rows; a cell is list A's rows that list B can hold",
        {"lists": [LIST_NAMES[x] for x in LISTS], **c,
         "containment": [[share(c["contained"][a][b], c["eligible"][a][b]) for b in range(width)] for a in range(width)],
         "blind_share": [[share(c["blind"][a][b], c["a_listed"][a][b]) for b in range(width)] for a in range(width)],
         "jaccard": [[share(c["both"][a][b], c["either"][a][b]) for b in range(width)] for a in range(width)]},
        note="containment is the share of A's listed rows that B lists, of those B can hold; the blind share is A's listed rows B cannot hold; Jaccard is computed over the rows both can hold"))
    # S3: exact combinations of families, over the rows every family can hold
    fh = combos(r.families)
    fw = len(FAMILIES)
    exact = []
    for key, n in fh.items():
        d = decode(key[0], fw)
        if -1 in d:
            continue
        exact.append({"families": [FAMILIES[j][0] for j in range(fw) if d[j] == 1], "rows": n})
    exact.sort(key=lambda e: (-e["rows"], e["families"]))
    every = sum(e["rows"] for e in exact)
    out.append(_entry("S3", "Which combinations of list families hold the rows?", "rows",
                      "the single-token rows that all 5 families can hold",
                      {"families": [f[0] for f in FAMILIES], "rows": every, "combinations": exact}))
    # S4 and S13: what each list and family holds alone; leave-one-out
    alone = {LIST_NAMES[LISTS[j]]: 0 for j in range(width)}
    for key, n in hist.items():
        d = decode(key[0], width)
        listed = [j for j, x in enumerate(d) if x == 1]
        if len(listed) == 1:
            alone[LIST_NAMES[LISTS[listed[0]]]] += n
    fam_alone = {f[0]: 0 for f in FAMILIES}
    for key, n in fh.items():
        d = decode(key[0], fw)
        listed = [j for j, x in enumerate(d) if x == 1]
        if len(listed) == 1:
            fam_alone[FAMILIES[listed[0]][0]] += n
    out.append(_entry("S4", "What does each list hold that no other does?", "rows",
                      "the single-token rows listed by exactly 1 list, or by exactly 1 family",
                      {"by_list": alone, "by_family": fam_alone}))
    union = unions(hist, width)
    out.append(_entry("S13", "What would be lost without each list, and how fast does the union grow?", "rows",
                      "the single-token rows listed by at least 1 of the lists",
                      {"lost_without": alone, "union_of_all": union[(1 << width) - 1],
                       "accumulation": accumulation(union, width)},
                      note="a row is lost without a list when no other list lists it, so the counts are S4's by list"))
    # S5: k of m, overall, by class, and by frequency band
    band = r.zipf_band()
    plain = np.ones(int(r.single.sum()), dtype=bool)
    flag_index = np.zeros(int(r.single.sum()), dtype=np.int8)
    for i, f in enumerate(FLAGS[:-1], start=1):
        fl = r.flag[f][r.single]
        flag_index = np.where((flag_index == 0) & fl, i, flag_index)
        plain &= ~fl
    class_names = ("plain",) + FLAGS[:-1]
    km = k_of_m(combos(r.families), fw)
    kmc = k_of_m(combos(r.families, flag_index), fw, 1)
    kmb = k_of_m(combos(r.families, band), fw, 1)
    def table(d, n_keys, key_names=None):
        rows_ = []
        for kk, n in sorted(d.items()):
            row = {"m": kk[0], "k": kk[1], "rows": n}
            if n_keys:
                row["key"] = key_names[kk[2]]
            rows_.append(row)
        return rows_
    out.append(_entry("S5", "How far do the list families agree?", "rows",
                      "the single-token rows; m is the families that can hold a row, k those that list it",
                      {"overall": table(km, 0), "by_class": table(kmc, 1, class_names),
                       "by_frequency_band": table(kmb, 1, ZIPF_BANDS)},
                      note="a row's class here is its first flag in the order plain, then the flags of F4; most rows are plain"))
    # S6: coverage by frequency band, by strings and weighted by tokens
    weight = np.where(np.isnan(r.zipf), 0.0, np.power(10.0, np.nan_to_num(r.zipf)))
    cov = []
    for j, name in enumerate(LISTS):
        col = r.lists[:, j]
        bands = []
        for b, bname in enumerate(ZIPF_BANDS):
            sel = band == b
            can = sel & (col != -1)
            hit = can & (col == 1)
            n_can, n_hit = int(can.sum()), int(hit.sum())
            entry = {"band": bname, "can_hold": n_can, "listed": n_hit, "share": share(n_hit, n_can),
                     "interval": wilson(n_hit, n_can)}
            if b > 0:
                w_can = float(weight[can].sum())
                entry["token_weighted_share"] = None if not w_can else round(float(weight[hit].sum()) / w_can, 6)
            bands.append(entry)
        cov.append({"list": LIST_NAMES[name], "bands": bands})
    band_rows = [int((band == b).sum()) for b in range(len(ZIPF_BANDS))]
    out.append(_entry("S6", "How does listing depend on frequency?", "rows",
                      "the single-token rows, in bands of wordfreq's Zipf value; a row wordfreq does not score is the band 'no value'",
                      {"bands": list(ZIPF_BANDS), "rows_per_band": band_rows, "lists": cov},
                      note="the token-weighted share weights each row by 10 to the power of its Zipf value, its frequency up to a constant; the interval is Wilson's at 95%"))
    # S8: the American and British dictionaries
    us, gb = r.lists[:, 2], r.lists[:, 3]
    by_class = {}
    for i, cname in enumerate(class_names):
        sel = flag_index == i
        by_class[cname] = {"us_not_gb": int((sel & (us == 1) & (gb == 0)).sum()),
                           "gb_not_us": int((sel & (gb == 1) & (us == 0)).sum()),
                           "both": int((sel & (us == 1) & (gb == 1)).sum())}
    vu = r.universe["variety_us_not_gb"].fill_null(False).to_numpy(zero_copy_only=False)
    vg = r.universe["variety_gb_not_us"].fill_null(False).to_numpy(zero_copy_only=False)
    out.append(_entry("S8", "How do the American and British dictionaries differ?", "rows",
                      "the single-token rows that both dictionaries can hold",
                      {"us_not_gb": int(((us == 1) & (gb == 0)).sum()), "gb_not_us": int(((gb == 1) & (us == 0)).sum()),
                       "both": int(((us == 1) & (gb == 1)).sum()), "by_class": by_class,
                       "variety_proxies": {"variety_us_not_gb": int(vu.sum()), "variety_gb_not_us": int(vg.sum())}}))
    # S9: the blind cells
    blind = {LIST_NAMES[name]: {f: int(((r.lists[:, j] == -1) & r.flag[f][r.single]).sum()) for f in FLAGS[:-1]}
             for j, name in enumerate(LISTS)}
    out.append(_entry("S9", "What can each list not hold?", "rows",
                      "the single-token rows a list cannot hold, by the class flag that blinds it",
                      {"by_list": blind}, note="the reason each list is blind to a class is the evidence matrix's account (pipeline/research/evidence/evidence.json)"))
    # S10: the consensus core
    core = r.tier == 0
    import pyarrow as pa
    import pyarrow.compute as pc
    single_layer = r.universe["intake_layer"].filter(pa.array(r.single))
    vc = pc.value_counts(single_layer.filter(pa.array(core))).to_pylist()
    u = [d["values"] for d in vc]
    cnt = [d["counts"] for d in vc]
    out.append(_entry("S10", "What is the consensus core?", "rows",
                      "the single-token rows listed by 2 or more of the 5 families",
                      {"rows": int(core.sum()), "by_class": {class_names[i]: int((core & (flag_index == i)).sum()) for i in range(len(class_names))},
                       "by_intake_layer": dict(sorted(zip(u, [int(x) for x in cnt])))}))
    # S14: the tails
    unlisted = (r.families == 1).sum(axis=1) == 0
    freq = {}
    for t in FREQUENT:
        sel = unlisted & (np.nan_to_num(r.zipf, nan=-1.0) >= t)
        freq[f"zipf {t:g} and over"] = {"rows": int(sel.sum()),
                                        "by_class": {class_names[i]: int((sel & (flag_index == i)).sum()) for i in range(len(class_names))}}
    absent = (~r.corpus)
    listed_absent = {LIST_NAMES[name]: int(((r.lists[:, j] == 1) & absent).sum()) for j, name in enumerate(LISTS)}
    out.append(_entry("S14", "Which rows are frequent but unlisted, or listed but absent from the corpora?", "rows",
                      "the single-token rows",
                      {"frequent_unlisted": freq,
                       "listed_absent_from_corpora": {"any_list": int((~unlisted & absent).sum()), "by_list": listed_absent}}))
    # S15: the hunspell family's internal agreement
    h = r.lists[:, 2:6]
    holdable = (h != -1).all(axis=1)
    k = (h == 1).sum(axis=1)
    pat = {}
    sub = h[holdable & (k > 0) & (k < 4)]
    for row, n in zip(*np.unique(sub, axis=0, return_counts=True)):
        pat[",".join(n_ for n_, v in zip(("en_US", "en_GB", "en_CA", "en_AU"), row) if v == 1)] = int(n)
    out.append(_entry("S15", "Do the 4 hunspell dictionaries agree?", "rows",
                      "the single-token rows all 4 dictionaries can hold",
                      {"rows": int(holdable.sum()), "all_4": int((holdable & (k == 4)).sum()),
                       "none": int((holdable & (k == 0)).sum()), "some": int((holdable & (k > 0) & (k < 4)).sum()),
                       "patterns": dict(sorted(pat.items(), key=lambda kv: -kv[1]))},
                      note="the dictionaries differ by design in spelling variety; the patterns show which of them list a row"))
    return out


def level_4(r: Release) -> list[dict]:
    out = []
    zedges = [x / 2 for x in range(0, 17)]
    gedges = [x / 2 for x in range(0, 25)]
    def per_tier(values, edges):
        return tier_histograms(values, r.tier, edges)
    out.append(_entry("U1", "How frequent are the candidates?", "rows",
                      "the single-token rows, by evidence tier",
                      {"wordfreq_zipf": {"edges": zedges, "by_tier": per_tier(r.zipf, zedges)},
                       "gb_log10_match": {"edges": gedges, "by_tier": per_tier(r.gb_match, gedges)}}))
    span = r.gb_span.astype(np.float64)
    span[span < 0] = np.nan
    sedges = list(range(0, 575, 25))
    fedges = [x / 10 for x in range(0, 11)]
    out.append(_entry("U3", "Over what span of years does each string occur in Google Books?", "rows",
                      "the single-token rows that are Google Books types, by evidence tier",
                      {"year_span": {"edges": sedges, "by_tier": per_tier(np.where(r.gb, span, np.nan), sedges)},
                       "span_fill": {"edges": fedges, "by_tier": per_tier(np.where(r.gb, r.gb_fill, np.nan), fedges)}},
                      note="a span in a corpus of scanned books, not a date of first use"))
    redges = [x / 2 for x in range(-12, 13)]
    out.append(_entry("U4", "How far does each string sit from the corpus's frequency law?", "rows",
                      "the single-token rows that are Google Books types, by evidence tier",
                      {"zipf_resid": {"edges": redges, "by_tier": per_tier(r.zipf_resid, redges)}}))
    k = (r.families == 1).sum(axis=1)
    by_k = {}
    for kk in range(len(FAMILIES) + 1):
        sel = k == kk
        z = r.zipf[sel]
        g = r.gb_match[sel]
        by_k[str(kk)] = {"rows": int(sel.sum()), "wordfreq_zipf": quantiles(z[~np.isnan(z)]),
                         "gb_log10_match": quantiles(g[~np.isnan(g)])}
    out.append(_entry("U5", "How do frequency and agreement relate?", "rows",
                      "the single-token rows, by the number of families that list them",
                      {"by_families_listing": by_k}))
    return out


def level_5(r: Release, eol_subset: dict) -> list[dict]:
    import pyarrow as pa
    import pyarrow.compute as pc
    out = []
    u = r.universe
    kind = u["intake_kind"].to_numpy(zero_copy_only=False)
    t = pa.table({"layer": u["intake_layer"], "kind": u["intake_kind"], "group": pa.array(r.group)})
    g = t.group_by(["layer", "kind", "group"]).aggregate([("group", "count")])
    flows = {}
    for lv, kv, gr, n in sorted(zip(g["layer"].to_pylist(), g["kind"].to_pylist(),
                                    g["group"].to_pylist(), g["group_count"].to_pylist())):
        flows.setdefault(lv, {}).setdefault(kv, {})[GROUPS[gr]] = int(n)
    out.append(_entry("P1", "How was the universe assembled?", "rows",
                      "every row, by intake layer, intake kind, and evidence tier",
                      {"flows": flows}))
    eng = u["eol_synthetic_engine_inferred"].to_numpy(zero_copy_only=False)
    gen = kind == "generated"
    res = {}
    for e in sorted({x for x in eng[gen].tolist() if x is not None}):
        sel = gen & (eng == e)
        res[e] = {GROUPS[g]: int((sel & (r.group == g)).sum()) for g in range(len(GROUPS))}
    out.append(_entry("P2", "What did the lost generator make?", "rows",
                      "the rows the English OpenList's synthetic engine made, by the engine inferred from each row's form and by evidence tier",
                      {"rows": int(gen.sum()), "by_engine": res},
                      note="the engine is inferred from the row's form and named as inferred"))
    vc = sorted((d["values"], int(d["counts"])) for d in pc.value_counts(u["provenance_class"]).to_pylist())
    vals = [v for v, _ in vc]
    cnts = [n for _, n in vc]
    out.append(_entry("P3", "How many rows have no evidence at all?", "rows", "every row, by provenance class",
                      {"by_provenance_class": dict(zip(vals, cnts))},
                      note="the private universe's count is not part of the public analysis"))
    # P4: each intake channel's rows, and how many a family lists or a corpus holds
    listed = np.zeros(r.n, dtype=bool)
    listed[r.single] = (r.families == 1).any(axis=1)
    listed[r.spaced] = r.spaced_wordnet | r.spaced_wiktionary
    corpus = np.zeros(r.n, dtype=bool)
    corpus[r.single] = r.corpus
    labels = pc.split_pattern(u["intake_channels"], ";")
    lengths = pc.list_value_length(labels).to_numpy()
    flat = pc.list_flatten(labels)
    rep = np.repeat(np.arange(r.n), lengths)
    t = pa.table({"label": flat, "listed": pa.array(listed[rep]), "corpus": pa.array(corpus[rep])})
    t = t.filter(pc.not_equal(t["label"], ""))
    g = t.group_by("label").aggregate([("label", "count"), ("listed", "sum"), ("corpus", "sum")])
    rows_ = sorted(({"channel": lab, "rows": int(n), "listed": int(l), "in_a_corpus": int(cp)}
                    for lab, n, l, cp in zip(g["label"].to_pylist(), g["label_count"].to_pylist(),
                                             g["listed_sum"].to_pylist(), g["corpus_sum"].to_pylist())),
                   key=lambda d: (-d["rows"], d["channel"]))
    shown, rest = rows_[:CHANNELS_SHOWN], rows_[CHANNELS_SHOWN:]
    data = {"channels": len(rows_), "shown": shown}
    if rest:
        data["other"] = {"channel": f"the other {len(rest)} channels", "rows": sum(d["rows"] for d in rest),
                         "listed": sum(d["listed"] for d in rest), "in_a_corpus": sum(d["in_a_corpus"] for d in rest)}
    out.append(_entry("P4", "Does a first-seen channel agree with containment?", "row-channel pairs",
                      "every row, once per intake channel label it carries", data,
                      note="a channel records where a string was first seen and is never an attestation"))
    # T3: the English OpenList since the pin
    out.append(_entry("T3", "How far has the English OpenList moved since its pin?", "entries",
                      "the English OpenList's last published list against its list at the pinned revision",
                      {"revision_pinned": eol_subset["pin_revision"],
                       "last_list_revision": eol_subset["last_list"]["revision"], **eol_subset["counts"]},
                      note="from pipeline/research/release/eol_subset.py"))
    return out


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

def build(version: str) -> tuple[Path, str]:
    spec = B.resolve(version)
    if not spec.public:
        raise AnalysisError(f"{version} is not a public version")
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    universe = _read(spec, record, "universe", UNIVERSE_COLUMNS)
    features = _read(spec, record, "features", FEATURE_COLUMNS)
    r = Release(universe, features)
    eol_subset = json.loads((REPO / "research" / "release" / f"eol_subset_{version}.json").read_text(encoding="utf-8"))
    files = {f["config"]: f for f in record["files"]}
    entries = level_1(r) + level_3(r) + level_4(r) + level_5(r, eol_subset)
    ids = [e["id"] for e in entries]
    if len(set(ids)) != len(ids):
        raise AnalysisError("an analysis id repeats")
    # the tiers under a stricter count of independence: SCOWL and the 4
    # hunspell dictionaries, which SCOWL's own data seeds, as 1 family
    strict = np.stack([r.families[:, 0], r.families[:, 1],
                       np.where((r.families[:, 2] == 1) | (r.families[:, 4] == 1), 1,
                                np.where((r.families[:, 2] == -1) & (r.families[:, 4] == -1), -1, 0)),
                       r.families[:, 3]], axis=1).astype(np.int8)
    strict_tier = tiers(strict, r.corpus)
    doc = {
        "version": version, "dataset": record["dataset"], "built_on": record["built_on"],
        "generated_by": "pipeline/research/analysis/descriptive.py",
        "plan": "docs/ANALYSIS_PLAN.md",
        "record": _rel(spec.record_out),
        "sources": {c: {"path": f"data/{files[c]['path']}", "sha256": files[c]["sha256"], "rows": files[c]["rows"]}
                    for c in ("universe", "features")},
        "list_set": {"lists": [LIST_NAMES[x] for x in LISTS], "families": {f: [LIST_NAMES[LISTS[i]] for i in idx] for f, idx in FAMILIES},
                     "note": "the 8 published lists in 5 families; the 5 withheld lists are not part of the public analysis"},
        "tiers": list(TIERS),
        "rows": {"all": r.n, "single_token": int(r.single.sum()), "multiword": int(r.spaced.sum()),
                 "by_tier": {TIERS[t]: int((r.tier == t).sum()) for t in range(len(TIERS))},
                 "by_tier_scowl_and_hunspell_as_1_family": {TIERS[t]: int((strict_tier == t).sum()) for t in range(len(TIERS))}},
        "what": "the descriptive analysis of the analysis plan, counts only; each entry under the plan's id",
        "analyses": entries,
    }
    return out_path(version), json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with the file")
    args = ap.parse_args(argv)
    start = time.perf_counter()
    try:
        path, text = build(args.version)
    except (AnalysisError, B.ReleaseError, FileNotFoundError) as exc:
        print(f"[analysis] refused: {exc}", file=sys.stderr)
        return 1
    took = time.perf_counter() - start
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            print(f"[analysis] {_rel(path)} differs from what the code prints", file=sys.stderr)
            return 1
        print(f"[analysis] {_rel(path)} re-derives ({took:.1f} s)")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[analysis] {len(text.encode('utf-8')):,} bytes  {_rel(path)} ({took:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
