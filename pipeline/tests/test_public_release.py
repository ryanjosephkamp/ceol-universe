"""v2.1's public documents: the card's check, the data
dictionary, CITATION.cff, and the Croissant file.

Each test runs the package's own functions on the committed files, and the
card's check is shown able to fail on each of its inputs, altered 1 at a
time. No word is read or printed.
"""

from __future__ import annotations

import copy
import json

import pytest
import yaml

import research.verify_doc_numbers as verify
from research.release import build_release as B
from research.release import columns as C
from research.release import documents as D
from research.release import public_card as P
from research.release import release_calcs as R
from research.release import withholding as W


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(P.RECORD.read_text(encoding="utf-8"))


def _inputs(record: dict) -> dict:
    """The committed inputs of `_public_release_failures`, as the check
    reads them."""
    from ceol.ingest.common import sha256_file
    return dict(
        card=P.CARD.read_text(encoding="utf-8"),
        template=P.TEMPLATE.read_text(encoding="utf-8"),
        row_values=P.rows(), table_lines=P.tables(), calcs=R,
        record=copy.deepcopy(record),
        documents={p.name: (p.read_text(encoding="utf-8"), text)
                   for p, text in D.outputs(record["version"]).items()},
        notices_sha=sha256_file(P.RDIR / f"NOTICES_{record['version']}.md"),
        commit_known=True, br=B)


def test_the_committed_public_release_passes_its_check(record):
    assert verify._public_release_failures(**_inputs(record)) == []


@pytest.mark.parametrize("case, change, message", [
    ("the card edited by hand",
     lambda i: i.update(card=i["card"].replace("## 1. Limitations", "## 1. Caveats")),
     "not the rendering"),
    ("a literal figure in the template",
     lambda i: i.update(template=i["template"] + "\n12,345 rows\n"),
     "literal figures"),
    ("a placeholder no calculator prints",
     lambda i: i.update(template=i["template"] + "\n{{no_such_row}}\n"),
     "names a row no calculator prints"),
    ("a document edited by hand",
     lambda i: i["documents"].update({"CITATION.cff": ("edited\n", "printed\n")}),
     "is not what documents.py prints"),
    ("an undeclared assertion field",
     lambda i: i["record"]["assertions"]["sample"]["AT-UR1-5"].update(extra=0),
     "not the declared fields"),
    ("another NOTICES file",
     lambda i: i.update(notices_sha="0" * 64),
     "NOTICES"),
    ("held-back rows that do not sum",
     lambda i: i["record"]["projection"]["held_back"].update(rows=1),
     "do not sum by reason"),
    ("a commit outside the history",
     lambda i: i.update(commit_known=False),
     "not in this repository's history"),
])
def test_the_public_release_check_fails_on_each_input(record, case, change, message):
    inputs = _inputs(record)
    change(inputs)
    failures = verify._public_release_failures(**inputs)
    assert any(message in f for f in failures), (case, failures)


def test_the_public_meanings_name_published_columns_only():
    published = set(B.PUBLIC.columns)
    assert set(D.PUBLIC_MEANINGS) <= published
    for _key, (_title, cols) in D.public_tables().items():
        names = {c[0] for c in cols}
        assert not names & set(W.WITHHELD_SETS)
        assert not names & set(W.WITHHELD_FEATURES)
    assert [c[0] for c in D.universe_columns()] == list(B.PUBLIC.columns)
    assert [c[0] for c in D.features_columns()] == \
        ["id", "word", *W.PUBLISHED_FEATURE_COLUMNS]
    # every published set is named in panel_sets' meaning, in order
    meaning = D.PUBLIC_MEANINGS["panel_sets"][0]
    assert ", ".join(W.PUBLISHED_SETS) in meaning
    assert not any(s in meaning for s in W.WITHHELD_SETS)


