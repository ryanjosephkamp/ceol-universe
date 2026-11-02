# site/fixtures/

A sample of version 1.0's rows for building the site's lookup.

| File | What it is |
|---|---|
| `rows.jsonl` | a sample of the rows of version 1.0's `universe` config, 1 JSON object per line, every column of the config |
| `MANIFEST.json` | the source file and its sha256, the sampling rule and its seed, and each file's sha256 |

Built by `python3 tools/build_fixtures.py`; `--check` rebuilds and compares. The rows are a sample for building the lookup. They are not the vetted example list, so no page quotes one as an example.

The figures and the cube for "compose a list" are not here: the pipeline writes them to `pipeline/research/release/figures/v1.0/`; `pipeline/research/release/figures.py` says what each file holds.
