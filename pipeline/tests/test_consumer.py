"""The consumer test of v1.0 (research/release/consumer_test.py): the stranger's script imports nothing from this repository, the
comparison with the record fails on each kind of difference, and the
committed receipt is a pass over the record's files. No word is read or
printed."""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

from research.release import build_release as B
from research.release import consumer_test as T

REPO = Path(__file__).resolve().parents[1]
VERSION = "v1.0"


def _found(expect: dict) -> dict:
    """What a stranger finds when the dataset is the record's."""
    return {
        "config_names": list(expect["configs"]),
        "default_config": "universe",
        "configs": {name: {"rows": c["rows"], "columns": list(c["columns"]),
                           "distinct_ids": c["rows"],
                           "withheld_columns_present": [],
                           **({"panel_count_mismatches": 0,
                               "withheld_labels_present": []}
                              if "panel_sets" in c["columns"] else {})}
                    for name, c in expect["configs"].items()},
        "metadata": {f"data/{name}.parquet": dict(expect["metadata"])
                     for name in expect["configs"]},
        "card": {"canary_present": True, "limitations_first": True},
        "notices": {"present": True, "bytes": 1},
        "croissant": {"record_sets": list(expect["configs"]),
                      "mlcroissant": "validated", "sha256_mismatches": []},
    }


