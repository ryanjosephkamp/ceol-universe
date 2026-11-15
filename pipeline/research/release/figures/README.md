# The figures files

1 folder per public version, written by `pipeline/research/release/figures.py` from the version's release files and record (`python3 -m research.release.figures --version v2.1`; `--check` rebuilds and compares). The site, the kit, and the blog post read their figures here and never type one.

## `figures.json`

`figures` is a list of `{id, value, what, source}`:

- `id` names the figure, and the same id names the same count in every version, so a page quotes `rows.by_provenance_class.neither`, never its value;
- `value` is an integer count;
- `what` says what is counted, in words;
- `source` is the file it was counted from: the version's `universe` file, its release record, or the projection's code.

## `cube.json`

The count of rows for every combination of the dimensions, over all rows of the version: the data behind "compose a list". `dimensions` is a list of `{name, values}`. A cell is 1 index into each dimension's `values`, in order, followed by the count of rows. A filter is answered by summing the cells whose values pass it. `panel_sets` holds the published sets that list a row, joined by `;`, so "listed by wordnet" is every cell whose `panel_sets` value, split at `;`, includes the name `wordnet`. `length` and `token_count` carry a last value for everything at or above the cap that `caps` gives.
