---
license: cc-by-sa-4.0
pretty_name: CEOL Universe
language:
- en
size_categories:
- 10M<n<100M
tags:
- lexicon
- word-list
- english
- lexicography
- candidate-inventory
configs:
- config_name: universe
  default: true
  data_files:
  - split: candidates
    path: data/universe.parquet
- config_name: features
  data_files:
  - split: candidates
    path: data/features.parquet
- config_name: panel-listed
  data_files:
  - split: candidates
    path: data/panel-listed.parquet
- config_name: eol-valid
  data_files:
  - split: candidates
    path: data/eol-valid.parquet
- config_name: spaced
  data_files:
  - split: candidates
    path: data/spaced.parquet
- config_name: exceptions
  data_files:
  - split: candidates
    path: data/exceptions.parquet
---

# The CEOL Universe, version v2.0

**A private rehearsal. Version v2.0 is uploaded to this private
dataset to rehearse the release pipeline and is never made public (the
owner's decision C-078, line 3). The first public version is v3.0. Every
row is a candidate; no row is validated.**

This card is a datasheet: what the dataset is and is not, its names, its
version, its configs, every column, its sources and their licenses, the
provenance of its rows, how it was built and audited, its limitations,
what it does not record, its relation to a study that uses it, a canary,
how to cite it, and its change log. Every figure on it is a row of the
release calculator `research/release/release_calcs.py`, computed from the
committed records of the Common English OpenList (CEOL) repository; the
decision entries it names (C-001 and onward) are in that repository's
`research/DECISIONS.md`.

## 1. What this dataset is, and what it is not

The CEOL Universe is the candidate inventory of the CEOL, a project to
build a list of valid common English words that excludes exclusive
proper nouns and exclusive acronyms and admits hyphenated compounds,
accented loanwords, contractions, apostrophe forms, ligature and
diaeresis spellings, and multiword terms under an executable grammar
(C-001, C-015). This version holds 10,294,621 rows, 1 per
string. A row says that a pinned source lists the string, that the
string was inherited from the English OpenList (EOL) universe, or both.
**A row is not a verdict.** No row of this dataset has been validated by
the CEOL; no threshold has been chosen; the split is named `candidates`
because that is what every row is. The `eol` column records whether the
string was in the EOL's valid list at the pinned revision `c1139698`: a
historical fact at a pin, never a CEOL judgment, and the live EOL moves
its split nightly.

## 2. The 3 datasets and their names (C-078 line 1)

- **The EOL** (`ryanjosephkamp/english-openlist`): the validated English
  word list under its own grammar and governance. The CEOL reads it at a
  pinned revision and never writes to it.
- **The CEOL Universe** (this dataset, `ryanjosephkamp/ceol-universe`): the candidate
  inventory, versioned as its pins are (v2 is the pin of C-016; v3 the
  pin of a later entry).
- **The validated subsets**, 1 per operational definition and version,
  named `ceol-<definition>-<version>`; the first, `ceol-itw-1`, will come
  from the in-the-wild programme when that study has run. Each is a
  separate dataset with its own card.

No dataset is called the CEOL alone: the CEOL is the family and the
mission.

## 3. The version and the pin

Version v2.0 is a projection of universe v2, the pin of C-016:
10,296,606 candidates, of which 1,985 are restricted
(§6) and are not in this dataset. It was built on 2026-09-26 by
`research/release/build_release.py`, which verifies every pinned layer's
sha256 against its committed record before reading it, writes the files,
re-reads them, and asserts the properties this card states before
anything is kept; the record of the build, with every file's rows,
columns, bytes, and sha256 and the assertions' counts, is
`research/release/release_v2.0.json`. Version v2.0 is a
private rehearsal of that pipeline. The public version is v3.0: the same
pipeline over the universe-v3 pin, which adds the lexicon-development
line's admitted rows and a part-of-speech and inflection layer (C-078
lines 2 to 4).

