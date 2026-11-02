# Universe v2: the C-016 pin

**2026-08-26** · built by
[`build_universe_v2.py`](build_universe_v2.py) at the owner's S4 gate
ruling (full-union intake, no filter); every figure below is
[`universe_v2.json`](universe_v2.json)'s or
[`spaced_applicability.json`](spaced_applicability.json)'s and is
re-derived by `research/verify_doc_numbers.py`. The artifact
(`data/universe_v2.parquet`) contains the 1,985 restricted rows and
stays local and gitignored, like its predecessor (C-009 licence rule).

## The pin

**10,296,606 rows** = the 10,001,741-row v1 universe (C-009,
byte-reproduced, see the proofs) + **294,865 spaced candidates**
admitted at the S4 gate: wordnet-only 43,972 · wiktionary_english-only
231,382 · both 19,511. Restricted rows: 1,985 — unchanged from v1;
every spaced row is shippable-layer (the census measured zero
space-bearing game-list entries).

Everything here remains a CANDIDATE inventory: no word
is validated by being pinned.

## Schema

The eight v1 columns unchanged, plus six C-015 columns:

| column | type | spaced rows | v1 rows |
|---|---|---|---|
| `token_count` | int32 | space count + 1 | 1 |
| `c015_addition` | bool | true | false |
| `wn_instance` | bool? | WordNet instance-synset membership; null unless wordnet attests | null |
| `wn_capitalized` | bool? | WordNet data-file capitalization; null unless wordnet attests | null |
| `wk_proper_noun` | bool? | Wiktionary Proper-noun heading; null unless wiktionary attests | null |
| `wk_flags` | string? | J3 category flags (`idiomatic`/`phrasal-verb`/`phrasebook`/`proverb`, semicolon-joined; may be empty); null unless wiktionary attests | null |

Properness signals are **recorded, never filtered on** (the S4 ruling);
nulls mean *not measured by that source*, never false. Provenance is
per-candidate in `sources` (C-008): `wordnet`, `wiktionary_english`, or
both; `intake_date` for spaced rows is `2026-08-26`, the ruling date.

## The two filter-equivalence proofs (permanent suite members)

Both re-derived from the shipped artifact by
`tests/test_universe_v2.py` on every suite run:

- **(a) EOL byte-exactness**: the `eol==true` and `eol_universe`
  projections hash to the EOL manifest pins (`aa8df4c5…`,
  `23701bd8…`) — no spaced candidate can leak into the EOL view.
- **(b) no-space projection**: rows with `token_count == 1`, serialized
  over the eight v1 columns in v1's canonical form, hash to
  `18733e975353f4f5f62983fc91715f5e3305d7cb981bcd273aafa3a54ca1e885` —
  v1's `canonical_content_sha256`, so the 10,001,741-row universe is
  reproduced byte-exact, columns and all (the structural revert
  guarantee of C-015 invariant 2).

## Spaced-class applicability (C-010 extended, measured)

Per C-010's rule — NA iff the derived output carries zero spaced
entries and a format/scope account is recorded — measured by
[`measure_spaced_applicability.py`](measure_spaced_applicability.py)
over every detector's pin-verified derived splits:

- **Applicable (2)**: `wordnet` (63,483 spaced entries),
  `wiktionary_english` (250,893) — the census re-ingest under the
  extended grammar is their spaced derived set.
- **Structural NA (11)**: enable1, sowpods_legacy, nwl2023, csw21
  (A–Z tile alphabet; the game lists additionally measured at zero
  space-bearing raw rows), hunspell ×4 (single-token dic entry
  grammar), web2, web2a (single-token entry grammars), scowl (ordinal
  covariate; all final lists space-free). Every zero measured over the
  pinned derived splits, none assumed.

Corpus boundary unchanged (D-030): wordfreq and Google Books 1-grams
cannot observe spaced terms; spaced-class corpus features remain
absent-with-mask until the C-014 reassessment selects an approach that
needs them.

## Artifact hashes

- `universe_v2.parquet` sha256
  `adaa1232b6bc4d9ead97f5e19a005b264bb6db8db77b6374fe66cdd1d2aca9dd`
- canonical content sha256 (all fourteen columns)
  `514549c8dc6c73ea626792dda308ac792c2f5b7a8ba7b041f32075560dc84257`
- v1 parquet sha256 (input, verified)
  `3703c793e7a4e72bfe4082793f2e3109a27e89e57093c859d84be73f0c3f0444`
