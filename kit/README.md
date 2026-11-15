# The study kit

The kit helps a researcher draw a reproducible sample of candidates from the CEOL Universe and run a labeling study on it. It loads the dataset at a pinned version, draws a stratified sample by a public rule, and ships a labeling codebook, a preregistration template, and contamination guidance.

**It describes version 1.0 of the dataset**, the Hugging Face dataset `ryanjosephkamp/ceol-universe` at the revision `v1.0`. Its card is [`CARD_v1.0.md`](../pipeline/research/release/CARD_v1.0.md), and its columns are in the [data dictionary](../docs/DATA_DICTIONARY.md).

Every row of the dataset is a candidate string with its provenance, never a verdict. The kit does not decide which candidates are words, supplies no definition of a word, and holds no labels. A study's definition and labels are the researcher's. Nothing here registers or files anything anywhere.

## What is in the kit

| Path | What it is |
|---|---|
| `ceolkit/load.py` | `load`: a config at a pinned version, from a local file or folder or from the hub; `join_features`; `figure` and `figures`, the release's published counts by id |
| `ceolkit/sample.py` | `draw`: the deterministic stratified sampler and its manifest |
| `ceolkit/strata.py` | the ready strata, `combine`, and `family_cells` |
| `notebooks/` | 3 Jupyter notebooks that run on the fixtures |
| `tests/` | the kit's tests; they run on the fixtures with no network |
| `fixtures/` | samples of version 1.0's rows, for the notebooks and tests |
| [`CODEBOOK.md`](CODEBOOK.md) | a labeling codebook template |
| [`PREREGISTRATION_TEMPLATE.md`](PREREGISTRATION_TEMPLATE.md) | a preregistration template that registers nothing |
| [`CONTAMINATION.md`](CONTAMINATION.md) | contamination guidance |

## Install

The kit needs Python 3.11 and 3 packages: `pyarrow`, `numpy`, and `pandas`. The repository's `requirements.txt` pins the versions the kit was tested with. To read the dataset from the hub, also install `huggingface_hub`; to run the tests, `pytest`.

```
pip install pyarrow numpy pandas
pip install huggingface_hub pytest      # optional: the hub, and the tests
```

`ceolkit` is a folder, not an installed package. Run Python from `kit/`, or put `kit/` on the import path. From the repository root:

```
PYTHONPATH=kit python3 -c "import ceolkit; print(ceolkit.__version__)"
```

## Load

```python
from ceolkit import load

universe = load("universe", "v1.0", source="path/to/data")   # a local copy
features = load("features", "v1.0", columns=["id", "wordfreq_zipf"], source="path/to/data")
universe = load("universe", "v1.0")                          # from the hub
```

