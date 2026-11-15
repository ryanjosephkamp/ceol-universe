"""Whether the orthotactic columns reveal a withheld list.

The 2 orthotactic columns of the feature layer (C-011) are a string's
log-probability under the layer's character model
(`research/features/charmodel.py`): an interpolated order-4 character
n-gram model over the 50 symbols of the CEOL alphabet. The model was
fitted on the strong-positive pool (`research/features/partitions.py`),
the strings that at least 2/3 of their applicable panel sets list, and the
13 panel sets include the 5 withheld lists. No public field may reveal a
withheld list's membership, so this test asks
what a reader holding only the public release and the public code could
learn about the withheld lists from those columns:

1. **The refit.** The model refitted by the committed code reproduces the
   layer's column, so a reader can rebuild it.
2. **The published-only model.** The same model fitted on the pool the
   same rule chooses from the 8 published panel sets alone, which a reader
   can also build.
3. **The residual test.** Over the shipped single-token rows with the
   commonest applicable count, in each stratum of the same number of
   published listings: the released column minus the published-only
   model's, as a score of whether a row is in the pool. Within a stratum a
   pool row is one that enough withheld lists also list, so the AUC is 0.5
   when the residual carries nothing about the withheld lists.
4. **The held-out pool.** The same test with the pool rows of the test
   partition alone, which the released model never fitted: a trace there
   is the model's lean, not its memory of single strings.
5. **Memorization.** The pool's training strings against its test strings,
   under the released column.

A column reveals a withheld list when, in any stratum, the 95% interval of
the residual's AUC lies above 0.5 (`reveals_any`). The AUC and its interval
are the feature gate's (`research/features/gate_report.auc_ci`). The
record holds AUCs and the pool sizes the feature manifest already
publishes, and no count of rows crossed with the pool, which would cross a
withheld list with a fine public attribute (docs/ANALYSIS_PLAN.md §9,
rule 3). No word is printed.

Run (needs `data/`, the pinned layers, and v2.1's release files):
    python3 -m research.release.feature_leak            write the record
    python3 -m research.release.feature_leak --check    recompute and compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from ceol.ingest.common import sha256_file
from research.features import charmodel
from research.features.build_features import DETECTORS
from research.features.gate_report import auc_ci
from research.features.partitions import assign, threshold
from research.release import build_release as B
from research.release import withholding as W

RDIR = B.REPO / "research" / "release"
VERSION = "v2.1"
RECORD = RDIR / f"feature_leak_{VERSION}.json"
COLUMNS = ("orthotactic_logp_total", "orthotactic_logp_per_char")
#: the strata reported. At the commonest applicable count, 12 (web2a does
#: not apply to plain strings, C-010), the pool needs 8 listings and the 4
#: withheld lists that apply give at most 4: a row with fewer than 4
#: published listings is never in the pool, and a row with 8 always is
STRATA = (4, 5, 6, 7)
#: the deterministic probe of the refit: every PROBE_STEP-th shipped row
PROBE_STEP = 200_000


def log(msg: str) -> None:
    print(f"[leak] {msg}", flush=True)


def layer(name: str) -> Path:
    """The pinned layer `name`, held to the sha256 v2.1's record names."""
    record = json.loads((RDIR / f"release_{VERSION}.json").read_text())
    source = record["sources"][name]
    path = B.REPO / source["path"]
    if sha256_file(path) != source["sha256"]:
        raise SystemExit(f"{source['path']} is not the layer v2.1 was built "
                         "from; nothing is written")
    return path


def fitted(words: list[str]) -> charmodel.CharModel:
    """The C-011 recipe (research/features/build_features.py): fit on the
    train partition, tune the interpolation on dev."""
    parts: dict[str, list[str]] = {"train": [], "dev": [], "test": []}
    for w in words:
        parts[assign(w)].append(w)
    model = charmodel.CharModel()
    model.fit(parts["train"])
    model.finalize()
    model.tune(parts["dev"])
    return model


