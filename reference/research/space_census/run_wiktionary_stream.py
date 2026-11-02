"""
S3 space census, source 2 of 2: the Wiktionary pages-articles stream.

A superset of the C4 parser (ceol/ingest/wiktionary_english.py): the same
title handling (NFC, the D-031 already-lowercase convention, then the
extended grammar), the same English-section state machine with the
hard-won ``(?:^|>)`` heading prefix — plus, for spaced English entries,
capture of every level-3/4 heading inside the English section and every
literally-written English category link. The pages-articles XML carries
titles with real spaces (the underscore encoding belongs to the
all-titles file alone), so no decode is needed here.

Sanity anchors (AGENDA S3), asserted before anything is written: the
spaceless projections of this stream reproduce the C4-era derived sets
byte-for-byte —
  english_all  831,973 entries, sha 26dbb270…
  exceptions    56,104 entries, sha 990d56a5…
  nouns        542,035 entries, sha 53a1cd7a…

New measurements, spaced entries only:
  - per-entry POS headings and literal English categories (template-
    generated categories are not visible to a text stream and are out of
    scope, stated in the report);
  - the J1 reject taxonomy: lowercase spaced-shaped titles with an
    English section that the extended grammar rejects, by reason;
  - U+00A0-fold gains: titles admitted only because of the C-015 fold.

Outputs:
  .cache/space_census/wiktionary_spaced.jsonl       per-entry records
  .cache/space_census/wiktionary_spaced_rejects.json reject profile
  research/space_census/wiktionary_census.json      aggregates (committed)

The dump (1.62 GB bz2, sha asserted against the C4 pin a0db4eea…) is
streamed once and deleted, the manifest pattern making it re-fetchable.
Progress prints every 500k pages; the pass is restartable from scratch
(all outputs are written atomically at the end).

Run:  python -m research.space_census.run_wiktionary_stream
"""

from __future__ import annotations

import bz2
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

from ceol.grammar import SPACE, classes, normalize, token_count

REPO = Path(__file__).resolve().parents[2]
DUMP = REPO / ".cache" / "raw" / "enwiktionary-20260804-pages-articles.xml.bz2"
DUMP_SHA = "a0db4eeaea5e6b9940e21ea143eaecf93195610888d345333ae560b9a15527d1"
CACHE_OUT = REPO / ".cache" / "space_census"
OUT_JSON = REPO / "research" / "space_census" / "wiktionary_census.json"

#: C4-era anchors (.cache/derived/wiktionary_english*.txt, built 2026-08-20).
ANCHORS = {
    "english_all": ("26dbb2708e4a961bb9d40224b3cd24ae818e334a1b99e7ab357b4fb7ccaea211", 831_973),
    "exceptions": ("990d56a5fe4ebdca810061f37c946602396228749bac681b17e3a860080f5685", 56_104),
    "nouns": ("53a1cd7a97f55ab086ffbcf377c5cbefb82a218e91694c591ee80ee7ecce75d6", 542_035),
}
ANCHOR_PAGES = 10_780_017

