"""
P2 of the intake-provenance package (C-064 rulings 1 and 2): the manifest
of the EOL's two dictionaries at the pinned revision, and their measured
coverage of the pinned universe.

research/provenance/eol_dictionaries_manifest.json records, for each
dictionary: its URL at the revision the pin reads (08ae92b8), its byte
size, its sha256 (the valid one over the local file, the invalid one over
the single stream, each equal to the hub's LFS object id), the hub's
identifiers as read, the retrieval time, and the extraction's counts
(entries, field names, the categorical intake fields' values, the state
of the channel list, the discovery-log labels). Then the coverage: how
many of the 9,308,837 invalid strings and the 344,830 valid strings have
an entry, how many entries carry a non-empty channel list, and how many
entries fall outside the inherited strings.

The layer is reproducible from this manifest alone: the URLs are
immutable hub artifacts and the hashes are the stop conditions of
extract_eol_intake.py. No candidate word is written here — counts, field
names, and the EOL schema's categorical values only.

Run:  python3 -m research.provenance.build_eol_dictionaries_manifest
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ceol.ingest.common import EOL_REPO, sha256_file

from .extract_eol_intake import DATASET, INVALID, REVISION, VALID

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "provenance" / "eol_dictionaries_manifest.json"
PIN_PARQUET = REPO / "data" / "universe_v2.parquet"
PIN_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"

LAYERS = ("eol_valid", "eol_invalid", "c1_exceptions", "c4_additions",
          "spaced_c015")

#: The EOL's correction ledgers that account for the inherited strings
#: with no entry in either dictionary (PACKAGE.md section 7, reading R9):
#: files of the EOL repository, read and never written, pinned here by
#: sha256. The two demotion ledgers name the generated forms the EOL
#: moved from its valid list to its invalid list on 2026-08-14; every
#: row's reason opens with the word "synthetic".
LEDGER_DIR = EOL_REPO / "corrections"
DEMOTION_LEDGERS = {
    "ledger_demotions.csv":
        "943afb5fbcd69233683160db62a02936ee35e67e463d4ac1e9b47d259741fedb",
    "ledger_demotions_stage4.csv":
        "d5cbe2c166c263928b87f8355c10e3403033d2cb0b5065f38072ce8fb290dee8",
}
OTHER_LEDGERS = {
    "ledger_single_letters.csv":
        "9845871e36417c21e3acd619d9ee33870a66ed4bf7f6a132e008ba0ff20c5648",
    "ledger_form_rules.csv":
        "a45df907dca8b369abad78fba3dbbe70cb2c133ca7e5e9abb8ba71910b6d0929",
}

#: A categorical field is printed value by value only while it stays a
#: small vocabulary; beyond this many distinct values the manifest keeps
#: the values seen at least MIN_VALUE_COUNT times and sums the rest, so
#: that no stray string of the EOL's data is copied into a committed file.
MAX_DISTINCT_VALUES = 64
MIN_VALUE_COUNT = 5


def intake_layers():
    """The pin's words and each row's intake layer code (PACKAGE.md §4.1),
    in the pin's order."""
    import numpy as np
    import pyarrow.parquet as pq

    meta = json.loads(PIN_JSON.read_text(encoding="utf-8"))
    got = sha256_file(PIN_PARQUET)
    if got != meta["artifacts"]["universe_v2_parquet_sha256"]:
        raise RuntimeError(f"universe_v2.parquet sha256 {got} is not the "
                           "C-016 pin")
    t = pq.read_table(PIN_PARQUET, columns=[
        "word", "eol", "eol_universe", "c4_addition", "c015_addition"])
    eol = t["eol"].to_numpy(zero_copy_only=False)
    uni = t["eol_universe"].to_numpy(zero_copy_only=False)
    c4 = t["c4_addition"].to_numpy(zero_copy_only=False)
    c15 = t["c015_addition"].to_numpy(zero_copy_only=False)
    layer = np.where(c15, 4, np.where(c4, 3, np.where(
        uni & eol, 0, np.where(uni, 1, 2)))).astype(np.int8)
    return t["word"].combine_chunks(), layer, got


def _entry_layers(intake_words, pin_words, layer):
    """For each dictionary entry, its row in the pin (or -1) and that
    row's layer code (or -1)."""
    import numpy as np
    import pyarrow.compute as pc

    idx = pc.index_in(intake_words, value_set=pin_words)
    pos = idx.fill_null(-1).to_numpy(zero_copy_only=False).astype(np.int64)
    codes = np.where(pos >= 0, layer[np.clip(pos, 0, None)], -1)
    return pos, codes


