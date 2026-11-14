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
---

# The CEOL Universe, version {{version}}

**A private rehearsal. Version {{version}} is uploaded to this private
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
(C-001, C-015). This version holds {{rows_universe}} rows, 1 per
string. A row says that a pinned source lists the string, that the
string was inherited from the English OpenList (EOL) universe, or both.
**A row is not a verdict.** No row of this dataset has been validated by
the CEOL; no threshold has been chosen; the split is named `candidates`
because that is what every row is. The `eol` column records whether the
string was in the EOL's valid list at the pinned revision `08ae92b8`: a
historical fact at a pin, never a CEOL judgment, and the live EOL moves
its split nightly.

## 2. The 3 datasets and their names (C-078 line 1)

- **The EOL** (`ryanjosephkamp/english-openlist`): the validated English
  word list under its own grammar and governance. The CEOL reads it at a
  pinned revision and never writes to it.
- **The CEOL Universe** (this dataset, `{{dataset}}`): the candidate
  inventory, versioned as its pins are (v2 is the pin of C-016; v3 the
  pin of a later entry).
- **The validated subsets**, 1 per operational definition and version,
  named `ceol-<definition>-<version>`; the first, `ceol-itw-1`, will come
  from the in-the-wild programme when that study has run. Each is a
  separate dataset with its own card.

No dataset is called the CEOL alone: the CEOL is the family and the
mission.

## 3. The version and the pin

Version {{version}} is a projection of universe v2, the pin of C-016:
{{rows_pin}} candidates, of which {{rows_restricted}} are restricted
(§6) and are not in this dataset. It was built on {{built_on}} by
`research/release/build_release.py`, which verifies every pinned layer's
sha256 against its committed record before reading it, writes the files,
re-reads them, and asserts the properties this card states before
anything is kept; the record of the build, with every file's rows,
columns, bytes, and sha256 and the assertions' counts, is
`research/release/release_{{version}}.json`. Version {{version}} is a
private rehearsal of that pipeline. The public version is v3.0: the same
pipeline over the universe-v3 pin, which adds the lexicon-development
line's admitted rows and a part-of-speech and inflection layer (C-078
lines 2 to 4).

{{table:sources}}

## 4. The configs

The default config, `universe`, holds every shippable row. `features` holds
the feature layer for the single-token rows. The other {{filter_count}}
configs are filters of `universe`, with every column of `universe` and its
row order; each is the filter of `universe` by the stated predicate and
nothing else, which the build asserts on the written files.

{{table:configs}}

The `exceptions` config holds the rows carrying any of the
{{exception_class_count}} exception classes of the census (C-005); a
spaced row with such a class is in both `spaced` and `exceptions`.

{{table:files}}

## 5. The columns

The `universe` config carries {{columns_universe}} columns in {{block_count}} blocks:
the key, the pin's columns, the release layer, the intake-provenance
layer, and the evidence matrix. The `features` config carries
{{columns_features}}: the key and the feature layer's
{{feature_layer_columns}} columns. `word` is the join key of every layer;
`id` is the first 16 hexadecimal digits of the sha256 of the word, the
same for the same string in every version.

**2 kinds of NA.** The layers' values are carried unchanged. In the
{{evidence_columns}} evidence columns a single-token row keeps the
evidence matrix's values: 1 listed, 0 not listed, and -1 where the source
is structurally blind to the row's class (a game list cannot hold a
hyphen; C-010). A spaced row holds null in every evidence column, because
the single-token sources were not measured over spaced rows (C-016).
Everywhere in this dataset, null means not measured by that source,
never false. The feature layer's NaN means the channel does not observe
the string (C-011).

{{table:columns_key}}

{{table:columns_pin}}

{{table:columns_release}}

{{table:columns_provenance}}

{{table:columns_evidence}}

{{table:columns_features}}

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
| The EOL universe at revision `08ae92b8` | its maintainer's contribution under MIT; its sources keep their own terms | the inherited strings, `eol`, `eol_universe`, the provenance layer's `eol:` channels |

**The licence split (C-009).** NWL2023 and CSW21 are not redistributable.
The {{rows_restricted}} rows of the pin that only those 2 lists attest are
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

**{{prov_neither}} rows ({{prov_neither_pct}}) have no recorded intake
channel and no measured containment**: the record does not say how the
string entered the EOL's pool, and neither a panel set nor a corpus
holds it. That count rests on a reading of the EOL's correction ledgers
that labels as generated the forms the EOL demoted; without it the
pin's residual would be {{prov_residual_without_reading}} (C-065). The
intake-provenance layer (C-064) records 2 senses of provenance and
keeps them apart: the intake channel, the route by which a string first
entered the pool (for inherited strings the EOL's discovery log, which is
a record of where a string was first seen and never an attestation), and
the measured containment in the {{panel_set_count}} panel sets and the 2
corpora. {{prov_channel_only}} rows have a channel and no containment.
{{generated_rows}} rows ({{generated_pct}}) were made by the EOL's
synthetic engine, whose code is lost; each carries `intake_kind`
`generated`, the category the EOL recorded, and an engine inferred from
its form and named as inferred. The layer's report is
`research/provenance/PROVENANCE.md`; its counts are
`research/provenance/provenance.json`.

