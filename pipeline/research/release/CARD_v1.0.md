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
- config_name: sample
  data_files:
  - split: candidates
    path: data/sample.parquet
---


# The CEOL Universe, version 1.0

**Release status (November 2, 2026).** This version is not published yet. A license review comes first, and it will be released once the review is finished; no date is promised. This note is removed when it is released.

**Every row is a candidate string, never a verdict.** A row records that a
pinned source lists the string, that the string was inherited from the
English OpenList (EOL) at a pinned revision, or both. No row says that a
string is a word, and no row has been validated. The split is named
`candidates` because that is what every row is.

This card is a datasheet. It states the dataset's limitations first, then
what the dataset is, its version and configs, every column, what this
version withholds and why, its sources and their licenses, how it was built
and checked, what it does not record, a canary, how to cite it, and its
change log. Every figure on it is a row of the card's calculator,
`pipeline/research/release/public_card.py`, computed from the committed
records of the code repository, https://github.com/ryanjosephkamp/ceol-universe. Every record it names is a file of that
repository.

## 1. Limitations

Read these before using the dataset.

- **Most rows rest on a single corpus.** 8,024,536
  single-token rows (80.08%) were inherited
  from the EOL, are listed by none of the 8 published
  panel sets, and are Google Books 1-gram types. For
  7,900,248 of them, Google Books is the only published
  containment, and it is a corpus built from scanned text, which carries
  recognition errors. In all, 8,761,768 rows are Google Books
  types.
- **602,165 single-token rows are listed by no
  published panel set and are in neither corpus.** What supports them is
  their intake channel, where a published one is recorded.
- **16,373 rows (0.16%) have no published intake
  channel and no measured containment.** Nothing published says how the
  string entered the pool, and no published panel set or corpus holds it.
- **330,386 rows (3.30%) were made by the EOL's
  synthetic engine.** Its code does not survive, and its own per-row
  record of the method is empty, but its author describes the methods:
  affixes applied without a part-of-speech filter to the list as it then
  stood (plurals, past tenses, gerunds, agent nouns, comparatives and
  superlatives, and prefixed forms); chemical names varied by substituent,
  and short chains of root, infix, and suffix, made by substitution over a
  hand-written list of substituents and roots, with no tool that derives a
  name from a formula; medical and scientific prefixes; and Greek plurals.
  It gave each base word a domain label, which `eol_synthetic_category`
  carries where it survives, and it used NLTK, lemminflect, and spaCy. `model_or_engine` marks these rows `engine_generated`, and
  each row's method is inferred from its form (§8).
- **137,485 rows of the EOL's valid list were decided with a
  language model:** 131,014 by the EOL's verification pipeline,
  which used one, and 6,471 by a model's verdict alone.
  `model_or_engine` marks them `model_pipeline` and `model_alone` (§12).
  The EOL's invalid list is not marked.
- **The withholding changes what the panel columns count.** The build
  measured 13 panel sets, and 5 of
  them are withheld (§6). `panel_sets`, `panel_count`, and
  `provenance_class` count the 8 published sets
  alone, so a row with `panel_count` 0 may still be listed by a withheld
  list.
- **274,471 rows of the shippable projection are not in this
  version.** Once the withheld lists and channels are taken away, nothing
  published supports them, so they are held back in the private record
  (§6).
- **A channel may be withheld for license reasons.** 210,109
  rows carry `eol:channel-withheld` in `intake_channels`: every channel
  recorded for them is withheld, because it names a withheld list or a
  source whose terms do not allow publishing the label.
- **12 of the feature layer's columns are
  withheld,** because each was computed against a reference that holds a
  withheld list, or by a character model fitted on strings the withheld
  lists help choose (§6).
- **The `sources` column has 2 meanings:** a per-source containment list
  on the CEOL's own rows, and the dataset-level tag `eol_universe@c1139698`
  on inherited rows, whose per-source listing is the evidence columns'.
- **Null and NaN mean different things** (§5), and the corpora do not
  measure multiword rows.
- **`eol` is a fact at a single revision of the EOL,** `c1139698`. The
  EOL's last published list adds 59 entries made
  after that revision; they are rows of this dataset with `eol` false.

## 2. What this dataset is