`load` returns an Arrow table. The configs are `universe`, `features`, `panel-listed`, `eol-valid`, `spaced`, `exceptions`, and `sample` (the card's §4 defines each).

- **`source`** is a local path. A file is read as it is. A folder is searched for `data/<config>.parquet`, then `<config>.parquet`.
- **Without `source`**, `load` reads `hf://datasets/ryanjosephkamp/ceol-universe@<version>/data/<config>.parquet` through `huggingface_hub`'s file system. Without that package it raises an error that says so.
- **The dataset is private until its release,** which is the author's decision. The code never asks for a login, a token, or a key. Before the release, pass `source=` with a local copy.
- **A version is pinned.** Each Parquet file carries its version in its metadata, and `load` refuses a file whose version differs from the one asked for. A released version never changes, so a version and a config name one file. Record the file's sha256 and compare it with the card's table of files (§4).

The `universe` config is large. Read only the columns you need: `id`, `word`, and the columns your stratum reads (each stratum lists them in its `columns`). The `universe` config has no frequency column. `join_features(universe, features, ["wordfreq_zipf"])` adds feature columns by `id` and returns a pandas frame.

## Sample

```python
from ceolkit import draw, strata

sample, manifest = draw(universe, strata.evidence_tier, 100, "my-seed")
```

`draw(table, stratum, n, seed)` takes a pyarrow table or a pandas frame with one row for each candidate. The rule:

> within each stratum, rows are ranked in ascending order by the hex digest of sha256(f"{seed}:{stratum}:{word}".encode("utf-8")), and the first N of each stratum are taken

It is the rule the repository uses to draw its fixtures and its vetted example list, with a public seed in place of a private key. A public seed lets anyone recompute the draw, which is the point of a study that others must reproduce.

- **`stratum`** is a column name, a ready `Stratum`, or a function of a row. A column's value becomes the label as text: booleans are `true` and `false`, a whole number is its digits, and null is `null`.
- **`n`** is an integer, or a dict from a label to a count. With a dict, a stratum it does not name is not sampled. A stratum with fewer rows than `n` gives all of them, and `short_strata` in the manifest names it.
- **Order does not matter.** The same rows in any order, as an Arrow table or a pandas frame, give the same sample in the same order.
- **A smaller sample is the head of a larger one.** A pilot of 10 for each stratum is the first 10 of a main sample of 50.
- **The sample** has every input column plus `sample_stratum` and `sample_rank`, and is ordered by stratum label, then rank.
- **The seed** is a string you choose and record before you look at the data. Do not try seeds until a sample looks right.

The manifest records the rule, the seed, the stratum and its definition, `n`, the input's row count, the rows available and selected in each stratum, `short_strata`, and `selected_ids_sha256`: the sha256 of the selected ids, sorted and joined by newlines. It holds no candidate. File it with the preregistration. Pass `source={...}` to record where the rows came from (dataset version, config, file sha256).

The fixtures were drawn by the same rule with a private key, so the sampler does not reproduce them. The fixtures hold the same number of rows from each intake layer, not the release's mix. A count computed on them describes the fixtures only.

An equal number from each stratum is not a sample of the frame. To estimate a share for the whole frame, weight each sampled row by `available / selected` for its stratum, from the manifest.

## Strata

A stratum is a function of a row that returns a label. Each ready stratum in `ceolkit.strata` states its definition in its `definition` text, and `strata.STRATA` lists them.

| Stratum | Labels | Reads |
|---|---|---|
| `evidence_tier` | `listed_by_2_or_more`, `listed_by_1`, `none_with_corpus`, `none_no_corpus`, and `not_single_token`, `not_measured`, `no_family_can_hold` | `token_count`, the evidence columns, `gb_type`, `wordfreq_scored` |
| `spelling_class` | `plain`, `spaced`, `diaeresis`, `contraction`, `ligature`, `accented`, `hyphenated`, `apostrophe-form` | `class_explicit` |
| `length_band` | `01-04`, `05-06`, `07-08`, `09-10`, `11-12`, `13-16`, `17+` | `word` |
| `frequency_band` | `zipf_below_2`, `zipf_2_to_3`, `zipf_3_to_4`, `zipf_4_to_5`, `zipf_5_or_more`, `no_value` | `wordfreq_zipf` (features config; join it first) |
| `intake_layer` | `c1_exceptions`, `c4_additions`, `eol_invalid`, `eol_valid`, `spaced_c015` | `intake_layer` |
| `model_or_engine` | `engine_generated`, `none` | `model_or_engine` |

`strata.combine(strata.evidence_tier, strata.length_band)` makes 1 stratum for each pair of labels. To stratify by the exact set of class flags, pass the column name `class_explicit`.

**How the evidence tier reads the evidence columns.** The card gives each evidence cell 1 of 4 meanings:

- 1 means the source lists the row.
- 0 means it does not.
- -1 means the source cannot hold the row's kind of string (a list without hyphens cannot hold a hyphenated string). It is never "not listed".
- null means the source was not measured over the row. It is never "not listed" either.

The tier counts the families that list the row: WordNet, Wiktionary, hunspell (any of the 4 `hunspell_en_*` columns), ENABLE, and SCOWL (`scowl_tier` above 0). A -1 is not a listing, and it is not a no. A null can leave the tier undecided, so it gets the label `not_measured`. A row with more than 1 token is `not_single_token`, because the single-token sources were not measured over it. These 5 families differ from the families of the vetted example list, which counts SCOWL and the en_US, en_CA, and en_AU dictionaries as 1.

## Notebooks

They run on the fixtures, print counts and never a candidate, and are saved with their outputs cleared.

| Notebook | What it does |
|---|---|
| `notebooks/01_load_and_first_look.ipynb` | loads the configs, compares the fixtures with the release's published counts, and reads the evidence columns (1, 0, -1, null) |
| `notebooks/02_draw_a_labeling_sample.ipynb` | draws a stratified sample, checks that it reproduces, weights it, and saves the manifest, the ids, and an annotation sheet |
| `notebooks/03_frequency_and_coverage.ipynb` | frequency bands, and coverage by list family with -1 and null read correctly (optional) |

The sampling notebook writes its files to `labeling_sample/` next to it. Set `CEOL_OUT_DIR` to write elsewhere.

## Tests

```
cd kit && python3 -m pytest -q
```

The tests need the fixtures and nothing else: no network, no private data. They check the sampler against the rule written out separately (determinism, order independence, per-stratum counts, a changed seed, the manifest), each stratum's handling of -1 and null, the loader (the fixtures by `source`, the wrong version, the hub path against a stand-in), and that every notebook's code cells run in order. A last check runs the notebooks on a copy of the fixtures whose words are replaced by markers, to show that nothing prints a candidate.

## Documents

- [`CODEBOOK.md`](CODEBOOK.md): a template for annotators who label sampled candidates against a definition the researcher chooses.
- [`PREREGISTRATION_TEMPLATE.md`](PREREGISTRATION_TEMPLATE.md): a form to fill in. It registers nothing until the researcher files it somewhere.
- [`CONTAMINATION.md`](CONTAMINATION.md): the canary string, the `model_or_engine` column, mentions and uses, and dating a release.

## Writing about candidates

A string of the dataset is a candidate. Write that a source lists it, which is evidence and not a verdict. A study that labels candidates reports labels about a definition, and the definition is the researcher's.
