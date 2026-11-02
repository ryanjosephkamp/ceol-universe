"""
The C-015 measured basis, re-derived from pinned bytes.

Produces research/space_census/c015_basis.json, the doc_figures source for
the C-015 entry in research/DECISIONS.md (checked by
research/verify_doc_numbers.py). Reads two pinned artifacts, both
hash-asserted before any counting:

  - ~/nltk_data/corpora/wordnet.zip — the WordNet 3.0 zip the EOL manifest
    pins (sha256 cbda5ea6…); its four index.* files carry the lemma
    inventory. Multiword lemmas appear with "_" separating tokens.
  - the English OpenList's cached all-titles.gz — the
    pinned enwiktionary all-titles-in-ns0 artifact (sha256 468b58bc…,
    pinned in the EOL manifest and research/census/census.json). Line 1 is
    the column header ``page_title``; it is not a title. The 2026-08-25
    pre-session measurement counted it (it is underscore-bearing and
    lowercase-ASCII-shaped, so it landed in every subset), which is why the
    four title figures here sit exactly one below that session's values —
    the correction is recorded in C-015's header line.

Both files are read, never written. Counting rules:

  - WordNet: every non-header line of index.{noun,verb,adj,adv} is one
    word-POS pair; the lemma is the first space-delimited field; a lemma is
    multiword iff it contains "_"; token count = underscores + 1.
  - Titles: a title is spaced iff it contains "_"; lowercase-ASCII-shaped
    iff every token matches [a-z']+ (the shape screen used 2026-08-25 —
    an upper bound on English candidates, not an English attribution).

Run:  python -m research.space_census.derive_c015_basis
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "space_census" / "c015_basis.json"

EOL_REPO = Path(os.environ.get("CEOL_EOL_REPO", ".inputs/english-openlist"))
WN_ZIP = Path(os.environ.get("CEOL_NLTK_WORDNET", ".inputs/nltk_data/corpora/wordnet.zip"))
WN_SHA256 = "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"
TITLES_GZ = EOL_REPO / ".cache" / "wiktionary" / "all-titles.gz"
TITLES_SHA256 = "468b58bc03f0d8e69b7df0c90c2ac3841be288acd5afe3b052939d70e44d633c"

#: The C-009 universe pin; the delta-range percentages re-derive against it.
UNIVERSE_PIN = 10_001_741

WN_PROBES = (
    "ad_hominem", "ad_hoc", "ice_cream", "of_course", "per_se", "de_facto",
    "faux_pas", "in_toto", "carte_blanche", "habeas_corpus",
    "kick_the_bucket", "give_up",
)
TITLE_PROBES = (
    "ad_hominem", "statistically_significant", "statistical_significance",
    "kick_the_bucket", "give_up",
    "a_bird_in_the_hand_is_worth_two_in_the_bush",
)
ASCII_SPACED = re.compile(r"[a-z']+(?:_[a-z']+)+")


def _assert_pin(path: Path, want: str) -> None:
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"{path}: sha256 {got} != pinned {want}")


def wordnet_figures() -> dict:
    _assert_pin(WN_ZIP, WN_SHA256)
    pairs = 0
    lemmas: set[str] = set()
    with zipfile.ZipFile(WN_ZIP) as zf:
        for pos in ("noun", "verb", "adj", "adv"):
            with zf.open(f"wordnet/index.{pos}") as f:
                for line in io.TextIOWrapper(f, encoding="utf-8"):
                    if line.startswith("  "):        # licence header block
                        continue
                    pairs += 1
                    lemmas.add(line.split(" ", 1)[0])
    multi = {l for l in lemmas if "_" in l}
    tokens = Counter(l.count("_") + 1 for l in multi)
    return {
        "word_pos_pairs": pairs,
        "unique_lemmas": len(lemmas),
        "multiword": len(multi),
        "multiword_pct": round(100 * len(multi) / len(lemmas), 1),
        "token_counts": {str(k): v for k, v in sorted(tokens.items())},
        "probes_present": {p: p in lemmas for p in WN_PROBES},
        "statistical_significance_absent":
            "statistical_significance" not in lemmas,
    }


def titles_figures() -> dict:
    _assert_pin(TITLES_GZ, TITLES_SHA256)
    titles = spaced = ascii_shaped = two_token = 0
    probes = {p: False for p in TITLE_PROBES}
    with gzip.open(TITLES_GZ, "rt", encoding="utf-8") as f:
        header = next(f).rstrip("\n")
        if header != "page_title":
            raise SystemExit(f"unexpected header line: {header!r}")
        for line in f:
            titles += 1
            t = line.rstrip("\n")
            if "_" not in t:
                continue
            spaced += 1
            if ASCII_SPACED.fullmatch(t):
                ascii_shaped += 1
                if t.count("_") == 1:
                    two_token += 1
            if t in probes:
                probes[t] = True
    return {
        "titles": titles,
        "spaced": spaced,
        "ascii_lower_shaped": ascii_shaped,
        "ascii_lower_two_token": two_token,
        "probes_present": probes,
    }


def main() -> None:
    wn = wordnet_figures()
    wk = titles_figures()
    basis = {
        "inputs": {
            "wordnet_zip_sha256": WN_SHA256,
            "all_titles_gz_sha256": TITLES_SHA256,
            "universe_pin": UNIVERSE_PIN,
        },
        "wordnet": wn,
        "wiktionary_titles": wk,
        "doc_figures": {
            "manifest_sources": 15,
            "multiword_capable_sources": 2,
            "wn_unique_lemmas": wn["unique_lemmas"],
            "wn_multiword": wn["multiword"],
            "wn_multiword_pct": wn["multiword_pct"],
            "wn_two_token": wn["token_counts"]["2"],
            "wk_titles": wk["titles"],
            "wk_spaced": wk["spaced"],
            "wk_ascii_lower_shaped": wk["ascii_lower_shaped"],
            "delta_low_m": 0.25,
            "delta_high_m": 0.7,
            "delta_low_pct": round(100 * 0.25e6 / UNIVERSE_PIN, 1),
            "delta_high_pct": round(100 * 0.7e6 / UNIVERSE_PIN),
        },
    }
    OUT.write_text(json.dumps(basis, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
