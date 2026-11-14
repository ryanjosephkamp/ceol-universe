"""The descriptive analysis (research/analysis/descriptive.py; the analysis
plan, D-007): the family and tier rules keep -1 apart from 0, the listing
histogram gives the pair, union, and agreement counts a direct count gives,
the interval and quantile helpers are right at their edges, and the
committed file re-derives where the release files are."""

import itertools
import json
import math

import numpy as np
import pytest

from research.analysis import descriptive as D
from research.release import build_release as B

RNG = np.random.default_rng(20261026)


def _lists(n=4000):
    """Random evidence for the 8 lists, with blind cells."""
    return RNG.choice(np.array([1, 0, 0, 0, -1], dtype=np.int8), size=(n, len(D.LISTS)))


def test_a_family_lists_when_any_list_does_and_is_blind_only_when_all_are():
    rows = np.array([
        [1, 0, -1, -1, -1, -1, 0, 0],   # hunspell blind in every dictionary
        [0, 0, -1, 1, -1, -1, 0, 0],    # hunspell listed by 1 dictionary
        [0, 0, -1, 0, -1, -1, 0, 0],    # hunspell holdable, not listed
        [-1, 1, 0, 0, 0, 0, -1, 1],
    ], dtype=np.int8)
    fam = D.family_codes(rows)
    assert fam.tolist() == [[1, 0, -1, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0], [-1, 1, 0, -1, 1]]


def test_the_tiers_count_families_and_never_count_a_blind_cell():
    fam = np.array([[1, 1, 0, 0, 0], [1, -1, -1, -1, -1], [0, -1, 0, 0, 0], [0, 0, 0, 0, 0]], dtype=np.int8)
    corpus = np.array([False, False, True, False])
    assert D.tiers(fam, corpus).tolist() == [0, 1, 2, 3]


def test_a_listing_code_decodes_to_itself():
    codes = _lists(500)
    enc = D.encode(codes)
    assert [D.decode(int(c), codes.shape[1]) for c in enc] == codes.tolist()


def test_the_pair_counts_equal_direct_counts():
    codes = _lists()
    hist = D.combos(codes)
    c = D.containment(hist, codes.shape[1])
    for a, b in itertools.product(range(codes.shape[1]), repeat=2):
        A, Bc = codes[:, a], codes[:, b]
        assert c["eligible"][a][b] == int(((A == 1) & (Bc != -1)).sum())
        assert c["contained"][a][b] == int(((A == 1) & (Bc == 1)).sum())
        assert c["blind"][a][b] == int(((A == 1) & (Bc == -1)).sum())
        hold = (A != -1) & (Bc != -1)
        assert c["both"][a][b] == int((hold & (A == 1) & (Bc == 1)).sum())
        assert c["either"][a][b] == int((hold & ((A == 1) | (Bc == 1))).sum())


def test_the_unions_and_the_accumulation_equal_direct_counts():
    codes = _lists()
    union = D.unions(D.combos(codes), codes.shape[1])
    for s in (0, 1, 0b101, 0b11110000, 0xFF):
        cols = [j for j in range(codes.shape[1]) if s >> j & 1]
        want = int((codes[:, cols] == 1).any(axis=1).sum()) if cols else 0
        assert union[s] == want
    acc = D.accumulation(union, codes.shape[1])
    assert acc[0]["mean"] == 0 and acc[-1]["min"] == acc[-1]["max"] == union[-1]
    assert [a["subsets"] for a in acc] == [math.comb(8, k) for k in range(9)]
    assert all(a["min"] <= a["mean"] <= a["max"] for a in acc)


def test_k_of_m_counts_the_families_that_can_hold_and_that_list():
    fam = D.family_codes(_lists())
    km = D.k_of_m(D.combos(fam), fam.shape[1])
    m = (fam != -1).sum(axis=1)
    k = (fam == 1).sum(axis=1)
    for (mm, kk), n in km.items():
        assert n == int(((m == mm) & (k == kk)).sum())
    assert sum(km.values()) == fam.shape[0]


def test_the_wilson_interval_and_the_quantiles_at_their_edges():
    assert D.wilson(0, 0) is None
    lo, hi = D.wilson(0, 10)
    assert lo == 0.0 and 0 < hi < 0.35
    lo, hi = D.wilson(10, 10)
    assert hi == 1.0 and 0.65 < lo < 1
    q = D.quantiles(np.array([5, 1, 3, 2, 4]))
    assert (q["min"], q["p50"], q["max"], q["n"]) == (1, 3, 5, 5)
    assert D.quantiles(np.array([])) == {"n": 0}
    assert D.share(1, 0) is None and D.share(1, 3) == round(1 / 3, 6)


def test_the_committed_file_describes_the_record():
    path = D.out_path("v1.0")
    doc = json.loads(path.read_text(encoding="utf-8"))
    record = json.loads(B.resolve("v1.0").record_out.read_text(encoding="utf-8"))
    files = {f["config"]: f for f in record["files"]}
    assert doc["version"] == record["version"]
    for c in ("universe", "features"):
        assert doc["sources"][c]["sha256"] == files[c]["sha256"]
    rows = doc["rows"]
    assert rows["all"] == files["universe"]["rows"] and rows["single_token"] == files["features"]["rows"]
    assert sum(rows["by_tier"].values()) == rows["single_token"]
    by_id = {e["id"]: e for e in doc["analyses"]}
    listed = rows["by_tier"]["2+ families"] + rows["by_tier"]["1 family"]
    assert by_id["S13"]["data"]["union_of_all"] == listed
    assert by_id["S10"]["data"]["rows"] == rows["by_tier"]["2+ families"]
    assert all(e["exact"] for e in doc["analyses"])


@pytest.mark.skipif(not B.resolve("v1.0").out_dir.exists(), reason="needs v1.0's release files under data/release/")
def test_the_committed_file_re_derives():
    assert D.main(["--version", "v1.0", "--check"]) == 0


def test_each_tier_histogram_accounts_for_every_measured_value():
    tier = np.array([0, 0, 1, 2, 3, 3])
    values = np.array([10.0, 499.0, 525.0, np.nan, 0.0, 550.0])
    res = D.tier_histograms(values, tier, list(range(0, 575, 25)))
    assert all(sum(v["counts"]) == v["with_value"] for v in res.values())
    assert res["2+ families"]["with_value"] == 2 and res["corpus only"]["with_value"] == 0
    with pytest.raises(ValueError, match="1 measured values fall outside"):
        D.tier_histograms(values, tier, list(range(0, 525, 25)))
