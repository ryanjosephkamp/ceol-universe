"""The NOTICES file of a public version: every notice, license, and credit
the pinned sources require of a copy of the data (the archive's C-079 line
2(d)).

    python3 -m research.release.notices --version v1.0          write it
    python3 -m research.release.notices --version v1.0 --check  rebuild and compare

It writes `research/release/NOTICES_<version>.md`, which the release build
copies beside the Parquet files as NOTICES.md. Every input is a pinned file,
or a text the license review saved at the pinned source's commit, and each
is held to its sha256 before it is read. The texts that must travel verbatim
(WordNet's license, SCOWL's `Copyright` file, wordfreq's license section)
are copied verbatim; the rest are the credits the review sets out. In a
clone the inputs are absent: the check is then a declared deferral and the
committed file stands.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import sys
import tarfile
import zipfile
from pathlib import Path

from ceol.ingest.common import EOL_REPO, NLTK_WORDNET_ZIP, input_path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "research" / "release"
EOL_RAW = EOL_REPO / ".cache" / "sources" / "raw"
CEOL_RAW = REPO / ".cache" / "raw"
#: the saved license texts (`CEOL_EVIDENCE_DIR`)
EVIDENCE = input_path("CEOL_EVIDENCE_DIR", "license-evidence")

#: the pinned files the notices are read from, with their sha256 (the EOL
#: manifest's for the first 2; docs/licenses/EVIDENCE.csv's for the README;
#: the installed distribution's METADATA for wordfreq, its wheel pinned by
#: the EOL manifest)
WORDNET_ZIP = ("wordnet.zip", [NLTK_WORDNET_ZIP],
               "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59")
SCOWL_TAR = ("scowl-2020.12.07.tar.gz",
             [CEOL_RAW / "scowl-2020.12.07.tar.gz", EOL_RAW / "scowl-2020.12.07.tar.gz"],
             "5587667caa20c4891390c2d42dbb4d5c4c3f41bee77af1457ece3ba23fb859cc")
EN_GB_README = ("README_en_GB.txt at LibreOffice dictionaries f2ff9905",
                [EVIDENCE / "o5-hunspell" /
                 "github_LibreOffice_dictionaries_f2ff99058268_en_README_en_GB.txt_2026-10-18.txt"],
                "18b5833de60a52ffcb6e5b6b5048bb5a5d910acfecd5b096985b77058223880c")
WORDFREQ_METADATA_SHA256 = \
    "fab1698966706a4b5fbfc9e50f7b4eafd96d78b21f75d491235b477bc26081e1"

#: the excerpts, as 1-based inclusive line ranges of each text
EN_GB_LINES = ((1, 28), (153, 172), (215, 215))
ENABLE_LINES = (104, 118)
WORDFREQ_LINES = (484, 532)


class InputAbsent(RuntimeError):
    """A pinned input is not on this machine (a clone)."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(spec) -> bytes:
    name, paths, sha = spec
    for path in paths:
        if path.exists():
            data = path.read_bytes()
            if _sha(data) != sha:
                raise SystemExit(f"{name}: {path} is not the pinned file "
                                 f"(sha256 {_sha(data)})")
            return data
    raise InputAbsent(name)


def ranges_in_words(ranges) -> str:
    """Line ranges as the prose names them: "lines 1 to 28, 153 to 172, and
    215" (a 1-line range is its number), so the text never repeats the
    constants by hand."""
    parts = [f"{a}" if a == b else f"{a} to {b}" for a, b in ranges]
    if len(parts) == 1:
        return f"lines {parts[0]}"
    return f"lines {', '.join(parts[:-1])}, and {parts[-1]}"


def _lines(text: str, ranges) -> str:
    """The lines of `ranges` (1-based, inclusive), an omission marked
    between 2 ranges."""
    rows = text.split("\n")
    parts = []
    for k, (a, b) in enumerate(ranges):
        if k:
            parts.append(f"[lines {ranges[k - 1][1] + 1} to {a - 1} omitted]")
        parts.append("\n".join(rows[a - 1:b]))
    return "\n".join(parts)


