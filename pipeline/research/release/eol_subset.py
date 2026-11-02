"""The English OpenList's public dataset against its last published list
(D-014 line 1): counts only. The public dataset is the release's `eol-valid`
config, the rows with `eol == true` at the pinned revision c1139698; this
script counts how the English OpenList's last published list differs from
it, and why, and writes the counts to research/release/eol_subset_<version>.json.
No word is printed or written.

The last published list is `latest/merged_valid_words.txt` of the dataset
ryanjosephkamp/english-openlist at revision c707c187b2c3 (2026-09-24), kept
under data/eol/ beside the release's files.

    python3 -m research.release.eol_subset            write the record
    python3 -m research.release.eol_subset --check    compare with it
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

import pyarrow.compute as pc
import pyarrow.parquet as pq

from research.release import build_release as B
from research.release import public_card as P
from safeguards import locations

VERSION = P.VERSION
OUT = B.REPO / "research" / "release" / f"eol_subset_{VERSION}.json"
HUB_REVISION = "c707c187b2c3"
LIST_FILE = f"eol/merged_valid_words_{HUB_REVISION}.txt"


def _words(table, column: str = "word") -> set[str]:
    return set(table[column].to_pylist())


def compute() -> dict:
    data = locations.data_dir()
    raw = (data / LIST_FILE).read_bytes()
    lines = [l.strip() for l in raw.decode("utf-8").splitlines()]
    listed = {l for l in lines if l and not l.startswith("#")}
    pin = pq.read_table(data / "universe_v2.parquet", columns=["word", "eol", "is_restricted"])
    pin_eol = _words(pin.filter(pc.equal(pin["eol"], True)))
    restricted = _words(pin.filter(pc.equal(pin["is_restricted"], True)))
    rel = data / "release" / f"ceol-universe-{VERSION}"
    subset = _words(pq.read_table(rel / "eol-valid.parquet", columns=["word"]))
    universe = _words(pq.read_table(rel / "universe.parquet", columns=["word"]))
    at_pin_out = pin_eol - subset
    added = listed - pin_eol
    counts = {
        "last_list": len(listed),
        "list_at_pin": len(pin_eol),
        "public_dataset": len(subset),
        "list_at_pin_not_public": len(at_pin_out),
        "of_which_restricted": len(at_pin_out & restricted),
        "of_which_held_back": len(at_pin_out - restricted - universe),
        "added_after_pin": len(added),
        "added_after_pin_in_universe": len(added & universe),
        "removed_after_pin": len(pin_eol - listed),
        "public_dataset_not_on_last_list": len(subset - listed),
        "last_list_less_held_back": len(listed & universe),
    }
    # the counts must account for each other, or the record is not written
    if not (counts["list_at_pin"] - counts["removed_after_pin"] + counts["added_after_pin"] == counts["last_list"]
            and counts["public_dataset"] + counts["list_at_pin_not_public"] == counts["list_at_pin"]
            and counts["of_which_restricted"] + counts["of_which_held_back"] == counts["list_at_pin_not_public"]
            and not subset - pin_eol):
        raise SystemExit("[eol] the counts do not account for each other")
    return {
        "version": VERSION,
        "generated_by": "research/release/eol_subset.py",
        "what": "the English OpenList's last published list against the release's eol-valid config, counts only",
        "last_list": {
            "dataset": "ryanjosephkamp/english-openlist",
            "path": "latest/merged_valid_words.txt",
            "revision": HUB_REVISION,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "pin_revision": "c1139698",
        "counts": counts,
        # the lengths tournament lists exclude, which the public dataset holds
        "lengths": {
            "one_letter": sum(1 for w in subset if len(w) == 1),
            "over_45": sum(1 for w in subset if len(w) > 45),
            "longest": max(len(w) for w in subset),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare the committed record with a fresh one")
    args = ap.parse_args(argv)
    text = json.dumps(compute(), indent=1) + "\n"
    rel = OUT.relative_to(B.REPO)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"[eol] {rel} does not re-derive", file=sys.stderr)
            return 1
        print(f"[eol] {rel} re-derives")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"[eol] {rel} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
