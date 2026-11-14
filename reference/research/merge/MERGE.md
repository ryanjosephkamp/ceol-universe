# C2 — The merged CEOL v0 and the filter-equivalence proof

Built by `research/merge/build_merge.py`; every figure below lives in
`merge.json` and is re-checked by the doc-numbers enforcer. The proof also
runs permanently in `tests/test_equivalence.py`.

## What was built

Two dataset configs (C-002), written to `data/` (gitignored; shipped to the
private Hugging Face dataset, sha256s recorded in `merge.json`):

- **`exceptions.parquet`** — 213,867 census candidates: `word`, `classes`,
  `sources` (per-word source containment, C-008), `intake_date`.
- **`merged.parquet`** — 9,867,866 rows: the EOL universe at pinned
  revision `c1139698…` (9,653,999 strings) plus the exceptions inventory
  (213,867), disjoint by construction and asserted at build. Schema:
  `word`, `eol`, `eol_universe`, `classes`, `sources`, `intake_date`.

`eol` records the **pinned** EOL valid/invalid split (eol_valid 345,103,
eol_invalid 9,308,896) as historical fact, not a CEOL verdict — the live
EOL nightly moves its split daily, and the CEOL compares against the pin,
never against "the current dataset". No candidate has been validated by
this phase.

## Provenance (C-008)

Exception rows carry the census's containment lists (every source whose
derived set holds the word). EOL-universe rows carry
`eol_universe@c1139698` — dataset-level provenance, deliberately: their
per-source attestation is exactly what the C4 evidence matrix will measure,
and pretending to know it earlier would rebuild the `candidate_source`
trap.

## The proof

Filtering the shipped `merged.parquet` regenerates both pinned EOL files
**byte-for-byte**:

| Filter | Regenerated sha256 matches pin |
|---|---|
| `eol == true`, sorted, one per line | `aa8df4c5…` (merged_valid_words.txt) — exact |
| `eol_universe and not eol` | `23701bd8…` (merged_invalid_words.txt) — exact |

sha256 equality accounts for both directions at once — a missing word, an
extra word, or a duplicate would all change the hash. The remainder
(`eol_universe == false`) is exactly the 213,867-word exceptions inventory,
and the merged table carries no duplicate words. The equivalence check is a
permanent member of the test suite from this commit.