TITLE = re.compile(r"<title>([^<]*)</title>")
ENGLISH = re.compile(r"(?:^|>)==\s*English\s*==\s*$")
LANG_L2 = re.compile(r"(?:^|>)==[^=]")          # any level-2 heading
NOUN = re.compile(r"(?:^|>)={3,4}\s*Noun\s*={3,4}\s*$")
HEADING34 = re.compile(r"(?:^|>)={3,4}\s*([^=\n]+?)\s*={3,4}\s*$")
CATEGORY = re.compile(
    r"\[\[\s*[Cc]ategory\s*:\s*(English [^\]|]+|en:[^\]|]+?)\s*(?:\|[^\]]*)?\]\]")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_lines(words: list[str]) -> str:
    h = hashlib.sha256()
    for w in words:
        h.update(w.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def diagnose_spaced_reject(t: str) -> str:
    """Why a lowercase spaced-shaped title failed the extended grammar.
    Ordered so each title lands in exactly one bucket."""
    if any(c.isdigit() for c in t):
        return "digit"
    if "." in t:
        return "period"
    if "," in t:
        return "comma"
    if any(c in "()[]{}" for c in t):
        return "bracket"
    if "  " in t or t.startswith(" ") or t.endswith(" "):
        return "space_structure"
    toks = [x for x in t.split(" ") if x]
    if any(x.endswith("'") for x in toks):
        return "token_trailing_apostrophe"
    if any(x.startswith("-") or x.endswith("-") for x in toks):
        return "token_edge_hyphen"
    if any(unicodedata.category(c).startswith("L") and normalize(c) is None
           for c in t):
        return "undeclared_letter"
    return "other"


def main() -> int:
    if not DUMP.exists():
        print(f"[space-census] {DUMP} not present; download it first "
              f"(pin {DUMP_SHA})", flush=True)
        return 1
    sha = sha256_file(DUMP)
    if sha != DUMP_SHA:
        print(f"[space-census] sha256 {sha} != pin {DUMP_SHA}; refusing — "
              "the byte-pinned path is gone, take the drift path instead",
              flush=True)
        return 1
    print(f"[space-census] artifact sha256 verified: {sha}", flush=True)

    english: set[str] = set()
    nouns: set[str] = set()
    spaced_meta: dict[str, dict] = {}
    reject_counts: Counter[str] = Counter()
    reject_examples: dict[str, list[str]] = {}
    keys_via_nbsp: set[str] = set()     # spaced English keys from NBSP titles
    keys_via_plain: set[str] = set()    # same keys from plain-space titles
    pages = 0

    cur_key: str | None = None
    cur_spaced = False
    cur_nbsp = False
    cur_reject: str | None = None       # lowercase spaced-shaped, rejected
    cur_reject_counted = False
    in_english = False
    t0 = time.time()

    with bz2.open(DUMP, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "<title>" in line:
                pages += 1
                if pages % 500_000 == 0:
                    print(f"[space-census] {pages:,} pages, "
                          f"{len(english):,} English "
                          f"({len(spaced_meta):,} spaced), "
                          f"{time.time()-t0:,.0f}s", flush=True)
                cur_key = None
                cur_spaced = False
                cur_nbsp = False
                cur_reject = None
                cur_reject_counted = False
                in_english = False
                m = TITLE.search(line)
                if m:
                    t = unicodedata.normalize("NFC", m.group(1))
                    if t == t.lower():          # case-sensitive convention
                        cur_key = normalize(t)
                        if cur_key is not None:
                            cur_spaced = SPACE in cur_key
                            cur_nbsp = cur_spaced and "\u00a0" in t
                        elif " " in t or "\u00a0" in t:
                            cur_reject = t
            elif "==" in line and (cur_key is not None
                                   or cur_reject is not None):
                stripped = line.rstrip("\n")
                is_english = ("English" in stripped
                              and ENGLISH.search(stripped) is not None)
                if is_english:
                    in_english = True
                    if cur_key is not None and cur_key not in english:
                        english.add(cur_key)
                        if cur_spaced:
                            spaced_meta[cur_key] = {
                                "pos": set(), "cats": set(), "pages": 0,
                                "phrasebook": False, "idiomatic": False}
                    if cur_spaced:
                        spaced_meta[cur_key]["pages"] += 1
                        (keys_via_nbsp if cur_nbsp
                         else keys_via_plain).add(cur_key)
                    if cur_reject is not None and not cur_reject_counted:
                        reason = diagnose_spaced_reject(cur_reject)
                        reject_counts[reason] += 1
                        ex = reject_examples.setdefault(reason, [])
                        if len(ex) < 15 and cur_reject not in ex:
                            ex.append(cur_reject)
                        cur_reject_counted = True
                elif in_english:
                    if cur_spaced:
                        hm = HEADING34.search(stripped)
                        if hm:
                            spaced_meta[cur_key]["pos"].add(
                                hm.group(1).strip())
                    if cur_key is not None and NOUN.search(stripped):
                        nouns.add(cur_key)
                    if LANG_L2.search(stripped) \
                            and not ENGLISH.search(stripped):
                        in_english = False
                        continue
            if cur_spaced:
                # capture only once the key is English-attested: category
                # links on pages without an English section (e.g.
                # Translingual-only pages) stay out, and the English-prefix
                # constraint in CATEGORY makes pre-heading occurrences of
                # English categories a non-class in practice
                meta = spaced_meta.get(cur_key)
                if meta is not None:
                    if "ategory" in line:
                        for cm in CATEGORY.finditer(line):
                            meta["cats"].add(cm.group(1).strip())
                    # template-generated categories are invisible to a text
                    # stream, so the phrasebook and idiomatic labels are
                    # captured as substring flags over the English section
                    # (the {{phrasebook}} and {{lb|en|idiomatic}} templates
                    # and their category spellings all contain them);
                    # approximate by construction, stated in the report
                    if in_english:
                        if not meta["phrasebook"] and "phrasebook" in line:
                            meta["phrasebook"] = True
                        if not meta["idiomatic"] and "idiomatic" in line:
                            meta["idiomatic"] = True

    if pages != ANCHOR_PAGES:
        raise SystemExit(f"ANCHOR FAILED: {pages:,} pages scanned != "
                         f"{ANCHOR_PAGES:,} (C4)")

    # --- anchors: spaceless projections reproduce C4 byte-for-byte ------
    projections = {
        "english_all": sorted(w for w in english if SPACE not in w),
        "exceptions": sorted(w for w in english
                             if SPACE not in w and classes(w)),
        "nouns": sorted(w for w in nouns if SPACE not in w),
    }
    for name, (want_sha, want_count) in ANCHORS.items():
        got = projections[name]
        got_sha = _sha256_lines(got)
        if (len(got), got_sha) != (want_count, want_sha):
            raise SystemExit(f"ANCHOR FAILED: {name} {len(got):,} "
                             f"{got_sha} != {want_count:,} {want_sha}")
    print("[space-census] anchors reproduced: english_all / exceptions / "
          "nouns", flush=True)

    # --- outputs, atomic -------------------------------------------------
    CACHE_OUT.mkdir(parents=True, exist_ok=True)
    jsonl = CACHE_OUT / "wiktionary_spaced.jsonl"
    tmp = jsonl.with_suffix(".part")
    with open(tmp, "w", encoding="utf-8") as f:
        for key in sorted(spaced_meta):
            m = spaced_meta[key]
            f.write(json.dumps({
                "key": key,
                "token_count": token_count(key),
                "classes": sorted(classes(key)),
                "pos": sorted(m["pos"]),
                "cats": sorted(m["cats"]),
                "noun": key in nouns,
                "pages": m["pages"],
                "phrasebook": m["phrasebook"],
                "idiomatic": m["idiomatic"],
            }, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.rename(jsonl)

    rejects = {
        "definition": "lowercase spaced-shaped titles carrying an English "
                      "section, rejected by the extended grammar",
        "total": sum(reject_counts.values()),
        "by_reason": dict(sorted(reject_counts.items())),
        "examples": reject_examples,
        "nbsp_fold": {
            "definition": "spaced English keys whose every attesting title "
                          "carried U+00A0 — the entries the C-015 fold "
                          "alone admits",
            "keys_via_nbsp_titles": len(keys_via_nbsp),
            "keys_only_via_nbsp": len(keys_via_nbsp - keys_via_plain),
            "examples": sorted(keys_via_nbsp - keys_via_plain)[:50],
        },
    }
    (CACHE_OUT / "wiktionary_spaced_rejects.json").write_text(
        json.dumps(rejects, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n", encoding="utf-8")

    tokc = Counter(k.count(SPACE) + 1 for k in spaced_meta)
    agg = {
        "generated_by":
            "research/space_census/run_wiktionary_stream.py",
        "inputs": {"pages_articles_sha256": sha, "pages": pages},
        "anchor": {name: {"count": len(projections[name]),
                          "sha256": _sha256_lines(projections[name]),
                          "status": "reproduced"}
                   for name in ANCHORS},
        "english_entries_all": len(english),
        "spaced_entries": len(spaced_meta),
        "spaced_nouns": sum(1 for k in spaced_meta if k in nouns),
        "spaced_phrasebook": sum(
            1 for m in spaced_meta.values() if m["phrasebook"]),
        "spaced_idiomatic": sum(
            1 for m in spaced_meta.values() if m["idiomatic"]),
        "token_count_distribution":
            {str(k): v for k, v in sorted(tokc.items())},
        "spaced_rejects_total": sum(reject_counts.values()),
        "spaced_rejects_by_reason": dict(sorted(reject_counts.items())),
        "spaced_jsonl_sha256": sha256_file(jsonl),
    }
    OUT_JSON.write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    print(f"[space-census] DONE: {len(english):,} English entries, "
          f"{len(spaced_meta):,} spaced, "
          f"{sum(reject_counts.values()):,} spaced-shaped rejects, "
          f"{pages:,} pages in {time.time()-t0:,.0f}s", flush=True)

    DUMP.unlink()                 # 1.62 GB; the pin makes it re-fetchable
    print("[space-census] dump deleted", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
