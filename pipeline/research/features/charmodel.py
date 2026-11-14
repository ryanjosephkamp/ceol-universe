"""
The orthotactic channel over the CEOL alphabet — the EOL charmodel
(english-openlist@496bf1f research/features/charmodel.py) with exactly
one change: ALPHABET is the 47 CEOL letters plus hyphen and apostrophe
plus the end marker — 50 symbols. Interpolated char n-gram, order 4,
lambdas EM-tuned on dev, renormalized over seen histories (the 0.53-mass
lesson is inherited machinery). Everything else is the ported code.
"""

from __future__ import annotations

import math
from collections import defaultdict

from ceol.grammar import APOSTROPHE, HYPHEN, LETTERS

BOUNDARY = "^"
END = "$"
ALPHABET = sorted(LETTERS) + [HYPHEN, APOSTROPHE, END]
ORDER = 4


class CharModel:
    def __init__(self, order: int = ORDER):
        self.order = order
        self.counts = [defaultdict(lambda: defaultdict(int))
                       for _ in range(order)]
        self.lambdas = [1.0 / (order + 1)] * (order + 1)
        self.uniform = 1.0 / len(ALPHABET)

    def fit(self, words) -> None:
        for w in words:
            padded = BOUNDARY * (self.order - 1) + w + END
            for i in range(self.order - 1, len(padded)):
                c = padded[i]
                for k in range(self.order):
                    h = padded[i - k:i]
                    self.counts[k][h][c] += 1

    def finalize(self) -> None:
        self._p = []
        for k in range(self.order):
            table = {}
            for h, dist in self.counts[k].items():
                total = sum(dist.values())
                table[h] = {c: n / total for c, n in dist.items()}
            self._p.append(table)

    def _ml(self, k: int, h: str, c: str) -> float:
        if hasattr(self, "_p"):
            dist = self._p[k].get(h)
            return dist.get(c, 0.0) if dist else 0.0
        dist = self.counts[k].get(h)
        if not dist:
            return 0.0
        total = sum(dist.values())
        return dist.get(c, 0) / total

    def _seen(self, k: int, h: str) -> bool:
        if hasattr(self, "_p"):
            return h in self._p[k]
        return h in self.counts[k]

    def prob(self, h: str, c: str) -> float:
        p = self.lambdas[0] * self.uniform
        mass = self.lambdas[0]
        for k in range(self.order):
            hk = h[len(h) - k:] if k else ""
            if self._seen(k, hk):
                mass += self.lambdas[k + 1]
                p += self.lambdas[k + 1] * self._ml(k, hk, c)
        return p / mass

    def tune(self, dev_words, iterations: int = 12) -> list[float]:
        events = []
        for w in dev_words:
            padded = BOUNDARY * (self.order - 1) + w + END
            for i in range(self.order - 1, len(padded)):
                events.append(
                    (padded[max(0, i - self.order + 1):i], padded[i]))
        for _ in range(iterations):
            weight = [0.0] * (self.order + 1)
            for h, c in events:
                parts = [self.lambdas[0] * self.uniform]
                for k in range(self.order):
                    hk = h[len(h) - k:] if k else ""
                    if self._seen(k, hk):
                        parts.append(self.lambdas[k + 1] * self._ml(k, hk, c))
                    else:
                        parts.append(0.0)
                z = sum(parts)
                if z <= 0:
                    continue
                for j, part in enumerate(parts):
                    weight[j] += part / z
            total = sum(weight)
            self.lambdas = [x / total for x in weight]
        return self.lambdas

    def logp_word(self, w: str) -> tuple[float, float]:
        padded = BOUNDARY * (self.order - 1) + w + END
        lp = 0.0
        n = 0
        for i in range(self.order - 1, len(padded)):
            h = padded[max(0, i - self.order + 1):i]
            p = self.prob(h, padded[i])
            lp += math.log10(max(p, 1e-12))
            n += 1
        return lp, lp / n

    def perplexity(self, words) -> float:
        total_lp, total_n = 0.0, 0
        for w in words:
            lp, _ = self.logp_word(w)
            total_lp += lp
            total_n += len(w) + 1
        return 10 ** (-total_lp / total_n)

    def sample_word(self, unit_stream, max_len: int = 24) -> str:
        h = BOUNDARY * (self.order - 1)
        out = []
        while len(out) < max_len:
            u = next(unit_stream)
            acc = 0.0
            for c in ALPHABET:
                acc += self.prob(h, c)
                if u <= acc:
                    break
            if c == END:
                break
            out.append(c)
            h = (h + c)[-(self.order - 1):]
        return "".join(out)
