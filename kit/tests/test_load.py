"""The loader: reading the fixtures by `source`, refusing the wrong version,
the hub path and its failures (with a stand-in for the hub's file system, so
that nothing touches the network), and the figures reader."""

from __future__ import annotations

import hashlib
import re
import sys
import types
from pathlib import Path

import pyarrow.parquet as pq
import pytest

import ceolkit
from ceolkit import figure, figures, hub_path, load

FILE = "universe_sample.parquet"


def test_the_fixtures_are_the_files_their_manifest_names(fixtures_dir, fixtures_manifest):
    for name in (FILE, "features_sample.parquet"):
        data = (fixtures_dir / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == fixtures_manifest["files"][name]["sha256"]


def test_load_reads_a_file_by_source(fixtures_dir, fixtures_manifest):
    table = load("universe", "v1.0", source=fixtures_dir / FILE)
    assert table.num_rows == fixtures_manifest["sampling"]["rows"]
    assert table.column_names == fixtures_manifest["columns"]
    assert table.schema.metadata[b"ceol.version"] == b"v1.0"


def test_load_reads_a_folder_by_source(fixtures_dir, fixtures_manifest):
    universe = load(source=fixtures_dir)
    features = load("features", source=fixtures_dir)
    assert universe.num_rows == fixtures_manifest["sampling"]["rows"]
    assert features.num_rows == fixtures_manifest["sampling"]["feature_rows"]
    assert features.column_names == fixtures_manifest["sampling"]["feature_columns"]


def test_load_accepts_a_path_given_as_text(fixtures_dir):
    assert load(source=str(fixtures_dir)).num_rows == load(source=fixtures_dir / FILE).num_rows


def test_load_reads_only_the_columns_asked_for(fixtures_dir):
    table = load(columns=["id", "token_count", "enable1"], source=fixtures_dir)
    assert table.column_names == ["id", "token_count", "enable1"]
    assert table.schema.metadata[b"ceol.version"] == b"v1.0"


def test_load_keeps_the_evidence_types_and_nulls(fixtures_dir):
    table = load(source=fixtures_dir)
    assert str(table.schema.field("wordnet").type) == "int8"
    assert str(table.schema.field("scowl_tier").type) == "int16"
    assert table["wordnet"].null_count > 0
    assert -1 in set(table["wordnet"].drop_null().to_pylist())


def test_a_folder_in_the_hub_layout_is_found(tmp_path, fixtures_dir):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "spaced.parquet").write_bytes((fixtures_dir / FILE).read_bytes())
    assert load("spaced", source=tmp_path).num_rows == load(source=fixtures_dir).num_rows


def test_a_config_the_folder_does_not_hold_is_an_error(fixtures_dir):
    with pytest.raises(FileNotFoundError, match="holds none of"):
        load("sample", source=fixtures_dir)
    with pytest.raises(FileNotFoundError, match="not a file or a folder"):
        load(source=fixtures_dir / "absent")


def test_a_file_of_another_version_is_refused(fixtures_dir):
    with pytest.raises(ValueError, match=r"is version v1\.0, not the version asked for, v2\.0"):
        load(version="v2.0", source=fixtures_dir)


def test_a_file_without_a_version_in_its_metadata_is_read_as_asked(tmp_path, fixtures_dir):
    plain = pq.read_table(fixtures_dir / FILE).replace_schema_metadata(None)
    pq.write_table(plain, tmp_path / "universe.parquet")
    assert load(version="v9.9", source=tmp_path).num_rows == plain.num_rows


@pytest.mark.parametrize("config", ["", "Universe", "universe.parquet", "../universe", "all"])
def test_an_unknown_config_is_refused(config, fixtures_dir):
    with pytest.raises(ValueError, match="unknown config"):
        load(config, source=fixtures_dir)


@pytest.mark.parametrize("version", ["1.0", "v1.", "v", "main", "../v1.0", "v1.0/x", None, 1.0])
def test_a_version_must_look_like_a_version(version, fixtures_dir):
    with pytest.raises(ValueError, match="looks like"):
        load(version=version, source=fixtures_dir)


