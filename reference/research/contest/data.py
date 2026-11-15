"""
Load the CEOL evidence matrix into the shapes the contest eats — the EOL
model/data.py extended to three-valued evidence (C-010).

Patterns are (values over K=13 detectors) with values in {1, 0, NA(-1)},
encoded base-3 for uniquing. The applicability MASK is part of the
pattern: two words with the same fires but different visibility are
different rows of the likelihood. The 10,001,741 rows collapse to a few
hundred mask-pattern rows; per-word ids map posteriors back.

Features: standardized continuous channels with missingness indicators,
NaN imputed to the mean AFTER standardization; scaler recorded. Only the
channels the C-011 gate ADMITTED enter (features_gate.json is read here,
so an inadmissible family cannot leak into a fit by accident).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FITS = REPO / "research" / "contest" / "fits"

DETECTORS = ["wordnet", "wiktionary_english", "web2", "web2a",
             "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
             "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
             "csw21"]          # + scowl_present appended -> K = 13

#: Declared dependence edges: the EOL's nine (§2.3) plus web2a<->web2 —
#: both derive from Webster's Second (web2a is its addenda list).
EDGE_NAMES = [("hunspell_en_US", "scowl"), ("hunspell_en_GB", "scowl"),
              ("hunspell_en_CA", "scowl"), ("hunspell_en_AU", "scowl"),
              ("hunspell_en_GB", "hunspell_en_US"),
              ("hunspell_en_CA", "hunspell_en_US"),
              ("hunspell_en_AU", "hunspell_en_US"),
              ("enable1", "nwl2023"), ("sowpods_legacy", "csw21"),
              ("web2a", "web2")]

#: Base feature channels (EOL Phase-3 list plus the C4 additions that are
#: not admission-gated). Family ratio columns join only via the gate.
BASE_FEATURES = ["orthotactic_logp_per_char", "ocr_neighbor_freq_ratio",
                 "gb_log10_volume", "gb_span_fill", "gb_tokens_per_volume",
                 "zipf_resid", "morph_productivity_vn",
                 "segment_attested_fraction", "wordfreq_zipf"]


def detector_names() -> list[str]:
    return DETECTORS + ["scowl"]


def edge_indices() -> list[tuple[int, int]]:
    names = detector_names()
    return [(names.index(a), names.index(b)) for a, b in EDGE_NAMES]


def load_patterns():
    """(pattern_ids [n] int32, pats [P,13] int8 in {1,0,-1}, counts [P],
    words). Base-3 packing: cell -> {0: silent, 1: fire, 2: NA}."""
    import pyarrow.parquet as pq
    ev = pq.read_table(DATA / "evidence.parquet")
    n = ev.num_rows
    K = len(DETECTORS) + 1
    Y = np.zeros((n, K), dtype=np.int8)
    for j, c in enumerate(DETECTORS):
        Y[:, j] = ev.column(c).to_numpy(zero_copy_only=False)
    tier = ev.column("scowl_tier").to_numpy(zero_copy_only=False)
    Y[:, K - 1] = np.where(tier == -1, -1, (tier > 0).astype(np.int8))

    trits = np.where(Y == -1, 2, Y).astype(np.int64)
    weights = (3 ** np.arange(K)).astype(np.int64)
    ids = trits @ weights
    uniq, inverse, counts = np.unique(ids, return_inverse=True,
                                      return_counts=True)
    P = len(uniq)
    pats = np.zeros((P, K), dtype=np.int8)
    rem = uniq.copy()
    for j in range(K):
        d = rem % 3
        pats[:, j] = np.where(d == 2, -1, d)
        rem //= 3
    words = ev.column("word").to_pylist()
    return inverse.astype(np.int32), pats, counts.astype(np.int64), words


STRATIFIED = ("wiktionary_english", "hunspell_en_GB", "scowl")


def load_patterns_stratified():
    """The class-stratified S1 variant (C-012): each detector in
    STRATIFIED splits into a plain-only and an exception-only virtual
    detector (complementary NA masks), K 13 -> 16. The battery's profile
    likelihoods rule whether the split rates are identified."""
    import pyarrow.parquet as pq
    ev = pq.read_table(DATA / "evidence.parquet")
    uni = pq.read_table(DATA / "universe.parquet", columns=["classes"])
    plain = np.array([c == "" for c in
                      uni.column("classes").to_pylist()], dtype=bool)
    n = ev.num_rows
    base = detector_names()
    cols: list[np.ndarray] = []
    names: list[str] = []
    for j, c in enumerate(DETECTORS):
        v = ev.column(c).to_numpy(zero_copy_only=False).astype(np.int8)
        if c in STRATIFIED:
            vp = np.where(plain, v, -1).astype(np.int8)
            ve = np.where(~plain, v, -1).astype(np.int8)
            cols += [vp, ve]
            names += [f"{c}::plain", f"{c}::exc"]
        else:
            cols.append(v)
            names.append(c)
    tier = ev.column("scowl_tier").to_numpy(zero_copy_only=False)
    sc = np.where(tier == -1, -1, (tier > 0).astype(np.int8)).astype(np.int8)
    scp = np.where(plain, sc, -1).astype(np.int8)
    sce = np.where(~plain, sc, -1).astype(np.int8)
    cols += [scp, sce]
    names += ["scowl::plain", "scowl::exc"]
    Y = np.column_stack(cols)
    K = Y.shape[1]
    trits = np.where(Y == -1, 2, Y).astype(np.int64)
    weights = (3 ** np.arange(K)).astype(np.int64)
    uniq, inverse, counts = np.unique(trits @ weights, return_inverse=True,
                                      return_counts=True)
    pats = np.zeros((len(uniq), K), dtype=np.int8)
    rem = uniq.copy()
    for j in range(K):
        d = rem % 3
        pats[:, j] = np.where(d == 2, -1, d)
        rem //= 3
    return inverse.astype(np.int32), pats, counts.astype(np.int64), names


def admitted_features() -> list[str]:
    gate = json.loads(
        (REPO / "research" / "features" / "features_gate.json").read_text())
    return BASE_FEATURES + sorted(gate.get("admitted_families", []))


def load_features():
    """(X [n,d] float32, names, scaler) — admitted channels only."""
    import pyarrow.parquet as pq
    ft = pq.read_table(DATA / "features.parquet")
    cols, names = [], []
    scaler = {}
    for c in admitted_features():
        v = ft.column(c).to_numpy(zero_copy_only=False).astype(np.float64)
        miss = ~np.isfinite(v)
        mu = float(np.nanmean(np.where(miss, np.nan, v)))
        sd = float(np.nanstd(np.where(miss, np.nan, v)))
        sd = sd if sd > 0 else 1.0
        z = (v - mu) / sd
        z[miss] = 0.0
        cols.append(z.astype(np.float32))
        names.append(c)
        scaler[c] = {"mean": mu, "sd": sd,
                     "missing_rate": float(miss.mean())}
        if miss.any():
            cols.append(miss.astype(np.float32))
            names.append(c + "__missing")
    X = np.column_stack(cols)
    return X, names, scaler


def enumerate_cells(K: int = 13) -> np.ndarray:
    ids = np.arange(1 << K, dtype=np.int64)
    out = np.zeros((1 << K, K), dtype=np.uint8)
    for j in range(K):
        out[:, j] = (ids >> j) & 1
    return out


def consistency(pats: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """CONS [P, 2^K] float32: cell consistent with the observed cells of
    each mask-pattern (NA cells impose nothing)."""
    P, K = pats.shape
    cons = np.ones((P, len(cells)), dtype=bool)
    for j in range(K):
        obs = pats[:, j] != -1
        eq = cells[None, :, j] == np.clip(pats[:, j], 0, 1)[:, None]
        cons &= np.where(obs[:, None], eq, True)
    return cons.astype(np.float32)


def save_fit(name: str, obj: dict) -> None:
    FITS.mkdir(exist_ok=True)
    with open(FITS / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def load_fit(name: str) -> dict:
    with open(FITS / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)
