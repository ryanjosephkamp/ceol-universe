# CEOL Universe

Word lists disagree about what counts as an English word. The CEOL Universe (the Common English OpenList Universe) is an inventory of 10,264,249 candidate English strings. For each one, it records which of 8 published word lists include it, whether 2 corpora contain it, and how it entered the dataset. No row claims that a string is a word: you state a definition, and the inventory gives you the list that meets it, with the code that reproduces it.

**The full dataset is not published yet.** A license review comes first, and the dataset will be released when it is finished; no date is promised. Until then, this repository and [the site](https://common-english-openlist.pages.dev/) show the code, the documents, the dataset's statistics, and a sample, and lists can't be built or downloaded. Version 1.0 is built. Its home will be [`ryanjosephkamp/ceol-universe`](https://huggingface.co/datasets/ryanjosephkamp/ceol-universe) on Hugging Face; that link, and the links to it in the documents, will work once it is released. The data itself is not in this repository.

This repository holds the code that builds the dataset, the site, the study kit, and the documents.

## Where to start

| To | Read |
|---|---|
| look a string up, or compose a list and get its count and code | [the site](https://common-english-openlist.pages.dev/) |
| know what the dataset holds, how it was built, and what it leaves out | [the dataset card](pipeline/research/release/CARD_v1.0.md) |
| see every column | [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) |
| read the technical report | [pipeline/research/release/report/PAPER_v1.0.md](pipeline/research/release/report/PAPER_v1.0.md) |
| draw a reproducible sample and run a labeling study | [kit/README.md](kit/README.md) |
| see how the universe is kept over time | [docs/UPKEEP.md](docs/UPKEEP.md) |
| see each source's terms and what the dataset withholds | [the dataset card](pipeline/research/release/CARD_v1.0.md), sections 6 and 7 |
| see the evidence behind the license readings | [docs/licenses/](docs/licenses/) |
| see what the archival folder holds | [reference/README.md](reference/README.md) |
| see how the fixtures were built | [site/fixtures/README.md](site/fixtures/README.md), [kit/fixtures/README.md](kit/fixtures/README.md) |
| see how the site is built | [site/README.md](site/README.md) |

## Load it

Once the dataset is released, load any of its 7 configs from Python:

    from datasets import load_dataset

    rows = load_dataset(
        "ryanjosephkamp/ceol-universe",
        "universe",
        revision="v1.0",
        split="candidates",
    )
    print(rows.num_rows)  # 10,264,249

The configs are `universe`, `features`, `panel-listed`, `eol-valid`, `spaced`, `exceptions`, and `sample`. To load only the rows you need, compose a list on [the site](https://common-english-openlist.pages.dev/compose/) and copy its code.

## Build and test

The code runs on Python 3.11 with the packages in `requirements.txt`.

    pip install -r requirements.txt
    make test      # the pipeline's tests and the kit's
    make figures   # every figure a document quotes, re-derived from the code
    make links     # every relative link in the documents
    make check     # all of the above, plus the scan for withheld material

The build reads the dataset's layers from `data/` and checks them against lists in `private/`; neither is in the repository, and both are ignored by git. In a checkout that has neither, `make test`, `make figures`, and `make links` run every test and check that needs no layers; the others are skipped or deferred, and each says so. The scan can't run without the lists in `private/`, so in a public clone `make check` stops at the scan with an error after the other three pass. `make site` builds the site and the report's PDF (Node 22, pnpm, and Chrome).

## Related

The English OpenList, the word list this grew out of, is its own project, with its own [repository](https://github.com/ryanjosephkamp/english-openlist) and [site](https://english-openlist.pages.dev/). The CEOL Universe holds a dated copy of it as the `eol-valid` config.

## Cite

`CITATION.cff` gives the citation. The DOI will be minted at the release. Until then, cite Ryan Kamp, *The CEOL Universe*, version 1.0, Hugging Face dataset `ryanjosephkamp/ceol-universe`, built November 13, 2026.

## Licenses

- The code is under the MIT license (`LICENSE`).
- The dataset, the site's text, and the documents are currently under CC BY-SA 4.0 (`LICENSE-CC-BY-SA-4.0.txt`); the technical report is under CC BY 4.0.
- The dataset draws on third-party sources under their own terms. The evidence for them is in `docs/licenses/`, and a NOTICES file ships with the dataset.

## Contact

Questions and corrections: [open an issue](https://github.com/ryanjosephkamp/ceol-universe/issues). To ask that a source or a row be withheld, corrected, or restored, write to ryanjosephkamp@gmail.com; a request is acknowledged within 7 days and acted on within 14 days of its verification (see `docs/UPKEEP.md`, section 7).
