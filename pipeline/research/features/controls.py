"""
The negative-control families under the CEOL grammar — C-011.

The EOL's four families carry over; the foreign and pseudo families now
live in the wider alphabet naturally (the census's foreign screen is FULL
of accented non-English — the `interprétation` class — which is exactly
the control the accent features need). Families are class-annotated so
the gate can report separation per class. Everything is sha256-ranked;
no library RNG anywhere.

  ocr        held-out strong positives corrupted through the six typed
             pairs; kept only when the corruption is NOT in the reference.
  strip      class-bearing held-out positives corrupted by the proposed
             families (diacritic-strip, hyphen-junction, hyphen-drop,
             apostrophe-loss, ligature-expansion), one subfamily each —
             the admission gates' instruments.
  pseudo     drawn from the trained CEOL char model, kept only if absent
             from EVERY source's key set.
  foreign    lowercase Wiktionary titles with NO English section and no
             binary-detector hit — real words, none of them English.
  mw         the EOL's MW-refuted inflections (read-only ledgers) — real,
             already-adjudicated negatives.
"""

from __future__ import annotations

import csv
import hashlib
import itertools

from ceol.ingest.common import EOL_REPO, read_derived

from . import ocr
from .partitions import hash_unit

FAMILY_SIZE = 2000


def _rank(words, seed):
    return sorted(words, key=lambda w: hashlib.sha256(
        f"{seed}:{w}".encode()).hexdigest())


def ocr_family(test_positives, reference) -> list[str]:
    out = []
    seen = set()
    for w in _rank(test_positives, "ocr-family"):
        c = ocr.corrupt(w, hash_unit(w, "ocr-site"))
        if c and c not in reference and c not in seen and c != w:
            seen.add(c)
            out.append(c)
        if len(out) >= FAMILY_SIZE:
            break
    return out


def strip_families(test_positives_by_class, all_source_keys) -> dict:
    """Manufactured corruptions for each proposed family: corrupt real
    class-bearing held-out positives, keep only corruptions no source
    attests (an attested 'corruption' is the variant-spelling confound
    itself and would poison the control with real words)."""
    fams = {
        "diacritic_strip": ("accented", ocr.corrupt_diacritic),
        "hyphen_junction": ("plain",
                            lambda w: ocr.corrupt_hyphen_junction(
                                w, hash_unit(w, "hyphen-site"))),
        "hyphen_drop": ("hyphenated", ocr.corrupt_hyphen_drop),
        "apostrophe_loss": ("apostrophe-form", ocr.corrupt_apostrophe_loss),
        "ligature_expansion": ("ligature", ocr.corrupt_ligature),
    }
    out = {}
    for name, (cls, fn) in fams.items():
        pool = test_positives_by_class.get(cls, [])
        family, seen = [], set()
        for w in _rank(pool, f"{name}-family"):
            c = fn(w)
            if c and c != w and c not in seen and c not in all_source_keys:
                seen.add(c)
                family.append((w, c))
            if len(family) >= FAMILY_SIZE:
                break
        out[name] = family
    return out


def pseudo_family(model, all_source_keys) -> list[str]:
    def units(tag):
        for i in itertools.count():
            h = hashlib.sha256(f"pseudo:{tag}:{i}".encode()).digest()
            yield int.from_bytes(h[:8], "big") / 2**64
    out, seen = [], set()
    for tag in itertools.count():
        w = model.sample_word(units(tag))
        if 2 <= len(w) <= 24 and w not in all_source_keys and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= FAMILY_SIZE:
            break
    return out


def foreign_family(detector_hit_words) -> dict[str, list[str]]:
    """Class-annotated: the plain slice plus the accented slice (the
    census's donor-language spillover, now a first-class control)."""
    from ceol.grammar import classes as class_flags
    titles = (read_derived("wiktionary_titles")
              | read_derived("wiktionary_titles_plain"))
    english = read_derived("wiktionary_english_all")
    pool = titles - english - detector_hit_words
    plain = [w for w in pool if not class_flags(w)]
    accented = [w for w in pool
                if class_flags(w) & {"accented", "diaeresis"}]
    return {"foreign_plain": _rank(plain, "foreign-family")[:FAMILY_SIZE],
            "foreign_accented":
                _rank(accented, "foreign-accented")[:FAMILY_SIZE]}


def mw_family() -> list[str]:
    forms = set()
    for name in ("ledger_stage3.csv", "ledger_stage4.csv"):
        path = EOL_REPO / "corrections" / name
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("outcome") == "inflection-absent":
                    forms.update(row.get("forms_missing", "").split())
    return sorted(forms)
