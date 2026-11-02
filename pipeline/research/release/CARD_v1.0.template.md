---
license: cc-by-sa-4.0
pretty_name: CEOL Universe
language:
- en
size_categories:
- {{size_category}}
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


# The CEOL Universe, version {{version_name}}

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
records of the code repository, {{code_repository}}. Every record it names is a file of that
repository.

## 1. Limitations

Read these before using the dataset.

- **Most rows rest on a single corpus.** {{limit_gb_inherited_no_panel}}
  single-token rows ({{limit_gb_inherited_no_panel_pct}}) were inherited
  from the EOL, are listed by none of the {{published_set_count}} published
  panel sets, and are Google Books 1-gram types. For
  {{limit_gb_only}} of them, Google Books is the only published
  containment, and it is a corpus built from scanned text, which carries
  recognition errors. In all, {{limit_gb_all}} rows are Google Books
  types.
- **{{limit_no_panel_no_corpus}} single-token rows are listed by no
  published panel set and are in neither corpus.** What supports them is
  their intake channel, where a published one is recorded.
- **{{prov_neither}} rows ({{prov_neither_pct}}) have no published intake
  channel and no measured containment.** Nothing published says how the
  string entered the pool, and no published panel set or corpus holds it.
- **{{generated_rows}} rows ({{generated_pct}}) were made by the EOL's
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
- **{{model_rows}} rows of the EOL's valid list were decided with a
  language model:** {{model_pipeline}} by the EOL's verification pipeline,
  which used one, and {{model_alone}} by a model's verdict alone.
  `model_or_engine` marks them `model_pipeline` and `model_alone` (§12).
  The EOL's invalid list is not marked.
- **The withholding changes what the panel columns count.** The build
  measured {{panel_set_count}} panel sets, and {{withheld_list_count}} of
  them are withheld (§6). `panel_sets`, `panel_count`, and
  `provenance_class` count the {{published_set_count}} published sets
  alone, so a row with `panel_count` 0 may still be listed by a withheld
  list.
- **{{held_back_rows}} rows of the shippable projection are not in this
  version.** Once the withheld lists and channels are taken away, nothing
  published supports them, so they are held back in the private record
  (§6).
- **A channel may be withheld for license reasons.** {{channel_withheld_rows}}
  rows carry `{{channel_withheld_label}}` in `intake_channels`: every channel
  recorded for them is withheld, because it names a withheld list or a
  source whose terms do not allow publishing the label.
- **{{withheld_feature_count}} of the feature layer's columns are
  withheld,** because each was computed against a reference that holds a
  withheld list, or by a character model fitted on strings the withheld
  lists help choose (§6).
- **The `sources` column has 2 meanings:** a per-source containment list
  on the CEOL's own rows, and the dataset-level tag `eol_universe@c1139698`
  on inherited rows, whose per-source listing is the evidence columns'.
- **Null and NaN mean different things** (§5), and the corpora do not
  measure multiword rows.
- **`eol` is a fact at a single revision of the EOL,** `c1139698`. The
  EOL's last published list adds {{eol_added_after_pin}} entries made
  after that revision; they are rows of this dataset with `eol` false.

## 2. What this dataset is

The CEOL Universe is an inventory of candidate English strings, each with
its provenance: which pinned sources list it, how it entered the pool, and
its corpus features. It is a frame from which anyone can derive a word
list under a definition of their own. Its strings are the output of an
executable grammar (`pipeline/ceol/grammar.py`) that admits hyphenated
compounds, accented loanwords, contractions, apostrophe forms, ligature and
diaeresis spellings, and multiword terms. This version holds
{{rows_universe}} rows, 1 per string.

The family of datasets has 3 kinds of member:

- **The EOL** (`ryanjosephkamp/english-openlist`): an English word list
  under its own grammar and governance. The universe reads it at a pinned
  revision and never writes to it. Its public dataset is this dataset's
  `eol-valid` config: the {{rows_eol_valid}} rows of its list at that
  revision that this version ships.
- **The CEOL Universe** (this dataset, `{{dataset}}`): the candidate
  inventory, versioned as its pins are.
- **Derived datasets,** each built from a version of the universe under
  its own rule, with its own name (`ceol-<rule>-<version>`) and its own
  card.

## 3. The version and the pin

Version {{version_name}} is the first public version of the CEOL Universe.
It is a projection of the pin, {{rows_pin}} candidates
(`pipeline/research/universe_v2/universe_v2.json`). {{rows_restricted}} of
them are restricted, attested only by 2 lists whose terms forbid
redistribution, and are in no version. The other {{rows_shippable}} are
shippable. The public projection holds back {{held_back_rows}} of those
(§6) and ships {{rows_universe}}.