def read_ledger(name: str) -> list[dict]:
    """One EOL correction ledger, hash-verified, as rows."""
    import csv

    want = {**DEMOTION_LEDGERS, **OTHER_LEDGERS}[name]
    path = LEDGER_DIR / name
    got = sha256_file(path)
    if got != want:
        raise RuntimeError(f"the EOL ledger {name} hashes to {got}, not the "
                           f"pinned {want}")
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def demoted_generated_forms() -> dict[str, str]:
    """word -> the ledger's `category`, for every row of the two demotion
    ledgers. Every row must be a demotion of a synthetic form, or the
    reading that treats the ledgers as a record of generated strings
    does not hold and the build stops."""
    out: dict[str, str] = {}
    for name in DEMOTION_LEDGERS:
        for row in read_ledger(name):
            if row["action"] != "demote_to_invalid" \
                    or not row["reason"].startswith("synthetic "):
                raise RuntimeError(f"{name}: a row that is not the "
                                   "demotion of a synthetic form")
            if row["word"] in out:
                raise RuntimeError(f"{name}: a word demoted twice")
            out[row["word"]] = row["category"]
    return out


def _ledger_block(no_entry_words: set[str]) -> dict:
    from collections import Counter

    block = {}
    for name, sha in {**DEMOTION_LEDGERS, **OTHER_LEDGERS}.items():
        rows = read_ledger(name)
        named = {r["word"] for r in rows}
        entry = {
            "path": f"english-openlist/corrections/{name} (the EOL "
                    "repository, read-only)",
            "sha256": sha,
            "rows": len(rows),
            "actions": dict(sorted(Counter(
                r["action"] for r in rows).items())),
            "rows_naming_a_string_with_no_dictionary_entry":
                len(named & no_entry_words),
        }
        if name in DEMOTION_LEDGERS:
            entry["claimed_form"] = dict(sorted(Counter(
                r["reason"].split(" of ")[0] for r in rows).items()))
            entry["category"] = dict(sorted(Counter(
                r["category"] for r in rows).items()))
        block[name] = entry
    return block


def _trim(values: dict) -> dict:
    if len(values) <= MAX_DISTINCT_VALUES:
        return values
    kept = {k: v for k, v in values.items() if v >= MIN_VALUE_COUNT}
    rest = {k: v for k, v in values.items() if v < MIN_VALUE_COUNT}
    kept["(values seen fewer than "
         f"{MIN_VALUE_COUNT} times, summed)"] = sum(rest.values())
    kept["(distinct values in all)"] = len(values)
    return kept


#: The key under which the manifest counts the `source` values whose names
#: are withheld (build_provenance.withheld_sources).
WITHHELD_SOURCES_KEY = "withheld-list"


def _without_withheld_names(values: dict) -> dict:
    """`source` value counts with the withheld values counted together
    under `WITHHELD_SOURCES_KEY`, unnamed."""
    from .build_provenance import withheld_sources
    hidden = withheld_sources()
    out: dict = {}
    for value, n in values.items():
        key = WITHHELD_SOURCES_KEY if value in hidden else value
        out[key] = out.get(key, 0) + n
    return dict(sorted(out.items()))


