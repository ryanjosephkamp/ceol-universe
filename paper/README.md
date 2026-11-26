# The CEOL Universe: an inventory of candidate English strings and the evidence for each

Ryan Kamp, November 26, 2026. [The paper (PDF, 29 pages)](ceol-universe-paper.pdf).

The paper describes version 1.0 of the CEOL Universe: its design (the spelling grammar, the evidence semantics, the
panel families and tiers, the identifier and canary), its sources and the public projection, its construction, its
contents, how the published word lists compare over the same strings, its limitations, uses, upkeep, and
availability. Its counts are those of version 1.0, built November 14, 2026, at commit `26b183d` of this repository.

## Build

```sh
cd paper
pdflatex main.tex
pdflatex main.tex
```

`main.bbl` is included, so BibTeX is optional; to rebuild the bibliography from `generated/refs_page.bib` (the site's
literature page) and `refs_added.bib`, run `pdflatex main.tex`, `bibtex main`, then `pdflatex main.tex` twice. Both
ways give the same PDF text as `ceol-universe-paper.pdf`.

Every number in the text is a macro, `\cv{key}`, defined in `generated/numbers.tex`, and every table is a file in
`generated/`. A script wrote them from version 1.0's records and files; they are not edited by hand.

## License

The paper is under CC BY 4.0, like the technical report.