## 8. How the universe was built and audited

Each step has a committed record in the CEOL repository and a decision
entry; the counts are those records'.

1. **The census** (C1; C-005): the pinned sources re-read under the CEOL
   grammar; {{census_candidates}} candidates in the exception classes
   the EOL's letters-only rule could not hold. Record:
   `research/census/census.json`.
2. **The merge** (C2; C-002): the EOL universe and the census's
   candidates; filtering the merge by the `eol` flag regenerates the EOL's
   pinned lists byte for byte. At the EOL's revision `08ae92b8` it holds
   {{eol_universe_rows}} inherited strings and {{merge_rows}} rows. Record:
   `research/merge/merge.json`.
3. **The audit** (C3): every source's coverage by the merged universe,
   reconciled to a remainder of {{audit_remainder}}; {{c4_additions}} additions. Records:
   `research/audit/audit.json`, `research/audit/reconcile.json`.
4. **The pin** (C-009), re-pinned to the EOL's revision `08ae92b8`: an
   inherited string in neither of the EOL's lists at that revision leaves
   the pin, `eol` is read again, and every other row is unchanged;
   {{v1_rows}} candidates. Records: `research/universe/universe.json`,
   `pipeline/research/universe/repin.json`.
5. **The spaced admission** (C-015, C-016): {{pin_spaced}} multiword
   candidates from WordNet and Wiktionary; universe v2, {{rows_pin}}
   rows, reproduces the C-009 pin byte for byte as its single-token
   projection. Records: `research/space_census/space_census.json`,
   `research/universe_v2/universe_v2.json`.
6. **The evidence and feature layers** (C-010, C-011). Records:
   `research/evidence/evidence.json`, `research/features/features.json`.
7. **The intake-provenance layer** (C-064, C-065). Record:
   `research/provenance/provenance.json`.
8. **This release** (C-078). Record:
   `research/release/release_{{version}}.json`.

## 9. Limitations

- **{{limit_gb_inherited_no_panel}} single-token rows
  ({{limit_gb_inherited_no_panel_pct}}) are strings inherited from the
  EOL that are Google Books 1-gram types and that none of the
  {{panel_set_count}} panel sets lists.** Their only measured
  containment is a corpus built from scanned text, which carries
  recognition errors. In all, {{limit_gb_all}} rows are Google Books
  types ({{limit_gb_pin}} over the pin, which counts the restricted rows).
- {{limit_no_panel_no_corpus}} single-token rows are listed by no panel
  set and are in neither corpus.
- {{generated_rows}} rows are the output of a lost engine that affixed
  and substituted without a part-of-speech filter (§7).
- The `sources` column has 2 meanings: a per-source containment list on
  the CEOL's own rows, and the dataset-level tag `eol_universe@08ae92b8`
  on inherited rows, whose per-source listing is the evidence columns'.
- The evidence columns carry 2 kinds of NA (§5), and the corpora do not
  measure multiword rows.
- `eol` is a fact at a single revision of the EOL, which changes daily.

## 10. What the universe does not record

Part of speech ({{wordnet_listed}} rows are WordNet-listed and could take
a part of speech from WordNet; v3.0 adds the morphology layer); lemma and inflection
relations (v3.0); definitions and senses (not planned: they move with
their sources and carry license obligations); pronunciation, syllables,
etymology, and a first attestation year (later layers, each by its own
decision); variety and register labels (the 2 variety columns are
proxies); a frequency for most rows (wordfreq scores {{wordfreq_scored}});
and validity, by design.

## 11. The relation to the in-the-wild study

The CEOL's in-the-wild programme studies whether a term is attested in
use outside the pinned sources. It samples from the universe, and its
material stays private for the study's life (C-078 line 5): the
development-ledger words and their labels, the synthetic controls (absent
from every pinned universe by construction), the probe batteries, the
pilot words, the human labels, and every model verdict. **No column of
this dataset states a study label or a study verdict**, and the build
asserts that the synthetic controls ({{controls_checked}} checked) and
the intake-ledger words not yet pinned ({{ledger_words_checked}} checked)
are in no file. The model posterior of the C-012 contest is not shipped.
The study's material is released after its confirmatory round closes,
under its own decision entry. The release's date and file hashes are in
its record, so that any later contamination question can be dated.

## 12. Canary

This card carries the canary string `{{canary_string}}`. It exists so
that a later test can check whether a model has memorized this dataset's
documentation (C-078 line 4); it is recorded in
`research/release/release_{{version}}.json`.

## 13. How to cite

The DOI is minted at the public version. Until then: ryanjosephkamp, *The
CEOL Universe*, version {{version}} (a private rehearsal), Hugging Face
dataset `{{dataset}}`, built {{built_on}}.

## 14. Change log

- **{{version}}** ({{built_on}}): the first build of the release pipeline,
  over universe v2 (C-016), uploaded to the private dataset (C-078 lines
  3 and 7).
