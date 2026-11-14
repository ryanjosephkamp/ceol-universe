# Contamination guidance

A study is contaminated when something it relies on has already seen what it tests, so that a result says less than it seems to. This note covers what the dataset marks, and how to keep a study that uses it honest. It does not say whether any model has seen anything. The dataset's files and card are in the [dataset card](../pipeline/research/release/CARD_v1.0.md) (§11, §12, and §14 are the parts that matter here).

## 1. Four routes

| Route | Example | What to do |
|---|---|---|
| A model under test has seen the dataset's files or documents | a model is probed on candidates and on the provenance the dataset records | use the canary (§2), and date the release (§5) |
| A model that labels or filters has seen them | a model is an annotator, or filters the frame | treat it as a source and an annotator; record its name, version, date, and prompt ([`CODEBOOK.md`](CODEBOOK.md) §6 and §9) |
| The English OpenList decided a row with a language model | a labeler's agreement with the EOL is measured on rows the EOL decided with a model | use `model_or_engine` (§3) |
| Candidates in a probe set appear on public pages | probe strings come from this project's pages | remember the difference between a mention and a use (§4) |

The dataset's strings come from earlier sources: the English OpenList's universe at a pinned revision, and the pinned public lists and corpora (the card's §7), such as Wiktionary, WordNet, SCOWL, ENABLE, and the Google Books 1-grams. A model with an early training cutoff may know many of the strings. What the dataset adds is its selection, its layers, its provenance columns, and its documents. Those are what the canary and the release date mark.

## 2. The canary

The canary string is:

```
CEOL UNIVERSE CANARY a8d1c96b-4b6e-413c-94a1-a6fa7066f992
```

It is recorded in 3 places:

- the card, §14, which carries the whole string;
- the release record, `pipeline/research/release/release_v1.0.json`, under the key `canary`, which holds the identifier;
- each Parquet file's metadata, under the key `ceol.canary`, which holds the identifier:

```python
import pyarrow.parquet as pq

pq.read_schema("universe.parquet").metadata[b"ceol.canary"].decode()
```

**What it can show.** If a corpus holds the string, the card or a copy of it reached that corpus; that alone does not show that a given model trained on the corpus. If a model, given the first words of the canary, completes the identifier, the model was exposed to the card or a copy: through its training data, through retrieval, or through text it was given. Telling those apart, and tying a match to a particular training run, needs controls and a record of how the tested system was built and served.

**What it cannot show.**

- A model that does not complete it may still have seen the card. A canary test finds memorization, not exposure.
- It marks the documents and the files, not the rows. A model may have seen a row, or the same string from an upstream source, without having seen the canary.
- A match says nothing about which model version trained on which copy.

**How to probe.** Give the model the prefix `CEOL UNIVERSE CANARY` and sample several completions, at temperature 0 and at the default. Count exact matches of the identifier. Also search for the identifier in any training corpus you can reach. Do not paste the whole card into the prompt. Record the model's name and version, the date, the prompts, the number of samples, and the results, and report a null result as a null result.

## 3. The `model_or_engine` column

`model_or_engine` records whether the English OpenList's synthetic engine made a row. It is a record of the EOL's method and not a verdict of this dataset. No language model decided any row that the CEOL added (card §12).

| Value | Meaning | Count (figure id) |
|---|---|---|
| `engine_generated` | the string was made by the EOL's synthetic engine, whose code is lost; the engine affixed and substituted without a part-of-speech filter | `rows.by_model_or_engine.engine_generated` |
| `none` | every other row | `rows.by_model_or_engine.none` |

Read the counts with `ceolkit.figure(...)`, from `figures.json`. The EOL decided some rows of its valid list with a language model, but no row says which: that is a fact of how the EOL took a word in (card §12). So `none` does not say that no model touched the row. The column `eol` is a fact at one revision of the EOL, `08ae92b8`, and not a verdict either.

**Why it matters.**

- A model that labels candidates is not independent of a list that a model decided. If your question is whether labelers agree with the EOL, treat the rows of its valid list (`eol` true) as partly a model's decisions.
- If a language model is the object of study, some of those rows are partly its relatives' output.
- `engine_generated` strings were made by rules, not drawn from usage. A study of what is attested should not mix them in unannounced.

**What to do.** Decide before sampling, and record it in the preregistration: keep the rows and stratify by the column, leave some out, or report results with and without them.

```python
from ceolkit import draw, strata

# one stratum for each value, so that no value is lost among the others
sample, manifest = draw(universe, strata.model_or_engine, 50, "my-seed")

# or leave every marked row out of the frame before sampling
frame = universe.to_pandas()
frame = frame[frame["model_or_engine"] == "none"]
```

## 4. Mentions, not uses

This project's own pages show candidate strings: the site, the card, the documents, and the repository's vetted example list (`examples/vetted_examples.txt`). Each is a mention. The string is displayed as an object of discussion, with the sources that list it. It is not a claim that the string is a word, and it is not a label.

A mention can still reach a model's training data. A model that read those pages may have seen those strings beside the project's name. So:

- Do not draw a probe set from the vetted example list unless you mean to test exposure to it. If you do, say so.
- If you publish candidates with labels, you make the same kind of page. Decide in advance whether to release the strings with the labels, or the ids and the labels only, and write the decision in the preregistration (§11 of its template). An `id` is the first 16 hexadecimal digits of the sha256 of the word, so it names a row without printing the string.
- A string you send to a hosted model in a prompt may be kept by the service. Send only what the task needs, and record the service and its retention terms.

## 5. Dating a release by its record and file hashes

Each version has a record in the code repository, `pipeline/research/release/release_v1.0.json` for version 1.0. It holds the build date (`built_on`), the commit of the code that built it (`code.commit`), the canary (`canary`), and, for each file, its config, rows, columns, bytes, and sha256 (`files`). The card repeats the build date and the commit in §3 and the files with their sha256 in §4.

To date what you used:

1. Compute the sha256 of the file you read.

   ```python
   import hashlib

   digest = hashlib.sha256()
   with open("universe.parquet", "rb") as handle:
       for block in iter(lambda: handle.read(1 << 20), b""):
           digest.update(block)
   print(digest.hexdigest())
   ```

2. Compare it with the record's `files` entry for that config. A match means you hold the bytes of the release. A released version never changes, so a match fixes the version.
3. Read the build date from the record. It is when the files were built, not when they became public. The date they became public is in the hub's history and in the DOI's record, once those exist. A model trained only on public data cannot have used the files or the card before they were public.
4. Reason from the dates. A model whose training data ends before the dataset became public did not train on its files or its card. It may still know the strings from their earlier sources (§1).

A later version has its own record, its own hashes, and a change log in its card. Cite the version, the file's sha256, the kit's version, and the sampler's `selected_ids_sha256` in the study's report.

## 6. What to record

- the dataset version and each file's sha256;
- the kit version (`ceolkit.__version__`) and the sampler's manifest;
- every model used anywhere in the study: its name, version, training cutoff if known, the date, and the prompts;
- how `model_or_engine` was handled;
- whether the vetted example list was excluded from probes;
- the canary check, if you ran one, and its result.
