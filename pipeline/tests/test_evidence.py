"""
C4 step 1: the evidence matrix re-checked from the shipped artifact.

Two layers: full-column recounts against evidence.json, and a
deterministic sha256-ranked sample re-derived cell-by-cell from the
derived sets under the C-010 applicability rules. Skips cleanly when the
matrix has not been built.
"""

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "data" / "evidence.parquet"
EVIDENCE_JSON = REPO / "research" / "evidence" / "evidence.json"

pytestmark = pytest.mark.skipif(
    not (EVIDENCE.exists() and EVIDENCE_JSON.exists()),
    reason="evidence.parquet not built")


def _ev():
    return json.loads(EVIDENCE_JSON.read_text())


def test_column_totals_match_json():
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    ev = _ev()
    t = pq.read_table(EVIDENCE)
    assert t.num_rows == ev["universe_rows"]
    for src in ev["detectors"]:
        col = t.column(src)
        fires = pc.sum(pc.cast(pc.equal(col, 1), "int64")).as_py()
        nas = pc.sum(pc.cast(pc.equal(col, -1), "int64")).as_py()
        assert fires == ev["fires"][src], src
        assert nas == ev["na_counts"][src], src
    restr = pc.sum(pc.cast(t.column("is_restricted"), "int64")).as_py()
    assert restr == 1985
    screen = pc.sum(pc.cast(pc.equal(t.column("wikt_title_screen"), 1),
                            "int64")).as_py()
    assert screen == ev["doc_figures"]["screen_hits"]


def test_sampled_cells_re_derive():
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    from ceol.grammar import classes as class_flags
    from ceol.ingest.common import DERIVED_DIR
    from ceol.ingest.evidence_sources import read_eol_derived

    ev = _ev()
    applicability = {s: set(v) for s, v in ev["applicability"].items()}

    def lines(name):
        with open(DERIVED_DIR / name, encoding="utf-8") as f:
            return {ln.rstrip("\n") for ln in f if ln.strip()}

    sets = {"wiktionary_english": lines("wiktionary_english_all.txt")}
    for s in ("wordnet", "web2", "web2a", "hunspell_en_US",
              "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU"):
        sets[s] = lines(f"{s}.txt") | lines(f"{s}_plain.txt")
    for s in ("enable1", "sowpods_legacy", "nwl2023", "csw21"):
        sets[s] = read_eol_derived(s)

    # deterministic sample: 400 words sha256-ranked from a slice of the
    # matrix itself (every stratum reachable through the rank ordering)
    t = ds.dataset(EVIDENCE).to_table(columns=["word"])
    words = t.column("word").to_pylist()
    ranked = sorted(
        words[::9973],
        key=lambda w: hashlib.sha256(f"evidence-sample:{w}".encode())
        .hexdigest())[:400]
    sample = ds.dataset(EVIDENCE).to_table(
        filter=pc.field("word").isin(ranked))
    got = {sample.column("word")[i].as_py():
           {s: sample.column(s)[i].as_py() for s in ev["detectors"]}
           for i in range(sample.num_rows)}
    assert len(got) == len(ranked)
    for w, cells in got.items():
        flags = frozenset(class_flags(w)) or frozenset(("plain",))
        for s in ev["detectors"]:
            if flags <= applicability[s]:
                assert cells[s] == (1 if w in sets[s] else 0), (w, s)
            else:
                assert cells[s] == -1, (w, s)
