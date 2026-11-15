"""
The C1 exceptions census: orchestration and assembly.

Stages (idempotent; a source with a derived file and meta is not re-run):

  python -m research.census.run_census --fast      # everything but the dump
  python -m ceol.ingest.wiktionary_english         # the 1.62 GB stream
  python -m research.census.run_census --assemble  # census.json + candidates

Everything this produces is a CANDIDATE inventory. No word is called valid,
no threshold is chosen, nothing is published anywhere (the project's rules).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from ceol.grammar import CENSUS_CLASSES, classes, normalize
from ceol.ingest import census_sources
from ceol.ingest.common import DERIVED_DIR, EOL_REPO, read_derived, sha256_file

REPO = Path(__file__).resolve().parents[2]
CENSUS_DIR = REPO / "research" / "census"
SEEDS_CSV = REPO / "corrections" / "seeds_from_eol_ledger.csv"

#: The EOL's pinned valid list (manifest sha256_valid at revision c1139698…)
#: — read-only, hash-verified before every read.
EOL_VALID = EOL_REPO / ".cache" / "hf" / "merged_valid_words.txt"
EOL_VALID_SHA = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
EOL_LEDGER = EOL_REPO / "corrections" / "ledger_form_rules.csv"

FAST_SOURCES = ("web2", "web2a", "wordfreq", "scowl", "hunspell_en_US",
                "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU",
                "wiktionary_titles")
ALL_SOURCES = FAST_SOURCES + ("wiktionary_english",)

#: The all-languages title index is a SCREEN (some language uses the
#: spelling), not an English detector; it is censused for context but kept
#: out of the deduplicated exceptions inventory.
INVENTORY_SOURCES = tuple(s for s in ALL_SOURCES if s != "wiktionary_titles")


def _ingest(source: str) -> dict:
    fn = {
        "web2": census_sources.ingest_web2,
        "web2a": census_sources.ingest_web2a,
        "wordfreq": census_sources.ingest_wordfreq,
        "scowl": census_sources.ingest_scowl,
        "wiktionary_titles": census_sources.ingest_wiktionary_titles,
    }
    if source.startswith("hunspell_"):
        return census_sources.ingest_hunspell(source.removeprefix("hunspell_"))
    return fn[source]()


def run_fast(force: bool = False) -> None:
    for source in FAST_SOURCES:
        meta_path = DERIVED_DIR / f"{source}.meta.json"
        if meta_path.exists() and not force:
            print(f"[census] {source}: derived exists, skipping")
            continue
        print(f"[census] ingesting {source} …", flush=True)
        meta = _ingest(source)
        print(f"[census] {source}: {meta['exception_candidates']:,} "
              f"exception candidates from {meta['entries_seen']:,} entries")


# ---------------------------------------------------------------------------
# Seeds: the 190 D-025 deletions preserved in the EOL's form-rules ledger
# ---------------------------------------------------------------------------

def build_seeds() -> dict:
    """
    Every `delete_malformed` row of the EOL ledger is a seed candidate; the
    CEOL grammar rules on each. The 20 truncated fragments (self-, high-)
    are EXPECTED to fail — they were deleted as malformed and stay
    malformed here; the census records them as grammar-rejected seeds
    rather than silently dropping them.
    """
    rows = list(csv.DictReader(open(EOL_LEDGER, encoding="utf-8")))
    deletions = [r for r in rows if r["action"] == "delete_malformed"]
    out_rows = []
    accepted = rejected = 0
    for r in deletions:
        key = normalize(r["word"])
        if key is None:
            status, flags = "rejected_by_grammar", ""
            rejected += 1
        else:
            status, flags = "accepted", ";".join(sorted(classes(key)))
            accepted += 1
        out_rows.append({
            "word": r["word"], "normalized": key or "",
            "status": status, "classes": flags,
            "eol_category": r["category"], "eol_decided": r["decided_date"],
            "provenance": "english-openlist corrections/ledger_form_rules.csv"
                          " (D-025)"})
    SEEDS_CSV.parent.mkdir(exist_ok=True)
    with open(SEEDS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(sorted(out_rows, key=lambda r: r["word"]))
    return {"ledger_rows": len(rows), "deletions": len(deletions),
            "accepted": accepted, "rejected_by_grammar": rejected,
            "by_category": _count(r["eol_category"] for r in out_rows),
            "seeds_csv_sha256": sha256_file(SEEDS_CSV)}


def _count(items) -> dict:
    out: dict[str, int] = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Possessive sizing: candidate common-noun stems among the pinned valid list
# ---------------------------------------------------------------------------

def possessive_sizing() -> dict:
    got = sha256_file(EOL_VALID)
    if got != EOL_VALID_SHA:
        raise RuntimeError(f"EOL valid list sha256 {got} != pin; refusing")
    valid = {line.strip() for line in open(EOL_VALID, encoding="utf-8")
             if line.strip()}

    from nltk.corpus import wordnet as wn
    wn_nouns = set()
    for syn in wn.all_synsets(pos="n"):
        for lemma in syn.lemmas():
            key = normalize(lemma.name())
            if key is not None and not classes(key):      # plain [a-z]+ only
                wn_nouns.add(key)

    wikt_path = DERIVED_DIR / "wiktionary_english_nouns.txt"
    wikt_nouns = {line.strip() for line in open(wikt_path, encoding="utf-8")
                  if line.strip() and not classes(line.strip())}

    wn_stems = wn_nouns & valid
    wikt_stems = wikt_nouns & valid
    union = wn_stems | wikt_stems
    return {
        "valid_at_pin": len(valid),
        "wordnet_noun_lemmas_az": len(wn_nouns),
        "wiktionary_english_nouns_az": len(wikt_nouns),
        "stems_wordnet_x_valid": len(wn_stems),
        "stems_wiktionary_x_valid": len(wikt_stems),
        "stems_union": len(union),
        "note": "each stem generates one possessive candidate (stem+'s; "
                "s-final stems take bare ' under the proposed rule), so "
                "stems_union sizes the class",
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _examples(words: list[str], klass: str, n: int = 10) -> list[str]:
    """Deterministic sample: sha256 ranking, never a library RNG."""
    return sorted(
        words,
        key=lambda w: hashlib.sha256(
            f"census-examples:{klass}:{w}".encode()).hexdigest())[:n]


def assemble() -> None:
    metas = {}
    for source in ALL_SOURCES:
        meta_path = DERIVED_DIR / f"{source}.meta.json"
        if not meta_path.exists():
            raise RuntimeError(f"{source}: no derived meta; run its ingest")
        metas[source] = json.loads(meta_path.read_text(encoding="utf-8"))

    seeds = build_seeds()

    # The deduplicated inventory: word -> sources, over detector sources.
    inventory: dict[str, set[str]] = {}
    for source in INVENTORY_SOURCES:
        for w in read_derived(source):
            inventory.setdefault(w, set()).add(source)
    for row in csv.DictReader(open(SEEDS_CSV, encoding="utf-8")):
        if row["status"] == "accepted":
            inventory.setdefault(row["normalized"], set()).add(
                "eol_ledger_d025")

    by_class: dict[str, list[str]] = {k: [] for k in CENSUS_CLASSES}
    by_class["s-final"] = []
    for w in inventory:
        for k in classes(w):
            by_class[k].append(w)

    candidates_csv = CENSUS_DIR / "candidates.csv"
    with open(candidates_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "classes", "sources"])
        for word in sorted(inventory):
            w.writerow([word, ";".join(sorted(classes(word))),
                        ";".join(sorted(inventory[word]))])

    sizing = possessive_sizing()

    census = {
        "generated_by": "research/census/run_census.py --assemble",
        "grammar": "ceol/grammar.py (C-001)",
        "sources": {s: metas[s] for s in ALL_SOURCES},
        "seeds": seeds,
        "inventory": {
            "sources": list(INVENTORY_SOURCES) + ["eol_ledger_d025"],
            "total_candidates": len(inventory),
            "by_class": {k: len(v) for k, v in sorted(by_class.items())},
            "single_source": sum(1 for s in inventory.values() if len(s) == 1),
            "examples": {k: _examples(v, k) for k, v in sorted(by_class.items())
                         if v},
        },
        "possessive_sizing": sizing,
        "candidates_csv_sha256": sha256_file(candidates_csv),
    }
    census["doc_figures"] = {
        "total_candidates": census["inventory"]["total_candidates"],
        **{f"class_{k}": v
           for k, v in census["inventory"]["by_class"].items()},
        "seeds_accepted": seeds["accepted"],
        "seeds_rejected": seeds["rejected_by_grammar"],
        "stems_union": sizing["stems_union"],
        "stems_pct_of_valid": str(round(
            100 * sizing["stems_union"] / sizing["valid_at_pin"], 1)),
        "valid_at_pin": sizing["valid_at_pin"],
        "wikt_english_all": metas["wiktionary_english"]["english_entries_all"],
        # Determinism cross-checks: the EOL tripwires, reproduced from the
        # same bytes under the wider grammar.
        "wikt_plain_az": metas["wiktionary_english"]["plain_az"],
        "wikt_titles_plain_az": metas["wiktionary_titles"]["plain_az"],
        "web2_plain_az": metas["web2"]["plain_az"],
        "pages_scanned": metas["wiktionary_english"]["pages_scanned"],
        "single_source": census["inventory"]["single_source"],
        "single_source_pct": str(round(
            100 * census["inventory"]["single_source"]
            / census["inventory"]["total_candidates"], 1)),
        "wikt_hyphen_share_pct": str(round(
            100 * metas["wiktionary_english"]["classes"]["hyphenated"]
            / census["inventory"]["by_class"]["hyphenated"], 1)),
    }
    out = CENSUS_DIR / "census.json"
    out.write_text(json.dumps(census, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[census] assembled: {len(inventory):,} candidates -> {out}")
    for k, v in census["inventory"]["by_class"].items():
        print(f"  {k:16s} {v:,}")
    print(f"  possessive stems (union): {sizing['stems_union']:,}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.fast:
        run_fast(force=args.force)
    if args.assemble:
        assemble()
    return 0


if __name__ == "__main__":
    sys.exit(main())