The release was built on {{built_on}} by
`pipeline/research/release/build_release.py`, at commit `{{code_commit}}`.
The build verifies every pinned layer's sha256 against its committed
record before reading it, writes the files, re-reads them, and asserts the
properties this card states before anything is kept. The record of the
build, with every file's rows, columns, bytes, and sha256 and the
assertions' counts, is `pipeline/research/release/release_{{version}}.json`.
A later version is built the same way, and its card's change log (§16)
states what changed.

{{table:sources}}

## 4. The configs

The default config, `universe`, holds every row of this version. `features`
holds the feature layer's values for the single-token rows; it is a
separate table, not a filter of `universe`. `universe` is the pin's
unrestricted rows less the {{held_back_rows}} rows held back (§6), in the public
columns. The other {{filter_count}} configs are filters of `universe`, with every
column of `universe` and its row order; each is the filter of `universe` by its
predicate and nothing else, which the build asserts on the written files.

{{table:configs}}

The `exceptions` config holds the rows carrying any of the
{{exception_class_count}} exception classes of the census
(`reference/research/census/census.json`); a spaced row with such a class
is in both `spaced` and `exceptions`. The `sample` config holds the rows
whose `id` begins with `{{sample_prefix}}`, {{rows_sample}} rows for a
quick look. Because `id` is a function of the string alone, the sample
holds the same strings in every version that holds them.

{{table:files}}

## 5. The columns

The `universe` config carries {{columns_universe}} columns: the key, the
pin's columns, the release layer, the intake-provenance layer, the
evidence matrix, and `model_or_engine`. The `features` config carries
{{columns_features}}: the key and {{feature_columns_published}} columns of
the feature layer. `word` is the join key of every config; `id` is the
first 16 hexadecimal digits of the sha256 of the word, the same for the
same string in every version. The data dictionary,
`docs/DATA_DICTIONARY.md` in the code repository, is generated from the
same module as these tables.

**Null and NaN.** The layers' values are carried unchanged. In the
{{evidence_columns}} evidence columns a single-token row keeps the evidence
matrix's values: 1 listed, 0 not listed, and -1 where the source is
structurally blind to the row's class (a list without hyphens cannot hold
a hyphenated string). A spaced row holds null in every evidence column,
because the single-token sources were not measured over spaced rows.
Everywhere in this dataset, null means not measured by that source, never
false. The feature layer's NaN means the channel does not observe the
string.

**The key**

{{table:columns_key}}

**The pin's columns**

{{table:columns_pin}}

**The release layer**

{{table:columns_release}}

**The intake-provenance layer** (`pipeline/research/provenance/provenance.json`)

{{table:columns_provenance}}

**The evidence matrix** (`pipeline/research/evidence/evidence.json`)

{{table:columns_evidence}}

**Model and engine**

{{table:columns_model}}

**The feature layer, the `features` config** (`pipeline/research/features/features.json`)

{{table:columns_features}}

## 6. What this version withholds, and why

Each source's terms were read at its primary source for this version; the
readings are not legal advice, and the author ruled on them. §7 states each source's
terms, and `NOTICES.md` carries the notices.

- **{{withheld_list_count}} lists whose membership may not be published:**
  NASPA Word List 2023 and Collins Scrabble Words 2021, which are
  proprietary; the legacy SOWPODS list, for which no license was found;
  and Webster's Second International and its supplement of hyphenated
  terms (`web2`, `web2a`), whose 1961 copyright renewal holds. Their
  columns ({{withheld_columns}}) are absent, and every label naming them is
  removed from `sources`, `intake_channels`, and `panel_sets`. Their rows
  still ship wherever published evidence supports them. The Webster's
  Second columns can return in a version built on or after
  January 1, 2030.
- **Channel labels withheld for license reasons.** Some intake channels
  name a source whose terms do not allow publishing the label. The label
  is removed; a row whose every label was withheld carries the single
  label `{{channel_withheld_label}}`.
- **{{withheld_feature_count}} feature columns,** in 2 groups
  (`docs/licenses/FEATURE_COLUMNS.md` in the code repository):
  - {{withheld_reference_feature_count}} computed against a reference that
    holds `web2` or `web2a`: {{withheld_reference_features}}. A value could
    reveal whether a withheld list holds a string's neighbor, stem, or
    segments.
  - {{withheld_model_feature_count}} from the layer's character model:
    {{withheld_model_features}}. The model was fitted on strings that at
    least 2/3 of their applicable panel sets list, the withheld lists
    among them. A test compared it with the same model fitted on the
    published lists alone: the difference between the two picks out the
    strings the withheld lists list, well above chance.

  They return in a later version once each is recomputed without the
  withheld lists.
