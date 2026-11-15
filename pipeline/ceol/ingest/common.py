"""
Shared machinery for the C1 exceptions census.

Adapted from the EOL's research/ingest/common.py — same property served:
every derived set must reproduce byte-for-byte from pinned artifacts alone.
Two differences: normalize() is the CEOL grammar (ceol/grammar.py), and
artifact resolution may REUSE the EOL repo's cached raw files (read-only)
when their sha256 matches the pin — same bytes, no second download.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

from ceol.grammar import (APOSTROPHE, CHARSET, LETTERS, classes, normalize)

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / ".cache"
RAW_DIR = CACHE / "raw"
DERIVED_DIR = CACHE / "derived"

#: Inputs that live outside this repository. Each is named by an environment
#: variable; where it is not set the default is a folder under `.inputs/` at the
#: root of the checkout, which does not exist, so a check that needs the input
#: reports it as missing instead of reading something elsewhere on the machine.
INPUTS = Path(os.environ.get("CEOL_INPUTS", REPO.parent / ".inputs"))


def input_path(env_name: str, *default: str) -> Path:
    value = os.environ.get(env_name)
    return Path(value) if value else INPUTS.joinpath(*default)


#: The English OpenList repository (`CEOL_EOL_REPO`): read-only. Reading its
#: cached artifacts is permitted; writing anything under it is not.
EOL_REPO = input_path("CEOL_EOL_REPO", "english-openlist")

#: The installed NLTK WordNet archive (`CEOL_NLTK_WORDNET`).
NLTK_WORDNET_ZIP = input_path("CEOL_NLTK_WORDNET", "nltk_data", "corpora", "wordnet.zip")

USER_AGENT = ("common-english-openlist/0.1 "
              "(https://github.com/ryanjosephkamp/common-english-openlist; "
              "C1 exceptions census)")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_artifact(filename: str, *, url: str | None, sha256: str,
                     eol_relative: str | None = None) -> Path:
    """
    Locate the pinned artifact, cheapest first: the CEOL cache, then the EOL
    repo's cache (read-only reuse of identical bytes), then a fresh download.
    Whatever the route, the file's sha256 must equal the pin — a mismatch is
    a hard error, never a silent substitution.
    """
    dest = RAW_DIR / filename
    if dest.exists() and sha256_file(dest) == sha256:
        return dest
    if eol_relative is not None:
        eol_path = EOL_REPO / eol_relative
        if eol_path.exists() and sha256_file(eol_path) == sha256:
            return eol_path
    if url is None or url.startswith("file:"):
        path = Path(url.removeprefix("file://")) if url else None
        if path and path.exists() and sha256_file(path) == sha256:
            return path
        raise RuntimeError(f"{filename}: pinned artifact not found locally "
                           "and not downloadable")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        for chunk in iter(lambda: r.read(1 << 20), b""):
            f.write(chunk)
            h.update(chunk)
    got = h.hexdigest()
    if got != sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{url}: sha256 {got} != pin {sha256}. The "
                           "artifact changed upstream; re-pin deliberately.")
    tmp.rename(dest)
    return dest


def diagnose_reject(raw: str) -> str:
    """
    Why a source entry failed the grammar — the census's reject taxonomy.

    'trailing_apostrophe' is the possessive-shaped reject (dogs'): the entry
    would pass were the pending possessive extension admitted. It feeds the
    C1 gate directly. 'undeclared_letter' counts entries whose only crime is
    a letter outside the closed inventory (å, ø, š) — the number that sizes
    any future inventory-extension decision.
    """
    s = unicodedata.normalize("NFC", raw)
    if "’" in s:
        s = s.replace("’", APOSTROPHE)
    s = unicodedata.normalize("NFC", s.lower())
    if s.endswith(APOSTROPHE) and normalize(s[:-1]) is not None:
        return "trailing_apostrophe"
    if any(c not in CHARSET and unicodedata.category(c).startswith("L")
           for c in s) and not any(c.isdigit() for c in s):
        return "undeclared_letter"
    return "other"


class SourceCensus:
    """
    Accumulates one source's census: every raw entry goes through add(),
    which normalizes under the CEOL grammar, tallies class flags for the
    survivors and reject reasons for the rest.
    """

    def __init__(self, source_id: str):
        self.source_id = source_id
        self.entries_seen = 0
        self.words: set[str] = set()          # CEOL-valid, class-flagged only
        self.plain: set[str] = set()          # CEOL-valid, plain [a-z]+
        self.class_counts: dict[str, int] = {}
        self.rejects: dict[str, int] = {}

    def add(self, raw: str) -> str | None:
        self.entries_seen += 1
        key = normalize(raw)
        if key is None:
            reason = diagnose_reject(raw)
            self.rejects[reason] = self.rejects.get(reason, 0) + 1
            return None
        flags = classes(key)
        if not flags:
            self.plain.add(key)
            return key
        if key not in self.words:
            self.words.add(key)
            for f in flags:
                self.class_counts[f] = self.class_counts.get(f, 0) + 1
        return key

    def stats(self) -> dict:
        return {
            "source": self.source_id,
            "entries_seen": self.entries_seen,
            "plain_az": len(self.plain),
            "exception_candidates": len(self.words),
            "classes": dict(sorted(self.class_counts.items())),
            "rejects": dict(sorted(self.rejects.items())),
        }


def write_derived(source_id: str, words: set[str], *, meta: dict) -> dict:
    """Sorted, hashed, meta beside it — the EOL determinism discipline."""
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = DERIVED_DIR / f"{source_id}.txt"
    with open(out, "w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(w + "\n")
    meta = {**meta, "record_count": len(words),
            "derived_sha256": sha256_file(out),
            "retrieved": date.today().isoformat()}
    with open(DERIVED_DIR / f"{source_id}.meta.json", "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


def read_derived(source_id: str) -> set[str]:
    with open(DERIVED_DIR / f"{source_id}.txt", encoding="utf-8") as f:
        return {line.rstrip("\n") for line in f if line.strip()}


def open_maybe_gzip(path: Path, encoding="utf-8", errors="strict"):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding=encoding, errors=errors)
    return open(path, encoding=encoding, errors=errors)