def test_the_data_dictionary_lists_every_config_and_column(record):
    text = D.DICTIONARY.read_text(encoding="utf-8")
    for f in record["files"]:
        assert f"| `{f['config']}` | `data/{f['path']}` |" in text
    for name in B.PUBLIC.columns + B.PUBLIC.features:
        assert f"| `{name}` |" in text, name


def test_citation_cff_parses_and_names_the_version(record):
    cff = yaml.safe_load(D.CITATION.read_text(encoding="utf-8"))
    assert cff["cff-version"] == "1.2.0" and cff["type"] == "dataset"
    assert cff["version"] == record["version"]
    assert cff["license"] == "CC-BY-SA-4.0"
    assert cff["url"].endswith(record["dataset"])
    assert "doi" not in cff and "date-released" not in cff


def test_the_croissant_file_describes_the_recorded_files(record):
    c = json.loads(D.croissant_path(record["version"]).read_text(encoding="utf-8"))
    assert c["conformsTo"] == "http://mlcommons.org/croissant/1.0"
    assert c["@type"] == "sc:Dataset" and c["version"] == record["version"]
    by_path = {f["path"]: f for f in record["files"]}
    assert [d["@id"] for d in c["distribution"]] == list(by_path)
    for d in c["distribution"]:
        assert d["sha256"] == by_path[d["@id"]]["sha256"]
        assert d["contentUrl"].endswith(f"/resolve/{record['version']}/data/{d['@id']}")
    for rs, f in zip(c["recordSet"], record["files"]):
        assert rs["@id"] == f["config"]
        assert [x["name"] for x in rs["field"]] == f["columns"]
        for x in rs["field"]:
            assert x["dataType"] in D.DATA_TYPES.values()
            assert x["source"]["fileObject"]["@id"] == f["path"]
    # every Arrow type the columns module names has a Croissant type
    kinds = {c[1] for _t, cols in C.TABLES.items() for c in cols[1]}
    assert kinds <= set(D.DATA_TYPES)


def test_the_card_states_its_limitations_first():
    card = P.CARD.read_text(encoding="utf-8")
    headings = [line for line in card.splitlines() if line.startswith("## ")]
    assert headings[0] == "## 1. Limitations"
    # the configs the card's front matter declares are the record's
    front = card.split("---")[1]
    names = [line.split(": ")[1] for line in front.splitlines()
             if line.startswith("- config_name: ")]
    assert names == B.PUBLIC.configs



def test_the_figures_check_fails_on_each_tie(record):
    """N-10: the clone half of check_release_figures fails when the figures
    file or the cube leaves the record."""
    import copy
    from research.release import figures as F
    out = F.out_dir(record["version"])
    figures = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    cube = json.loads((out / "cube.json").read_text(encoding="utf-8"))
    assert verify._release_figures_failures(figures, cube, record) == []
    for change, message in (
            (lambda f, c: f["figures"][0].update(value=f["figures"][0]["value"] + 1),
             "does not state the record's"),
            (lambda f, c: f["source"].update(sha256="0" * 64), "not of the recorded"),
            (lambda f, c: c["cells"][0].__setitem__(-1, c["cells"][0][-1] + 1),
             "do not sum")):
        f2, c2 = copy.deepcopy(figures), copy.deepcopy(cube)
        change(f2, c2)
        assert any(message in x for x in verify._release_figures_failures(f2, c2, record)), message


def test_the_public_documents_cite_no_archive_code():
    """A reader of the public documents cannot open the archive's decision
    record, so none of them cites its codes (D-014; documents.plain)."""
    import re
    code = re.compile(r"\bC-\d{3}\b")
    root = P.REPO.parent
    for path in (P.CARD, D.DICTIONARY, D.croissant_path(P.VERSION),
                 root / "docs" / "licenses" / "FEATURE_COLUMNS.md"):
        found = code.findall(path.read_text(encoding="utf-8"))
        assert not found, (path.name, found[:5])
    with pytest.raises(ValueError):
        D.plain("a meaning that cites C-999")