def test_the_configs_are_the_card_s_seven():
    assert ceolkit.CONFIGS == ("universe", "features", "panel-listed", "eol-valid",
                               "spaced", "exceptions", "sample")


# ---- the hub ---------------------------------------------------------------

def test_the_hub_path_names_the_dataset_the_version_and_the_file():
    assert hub_path("universe", "v1.0") == \
        "hf://datasets/ryanjosephkamp/ceol-universe@v1.0/data/universe.parquet"
    assert hub_path("eol-valid", "v1.0").endswith("@v1.0/data/eol-valid.parquet")
    assert ceolkit.DATASET_VERSION == "v1.0"


def _stand_in_for_the_hub(monkeypatch, local: Path, opened: list):
    class FileSystem:
        def open(self, path, mode="rb"):
            opened.append((path, mode))
            return open(local, "rb")

    module = types.ModuleType("huggingface_hub")
    module.HfFileSystem = FileSystem
    monkeypatch.setitem(sys.modules, "huggingface_hub", module)


def test_without_source_the_file_is_read_from_the_hub_path(monkeypatch, fixtures_dir):
    opened: list = []
    _stand_in_for_the_hub(monkeypatch, fixtures_dir / FILE, opened)
    table = load("universe", "v1.0", columns=["id", "word"])
    assert opened == [("hf://datasets/ryanjosephkamp/ceol-universe@v1.0/data/universe.parquet", "rb")]
    assert table.column_names == ["id", "word"]


def test_a_hub_file_of_another_version_is_refused(monkeypatch, fixtures_dir):
    _stand_in_for_the_hub(monkeypatch, fixtures_dir / FILE, [])
    with pytest.raises(ValueError, match="not the version asked for"):
        load("universe", "v3.0")


def test_without_huggingface_hub_the_message_says_what_to_do(monkeypatch):
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)
    with pytest.raises(ImportError) as caught:
        load("universe", "v1.0")
    message = str(caught.value)
    assert "huggingface_hub" in message and "pip install" in message and "source=" in message


def test_a_hub_failure_says_the_dataset_is_private_until_its_release(monkeypatch):
    class FileSystem:
        def open(self, path, mode="rb"):
            raise FileNotFoundError("not found")

    module = types.ModuleType("huggingface_hub")
    module.HfFileSystem = FileSystem
    monkeypatch.setitem(sys.modules, "huggingface_hub", module)
    with pytest.raises(RuntimeError) as caught:
        load("universe", "v1.0")
    assert "private until its release" in str(caught.value) and "source=" in str(caught.value)
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_the_loader_never_asks_for_a_login(kit_dir):
    text = (kit_dir / "ceolkit" / "load.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"import\s+login|get_token|HF_TOKEN|token\s*=|\.login\(", code)
    assert "private until its release" in text


# ---- the figures -----------------------------------------------------------

def test_figures_are_read_by_id(fixtures_manifest):
    assert figure("config.universe.rows") == fixtures_manifest["source"]["rows"]
    found = figures()
    assert found["config.universe.rows"] == figure("config.universe.rows")
    # the layers partition the rows of the universe config
    layers = sum(v for k, v in found.items() if k.startswith("rows.by_intake_layer."))
    assert layers == found["rows"] == found["config.universe.rows"]


def test_figures_hold_the_ids_the_documents_quote():
    found = figures()
    for figure_id in ("rows.by_model_or_engine.none",
                      "rows.by_model_or_engine.engine_generated", "rows.listed_by.wordnet",
                      "rows.single_token_no_published_set_no_corpus", "columns.universe"):
        assert figure_id in found


def test_an_unknown_figure_or_version_or_path_is_an_error(tmp_path):
    with pytest.raises(KeyError, match="no figure"):
        figure("no.such.figure")
    with pytest.raises(FileNotFoundError, match="figures.json"):
        figures("v9.9")
    with pytest.raises(FileNotFoundError, match="path="):
        figures(path=tmp_path / "absent.json")
    with pytest.raises(ValueError, match="looks like"):
        figures("latest")