def inputs() -> dict[str, str]:
    """The texts the notices quote, each from its pinned file."""
    wordnet = zipfile.ZipFile(io.BytesIO(_read(WORDNET_ZIP)))
    tar = tarfile.open(fileobj=io.BytesIO(_read(SCOWL_TAR)), mode="r:gz")

    def member(path: str, encoding: str = "utf-8") -> str:
        return tar.extractfile(path).read().decode(encoding).replace("\r\n", "\n")

    try:
        dist = importlib.metadata.distribution("wordfreq")
    except importlib.metadata.PackageNotFoundError as exc:
        raise InputAbsent("wordfreq") from exc
    metadata = dist.read_text("METADATA") or ""
    if dist.version != "3.1.1" or _sha(metadata.encode("utf-8")) != WORDFREQ_METADATA_SHA256:
        raise SystemExit("wordfreq: the installed distribution is not the "
                         "pinned 3.1.1")
    en_gb = _read(EN_GB_README).decode("utf-8").lstrip("﻿")
    return {
        "wordnet": wordnet.read("wordnet/LICENSE").decode("utf-8").replace("\r\n", "\n"),
        "scowl": member("scowl-2020.12.07/Copyright"),
        "enable": _lines(member("scowl-2020.12.07/r/enable/readme", "latin-1"),
                         (ENABLE_LINES,)),
        "en_gb": _lines(en_gb, EN_GB_LINES),
        "wordfreq": _lines(metadata, (WORDFREQ_LINES,)),
    }


def _block(text: str) -> str:
    """A verbatim text as an indented Markdown code block."""
    return "\n".join(("    " + line).rstrip() for line in text.rstrip("\n").split("\n"))


#: the internal builds, whose committed NOTICES stand as they were generated
INTERNAL_VERSIONS = frozenset({"v2.0", "v2.1"})

