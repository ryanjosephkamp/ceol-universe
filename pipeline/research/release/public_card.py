"""Every figure of the public card of the CEOL Universe
(research/release/CARD_<version>.md, v1.0 on), printed as a named row from
committed records and committed code (rule 3): the
release record `release_<version>.json` (build_release.py), the version's
profile `profile/<version>/profile.json` (universe_profile.py, computed
from the release files), and the pinned records of the layers the release
projects. Nothing here
reads a gitignored file, so every row re-derives in a fresh clone; no row
prints a word.

The card is the rendering of `CARD_<version>.template.md` by the renderer
of v2.0's card (`release_calcs.render`): a `{{name}}` placeholder is a row
of `rows()`, a `{{table:name}}` placeholder a table of `tables()`, and the
template carries no literal figure (`release_calcs.template_literals`).
`check_public_release` in research/verify_doc_numbers.py holds the card to
this rendering.

Run:  python3 -m research.release.public_card            (print the rows)
      python3 -m research.release.public_card --render   (write the card)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research.archival import REFERENCE
from research.release import build_release as B
from research.release import columns as C
from research.release import documents as D
from research.release import release_calcs as R
from research.release import withholding as W

REPO = B.REPO
RDIR = REPO / "research" / "release"
#: the first public release, version 1.0
VERSION = "v1.0"
RECORD = RDIR / f"release_{VERSION}.json"
PROFILE = RDIR / "profile" / VERSION / "profile.json"
PLOTS_DIR = PROFILE.parent / "plots"
CARD = RDIR / f"CARD_{VERSION}.md"
TEMPLATE = RDIR / f"CARD_{VERSION}.template.md"
PIN_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
PROVENANCE_JSON = REPO / "research" / "provenance" / "provenance.json"
MODEL_JSON = REPO / "research" / "provenance" / "model_basis.json"
#: the EOL's last published list against the eol-valid config (eol_subset.py)
EOL_SUBSET_JSON = RDIR / f"eol_subset_{VERSION}.json"
#: universe v1 re-pinned to the EOL's revision (research/universe/repin.py)
REPIN_JSON = REPO / "research" / "universe" / "repin.json"
CENSUS_JSON = REFERENCE / "research" / "census" / "census.json"
AUDIT_RECONCILE_JSON = REFERENCE / "research" / "audit" / "reconcile.json"

_n, _pct, _load = R._n, R._pct, R._load



_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _us_date(day: str) -> str:
    """`2026-10-25` as `October 25, 2026`."""
    year, month, date = (int(part) for part in day.split("-"))
    return f"{_MONTHS[month - 1]} {date}, {year}"


def rows() -> dict[str, str]:
    rec, prof = _load(RECORD), _load(PROFILE)
    pin, prov = _load(PIN_JSON), _load(PROVENANCE_JSON)
    repin, census = _load(REPIN_JSON), _load(CENSUS_JSON)
    v1 = repin["counts"]
    audit, model = _load(AUDIT_RECONCILE_JSON), _load(MODEL_JSON)
    cfg = rec["rows_by_config"]
    U = prof["universe"]
    eol_len = _load(EOL_SUBSET_JSON)["lengths"]
    V, L = U["provenance"], U["limits"]
    total = cfg["universe"]
    if prof["version"] != rec["version"] or prof["configs"] != cfg:
        raise ValueError("the profile does not describe the recorded files")
    files = {f["config"]: f for f in rec["files"]}
    held = rec["projection"]["held_back"]
    a = rec["assertions"]
    by_value = a["universe"]["AT-UR1-13"]["rows_by_value"]
    neither = V["provenance_class"]["neither"]
    generated = V["intake_kind"]["generated"]
    if generated != by_value["engine_generated"]:
        raise ValueError("the generated rows are not the engine_generated rows")
    cw = V["intake_channels_per_label"].get(W.CHANNEL_WITHHELD, 0)
    out = {
        "version": rec["version"],
        # the name a reader sees: "1.0" for v1.0
        "version_name": rec["version"].removeprefix("v"),
        "dataset": rec["dataset"],
        "code_repository": D.CODE,
        "contact_address": D.CONTACT,
        "built_on": _us_date(rec["built_on"]),
        "code_commit": rec["code"]["commit"][:12],
        "canary": rec["canary"],
        "canary_string": f"CEOL UNIVERSE CANARY {rec['canary']}",
        "size_category": R.size_category(total),
        "rows_universe": _n(total),
        "rows_features": _n(cfg["features"]),
        "rows_panel_listed": _n(cfg["panel-listed"]),
        "rows_eol_valid": _n(cfg["eol-valid"]),
        "rows_spaced": _n(cfg["spaced"]),
        "rows_exceptions": _n(cfg["exceptions"]),
        "rows_sample": _n(cfg["sample"]),
        "pct_panel_listed": _pct(cfg["panel-listed"], total),
        "rows_pin": _n(rec["pin_counts"]["rows"]),
        "rows_restricted": _n(rec["pin_counts"]["restricted_rows"]),
        "rows_shippable": _n(rec["pin_counts"]["shippable_rows"]),
        "held_back_rows": _n(held["rows"]),
        "held_tier_2": _n(held["by_reason"]["tier_2"]),
        "held_withheld_channel": _n(held["by_reason"]["withheld_channel"]),
        "held_withheld_sources": _n(held["by_reason"]["withheld_sources"]),
        "columns_universe": str(len(files["universe"]["columns"])),
        "columns_features": str(len(files["features"]["columns"])),
        "feature_columns_published": str(len(W.PUBLISHED_FEATURE_COLUMNS)),
        "evidence_columns": str(sum(1 for c in C.EVIDENCE_LAYER_COLUMNS
                                    if c not in W.WITHHELD_SETS)),
        "published_set_count": str(len(W.PUBLISHED_SETS)),
        "published_sets": ", ".join(f"`{s}`" for s in W.PUBLISHED_SETS),
        "panel_set_count": str(len(C.PANEL_SETS)),
        "withheld_list_count": str(len(W.WITHHELD_SETS)),
        "withheld_columns": ", ".join(f"`{s}`" for s in W.WITHHELD_SETS),
        "withheld_feature_count": str(len(W.WITHHELD_FEATURES)),
        "withheld_features": ", ".join(f"`{c}`" for c in W.WITHHELD_FEATURES),
        "withheld_reference_feature_count":
            str(len(W.WITHHELD_REFERENCE_FEATURES)),
        "withheld_reference_features":
            ", ".join(f"`{c}`" for c in W.WITHHELD_REFERENCE_FEATURES),
        "withheld_model_feature_count": str(len(W.WITHHELD_MODEL_FEATURES)),
        "withheld_model_features":
            ", ".join(f"`{c}`" for c in W.WITHHELD_MODEL_FEATURES),
        "channel_withheld_label": W.CHANNEL_WITHHELD,
        "channel_withheld_rows": _n(cw),
        "exception_class_count": str(len(B.EXCEPTION_CLASSES)),
        "filter_count": str(len(B.PUBLIC.filters)),
        "sample_prefix": B.SAMPLE_PREFIX,
        "prov_neither": _n(neither),
        "prov_neither_pct": _pct(neither, total),
        "prov_channel_only": _n(V["provenance_class"]["channel_only"]),
        "prov_containment_only": _n(V["provenance_class"]["containment_only"]),
        "prov_channel_and_containment": _n(
            V["provenance_class"]["channel_and_containment"]),
        "prov_residual_without_reading": _n(
            prov["reconciliations"]["residual_without_the_ledger_reading"]),
        "generated_rows": _n(generated),
        "generated_pct": _pct(generated, total),
        "model_basis_entries": _n(model["counts"]["entries"]),
        "limit_gb_inherited_no_panel": _n(
            L["gb_type_inherited_no_panel_set"]),
        "limit_gb_inherited_no_panel_pct": _pct(
            L["gb_type_inherited_no_panel_set"], total),
        "limit_gb_only": _n(L["gb_type_inherited_no_panel_set_no_wordfreq"]),
        "limit_gb_all": _n(L["gb_type_rows"]),
        "limit_no_panel_no_corpus": _n(
            L["single_token_no_panel_set_no_corpus"]),
        "single_token_no_panel": _n(L["single_token_no_panel_set"]),
        "wordfreq_scored": _n(U["wordfreq_scored"]["true"]),
        "wordnet_listed": _n(U["panel_sets_per_label"]["wordnet"]),
        "census_candidates": _n(census["inventory"]["total_candidates"]),
        "merge_rows": _n(v1["inherited_rows"] + v1["exceptions"]),
        "eol_universe_rows": _n(v1["inherited_rows"]),
        "eol_revision": repin["eol"]["revision"][:8],
        "c4_additions": _n(v1["c4_additions"]),
        # the audit's unexplained remainder, as v2.0's card states it
        "audit_remainder": _n(audit["miss_union"]
                              - audit["miss_in_frame_additions"]
                              - audit["miss_beyond_frame"]),
        "v1_rows": _n(v1["universe_rows"]),
        "pin_spaced": _n(pin["counts"]["spaced_additions"]),
        "ledger_words_checked": _n(a["universe"]["AT-UR1-6"][
            "ledger_words_outside_the_pin_checked"]),
        "controls_checked": _n(a["universe"]["AT-UR1-6"]["controls_checked"]),
        "restricted_words_checked": _n(a["universe"]["AT-UR1-1"][
            "restricted_words_checked"]),
        "files_asserted": str(len(a)),
        "config_count": str(len(rec["files"])),
        "eol_one_letter": _n(eol_len["one_letter"]),
        "eol_over_45": _n(eol_len["over_45"]),
        "eol_longest": str(eol_len["longest"]),
    }
    return out


def tables() -> dict[str, list[str]]:
    rec = _load(RECORD)
    out: dict[str, list[str]] = {}
    lines = ["| Config | File on the hub | Rows | Predicate |",
             "|---|---|---:|---|"]
    for f in rec["files"]:
        lines.append(f"| `{f['config']}` | `data/{f['path']}` | "
                     f"{_n(f['rows'])} | {D.public_predicate(f['config'], f['predicate'])} |")
    out["configs"] = lines
    lines = ["| File | Bytes | Row-group rows | sha256 |",
             "|---|---:|---:|---|"]
    for f in rec["files"]:
        lines.append(f"| `data/{f['path']}` | {_n(f['bytes'])} | "
                     f"{_n(f['row_group_rows'])} | `{f['sha256']}` |")
    for d in rec["documents"]:
        lines.append(f"| `{d['path']}` | {_n(d['bytes'])} | | "
                     f"`{d['sha256']}` |")
    out["files"] = lines
    lines = ["| Layer | sha256 | Committed record |", "|---|---|---|"]
    for k, v in rec["sources"].items():
        lines.append(f"| {k} (`{v['path']}`) | `{v['sha256']}` | "
                     f"`{v['record']}`, `{v['record_key']}` |")
    out["sources"] = lines
    for key, (_title, cols) in D.public_tables().items():
        out[f"columns_{key}"] = C.markdown_table(cols)
    out["columns_features"] = C.markdown_table(D.features_columns())
    held = rec["projection"]["held_back"]["by_reason"]
    out["held_back"] = [
        "| Why the row is held back | Rows |", "|---|---:|",
        f"| every listing a withheld list, and no public evidence left | "
        f"{_n(held['tier_2'])} |",
        f"| a withheld channel label its only evidence | "
        f"{_n(held['withheld_channel'])} |",
        f"| a census or audit row whose every source is a withheld list | "
        f"{_n(held['withheld_sources'])} |"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args(argv)
    row_values = rows()
    if args.render:
        template = TEMPLATE.read_text(encoding="utf-8")
        literal = R.template_literals(template)
        if literal:
            print(f"[card] the template carries literal figures: {literal}",
                  file=sys.stderr)
            return 1
        CARD.write_text(R.render(template, row_values, tables()),
                        encoding="utf-8")
        print(f"[card] {CARD.relative_to(REPO)} rendered")
        return 0
    for name, value in row_values.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
