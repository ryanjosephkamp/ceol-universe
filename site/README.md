# site/

The site of the Common English OpenList family: the CEOL Universe, with the English OpenList as one of its sections. Astro with React islands, built as static pages for Cloudflare Pages.

| Path | What it is |
|---|---|
| `src/pages/` | the pages: Start, Explore, Compose a list, the dataset section (`dataset/`), How it was built, Definitions (`definitions/`, with the in-the-wild definition), Research (`research/`: the sources compared, the technical report, the literature, the proposed study), Run a study (`study/`, the kit's documents), the English OpenList, and About; `data/` writes the cube and the sample rows at build time |
| `src/islands/` | the interactive parts: the composer (`Compose.tsx`), the profile (`Profile.tsx`), the lookup (`Explore.tsx`), the grammar box (`GrammarBox.tsx`), the English OpenList's charts, the Start page's teaser, and the research figures (`ResearchFigure.tsx`: the containment heat map, the intersection plot, coverage by frequency, agreement, the union's growth, intake by tier) |
| `src/charts/` | the chart components: bars, columns, a comparison of shares, and the to-scale squares; each chart has a table view |
| `src/lib/cube.ts` | the engine: every count of every filter, computed exactly from the cube (`pipeline/research/release/figures/v1.0/cube.json`) |
| `src/lib/codegen.ts` | the DuckDB, Polars, and pandas code for a selection |
| `src/lib/datasheet.ts` | a composed list's datasheet (definition, counts, every distribution, code, provenance) as the page draws it and as Markdown and CSV; the page is `src/pages/compose/datasheet.astro` |
| `src/lib/list-*.ts` | the list download: the row test that mirrors the code (`list-filter.ts`), the byte-range reader (`list-read.ts`), the zip (`list-zip.ts`), and the worker that runs them (`list-download.worker.ts`) |
| `src/lib/release-state.ts` | whether the dataset is public yet, which opens the list download and drops the "private until the release" notes |
| `src/lib/data.ts` | every figure, example, and sample row the pages read, from the files the pipeline writes |
| `src/lib/docs.ts` | the card and the data dictionary, rendered from their own files |
| `src/lib/analysis.ts` | the descriptive analysis (`pipeline/research/release/figures/v1.0/analysis.json`), read by id at build time |
| `src/lib/study.ts` | the proposed study's pages (`content/study/`), their figures filled from `content/study/figures.json`, which `tools/study_figures.py` prints from the study's own calculator |
| `src/lib/kit.ts` | the study kit's documents (`kit/*.md`), rendered for Run a study |
| `content/` | the text of the pages that are not generated: the proposed study, the in-the-wild definition, and the literature |
| `src/lib/grammar.ts` | the spelling grammar in TypeScript, held to `pipeline/ceol/grammar.py` by its test |
| `src/styles/global.css` | the tokens: color in both themes, type, and space |
| `fixtures/` | a sample of version 1.0's rows for the lookup, built by `tools/build_fixtures.py`; `fixtures/MANIFEST.json` says how it was drawn |

## Rules every page keeps

- **Every count is exact.** The interactive pages compute from the cube, the joint count of every row over 12 dimensions; `src/lib/cube.test.ts` holds the engine to the figures file, which other code computes from the release files.
- **Every snippet has been run.** `src/lib/codegen.test.ts` runs the generated DuckDB, Polars, and pandas code on version 1.0's own universe file for a battery of selections, and each count must equal the cube's. It needs `data/` and uv; without them it is skipped and says so.
- **The download returns the code's rows.** `src/lib/list-download.test.ts` holds the strings the list download keeps to the strings DuckDB returns for the generated code, line for line (count and SHA-256), on version 1.0's own file, and reads 3 lists by byte range into a zip. Like the code's test, it needs `data/` and uv.
- **Every figure comes from a data file at build time.** `fig(id)` in `src/lib/data.ts` reads the version's figures file, `pipeline/research/release/figures/v1.0/figures.json`, and an id the file does not hold stops the build. "Show figure sources" in the footer shows each figure's id beside it.
- **Example strings come from the vetted example list alone** (`examples/vetted_examples.txt`). The sample rows are data for the lookup, shown when a visitor searches; the only strings a page offers unasked are vetted ones.
- **A string of the universe is a candidate.** No page calls one a valid word.

## Build and test

Node 22 or later and pnpm 11.7. The grammar's test also runs `python3` on `pipeline/ceol/grammar.py`.

```sh
pnpm install --frozen-lockfile
pnpm test       # the grammar against grammar.py, the lookup's modes, the cube engine, the generated code
pnpm build      # the pages into dist/
python3 ../tools/report_pdf.py   # the technical report's PDF, printed from its built page (needs Chrome)
pnpm dev        # a local preview at http://localhost:4321
```

## The list download

"Download the list" on Compose a list reads the composed list in the visitor's browser, from the version's universe file on the Hugging Face hub, and saves a zip: `list.txt` (1 string per line, in the code's order), `DATASHEET.md`, and `NOTICES.md`. There is no server. The page reads only the strings and the columns the criteria use, by byte range, a row group at a time; where they lie is recorded in `pipeline/research/release/layout_v1.0.json` (`python3 -m research.release.layout --version v1.0`, from `pipeline/`). It refuses to save a list whose rows differ from the page's count. No row is ever shown on a page.

Until the dataset is public, the hub cannot serve the file, so the button says it opens with the release. To try it before then against the local file:

```sh
python3 tools/serve_range.py data/release/ceol-universe-v1.0/universe.parquet 8766   # from the repository's root
PUBLIC_LIST_SOURCE=http://127.0.0.1:8766/universe.parquet pnpm dev
```

`PUBLIC_LIST_SOURCE` is read in a dev build only. At the release, set `DATASET_PUBLIC` to `true` in `src/lib/release-state.ts`; the button then reads `https://huggingface.co/datasets/ryanjosephkamp/ceol-universe/resolve/v1.0/data/universe.parquet`.

## The review preview

Until the release, the site is deployed only as a preview for review: a Cloudflare Pages project, `common-english-openlist`, uploaded from a checkout with wrangler, so no GitHub Actions minutes are spent. Previews go to the branch `review`, at `review.common-english-openlist.pages.dev`; the project's main address stays empty until the release. Every page carries `noindex` and a banner saying it is a preview.

```sh
make site-preview    # from the repository's root
make site-production # at the release: no banner, no noindex, the main address
```

It runs the tests, builds the pages, runs the repository's scan over `dist/`, and uploads only when the scan is clean, since the built pages are what a deployment publishes.

The full lookup over every row, the remaining sections, and the move to the main address come with the release.