| Layer | sha256 | Committed record |
|---|---|---|
| pin (`data/universe_v2.parquet`) | `adaa1232b6bc4d9ead97f5e19a005b264bb6db8db77b6374fe66cdd1d2aca9dd` | `research/universe_v2/universe_v2.json`, `artifacts.universe_v2_parquet_sha256` |
| provenance (`data/universe_v2_provenance.parquet`) | `7c9dc6284bf6393769eec3b26c27b8c77fa68dcf08cb5ef77148c2b7f07bec1b` | `research/provenance/provenance.json`, `artifact.sha256` |
| evidence (`data/evidence.parquet`) | `e4c86cc4a0caf3f01996e0abb50cedfd525ee7e08183679f154884bf7250d6ee` | `research/evidence/evidence.json`, `artifacts.evidence_parquet_sha256` |
| features (`data/features.parquet`) | `c578289b61d7b957bba1c91b9e65d3dbfcde3c5d74098316f6993643f240b7c7` | `research/provenance/provenance.json`, `inputs.features_parquet_sha256` |

## 4. The configs

The default config, `universe`, holds every shippable row. `features` holds
the feature layer for the single-token rows. The other 4
configs are filters of `universe`, with every column of `universe` and its
row order; each is the filter of `universe` by the stated predicate and
nothing else, which the build asserts on the written files.

| Config | File on the hub | Rows | Predicate |
|---|---|---:|---|
| `universe` | `data/universe.parquet` | 10,294,621 | is_restricted == false over the pin |
| `features` | `data/features.parquet` | 9,999,756 | token_count == 1 over universe; id, word, and the feature layer's columns |
| `panel-listed` | `data/panel-listed.parquet` | 1,429,181 | panel_count >= 1 |
| `eol-valid` | `data/eol-valid.parquet` | 345,103 | eol == true |
| `spaced` | `data/spaced.parquet` | 294,865 | token_count > 1 |
| `exceptions` | `data/exceptions.parquet` | 236,484 | classes carries any of hyphenated, accented, contraction, apostrophe-form, ligature, diaeresis |

The `exceptions` config holds the rows carrying any of the
6 exception classes of the census (C-005); a
spaced row with such a class is in both `spaced` and `exceptions`.

| File | Bytes | Row-group rows | sha256 |
|---|---:|---:|---|
| `data/universe.parquet` | 167,875,288 | 420,000 | `0336196b54ee2cd93d1bfd01e2bf3a07a35b520a709bafa80eb35f59b50defda` |
| `data/features.parquet` | 381,330,612 | 920,000 | `4541bbea7ef0d7858bec106efdbe6b3a1a526a4434bd0432792a8076bad54ff0` |
| `data/panel-listed.parquet` | 30,444,483 | 350,000 | `13b614bf879d33b4042f9238fd9956e1d7ff1ce5f71f58227c82d0f6cd1e49b1` |
| `data/eol-valid.parquet` | 6,234,316 | 340,000 | `5ac23bf717e3d9936158c3e331948e3e552588b9f5d9f7c2fb8d3a71caa2a7f8` |
| `data/spaced.parquet` | 4,989,113 | 294,865 | `8010583b031d7a7baab25df80463ed4e4495f4070aad229e34b14fdfaa6f7c9c` |
| `data/exceptions.parquet` | 4,850,695 | 236,484 | `9a904087f4ab27036c65c8f6565637e72f8100c8427451ec4d9567d101e6b44f` |

## 5. The columns

The `universe` config carries 45 columns in 5 blocks:
the key, the pin's columns, the release layer, the intake-provenance
layer, and the evidence matrix. The `features` config carries
23: the key and the feature layer's
21 columns. `word` is the join key of every layer;
`id` is the first 16 hexadecimal digits of the sha256 of the word, the
same for the same string in every version.

