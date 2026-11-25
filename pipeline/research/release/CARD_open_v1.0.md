---
license: cc-by-sa-4.0
pretty_name: CEOL Universe, open subset
language:
- en
size_categories:
- 1M<n<10M
tags:
- lexicon
- word-list
- english
- lexicography
- candidate-inventory
configs:
- config_name: open-lists
  default: true
  data_files:
  - split: candidates
    path: data/open-lists.parquet
- config_name: wordnet-wiktionary
  data_files:
  - split: candidates
    path: data/wordnet-wiktionary.parquet
- config_name: sample
  data_files:
  - split: candidates
    path: data/sample.parquet
---

# The CEOL Universe, open subset, version 1.0

**This is the open subset of the CEOL Universe.** It holds the universe's
rows that open word lists list, in the columns those lists and Google Books
give: 1,179,657 of the universe's 10,264,273 rows. The full universe,
with its other lists, its corpus rows, and the record of how each string
came into it, will be released after a license review; no date is promised.
Until then, [the site](https://common-english-openlist.pages.dev/) describes
the full universe, and [the code repository](https://github.com/ryanjosephkamp/ceol-universe)
holds the code that built both.

**Every row is a candidate string, never a verdict.** A row records which
open lists list the string. No row says that a string is a word. The split
is named `candidates` because that is what every row is.

## 1. Limitations

- **The rows are the universe's.** A row is here when the universe's
  version 1.0 holds the string and an open list lists it. A string an open
  list holds that the universe does not is not a row: under the CEOL
  grammar, WordNet holds 2,291 such strings, and the other open lists
  hold none.
- **The English Wiktionary is most of it.** 697,984 single-word rows
  (78.89% of them) are listed by the English Wiktionary alone. Its
  English sections hold inflected forms, proper nouns, abbreviations, and
  rare and obsolete words.
- **The lists are not independent.** The en_US, en_CA, and en_AU hunspell
  dictionaries come from SCOWL, by their own READMEs, so `list_count`
  counts lists, not independent evidence.
- **SCOWL is cut at size 70.** `scowl_size` names SCOWL's lists of sizes 10
  to 70 only. A row that SCOWL lists only at size 80 or 95 has
  `scowl_size` 0 (230,486 rows here), and a row that only those
  sizes list is not here.
- **Multiword rows are measured differently.** The 294,865 multiword
  rows come from WordNet's and the English Wiktionary's multiword entries,
  and `listed_by` names which. The single-word list columns and `gb_type`
  are null on them, because those sources were not measured over multiword
  strings. Their properness signals are recorded, never filtered on:
  582 carry a Wiktionary proper-noun heading, and
  7,812 are WordNet instances.
- **`gb_type` rests on scanned books,** which carry recognition errors.
  227,790 single-word rows here are not Google Books types.
- **Null means not measured** by that source, never false.

## 2. What this dataset is

The CEOL Universe is an inventory of candidate English strings, each with
its provenance: which pinned lists list it, which corpora contain it, and
how it entered the inventory. Its strings are the output of an executable
grammar (`pipeline/ceol/grammar.py` in the code repository) that admits
hyphenated compounds, accented loanwords, contractions, apostrophe forms,
ligature and diaeresis spellings, and multiword terms. Its version 1.0
holds 10,264,273 rows, 1 per string.

This subset keeps the rows of version 1.0 that at least 1 of 6 open lists
lists: WordNet 3.0, the English Wiktionary, the LibreOffice hunspell
dictionaries en_US, en_CA, and en_AU, and SCOWL at sizes 10 to 70. It
keeps only the columns derived from those lists and from Google Books'
1-gram types. Every column, and each config's rule, is a function of those
sources alone.

`id` is the first 16 hexadecimal digits of the sha256 of the word, as in
the full release, so a row here joins the full release's row for the same
string by `id` or by `word`.

## 3. The configs

| Config | File | Rows | Single-word | Multiword | Rule |
|---|---|---:|---:|---:|---|
| `open-lists` (default) | `data/open-lists.parquet` | 1,179,657 | 884,792 | 294,865 | listed by at least 1 of the 6 open lists |
| `wordnet-wiktionary` | `data/wordnet-wiktionary.parquet` | 1,139,896 | 845,031 | 294,865 | listed by WordNet or the English Wiktionary; only the columns derived from those 2 |
| `sample` | `data/sample.parquet` | 4,554 | | | the rows of `open-lists` whose `id` begins with `00` (about 1 in 256) |

Each config holds its rows in the full release's order. `wordnet-wiktionary`
holds the rows of `open-lists` that WordNet or the English Wiktionary
lists, without the hunspell, SCOWL, and Google Books columns, and its
`list_count` and `listed_by` count those 2 lists alone. Because `id` is a
function of the string alone, the sample holds the same strings in every
version that holds them.

The single-word rows of `open-lists`, by list (a row may have several):

| List | Rows |
|---|---:|
| WordNet 3.0 | 80,441 |
| English Wiktionary | 831,973 |
| hunspell en_US | 121,252 |
| hunspell en_CA | 120,947 |
| hunspell en_AU | 121,490 |
| SCOWL, sizes 10 to 70 | 143,729 |

The multiword rows: 231,382 listed by the English Wiktionary alone,
43,972 by WordNet alone, and 19,511 by both.

| File | Bytes | Row-group rows | sha256 |
|---|---:|---:|---|
| `data/open-lists.parquet` | 18,894,524 | 1,140,000 | `beb133fc59d017168f81317800a19bdc6049c86e83f2e331686a37fb9038b3f0` |
| `data/wordnet-wiktionary.parquet` | 16,974,568 | 1,139,896 | `6d86c82d23875a28aad39b4097779bd630e82bb90a8c28747e83d1cb1ef4be51` |
| `data/sample.parquet` | 102,919 | 4,554 | `b7d0ee9d705dc011974e83ec737dc2d841accb9623eb815f9778c5a7730cb4f5` |
| `NOTICES.md` | 17,198 | | `a5b3646d209c7ffd621375636e3b7bdf5ee408d8dc5def2cd8bb1fd15e195dd4` |

## 4. The columns

`open-lists` and `sample` carry 17 columns; `wordnet-wiktionary` carries
12 of them (all but the 3 hunspell columns, `scowl_size`, and `gb_type`).
Every value but `scowl_size`, `list_count`, and `listed_by` is the full
release's value for the same row.

| Column | Type | Meaning | Null |
|---|---|---|---|
| `id` | string | the first 16 hexadecimal digits of the sha256 of the word's UTF-8 bytes; the full release's id for the same string | never null |
| `word` | string | the candidate string, the grammar's output: lower case, the 50-character charset, spaces single and interior | never null |
| `token_count` | int32 | the number of space-separated tokens | never null |
| `classes` | string | the grammar's class flags joined by ';' (hyphenated, accented, diaeresis, ligature, apostrophe-form, contraction, s-final, spaced); the empty string on a plain-letter string | never null |
| `wordnet` | int8 | listed by WordNet 3.0's lemmas under the CEOL grammar: 1 listed, 0 not listed, -1 the list cannot hold the row's class (WordNet holds no accented, ligature, or diaeresis string) | null on multiword rows |
| `wiktionary_english` | int8 | listed by an English Wiktionary page with an English section, under the CEOL grammar: 1 listed, 0 not listed | null on multiword rows |
| `hunspell_en_US` | int8 | listed by the LibreOffice hunspell en_US dictionary, expanded: 1 listed, 0 not listed, -1 the dictionary cannot hold the row's class | null on multiword rows |
| `hunspell_en_CA` | int8 | the same for en_CA | null on multiword rows |
| `hunspell_en_AU` | int8 | the same for en_AU | null on multiword rows |
| `scowl_size` | int16 | the size, 10 to 70, of the smallest SCOWL list of size 70 or below that holds the string; 0 where none of them does; -1 where SCOWL cannot hold the row's class | null on multiword rows |
| `gb_type` | bool | the string is a Google Books English 1-gram type (the 2020 release) under the CEOL grammar | null on multiword rows |
| `list_count` | int8 | the number of the config's open lists that list the row | never null; at least 1 |
| `listed_by` | string | those lists' names joined by ';', in the order wordnet, wiktionary_english, hunspell_en_US, hunspell_en_CA, hunspell_en_AU, scowl | never null |
| `wn_instance` | bool | WordNet instance-synset membership, a properness signal, recorded and never filtered on | null unless WordNet lists the multiword row; null on every single-word row |
| `wn_capitalized` | bool | WordNet data-file capitalization, a properness signal | null unless WordNet lists the multiword row; null on every single-word row |
| `wk_proper_noun` | bool | a Wiktionary Proper-noun heading, a properness signal | null unless the English Wiktionary lists the multiword row; null on every single-word row |
| `wk_flags` | string | Wiktionary's category flags joined by ';' (idiomatic, phrasal-verb, phrasebook, proverb); may be the empty string | null unless the English Wiktionary lists the multiword row; null on every single-word row |

## 5. What this subset leaves out

The full release records more than this subset publishes. These parts wait
on the license review, because each is among its questions:

- the en_GB hunspell dictionary, ENABLE, and SCOWL's lists at sizes 80 and
  95, and the 205,176 rows of the universe that only they list;
- the universe's rows that no list lists, which a corpus or the English
  OpenList holds, and the wordfreq values and the feature layer;
- the English OpenList's lists, and every field that records how a string
  came into the universe.

## 6. The sources, their licenses, and the credits

This subset is licensed CC BY-SA 4.0, as the full release is: its
Wiktionary-derived fields ask that adaptations share alike. `NOTICES.md`,
beside the data files, carries every notice, license, and credit its
sources require, in their own words where their terms require the text
itself, and each Parquet file names it in its metadata.

| Source | What its own files state | What this dataset carries from it |
|---|---|---|
| The English Wiktionary (Wikimedia dumps, the run of August 1, 2026) | CC BY-SA 4.0 and the GFDL, under the Wikimedia Terms of Use | `wiktionary_english`, `wk_proper_noun`, `wk_flags`, the multiword rows' listing |
| WordNet 3.0 (Princeton University), as nltk distributes it | the WordNet 3.0 license, which `NOTICES.md` carries verbatim | `wordnet`, `wn_instance`, `wn_capitalized`, the multiword rows' listing |
| SCOWL (Kevin Atkinson; the December 7, 2020 archive) | SCOWL's `Copyright` file, with its components' notices, which `NOTICES.md` carries verbatim | `scowl_size` |
| The LibreOffice hunspell dictionaries en_US, en_CA, en_AU | their READMEs: they "come directly from SCOWL and is thus under the same copyright of SCOWL" | `hunspell_en_US`, `hunspell_en_CA`, `hunspell_en_AU` |
| The Google Books Ngram corpus, English 1-grams, the 2020 release | its export page: a Creative Commons Attribution 3.0 Unported License | `gb_type` |

**Credits.** The English Wiktionary's contributors; Princeton University
for WordNet; Kevin Atkinson and the contributors named in SCOWL's
copyright notice; the LibreOffice dictionary maintainers; the Google Books
Ngram corpus (https://books.google.com/ngrams), described by Jean-Baptiste
Michel and colleagues, "Quantitative Analysis of Culture Using Millions of
Digitized Books", Science 331 (2011).

## 7. How it was built and checked

`pipeline/research/release/open_subset.py` in the code repository built
this subset on November 25, 2026 from the full release's `universe.parquet`
(version 1.0, sha256 `f4355af70b01bd40ea340849bac07bd79a680695d31aced94a53cde39ef3de60`), which it holds to the release's
record before reading. It reads that file's open columns and nothing else
for a row's membership or values. Its record, with every file's rows,
columns, bytes, and sha256 and the counts on this card, is
`pipeline/research/release/open_subset_v1.0.json`. The build re-read every
file it wrote and asserted:

- that each config is its rule's filter of the full release's rows, in
  their order, recomputed from the file's own columns and, apart from the
  build's own code, from the full release's columns;
- that every value equals the full release's value for the same row, but
  `scowl_size`, which never names a size above 70;
- that no other column of the full release is present;
- that every `id` is distinct and is its string's hash;
- that `list_count` is the number of names in `listed_by`, and at least 1;
- that `NOTICES.md` carries the full release's notice texts unchanged.

Before release, the rows were derived again from the pinned files of the
6 lists themselves, apart from the full release's columns, and matched
row for row. A check on the project's private records found none of the
strings the full release keeps out of every version in any file of this
subset.

## 8. Requests and takedowns

A request to withhold, correct, or restore a source or a row goes to
ryanjosephkamp@gmail.com; the hub's own copyright process also reaches the
dataset. A request is acknowledged within 7 days and acted on within 14
days of its verification, and each version's change log records every
withholding, as counts.

## 9. Canary

This card carries the canary string `CEOL UNIVERSE OPEN SUBSET CANARY 5d0f3e2a-7c1b-4f86-9a3e-2b8c6d41e957`.
It exists so that a later test can check whether a model has memorized
this dataset's documentation. It is recorded in the build's record and in
each Parquet file's metadata.

## 10. How to cite

`CITATION.cff` in the code repository gives the citation for the CEOL
Universe. For this subset: Ryan Kamp, *The CEOL Universe, open subset*,
version 1.0, Hugging Face dataset `ryanjosephkamp/ceol-universe-open`, built November 25, 2026.

## 11. Change log

- **1.0** (November 25, 2026): the first version, from the CEOL Universe's version
  1.0. 1,179,657 rows in 3 configs, with `NOTICES.md`, the canary, the
  license, and the attribution in each Parquet file's metadata.
