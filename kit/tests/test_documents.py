"""The kit's documents and code keep the repository's rules for text: no
figure typed by hand, no candidate described as a word that is valid,
American spelling, relative links that resolve, the canary quoted as the
files carry it, and no printing in the package."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from ceolkit import RULE, figures, strata

KIT = Path(__file__).resolve().parents[1]
DOCUMENTS = ["README.md", "CODEBOOK.md", "PREREGISTRATION_TEMPLATE.md", "CONTAMINATION.md"]
FILES_WITH_TEXT = (sorted(KIT.glob("*.md")) + sorted((KIT / "ceolkit").glob("*.py"))
                   + sorted((KIT / "tests").glob("*.py")) + sorted((KIT / "notebooks").glob("*.ipynb")))
#: this file spells out the patterns it checks for, so it is not checked for them
CHECKED = [p for p in FILES_WITH_TEXT if p.name != Path(__file__).name]


def text_of(path: Path) -> str:
    """A file's text; for a notebook, the text of its cells."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".ipynb":
        return "\n".join("".join(c["source"]) for c in json.loads(raw)["cells"])
    return raw


def test_the_kit_has_its_documents():
    for name in DOCUMENTS:
        assert (KIT / name).is_file(), name


@pytest.mark.parametrize("path", FILES_WITH_TEXT, ids=lambda p: p.name)
def test_no_figure_is_typed_by_hand(path):
    text = text_of(path)
    assert not re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text)
    if path.suffix == ".md":
        assert not re.findall(r"\b\d{5,}\b", text)


@pytest.mark.parametrize("path", FILES_WITH_TEXT, ids=lambda p: p.name)
def test_a_candidate_is_never_called_a_valid_word(path):
    assert not re.search("valid" + r"\s+words?\b", text_of(path), re.I)


@pytest.mark.parametrize("path", CHECKED, ids=lambda p: p.name)
def test_the_text_uses_american_spelling(path):
    british = (r"\b(colour\w*|behaviour\w*|organis\w+|analys(?:e|ed|ing)|labell\w+|licence\w*|"
               r"favour\w*|centre\w*|catalogue\w*|normalis\w+|recognis\w+|summaris\w+|"
               r"judgement\w*|grey|programme\w*)\b")
    assert not re.findall(british, text_of(path), re.I)


@pytest.mark.parametrize("name", DOCUMENTS)
def test_relative_links_resolve(name):
    text = re.sub(r"```.*?```", "", (KIT / name).read_text(encoding="utf-8"), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    for target in re.findall(r"\]\(\s*([^)\s]+)\s*\)", text):
        if re.match(r"[a-z]+:", target) or target.startswith("#"):
            continue
        assert (KIT / target.split("#")[0]).resolve().exists(), f"{name}: {target}"


def test_the_contamination_note_quotes_the_canary_the_files_carry():
    carried = pq.read_schema(KIT / "fixtures" / "universe_sample.parquet").metadata[b"ceol.canary"].decode()
    assert f"CEOL UNIVERSE CANARY {carried}" in (KIT / "CONTAMINATION.md").read_text(encoding="utf-8")
    card = KIT.parent / "pipeline" / "research" / "release" / "CARD_v1.0.md"
    if card.exists():
        assert f"CEOL UNIVERSE CANARY {carried}" in card.read_text(encoding="utf-8")


def test_the_readme_states_the_rule_and_every_ready_stratum():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    for name, stratum in strata.STRATA.items():
        assert f"`{name}`" in readme
        for label in stratum.labels:
            assert f"`{label}`" in readme, (name, label)
    for notebook in sorted((KIT / "notebooks").glob("*.ipynb")):
        assert f"notebooks/{notebook.name}" in readme


def test_the_rule_in_the_readme_is_the_sampler_s_rule():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    quoted = re.search(r"^> (.+)$", readme, re.M).group(1)
    assert quoted == RULE


def test_figure_ids_quoted_in_the_documents_exist():
    found = figures()
    quoted = set()
    for name in DOCUMENTS:
        text = (KIT / name).read_text(encoding="utf-8")
        quoted |= set(re.findall(r"`((?:rows|config|columns|projection|pin|held_back)\.[a-z0-9_.\-]+)`", text))
    assert quoted
    for figure_id in quoted:
        assert figure_id in found, figure_id


def test_the_preregistration_template_registers_nothing():
    text = (KIT / "PREREGISTRATION_TEMPLATE.md").read_text(encoding="utf-8")
    head = text.split("## 1.")[0]
    assert "registers nothing" in head
    assert "| Status | not filed |" in text
    assert "does not file, upload, or register anything" in text


def test_the_package_never_prints():
    for path in sorted((KIT / "ceolkit").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id in {"print", "pprint", "breakpoint"}]
        assert not calls, path.name