**2 kinds of NA.** The layers' values are carried unchanged. In the
14 evidence columns a single-token row keeps the
evidence matrix's values: 1 listed, 0 not listed, and -1 where the source
is structurally blind to the row's class (a game list cannot hold a
hyphen; C-010). A spaced row holds null in every evidence column, because
the single-token sources were not measured over spaced rows (C-016).
Everywhere in this dataset, null means not measured by that source,
never false. The feature layer's NaN means the channel does not observe
the string (C-011).

| Column | Type | Meaning | Null |
|---|---|---|---|
| `id` | string | the first 16 hexadecimal digits of the sha256 of the word's UTF-8 bytes; a function of the string alone, so the same string carries the same id in every version | never null |
| `word` | string | the candidate string, the output of the C-001 grammar: lower case, the 50-character charset, spaces single and interior; the join key of every layer | never null |

| Column | Type | Meaning | Null |
|---|---|---|---|
| `eol` | bool | in the EOL's valid list at the pinned revision c1139698: a historical fact at a pin, carried as a covariate, never a CEOL verdict | never null |
| `eol_universe` | bool | in the EOL's pinned candidate universe (its valid or its invalid list); false for the CEOL's own 3 layers | never null |
| `classes` | string | the grammar's non-exclusive class flags joined by ';' (hyphenated, accented, diaeresis, ligature, apostrophe-form, contraction, s-final, spaced); the empty string on a plain-letter string | never null |
| `sources` | string | C-008 provenance at intake: for the CEOL's own layers the sources whose derived sets contain the string, joined by ';'; for the strings inherited from the EOL the dataset-level tag eol_universe@c1139698 (their per-source listedness is the evidence columns') | never null |
| `intake_date` | string | the date the row entered a CEOL artifact: 2026-08-17 the EOL universe at the pinned revision, 2026-08-20 the C1 exceptions and the C-009 audited additions, 2026-08-26 the C-016 spaced candidates | never null |
| `c4_addition` | bool | a row of the audited additions of the C-009 pin | never null |
| `is_restricted` | bool | attested only by NWL2023 or CSW21 (C-009); false on every row of this dataset, because those rows never ship | never null |
| `token_count` | int32 | the number of space-separated tokens (C-015) | never null |
| `c015_addition` | bool | a row of the spaced candidates admitted at C-016 | never null |
| `wn_instance` | bool | WordNet instance-synset membership, a properness signal recorded and never filtered on (C-016) | null unless WordNet attests the row; measured on the spaced layer only; null means not measured, never false |
| `wn_capitalized` | bool | WordNet data-file capitalization, a properness signal | null unless WordNet attests the row; measured on the spaced layer only |
| `wk_proper_noun` | bool | a Wiktionary Proper-noun heading, a properness signal | null unless Wiktionary attests the row; measured on the spaced layer only |
| `wk_flags` | string | Wiktionary's category flags joined by ';' (idiomatic, phrasal-verb, phrasebook, proverb); may be the empty string | null unless Wiktionary attests the row; measured on the spaced layer only |

| Column | Type | Meaning | Null |
|---|---|---|---|
| `class_explicit` | string | the pin's classes with the value 'plain' in place of the empty string; otherwise the flags unchanged | never null |
| `panel_sets` | string | the panel sets that list the row, joined by ';' in the order wordnet, wiktionary_english, web2, web2a, hunspell_en_US, hunspell_en_GB, hunspell_en_CA, hunspell_en_AU, enable1, sowpods_legacy, nwl2023, csw21, scowl; on a single-token row a binary set lists the row where its evidence column is 1 and SCOWL where scowl_tier is above 0; on a spaced row the sets are the pin's sources; the empty string where none lists the row | never null |
| `variety_gb_not_us` | bool | true where hunspell_en_GB is 1 and hunspell_en_US is 0: a proxy for a variety difference between the 2 dictionaries, never a variety label | null where either hunspell column is -1 or null |
| `variety_us_not_gb` | bool | true where hunspell_en_US is 1 and hunspell_en_GB is 0: the reverse proxy | null where either hunspell column is -1 or null |