def test_the_stranger_imports_nothing_from_this_repository():
    tree = ast.parse((T.STRANGER).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    allowed = {"datasets", "pyarrow", "huggingface_hub", "mlcroissant"}
    assert names - allowed <= set(sys.stdlib_module_names) | {"__future__"}
    assert not names & {"research", "ceol", "safeguards", "tools"}


def test_the_comparison_passes_when_the_dataset_is_the_record_s():
    expect = T.expectations(VERSION)
    assert not any(T.compare(_found(expect), expect).values())


@pytest.mark.parametrize("check, change", [
    ("configs_declared", lambda f: f["config_names"].pop()),
    ("default_config", lambda f: f.update(default_config="sample")),
    ("rows_by_config",
     lambda f: f["configs"]["universe"].update(rows=1, distinct_ids=1)),
    ("columns_by_config", lambda f: f["configs"]["features"]["columns"].pop()),
    ("ids_distinct", lambda f: f["configs"]["sample"].update(distinct_ids=1)),
    ("panel_count_is_the_names_in_panel_sets",
     lambda f: f["configs"]["universe"].update(panel_count_mismatches=2)),
    ("nothing_withheld",
     lambda f: f["configs"]["universe"]["withheld_columns_present"].append("web2")),
    ("nothing_withheld",
     lambda f: f["configs"]["spaced"]["withheld_labels_present"].append("eol:collins")),
    ("metadata", lambda f: f["metadata"]["data/universe.parquet"].pop("ceol.canary")),
    ("card", lambda f: f["card"].update(canary_present=False)),
    ("card", lambda f: f["card"].update(limitations_first=False)),
    ("notices", lambda f: f["notices"].update(present=False)),
    ("croissant", lambda f: f["croissant"].update(mlcroissant="refused: X")),
    ("croissant", lambda f: f["croissant"].update(sha256_mismatches=["sample.parquet"])),
])
def test_the_comparison_fails_on_each_difference(check, change):
    expect = T.expectations(VERSION)
    found = copy.deepcopy(_found(expect))
    change(found)
    checks = T.compare(found, expect)
    assert checks[check], check
    assert [k for k, v in checks.items() if v] == [check]


def test_the_receipt_is_a_pass_over_the_record_s_files():
    receipt = json.loads(T.receipt_path(VERSION).read_text(encoding="utf-8"))
    record = json.loads(B.resolve(VERSION).record_out.read_text(encoding="utf-8"))
    assert receipt["passed"] is True and not any(receipt["checks"].values())
    assert {k: v["rows"] for k, v in receipt["configs"].items()} == \
        record["rows_by_config"]
    for f in record["files"]:
        assert receipt["files"][f"data/{f['path']}"] == f["sha256"]
    assert receipt["files"]["NOTICES.md"] == record["documents"][0]["sha256"]
    env = receipt["environment"]
    assert env["offline"] == list(T.OFFLINE) and env["isolated"] is True
    assert env["proxies"] == [T.DEAD_PROXY] and env["home_in_scratch"] is True
    assert env["hf_token_passed"] is False
    assert receipt["croissant"]["mlcroissant"] == "validated"
    assert receipt["croissant"]["sha256_mismatches"] == []
    # the receipt is of the committed card and Croissant file (note 11)
    from ceol.ingest.common import sha256_file
    from research.release import documents as D
    from research.release import public_card as P
    assert receipt["files"]["README.md"] == sha256_file(P.CARD)
    assert receipt["files"]["croissant.json"] == sha256_file(D.croissant_path(VERSION))


@pytest.mark.skipif(not (REPO / "data" / "release").exists(),
                    reason="data/ is absent in this environment")
def test_the_hub_files_are_the_record_s_files_the_card_and_the_documents():
    files = T.hub_files(VERSION)
    record = json.loads(B.resolve(VERSION).record_out.read_text(encoding="utf-8"))
    assert sorted(files) == sorted(
        [f"data/{f['path']}" for f in record["files"]]
        + ["NOTICES.md", "README.md", "croissant.json"])



def test_the_stranger_environment_is_offline_isolated_and_proxied_to_a_dead_port(tmp_path):
    """T1: the receipt reads what was passed; a run without the switches, or
    without -I, says so."""
    env = T.stranger_env(tmp_path, tmp_path / "venv", None)
    command = T.stranger_command(tmp_path / "venv/bin/python", tmp_path, None, tmp_path / "hub")
    passed = T.environment_as_passed(env, command, tmp_path)
    assert passed == {"offline": list(T.OFFLINE), "isolated": True,
                      "proxies": [T.DEAD_PROXY], "home_in_scratch": True,
                      "hf_token_passed": False}
    assert env["HF_HOME"].startswith(str(tmp_path)) and "HF_TOKEN" not in env
    assert env["HF_HUB_CACHE"].startswith(str(tmp_path))
    assert command[1] == "-I" and "--path" in command and "--repo" not in command
    stripped = {k: v for k, v in env.items() if k not in T.OFFLINE}
    assert T.environment_as_passed(stripped, command[:1] + command[2:], tmp_path) \
        ["offline"] == []
    assert T.environment_as_passed(stripped, command[:1] + command[2:], tmp_path) \
        ["isolated"] is False
    # on the hub: the user's HOME for the login, the caches still in scratch
    hub = T.stranger_env(tmp_path, tmp_path / "venv", "abc")
    assert hub["HOME"] == str(Path.home()) and hub["HF_HUB_CACHE"].startswith(str(tmp_path))
    assert not set(T.OFFLINE) & set(hub)


def test_the_hub_run_needs_the_owners_word_and_the_upload_s_commit(
        tmp_path, monkeypatch, capsys):
    """T3 and NB-2: --hub refuses without the owner's word, without the
    upload record, at any revision but the record's commit, and with an
    entry or a build other than the ones the upload ran on."""
    from ceol.ingest.common import sha256_file
    from research.release import upload_release as U
    # a plain run refuses for the missing word, before anything else (N-2)
    assert T.main(["--version", VERSION, "--hub", "abc"]) == 1
    assert "--owner-word" in capsys.readouterr().err
    with pytest.raises(U.UploadRefused, match="--owner-word"):
        T.hub_gate(VERSION, "abc", None)
    monkeypatch.setattr(U, "owner_word", lambda entry, *a, **k: entry)
    monkeypatch.setattr(U, "upload_record", lambda spec: tmp_path / "hf_upload_v1.0.json")
    with pytest.raises(B.ReleaseError, match="absent"):
        T.hub_gate(VERSION, "abc", "D-999")
    sha = sha256_file(B.resolve(VERSION).record_out)
    good = {"commit": "abc", "complete": True, "record_sha256": sha,
            "decision": "D-999, the owner's word for this upload"}

    def record(**change):
        (tmp_path / "hf_upload_v1.0.json").write_text(json.dumps({**good, **change}),
                                                      encoding="utf-8")
    record()
    assert T.hub_gate(VERSION, "abc", "D-999")["commit"] == "abc"
    with pytest.raises(B.ReleaseError, match="not the commit"):
        T.hub_gate(VERSION, "def", "D-999")
    record(complete=False)
    with pytest.raises(B.ReleaseError, match="not the commit"):
        T.hub_gate(VERSION, "abc", "D-999")
    record(decision="D-998, the owner's word for this upload")
    with pytest.raises(B.ReleaseError, match="not the entry the upload record names"):
        T.hub_gate(VERSION, "abc", "D-999")
    record(record_sha256="0" * 64)
    with pytest.raises(B.ReleaseError, match="not this build's"):
        T.hub_gate(VERSION, "abc", "D-999")


def test_the_environment_never_downloads_a_python(tmp_path):
    """Note 7 and N-10: uv takes a Python already on this machine."""
    command = T.venv_command("uv", tmp_path / "venv")
    assert "--no-python-downloads" in command and "--no-project" in command
