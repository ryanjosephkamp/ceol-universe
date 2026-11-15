"""The notebooks stay runnable: their outputs are cleared, their code cells
run in order in 1 namespace against the fixtures (no Jupyter needed), and
nothing they print or display is a candidate.

The last check runs each notebook on a copy of the fixtures whose words are
replaced by markers. A marker in a printed line, a displayed value, or a
saved file other than the annotation sheet would be a candidate in it."""

from __future__ import annotations

import ast
import contextlib
import io
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

KIT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((KIT / "notebooks").glob("*.ipynb"))
MARK = "qzx"


def code_cells(path: Path) -> list[str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(cell["source"]) for cell in notebook["cells"]
            if cell["cell_type"] == "code"]


def run(path: Path) -> str:
    """Execute a notebook's code cells in order in 1 namespace. Returns what
    the cells print, and the repr (and HTML) of each cell's last expression,
    which a notebook would display."""
    namespace = {"__name__": "__main__"}
    shown = io.StringIO()
    for number, source in enumerate(code_cells(path), start=1):
        tree = ast.parse(source, f"{path.name} code cell {number}")
        last = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last = ast.Expression(tree.body.pop().value)
            ast.fix_missing_locations(last)
        with contextlib.redirect_stdout(shown):
            exec(compile(tree, f"{path.name} code cell {number}", "exec"), namespace)
            if last is not None:
                value = eval(compile(last, f"{path.name} code cell {number}", "eval"), namespace)
                if value is not None:
                    print(repr(value))
                    if hasattr(value, "_repr_html_"):
                        print(value._repr_html_())
    return shown.getvalue()


def marked_fixtures(source: Path, target: Path) -> None:
    """A copy of the fixtures with each word replaced by a marker."""
    target.mkdir()
    universe = pq.read_table(source / "universe_sample.parquet")
    marker_of = {i: f"{MARK}{n}{MARK}" for n, i in enumerate(universe["id"].to_pylist())}
    position = universe.schema.get_field_index("word")
    universe = universe.set_column(position, "word", pa.array(list(marker_of.values())))
    pq.write_table(universe, target / "universe_sample.parquet")
    features = pq.read_table(source / "features_sample.parquet")
    position = features.schema.get_field_index("word")
    features = features.set_column(position, "word", pa.array(
        [marker_of[i] for i in features["id"].to_pylist()]))
    pq.write_table(features, target / "features_sample.parquet")


def test_the_kit_has_the_notebooks_its_readme_names():
    assert [p.name for p in NOTEBOOKS] == ["01_load_and_first_look.ipynb",
                                           "02_draw_a_labeling_sample.ipynb",
                                           "03_frequency_and_coverage.ipynb"]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_a_notebook_is_valid_and_has_its_outputs_cleared(path):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert {"cells", "metadata"} <= set(notebook)
    kinds = {cell["cell_type"] for cell in notebook["cells"]}
    assert kinds == {"markdown", "code"}
    for cell in notebook["cells"]:
        assert isinstance(cell["source"], list)
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None
    assert path.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_a_notebook_runs_on_the_fixtures(path, monkeypatch, tmp_path):
    monkeypatch.chdir(path.parent)
    monkeypatch.delenv("CEOL_FIXTURES", raising=False)
    monkeypatch.setenv("CEOL_OUT_DIR", str(tmp_path / "out"))
    output = run(path)
    assert output.strip()
    assert "Traceback" not in output


def test_the_sampling_notebook_saves_a_manifest_that_matches_its_ids(monkeypatch, tmp_path):
    path = KIT / "notebooks" / "02_draw_a_labeling_sample.ipynb"
    monkeypatch.chdir(path.parent)
    monkeypatch.delenv("CEOL_FIXTURES", raising=False)
    monkeypatch.setenv("CEOL_OUT_DIR", str(tmp_path / "out"))
    run(path)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "annotation_sheet.csv", "manifest.json", "sample_ids.csv"]
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] and manifest["rule"] and manifest["selected_ids_sha256"]
    ids_header = (tmp_path / "out" / "sample_ids.csv").read_text(encoding="utf-8").splitlines()[0]
    assert ids_header == "id,sample_stratum,sample_rank"
    sheet_header = (tmp_path / "out" / "annotation_sheet.csv").read_text(encoding="utf-8").splitlines()[0]
    assert sheet_header == "id,word,label,evidence_type,evidence_ref,note"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_a_notebook_shows_no_candidate(path, monkeypatch, tmp_path):
    marked = tmp_path / "marked"
    marked_fixtures(KIT / "fixtures", marked)
    out = tmp_path / "out"
    monkeypatch.chdir(path.parent)
    monkeypatch.setenv("CEOL_FIXTURES", str(marked))
    monkeypatch.setenv("CEOL_OUT_DIR", str(out))
    output = run(path)
    assert output.strip() and MARK not in output
    if out.exists():
        for saved in out.iterdir():
            if saved.name != "annotation_sheet.csv":
                assert MARK not in saved.read_text(encoding="utf-8"), saved.name
        # the annotation sheet is the one file that holds candidates, by design
        assert MARK in (out / "annotation_sheet.csv").read_text(encoding="utf-8")