The CEOL Universe is an inventory of candidate English strings, each with
its provenance: which pinned sources list it, how it entered the pool, and
its corpus features. It is a frame from which anyone can derive a word
list under a definition of their own. Its strings are the output of an
executable grammar (`pipeline/ceol/grammar.py`) that admits hyphenated
compounds, accented loanwords, contractions, apostrophe forms, ligature and
diaeresis spellings, and multiword terms. This version holds
10,020,150 rows, 1 per string.

The family of datasets has 3 kinds of member:

- **The EOL** (`ryanjosephkamp/english-openlist`): an English word list
  under its own grammar and governance. The universe reads it at a pinned
  revision and never writes to it. Its public dataset is this dataset's
  `eol-valid` config: the 344,713 rows of its list at that
  revision that this version ships.
- **The CEOL Universe** (this dataset, `ryanjosephkamp/ceol-universe`): the candidate
  inventory, versioned as its pins are.
- **Derived datasets,** each built from a version of the universe under
  its own rule, with its own name (`ceol-<rule>-<version>`) and its own
  card.

## 3. The version and the pin

Version 1.0 is the first public version of the CEOL Universe.
It is a projection of the pin, 10,296,606 candidates
(`pipeline/research/universe_v2/universe_v2.json`). 1,985 of
them are restricted, attested only by 2 lists whose terms forbid
redistribution, and are in no version. The other 10,294,621 are
shippable. The public projection holds back 274,471 of those
(§6) and ships 10,020,150.

The release was built on October 25, 2026 by
`pipeline/research/release/build_release.py`, at commit `6891bff41ef0`.
The build verifies every pinned layer's sha256 against its committed
record before reading it, writes the files, re-reads them, and asserts the
properties this card states before anything is kept. The record of the
build, with every file's rows, columns, bytes, and sha256 and the
assertions' counts, is `pipeline/research/release/release_v1.0.json`.
A later version is built the same way, and its card's change log (§16)
states what changed.

| Layer | sha256 | Committed record |
|---|---|---|
| pin (`data/universe_v2.parquet`) | `adaa1232b6bc4d9ead97f5e19a005b264bb6db8db77b6374fe66cdd1d2aca9dd` | `research/universe_v2/universe_v2.json`, `artifacts.universe_v2_parquet_sha256` |
| provenance (`data/universe_v2_provenance.parquet`) | `7c9dc6284bf6393769eec3b26c27b8c77fa68dcf08cb5ef77148c2b7f07bec1b` | `research/provenance/provenance.json`, `artifact.sha256` |
| evidence (`data/evidence.parquet`) | `e4c86cc4a0caf3f01996e0abb50cedfd525ee7e08183679f154884bf7250d6ee` | `research/evidence/evidence.json`, `artifacts.evidence_parquet_sha256` |
| features (`data/features.parquet`) | `c578289b61d7b957bba1c91b9e65d3dbfcde3c5d74098316f6993643f240b7c7` | `research/provenance/provenance.json`, `inputs.features_parquet_sha256` |
| model_basis (`data/eol_valid_model_basis.parquet`) | `4395526a55acb7a2464fd6439984f478889bf65e419f41eeed272d168eb43ce0` | `research/provenance/model_basis.json`, `artifact.sha256` |

## 4. The configs

The default config, `universe`, holds every row of this version. `features`
holds the feature layer's values for the single-token rows; it is a
separate table, not a filter of `universe`. `universe` is the pin's
unrestricted rows less the 274,471 rows held back (§6), in the public
columns. The other 5 configs are filters of `universe`, with every
column of `universe` and its row order; each is the filter of `universe` by its
predicate and nothing else, which the build asserts on the written files.

| Config | File on the hub | Rows | Predicate |
|---|---|---:|---|
| `universe` | `data/universe.parquet` | 10,020,150 | the pin's unrestricted rows, less the rows held back (card §6), in the public columns |
| `features` | `data/features.parquet` | 9,725,285 | token_count == 1 over universe; id, word, and the feature layer's columns |
| `panel-listed` | `data/panel-listed.parquet` | 1,384,833 | panel_count >= 1 |
| `eol-valid` | `data/eol-valid.parquet` | 344,713 | eol == true |
| `spaced` | `data/spaced.parquet` | 294,865 | token_count > 1 |
| `exceptions` | `data/exceptions.parquet` | 209,883 | classes carries any of hyphenated, accented, contraction, apostrophe-form, ligature, diaeresis |
| `sample` | `data/sample.parquet` | 38,988 | id starts with '00' (about 1 row in 256) |

