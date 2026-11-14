"""The card's rows that the site shows (site/): each one a row of the card's
calculator, research/release/public_card.py, written by name to
research/release/figures/<version>/card_rows.json so the site reads it at
build time. The calculator reads committed records only, so the file re-derives
in a fresh clone. No word is printed.

    python3 -m research.release.site_rows            write the file
    python3 -m research.release.site_rows --check    compare with it
"""

from __future__ import annotations

import argparse
import json
import sys

from research.release import build_release as B
from research.release import public_card as P

VERSION = P.VERSION
OUT = B.REPO / "research" / "release" / "figures" / VERSION / "card_rows.json"

#: the rows the site shows, in the order of the card's build section (§9),
#: then the projection's
ROWS: tuple[str, ...] = (
    "census_candidates", "eol_universe_rows", "merge_rows", "audit_remainder",
    "c4_additions", "v1_rows", "pin_spaced", "rows_pin",
    "model_basis_entries", "rows_restricted", "rows_shippable",
    "held_back_rows", "held_tier_2", "held_withheld_channel",
    "held_withheld_sources", "rows_universe", "files_asserted",
    "restricted_words_checked", "exception_class_count",
    "published_set_count", "withheld_list_count", "panel_set_count",
    "built_on", "code_commit", "contact_address", "generated_rows",
    "eol_one_letter", "eol_over_45", "eol_longest", "limit_gb_all", "wordfreq_scored",
    "rows_features")


def _value(text: str):
    """A row's value: an integer where the row is a count, else its text."""
    plain = text.replace(",", "")
    return int(plain) if plain.isdigit() else text


def compute() -> dict:
    rows = P.rows()
    missing = [name for name in ROWS if name not in rows]
    if missing:
        raise SystemExit(f"the card's calculator has no row {missing}")
    return {
        "version": VERSION,
        "generated_by": "research/release/site_rows.py",
        "source": "research/release/public_card.py",
        "what": "rows of the card's calculator that the site shows, by name",
        "rows": {name: {"value": _value(rows[name]), "text": rows[name]}
                 for name in ROWS},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="compare the committed file with a fresh one")
    args = ap.parse_args(argv)
    text = json.dumps(compute(), indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"[site] {OUT.relative_to(B.REPO)} does not re-derive",
                  file=sys.stderr)
            return 1
        print(f"[site] {OUT.relative_to(B.REPO)} re-derives")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"[site] {OUT.relative_to(B.REPO)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