| Column | Type | Meaning | Null |
|---|---|---|---|
| `intake_layer` | string | the layer the row entered by: eol_valid, eol_invalid, c1_exceptions, c4_additions, spaced_c015 | never null |
| `intake_kind` | string | obtained (an inherited string taken in through a channel), derived (a row of a CEOL layer derived from pinned sources), or generated (made by the EOL's lost synthetic engine) | never null |
| `intake_channels` | string | the first-seen channel labels joined by ';': the EOL's discovery log with its tiers removed, and the CEOL layers' own namespaces census:, audit:, spaced:, ledger:; a record of where a string was first seen, never an attestation (C-064) | never null |
| `eol_phase1_tier` | string | the tier suffix the EOL's labels on the row share: valid, unlikely, or none (C-064 declares mixed for labels that disagree) | never null |
| `eol_record` | string | which EOL dictionary holds the row's entry: valid-dict, invalid-dict, none | never null |
| `eol_synthetic_category` | string | the category recorded on a generated string (a domain label, or the EOL validation step's judgment) | null on every row that is not generated |
| `eol_synthetic_engine_inferred` | string | the engine and rule inferred from a generated string's form (affixation, chemical-variation, greek-plural, medical-scientific-prefixing, unresolved); an inference, so named | null on every row that is not generated |
| `panel_count` | int16 | the number of the 13 panel sets that list the row (the number of names in panel_sets, asserted equal on every row) | never null |
| `gb_type` | bool | the string is a Google Books English 1-gram type in the CEOL re-stream (C-011) | null on spaced rows, which the corpora do not measure |
| `wordfreq_scored` | bool | wordfreq 3.1.1 scores the string | null on spaced rows, which the corpora do not measure |
| `wikt_title_any` | bool | some language's Wiktionary has a page titled with the string: a screen, not containment (C-010) | null on spaced rows |
| `provenance_class` | string | exactly 1 of channel_and_containment, channel_only, containment_only, neither: whether the row has a recorded intake channel and whether a panel set or a corpus contains it | never null |

| Column | Type | Meaning | Null |
|---|---|---|---|
| `wordnet` | int8 | listed by WordNet 3.0's lemmas, re-derived under the CEOL grammar: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `wiktionary_english` | int8 | listed by Wiktionary pages with an English section (the 2026-08-04 dump): 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `web2` | int8 | listed by Webster's Second International (1934), the system word list: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `web2a` | int8 | listed by web2's supplemental list of hyphenated terms and phrases: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `hunspell_en_US` | int8 | listed by the LibreOffice hunspell en_US dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `hunspell_en_GB` | int8 | listed by the LibreOffice hunspell en_GB dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `hunspell_en_CA` | int8 | listed by the LibreOffice hunspell en_CA dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `hunspell_en_AU` | int8 | listed by the LibreOffice hunspell en_AU dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `enable1` | int8 | listed by the ENABLE word list: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `sowpods_legacy` | int8 | listed by the legacy SOWPODS list: 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `nwl2023` | int8 | listed by NASPA Word List 2023 (a restricted source, C-009): 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `csw21` | int8 | listed by Collins Scrabble Words 2021 (a restricted source, C-009): 1 listed, 0 not listed, -1 structurally blind to the row's class (C-010) | null on spaced rows, which the single-token sets were not measured over (C-016) |
| `scowl_tier` | int16 | the SCOWL size tier (10 to 95) of the smallest SCOWL list holding the string; 0 not listed; -1 not applicable to the row's class | null on spaced rows |
| `wikt_title_screen` | int8 | 1 where some language's Wiktionary has a page titled with the string, else 0: a screen, never a detector (C-010) | null on spaced rows |

| Column | Type | Meaning | Null |
|---|---|---|---|
| `orthotactic_logp_total` | float | the log-probability of the string under the C-011 character model (an interpolated order-4 model over the 50-symbol alphabet, trained on the strong-positive pool) | never null |
| `orthotactic_logp_per_char` | float | the same log-probability per character | never null |
| `ocr_neighbor_hits` | int8 | the number of the string's neighbours under the 6 typed OCR confusions that the base reference (WordNet and web2) lists, capped at 127 | never null |
| `ocr_neighbor_freq_ratio` | float | the largest log10 ratio of a neighbour's Google Books match count to the string's (each plus 1) | NaN where the string has no neighbour |
| `ocr_apostrophe_ratio` | float | on a plain string, the largest log10 frequency ratio of an apostrophe restoration a class-capable reference lists (an admitted family) | NaN where no restoration is listed or the string is not plain |
| `ocr_ligature_ratio` | float | on a plain string, the same for a ligature restoration (admitted) | NaN where no restoration is listed or the string is not plain |
| `ocr_hyphen_drop_ratio` | float | on a plain string, the same for a hyphen restoration (admitted) | NaN where no restoration is listed or the string is not plain |
| `ocr_strip_ratio` | float | on a plain string, the same for an accent restoration (a family the C-011 gate rejected; the column exists, flagged inadmissible) | NaN where no restoration is listed or the string is not plain |
| `ocr_hyphen_junction_ratio` | float | on a hyphenated string, the ratio for its junction concatenation (a family the gate rejected; flagged inadmissible) | NaN where none is listed or the string is not hyphenated |
| `morph_productivity_vn` | float | the realized productivity V/N of the productive suffix the string parses to on an attested stem | NaN where the string has no such parse |
| `morph_has_parse` | bool | whether that parse exists | never null |
| `segment_attested_fraction` | float | on a hyphenated string, the fraction of its hyphen-separated segments the base reference lists | NaN on a string that is not hyphenated |
| `gb_year_span` | int16 | the years from the first to the last in which the string occurs in the Google Books English 1-grams (the 2020 release), inclusive | 0 where the string is not a 1-gram type |
| `gb_span_fill` | float | the share of the span's years in which the string occurs | NaN where the string is not a 1-gram type |
| `gb_tokens_per_volume` | float | the total match count over the total volume count | NaN where no volume carries the string |
| `gb_volumes_per_year` | float | the total volume count over the years in which the string occurs | NaN where the string is not a 1-gram type |
| `gb_log10_match` | float | log10 of the total match count | NaN where the string is not a 1-gram type |
| `gb_log10_volume` | float | log10 of the total volume count | NaN where no volume carries the string |
| `zipf_log10_rank` | float | log10 of the string's frequency rank among the aggregate's types | NaN where the string is not a 1-gram type |
| `zipf_resid` | float | log10 of the match count minus the Zipf-Mandelbrot fit's prediction at that rank | NaN where the string is not a 1-gram type |
| `wordfreq_zipf` | float | the wordfreq 3.1.1 Zipf frequency (English) where wordfreq's list holds the string | NaN elsewhere, and on every hyphenated string (C-010: wordfreq is hyphen-blind) |

## 6. The sources, their licenses, and the licence split

The CEOL Universe is licensed CC-BY-SA 4.0, the share-alike floor of its
Wiktionary-derived rows and columns (C-078 line 6). Each source, with the
license the EOL's source manifest records for it:

| Source | License as recorded | What this dataset carries from it |
|---|---|---|
| Wiktionary, English sections and all titles (Wikimedia dumps) | CC-BY-SA-4.0 | `wiktionary_english`, `wikt_title_screen`, `wikt_title_any`, the spaced rows' listing, `wk_proper_noun`, `wk_flags` |
| WordNet 3.0 (Princeton University), as distributed with nltk | WordNet-3.0 | `wordnet`, the spaced rows' listing, `wn_instance`, `wn_capitalized` |
| Webster's Second International (1934), the system word list | public domain (1934) | `web2` |
| web2a, web2's supplemental list of hyphenated terms | not recorded; its README reports the copyright of web2 lapsed | `web2a` |
| LibreOffice hunspell dictionaries en_US, en_GB, en_CA, en_AU | LGPL-2.1-or-later OR MPL-1.1 | the 4 hunspell columns, the variety proxies |
| ENABLE | public domain | `enable1` |
| SOWPODS (a legacy mirror) | freely mirrored | `sowpods_legacy` |
| NASPA Word List 2023 | proprietary (NASPA); not redistributable | `nwl2023` on shippable rows only |
| Collins Scrabble Words 2021 | proprietary (Collins); not redistributable | `csw21` on shippable rows only |
| SCOWL (Kevin Atkinson; the 2020-12-07 archive) | permissive (SCOWL); its copyright and permission notices travel with it | `scowl_tier` |
| wordfreq 3.1.1 (Robyn Speer) | recorded as MIT; the installed package declares Apache-2.0 for its code and CC-BY-SA 4.0 for its data | `wordfreq_zipf`, `wordfreq_scored` |
| Google Books Ngram corpus, English 1-grams, the 2020 release | CC-BY-3.0, aggregates only | the `gb_` columns, `zipf_log10_rank`, `zipf_resid`, `gb_type` |
| The EOL universe at revision `c1139698` | MIT, as its card states | the inherited strings, `eol`, `eol_universe`, the provenance layer's `eol:` channels |

**The licence split (C-009).** NWL2023 and CSW21 are not redistributable.
The 1,985 rows of the pin that only those 2 lists attest are
not in any file of this dataset; the build asserts that none of their
words is in any file. The per-row `nwl2023` and `csw21` columns of the
shippable rows, and the labels that name those lists in `panel_sets`,
`sources`, and `intake_channels`, are carried in this private version;
whether the public version carries them is an open question for the
owner, recorded in `research/release/PACKAGE_UR1.md` §4.5 with the
other license questions (SOWPODS, the notices that must travel with the
public version, web2a's status, and this repository's history).

**Credits.** Wiktionary's contributors; Princeton University for
WordNet; Kevin Atkinson and the contributors named in SCOWL's copyright
notice; the LibreOffice dictionary maintainers; Robyn Speer for wordfreq
(Zenodo, doi:10.5281/zenodo.7199437, the README's recommended citation,
which identifies its record v3.0.2) and, for the SUBTLEX word lists that
wordfreq distributes, Marc Brysbaert and his colleagues, on the 2
conditions the README states: that wordfreq and code derived from it
credit the SUBTLEX authors, and that it remain clear that SUBTLEX is
freely available data (https://crr.ugent.be/programs-data/subtitle-frequencies);
the Google Books Ngram corpus (http://books.google.com/ngrams).

## 7. The intake provenance

**16,373 rows (0.16%) have no recorded intake
channel and no measured containment**: the record does not say how the
string entered the EOL's pool, and neither a panel set nor a corpus
holds it. That count rests on a reading of the EOL's correction ledgers
that labels as generated the forms the EOL demoted; without it the
pin's residual would be 46,185 (C-065). The
intake-provenance layer (C-064) records 2 senses of provenance and
keeps them apart: the intake channel, the route by which a string first
entered the pool (for inherited strings the EOL's discovery log, which is
a record of where a string was first seen and never an attestation), and
the measured containment in the 13 panel sets and the 2
corpora. 828,789 rows have a channel and no containment.
330,386 rows (3.21%) were made by the EOL's
synthetic engine, whose code is lost; each carries `intake_kind`
`generated`, the category the EOL recorded, and an engine inferred from
its form and named as inferred. The layer's report is
`research/provenance/PROVENANCE.md`; its counts are
`research/provenance/provenance.json`.

## 8. How the universe was built and audited

Each step has a committed record in the CEOL repository and a decision
entry; the counts are those records'.

1. **The census** (C1; C-005): the pinned sources re-read under the CEOL
   grammar; 213,867 candidates in the exception classes
   the EOL's letters-only rule could not hold. Record:
   `research/census/census.json`.
2. **The merge** (C2; C-002): the EOL universe at `c1139698`
   (9,653,999 strings) and the census's candidates,
   9,867,866 rows; filtering the merge by the `eol` flag regenerates
   the EOL's pinned lists byte for byte. Record:
   `research/merge/merge.json`.
3. **The audit** (C3): every source's coverage by the merged universe,
   reconciled to a remainder of 0; 133,875 additions. Records:
   `research/audit/audit.json`, `research/audit/reconcile.json`.
4. **The pin** (C-009): 10,001,741 candidates. Record:
   `research/universe/universe.json`.
5. **The spaced admission** (C-015, C-016): 294,865 multiword
   candidates from WordNet and Wiktionary; universe v2, 10,296,606
   rows, reproduces the C-009 pin byte for byte as its single-token
   projection. Records: `research/space_census/space_census.json`,
   `research/universe_v2/universe_v2.json`.
6. **The evidence and feature layers** (C-010, C-011). Records:
   `research/evidence/evidence.json`, `research/features/features.json`.
7. **The intake-provenance layer** (C-064, C-065). Record:
   `research/provenance/provenance.json`.
8. **This release** (C-078). Record:
   `research/release/release_v2.0.json`.

## 9. Limitations

- **8,011,809 single-token rows
  (77.83%) are strings inherited from the
  EOL that are Google Books 1-gram types and that none of the
  13 panel sets lists.** Their only measured
  containment is a corpus built from scanned text, which carries
  recognition errors. In all, 8,763,746 rows are Google Books
  types (8,763,899 over the pin, which counts the restricted rows).
- 845,162 single-token rows are listed by no panel
  set and are in neither corpus.
- 330,386 rows are the output of a lost engine that affixed
  and substituted without a part-of-speech filter (§7).
- The `sources` column has 2 meanings: a per-source containment list on
  the CEOL's own rows, and the dataset-level tag `eol_universe@c1139698`
  on inherited rows, whose per-source listing is the evidence columns'.
- The evidence columns carry 2 kinds of NA (§5), and the corpora do not
  measure multiword rows.
- `eol` is a fact at a single revision of the EOL, which changes daily.

## 10. What the universe does not record

Part of speech (144,512 rows are WordNet-listed and could take
a part of speech from WordNet; v3.0 adds the morphology layer); lemma and inflection
relations (v3.0); definitions and senses (not planned: they move with
their sources and carry license obligations); pronunciation, syllables,
etymology, and a first attestation year (later layers, each by its own
decision); variety and register labels (the 2 variety columns are
proxies); a frequency for most rows (wordfreq scores 303,511);
and validity, by design.

## 11. The relation to the in-the-wild study

The CEOL's in-the-wild programme studies whether a term is attested in
use outside the pinned sources. It samples from the universe, and its
material stays private for the study's life (C-078 line 5): the
development-ledger words and their labels, the synthetic controls (absent
from every pinned universe by construction), the probe batteries, the
pilot words, the human labels, and every model verdict. **No column of
this dataset states a study label or a study verdict**, and the build
asserts that the synthetic controls (20 checked) and
the intake-ledger words not yet pinned (17,113 checked)
are in no file. The model posterior of the C-012 contest is not shipped.
The study's material is released after its confirmatory round closes,
under its own decision entry. The release's date and file hashes are in
its record, so that any later contamination question can be dated.

## 12. Canary

This card carries the canary string `CEOL UNIVERSE CANARY a8d1c96b-4b6e-413c-94a1-a6fa7066f992`. It exists so
that a later test can check whether a model has memorized this dataset's
documentation (C-078 line 4); it is recorded in
`research/release/release_v2.0.json`.

## 13. How to cite

The DOI is minted at the public version. Until then: ryanjosephkamp, *The
CEOL Universe*, version v2.0 (a private rehearsal), Hugging Face
dataset `ryanjosephkamp/ceol-universe`, built 2026-09-26.

## 14. Change log

- **v2.0** (2026-09-26): the first build of the release pipeline,
  over universe v2 (C-016), uploaded to the private dataset (C-078 lines
  3 and 7).
