"""The documents-only path of the release builder (D-018 line 2): it carries
a corrected document into a version already built, rewrites only that
document's bytes and sha256 in the record, and refuses when a data file no
longer matches the record."""

import json
from types import SimpleNamespace

import pytest

from ceol.ingest.common import sha256_file
from research.release import build_release as B


def _built(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "NOTICES_vX.md").write_text("new notice\n", encoding="utf-8")
    out = tmp_path / "release"
    out.mkdir()
    (out / "a.parquet").write_bytes(b"0123")
    (out / "NOTICES.md").write_text("old notice\n", encoding="utf-8")
    record = {"files": [{"path": "a.parquet", "sha256": sha256_file(out / "a.parquet")}],
              "documents": [{"path": "NOTICES.md", "source": "src/NOTICES_vX.md",
                             "bytes": 11, "sha256": sha256_file(out / "NOTICES.md")}],
              "built_on": "2026-01-01"}
    rec = tmp_path / "release_vX.json"
    rec.write_text(json.dumps(record), encoding="utf-8")
    return SimpleNamespace(version="vX", out_dir=out, record_out=rec), root


def test_documents_only_rewrites_the_document_and_nothing_else(tmp_path):
    spec, root = _built(tmp_path)
    before = json.loads(spec.record_out.read_text())
    after = B.documents_only(spec, root=root, today="2026-10-26", log=lambda *a: None)
    assert (spec.out_dir / "NOTICES.md").read_text() == "new notice\n"
    assert after["documents"][0]["sha256"] == sha256_file(spec.out_dir / "NOTICES.md")
    assert after["files"] == before["files"] and after["built_on"] == "2026-01-01"
    assert after["documents_rewritten_on"] == "2026-10-26"


def test_documents_only_refuses_when_a_data_file_changed(tmp_path):
    spec, root = _built(tmp_path)
    (spec.out_dir / "a.parquet").write_bytes(b"changed")
    before = spec.record_out.read_text()
    with pytest.raises(B.ReleaseError, match="changes no data file"):
        B.documents_only(spec, root=root, log=lambda *a: None)
    assert spec.record_out.read_text() == before
    assert (spec.out_dir / "NOTICES.md").read_text() == "old notice\n"
