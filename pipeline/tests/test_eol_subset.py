"""The English OpenList's public dataset (research/release/eol_subset.py):
its record's counts account for each other,
the public dataset is the figures file's eol-valid config, and the record
re-derives where the release's files are."""

import json

import pytest

from research.release import eol_subset as E
from safeguards import locations

RECORD = json.loads(E.OUT.read_text(encoding="utf-8"))
N = RECORD["counts"]
FIGURES = json.loads((E.B.REPO / "research" / "release" / "figures" / E.VERSION / "figures.json").read_text(encoding="utf-8"))
FIG = {f["id"]: f["value"] for f in FIGURES["figures"]}


def test_the_counts_account_for_each_other():
    assert N["list_at_pin"] - N["removed_after_pin"] + N["added_after_pin"] == N["last_list"]
    assert N["public_dataset"] + N["list_at_pin_not_public"] == N["list_at_pin"]
    assert N["of_which_restricted"] + N["of_which_held_back"] == N["list_at_pin_not_public"]
    assert N["last_list_less_held_back"] == N["public_dataset"] + N["added_after_pin_in_universe"]


def test_the_public_dataset_is_the_eol_valid_config():
    assert N["public_dataset"] == FIG["config.eol-valid.rows"] == FIG["rows.eol"]
    assert N["public_dataset_not_on_last_list"] == 0


@pytest.mark.skipif(not (locations.data_dir() / E.LIST_FILE).exists(),
                    reason="needs the English OpenList's last list and the release's files under data/")
def test_the_record_re_derives():
    assert E.main(["--check"]) == 0
