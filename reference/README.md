# reference/

Archival construction code and records of the CEOL Universe, kept read-only. They show how universe v1 and v2 were built: the census of sources, the merge, the audit, the v1 pin, the model contest, and the census of spaced strings. The pipeline runs none of this code. It reads a few of the records, listed below.

## The files

| File | What it is |
|---|---|
| `PROVENANCE.csv` | the record of the archive's files this folder came from: each file's class (live, archival, or shared reference), git blob, sha256, and size, at the archive's commit c1e5440 |
| `IMPORT.csv` | what the import did with each of those files: copied to `pipeline/` or here, imported as a projection, held out, or not imported |
| `HELD_OUT.csv` | the files that list candidate strings and stay out of the repository, each with the reason |
| `research/`, `tests/`, `references/` | the files themselves, at the paths the archive gave them |

## Read-only

A file here equals the archive's bytes. A correction is never an edit here; it is new code in `pipeline/` or a note in a document.

Two kinds of file differ from the archive by rule:

- **Projected records.** A JSON record that holds example lists is imported with each list replaced by `{"withheld_strings": <count>}`. Every figure of the record is kept. `IMPORT.csv` gives both hashes and the count of strings withheld.
- **Text edits.** One comment that named a folder on the maintainer's machine was reworded; `IMPORT.csv` marks the file `projected` with no count of withheld strings, and gives both hashes.
- **Held files.** A file whose content is a list of candidate strings, or a Markdown record that prints strings of those example lists, is not imported. the maintainer's private build copies it to `private/held/`, where the tests that need it find it. A clone has no `private/`, and those tests skip.

## What the pipeline reads from here

- `research/census/census.json`, `research/merge/merge.json`, `research/audit/audit.json`, `research/audit/reconcile.json`, `research/universe/universe.json`, `research/space_census/space_census.json`: figures that the card's and the report's calculators quote.
- `references/MANIFEST.csv`: the references the report cites.
- `research/space_census/analyze_space_census.py` and `research/contest/data.py`: 1 constant each, loaded by `pipeline/research/archival.py`.

## Not imported

The shared-reference files that `IMPORT.csv` marks "not imported" are the archive's own working machinery: its hooks and settings, its instruction files and stop conditions, its enforcer and the enforcer's baseline, its wall module, and its question-gate module. This repository replaces them with `pipeline/safeguards/` and the figure check, which is the enforcer reduced to the documents held here.

Three live files are here and not in `pipeline/`: the lexicon design's question gate, its generator, and its test. They run only on the archive's question-gate module and on a study document, and neither is in this repository.