def reveals(row: dict | None) -> bool:
    """Whether 1 stratum's residual AUC lies above chance: its whole 95%
    interval above 0.5."""
    return row is not None and row["lo"] > 0.5


def reveals_any(strata: dict[str, dict | None]) -> bool:
    """The rule for a column: any stratum's residual AUC above chance."""
    return any(reveals(row) for row in strata.values())


def _auc(pos: np.ndarray, neg: np.ndarray) -> dict | None:
    out = auc_ci(pos, neg)
    if out is None:
        return None
    return {k: out[k] for k in ("auc", "lo", "hi")}


def compute() -> dict:
    """The record: every figure of the test, from the pinned layers."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    paths = {name: layer(name) for name in ("evidence", "features")}
    ev = pq.read_table(paths["evidence"])
    feats = pq.read_table(paths["features"], columns=["word", *COLUMNS])
    if not ev.column("word").equals(feats.column("word")):
        raise SystemExit("the evidence and feature layers' rows diverged")
    words = feats.column("word")
    n = len(words)
    shipped_words = pq.read_table(
        B.resolve(VERSION).out_dir / "features.parquet",
        columns=["word"]).column("word")
    shipped = pc.is_in(words, value_set=shipped_words).to_numpy(
        zero_copy_only=False)
    log(f"{n:,} rows of the feature layer; the features config ships "
        f"{int(shipped.sum()):,}")

    fires = np.zeros(n, dtype=np.int8)
    applicable = np.zeros(n, dtype=np.int8)
    fires_pub = np.zeros(n, dtype=np.int8)
    applicable_pub = np.zeros(n, dtype=np.int8)
    names = [*DETECTORS, "scowl"]
    for name in names:
        if name == "scowl":
            tier = ev.column("scowl_tier").to_numpy(zero_copy_only=False)
            fire, app = tier > 0, tier != -1
        else:
            col = ev.column(name).to_numpy(zero_copy_only=False)
            fire, app = col == 1, col != -1
        fires += fire
        applicable += app
        if name not in W.WITHHELD_SETS:
            fires_pub += fire
            applicable_pub += app
    published = [s for s in names if s not in W.WITHHELD_SETS]
    if sorted(published) != sorted(W.PUBLISHED_SETS):
        raise SystemExit("the test's published panel is not the projection's")
    thresh = np.array([threshold(a) for a in range(len(names) + 1)],
                      dtype=np.int8)
    pool = fires >= thresh[applicable]
    pool_pub = fires_pub >= thresh[applicable_pub]
    pool_words = words.filter(pool).to_pylist()
    part = np.array([assign(w) for w in pool_words])
    pool_idx = np.flatnonzero(pool)
    log(f"pool {len(pool_idx):,}, the published-only pool "
        f"{int(pool_pub.sum()):,}")

    released = fitted(pool_words)
    published_only = fitted(words.filter(pool_pub).to_pylist())
    values = {c: feats.column(c).to_numpy(zero_copy_only=False).astype(float)
              for c in COLUMNS}

    probe = np.flatnonzero(shipped)[::PROBE_STEP]
    refit = 0.0
    for i, w in zip(probe, words.take(probe).to_pylist()):
        total, per_char = released.logp_word(w)
        for c, v in zip(COLUMNS, (total, per_char)):
            if not np.isnan(values[c][i]):
                refit = max(refit, abs(v - values[c][i]))
    log(f"the refit reproduces the layer to {refit:.2e} over "
        f"{len(probe)} probes")

    memorization = {c: _auc(values[c][pool_idx[part == "train"]],
                            values[c][pool_idx[part == "test"]])
                    for c in COLUMNS}

    common = int(np.bincount(applicable[shipped]).argmax())
    held_out = np.zeros(n, dtype=bool)
    held_out[pool_idx[part == "test"]] = True
    residual: dict[str, dict] = {c: {} for c in COLUMNS}
    residual_held_out: dict[str, dict] = {c: {} for c in COLUMNS}
    for k in STRATA:
        stratum = shipped & (applicable == common) & (fires_pub == k)
        inside = np.flatnonzero(stratum & pool)
        outside = np.flatnonzero(stratum & ~pool)
        idx = np.concatenate([inside, outside])
        scored = [published_only.logp_word(w)
                  for w in words.take(idx).to_pylist()]
        base = {COLUMNS[0]: np.array([s[0] for s in scored]),
                COLUMNS[1]: np.array([s[1] for s in scored])}
        tested = held_out[inside]
        for c in COLUMNS:
            r = values[c][idx] - base[c]
            r_in, r_out = r[:len(inside)], r[len(inside):]
            residual[c][str(k)] = _auc(r_in, r_out)
            residual_held_out[c][str(k)] = _auc(r_in[tested], r_out)
        log(f"{k} published listings: residual AUC "
            f"{residual[COLUMNS[1]][str(k)]['auc']:.4f}")

    verdict = {c: reveals_any(residual[c]) for c in COLUMNS}
    lows = [row["auc"] for row in residual[COLUMNS[1]].values()]
    held = [row["auc"] for row in residual_held_out[COLUMNS[1]].values()]
    record = {
        "generated_by": "research/release/feature_leak.py",
        "decision": "D-013",
        "version": VERSION,
        "inputs": {name: {"path": f"data/{path.name}",
                          "sha256": sha256_file(path)}
                   for name, path in paths.items()},
        "model": {"recipe": "research/features/charmodel.py, fitted and "
                            "tuned as research/features/build_features.py "
                            "does",
                  "order": charmodel.ORDER,
                  "alphabet": len(charmodel.ALPHABET),
                  "pool_rule": "fires >= ceil(2/3 * applicable) over the "
                               "13 panel sets (research/features/"
                               "partitions.py)",
                  "partition_rule": "sha256(seed:word): train < 0.7, "
                                    "dev < 0.8, else test"},
        "published_sets": published,
        "withheld_sets": list(W.WITHHELD_SETS),
        "pool": len(pool_idx),
        "pool_train": int((part == "train").sum()),
        "pool_published_only": int(pool_pub.sum()),
        "refit_max_abs_difference": float(f"{refit:.3g}"),
        "probes": len(probe),
        "applicable_count_of_the_strata": common,
        "memorization_auc": memorization,
        "residual_auc": residual,
        "residual_auc_held_out": residual_held_out,
        "rule": "a column reveals a withheld list when, in any stratum, the "
                "95% interval of the residual's AUC lies above 0.5",
        "reveals": verdict,
        "doc_figures": {
            "withheld_feature_columns": len(W.WITHHELD_FEATURES),
            "published_feature_columns": len(W.PUBLISHED_FEATURE_COLUMNS),
            "pool": len(pool_idx),
            "pool_train": int((part == "train").sum()),
            "pool_published_only": int(pool_pub.sum()),
            "refit": f"{refit:.2e}",
            "memorization_per_char": f"{memorization[COLUMNS[1]]['auc']:.4f}",
            **{f"residual_{k}": f"{residual[COLUMNS[1]][str(k)]['auc']:.4f}"
               for k in STRATA},
            **{f"residual_held_out_{k}":
               f"{residual_held_out[COLUMNS[1]][str(k)]['auc']:.4f}"
               for k in STRATA},
        },
        "decision_figures": {
            "residual_low": f"{min(lows):.2f}",
            "residual_high": f"{max(lows):.2f}",
            "held_out_low": f"{min(held):.2f}",
            "held_out_high": f"{max(held):.2f}",
        },
    }
    log(f"reveals: {verdict}")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="recompute the record and compare it with the "
                         "committed one; write nothing")
    args = ap.parse_args(argv)
    text = json.dumps(compute(), indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if text != RECORD.read_text(encoding="utf-8"):
            print(f"[leak] {RECORD.relative_to(B.REPO)} does not re-derive",
                  file=sys.stderr)
            return 1
        log(f"{RECORD.relative_to(B.REPO)} re-derives")
        return 0
    RECORD.write_text(text, encoding="utf-8")
    log(f"{RECORD.relative_to(B.REPO)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
