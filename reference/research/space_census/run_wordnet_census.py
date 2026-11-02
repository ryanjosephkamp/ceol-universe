"""
S3 space census, source 1 of 2: WordNet 3.0 under the extended grammar.

Traverses every synset of the pinned zip (the same nltk corpus the C4
ingest read; artifact sha256 asserted), decodes WordNet's documented
space encoding — the underscore — at this parse layer only, and runs
every lemma through the extended CEOL grammar.

Sanity anchor (AGENDA S3): the spaceless projection of this traversal
must reproduce the C4-era derived sets byte-for-byte — wordnet_plain
(77,503 entries, sha 266b875d…) and the exception split (5,229 entries,
sha 801b2823…). The anchor is asserted here, not merely reported: a
mismatch aborts the census.

Outputs:
  .cache/space_census/wordnet_spaced.jsonl   per-candidate records
  research/space_census/wordnet_census.json  aggregates (committed)

Per-candidate properness signals (AGENDA S3): instance-synset membership
(instance hypernym pointers in the data files) and data-file
capitalization (any occurrence whose cased lemma name differs from its
lowercase). The index lowercases lemmas, so case must come from the data
files — nltk lemma names preserve it.

Run:  python -m research.space_census.run_wordnet_census
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from ceol.grammar import SPACE, classes, normalize, token_count

REPO = Path(__file__).resolve().parents[2]
CACHE_OUT = REPO / ".cache" / "space_census"
OUT_JSON = REPO / "research" / "space_census" / "wordnet_census.json"

WN_ZIP = Path.home() / "nltk_data" / "corpora" / "wordnet.zip"
WN_SHA256 = "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"

#: C4-era anchors (.cache/derived/wordnet*.txt, built 2026-08-20).
ANCHOR_PLAIN_SHA = "266b875d86cb132cb924490626140e8c104b7170db5c5e14d2e117fd3a32bed2"
ANCHOR_PLAIN_COUNT = 77_503
ANCHOR_EXC_SHA = "801b28237a7138d2e135cad82d904d63bc7d78997527301acb4ebbb2e6a351eb"
ANCHOR_EXC_COUNT = 5_229


def _sha256_lines(words: list[str]) -> str:
    h = hashlib.sha256()
    for w in words:
        h.update(w.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _diagnose(decoded: str) -> str:
    """Why a decoded multiword lemma failed the extended grammar."""
    if any(c.isdigit() for c in decoded):
        return "digit"
    if "." in decoded:
        return "period"
    if any(t.endswith("'") for t in decoded.split(SPACE) if t):
        return "token_trailing_apostrophe"
    return "other"


def main() -> None:
    import zipfile

    got = hashlib.sha256(WN_ZIP.read_bytes()).hexdigest()
    if got != WN_SHA256:
        raise SystemExit(f"wordnet.zip sha256 {got} != pin {WN_SHA256}")
    with zipfile.ZipFile(WN_ZIP):
        pass                      # zip readable; nltk reads the same bytes

    from nltk.corpus import wordnet as wn
    assert wn.get_version() == "3.0"

    entries_seen = 0
    plain: set[str] = set()
    exceptions: set[str] = set()          # spaceless exception classes
    spaced: dict[str, dict] = {}          # key -> record
    reject_reasons: Counter[str] = Counter()
    reject_examples: dict[str, list[str]] = {}

    for syn in wn.all_synsets():
        pos = syn.pos()
        is_instance = bool(syn.instance_hypernyms())
        for lemma in syn.lemmas():
            entries_seen += 1
            raw = lemma.name()
            decoded = raw.replace("_", " ")   # WordNet's documented encoding
            key = normalize(decoded)
            if key is None:
                if "_" in raw:                # multiword reject
                    reason = _diagnose(decoded.lower())
                    reject_reasons[reason] += 1
                    ex = reject_examples.setdefault(reason, [])
                    if len(ex) < 10 and decoded not in ex:
                        ex.append(decoded)
                continue
            if SPACE not in key:
                (plain if not classes(key) else exceptions).add(key)
                continue
            rec = spaced.get(key)
            if rec is None:
                rec = spaced[key] = {
                    "key": key,
                    "token_count": token_count(key),
                    "classes": sorted(classes(key)),
                    "pos": set(),
                    "instance": False,
                    "capitalized": False,
                    "synsets": 0,
                }
            rec["pos"].add(pos)
            rec["synsets"] += 1
            if is_instance:
                rec["instance"] = True
            if raw != raw.lower():
                rec["capitalized"] = True

    # --- the anchor: spaceless projection reproduces C4 byte-for-byte ----
    plain_sorted = sorted(plain)
    exc_sorted = sorted(exceptions)
    plain_sha = _sha256_lines(plain_sorted)
    exc_sha = _sha256_lines(exc_sorted)
    if (len(plain_sorted), plain_sha) != (ANCHOR_PLAIN_COUNT,
                                          ANCHOR_PLAIN_SHA):
        raise SystemExit(f"ANCHOR FAILED: plain {len(plain_sorted):,} "
                         f"{plain_sha} != {ANCHOR_PLAIN_COUNT:,} "
                         f"{ANCHOR_PLAIN_SHA}")
    if (len(exc_sorted), exc_sha) != (ANCHOR_EXC_COUNT, ANCHOR_EXC_SHA):
        raise SystemExit(f"ANCHOR FAILED: exceptions {len(exc_sorted):,} "
                         f"{exc_sha} != {ANCHOR_EXC_COUNT:,} "
                         f"{ANCHOR_EXC_SHA}")

    # --- per-candidate records, sorted, deterministic --------------------
    CACHE_OUT.mkdir(parents=True, exist_ok=True)
    jsonl = CACHE_OUT / "wordnet_spaced.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for key in sorted(spaced):
            rec = dict(spaced[key])
            rec["pos"] = sorted(rec["pos"])
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)
                    + "\n")

    # --- aggregates ------------------------------------------------------
    tokc = Counter(r["token_count"] for r in spaced.values())
    lenc = Counter(len(k) for k in spaced)
    posc = Counter()
    for r in spaced.values():
        for p in r["pos"]:
            posc[p] += 1
    classc = Counter()
    for r in spaced.values():
        for c in r["classes"]:
            classc[c] += 1
    n_instance = sum(1 for r in spaced.values() if r["instance"])
    n_capitalized = sum(1 for r in spaced.values() if r["capitalized"])

    agg = {
        "generated_by": "research/space_census/run_wordnet_census.py",
        "inputs": {"wordnet_zip_sha256": WN_SHA256},
        "anchor": {
            "plain_count": len(plain_sorted), "plain_sha256": plain_sha,
            "exception_count": len(exc_sorted), "exception_sha256": exc_sha,
            "status": "reproduced",
        },
        "entries_seen": entries_seen,
        "spaced_candidates": len(spaced),
        "token_count_distribution":
            {str(k): v for k, v in sorted(tokc.items())},
        "char_length": {
            "min": min(lenc), "max": max(lenc),
            "distribution_by_decile": {},
        },
        "pos_counts": dict(sorted(posc.items())),
        "class_counts": dict(sorted(classc.items())),
        "properness": {
            "instance_synset_members": n_instance,
            "capitalized_in_data": n_capitalized,
            "both": sum(1 for r in spaced.values()
                        if r["instance"] and r["capitalized"]),
        },
        "multiword_rejects": {
            "total": sum(reject_reasons.values()),
            "by_reason": dict(sorted(reject_reasons.items())),
            "examples": reject_examples,
        },
        "spaced_jsonl_sha256": hashlib.sha256(
            jsonl.read_bytes()).hexdigest(),
    }
    lengths = sorted(len(k) for k in spaced)
    agg["char_length"]["distribution_by_decile"] = {
        f"p{q}": lengths[min(len(lengths) - 1, len(lengths) * q // 100)]
        for q in (10, 25, 50, 75, 90, 99)
    }

    OUT_JSON.write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"anchor reproduced: plain {len(plain_sorted):,} / "
          f"exceptions {len(exc_sorted):,}")
    print(f"spaced candidates: {len(spaced):,} "
          f"(rejected multiword: {sum(reject_reasons.values()):,})")
    print(f"wrote {jsonl} and {OUT_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    main()