- **The rows left with no public evidence.** {{held_tier_2}} rows were
  listed only by withheld lists and keep no published channel or corpus
  containment; {{held_withheld_channel}} rows had a withheld channel as
  their only evidence. Both are held back in the private record with the
  decision as the reason. Those that Webster's Second listed return
  with its columns; those whose only evidence was a withheld channel
  return if that channel's terms are found to allow it, or when a
  published source lists them.
- **The CEOL's own rows whose every source is withheld.**
  {{held_withheld_sources}} rows of the census and the audit's additions
  have every `sources` label naming a withheld list. Shipped, their empty
  `sources` would say that a withheld list holds them, so they are held back
  the same way, though they keep corpus containment.

The rows held back, {{held_back_rows}} in all, by reason. They are counted
and never listed.

{{table:held_back}}

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
{{prov_channel_and_containment}} rows have both, {{prov_channel_only}} a
channel and no containment, {{prov_containment_only}} containment and no
channel, and {{prov_neither}} neither. The count of the last rests on a
reading of the EOL's correction ledgers that labels as generated the forms
the EOL demoted, which the same record states. {{generated_rows}} rows were
made by the EOL's synthetic engine; each carries `intake_kind`
`generated`, the category the EOL recorded, and an engine inferred from
its form and named as inferred.

## 9. How the universe was built and checked

Each step has a committed record; the counts are those records'.

1. **The census** (`reference/research/census/census.json`): the pinned
   sources re-read under the grammar; {{census_candidates}} candidates in
   the exception classes the EOL's letters-only rule could not hold.
2. **The merge** (`reference/research/merge/merge.json`): the EOL universe
   at `c1139698` ({{eol_universe_rows}} strings) and the census's
   candidates, {{merge_rows}} rows; filtering the merge by the `eol` flag
   regenerates the EOL's pinned lists byte for byte.
3. **The audit** (`reference/research/audit/reconcile.json`): every
   source's coverage by the merged universe, reconciled to a remainder of
   {{audit_remainder}}; {{c4_additions}} additions.
4. **The single-token pin** (`reference/research/universe/universe.json`):
   {{v1_rows}} candidates.
5. **The spaced admission** (`pipeline/research/universe_v2/universe_v2.json`):
   {{pin_spaced}} multiword candidates from WordNet and Wiktionary. The pin,
   {{rows_pin}} rows, reproduces the single-token pin byte for byte as its
   single-token projection.
6. **The evidence and feature layers** (`pipeline/research/evidence/evidence.json`,
   `pipeline/research/features/features.json`).
7. **The intake-provenance layer** (`pipeline/research/provenance/provenance.json`).
8. **The model-and-engine column:** derived from the EOL's valid
   dictionary at the pin ({{model_basis_entries}} entries) by
   `pipeline/research/provenance/model_basis.py`.
9. **This release:** the public projection and the build.
   The build asserted, on each of its {{files_asserted}} written files,
   that none of the {{restricted_words_checked}} restricted rows' strings is
   present, that every id is distinct, that each filter config is its
   predicate's filter, that no withheld column or label is present, that
   no held-back row is present, and that `provenance_class` and
   `model_or_engine` re-derive from the file's own fields.

## 10. What the universe does not record

Part of speech ({{wordnet_listed}} rows are WordNet-listed and could take a
part of speech from WordNet); lemma and inflection relations; definitions
and senses (they move with their sources and carry license obligations);
pronunciation, syllables, etymology, and a first attestation year; variety
and register labels (the 2 variety columns are proxies); a frequency drawn
from many kinds of text for most rows (wordfreq scores {{wordfreq_scored}};
the Google Books counts cover {{limit_gb_all}} rows, but from scanned books
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
{{contact_address}}; the hub's own copyright process also reaches the
dataset. A request is acknowledged within 7 days
and acted on within 14 days of its verification, and each version's change
log records every withholding, as counts (`docs/UPKEEP.md` §7 in the code
repository).

## 14. Canary

This card carries the canary string `{{canary_string}}`. It exists so that a
later test can check whether a model has memorized this dataset's
documentation. It is recorded in the release record and in each Parquet
file's metadata.

## 15. How to cite

`CITATION.cff` in the code repository gives the citation. The DOI is
minted at the release. Until then: Ryan Kamp, *The CEOL Universe*,
version {{version_name}}, Hugging Face dataset `{{dataset}}`, built
{{built_on}}.

## 16. Change log

- **{{version_name}}** ({{built_on}}): the first public version.
  {{rows_universe}} rows in {{config_count}} configs, with the withholding
  of §6, `NOTICES.md`, and the canary, the license, and the attribution
  in each Parquet file's metadata.
