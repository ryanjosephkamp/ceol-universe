"""
S5b: the universe-v2 filter-equivalence proofs as permanent suite members
(C-015 invariant 2, ruled at the S4 gate; pin decision C-016).

Both proofs re-derive from the SHIPPED artifact, never from the build's
own claims:

  (a) the eol==true and eol_universe subsets hash byte-exact to the EOL
      manifest pins — no spaced candidate can ever leak into the EOL
      view;
  (b) the no-space projection (token_count == 1, the eight v1 columns,
      canonical serialization) reproduces the 10,001,741-row v1 universe
      byte-exact — the structural revert guarantee on top of git.

Skips cleanly when data/universe_v2.parquet has not been built
(fresh clone before `python -m research.universe_v2.build_universe_v2`).
"""

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
V2 = REPO / "data" / "universe_v2.parquet"
V2_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
V1_JSON = (REPO.parent / "reference" / "research" / "universe"
           / "universe.json")
CENSUS_JSON = (REPO.parent / "reference" / "research" / "space_census"
               / "space_census.json")

PIN_VALID = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
PIN_INVALID = "23701bd85e9be2aad94c10628cb257cb08d1db9494b01b8672e46270a6cd5672"

V1_COLUMNS = ("word", "eol", "eol_universe", "classes", "sources",
              "intake_date", "c4_addition", "is_restricted")
V2_COLUMNS = V1_COLUMNS + ("token_count", "c015_addition", "wn_instance",
                           "wn_capitalized", "wk_proper_noun", "wk_flags")

pytestmark = pytest.mark.skipif(
    not (V2.exists() and V2_JSON.exists()),
    reason="universe_v2.parquet not built")


def test_universe_v2_proofs_from_shipped_artifact():
    import pyarrow.parquet as pq

    v1_meta = json.loads(V1_JSON.read_text(encoding="utf-8"))
    v2_meta = json.loads(V2_JSON.read_text(encoding="utf-8"))
    census = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))["doc_figures"]

    f = pq.ParquetFile(V2)
    assert [c.name for c in f.schema_arrow] == list(V2_COLUMNS)

    h_valid, h_invalid = hashlib.sha256(), hashlib.sha256()
    projection = hashlib.sha256()
    counts = {"rows": 0, "valid": 0, "invalid": 0, "spaced": 0,
              "restricted": 0, "wn_only": 0, "wk_only": 0, "both": 0}
    prev = None
    n_v1 = len(V1_COLUMNS)
    for batch in f.iter_batches(batch_size=1 << 16):
        cols = [batch.column(i).to_pylist() for i in range(len(V2_COLUMNS))]
        for row in zip(*cols):
            w, eol, uni, _, sources, intake, _, restr = row[:n_v1]
            tc, c015, wn_i, wn_c, wk_p, wk_f = row[n_v1:]
            # strict order, no duplicates — one pass over the shipped order
            assert prev is None or prev < w
            prev = w
            counts["rows"] += 1
            if tc == 1:
                # spaceless rows are exactly the non-additions, with every
                # C-015 column at its v1-neutral value
                assert " " not in w and not c015
                assert wn_i is None and wn_c is None and wk_p is None \
                    and wk_f is None
                projection.update(
                    ("\t".join(str(x) for x in row[:n_v1]) + "\n")
                    .encode("utf-8"))
            else:
                assert " " in w and c015 and tc == w.count(" ") + 1
                # licence split: no spaced row is EOL-visible or restricted
                assert not eol and not uni and not restr
                assert intake == v2_meta["intake_date_spaced"]
                counts["spaced"] += 1
                srcs = set(sources.split(";"))
                assert srcs <= {"wordnet", "wiktionary_english"} and srcs
                # properness signals: null iff the source did not attest
                assert (wn_i is not None) == (wn_c is not None) \
                    == ("wordnet" in srcs)
                assert (wk_p is not None) == (wk_f is not None) \
                    == ("wiktionary_english" in srcs)
                if srcs == {"wordnet"}:
                    counts["wn_only"] += 1
                elif srcs == {"wiktionary_english"}:
                    counts["wk_only"] += 1
                else:
                    counts["both"] += 1
            if eol:
                counts["valid"] += 1
                h_valid.update(w.encode("utf-8") + b"\n")
            elif uni:
                counts["invalid"] += 1
                h_invalid.update(w.encode("utf-8") + b"\n")
            if restr:
                counts["restricted"] += 1

    # proof (a): the EOL view is byte-exact against the manifest pins
    assert h_valid.hexdigest() == PIN_VALID
    assert h_invalid.hexdigest() == PIN_INVALID

    # proof (b): the no-space projection reproduces universe v1 byte-exact
    assert projection.hexdigest() \
        == v1_meta["artifacts"]["canonical_content_sha256"]

    # counts tie to the census and to both pin records
    assert counts["rows"] == v2_meta["counts"]["v2_rows"] \
        == v1_meta["counts"]["universe_rows"] + census["union_total"]
    assert counts["spaced"] == census["union_total"]
    assert counts["wn_only"] == census["wn_only"]
    assert counts["wk_only"] == census["wk_only"]
    assert counts["both"] == census["overlap_both"]
    assert counts["restricted"] == v1_meta["counts"]["restricted_rows"] \
        == v2_meta["counts"]["restricted_rows"]
    assert counts["valid"] == v1_meta["counts"]["eol_valid"]
    assert counts["invalid"] == v1_meta["counts"]["eol_invalid"]
