# site/

The site of the Common English OpenList family: the CEOL Universe, with the English OpenList as one of its sections. Astro with React islands, built as static pages for Cloudflare Pages.

| Path | What it is |
|---|---|
| `src/pages/` | the pages: Start, Explore, Compose a list, Compose from the open subset (`compose/open.astro`), the dataset section (`dataset/`), How it was built, Definitions (`definitions/`, with the in-the-wild definition), Research (`research/`: the sources compared, the technical report, the literature, the proposed study), Run a study (`study/`, the kit's documents), the English OpenList, and About; `data/` writes the cubes, the sample rows, and the notices at build time |
| `src/islands/` | the interactive parts: the composer (`Compose.tsx`), the open subset's composer (`ComposeOpen.tsx`), the list download's button (`ZipDownload.tsx`, which both composers use), the profile (`Profile.tsx`), the lookup (`Explore.tsx`), the grammar box (`GrammarBox.tsx`), the English OpenList's charts, the Start page's teaser, and the research figures (`ResearchFigure.tsx`: the containment heat map, the intersection plot, coverage by frequency, agreement, the union's growth, intake by tier) |
| `src/charts/` | the chart components: bars, columns, a comparison of shares, and the to-scale squares; each chart has a table view |
| `src/lib/cube.ts` | the engine: every count of every filter, computed exactly from the cube (`pipeline/research/release/figures/v1.0/cube.json`) |
| `src/lib/codegen.ts` | the DuckDB, Polars, and pandas code for a selection |
| `src/lib/datasheet.ts` | a composed list's datasheet (definition, counts, every distribution, code, provenance) as the page draws it and as Markdown and CSV; the page is `src/pages/compose/datasheet.astro` |
| `src/lib/list-*.ts` | the list download: the row test that mirrors the code (`list-filter.ts`), the byte-range reader (`list-read.ts`), the zip (`list-zip.ts`), and the worker that runs them (`list-download.worker.ts`), for the universe file and for the open subset's |
| `src/lib/open-*.ts` | Compose from the open subset: its cube engine (`open-cube.ts`, over `pipeline/research/release/open_cube_v1.0.json`), its code (`open-codegen.ts`), its row test (`open-filter.ts`), its address (`open-url.ts`), and its datasheet (`open-datasheet.ts`) |
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
| `test-files/open-test/` | a made-up file in the open subset's `open-lists` columns (90 rows of synthetic strings in 2 row groups, nothing from the dataset) and its layout, which the list download's mocked-HTTP test reads; built by `python3 tools/build_open_test_file.py` (`--check` rebuilds and compares) |

## Rules every page keeps

- **Every count is exact.** The interactive pages compute from 2 cubes, each the joint count of every row of its file: the universe's, over 12 dimensions (`pipeline/research/release/figures/v1.0/cube.json`), for Compose a list and the other universe pages, and the open subset's, over 8 dimensions of its `open-lists` config (`pipeline/research/release/open_cube_v1.0.json`), for Compose from the open subset. `src/lib/cube.test.ts` holds the first engine to the figures file, and `src/lib/open-cube.test.ts` the second to the subset's record; other code computes both from the files.
- **The generated code has been run, on the local files, not against the hub.** For Compose a list, `src/lib/codegen.test.ts` runs the DuckDB, Polars, and pandas code on version 1.0's own universe file for 47 selections (23 fixed, 24 drawn with a fixed seed; pandas on the 23 fixed), and each count must equal the cube's: it compares counts. For Compose from the open subset, `src/lib/open-download.test.ts` runs the DuckDB, Polars, and pandas code on the subset's own `open-lists` file for 53 selections (29 fixed, 24 drawn; pandas on all 53, with the local file in place of the hub's `load_dataset` and pandas' default types), and each must return the same strings in the same order as DuckDB (the count and the SHA-256 of the lines), and only the strings.
- **The download returns the code's rows.** `src/lib/list-download.test.ts` holds the strings the universe's download keeps to the strings DuckDB returns for the generated code, line for line, for 35 selections (the 23 fixed and 12 drawn), and reads 3 lists by byte range into a zip. `src/lib/open-download.test.ts` does the same for the open subset's 53 selections and 3 lists, and holds the layout's spans to the file's footer. These 3 tests need the data files (`data/`, and the subset's file, which `open_subset.py` writes beside `data/`) and uv; without them they are skipped and say so.
- **The download's parts are tested without the data.** `src/lib/download-mocked.test.ts` runs the whole download, from the range requests and the footer's checks through the windows, the row test, the count's check, and the zip, to the worker's own code, on a small made-up file (`test-files/open-test/`) through mocked HTTP answers, with its refusals; `src/lib/range-fetch.test.ts` holds each range answer to the bytes asked for; `src/lib/download-session.test.ts` holds Cancel, a new list, and leaving the page to ending the attempt; and `src/lib/open-cube.test.ts` holds the open cube to the subset's own record and each count beside a choice to what its note says. These need neither data nor Python, and `.github/workflows/checks.yml` runs `pnpm test` on every pull request.
- **Every reference figure comes from a data file at build time.** The figures the pages quote, as opposed to the composers' counts, which come from the cubes in the browser: `fig(id)` in `src/lib/data.ts` reads the version's figures file, `pipeline/research/release/figures/v1.0/figures.json`, and an id the file does not hold stops the build. "Show figure sources" in the footer shows each figure's id beside it.
- **Example strings come from the vetted example list alone** (`examples/vetted_examples.txt`). The sample rows are data for the lookup, shown when a visitor searches; the only strings a page offers unasked are vetted ones.
- **A string of the universe is a candidate.** No page calls one a valid word.

## Build and test

Node 22 or later and pnpm 11.7. The grammar's test also runs `python3` on `pipeline/ceol/grammar.py`.

```sh
pnpm install --frozen-lockfile
pnpm test       # the grammar against grammar.py, the lookup's modes, the cube engines, the generated code, the list downloads
pnpm build      # the pages into dist/
python3 ../tools/report_pdf.py   # the technical report's PDF, printed from its built page (needs Chrome)
pnpm dev        # a local preview at http://localhost:4321
```

## The list download

### From the open subset

"Download the list" on Compose from the open subset (`/compose/open/`) works on any deployment of the site, preview or production, because the subset is public. It reads the list in the visitor's browser from the open subset's `open-lists` file on the Hugging Face hub, pinned to the commit the subset was uploaded at (`https://huggingface.co/datasets/ryanjosephkamp/ceol-universe-open/resolve/<commit>/data/open-lists.parquet`), and saves a zip: `list.txt` (1 string per line, in the code's order), `DATASHEET.md` (the criteria, the count, the distributions, the code, the dataset and commit, the license, and the attribution the file's own metadata carries), and the subset's `NOTICES.md`, verbatim. The page decodes only the strings and the columns the criteria use. It requests them by byte range, merging chunks less than 64 KB apart into 1 request, so a request also carries the chunks between them, and it reads the file's last 512 KB for its footer: about 7 MB of the file's 18.9 MB for a typical list, 7.9 MB with every criterion. It tests a row group's rows in batches (windows) of 131,072 and hands on each batch's kept strings, testing each row through 1 reused object, so it never builds an object per row. A column's pages are decoded whole, 1 column at a time, and kept while they still hold the next batch's rows, a column of few distinct values at a byte a row: in the open subset's file each small column is 1 page for its whole row group, so that page stays decoded for the group; the same reader serves the universe's download. The counts come from the subset's cube, so no row is fetched to count, and the page refuses to save a list whose rows differ from its count.

Both files it reads are made from the subset's file by `python3 -m research.release.open_compose` (from `pipeline/`), which holds the file to the sha256 the subset's record and its upload's record name first:

- `pipeline/research/release/open_cube_v1.0.json`, the cube (counts only; `src/pages/data/cube-open-v1.0.json.ts` serves it);
- `pipeline/research/release/layout_open_v1.0.json`, where each column lies in each row group, with the commit, the file's address, and its license and attribution.

`--check` rebuilds both and compares; `pipeline/tests/test_open_compose.py` runs it where the subset's file is present. The notices are `pipeline/research/release/NOTICES_open_v1.0.md`, served by `src/pages/data/NOTICES-open-v1.0.md.ts`, which stops the build if its sha256 is not the one the upload's record gives for the hub's `NOTICES.md`.

### From the universe

"Download the list" on Compose a list reads the composed list in the visitor's browser, from the version's universe file on the Hugging Face hub, and saves a zip: `list.txt` (1 string per line, in the code's order), `DATASHEET.md`, and `NOTICES.md`. There is no server. The page decodes only the strings and the columns the criteria use, and requests them by byte range a row group at a time, merging nearby chunks as the open subset's download does; where they lie is recorded in `pipeline/research/release/layout_v1.0.json` (`python3 -m research.release.layout --version v1.0`, from `pipeline/`). It refuses to save a list whose rows differ from the page's count. No row is ever shown on a page.

Until the dataset is public, the hub cannot serve the file, so the button says it opens with the release. To try it before then against the local file:

```sh
python3 tools/serve_range.py data/release/ceol-universe-v1.0/universe.parquet 8766   # from the repository's root
PUBLIC_LIST_SOURCE=http://127.0.0.1:8766/universe.parquet pnpm dev
```

`PUBLIC_LIST_SOURCE` is read in a dev build only. At the release, set `DATASET_PUBLIC` to `true` in `src/lib/release-state.ts`; the button then reads `https://huggingface.co/datasets/ryanjosephkamp/ceol-universe/resolve/v1.0/data/universe.parquet`.

## Deployment

The site is a Cloudflare Pages project, `common-english-openlist`, uploaded from a checkout with wrangler, so no GitHub Actions minutes are spent. Until the site is put on its main address, it is deployed only as a preview for review: previews go to the branch `review`, at `review.common-english-openlist.pages.dev`, and the main address stays empty. Every preview page carries `noindex` and a banner saying it is a preview.

```sh
make site-preview    # from the repository's root: the review preview
make site-production # the main address: no preview banner, no noindex
```

Each runs the tests, builds the pages, runs the repository's scan over `dist/`, and uploads only when the scan is clean, since the built pages are what a deployment publishes.

Two steps are separate:

- **The site on its main address.** It doesn't wait for the full dataset's release. Compose from the open subset reads only the open subset, which is public, so a production deployment works before the license review ends. Every page then carries the pending note (`PENDING_NOTE` in `src/lib/release-state.ts`): the full dataset is not published yet, and lists can be composed and downloaded from the open subset.
- **The full dataset's release.** It sets `DATASET_PUBLIC` to `true`, which opens the universe's download and drops the pending note. The full lookup over every row and the remaining sections come with it.

The open subset's own dates are distinct: it was built on November 25, 2026 (its card); its files were uploaded to the hub at commit `0bbf4b8` on November 26, 2026 (`pipeline/research/release/hf_upload_open_v1.0.json`, which records the dataset as still private when the upload was verified); and it was made public on the hub after that, a change this repository's records don't date.
