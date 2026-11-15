"""
Leakage-clean partitions for the C4 character model — C-011.

The pool is the strong positives under masked evidence: a word qualifies
iff it fires on >= ceil((2/3) * A(w)) of its APPLICABLE detectors, where
A(w) = applicable binary detectors + SCOWL where applicable (C-010
masks). On plain words A = 12 and the threshold is 8 — exactly the EOL's
published 8-of-12 rule; on masked classes the ratio is the same standard
applied to the evidence that exists. The declared sensitivity variant
uses 3/4.

Splits are sha256(seed:word) hash-range — one word's membership never
depends on the rest of the pool. No library RNG. The C5 calibration
sample must exclude train ∪ dev, re-derived from this seed and rule.
"""

from __future__ import annotations

import hashlib
import math

SEED = "c4-partitions-2026-08-20"
POOL_RATIO = 2 / 3
SENSITIVITY_RATIO = 3 / 4

TRAIN_END = 0.70
DEV_END = 0.80


def hash_unit(word: str, seed: str = SEED) -> float:
    h = hashlib.sha256(f"{seed}:{word}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


def assign(word: str) -> str:
    u = hash_unit(word)
    if u < TRAIN_END:
        return "train"
    if u < DEV_END:
        return "dev"
    return "test"


def threshold(applicable: int, ratio: float = POOL_RATIO) -> int:
    """Strong-positive fire threshold for a word with `applicable`
    detectors visible. ceil(2/3 * 12) == 8: the EOL rule on plain words."""
    return max(1, math.ceil(ratio * applicable))