#: the English OpenList's MIT notice (D-018 line 2), which its license asks
#: every copy to carry
EOL_MIT_NOTICE = """MIT License

Copyright (c) 2026 Ryan Kamp

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


def render(version: str, texts: dict[str, str]) -> str:
    parts = [
        f"# NOTICES: the CEOL Universe {version}",
        "",
        "The CEOL Universe is licensed under the Creative Commons "
        "Attribution-ShareAlike 4.0 International License "
        "(https://creativecommons.org/licenses/by-sa/4.0/). Its fields are "
        "derived from the sources below. This file carries every notice, "
        "license, and credit those sources ask a copy of their data to "
        "carry, in the sources' own words where their terms require the "
        "text itself. It was generated by `research/release/notices.py` from "
        "the pinned files.",
        "",
        "Several lists the build measured are not published in any form in "
        "this dataset, and no notice of theirs is needed here; the card says "
        "which and why.",
        "",
        "## The English Wiktionary",
        "",
        "The fields `wiktionary_english`, `wikt_title_screen`, "
        "`wikt_title_any`, `wk_proper_noun`, and `wk_flags`, and the listing "
        "of the spaced rows, are derived from the English Wiktionary's "
        "pages-articles dump and all-titles list of the run of August 1, "
        "2026 (https://dumps.wikimedia.org/enwiktionary/). The text of "
        "Wiktionary is written by its contributors and is available under "
        "the Creative Commons Attribution-ShareAlike License "
        "(https://creativecommons.org/licenses/by-sa/4.0/) and the GNU Free "
        "Documentation License, under the Wikimedia Foundation's Terms of "
        "Use (https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use). "
        "Each page's history lists its authors "
        "(https://en.wiktionary.org/wiki/Special:History). The fields here "
        "are derived from the pages and are not their text; they were "
        "modified by extraction under the CEOL grammar.",
        "",
        "The channel label `eol:dictionary-api:free-dictionary` records that "
        "the Free Dictionary API (https://dictionaryapi.dev/), which draws "
        "its entries from the English Wiktionary under the same license, "
        "returned an entry for the string to the English OpenList.",
        "",
        "## WordNet 3.0 (Princeton University)",
        "",
        "The fields `wordnet`, `wn_instance`, and `wn_capitalized`, and the "
        "listing of the spaced rows, are derived from WordNet 3.0, as nltk "
        "distributes it. Its license, verbatim:",
        "",
        _block(texts["wordnet"]),
        "",
        "## SCOWL 2020.12.07 (Kevin Atkinson), and the en_US, en_CA, and en_AU hunspell dictionaries",
        "",
        "The field `scowl_tier` is derived from SCOWL 2020.12.07, and the "
        "fields `hunspell_en_US`, `hunspell_en_CA`, and `hunspell_en_AU` from "
        "the LibreOffice hunspell dictionaries, whose READMEs state that they "
        "come directly from SCOWL and are under SCOWL's copyright. SCOWL's "
        "`Copyright` file, verbatim, with the notices of its components "
        "(among them the UK Advanced Cryptics Dictionary's, which must be "
        "included verbatim, and WordNet 1.6's):",
        "",
        _block(texts["scowl"]),
        "",
        "## The en_GB hunspell dictionary (Marco A.G. Pinto and others)",
        "",
        "The field `hunspell_en_GB` is derived from the LibreOffice en_GB "
        "hunspell dictionary. Its README's license statement and its credits "
        f"for added place names, verbatim ({ranges_in_words(EN_GB_LINES)} "
        "of the README at LibreOffice dictionaries commit `f2ff9905`):",
        "",
        _block(texts["en_gb"]),
        "",
        "## ENABLE",
        "",
        "The field `enable1` is derived from the ENABLE word list. Its "
        "public-domain statement, verbatim, as SCOWL 2020.12.07 carries its "
        f"readme ({ranges_in_words((ENABLE_LINES,))}). Its authors ask to be "
        "credited as the "
        "originators of the list: Alan Beale, its researcher and compiler, "
        "and M. Cooper, the package's maintainer.",
        "",
        _block(texts["enable"]),
        "",
        "## wordfreq 3.1.1 (Robyn Speer), and SUBTLEX",
        "",
        "The fields `wordfreq_zipf` and `wordfreq_scored` are derived from "
        "wordfreq 3.1.1, by Robyn Speer: Robyn Speer. (2022). rspeer/wordfreq: "
        "v3.0 (v3.0.2). Zenodo. https://doi.org/10.5281/zenodo.7199437. The "
        "license section of its README, verbatim, with the terms of the data "
        "it contains:",
        "",
        _block(texts["wordfreq"]),
        "",
        "wordfreq's data includes the SUBTLEX word lists, created by Marc "
        "Brysbaert and his colleagues, which wordfreq distributes by the "
        "author's permission on 2 conditions: that wordfreq and code derived "
        "from it credit the SUBTLEX authors, and that it remain clear that "
        "SUBTLEX is freely available data. The page wordfreq's README names "
        "is no longer served; its last capture by the Internet Archive is "
        "https://web.archive.org/web/20231116144719/http://crr.ugent.be/programs-data/subtitle-frequencies "
        "(November 16, 2023). SUBTLEX-US is offered at "
        "https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus "
        "and SUBTLEX-UK at https://osf.io/zq49t/. The authors' current copies "
        "carry the license CC BY-NC-SA 4.0; this dataset's values come "
        "through wordfreq 3.1.1, under wordfreq's statement of the "
        "permission.",
        "",
        "## The Google Books Ngram corpus",
        "",
        "The `gb_` fields of the features config, `zipf_log10_rank`, "
        "`zipf_resid`, and `gb_type` are aggregates per string of the Google "
        "Books Ngram corpus, English 1-grams, version 20200217 "
        "(googlebooks-eng-20200217; "
        "https://storage.googleapis.com/books/ngrams/books/datasetsv3.html). "
        "The export page states: \"This compilation is licensed under a "
        "Creative Commons Attribution 3.0 Unported License\" "
        "(http://creativecommons.org/licenses/by/3.0/). The values are "
        "derived from it. The corpus is described by Jean-Baptiste Michel "
        "and colleagues, \"Quantitative Analysis of Culture Using Millions "
        "of Digitized Books\", Science 331 (2011).",
        "",
        "## The English OpenList",
        "",
        "The strings inherited from the English OpenList at its pinned "
        "revision `c1139698` (https://huggingface.co/datasets/ryanjosephkamp/english-openlist), "
        "and the `eol` fields and `eol:` channel labels derived from its "
        "dictionaries, come from that dataset, whose card states: \"This "
        "dataset is released under the **MIT License**.\"",
        "",
    ]
    if version not in INTERNAL_VERSIONS:
        parts += [
            "Its notice, as the English OpenList's author gives it:",
            "",
            "```text",
            EOL_MIT_NOTICE,
            "```",
            "",
        ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", default="v1.0")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the committed file")
    args = ap.parse_args(argv)
    out = OUT_DIR / f"NOTICES_{args.version}.md"
    try:
        text = render(args.version, inputs())
    except InputAbsent as exc:
        print(f"notices: the pinned input {exc} is absent here; the committed "
              f"{out.name} stands (a declared deferral)")
        return 0
    if args.check:
        same = out.exists() and out.read_text(encoding="utf-8") == text
        print(f"notices: {out.name} {'reproduces' if same else 'DIFFERS'}")
        return 0 if same else 1
    out.write_text(text, encoding="utf-8")
    print(f"notices: {out.name} written, {len(text.encode('utf-8'))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
