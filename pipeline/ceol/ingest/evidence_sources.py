"""
C4 evidence-layer sources — what the census never had to read.

Three jobs on top of the census's ingest (whose derived sets the evidence
matrix reuses as-is):

- **WordNet re-derived under the CEOL grammar.** The census never read
  WordNet (it entered the EOL as a binary source, derived under
  `^[a-z]+$`), so its hyphenated and apostrophe lemmas — measured at
  5,220 and 56 — were invisible everywhere. The plain split must equal
  the EOL's pinned derived set exactly; parity is asserted, not assumed.
- **The SCOWL ordinal tier map under the census's inclusion rule**
  (words + contractions, every non-special category — wider than the
  EOL's six `*-words.N` families), so every census-scowl word carries a
  tier. Membership must equal the census's scowl set exactly.
- **The four Scrabble lists** read READ-ONLY from the EOL cache and
  verified against the audit's pins before every use.
"""

from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path

from .census_sources import PINS, SCOWL_FILE, SCOWL_SPECIAL, _finish
from .common import (DERIVED_DIR, EOL_REPO, NLTK_WORDNET_ZIP, SourceCensus, resolve_artifact,
                     sha256_file)

#: EOL derived sets used as binary detectors, pinned (same values the C3
#: audit verified). wordnet's pin guards the PARITY check, not a reuse.
EOL_DERIVED_PINS = {
    "wordnet": ("266b875d86cb132cb924490626140e8c104b7170db5c5e14d2e117fd3a32bed2", 77503),
    "enable1": ("3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89", 172823),
    "sowpods_legacy": ("5a855b21aa2bef5b98be71c719668337b3ceeaa6cb1cc08efab2a8ff0759a38f", 267751),
    "nwl2023": ("79de4b07ed6f38ad1bdb1bf874e42383815b78730b23a0edce511f3ef043058e", 196601),
    "csw21": ("136332497985c48389f017064e7875ce49398ee10b5dc0fa4c701f7a5085985c", 279077),
}

SCOWL_TIERS_TSV = DERIVED_DIR / "scowl_tiers_ceol.tsv"


def read_eol_derived(source: str) -> set[str]:
    """An EOL derived set, read-only, refused unless it matches its pin."""
    pin, count = EOL_DERIVED_PINS[source]
    path = EOL_REPO / ".cache" / "sources" / "derived" / f"{source}.txt"
    got = sha256_file(path)
    if got != pin:
        raise RuntimeError(f"{source}: EOL derived sha {got} != pin {pin}")
    with open(path, encoding="utf-8") as f:
        words = {line.rstrip("\n") for line in f if line.strip()}
    if len(words) != count:
        raise RuntimeError(f"{source}: {len(words):,} words != pinned {count:,}")
    return words


def ingest_wordnet() -> dict:
    """WordNet under the CEOL grammar, with EOL parity on the plain split."""
    from nltk.corpus import wordnet as wn

    census = SourceCensus("wordnet")
    for syn in wn.all_synsets():
        for lemma in syn.lemmas():
            census.add(lemma.name())

    eol_set = read_eol_derived("wordnet")
    if census.plain != eol_set:
        only_ceol = sorted(census.plain - eol_set)[:5]
        only_eol = sorted(eol_set - census.plain)[:5]
        raise RuntimeError(
            "wordnet parity FAILED: plain split != EOL derived set "
            f"(ceol-only {only_ceol}, eol-only {only_eol})")

    artifact = NLTK_WORDNET_ZIP
    return _finish(census, meta={
        "artifact_sha256": sha256_file(artifact) if artifact.exists() else None,
        "url": "nltk corpora/wordnet (installed)",
        "wordnet_version": wn.get_version(),
        "eol_parity": "plain split == EOL derived set (asserted)",
    })


def ingest_scowl_tiers() -> dict:
    """
    The ordinal tier map: smallest SCOWL size containing each word, over
    exactly the files the census included (words + contractions, every
    non-special category). Membership must equal the census's scowl set.
    """
    url, sha, eol_rel = PINS["scowl"]
    path = resolve_artifact("scowl-2020.12.07.tar.gz", url=url, sha256=sha,
                            eol_relative=eol_rel)
    from ceol.grammar import normalize

    tier: dict[str, int] = {}
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if SCOWL_SPECIAL.match(member.name):
                continue
            m = SCOWL_FILE.match(member.name)
            if not m or m.group(2) not in ("words", "contractions"):
                continue
            size = int(m.group(3))
            fh = tar.extractfile(member)
            assert fh is not None
            for line in io.TextIOWrapper(fh, encoding="latin-1"):
                key = normalize(line.strip()) if line.strip() else None
                if key and size < tier.get(key, 999):
                    tier[key] = size

    from .common import read_derived
    census_set = read_derived("scowl") | read_derived("scowl_plain")
    if set(tier) != census_set:
        raise RuntimeError(
            f"scowl tier membership {len(tier):,} != census set "
            f"{len(census_set):,} — inclusion rules drifted")

    with open(SCOWL_TIERS_TSV, "w", encoding="utf-8") as f:
        for w in sorted(tier):
            f.write(f"{w}\t{tier[w]}\n")

    # Comparison with the EOL's words-only tier map: reported, not asserted
    # (the census's wider inclusion can only lower a tier).
    eol_tsv = EOL_REPO / ".cache" / "sources" / "derived" / "scowl_tiers.tsv"
    same = lower = higher = eol_only = 0
    with open(eol_tsv, encoding="utf-8") as f:
        for line in f:
            w, t = line.rstrip("\n").split("\t")
            t = int(t)
            if w not in tier:
                eol_only += 1
            elif tier[w] == t:
                same += 1
            elif tier[w] < t:
                lower += 1
            else:
                higher += 1
    if higher or eol_only:
        raise RuntimeError(
            f"scowl tiers must never exceed the EOL's on shared words "
            f"(higher={higher}, eol_only={eol_only})")
    return {
        "record_count": len(tier),
        "tiers_sha256": sha256_file(SCOWL_TIERS_TSV),
        "tier_values": sorted(set(tier.values())),
        "eol_comparison": {"same": same, "lower": lower, "higher": higher,
                           "eol_only": eol_only},
    }
