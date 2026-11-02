"""
S5c: the spaced-class applicability masks — measured, never assumed.

C-010's rule extends to the spaced class: detector x spaced is NA iff the
detector's derived output carries zero spaced entries AND a format/scope
account of the zero is recorded; any non-zero cell is applicable. This
script measures every cell and writes
research/universe_v2/spaced_applicability.json.

What is measured, per detector:

  - every pinned derived split (exceptions and plain), hash-verified
    against its recorded pin before counting, then scanned for
    space-bearing lines. The C4-era splits were derived under the
    pre-C-015 grammar, so their zeros are expected by construction —
    the measurement records them anyway, alongside the raw-format
    account of WHY the source cannot emit a spaced entry (the
    2026-08-25 panel analysis, and for the game lists the census's own
    raw-row measurement of zero space-bearing rows).
  - for the two multiword-capable sources (wordnet,
    wiktionary_english), the spaced derived sets ARE the census's
    re-ingest under the extended grammar (.cache/space_census/*.jsonl);
    their counts are read from space_census.json and re-asserted
    against the shipped universe_v2 counts by the test suite.

The four game-list derived sets are read READ-ONLY from the EOL cache,
verified against the same pins research/audit/run_audit.py records;
only counts are recorded here — no restricted word appears in any
output (C-009 licence rule).

Run:  python -m research.universe_v2.measure_spaced_applicability
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.archival import REFERENCE

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "universe_v2" / "spaced_applicability.json"
CEOL_DERIVED = REPO / ".cache" / "derived"
EOL_DERIVED = EOL_REPO / ".cache" / "sources" / "derived"
CENSUS_JSON = REFERENCE / "research" / "space_census" / "space_census.json"

#: EOL-side binary detector derived sets: the same pins
#: research/audit/run_audit.py carries (derived_sha256, record_count).
EOL_BINARY = {
    "enable1": ("3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89", 172823),
    "sowpods_legacy": ("5a855b21aa2bef5b98be71c719668337b3ceeaa6cb1cc08efab2a8ff0759a38f", 267751),
    "nwl2023": ("79de4b07ed6f38ad1bdb1bf874e42383815b78730b23a0edce511f3ef043058e", 196601),
    "csw21": ("136332497985c48389f017064e7875ce49398ee10b5dc0fa4c701f7a5085985c", 279077),
}

#: The format/scope accounts behind each structural zero (C-010 pattern;
#: panel analysis of 2026-08-25, census licence check for the game lists).
ACCOUNTS = {
    "web2": "single-token historical list (the ASCII /usr/share/dict/words "
            "of 1934); entry grammar carries no space",
    "web2a": "hyphenated-compound list; every entry single-token at the "
             "entry grammar (hyphens, never spaces)",
    "hunspell_en_US": "dic entry grammar is single-token; space-bearing "
                      "lines are morphological annotation fields, parsed "
                      "off by the pinned ingest",
    "hunspell_en_GB": "dic entry grammar is single-token; space-bearing "
                      "lines are morphological annotation fields, parsed "
                      "off by the pinned ingest",
    "hunspell_en_CA": "dic entry grammar is single-token; space-bearing "
                      "lines are morphological annotation fields, parsed "
                      "off by the pinned ingest",
    "hunspell_en_AU": "dic entry grammar is single-token; space-bearing "
                      "lines are morphological annotation fields, parsed "
                      "off by the pinned ingest",
    "enable1": "competition lexicon over the A-Z tile alphabet; spaces "
               "unplayable — format, not judgement",
    "sowpods_legacy": "competition lexicon over the A-Z tile alphabet; "
                      "spaces unplayable — format, not judgement",
    "nwl2023": "competition lexicon over the A-Z tile alphabet; spaces "
               "unplayable; census raw-row measurement: 0 space-bearing "
               "rows in 196,601",
    "csw21": "competition lexicon over the A-Z tile alphabet; spaces "
             "unplayable; census raw-row measurement: 0 space-bearing "
             "rows in 279,077",
    "scowl": "ordinal tier covariate, never a binary detector (C-010); "
             "all 360 final lists space-free (panel measurement "
             "2026-08-25)",
}


def _scan(path: Path) -> tuple[int, int]:
    lines = spaced = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            lines += 1
            if " " in line.rstrip("\n"):
                spaced += 1
    return lines, spaced


def measure() -> dict:
    census = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))["doc_figures"]
    detectors: dict[str, dict] = {}

    # CEOL-side detectors: exceptions split pinned by derived_sha256,
    # plain split pinned by plain_sha256 where the meta records one.
    ceol_names = ("wiktionary_english", "wordnet", "web2", "web2a",
                  "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
                  "hunspell_en_AU", "scowl")
    for name in ceol_names:
        meta = json.loads(
            (CEOL_DERIVED / f"{name}.meta.json").read_text(encoding="utf-8"))
        files = []
        for suffix, pin_key in (("", "derived_sha256"), ("_plain", "plain_sha256")):
            p = CEOL_DERIVED / f"{name}{suffix}.txt"
            if not p.exists():
                continue
            got = sha256_file(p)
            pin = meta.get(pin_key)
            if pin is not None and got != pin:
                raise SystemExit(f"{p.name}: sha256 {got} != pinned {pin}")
            lines, spaced = _scan(p)
            files.append({"file": p.name, "sha256": got,
                          "pin_verified": pin is not None,
                          "lines": lines, "spaced_lines": spaced})
        detectors[name] = {"splits": files,
                           "spaced_in_c4_derived": sum(
                               f["spaced_lines"] for f in files)}

    # EOL-side game-list detectors, read-only, pin-verified.
    for name, (pin, count) in EOL_BINARY.items():
        if name == "wordnet":
            continue
        p = EOL_DERIVED / f"{name}.txt"
        got = sha256_file(p)
        if got != pin:
            raise SystemExit(f"{p}: sha256 {got} != pinned {pin}")
        lines, spaced = _scan(p)
        if lines != count:
            raise SystemExit(f"{p}: {lines:,} lines != pinned {count:,}")
        detectors[name] = {"splits": [{"file": str(p.name), "sha256": got,
                                       "pin_verified": True, "lines": lines,
                                       "spaced_lines": spaced}],
                           "spaced_in_c4_derived": spaced}

    # Applicability ruling per C-010's rule, from the measurements.
    for name, rec in detectors.items():
        if name in ("wordnet", "wiktionary_english"):
            rec["spaced_count"] = (census["wn_spaced"] if name == "wordnet"
                                   else census["wk_spaced"])
            rec["applicable"] = True
            rec["account"] = ("multiword-capable; spaced derived set is "
                              "the census re-ingest under the extended "
                              "grammar (.cache/space_census/)")
        else:
            if rec["spaced_in_c4_derived"] != 0:
                raise SystemExit(f"{name}: unexpected spaced entries in a "
                                 "single-token-only derived set")
            rec["spaced_count"] = 0
            rec["applicable"] = False
            rec["account"] = ACCOUNTS[name]

    applicable = sorted(n for n, r in detectors.items() if r["applicable"])
    na = sorted(n for n, r in detectors.items() if not r["applicable"])
    out = {
        "generated_by":
            "research/universe_v2/measure_spaced_applicability.py",
        "rule": "C-010: detector x spaced is NA iff the derived output "
                "carries zero spaced entries and a format/scope account "
                "is recorded; any non-zero cell is applicable",
        "detectors": detectors,
        "applicable": applicable,
        "not_applicable": na,
        "doc_figures": {
            "spaced_applicable_detectors": len(applicable),
            "spaced_na_detectors": len(na),
            "wordnet_spaced": detectors["wordnet"]["spaced_count"],
            "wiktionary_spaced":
                detectors["wiktionary_english"]["spaced_count"],
        },
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return out


def main() -> int:
    out = measure()
    print(f"[applicability] applicable on spaced: "
          f"{', '.join(out['applicable'])}")
    print(f"[applicability] structural NA ({len(out['not_applicable'])}): "
          f"{', '.join(out['not_applicable'])}")
    print(f"[applicability] wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
