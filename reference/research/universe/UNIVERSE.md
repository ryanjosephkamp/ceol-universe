# C4 step 0 — the pinned measurement universe

**Everything in this artifact is a CANDIDATE. Nothing is validated by
being pinned; validation is what the rest of C4 exists to measure.**
Built by `research/universe/build_universe.py` under C-009; every figure
lives in `universe.json` and is re-checked by the doc-numbers enforcer.

## What was built

`data/universe.parquet` (gitignored, local): **10,001,741 rows** — the
merged v0 table (9,867,866 rows, hash-verified against `merge.json`)
plus the **133,875 C-009 pin additions**, re-derived word-for-word from
the union of `research/audit/universe_miss_candidates.csv` and the
gitignored restricted split, minus the wordfreq-only rows held at the
D-030 boundary. Schema: the merged columns plus `c4_addition` and
**`is_restricted`** — True for exactly the **1,985** words attested only
by NWL2023/CSW21, so every downstream artifact can enforce the licence
split mechanically.

| Stratum | Rows |
|---|---:|
| EOL valid (pinned split, historical fact) | 345,103 |
| EOL invalid | 9,308,896 |
| C1 exceptions | 213,867 |
| C4 additions | 133,875 |
| **Total** | **10,001,741** |

## Proofs carried by the build

- **Filter-equivalence re-asserted over the new artifact**: `eol == true`
  regenerates `merged_valid_words.txt` (`aa8df4c5…`) and
  `eol_universe and not eol` regenerates `merged_invalid_words.txt`
  (`23701bd8…`), both byte-exact — the C2 proof survives the pin.
- **Order and uniqueness**: rows are sorted, no duplicate words (checked
  row-by-row on the shipped bytes).
- **Reconciliation**: addition and restricted counts re-derive from
  `audit.json` inside the build, which refuses to write on any mismatch.
- **Licence**: the artifact contains restricted words and therefore
  lives in gitignored `data/`, never committed or pushed; the permanent
  suite member `tests/test_licence.py` scans every tracked file for
  restricted tokens.
