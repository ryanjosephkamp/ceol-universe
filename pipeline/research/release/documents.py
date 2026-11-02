"""The documents of a public version that are generated, never written by
hand (the project plan, item 6):

- the data dictionary, `docs/DATA_DICTIONARY.md`, from the columns module
  (`columns.py`) and the public projection (`withholding.py`);
- `CITATION.cff` at the repository's root;
- the Croissant file, `research/release/croissant_<version>.json`, the
  dataset's machine-readable description (MLCommons Croissant 1.0).

Each reads the committed release record of the version, so each re-derives
in a fresh clone. No figure is typed here: a count is the record's, a
column's meaning the columns module's, and the meanings the projection
changes are stated once, in `PUBLIC_MEANINGS`. No word is printed.

    python3 -m research.release.documents --version v2.1          write them
    python3 -m research.release.documents --version v2.1 --check  compare
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from research.release import build_release as B
from research.release import columns as C
from research.release import withholding as W

REPO = B.REPO
ROOT = REPO.parent
DICTIONARY = ROOT / "docs" / "DATA_DICTIONARY.md"
CITATION = ROOT / "CITATION.cff"
HUB = f"https://huggingface.co/datasets/{B.DATASET}"
CODE = "https://github.com/ryanjosephkamp/ceol-universe"
#: where requests to withhold, correct, or restore go (D-017)
CONTACT = "ryanjosephkamp@gmail.com"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
TITLE = "The CEOL Universe"


def record_of(version: str) -> dict:
    spec = B.resolve(version)
    if not spec.public:
        raise B.ReleaseError(f"{version} is not a public version")
    return json.loads(spec.record_out.read_text(encoding="utf-8"))


def croissant_path(version: str) -> Path:
    return REPO / "research" / "release" / f"croissant_{version}.json"


# ---------------------------------------------------------------------------
# The public meanings
# ---------------------------------------------------------------------------

_SETS = ", ".join(W.PUBLISHED_SETS)

#: The meanings a public version gives the columns its projection changes,
#: in place of `columns.py`'s, which describe the full projection of v2.0
#: (D-010, D-011): name to (meaning, null).
PUBLIC_MEANINGS: dict[str, tuple[str, str]] = {
    "sources": (
        "provenance at intake: for the CEOL's own layers the published "
        "sources whose derived sets contain the string, joined by ';', a "
        "withheld list's label removed (the empty string where each such "
        "source is withheld); for the strings inherited from the EOL the "
        "dataset-level tag eol_universe@c1139698 (their per-source "
        "listedness is the evidence columns')",
        "never null"),
    "panel_sets": (
        f"the published panel sets that list the row, joined by ';' in the "
        f"order {_SETS}; on a single-token row a binary set lists the row "
        f"where its evidence column is 1 and SCOWL where scowl_tier is above "
        f"0; on a spaced row the sets are the pin's published sources; the "
        f"empty string where none lists the row. A withheld list is never "
        f"named",
        "never null"),
    "panel_count": (
        f"the number of the {len(W.PUBLISHED_SETS)} published panel sets "
        f"that list the row (the number of names in panel_sets, asserted "
        f"equal on every row); a withheld list's listing is not counted",
        "never null"),
    "intake_channels": (
        "the first-seen channel labels joined by ';': the EOL's discovery "
        "log with its tiers removed, and the CEOL layers' own namespaces "
        "census:, audit:, spaced:, ledger:; a record of where a string was "
        "first seen, never an attestation. A label naming a withheld "
        f"list is removed, and so is a channel withheld for license reasons; "
        f"a row whose every label was withheld carries the single label "
        f"{W.CHANNEL_WITHHELD}",
        "never null"),
    "provenance_class": (
        "exactly 1 of channel_and_containment, channel_only, "
        "containment_only, neither, over the published fields: whether the "
        f"row has a published intake channel (a label other than "
        f"{W.UNRECORDED} and {W.CHANNEL_WITHHELD}) and whether a published "
        "panel set or a corpus contains it",
        "never null"),
}


#: A decision code (C-001 and on, D-001 and on, and the construction steps C1
#: to C4) names a record a reader of the public documents cannot open.
_ARCHIVE_CODE = re.compile(r"\bC-\d{3}\b|\bC[1-4]\b|\bD-\d{3}\b")

#: The public documents state `columns.py`'s meanings without the archive's
#: codes, which the archival card of v2.0 keeps: old text to new, in order.
PLAIN: tuple[tuple[str, str], ...] = (
    ("the output of the C-001 grammar", "the output of the grammar"),
    ("the date the row entered a CEOL artifact: 2026-08-17 the EOL "
     "universe at the pinned revision, 2026-08-20 the C1 exceptions and "
     "the C-009 audited additions, 2026-08-26 the C-016 spaced candidates",
     "the date the row entered a CEOL artifact (an ISO date): August 17, 2026 "
     "the EOL universe at the pinned revision, August 20, 2026 the census's "
     "exception candidates and the audit's additions, August 26, 2026 the "
     "spaced admission's multiword candidates"),
    ("(the 2026-08-04 dump)", "(the August 4, 2026 dump)"),
    ("a row of the audited additions of the C-009 pin",
     "a row of the audit's additions to the single-token pin"),
    ("a row of the spaced candidates admitted at C-016",
     "a row of the multiword candidates of the spaced admission"),
    ("(C-064 declares mixed for labels that disagree)",
     "(mixed where the labels disagree)"),
    ("(C-010: wordfreq is hyphen-blind)", "(wordfreq is hyphen-blind)"),
    ("Model and engine (v2.1 on)", "Model and engine"),
)


def plain(text: str) -> str:
    """`text` without the archive's codes; a code left over stops the build
    of the documents, so a new one cannot reach a public page."""
    for old, new in PLAIN:
        text = text.replace(old, new)
    text = re.sub(r" \(C-\d{3}(?: line \d+)?\)", "", text)
    if _ARCHIVE_CODE.search(text):
        raise ValueError(f"an archive code is left in a public text: {text!r}")
    return text


def public_predicate(config: str, predicate: str) -> str:
    """The predicate a reader sees for a config. The release record's predicate
    for `universe` names only the pin's restriction flag; the build also holds
    back rows (card section 6) and writes only the public columns."""
    if config == "universe":
        return ("the pin's unrestricted rows, less the rows held back (card §6), "
                "in the public columns")
    return predicate


def _public(cols: tuple[C.Column, ...]) -> tuple[C.Column, ...]:
    out = []
    for name, kind, meaning, nulls in cols:
        if name in W.WITHHELD_SETS or name in W.WITHHELD_FEATURES:
            continue
        meaning, nulls = PUBLIC_MEANINGS.get(name, (meaning, nulls))
        out.append((name, kind, plain(meaning), plain(nulls)))
    return tuple(out)


def public_tables() -> dict[str, tuple[str, tuple[C.Column, ...]]]:
    """The column tables of a public version, in `columns.TABLES`' order:
    the withheld columns left out, the changed meanings in place, and no
    archive code."""
    return {key: (plain(title), _public(cols)) for key, (title, cols)
            in C.TABLES.items()}


def universe_columns() -> tuple[C.Column, ...]:
    """The universe config's columns, in the file's order."""
    by_name = {c[0]: c for _t, cols in public_tables().values() for c in cols}
    return tuple(by_name[name] for name in B.PUBLIC.columns)


def features_columns() -> tuple[C.Column, ...]:
    by_name = {c[0]: c for c in _public(C.KEY + C.FEATURES)}
    return tuple(by_name[name] for name in ("id", "word") + B.PUBLIC.features)


def config_columns(config: str) -> tuple[C.Column, ...]:
    return features_columns() if config == "features" else universe_columns()


# ---------------------------------------------------------------------------
# The data dictionary
# ---------------------------------------------------------------------------

def _n(x: int) -> str:
    return f"{x:,}"


def data_dictionary(record: dict) -> str:
    version = record["version"]
    tables = public_tables()
    lines = [
        f"# The data dictionary of the CEOL Universe, {version}",
        "",
        f"Generated by `pipeline/research/release/documents.py` from the "
        f"columns module (`pipeline/research/release/columns.py`), the public "
        f"projection (`pipeline/research/release/withholding.py`), and the "
        f"release record (`pipeline/research/release/release_{version}.json`)"
        f". Do not edit it by hand: `make check` compares it with what the "
        f"code prints.",
        "",
        "Every row is a candidate string, never a verdict. `word` is the join "
        "key of every config, and `id` is the first 16 hexadecimal digits of "
        "the sha256 of the word, the same for the same string in every "
        "version.",
        "",
        "## The configs",
        "",
        "| Config | File | Rows | Columns | Predicate |",
        "|---|---|---:|---:|---|",
    ]
    for f in record["files"]:
        lines.append(f"| `{f['config']}` | `data/{f['path']}` | "
                     f"{_n(f['rows'])} | {len(f['columns'])} | "
                     f"{public_predicate(f['config'], f['predicate'])} |")
    lines += [
        "",
        "The filter configs (every config but `universe` and `features`) "
        "carry every column of `universe`, in its row order.",
        "",
        "## Null and NaN",
        "",
        "- **Null means not measured by that source, never false.** In the "
        "evidence columns a single-token row holds 1 (listed), 0 (not "
        "listed), or -1 (the source is structurally blind to the row's "
        "class, as a list without hyphens is to a hyphenated string). "
        "A spaced row holds null in every evidence column and in the corpus "
        "columns, because those sources were not measured over spaced rows.",
        "- **NaN in the features config** means the channel does not observe "
        "the string. It is a float value, not a null: no column of "
        "the features config holds a null.",
        "",
        "## The universe config",
        "",
        f"{len(B.PUBLIC.columns)} columns, in this order.",
    ]
    for key in ("key", "pin", "release", "provenance", "evidence", "model"):
        title, cols = tables[key]
        lines += ["", f"### {title}", "", *C.markdown_table(cols)]
    title, _cols = tables["features"]
    lines += [
        "", "## The features config", "",
        f"{len(features_columns())} columns: the key and the feature layer's "
        f"published columns, 1 row per single-token row of `universe`, in its "
        f"order.", "", f"### {title}", "",
        *C.markdown_table(features_columns()),
        "", f"## What {version} withholds", "",
        f"- **The columns of {len(W.WITHHELD_SETS)} lists** whose membership "
        f"may not be published "
        f"(see the card, section 6): "
        + ", ".join(f"`{s}`" for s in W.WITHHELD_SETS)
        + ". Their labels are removed from `sources`, `intake_channels`, "
        "and `panel_sets`, and `panel_sets`, `panel_count`, and "
        "`provenance_class` are computed over the published panel sets "
        "alone.",
        "- **Channel labels withheld for license reasons**, removed from "
        f"`intake_channels`; a row whose every label was withheld carries "
        f"`{W.CHANNEL_WITHHELD}`.",
        f"- **{len(W.WITHHELD_FEATURES)} feature columns** "
        "(`docs/licenses/FEATURE_COLUMNS.md`): the "
        f"{len(W.WITHHELD_REFERENCE_FEATURES)} computed against a reference "
        "that holds a withheld list, "
        + ", ".join(f"`{c}`" for c in W.WITHHELD_REFERENCE_FEATURES)
        + f"; and the {len(W.WITHHELD_MODEL_FEATURES)} of the character "
        "model, fitted on strings the withheld lists help choose, whose "
        "values pick out the strings those lists list: "
        + ", ".join(f"`{c}`" for c in W.WITHHELD_MODEL_FEATURES) + ".",
        "- **The rows left with no public evidence** once those are withheld, "
        "and the census and audit rows whose every source label names a "
        "withheld list; the card counts them by reason.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CITATION.cff
# ---------------------------------------------------------------------------

def citation(record: dict) -> str:
    version = record["version"]
    return "\n".join([
        f"# Generated by pipeline/research/release/documents.py from the "
        f"release record of {version}; do not edit it by hand.",
        "# The DOI and the release date are added at the release, each on the",
        "# maintainer's word.",
        "cff-version: 1.2.0",
        'message: "If you use the CEOL Universe, please cite it as below."',
        "type: dataset",
        f'title: "{TITLE}"',
        f'version: "{version}"',
        "license: CC-BY-SA-4.0",
        f'url: "{HUB}"',
        f'repository-code: "{CODE}"',
        "authors:",
        "  - family-names: Kamp",
        "    given-names: Ryan",
        "abstract: >-",
        "  A public inventory of candidate English strings, each with its",
        "  provenance: which pinned sources list it, how it entered the pool,",
        "  and its corpus features. Every row is a candidate, never a verdict.",
        "keywords:",
        "  - lexicon",
        "  - word list",
        "  - English",
        "  - lexicography",
        "  - candidate inventory",
        "",
    ])


# ---------------------------------------------------------------------------
# The Croissant file
# ---------------------------------------------------------------------------

#: The JSON-LD context of Croissant 1.0, as its specification gives it.
CROISSANT_CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
}

#: The Croissant data type of each Arrow type the columns module names.
DATA_TYPES = {"string": "sc:Text", "bool": "sc:Boolean", "int8": "sc:Integer",
              "int16": "sc:Integer", "int32": "sc:Integer",
              "float": "sc:Float"}


def croissant(record: dict) -> dict:
    version = record["version"]
    files = record["files"]
    distribution = [{
        "@type": "cr:FileObject",
        "@id": f["path"],
        "name": f["path"],
        "description": f"the {f['config']} config",
        # the version's tag, which the upload creates at its commit, so the
        # address does not move when a later version is uploaded
        "contentUrl": f"{HUB}/resolve/{version}/data/{f['path']}",
        "contentSize": f"{f['bytes']} B",
        "encodingFormat": "application/x-parquet",
        "sha256": f["sha256"],
    } for f in files]
    record_sets = []
    for f in files:
        cols = config_columns(f["config"])
        if [c[0] for c in cols] != f["columns"]:
            raise B.ReleaseError(f"{f['config']}: the record's columns are "
                                 "not the columns module's")
        record_sets.append({
            "@type": "cr:RecordSet",
            "@id": f["config"],
            "name": f["config"],
            "description": f"{public_predicate(f['config'], f['predicate'])}; {f['rows']} rows",
            "key": {"@id": f"{f['config']}/id"},
            "field": [{
                "@type": "cr:Field",
                "@id": f"{f['config']}/{name}",
                "name": name,
                "description": f"{meaning} (null: {nulls})",
                "dataType": DATA_TYPES[kind],
                "source": {"fileObject": {"@id": f["path"]},
                           "extract": {"column": name}},
            } for name, kind, meaning, nulls in cols],
        })
    return {
        "@context": CROISSANT_CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": "ceol-universe",
        "alternateName": TITLE,
        "description": (
            "A public inventory of candidate English strings, each with its "
            "provenance. Every row is a candidate, never a verdict. The card "
            "(README.md) states its limitations first."),
        "version": version,
        "license": LICENSE_URL,
        "url": HUB,
        "sameAs": CODE,
        "creator": {"@type": "Person", "name": "Ryan Kamp"},
        "citeAs": (f"Ryan Kamp, The CEOL Universe, version {version}, "
                   f"Hugging Face dataset {B.DATASET}."),
        "keywords": ["lexicon", "word list", "English", "lexicography",
                     "candidate inventory"],
        "inLanguage": "en",
        "distribution": distribution,
        "recordSet": record_sets,
    }


def croissant_text(record: dict) -> str:
    return json.dumps(croissant(record), indent=1, ensure_ascii=False) + "\n"


def outputs(version: str) -> dict[Path, str]:
    record = record_of(version)
    return {DICTIONARY: data_dictionary(record), CITATION: citation(record),
            croissant_path(version): croissant_text(record)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--check", action="store_true",
                    help="compare the committed files with what the code prints")
    args = ap.parse_args(argv)
    try:
        out = outputs(args.version)
    except (B.ReleaseError, FileNotFoundError) as exc:
        print(f"[documents] refused: {exc}", file=sys.stderr)
        return 1
    if args.check:
        stale = [p for p, text in out.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"[documents] {p.relative_to(ROOT)} differs from what the "
                  "code prints", file=sys.stderr)
        if not stale:
            print(f"[documents] {len(out)} documents of {args.version} equal "
                  "what the code prints")
        return 1 if stale else 0
    for p, text in out.items():
        p.write_text(text, encoding="utf-8")
        print(f"[documents] {p.relative_to(ROOT)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
