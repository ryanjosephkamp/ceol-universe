"""
Drive the C4 step-2 feature build — C-011 over the pinned universe.

Reads data/universe.parquet + data/evidence.parquet + the CEOL Google
Books aggregate, computes every channel over 10,001,741 words, writes
data/features.parquet keyed to the same word order, and records every
hyperparameter, seed, count and deviation in
research/features/features_manifest.json.

Channel inventory (C-011): orthotactics over the 50-symbol alphabet
(per-class gated); the six typed OCR pairs plus five PROPOSED
wider-alphabet family columns (admission decided by the gate report,
never here); realized productivity V/N plus segment attestation for
hyphenated words; the six year-level dispersion proxies; Zipf-Mandelbrot
conformity over the CEOL aggregate; wordfreq Zipf for words wordfreq
lists. SR2 reading B is finalized here (all-zero AND no wordfreq AND no
Google Books), bar <= 50%.

Run:  python -m research.features.build_features
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

from ceol.grammar import classes as class_flags
from ceol.ingest.common import DERIVED_DIR, read_derived, sha256_file

from . import charmodel, ocr, productivity
from .partitions import (DEV_END, POOL_RATIO, SEED, SENSITIVITY_RATIO,
                         TRAIN_END, assign, threshold)

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FEATURES_DIR = REPO / "research" / "features"
GB_AGGREGATE = DERIVED_DIR / "google_books_1grams_ceol.parquet"

#: C-011 pre-declared per-class held-out perplexity bounds.
PPL_BOUNDS = {"plain": 9.0, "hyphenated": 25.0, "accented": 25.0,
              "contraction": 25.0, "apostrophe-form": 25.0,
              "ligature": 25.0, "diaeresis": 25.0}

DETECTORS = ("wordnet", "wiktionary_english", "web2", "web2a",
             "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
             "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
             "csw21")


def log(msg):
    print(f"[features] {msg}", flush=True)


def primary_class(cls_string: str) -> str:
    """One reporting class per word, majority-of-report-order: the first
    census class the word carries, else plain."""
    if not cls_string:
        return "plain"
    flags = set(cls_string.split(";"))
    for c in ("ligature", "diaeresis", "accented", "contraction",
              "apostrophe-form", "hyphenated"):
        if c in flags:
            return c
    return "plain"


def main() -> int:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    t0 = time.time()
    uni = pq.read_table(DATA / "universe.parquet",
                        columns=["word", "classes"])
    ev = pq.read_table(DATA / "evidence.parquet")
    words = uni.column("word").to_pylist()
    classes_col = uni.column("classes").to_pylist()
    n = len(words)
    if ev.column("word").to_pylist()[:1000] != words[:1000]:
        raise RuntimeError("universe and evidence word order diverged")
    log(f"universe: {n:,} words")

    # -- applicable-aware strong positives (C-011) --------------------------
    fires = np.zeros(n, dtype=np.int8)
    applicable = np.zeros(n, dtype=np.int8)
    for c in DETECTORS:
        col = ev.column(c).to_numpy(zero_copy_only=False)
        fires += (col == 1).astype(np.int8)
        applicable += (col != -1).astype(np.int8)
    tier = ev.column("scowl_tier").to_numpy(zero_copy_only=False)
    fires += (tier > 0).astype(np.int8)
    applicable += (tier != -1).astype(np.int8)

    thresh = np.array([threshold(int(a)) for a in range(0, 14)],
                      dtype=np.int8)
    pool_mask = fires >= thresh[applicable]
    strict = np.array([threshold(int(a), SENSITIVITY_RATIO)
                       for a in range(0, 14)], dtype=np.int8)
    pool_strict_mask = fires >= strict[applicable]

    pclass = [primary_class(c) for c in classes_col]
    parts: dict[str, list[str]] = {"train": [], "dev": [], "test": []}
    test_by_class: dict[str, list[str]] = {}
    pool_by_class: dict[str, int] = {}
    for i in np.flatnonzero(pool_mask):
        w = words[i]
        part = assign(w)
        parts[part].append(w)
        pool_by_class[pclass[i]] = pool_by_class.get(pclass[i], 0) + 1
        if part == "test":
            test_by_class.setdefault(pclass[i], []).append(w)
    log(f"pool {int(pool_mask.sum()):,} (strict variant "
        f"{int(pool_strict_mask.sum()):,}) -> train {len(parts['train']):,} "
        f"/ dev {len(parts['dev']):,} / test {len(parts['test']):,}")
    log(f"pool by class: { {k: v for k, v in sorted(pool_by_class.items())} }")

    # -- orthotactics -------------------------------------------------------
    model = charmodel.CharModel()
    model.fit(parts["train"])
    model.finalize()
    lambdas = model.tune(parts["dev"])
    log(f"lambdas: {[round(x, 4) for x in lambdas]}")
    ppl_class = {}
    for cls, ws in sorted(test_by_class.items()):
        if len(ws) >= 25:
            ppl_class[cls] = round(model.perplexity(ws), 3)
    ppl_class["__train_slice__"] = round(
        model.perplexity(parts["train"][: len(parts["test"])]), 3)
    class_na = {c for c, p in ppl_class.items()
                if c in PPL_BOUNDS and p > PPL_BOUNDS[c]}
    log(f"held-out perplexity by class: {ppl_class}; NA fallback: "
        f"{sorted(class_na) or 'none'}")

    logp_total = np.full(n, np.nan, dtype=np.float32)
    logp_char = np.full(n, np.nan, dtype=np.float32)
    t1 = time.time()
    for i, w in enumerate(words):
        if pclass[i] in class_na:
            continue
        lt, lc = model.logp_word(w)
        logp_total[i] = lt
        logp_char[i] = lc
        if i and i % 2_000_000 == 0:
            log(f"  orthotactics {i:,}/{n:,} ({time.time()-t1:.0f}s)")
    log(f"orthotactics in {time.time()-t1:.0f}s")

    # -- references (C-011, dependence declared) ----------------------------
    reference = ((read_derived("wordnet") | read_derived("wordnet_plain"))
                 | (read_derived("web2") | read_derived("web2_plain")))
    wikt_all = read_derived("wiktionary_english_all")
    hs_gb = read_derived("hunspell_en_GB") \
        | read_derived("hunspell_en_GB_plain")
    scowl_full = read_derived("scowl") | read_derived("scowl_plain")
    capable = wikt_all | hs_gb | scowl_full \
        | read_derived("wordnet") | read_derived("web2a")

    def class_ref(*flags):
        want = set(flags)
        return {w for w in capable if class_flags(w) & want}

    accent_ref = class_ref("accented", "diaeresis")
    hyphen_ref = class_ref("hyphenated")
    apos_ref = class_ref("apostrophe-form")
    lig_ref = class_ref("ligature")
    log(f"references: base {len(reference):,} | accent {len(accent_ref):,} "
        f"| hyphen {len(hyphen_ref):,} | apos {len(apos_ref):,} "
        f"| lig {len(lig_ref):,}")

    # -- Google Books columns (CEOL aggregate) ------------------------------
    gb = pq.read_table(GB_AGGREGATE)
    gb_index = {w: i for i, w in enumerate(gb.column("word").to_pylist())}
    gb_match_a = gb.column("total_match").to_numpy()
    gb_volume_a = gb.column("total_volume").to_numpy()
    gb_first_a = gb.column("first_year").to_numpy()
    gb_last_a = gb.column("last_year").to_numpy()
    gb_years_a = gb.column("year_count").to_numpy()
    log(f"GB aggregate: {len(gb_index):,} types")

    gb_match = np.zeros(n, dtype=np.int64)
    gb_volume = np.zeros(n, dtype=np.int64)
    gb_first = np.zeros(n, dtype=np.int16)
    gb_last = np.zeros(n, dtype=np.int16)
    gb_years = np.zeros(n, dtype=np.int16)
    for i, w in enumerate(words):
        j = gb_index.get(w)
        if j is not None:
            gb_match[i] = gb_match_a[j]
            gb_volume[i] = gb_volume_a[j]
            gb_first[i] = gb_first_a[j]
            gb_last[i] = gb_last_a[j]
            gb_years[i] = gb_years_a[j]

    def agg_match(w) -> int:
        j = gb_index.get(w)
        return int(gb_match_a[j]) if j is not None else 0

    # -- typed OCR neighbourhood (six pairs) --------------------------------
    hits = np.zeros(n, dtype=np.int8)
    ratio = np.full(n, np.nan, dtype=np.float32)
    t1 = time.time()
    for i, w in enumerate(words):
        best = None
        k = 0
        for neighbor, _pair in ocr.detect_neighbors(w, reference):
            k += 1
            r = np.log10((agg_match(neighbor) + 1) / (int(gb_match[i]) + 1))
            if best is None or r > best:
                best = r
        hits[i] = min(k, 127)
        if best is not None:
            ratio[i] = best
        if i and i % 2_000_000 == 0:
            log(f"  ocr {i:,}/{n:,} ({time.time()-t1:.0f}s)")
    log(f"ocr six-pair in {time.time()-t1:.0f}s")

    # -- proposed family columns (admission decided by the gate) ------------
    fam_cols = {name: np.full(n, np.nan, dtype=np.float32) for name in
                ("ocr_strip_ratio", "ocr_hyphen_junction_ratio",
                 "ocr_hyphen_drop_ratio", "ocr_apostrophe_ratio",
                 "ocr_ligature_ratio")}
    t1 = time.time()
    for i, w in enumerate(words):
        cm = int(gb_match[i]) + 1
        cls = pclass[i]
        if cls == "plain":
            pairs = (("ocr_strip_ratio",
                      ocr.detect_diacritic_source(w, accent_ref)),
                     ("ocr_hyphen_drop_ratio",
                      ocr.detect_hyphen_drop_source(w, hyphen_ref)),
                     ("ocr_apostrophe_ratio",
                      ocr.detect_apostrophe_source(w, apos_ref)),
                     ("ocr_ligature_ratio",
                      ocr.detect_ligature_source(w, lig_ref)))
        elif cls == "hyphenated":
            pairs = (("ocr_hyphen_junction_ratio",
                      ocr.detect_hyphen_junction_source(w, reference)),)
        else:
            continue
        for col, sources in pairs:
            if sources:
                best = max(np.log10((agg_match(s) + 1) / cm)
                           for s in sources)
                fam_cols[col][i] = best
        if i and i % 2_000_000 == 0:
            log(f"  families {i:,}/{n:,} ({time.time()-t1:.0f}s)")
    log(f"proposed families in {time.time()-t1:.0f}s")

    # -- productivity -------------------------------------------------------
    t1 = time.time()
    table = productivity.affix_table(
        gb.column("word").to_pylist(), gb_match_a, gb_volume_a, reference)
    with open(FEATURES_DIR / "productivity_table.json", "w") as f:
        json.dump({f"{k[0]}:{k[1]}": v for k, v in table.items()}, f,
                  indent=2)
    suffix_p = {s: table[("suffix", s)]["P_vn"]
                for s in productivity.SUFFIXES}
    morph_p = np.full(n, np.nan, dtype=np.float32)
    has_parse = np.zeros(n, dtype=bool)
    seg_att = np.full(n, np.nan, dtype=np.float32)
    for i, w in enumerate(words):
        ps = productivity.parse_suffix(w, reference)
        if ps and suffix_p.get(ps[0]) is not None:
            morph_p[i] = suffix_p[ps[0]]
            has_parse[i] = True
        if pclass[i] == "hyphenated":
            sa = productivity.segment_attestation(w, reference)
            if sa is not None:
                seg_att[i] = sa
    log(f"productivity in {time.time()-t1:.0f}s "
        f"({int(has_parse.sum()):,} parsed)")

    # -- dispersion proxies -------------------------------------------------
    has_gb = gb_match > 0
    span = np.where(has_gb, gb_last - gb_first + 1, 0).astype(np.int16)
    span_fill = np.where(span > 0, gb_years / np.maximum(span, 1), np.nan)
    tokens_per_volume = np.where(
        gb_volume > 0, gb_match / np.maximum(gb_volume, 1), np.nan)
    volumes_per_year = np.where(
        gb_years > 0, gb_volume / np.maximum(gb_years, 1), np.nan)
    log10_match = np.where(has_gb, np.log10(np.maximum(gb_match, 1)), np.nan)
    log10_volume = np.where(gb_volume > 0,
                            np.log10(np.maximum(gb_volume, 1)), np.nan)

    # -- Zipf-Mandelbrot over the CEOL aggregate ----------------------------
    order = np.sort(gb_match_a)[::-1].astype(np.float64)
    R = len(order)
    probe_ranks = np.unique(np.geomspace(1, R, 400).astype(np.int64))
    probe_f = order[probe_ranks - 1]
    keep = probe_f > 0
    pr, pf = probe_ranks[keep].astype(np.float64), probe_f[keep]
    best = None
    for beta in (0.0, 1.0, 2.7, 5.0, 10.0, 26.0, 100.0, 1000.0):
        X = np.vstack([np.ones_like(pr), np.log10(pr + beta)]).T
        y = np.log10(pf)
        coef, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(res[0]) if len(res) else float(
            ((X @ coef - y) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, beta, coef)
    sse, beta, (logC, neg_alpha) = best
    alpha = -neg_alpha
    log(f"Zipf-Mandelbrot: alpha={alpha:.4f} beta={beta} logC={logC:.3f} "
        f"sse={sse:.4f}")
    sorted_match = np.sort(gb_match_a)
    rank = np.zeros(n, dtype=np.int64)
    rank[has_gb] = R - np.searchsorted(sorted_match, gb_match[has_gb],
                                       side="right") + 1
    zipf_rank = np.where(has_gb, np.log10(np.maximum(rank, 1)), np.nan)
    pred = logC - alpha * np.log10(np.maximum(rank, 1) + beta)
    zipf_resid = np.where(has_gb, log10_match - pred, np.nan)

    # -- wordfreq Zipf (pinned package, its own derived set only) -----------
    from wordfreq import zipf_frequency
    wf_set = read_derived("wordfreq") | read_derived("wordfreq_plain")
    wf_zipf = np.full(n, np.nan, dtype=np.float32)
    for i, w in enumerate(words):
        if w in wf_set and "hyphenated" not in (classes_col[i] or ""):
            wf_zipf[i] = zipf_frequency(w, "en")
    log(f"wordfreq zipf for {int(np.isfinite(wf_zipf).sum()):,} words")

    # -- SR2 reading B, final (D-032 governance) ----------------------------
    binary_zero = fires == 0
    sr2_b = binary_zero & ~has_gb & np.fromiter(
        (w not in wf_set for w in words), dtype=bool, count=n)
    sr2_b_rows = int(sr2_b.sum())
    sr2_b_pct = round(100 * sr2_b_rows / n, 2)
    log(f"SR2 reading B FINAL: {sr2_b_rows:,} rows = {sr2_b_pct}% "
        f"(bar 50%) -> {'PASS' if sr2_b_pct <= 50 else 'FIRE'}")

    # -- write --------------------------------------------------------------
    import pyarrow as pa
    import pyarrow.parquet as pq2
    out = pa.table({
        "word": words,
        "orthotactic_logp_total": logp_total,
        "orthotactic_logp_per_char": logp_char,
        "ocr_neighbor_hits": hits,
        "ocr_neighbor_freq_ratio": ratio,
        **{name: col for name, col in fam_cols.items()},
        "morph_productivity_vn": morph_p,
        "morph_has_parse": has_parse,
        "segment_attested_fraction": seg_att,
        "gb_year_span": span,
        "gb_span_fill": span_fill.astype(np.float32),
        "gb_tokens_per_volume": tokens_per_volume.astype(np.float32),
        "gb_volumes_per_year": volumes_per_year.astype(np.float32),
        "gb_log10_match": log10_match.astype(np.float32),
        "gb_log10_volume": log10_volume.astype(np.float32),
        "zipf_log10_rank": zipf_rank.astype(np.float32),
        "zipf_resid": zipf_resid.astype(np.float32),
        "wordfreq_zipf": wf_zipf,
    })
    pq2.write_table(out, DATA / "features.parquet", compression="zstd")

    manifest = {
        "built": "2026-08-20",
        "universe_rows": n,
        "partitions": {
            "seed": SEED,
            "rule": f"sha256(seed:word) unit in [0,1): train<{TRAIN_END}, "
                    f"dev<{DEV_END}, else test",
            "pool_rule": f"fires >= ceil({POOL_RATIO:.4f} * applicable) "
                         "(== EOL 8-of-12 on plain words)",
            "sensitivity_rule": f"ceil({SENSITIVITY_RATIO} * applicable)",
            "pool": int(pool_mask.sum()),
            "pool_strict": int(pool_strict_mask.sum()),
            "pool_by_class": dict(sorted(pool_by_class.items())),
            "train": len(parts["train"]), "dev": len(parts["dev"]),
            "test": len(parts["test"]),
            "c5_exclusion": "calibration items must exclude train+dev; "
                            "re-derive from seed and rule",
        },
        "charmodel": {
            "order": charmodel.ORDER, "alphabet": len(charmodel.ALPHABET),
            "lambdas": lambdas,
            "perplexity_by_class": ppl_class,
            "ppl_bounds": PPL_BOUNDS,
            "class_na_fallback": sorted(class_na),
        },
        "references": {
            "base": "wordnet ∪ web2 (CEOL derivations)",
            "class_capable": "wikt_english ∪ hunspell_en_GB ∪ scowl ∪ "
                             "wordnet ∪ web2a, filtered per class",
            "sizes": {"base": len(reference), "accent": len(accent_ref),
                      "hyphen": len(hyphen_ref), "apostrophe": len(apos_ref),
                      "ligature": len(lig_ref)},
            "dependence": "references overlap detector columns "
                          "(wordnet/web2/wikt/hunspell_GB/scowl); declared "
                          "for the contest's conditioning",
        },
        "ocr_pairs": ocr.CONFUSIONS,
        "proposed_families": list(fam_cols),
        "gb": {"aggregate": str(GB_AGGREGATE.name),
               "aggregate_sha256": sha256_file(GB_AGGREGATE),
               "types": int(R)},
        "zipf": {"alpha": float(alpha), "beta": float(beta),
                 "logC": float(logC), "sse": float(sse),
                 "population": int(R)},
        "wordfreq": {"rule": "zipf for words in the wordfreq derived set, "
                             "NA elsewhere and NA on hyphenated (C-010)",
                     "scored": int(np.isfinite(wf_zipf).sum())},
        "sr2_reading_b": {"rows": sr2_b_rows, "pct": sr2_b_pct,
                          "bar_pct": 50,
                          "pass": bool(sr2_b_pct <= 50)},
    }
    with open(FEATURES_DIR / "features_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    log(f"features.parquet "
        f"({(DATA/'features.parquet').stat().st_size/1e6:.1f} MB) "
        f"+ manifest in {(time.time()-t0)/60:.1f}m total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
