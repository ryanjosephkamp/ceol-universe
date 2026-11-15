"""reference/ is read-only and is what reference/IMPORT.csv says it is; no
held file is in the repository; and the link check can fail. Every test runs
in a clone, on the committed files."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
OWN_FILES = {"README.md", "PROVENANCE.csv", "IMPORT.csv", "HELD_OUT.csv"}

sys.path.insert(0, str(ROOT / "tools"))
import check_links  # noqa: E402


def _rows(name: str) -> list[dict]:
    with (REFERENCE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_import_record_accounts_for_every_file_of_the_seed():
    provenance = {r["path"]: r for r in _rows("PROVENANCE.csv")}
    imported = {r["path"]: r for r in _rows("IMPORT.csv")}
    assert set(imported) == set(provenance)
    for path, row in imported.items():
        assert row["class"] == provenance[path]["class"]
        assert row["source_sha256"] == provenance[path]["sha256"]
        assert row["treatment"] in ("copied", "projected", "held out", "not imported")
        assert bool(row["destination"]) == (row["treatment"] in ("copied", "projected"))


def test_every_file_under_reference_is_the_file_the_import_record_names():
    rows = [r for r in _rows("IMPORT.csv") if r["destination"].startswith("reference/")]
    named = {r["destination"] for r in rows}
    present = {p.relative_to(ROOT).as_posix() for p in REFERENCE.rglob("*")
               if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts}
    assert present - {f"reference/{name}" for name in OWN_FILES} == named
    for row in rows:
        assert _sha256(ROOT / row["destination"]) == row["destination_sha256"], row["path"]
        if row["treatment"] == "copied":
            assert row["destination_sha256"] == row["source_sha256"], row["path"]
        else:
            assert row["destination_sha256"] != row["source_sha256"], row["path"]


def test_a_projected_record_holds_no_example_string():
    def strings_under_example_keys(value, under=False) -> int:
        if isinstance(value, dict):
            return sum(strings_under_example_keys(
                v, under or bool(re.search(r"example|longest", k)))
                for k, v in value.items())
        if isinstance(value, list):
            return sum(strings_under_example_keys(v, under) for v in value)
        return int(under and isinstance(value, str))

    # a projected file with no count of withheld strings is a text edit (a local
    # path in a comment), not a record with example lists
    projected = [r for r in _rows("IMPORT.csv")
                 if r["treatment"] == "projected" and r["withheld_strings"]]
    assert projected
    for row in projected:
        body = json.loads((ROOT / row["destination"]).read_text(encoding="utf-8"))
        assert strings_under_example_keys(body) == 0, row["path"]
        assert int(row["withheld_strings"]) > 0, row["path"]
        assert f'"withheld_strings": ' in (ROOT / row["destination"]).read_text(encoding="utf-8")


def test_no_held_file_is_in_the_repository():
    held = {r["path"] for r in _rows("HELD_OUT.csv")}
    assert held == {r["path"] for r in _rows("IMPORT.csv") if r["treatment"] == "held out"}
    tracked = set(filter(None, subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others",
         "--exclude-standard"], capture_output=True, check=True)
        .stdout.decode("utf-8").split("\0")))
    for path in held:
        for home in ("pipeline", "reference"):
            assert f"{home}/{path}" not in tracked, path
    # nothing under the ignored folders is committable
    assert not [t for t in tracked if t.startswith(("data/", "private/"))
                or t in ("data", "private", "pipeline/data", "pipeline/.cache")]


def test_the_link_check_passes_here_and_fails_on_a_dead_link(tmp_path, monkeypatch):
    assert check_links.main([]) == 0
    (tmp_path / "there.md").write_text("# A Heading\n\n## Second `part`\n", encoding="utf-8")
    page = tmp_path / "page.md"
    cases = {
        "[ok](there.md) [ok](there.md#a-heading) [ok](there.md#second-part)": 0,
        "[dead](nowhere.md)": 1,
        "[dead](there.md#no-such-heading)": 1,
        "`[in code](nowhere.md)` and\n```\n[fenced](nowhere.md)\n```\n": 0,
        "[outside](https://example.invalid/x) [mail](mailto:a@example.invalid)": 0,
        '<a href="nowhere.md">dead</a>': 1,
        "[ref]: nowhere.md": 1,
    }
    monkeypatch.setattr(check_links, "REPO", tmp_path)
    for text, expected in cases.items():
        page.write_text(text + "\n", encoding="utf-8")
        problems, _external = check_links.check_file("page.md")
        assert len(problems) == expected, text