def build() -> dict:
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    pin_words, layer, pin_sha = intake_layers()
    n_layer = {name: int((layer == i).sum()) for i, name in enumerate(LAYERS)}

    dictionaries: dict[str, dict] = {}
    found = {}
    for label, spec in (("valid", VALID), ("invalid", INVALID)):
        meta_path = spec["out"].with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["sha256"] != spec["sha256"] or meta["bytes"] != spec["bytes"] \
                or meta["revision"] != REVISION:
            raise RuntimeError(f"the {label} extraction's record does not "
                               "carry the pinned hash, size, and revision")
        if sha256_file(spec["out"]) != meta["intake_parquet_sha256"]:
            raise RuntimeError(f"{spec['out'].name} is not the file the "
                               "extraction recorded")
        t = pq.read_table(spec["out"], columns=[
            "word", "has_candidate_source", "candidate_source", "source"])
        if t.num_rows != meta["entries"]:
            raise RuntimeError(f"{spec['out'].name}: row count drifted")
        pos, codes = _entry_layers(t["word"].combine_chunks(), pin_words,
                                   layer)
        non_empty = pc.greater(pc.utf8_length(t["candidate_source"]), 0) \
            .fill_null(False).to_numpy(zero_copy_only=False)
        has_source = pc.is_valid(t["source"]).to_numpy(zero_copy_only=False)
        by_layer = {name: int((codes == i).sum())
                    for i, name in enumerate(LAYERS)}
        by_layer["outside_the_universe"] = int((codes == -1).sum())
        own = 0 if label == "valid" else 1
        in_own = codes == own
        entry = {k: v for k, v in meta.items()
                 if k not in ("categorical_value_counts",)}
        entry["categorical_value_counts"] = {
            name: _trim(_without_withheld_names(values) if name == "source" else values)
            for name, values in meta["categorical_value_counts"].items()}
        entry["entries_by_the_layer_of_their_key"] = by_layer
        entry["entries_with_a_non_empty_channel_list"] = int(non_empty.sum())
        entry["entries_with_a_source_value"] = int(has_source.sum())
        entry["entries_with_neither"] = int((~non_empty & ~has_source).sum())
        entry["own_layer"] = LAYERS[own]
        entry["own_layer_entries_with_a_non_empty_channel_list"] = int(
            (in_own & non_empty).sum())
        entry["own_layer_entries_with_a_source_value"] = int(
            (in_own & has_source).sum())
        entry["own_layer_entries_with_neither"] = int(
            (in_own & ~non_empty & ~has_source).sum())
        dictionaries[label] = entry
        hit = np.zeros(len(layer), dtype=bool)
        hit[pos[pos >= 0]] = True
        found[label] = hit

    coverage = {}
    for i, name in ((0, "eol_valid"), (1, "eol_invalid")):
        rows = layer == i
        own, other = ("valid", "invalid") if i == 0 else ("invalid", "valid")
        coverage[name] = {
            "rows": int(rows.sum()),
            "with_an_entry_in_its_own_dictionary":
                int((rows & found[own]).sum()),
            "with_an_entry_in_the_other_dictionary_only":
                int((rows & ~found[own] & found[other]).sum()),
            "with_an_entry_in_both": int((rows & found[own]
                                          & found[other]).sum()),
            "with_no_entry": int((rows & ~found[own] & ~found[other]).sum()),
        }

    # the inherited strings with no entry, accounted for by the ledgers
    no_entry = (layer <= 1) & ~found["valid"] & ~found["invalid"]
    import pyarrow as pa
    no_entry_words = set(pin_words.filter(pa.array(no_entry)).to_pylist())
    ledgers = _ledger_block(no_entry_words)
    demoted = set(demoted_generated_forms())
    single = {r["word"] for r in read_ledger("ledger_single_letters.csv")}
    form_rules = {r["word"] for r in read_ledger("ledger_form_rules.csv")
                  if r["action"] == "add_candidate"}
    accounted = {
        "inherited_strings_with_no_entry": len(no_entry_words),
        "named_by_the_two_demotion_ledgers": len(no_entry_words & demoted),
        "demotion_ledger_rows_in_all": len(demoted),
        "demotion_ledger_words_that_do_have_an_entry":
            len(demoted - no_entry_words),
        "named_by_the_single_letter_ledger":
            len((no_entry_words - demoted) & single),
        "named_by_the_form_rule_ledger_as_added_candidates":
            len((no_entry_words - demoted - single) & form_rules),
        "named_by_none_of_the_four":
            len(no_entry_words - demoted - single - form_rules),
    }

    manifest = {
        "generated_by":
            "research/provenance/build_eol_dictionaries_manifest.py",
        "decision": "C-064 rulings 1 and 2",
        "dataset": DATASET,
        "revision": REVISION,
        "note_on_the_invalid_dictionary_hash":
            "sha256 is the hub's ETag (X-Linked-ETag) and LFS object id, "
            "and the value the single stream reproduced; hub_xet_hash is "
            "the hub's Xet content hash, the value C-064 ruling 2 quotes "
            "as the ETag (PACKAGE.md section 7, reading R1)",
        "pin": {"universe_v2_parquet_sha256": pin_sha,
                "rows_by_layer": n_layer},
        "dictionaries": dictionaries,
        "coverage": coverage,
        "eol_correction_ledgers": ledgers,
        "no_entry_strings_accounted_for": accounted,
    }
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return manifest


def main() -> int:
    m = build()
    for name, c in m["coverage"].items():
        print(f"[manifest] {name}: {c['rows']:,} rows, "
              f"{c['with_an_entry_in_its_own_dictionary']:,} with an entry "
              f"in their own dictionary, {c['with_no_entry']:,} with none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
