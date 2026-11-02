---
license: cc-by-sa-4.0
pretty_name: Common English OpenList
configs:
- config_name: exceptions
  data_files:
  - split: candidates
    path: data/exceptions.parquet
- config_name: merged
  data_files:
  - split: candidates
    path: data/merged.parquet
- config_name: universe_v2_shippable
  data_files:
  - split: candidates
    path: data/universe_v2_shippable.parquet
---

# Common English OpenList (CEOL) — candidate inventories, v0

**PRIVATE — pre-release working data. Every row is a CANDIDATE. No word in
this dataset has been validated by the CEOL programme; no threshold has
been chosen; the split named `candidates` means what it says.**

The CEOL will be the largest list of valid *common* English words —
excluding exclusive proper nouns and exclusive acronyms — grown from the
[English OpenList](https://huggingface.co/datasets/ryanjosephkamp/english-openlist)
(EOL) by admitting hyphenated compounds, accepted accented loanwords,
contractions and apostrophe forms, ligature and diaeresis spellings, under
an executable grammar. Validation science (calibrated per-word scores)
lands in a later phase; this v0 carries the C1/C2 candidate inventories.

## Configs

- **`exceptions`** — 213,867 candidates the EOL's `^[a-z]+$` rule could
  not hold: `word`, `classes` (non-exclusive flags: hyphenated, accented,
  contraction, apostrophe-form, ligature, diaeresis, s-final), `sources`,
  `intake_date`.
- **`merged`** — 9,867,866 rows: the EOL candidate universe at pinned
  revision `c113969807f3045f5ddd8cc919d0189d54ba368b` (9,653,999 strings)
  plus the exceptions. Columns: `word`, `eol` (bool: on the EOL's pinned
  valid list), `eol_universe` (bool: in the pinned universe), `classes`,
  `sources`, `intake_date`.

- **`universe_v2_shippable`** — 10,294,621 rows: the shippable layer of
  universe v2 (the C-016 pin, 10,296,606 candidates), added on
  2026-09-17 as an off-machine copy under decision C-064. It is every
  row of the pin whose `is_restricted` is false, with the pin's fourteen
  columns: `word`, `eol`, `eol_universe`, `classes`, `sources`,
  `intake_date`, `c4_addition`, `is_restricted`, `token_count`,
  `c015_addition`, `wn_instance`, `wn_capitalized`, `wk_proper_noun`,
  `wk_flags`. The 1,985 rows attested only by the two non-redistributable
  game lists are not here and never ship in any channel; they are
  re-derived locally from the pinned lists. Internal spaces are admitted
  in this config (294,865 multiword candidates).

**Filter-equivalence, proven:** filtering `merged` on `eol == true`
(sorted, one word per line) regenerates the EOL's pinned
`merged_valid_words.txt` byte-for-byte (sha256 `aa8df4c5…`), and
`eol_universe and not eol` regenerates `merged_invalid_words.txt`
(`23701bd8…`). The proof runs in the repository's permanent test suite.

`eol` records the **pinned** EOL split as historical fact, not a CEOL
verdict — the live EOL moves its valid/invalid split nightly.

## Provenance

`sources` on an exceptions row lists every censused source whose derived
set contains the word (containment, re-derived — not first-seen):
Wiktionary (English-confirmed), hunspell en_US/GB/CA/AU, SCOWL
(words + contractions), web2/web2a, wordfreq, and the EOL correction
ledger's 170 preserved form-rule deletions. EOL-universe rows carry
`eol_universe@c1139698` — dataset-level provenance; per-source attestation
for the full universe is measured by a later phase.

Sources are redistributable (Wiktionary CC-BY-SA 4.0, SCOWL, LibreOffice
hunspell dictionaries, web2 public domain, wordfreq); the card's license
reflects the CC-BY-SA share-alike floor. License review precedes any
public release.
