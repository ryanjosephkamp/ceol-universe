"""The study's wall list and the whole-word matcher over it.

The in-the-wild study keeps 4 lists private (PLAN.md §2, rule 7): the
development ledger with its decks, the synthetic controls, the probe words,
and the pilot words. The archive's module `research/inthewild/walled_terms.py`
reads them from the archive's committed files. `tools/build_private.py` runs
that module over the archive's `main` and writes its result to
`private/wall/walled_terms.json`; this module reads that file. The lists
themselves are never in this repository.

The matcher is the archive's, unchanged: `canon`, `pattern`, `find_hits`, and
`redact` are copied from the archive's module at its commit 5faa780. A term
matches as a whole word or a whole phrase: it never matches where a letter
stands directly before or after it, and a spaced term matches across any run
of whitespace.

`Matcher` returns the same set as `find_hits` and reads the text once. The
scan uses it; `tests/test_safeguards.py` holds the two to the same result.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata

from safeguards import locations

#: what a redacted copy shows in place of every walled term
PLACEHOLDER = "[WALLED]"

#: the names of the 4 lists, as the archive's module returns them
LISTS = ("ledger", "controls", "probes", "pilot")


class WallAbsent(RuntimeError):
    """`private/wall/walled_terms.json` is not on this machine."""


def canon(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower().strip()


def available() -> bool:
    return locations.wall_json().exists()


def walled_terms() -> dict[str, set[str]]:
    """The 4 walled lists, read from the private file."""
    path = locations.wall_json()
    if not path.exists():
        raise WallAbsent(
            f"{path} is absent; it isn't in the public repository. "
            f"In a worktree of a checkout that has it, run `make link`")
    body = json.loads(path.read_text(encoding="utf-8"))
    lists = {name: {canon(t) for t in body["lists"][name]} for name in LISTS}
    assert all(lists.values())
    assert lists["controls"] <= lists["ledger"]
    return lists


def all_terms() -> set[str]:
    return set().union(*walled_terms().values())


def pattern(term: str) -> re.Pattern[str]:
    """The whole-word (or whole-phrase) pattern for one canonical term."""
    return re.compile(
        r"(?<![^\W\d_'\-])"
        + r"\s+".join(re.escape(part) for part in term.split())
        + r"(?![^\W\d_'\-])")


def find_hits(text: str, terms: set[str]) -> set[str]:
    """Every walled term that occurs in `text` as a whole word or phrase."""
    text_c = canon(text)
    return {term for term in terms if pattern(term).search(text_c)}


#: a maximal run of letters; the patterns above treat nothing else as part
#: of a word
_LETTER_RUN = re.compile(r"[^\W\d_]+")


class Matcher:
    """`find_hits` for 1 fixed set of terms, reading each text once.

    A pattern can only match where a letter run of the text starts, and that
    run then equals the term's own leading letter run. So the terms are
    indexed by their leading letter run, and only the terms indexed under a
    run of the text are tried at that run. A term that starts with a
    character other than a letter has no such run and is searched for
    directly.
    """

    def __init__(self, terms: set[str]):
        self.terms = set(terms)
        self._by_run: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        self._unanchored: list[tuple[str, re.Pattern[str]]] = []
        for term in sorted(self.terms):
            lead = _LETTER_RUN.match(term)
            if lead:
                self._by_run.setdefault(lead.group(0), []).append(
                    (term, pattern(term)))
            else:
                self._unanchored.append((term, pattern(term)))

    def spans(self, text: str) -> list[tuple[int, int, str]]:
        """Every match as (start, end, term), over the canonical text."""
        text_c = canon(text)
        found = []
        for run in _LETTER_RUN.finditer(text_c):
            for term, pat in self._by_run.get(run.group(0), ()):
                m = pat.match(text_c, run.start())
                if m:
                    found.append((m.start(), m.end(), term))
        for term, pat in self._unanchored:
            found.extend((m.start(), m.end(), term)
                         for m in pat.finditer(text_c))
        return found

    def hits(self, text: str) -> set[str]:
        return {term for _start, _end, term in self.spans(text)}

    def hit_lines(self, text: str) -> list[int]:
        """The 1-based numbers of the lines of the canonical text on which
        a match starts. A report names lines, never terms."""
        text_c = canon(text)
        starts = sorted({start for start, _end, _term in self.spans(text)})
        return sorted({text_c.count("\n", 0, start) + 1 for start in starts})


#: the distinct placeholder's shape: one 6-hex label per distinct term
DISTINCT_PLACEHOLDER = re.compile(r"\[WALLED-[0-9a-f]{6}\]")


def redact(text: str, terms: set[str] | None = None, *,
           distinct: bool = False, salt: str | None = None) -> tuple[str, int]:
    """Replace every whole-word occurrence of every walled term in `text`
    with PLACEHOLDER, longest terms first so that a phrase is 1 replacement,
    and return the redacted text with the count. Matching is
    case-insensitive over the NFC text, so the text's own casing and
    structure survive. Raises if any hit survives: a redacted copy is clean
    or it is not produced.

    With `distinct`, each distinct term gets its own label
    `[WALLED-<6 hex>]` from a salt that is never recorded, so equality and
    distinctness of the withheld words survive in the copy while no term is
    recoverable. Pass 1 `salt` to every call of 1 export so that a word
    carries 1 label across its files."""
    if terms is None:
        terms = all_terms()
    out = unicodedata.normalize("NFC", text)
    count = 0
    if distinct:
        salt = salt or secrets.token_hex(16)

        def label(term: str) -> str:
            digest = hashlib.sha256((salt + term).encode("utf-8")).hexdigest()
            return f"[WALLED-{digest[:6]}]"
    else:
        def label(term: str) -> str:
            return PLACEHOLDER
    for term in sorted(terms, key=lambda t: (-len(t), t)):
        out, n = re.subn(pattern(term).pattern, label(term), out,
                         flags=re.IGNORECASE)
        count += n
    left = find_hits(out, terms)
    if left:
        raise ValueError(f"{len(left)} walled term(s) survived redaction")
    return out, count