The `exceptions` config holds the rows carrying any of the
6 exception classes of the census
(`reference/research/census/census.json`); a spaced row with such a class
is in both `spaced` and `exceptions`. The `sample` config holds the rows
whose `id` begins with `00`, 38,988 rows for a
quick look. Because `id` is a function of the string alone, the sample
holds the same strings in every version that holds them.

| File | Bytes | Row-group rows | sha256 |
|---|---:|---:|---|
| `data/universe.parquet` | 158,978,290 | 420,000 | `d30db2c351c6941edafb7d7dbeeadedd8d12bd8c4975350d0a5cf8890f42c7ce` |
| `data/features.parquet` | 288,074,901 | 1,490,000 | `d3e08959f67bf654f8ec3ac631fb181218fcc26136f9a1f425c790c80a38b4c9` |
| `data/panel-listed.parquet` | 27,741,529 | 360,000 | `fdf181a22b03e696d5c7cac4a5b2af34d16f686dc13bd6aad6744bc6751de79f` |
| `data/eol-valid.parquet` | 6,115,642 | 344,713 | `a371578f30aec90015f8254327fef5daf0a90e7da31e79fc9500cd2414b37408` |
| `data/spaced.parquet` | 4,988,532 | 294,865 | `0a25533c65285531d2d0bf332e1d4ce5cd2c5fcc33486df35e7f15d910f591df` |
| `data/exceptions.parquet` | 4,226,501 | 209,883 | `ad0487b18644914f8f32fb1386e6ece38c9c677a39dc428b84d08e1c15628f28` |
| `data/sample.parquet` | 839,937 | 38,988 | `302f02419f1accedd6d16d851d325b78ff001f9d3f70b48af652f64130dace28` |
| `NOTICES.md` | 27,196 | | `15fe576c9c6a34ac6387e0f1360cc41668787ffa4236e4e6d76d77b9b21b0e95` |

## 5. The columns

The `universe` config carries 41 columns: the key, the
pin's columns, the release layer, the intake-provenance layer, the
evidence matrix, and `model_or_engine`. The `features` config carries
11: the key and 9 columns of
the feature layer. `word` is the join key of every config; `id` is the
first 16 hexadecimal digits of the sha256 of the word, the same for the
same string in every version. The data dictionary,
`docs/DATA_DICTIONARY.md` in the code repository, is generated from the
same module as these tables.

**Null and NaN.** The layers' values are carried unchanged. In the
9 evidence columns a single-token row keeps the evidence
matrix's values: 1 listed, 0 not listed, and -1 where the source is
structurally blind to the row's class (a list without hyphens cannot hold
a hyphenated string). A spaced row holds null in every evidence column,
because the single-token sources were not measured over spaced rows.
Everywhere in this dataset, null means not measured by that source, never
false. The feature layer's NaN means the channel does not observe the
string.

**The key**

| Column | Type | Meaning | Null |
|---|---|---|---|
| `id` | string | the first 16 hexadecimal digits of the sha256 of the word's UTF-8 bytes; a function of the string alone, so the same string carries the same id in every version | never null |
| `word` | string | the candidate string, the output of the grammar: lower case, the 50-character charset, spaces single and interior; the join key of every layer | never null |

**The pin's columns**

