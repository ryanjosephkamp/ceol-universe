"""
The C4 step-2 gate: per-class held-out perplexity, negative-control
separation, family admission, SR3 — every verdict against the C-011
pre-declarations.

AUC is Mann-Whitney with the Hanley-McNeil closed-form 95% interval —
deterministic, no bootstrap. Family admission (C-011): oriented AUC
lower-95 >= 0.60 against the matched corruption family AND corruption
fire rate >= 5x the real fire rate; failing families are reported and
ship nothing to the contest.

Writes research/features/features_gate.json.
Run:  python -m research.features.gate_report
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from ceol.grammar import classes as class_flags
from ceol.ingest.common import DERIVED_DIR, read_derived

from . import charmodel, controls, ocr
from .build_features import (DETECTORS, GB_AGGREGATE, PPL_BOUNDS,
                             primary_class)
from .partitions import assign, threshold

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FEATURES_DIR = REPO / "research" / "features"

#: Admission thresholds — C-011, quoted not chosen here.
ADMIT_AUC_LO = 0.60
ADMIT_FIRE_RATIO = 5.0

FAMILY_FEATURE = {
    "diacritic_strip": ("ocr_strip_ratio", "plain"),
    "hyphen_junction": ("ocr_hyphen_junction_ratio", "hyphenated"),
    "hyphen_drop": ("ocr_hyphen_drop_ratio", "plain"),
    "apostrophe_loss": ("ocr_apostrophe_ratio", "plain"),
    "ligature_expansion": ("ocr_ligature_ratio", "plain"),
}

CORPUS_FEATURES = ["ocr_neighbor_freq_ratio", "gb_tokens_per_volume",
                   "gb_span_fill", "gb_log10_volume", "zipf_resid"]


def auc_ci(pos: np.ndarray, neg: np.ndarray):
    pos = pos[~np.isnan(pos)]
    neg = neg[~np.isnan(neg)]
    n1, n2 = len(pos), len(neg)
    if n1 < 10 or n2 < 10:
        return None
    both = np.concatenate([pos, neg])
    order = both.argsort()
    sorted_vals = both[order]
    avg = np.empty_like(both)
    avg[order] = np.arange(1, len(both) + 1, dtype=np.float64)
    i = 0
    while i < len(sorted_vals):
        j = i
        while j + 1 < len(sorted_vals) and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        if j > i:
            avg[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    r1 = avg[:n1].sum()
    auc = (r1 - n1 * (n1 + 1) / 2) / (n1 * n2)
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = math.sqrt(max((auc * (1 - auc) + (n1 - 1) * (q1 - auc**2)
                        + (n2 - 1) * (q2 - auc**2)) / (n1 * n2), 1e-12))
    return {"auc": round(float(auc), 4), "lo": round(float(auc - 1.96 * se), 4),
            "hi": round(float(auc + 1.96 * se), 4), "n_pos": n1, "n_neg": n2}


def flip(row):
    if row is None:
        return None
    return {**row, "auc": round(1 - row["auc"], 4),
            "lo": round(1 - row["hi"], 4), "hi": round(1 - row["lo"], 4)}


def main() -> int:
    import pyarrow.parquet as pq

    feats = pq.read_table(DATA / "features.parquet")
    ev = pq.read_table(DATA / "evidence.parquet")
    uni = pq.read_table(DATA / "universe.parquet", columns=["word", "classes"])
    words = feats.column("word").to_pylist()
    n = len(words)
    ix = {w: i for i, w in enumerate(words)}
    manifest = json.loads(
        (FEATURES_DIR / "features_manifest.json").read_text())

    fires = np.zeros(n, dtype=np.int8)
    applicable = np.zeros(n, dtype=np.int8)
    for c in DETECTORS:
        col = ev.column(c).to_numpy(zero_copy_only=False)
        fires += (col == 1).astype(np.int8)
        applicable += (col != -1).astype(np.int8)
    tier = ev.column("scowl_tier").to_numpy(zero_copy_only=False)
    fires += (tier > 0).astype(np.int8)
    applicable += (tier != -1).astype(np.int8)
    thresh = np.array([threshold(int(a)) for a in range(14)], dtype=np.int8)
    pool_mask = fires >= thresh[applicable]
    detector_hit_words = {words[i] for i in np.flatnonzero(fires > 0)}

    classes_col = uni.column("classes").to_pylist()
    pclass = [primary_class(c) for c in classes_col]
    pool_idx = np.flatnonzero(pool_mask)
    train, dev = [], []
    test_by_class: dict[str, list[str]] = {}
    for i in pool_idx:
        part = assign(words[i])
        if part == "train":
            train.append(words[i])
        elif part == "dev":
            dev.append(words[i])
        else:
            test_by_class.setdefault(pclass[i], []).append(words[i])
    test_pos = [w for ws in test_by_class.values() for w in ws]

    model = charmodel.CharModel()
    model.fit(train)
    model.finalize()
    model.tune(dev)

    reference = ((read_derived("wordnet") | read_derived("wordnet_plain"))
                 | (read_derived("web2") | read_derived("web2_plain")))
    gb = pq.read_table(GB_AGGREGATE, columns=["word", "total_match"])
    gb_match_map = dict(zip(gb.column("word").to_pylist(),
                            gb.column("total_match").to_numpy()))
    del gb

    all_keys: set[str] = set()
    for sid in ("wordnet", "wordnet_plain", "wiktionary_english_all",
                "wiktionary_titles", "wiktionary_titles_plain",
                "web2", "web2_plain", "web2a", "web2a_plain",
                "hunspell_en_US", "hunspell_en_US_plain",
                "hunspell_en_GB", "hunspell_en_GB_plain",
                "hunspell_en_CA", "hunspell_en_CA_plain",
                "hunspell_en_AU", "hunspell_en_AU_plain",
                "scowl", "scowl_plain", "wordfreq", "wordfreq_plain"):
        all_keys |= read_derived(sid)
    for sid in ("enable1", "sowpods_legacy", "nwl2023", "csw21"):
        from ceol.ingest.evidence_sources import read_eol_derived
        all_keys |= read_eol_derived(sid)

    families: dict[str, list[str]] = {
        "ocr": controls.ocr_family(test_pos, reference),
        "pseudo": controls.pseudo_family(model, all_keys),
        "mw_refuted": controls.mw_family(),
        **controls.foreign_family(detector_hit_words),
    }
    strip = controls.strip_families(test_by_class, all_keys)

    col = {name: feats.column(name).to_numpy(zero_copy_only=False)
           for name in feats.schema.names if name != "word"}

    def live_ratio(artifact: str, detect_fn, ref) -> float:
        cm = gb_match_map.get(artifact, 0) + 1
        sources = detect_fn(artifact, ref)
        if not sources:
            return np.nan
        return max(math.log10((gb_match_map.get(s, 0) + 1) / cm)
                   for s in sources)

    def feature_values(ws, feature):
        vals = []
        for w in ws:
            i = ix.get(w)
            if i is not None:
                vals.append(col[feature][i])
            elif feature == "orthotactic_logp_per_char":
                vals.append(model.logp_word(w)[1])
            elif feature == "ocr_neighbor_freq_ratio":
                best = np.nan
                cm = gb_match_map.get(w, 0) + 1
                for nb, _ in ocr.detect_neighbors(w, reference):
                    r = math.log10((gb_match_map.get(nb, 0) + 1) / cm)
                    if np.isnan(best) or r > best:
                        best = r
                vals.append(best)
            else:
                vals.append(np.nan)
        return np.array(vals, dtype=np.float64)

    report: dict = {"perplexity": {
        "by_class": manifest["charmodel"]["perplexity_by_class"],
        "bounds": PPL_BOUNDS,
        "class_na_fallback": manifest["charmodel"]["class_na_fallback"],
        "pass": [c for c, p in
                 manifest["charmodel"]["perplexity_by_class"].items()
                 if c in PPL_BOUNDS and p <= PPL_BOUNDS[c]],
    }}

    # -- core separations (held-out positives vs each family) ---------------
    test_ortho = feature_values(test_pos, "orthotactic_logp_per_char")
    seps = {}
    for fam, ws in families.items():
        fam_ortho = feature_values(ws, "orthotactic_logp_per_char")
        seps[fam] = {"orthotactic_logp_per_char":
                     auc_ci(test_ortho, fam_ortho)}
    ocr_real = feature_values(test_pos, "ocr_neighbor_freq_ratio")
    ocr_fam = feature_values(families["ocr"], "ocr_neighbor_freq_ratio")
    # P(corruption ranks above real on the ratio) IS the oriented
    # artifact-detection AUC — no flip
    seps["ocr"]["ocr_neighbor_freq_ratio_oriented"] = auc_ci(
        ocr_fam, ocr_real)
    seps["ocr"]["fire_rates"] = {
        "real": round(float(np.isfinite(ocr_real).mean()), 4),
        "corruptions": round(float(np.isfinite(ocr_fam).mean()), 4)}
    report["separation"] = seps

    # -- family admission (C-011) -------------------------------------------
    detect_for = {
        "diacritic_strip": (ocr.detect_diacritic_source, "accent"),
        "hyphen_junction": (ocr.detect_hyphen_junction_source, "base"),
        "hyphen_drop": (ocr.detect_hyphen_drop_source, "hyphen"),
        "apostrophe_loss": (ocr.detect_apostrophe_source, "apos"),
        "ligature_expansion": (ocr.detect_ligature_source, "lig"),
    }
    wikt_all = read_derived("wiktionary_english_all")
    hs_gb = read_derived("hunspell_en_GB") | read_derived(
        "hunspell_en_GB_plain")
    scowl_full = read_derived("scowl") | read_derived("scowl_plain")
    capable = wikt_all | hs_gb | scowl_full | read_derived("wordnet") \
        | read_derived("web2a")
    refs = {
        "base": reference,
        "accent": {w for w in capable
                   if class_flags(w) & {"accented", "diaeresis"}},
        "hyphen": {w for w in capable if "-" in w},
        "apos": {w for w in capable if "'" in w},
        "lig": {w for w in capable
                if class_flags(w) & {"ligature"}},
    }
    admission = {}
    for fam, (feature, real_class) in FAMILY_FEATURE.items():
        pairs = strip.get(fam, [])
        artifacts = [c for _, c in pairs]
        detect_fn, refname = detect_for[fam]
        fam_vals = np.array(
            [live_ratio(a, detect_fn, refs[refname]) for a in artifacts],
            dtype=np.float64)
        real_ws = test_by_class.get(real_class, [])[:4000]
        real_vals = feature_values(real_ws, feature)
        fire_fam = float(np.isfinite(fam_vals).mean()) if len(fam_vals) \
            else 0.0
        fire_real = float(np.isfinite(real_vals).mean()) if len(real_vals) \
            else 0.0
        sep = auc_ci(fam_vals, real_vals)   # oriented: high ratio = artifact
        ratio = fire_fam / fire_real if fire_real > 0 else float("inf") \
            if fire_fam > 0 else 0.0
        admitted = (sep is not None and sep["lo"] >= ADMIT_AUC_LO
                    and ratio >= ADMIT_FIRE_RATIO)
        admission[fam] = {
            "n_corruptions": len(artifacts),
            "auc_oriented": sep,
            "fire_rate_corruptions": round(fire_fam, 4),
            "fire_rate_real": round(fire_real, 4),
            "fire_ratio": None if ratio == float("inf")
            else round(ratio, 2),
            "admitted": bool(admitted),
        }
    report["family_admission"] = admission
    report["admitted_families"] = sorted(
        FAMILY_FEATURE[f][0] for f, a in admission.items() if a["admitted"])

    # -- SR3: corpus features on GB-contained corruptions vs rare real ------
    gb_vol = ev.column("scowl_tier")  # placeholder replaced below
    vol = col["gb_log10_volume"]
    contained = [w for w in families["ocr"] if gb_match_map.get(w, 0) > 0]
    test_vol = np.array([vol[ix[w]] for w in test_pos])
    finite = np.isfinite(test_vol)
    if finite.sum() > 100:
        q1 = np.nanquantile(test_vol[finite], 0.25)
        rare_real = [w for w in test_pos
                     if np.isfinite(vol[ix[w]]) and vol[ix[w]] <= q1]
    else:
        rare_real = []
    sr3 = {}
    fired = False
    for feature in CORPUS_FEATURES:
        rv = feature_values(rare_real, feature)
        cv = feature_values(contained, feature)
        row = auc_ci(rv, cv)
        if feature == "ocr_neighbor_freq_ratio":
            row = auc_ci(cv, rv)      # oriented: corruption above rare-real
        sr3[feature] = row
    separated = [f for f, r in sr3.items()
                 if r is not None and not (r["lo"] <= 0.5 <= r["hi"])]
    report["sr3"] = {
        "gb_contained_corruptions": len(contained),
        "rare_real": len(rare_real),
        "per_feature": sr3,
        "separated_features": separated,
        "fires": len(separated) == 0,
    }
    report["sr2_reading_b"] = manifest["sr2_reading_b"]
    report["family_sizes"] = {k: len(v) for k, v in families.items()}
    report["strip_family_sizes"] = {k: len(v) for k, v in strip.items()}

    (FEATURES_DIR / "features_gate.json").write_text(
        json.dumps(report, indent=2) + "\n")

    # doc-figures for FEATURES.md, re-checked by the enforcer
    figures = {
        "universe_rows": manifest["universe_rows"],
        "pool": manifest["partitions"]["pool"],
        "pool_strict": manifest["partitions"]["pool_strict"],
        "train": manifest["partitions"]["train"],
        "dev": manifest["partitions"]["dev"],
        "test": manifest["partitions"]["test"],
        "ppl_plain": manifest["charmodel"]["perplexity_by_class"].get(
            "plain"),
        "gb_types": manifest["gb"]["types"],
        "zipf_alpha": round(manifest["zipf"]["alpha"], 4),
        "wordfreq_scored": manifest["wordfreq"]["scored"],
        "sr2_b_rows": manifest["sr2_reading_b"]["rows"],
        "sr2_b_pct": manifest["sr2_reading_b"]["pct"],
        "admitted_count": len(report["admitted_families"]),
        "morph_parsed": None,
    }
    for cls, v in manifest["charmodel"]["perplexity_by_class"].items():
        if not cls.startswith("__"):
            figures[f"ppl_{cls}"] = v
    (FEATURES_DIR / "features.json").write_text(
        json.dumps({"generated_by": "research/features/gate_report.py",
                    "doc_figures": {k: v for k, v in figures.items()
                                    if v is not None}}, indent=2) + "\n")
    print(json.dumps({
        "perplexity_na": report["perplexity"]["class_na_fallback"],
        "admitted": report["admitted_families"],
        "sr3_fires": report["sr3"]["fires"],
        "sr2_b": report["sr2_reading_b"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
