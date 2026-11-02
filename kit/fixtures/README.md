# kit/fixtures/

Samples of version 1.0's rows for the study kit's notebooks and tests.

| File | What it is |
|---|---|
| `universe_sample.parquet` | a sample of the rows of version 1.0's `universe` config, every column, with the release file's metadata |
| `features_sample.parquet` | the `features` config's rows for the single-token rows of that sample, in the same order |
| `MANIFEST.json` | the source file and its sha256, the sampling rule and its seed, and each file's sha256 |

Built by `python3 tools/build_fixtures.py`; `--check` rebuilds and compares.

The sample is drawn by the rule the kit's sampler implements: within a stratum (the intake layer), rows are ranked by `sha256(key:stratum:word)` in ascending order and the first N are taken. The key is random and kept privately, so the ranking cannot be recomputed from committed values. The site's sample is the head of the same ranking. The figures and the cube are the pipeline's: `pipeline/research/release/figures/v1.0/`.