| Column | Type | Meaning | Null |
|---|---|---|---|
| `eol` | bool | in the EOL's valid list at the pinned revision c1139698: a historical fact at a pin, carried as a covariate, never a CEOL verdict | never null |
| `eol_universe` | bool | in the EOL's pinned candidate universe (its valid or its invalid list); false for the CEOL's own 3 layers | never null |
| `classes` | string | the grammar's non-exclusive class flags joined by ';' (hyphenated, accented, diaeresis, ligature, apostrophe-form, contraction, s-final, spaced); the empty string on a plain-letter string | never null |
| `sources` | string | provenance at intake: for the CEOL's own layers the published sources whose derived sets contain the string, joined by ';', a withheld list's label removed (the empty string where each such source is withheld); for the strings inherited from the EOL the dataset-level tag eol_universe@c1139698 (their per-source listedness is the evidence columns') | never null |
| `intake_date` | string | the date the row entered a CEOL artifact (an ISO date): August 17, 2026 the EOL universe at the pinned revision, August 20, 2026 the census's exception candidates and the audit's additions, August 26, 2026 the spaced admission's multiword candidates | never null |
| `c4_addition` | bool | a row of the audit's additions to the single-token pin | never null |
| `is_restricted` | bool | attested only by NWL2023 or CSW21; false on every row of this dataset, because those rows never ship | never null |
| `token_count` | int32 | the number of space-separated tokens | never null |
| `c015_addition` | bool | a row of the multiword candidates of the spaced admission | never null |
| `wn_instance` | bool | WordNet instance-synset membership, a properness signal recorded and never filtered on | null unless WordNet attests the row; measured on the spaced layer only; null means not measured, never false |
| `wn_capitalized` | bool | WordNet data-file capitalization, a properness signal | null unless WordNet attests the row; measured on the spaced layer only |
| `wk_proper_noun` | bool | a Wiktionary Proper-noun heading, a properness signal | null unless Wiktionary attests the row; measured on the spaced layer only |
| `wk_flags` | string | Wiktionary's category flags joined by ';' (idiomatic, phrasal-verb, phrasebook, proverb); may be the empty string | null unless Wiktionary attests the row; measured on the spaced layer only |

**The release layer**

| Column | Type | Meaning | Null |
|---|---|---|---|
| `class_explicit` | string | the pin's classes with the value 'plain' in place of the empty string; otherwise the flags unchanged | never null |
| `panel_sets` | string | the published panel sets that list the row, joined by ';' in the order wordnet, wiktionary_english, hunspell_en_US, hunspell_en_GB, hunspell_en_CA, hunspell_en_AU, enable1, scowl; on a single-token row a binary set lists the row where its evidence column is 1 and SCOWL where scowl_tier is above 0; on a spaced row the sets are the pin's published sources; the empty string where none lists the row. A withheld list is never named | never null |
| `variety_gb_not_us` | bool | true where hunspell_en_GB is 1 and hunspell_en_US is 0: a proxy for a variety difference between the 2 dictionaries, never a variety label | null where either hunspell column is -1 or null |
| `variety_us_not_gb` | bool | true where hunspell_en_US is 1 and hunspell_en_GB is 0: the reverse proxy | null where either hunspell column is -1 or null |

**The intake-provenance layer** (`pipeline/research/provenance/provenance.json`)

| Column | Type | Meaning | Null |
|---|---|---|---|
| `intake_layer` | string | the layer the row entered by: eol_valid, eol_invalid, c1_exceptions, c4_additions, spaced_c015 | never null |
| `intake_kind` | string | obtained (an inherited string taken in through a channel), derived (a row of a CEOL layer derived from pinned sources), or generated (made by the EOL's lost synthetic engine) | never null |
| `intake_channels` | string | the first-seen channel labels joined by ';': the EOL's discovery log with its tiers removed, and the CEOL layers' own namespaces census:, audit:, spaced:, ledger:; a record of where a string was first seen, never an attestation. A label naming a withheld list is removed, and so is a channel withheld for license reasons; a row whose every label was withheld carries the single label eol:channel-withheld | never null |
| `eol_phase1_tier` | string | the tier suffix the EOL's labels on the row share: valid, unlikely, or none (mixed where the labels disagree) | never null |
| `eol_record` | string | which EOL dictionary holds the row's entry: valid-dict, invalid-dict, none | never null |
| `eol_synthetic_category` | string | the category recorded on a generated string (a domain label, or the EOL validation step's judgment) | null on every row that is not generated |
| `eol_synthetic_engine_inferred` | string | the engine and rule inferred from a generated string's form (affixation, chemical-variation, greek-plural, medical-scientific-prefixing, unresolved); an inference, so named | null on every row that is not generated |
| `panel_count` | int16 | the number of the 8 published panel sets that list the row (the number of names in panel_sets, asserted equal on every row); a withheld list's listing is not counted | never null |
| `gb_type` | bool | the string is a Google Books English 1-gram type in the CEOL re-stream | null on spaced rows, which the corpora do not measure |
| `wordfreq_scored` | bool | wordfreq 3.1.1 scores the string | null on spaced rows, which the corpora do not measure |
| `wikt_title_any` | bool | some language's Wiktionary has a page titled with the string: a screen, not containment | null on spaced rows |
| `provenance_class` | string | exactly 1 of channel_and_containment, channel_only, containment_only, neither, over the published fields: whether the row has a published intake channel (a label other than eol:phase1-unrecorded and eol:channel-withheld) and whether a published panel set or a corpus contains it | never null |

**The evidence matrix** (`pipeline/research/evidence/evidence.json`)

| Column | Type | Meaning | Null |
|---|---|---|---|
| `wordnet` | int8 | listed by WordNet 3.0's lemmas, re-derived under the CEOL grammar: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `wiktionary_english` | int8 | listed by Wiktionary pages with an English section (the August 4, 2026 dump): 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `hunspell_en_US` | int8 | listed by the LibreOffice hunspell en_US dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `hunspell_en_GB` | int8 | listed by the LibreOffice hunspell en_GB dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `hunspell_en_CA` | int8 | listed by the LibreOffice hunspell en_CA dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `hunspell_en_AU` | int8 | listed by the LibreOffice hunspell en_AU dictionary, expanded: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `enable1` | int8 | listed by the ENABLE word list: 1 listed, 0 not listed, -1 structurally blind to the row's class | null on spaced rows, which the single-token sets were not measured over |
| `scowl_tier` | int16 | the SCOWL size tier (10 to 95) of the smallest SCOWL list holding the string; 0 not listed; -1 not applicable to the row's class | null on spaced rows |
| `wikt_title_screen` | int8 | 1 where some language's Wiktionary has a page titled with the string, else 0: a screen, never a detector | null on spaced rows |

**Model and engine**

| Column | Type | Meaning | Null |
|---|---|---|---|
| `model_or_engine` | string | engine_generated on a row the EOL's synthetic engine made (intake_kind generated); on a row of the EOL's valid list, model_pipeline where the EOL listed it through its verification pipeline, which used a language model, and model_alone where a language model's verdict is its only basis; none on every other row. A record of how the EOL decided, never a verdict of this dataset's; the EOL's invalid list is not marked | never null |

**The feature layer, the `features` config** (`pipeline/research/features/features.json`)

| Column | Type | Meaning | Null |
|---|---|---|---|
| `id` | string | the first 16 hexadecimal digits of the sha256 of the word's UTF-8 bytes; a function of the string alone, so the same string carries the same id in every version | never null |
| `word` | string | the candidate string, the output of the grammar: lower case, the 50-character charset, spaces single and interior; the join key of every layer | never null |
| `gb_year_span` | int16 | the years from the first to the last in which the string occurs in the Google Books English 1-grams (the 2020 release), inclusive | 0 where the string is not a 1-gram type |
| `gb_span_fill` | float | the share of the span's years in which the string occurs | NaN where the string is not a 1-gram type |
| `gb_tokens_per_volume` | float | the total match count over the total volume count | NaN where no volume carries the string |
| `gb_volumes_per_year` | float | the total volume count over the years in which the string occurs | NaN where the string is not a 1-gram type |
| `gb_log10_match` | float | log10 of the total match count | NaN where the string is not a 1-gram type |
| `gb_log10_volume` | float | log10 of the total volume count | NaN where no volume carries the string |
| `zipf_log10_rank` | float | log10 of the string's frequency rank among the aggregate's types | NaN where the string is not a 1-gram type |
| `zipf_resid` | float | log10 of the match count minus the Zipf-Mandelbrot fit's prediction at that rank | NaN where the string is not a 1-gram type |
| `wordfreq_zipf` | float | the wordfreq 3.1.1 Zipf frequency (English) where wordfreq's list holds the string | NaN elsewhere, and on every hyphenated string (wordfreq is hyphen-blind) |

## 6. What this version withholds, and why

Each source's terms were read at its primary source for this version; the
readings are not legal advice, and the author ruled on them. §7 states each source's
terms, and `NOTICES.md` carries the notices.

- **5 lists whose membership may not be published:**
  NASPA Word List 2023 and Collins Scrabble Words 2021, which are
  proprietary; the legacy SOWPODS list, for which no license was found;
  and Webster's Second International and its supplement of hyphenated
  terms (`web2`, `web2a`), whose 1961 copyright renewal holds. Their
  columns (`nwl2023`, `csw21`, `sowpods_legacy`, `web2`, `web2a`) are absent, and every label naming them is
  removed from `sources`, `intake_channels`, and `panel_sets`. Their rows
  still ship wherever published evidence supports them. The Webster's
  Second columns can return in a version built on or after
  January 1, 2030.
- **Channel labels withheld for license reasons.** Some intake channels
  name a source whose terms do not allow publishing the label. The label
  is removed; a row whose every label was withheld carries the single
  label `eol:channel-withheld`.
- **12 feature columns,** in 2 groups
  (`docs/licenses/FEATURE_COLUMNS.md` in the code repository):
  - 10 computed against a reference that
    holds `web2` or `web2a`: `ocr_neighbor_hits`, `ocr_neighbor_freq_ratio`, `ocr_apostrophe_ratio`, `ocr_ligature_ratio`, `ocr_hyphen_drop_ratio`, `ocr_strip_ratio`, `ocr_hyphen_junction_ratio`, `morph_productivity_vn`, `morph_has_parse`, `segment_attested_fraction`. A value could
    reveal whether a withheld list holds a string's neighbor, stem, or
    segments.
  - 2 from the layer's character model:
    `orthotactic_logp_total`, `orthotactic_logp_per_char`. The model was fitted on strings that at
    least 2/3 of their applicable panel sets list, the withheld lists
    among them. A test compared it with the same model fitted on the
    published lists alone: the difference between the two picks out the
    strings the withheld lists list, well above chance.

  They return in a later version once each is recomputed without the
  withheld lists.
- **The rows left with no public evidence.** 27,661 rows were
  listed only by withheld lists and keep no published channel or corpus
  containment; 244,252 rows had a withheld channel as
  their only evidence. Both are held back in the private record with the
  decision as the reason. Those that Webster's Second listed return
  with its columns; those whose only evidence was a withheld channel
  return if that channel's terms are found to allow it, or when a
  published source lists them.
- **The CEOL's own rows whose every source is withheld.**
  2,558 rows of the census and the audit's additions
  have every `sources` label naming a withheld list. Shipped, their empty
  `sources` would say that a withheld list holds them, so they are held back
  the same way, though they keep corpus containment.

The rows held back, 274,471 in all, by reason. They are counted
and never listed.

| Why the row is held back | Rows |
|---|---:|
| every listing a withheld list, and no public evidence left | 27,661 |
| a withheld channel label its only evidence | 244,252 |
| a census or audit row whose every source is a withheld list | 2,558 |

`panel_sets`, `panel_count`, and `provenance_class` are recomputed over
the published fields, so no published field reveals a withheld list's
membership. The counts on this card that concern the withheld lists are
aggregates of 10 rows or more, under the rules of the report's appendix
of aggregate counts.

The measurement records committed under `pipeline/research/` (the evidence,
provenance, and profile records, and the census of the archival folder) are
kept exact because the figure check re-derives each of them from the layers.
For a single withheld list a few of their cells are below 10; each is a count
of rows by class or channel, and none names a string.

## 7. The sources, their licenses, and the credits

The CEOL Universe is licensed CC BY-SA 4.0, the share-alike floor of its
Wiktionary-derived fields. `NOTICES.md`, beside the data files, carries
every notice, license, and credit the sources require, in their own words
where their terms require the text itself, and each Parquet file names it
in its metadata.

The 2nd column is the license the EOL's source manifest records; the 3rd
is what the source's own files state, as the license review read them.

| Source | Recorded | What its own files state | What this dataset carries from it |
|---|---|---|---|
| Wiktionary, English sections and all titles (Wikimedia dumps) | CC-BY-SA-4.0 | CC BY-SA 4.0 and the GFDL, under the Wikimedia Terms of Use | `wiktionary_english`, `wikt_title_screen`, `wikt_title_any`, the spaced rows' listing, `wk_proper_noun`, `wk_flags` |
| WordNet 3.0 (Princeton University), as distributed with nltk | WordNet-3.0 | the WordNet 3.0 license, which `NOTICES.md` carries verbatim | `wordnet`, the spaced rows' listing, `wn_instance`, `wn_capitalized` |
| SCOWL (Kevin Atkinson; the December 7, 2020 archive) | permissive (SCOWL) | SCOWL's `Copyright` file, with its components' notices, which `NOTICES.md` carries verbatim | `scowl_tier` |
| LibreOffice hunspell dictionaries en_US, en_CA, en_AU | LGPL-2.1-or-later OR MPL-1.1 | their READMEs: they "come directly from SCOWL and is thus under the same copyright of SCOWL" | `hunspell_en_US`, `hunspell_en_CA`, `hunspell_en_AU`, the variety proxies |
| LibreOffice hunspell dictionary en_GB | LGPL-2.1-or-later OR MPL-1.1 | its README: begun from Kevin Atkinson's list and covered by his original LGPL license, since extensively updated by others; its credits include OpenStreetMap's contributors | `hunspell_en_GB`, the variety proxies |
| ENABLE (Alan Beale and M. Cooper) | public domain | its public-domain statement | `enable1` |
| wordfreq 3.1.1 (Robyn Speer) | MIT | its README: the code under the Apache license, and data files that may be redistributed under CC BY-SA 4.0 | `wordfreq_zipf`, `wordfreq_scored` |
| Google Books Ngram corpus, English 1-grams, the 2020 release | CC-BY-3.0, aggregates only | its export page: a Creative Commons Attribution 3.0 Unported License | the `gb_` columns, `zipf_log10_rank`, `zipf_resid`, `gb_type` |
| The EOL universe at revision `c1139698` | MIT | its card: the MIT License | the inherited strings, `eol`, `eol_universe`, the provenance layer's `eol:` channels |

**Word-game material in 2 published lists.** ENABLE's README says it
reflects the changes to the Official Scrabble Players Dictionary in effect
from January 1, 1998, and SCOWL's lists at size 80 and above include the
lists of the ENABLE supplement package, which SCOWL's successor documents
as holding additional and stale entries of that dictionary. Both lists'
own terms allow the use this dataset makes of them, so `enable1` and
`scowl_tier` are published. Where they agree with a withheld game
list, the agreement is not independent evidence; a filter can leave out
ENABLE and SCOWL's sizes 80 and above to count without them.

**Credits.** Wiktionary's contributors, and the Free Dictionary API, which
draws on Wiktionary; Princeton University for WordNet; Kevin Atkinson and
the contributors named in SCOWL's copyright notice; the LibreOffice
dictionary maintainers, among them Marco A.G. Pinto for en_GB; Alan Beale
and M. Cooper for ENABLE; Robyn Speer for wordfreq (Zenodo,
doi:10.5281/zenodo.7199437); the Google Books Ngram corpus
(https://books.google.com/ngrams). wordfreq's data includes the SUBTLEX
word lists of Marc Brysbaert and his colleagues, which wordfreq
distributes by the authors' permission on 2 conditions: that wordfreq and
code derived from it credit the SUBTLEX authors, and that it remain clear
that SUBTLEX is freely available data. The page wordfreq's README names is
no longer served; its last capture by the Internet Archive is of November
16, 2023
(https://web.archive.org/web/20231116144719/http://crr.ugent.be/programs-data/subtitle-frequencies).
SUBTLEX-US is offered on Ghent University's pages
(https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus)
and SUBTLEX-UK on OSF (https://osf.io/zq49t/). The authors' current copies
carry the license CC BY-NC-SA 4.0; this dataset's values come through
wordfreq 3.1.1, under wordfreq's statement of the permission.

## 8. The intake provenance

The intake-provenance layer (`pipeline/research/provenance/provenance.json`)
records 2 senses of provenance and keeps them apart: the intake channel,
the route by which a string first entered the pool (for inherited strings,
the EOL's discovery log, which records where a string was first seen and is
never an attestation), and the measured containment in the published panel
sets and the 2 corpora. Over the published fields,
8,920,645 rows have both, 585,792 a
channel and no containment, 497,340 containment and no
channel, and 16,373 neither. The count of the last rests on a
reading of the EOL's correction ledgers that labels as generated the forms
the EOL demoted, which the same record states. 330,386 rows were
made by the EOL's synthetic engine; each carries `intake_kind`
`generated`, the category the EOL recorded, and an engine inferred from
its form and named as inferred.

## 9. How the universe was built and checked

Each step has a committed record; the counts are those records'.

1. **The census** (`reference/research/census/census.json`): the pinned
   sources re-read under the grammar; 213,867 candidates in
   the exception classes the EOL's letters-only rule could not hold.
2. **The merge** (`reference/research/merge/merge.json`): the EOL universe
   at `c1139698` (9,653,999 strings) and the census's
   candidates, 9,867,866 rows; filtering the merge by the `eol` flag
   regenerates the EOL's pinned lists byte for byte.
3. **The audit** (`reference/research/audit/reconcile.json`): every
   source's coverage by the merged universe, reconciled to a remainder of
   0; 133,875 additions.
4. **The single-token pin** (`reference/research/universe/universe.json`):
   10,001,741 candidates.
5. **The spaced admission** (`pipeline/research/universe_v2/universe_v2.json`):
   294,865 multiword candidates from WordNet and Wiktionary. The pin,
   10,296,606 rows, reproduces the single-token pin byte for byte as its
   single-token projection.
6. **The evidence and feature layers** (`pipeline/research/evidence/evidence.json`,
   `pipeline/research/features/features.json`).
7. **The intake-provenance layer** (`pipeline/research/provenance/provenance.json`).
8. **The model-and-engine column:** derived from the EOL's valid
   dictionary at the pin (345,103 entries) by
   `pipeline/research/provenance/model_basis.py`.
9. **This release:** the public projection and the build.
   The build asserted, on each of its 7 written files,
   that none of the 1,985 restricted rows' strings is
   present, that every id is distinct, that each filter config is its
   predicate's filter, that no withheld column or label is present, that
   no held-back row is present, and that `provenance_class` and
   `model_or_engine` re-derive from the file's own fields.

## 10. What the universe does not record

Part of speech (143,924 rows are WordNet-listed and could take a
part of speech from WordNet); lemma and inflection relations; definitions
and senses (they move with their sources and carry license obligations);
pronunciation, syllables, etymology, and a first attestation year; variety
and register labels (the 2 variety columns are proxies); a frequency drawn
from many kinds of text for most rows (wordfreq scores 303,511;
the Google Books counts cover 8,761,768 rows, but from scanned books
alone); and validity, by design.
The next major version plans parts of speech, lemma and inflection
relations, and WordNet's categories.

## 11. The relation to the in-the-wild study

The project publishes a study design, the in-the-wild study, as a proposal
and a worked example; the study has not been run. Its material stays
private: the development ledger, the synthetic controls, the probe
batteries, the pilot's items, and every label and verdict. **No column of
this dataset states a study label or a study verdict,** and the build
asserts that none of the synthetic controls and none of the intake
ledger's strings outside the pin is in any file. The release's date and
file hashes are in its record, so that a later question of contamination
can be dated.

## 12. Language models and this dataset

No language model decided any row the CEOL added: the census, the audit,
and the spaced admission follow the grammar and the pinned sources, and
every figure on this card is computed by committed code from committed
records. The feature layer's character model (§6) is an interpolated
character n-gram model, not a language model.

The EOL decided some rows of its valid list with a language model. Its
valid dictionary names the model on each of those entries: Google Gemini 3
Flash Preview, through its verification pipeline or by the model's verdict
alone. The EOL's own report says the earlier phases of its pipeline used
Gemini 2.0 Flash and Gemini 2.5 Flash. `model_or_engine` marks these rows
(§1, §5), so a list can keep them or leave them out.

## 13. Requests and takedowns

A request to withhold, correct, or restore a source or a row goes to
ryanjosephkamp@gmail.com; the hub's own copyright process also reaches the
dataset. A request is acknowledged within 7 days
and acted on within 14 days of its verification, and each version's change
log records every withholding, as counts (`docs/UPKEEP.md` §7 in the code
repository).

## 14. Canary

This card carries the canary string `CEOL UNIVERSE CANARY a8d1c96b-4b6e-413c-94a1-a6fa7066f992`. It exists so that a
later test can check whether a model has memorized this dataset's
documentation. It is recorded in the release record and in each Parquet
file's metadata.

## 15. How to cite

`CITATION.cff` in the code repository gives the citation. The DOI is
minted at the release. Until then: Ryan Kamp, *The CEOL Universe*,
version 1.0, Hugging Face dataset `ryanjosephkamp/ceol-universe`, built
October 25, 2026.

## 16. Change log

- **1.0** (October 25, 2026): the first public version.
  10,020,150 rows in 7 configs, with the withholding
  of §6, `NOTICES.md`, and the canary, the license, and the attribution
  in each Parquet file's metadata.
