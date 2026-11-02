"""The restricted words of the license split and their matcher.

A restricted word is a string of the universe that only NWL2023 or CSW21
lists. PLAN.md §2 rule 2 keeps those words out of every commit and every
publication. The list is the pin's own (`data/cache/audit/
universe_miss_restricted.csv` in the bootstrap package), copied to
`private/restricted/` by `tools/build_private.py`.

The matcher is the archive's license test's, unchanged: the text in lower
case is split on every character outside a to z, and a restricted word is
found where it equals 1 of the pieces.
"""

from __future__ import annotations

import csv
import re

from safeguards import locations

_NOT_A_TO_Z = re.compile(r"[^a-z]+")


class RestrictedAbsent(RuntimeError):
    """`private/restricted/universe_miss_restricted.csv` is not on this machine."""


def available() -> bool:
    return locations.restricted_csv().exists()


def restricted_words() -> set[str]:
    path = locations.restricted_csv()
    if not path.exists():
        raise RestrictedAbsent(
            f"{path} is absent; build it with `make private` in the main "
            f"checkout, or link it into a worktree with `make link`")
    with path.open(encoding="utf-8", newline="") as f:
        words = {row["word"] for row in csv.DictReader(f)}
    assert words
    return words


def pieces(text: str) -> set[str]:
    return set(_NOT_A_TO_Z.split(text.lower()))


def find_hits(text: str, words: set[str]) -> set[str]:
    """Every restricted word that occurs in `text` as a whole piece."""
    return pieces(text) & words


def hit_lines(text: str, words: set[str]) -> list[int]:
    """The 1-based numbers of the lines that hold a restricted word. A report
    names lines, never words."""
    return [n for n, line in enumerate(text.split("\n"), 1)
            if pieces(line) & words]
