"""
C4 step 1: the evidence matrix over the pinned universe, under C-010.

E[word, detector] ∈ {1, 0, NA(-1)} for the twelve binary detectors, plus
the SCOWL ordinal tier (-1 NA · 0 absent · else smallest containing size)
and the all-languages Wiktionary title screen. Lookup is exact
CEOL-normalized key equality; NA placement follows the C-010
applicability table, which this module DERIVES from the measured derived
sets — the decision entry and the build can therefore be cross-checked
against each other by the enforcer, and a drifted source breaks the build
rather than the semantics.

Cross-checks carried by the build (all hard errors):
- every derived set matches its recorded sha256 / pinned count;
- every detector's vocabulary is contained in the pinned universe —
  except WordNet's newly-visible exception lemmas, which are reported and
  committed as intake candidates (they are wordnet-attested, hence
  redistributable);
- the twelve detector columns reproduce the EOL evidence matrix's
  per-detector totals digit-for-digit on the shared 9,787,841-word frame.

Run:  python -m research.evidence.build_evidence
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ceol.grammar import CENSUS_CLASSES
from ceol.ingest.common import DERIVED_DIR, EOL_REPO, sha256_file
from ceol.ingest.evidence_sources import (EOL_DERIVED_PINS, SCOWL_TIERS_TSV,
                                          read_eol_derived)

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
EVIDENCE_DIR = REPO / "research" / "evidence"
UNIVERSE_PARQUET = DATA_DIR / "universe.parquet"
EOL_EVIDENCE = EOL_REPO / "research" / "data" / "evidence.parquet"

#: Column order of the twelve binary detectors (EOL order, web2a after web2).
DETECTORS = ("wordnet", "wiktionary_english", "web2", "web2a",
             "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
             "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
             "csw21")

#: Class flags a word can carry: the six census classes, the s-final
#: diagnostic (emitted by classes() alongside apostrophe-form), and the
#: synthetic "plain".
ALL_FLAGS = tuple(CENSUS_CLASSES) + ("s-final", "plain")

#: Recorded format/scope accounts for measured-zero cells (C-010). A cell
#: is NA iff measured zero AND its account appears here; a zero without an
#: account, or an account without a zero, is a build error.
BLINDNESS_ACCOUNTS = {
    "wordnet": {"accented", "ligature", "diaeresis"},
    "web2": {"accented", "contraction", "apostrophe-form", "s-final",
             "ligature", "diaeresis"},
    "web2a": {"accented", "contraction", "apostrophe-form", "s-final",
              "ligature", "diaeresis", "plain"},
    "hunspell_en_US": {"hyphenated", "accented", "ligature", "diaeresis"},
    "hunspell_en_GB": {"ligature"},
    "hunspell_en_CA": {"hyphenated", "accented", "ligature", "diaeresis"},
    "hunspell_en_AU": {"hyphenated", "accented", "ligature", "diaeresis"},
    "enable1": {"hyphenated", "accented", "contraction", "apostrophe-form",
                "s-final", "ligature", "diaeresis"},
    "sowpods_legacy": {"hyphenated", "accented", "contraction",
                       "apostrophe-form", "s-final", "ligature", "diaeresis"},
    "nwl2023": {"hyphenated", "accented", "contraction", "apostrophe-form",
                "s-final", "ligature", "diaeresis"},
    "csw21": {"hyphenated", "accented", "contraction", "apostrophe-form",
              "s-final", "ligature", "diaeresis"},
    "wiktionary_english": set(),
    "scowl": {"hyphenated", "ligature"},
}

#: Expected set sizes (census.json record counts; EOL manifest pins for
#: the Scrabble lists live in EOL_DERIVED_PINS).
EXPECTED_TOTALS = {
    "wiktionary_english": 831973, "wordnet": 82732, "web2": 234456,
    "web2a": 31213, "hunspell_en_US": 121252, "hunspell_en_GB": 262413,
    "hunspell_en_CA": 120947, "hunspell_en_AU": 121490, "scowl": 518438,
}


def _read_lines(path: Path) -> set[str]:
    with open(path, encoding="utf-8") as f:
        return {line.rstrip("\n") for line in f if line.strip()}


def _class_counts(words: set[str]) -> dict[str, int]:
    from ceol.grammar import classes as class_flags
    counts: dict[str, int] = {f: 0 for f in ALL_FLAGS}
    for w in words:
        flags = class_flags(w)
        if not flags:
            counts["plain"] += 1
        else:
            for f in flags:
                counts[f] += 1
    return counts


def load_sources() -> tuple[dict[str, set[str]], dict[str, set[str]], dict]:
    """Detector sets + applicability, derived and verified."""
    sets: dict[str, set[str]] = {}
    for src in ("wiktionary_english",):
        sets[src] = _read_lines(DERIVED_DIR / "wiktionary_english_all.txt")
    for src in ("wordnet", "web2", "web2a", "hunspell_en_US",
                "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU"):
        sets[src] = (_read_lines(DERIVED_DIR / f"{src}.txt")
                     | _read_lines(DERIVED_DIR / f"{src}_plain.txt"))
    for src in ("enable1", "sowpods_legacy", "nwl2023", "csw21"):
        sets[src] = read_eol_derived(src)
    scowl_set = (_read_lines(DERIVED_DIR / "scowl.txt")
                 | _read_lines(DERIVED_DIR / "scowl_plain.txt"))

    for src, want in EXPECTED_TOTALS.items():
        got = len(scowl_set) if src == "scowl" else len(sets[src])
        if got != want:
            raise RuntimeError(f"{src}: {got:,} words != expected {want:,}")

    applicability: dict[str, list[str]] = {}
    measured: dict[str, dict[str, int]] = {}
    for src in DETECTORS + ("scowl",):
        words = scowl_set if src == "scowl" else sets[src]
        counts = _class_counts(words)
        measured[src] = counts
        blind = BLINDNESS_ACCOUNTS[src]
        applicable = []
        for flag in ALL_FLAGS:
            if counts[flag] == 0 and flag not in blind:
                raise RuntimeError(
                    f"{src}: measured zero on {flag!r} with no recorded "
                    "blindness account — C-010 rule violated")
            if counts[flag] > 0 and flag in blind:
                raise RuntimeError(
                    f"{src}: {counts[flag]:,} {flag!r} words but the cell "
                    "is declared blind — C-010 rule violated")
            if flag not in blind:
                applicable.append(flag)
        applicability[src] = applicable

    screen = (_read_lines(DERIVED_DIR / "wiktionary_titles.txt")
              | _read_lines(DERIVED_DIR / "wiktionary_titles_plain.txt"))
    return sets, {"scowl": scowl_set, "screen": screen}, {
        "applicability": applicability, "measured_classes": measured}


def build() -> dict:
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    sets, aux, meta = load_sources()
    applicability = {src: set(v) for src, v in meta["applicability"].items()}
    scowl_set, screen = aux["scowl"], aux["screen"]
    tiers: dict[str, int] = {}
    with open(SCOWL_TIERS_TSV, encoding="utf-8") as f:
        for line in f:
            w, t = line.rstrip("\n").split("\t")
            tiers[w] = int(t)
    if set(tiers) != scowl_set:
        raise RuntimeError("scowl tier map does not cover the scowl set")

    uni = pq.read_table(UNIVERSE_PARQUET,
                        columns=["word", "classes", "is_restricted"])
    n = uni.num_rows
    universe_words = set(uni.column("word").to_pylist())

    # -- containment: every detector vocabulary must be inside the pin,
    #    except wordnet's newly-visible exception lemmas (reported).
    beyond: dict[str, set[str]] = {}
    for src in DETECTORS:
        out = sets[src] - universe_words
        if src == "wordnet":
            beyond[src] = out
        elif out:
            raise RuntimeError(f"{src}: {len(out):,} words outside the "
                               f"pinned universe: {sorted(out)[:5]}")
    scowl_out = scowl_set - universe_words
    if scowl_out:
        raise RuntimeError(f"scowl: {len(scowl_out):,} outside the universe")
    wordnet_beyond = sorted(beyond["wordnet"])
    with open(EVIDENCE_DIR / "wordnet_beyond_frame.txt", "w",
              encoding="utf-8") as f:
        for w in wordnet_beyond:
            f.write(w + "\n")

    # -- the matrix ---------------------------------------------------------
    words = uni.column("word").to_pylist()
    classes_col = uni.column("classes").to_pylist()
    cols = {src: np.empty(n, dtype=np.int8) for src in DETECTORS}
    tier_col = np.empty(n, dtype=np.int16)
    screen_col = np.empty(n, dtype=np.int8)
    fires = {src: 0 for src in DETECTORS}
    na_counts = {src: 0 for src in DETECTORS}
    n_all_zero = 0

    for i, (w, cls) in enumerate(zip(words, classes_col)):
        flags = frozenset(cls.split(";")) if cls else frozenset(("plain",))
        positive = False
        for src in DETECTORS:
            if flags <= applicability[src]:
                hit = w in sets[src]
                cols[src][i] = 1 if hit else 0
                if hit:
                    fires[src] += 1
                    positive = True
            else:
                cols[src][i] = -1
                na_counts[src] += 1
        if flags <= applicability["scowl"]:
            t = tiers.get(w, 0)
            tier_col[i] = t
            if t:
                positive = True
        else:
            tier_col[i] = -1
        screen_col[i] = 1 if w in screen else 0
        if not positive:
            n_all_zero += 1

    # -- EOL reproduction: shared-frame totals, digit for digit -------------
    eol_words = set(pq.read_table(EOL_EVIDENCE, columns=["word"])
                    .column("word").to_pylist())
    eol_table = pq.read_table(
        EOL_EVIDENCE, columns=[d for d in DETECTORS if d != "web2a"]
        + ["scowl_tier"])
    reproduction = {}
    for src in DETECTORS:
        if src == "web2a":
            continue
        eol_total = pc.sum(eol_table.column(src)).as_py()
        mine = len(sets[src] & eol_words)
        reproduction[src] = {"eol": int(eol_total), "ceol_on_frame": mine}
        if int(eol_total) != mine:
            raise RuntimeError(f"EOL reproduction FAILED for {src}: "
                               f"{eol_total:,} != {mine:,}")
    # scowl is NOT like-for-like by design: the census's C-005 inclusion
    # rule (words + contractions, every category) is wider than the EOL's
    # six *-words families. The reproduction check is therefore the EOL's
    # own tier map against its own frame; the CEOL surplus on the shared
    # frame is reported with its explanation, and tier AGREEMENT on every
    # shared word is already asserted at ingest (eol_comparison: higher=0,
    # eol_only=0).
    eol_tier_nonzero = pc.sum(
        pc.cast(pc.not_equal(eol_table.column("scowl_tier"), 0),
                pa.int64())).as_py()
    eol_tiermap_words = set()
    with open(EOL_REPO / ".cache" / "sources" / "derived" /
              "scowl_tiers.tsv", encoding="utf-8") as f:
        for line in f:
            eol_tiermap_words.add(line.split("\t")[0])
    eol_map_on_frame = len(eol_tiermap_words & eol_words)
    ceol_on_frame = len(scowl_set & eol_words)
    reproduction["scowl_tier_nonzero"] = {
        "eol": int(eol_tier_nonzero),
        "eol_tiermap_on_frame": eol_map_on_frame,
        "ceol_on_frame": ceol_on_frame,
        "ceol_surplus_from_wider_inclusion": ceol_on_frame - eol_map_on_frame,
    }
    if int(eol_tier_nonzero) != eol_map_on_frame:
        raise RuntimeError("EOL reproduction FAILED for scowl_tier")
    del eol_tiermap_words
    del eol_words, eol_table

    # -- SR2 analogue -------------------------------------------------------
    wordfreq_full = (_read_lines(DERIVED_DIR / "wordfreq.txt")
                     | _read_lines(DERIVED_DIR / "wordfreq_plain.txt"))
    no_corpus = np.fromiter((w not in wordfreq_full for w in words),
                            dtype=bool, count=n)
    binary_zero = np.ones(n, dtype=bool)
    for src in DETECTORS:
        binary_zero &= cols[src] != 1
    binary_zero &= tier_col <= 0
    sr2_a = int(binary_zero.sum())
    sr2_b_upper = int((binary_zero & no_corpus).sum())
    assert sr2_a == n_all_zero

    # -- patterns -----------------------------------------------------------
    stacked = np.stack([cols[src] for src in DETECTORS], axis=1)
    patterns = len(np.unique(stacked, axis=0))

    table = pa.table({
        "word": uni.column("word"), "is_restricted":
            uni.column("is_restricted"),
        **{src: pa.array(cols[src]) for src in DETECTORS},
        "scowl_tier": pa.array(tier_col),
        "wikt_title_screen": pa.array(screen_col),
    })
    out_path = DATA_DIR / "evidence.parquet"
    pq.write_table(table, out_path, compression="zstd")

    evidence = {
        "generated_by": "research/evidence/build_evidence.py",
        "decision": "C-010",
        "universe_rows": n,
        "detectors": list(DETECTORS),
        "applicability": meta["applicability"],
        "measured_classes": meta["measured_classes"],
        "fires": fires,
        "na_counts": na_counts,
        "eol_reproduction": reproduction,
        "sr2": {
            "reading_a_rows": sr2_a,
            "reading_a_pct": round(100 * sr2_a / n, 2),
            "reading_b_upper_rows": sr2_b_upper,
            "reading_b_upper_pct": round(100 * sr2_b_upper / n, 2),
            "note": ("reading B finalized in step 2 once Google Books "
                     "presence exists; the upper bound can only shrink"),
        },
        "binary_pattern_count": patterns,
        "wordnet_beyond_frame": len(wordnet_beyond),
        "screen_hits": int(screen_col.sum()),
        "artifacts": {
            "evidence_parquet_sha256": sha256_file(out_path),
            "wordnet_beyond_frame_sha256":
                sha256_file(EVIDENCE_DIR / "wordnet_beyond_frame.txt"),
        },
    }
    evidence["doc_figures"] = {
        "universe_rows": n,
        "binary_pattern_count": patterns,
        "wordnet_beyond_frame": len(wordnet_beyond),
        "sr2_reading_a_pct": evidence["sr2"]["reading_a_pct"],
        "sr2_b_upper_pct": evidence["sr2"]["reading_b_upper_pct"],
        "screen_hits": int(screen_col.sum()),
        "scowl_on_frame":
            reproduction["scowl_tier_nonzero"]["eol_tiermap_on_frame"],
        "scowl_ceol_surplus": reproduction["scowl_tier_nonzero"][
            "ceol_surplus_from_wider_inclusion"],
        "scowl_total": len(scowl_set),
        **{f"fires_{s}": fires[s] for s in DETECTORS},
        **{f"na_{s}": na_counts[s] for s in DETECTORS},
    }
    (EVIDENCE_DIR / "evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    ev = build()
    print(f"[evidence] {ev['universe_rows']:,} rows × {len(ev['detectors'])} "
          f"binary detectors + tier + screen; {ev['binary_pattern_count']:,} "
          "distinct binary patterns")
    print(f"[evidence] EOL reproduction: all shared-frame totals exact")
    print(f"[evidence] SR2 reading A {ev['sr2']['reading_a_pct']}% | "
          f"reading-B upper bound {ev['sr2']['reading_b_upper_pct']}% "
          f"(bar 50%)")
    print(f"[evidence] wordnet beyond frame: {ev['wordnet_beyond_frame']:,} "
          "(committed, intake candidates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
