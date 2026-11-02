# The feature columns that version 1.0 withholds

Version 1.0's `features` config leaves out 12 of the feature layer's columns. This page says what the 12 columns are, why each is withheld, how the test behind the 2 orthotactic columns works, what its results mean, and what a later version needs before the columns return.

The rule they answer to is the project's: no public field may reveal a withheld list's membership. The 5 withheld lists are NWL2023, CSW21, SOWPODS, and Webster's Second in its 2 forms, `web2` and `web2a`. Their rows still ship. What a public version leaves out is anything that says which rows they list.

## 1. The feature layer

The feature layer (`pipeline/research/features/FEATURES.md`) gives each single-token candidate a set of measured signals: Google Books counts and their Zipf residual, wordfreq's frequency, OCR-confusion ratios, a morphology measure, and a character model's score. They were built as signals of unknown reliability, and none of them decides whether a string is in the universe. The 9 columns that ship come from Google Books and wordfreq alone, so no panel set enters them.

## 2. The 10 columns computed against a withheld list

These columns compare a string with a reference list. The base reference is WordNet together with `web2`, and the class-capable reference is WordNet together with `web2a`.

| Column | What it measures |
|---|---|
| `ocr_neighbor_hits` | how many of the string's neighbors under 6 typed OCR confusions the base reference lists |
| `ocr_neighbor_freq_ratio` | the largest frequency ratio of such a neighbor to the string |
| `ocr_apostrophe_ratio`, `ocr_ligature_ratio`, `ocr_hyphen_drop_ratio`, `ocr_strip_ratio` | on a plain string, the frequency ratio of a restored form (with an apostrophe, a ligature, a hyphen, or an accent) that the class-capable reference lists |
| `ocr_hyphen_junction_ratio` | on a hyphenated string, the same for the string with its hyphens removed |
| `morph_productivity_vn`, `morph_has_parse` | whether the string parses as a productive suffix on a stem the reference lists, and that suffix's productivity |
| `segment_attested_fraction` | on a hyphenated string, the share of its segments the base reference lists |

A reader who knows WordNet, which is public, can work back from any of these values to whether `web2` or `web2a` lists the string's OCR neighbor, its stem, or its segments. So the columns are withheld as built. No test was needed: the dependence is direct.

## 3. The 2 orthotactic columns

### What the character model is

`orthotactic_logp_total` and `orthotactic_logp_per_char` are a string's log-probability (base 10) under the layer's character model, in total and per character. The model (`pipeline/research/features/charmodel.py`) is an interpolated character n-gram model of order 4. It reads a string 1 character at a time over 50 symbols: the CEOL alphabet's 47 letters, the hyphen, the apostrophe, and an end marker. Each character's probability mixes the estimates given the previous 3, 2, 1, and 0 characters with a uniform floor, and the mixing weights are tuned on a held-out development set. It is the EOL's character model with only its alphabet widened.

A high score says a string's letter sequences resemble those of the strings the model was fitted on. It was built as 1 signal among several for telling English-like candidates from OCR errors and foreign spellings, and the layer's gate measured that separation (`FEATURES.md`).

### Why it depends on the withheld lists

The model was fitted on the "strong-positive pool" (`pipeline/research/features/partitions.py`): the strings that at least 2/3 of their applicable panel sets list. The 13 panel sets are the 8 published ones and the 5 withheld lists. On a plain string 12 sets apply, because `web2a` does not apply to plain strings, so the pool needs 8 listings, and the 4 withheld lists that apply can supply up to 4 of them. The pool holds 127,043 strings, split by a hash of each string into training, development, and test parts; the model was fitted on the 89,059 training strings.

So which strings the model learned from depends on the withheld lists. A probability names no list, so the columns can look safe. The test below checks that the way a reader could, with only the public release and the public code.

### The test

The test is `pipeline/research/release/feature_leak.py`, and its record is `pipeline/research/release/feature_leak_v2.1.json`. It ran on October 25, 2026, over the private layers, against the build the ruling reviewed, which the repository's records name v2.1; version 1.0 holds that build's rows and columns unchanged, value for value (`pipeline/research/release/rename_v1.0.json`). It publishes only the figures below.

1. **The refit.** The committed code, refitted, reproduces the layer's column to within 7.39e-07. A reader can rebuild the model.
2. **A published-only model.** The same model, fitted on the pool that the same rule chooses from the 8 published sets alone: 110,045 strings. A reader can build this model too.
3. **The residual test.** Take the shipped single-token rows with 12 applicable sets, and group them by how many published sets list them. In a group with 4 to 7 published listings, a row is in the pool exactly when enough withheld lists also list it. Within each group, the test subtracts the published-only model's score from the released column and asks how well that difference picks out the pool rows. A row with 8 published listings is always in the pool, and a row with fewer than 4 never is, so those groups tell nothing.
4. **The held-out pool.** The same test with the pool's test strings alone, which the released model never saw during fitting.
5. **Memorization.** The released column on the pool's training strings against its test strings.

The measure is the AUC: the chance that a pool row, drawn at random, scores higher than a row outside the pool from the same group. At 0.5 the difference carries nothing about the withheld lists; at 1.0 it sorts them perfectly.

| Published listings | AUC of the difference | The same, held-out pool strings only |
|---|---:|---:|
| 4 of 8 | 0.7076 | 0.6280 |
| 5 of 8 | 0.7823 | 0.7156 |
| 6 of 8 | 0.7650 | 0.7752 |
| 7 of 8 | 0.6044 | 0.6170 |

The training strings score barely above the test strings (AUC 0.5349). The per-character column is shown; the total column's results are in the record and read the same. Every AUC in the record carries its 95% interval, from the feature gate's own formula.

### What the results mean

- **The columns reveal the withheld lists, in part.** A reader with the public release and the public code could rank strings by how likely the withheld lists are to list them, well above chance. The ranking names no list and settles no single string, but it is a trace of their membership, and the plan's rule forbids that.
- **The model does not memorize single strings.** Pool strings the model never saw show the trace as well. It comes from the model's lean as a whole: fitted on strings the withheld lists helped choose, it rates strings like theirs higher.
- **The other columns are not affected.** The test covers the orthotactic columns only. The 10 columns of §2 are withheld on their direct dependence, and the 9 that ship use no panel set.
- **The values themselves are unchanged.** The columns stay in the private feature layer as built.

## 4. The ruling, and when the columns return

All 12 columns are withheld, and version 1.0 ships none of them. A later version can bring them back once each is recomputed without the withheld lists. The 10 need a published reference in place of `web2` and `web2a`. The 2 orthotactic columns need the model refitted on the published-only pool, and this test run again on the result.

Until then, 2 questions of the analysis plan wait for that version, because the analysis uses only the public release: F5, which needs `orthotactic_logp_per_char`, and F7, which needs `segment_attested_fraction`.
