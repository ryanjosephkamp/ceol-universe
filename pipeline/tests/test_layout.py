"""The universe file's layout for the site's list download
(research/release/layout.py): each span is a column chunk's exact bytes, the
record agrees with the release record, and it re-derives where the release
files are."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from research.release import build_release as B
from research.release import layout as L

VERSION = "v1.0"
RECORD = json.loads(L.out_path(VERSION).read_text(encoding="utf-8"))


def test_each_span_is_the_column_chunk(tmp_path):
    path = tmp_path / "t.parquet"
    table = pa.table({
        "id": [f"id{i}" for i in range(30)],
        "word": [f"w{i:03d}" for i in range(30)],
        "panel_count": list(range(30)),
    })
    pq.write_table(table, path, row_group_size=10, compression="zstd")
    found = L.layout_of(path, columns=("word", "panel_count"))
    assert found["rows"] == 30 and [g["rows"] for g in found["row_groups"]] == [10, 10, 10]
    data = path.read_bytes()
    meta = pq.ParquetFile(path).metadata
    for g, group in enumerate(found["row_groups"]):
        for c, name in ((1, "word"), (2, "panel_count")):
            start, size = group["columns"][name]
            col = meta.row_group(g).column(c)
            assert size == col.total_compressed_size and start + size <= len(data)
            assert start == min(x for x in (col.data_page_offset, col.dictionary_page_offset) if x is not None)


def test_a_missing_column_is_refused(tmp_path):
    path = tmp_path / "t.parquet"
    pq.write_table(pa.table({"word": ["a"]}), path)
    with pytest.raises(L.LayoutError, match="no column panel_count"):
        L.layout_of(path, columns=("word", "panel_count"))


def test_the_record_agrees_with_the_release_record():
    release = json.loads(B.resolve(VERSION).record_out.read_text(encoding="utf-8"))
    entry = next(f for f in release["files"] if f["config"] == L.CONFIG)
    assert RECORD["sha256"] == entry["sha256"] and RECORD["bytes"] == entry["bytes"]
    assert RECORD["rows"] == entry["rows"] == sum(g["rows"] for g in RECORD["row_groups"])
    assert RECORD["hub_path"] == "data/universe.parquet"
    for group in RECORD["row_groups"]:
        assert list(group["columns"]) == list(L.READ_COLUMNS)
        for start, size in group["columns"].values():
            assert 0 < start and start + size <= RECORD["bytes"]


@pytest.mark.skipif(not B.resolve(VERSION).out_dir.exists(), reason="needs the release files under data/release/")
def test_the_record_re_derives():
    assert L.main(["--version", VERSION, "--check"]) == 0
