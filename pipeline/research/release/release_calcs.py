"""Every figure of the CEOL Universe's dataset card (research/release/CARD.md)
and of PACKAGE_UR1.md §11, printed as a named row from committed records
and committed code: the release record
`release_<version>.json` (build_release.py), the release profile
`profile/profile.json` and `profile/pos_estimate.json` (the profile
scripts, computed from the release files), and the pinned records of the
layers the release projects. Nothing here reads a gitignored file, so
every row re-derives in a fresh clone; no row prints a word.

The card is the rendering of `CARD.template.md`: a `{{name}}` placeholder
is a row of `rows()`, a `{{table:name}}` placeholder a table of
`tables()`, and the template itself carries no literal figure (a
comma-grouped number, a percentage, an integer of 3 or more digits that
is not a year, or a bare decimal that is not a version, license, section,
or identifier number; `template_literals`). `check_release` in
research/verify_doc_numbers.py holds the card to this rendering and
PACKAGE_UR1.md §11 to `PACKAGE_ROWS`.

Run:  python3 -m research.release.release_calcs            (print the rows)
      python3 -m research.release.release_calcs --render   (write CARD.md)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from research.release import build_release as B
from research.archival import REFERENCE
from research.release import columns as C

REPO = Path(__file__).resolve().parents[2]
RDIR = REPO / "research" / "release"
VERSION = "v2.0"
RECORD = RDIR / f"release_{VERSION}.json"
PROFILE = RDIR / "profile" / "profile.json"
POS = RDIR / "profile" / "pos_estimate.json"
CARD = RDIR / "CARD.md"
TEMPLATE = RDIR / "CARD.template.md"
PIN_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
PROVENANCE_JSON = REPO / "research" / "provenance" / "provenance.json"
#: universe v1 re-pinned to the EOL's revision (research/universe/repin.py)
REPIN_JSON = REPO / "research" / "universe" / "repin.json"
CENSUS_JSON = REFERENCE / "research" / "census" / "census.json"
AUDIT_RECONCILE_JSON = REFERENCE / "research" / "audit" / "reconcile.json"
EVIDENCE_JSON = REPO / "research" / "evidence" / "evidence.json"
UPLOAD = RDIR / "hf_upload.json"

#: The rows PACKAGE_UR1.md §11 quotes verbatim, each in backticks.
PACKAGE_ROWS = ("as_built_files", "as_built_assertions", "as_built_sources",
                "as_built_profile", "as_built_limit", "as_built_upload")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _n(x: int) -> str:
    return f"{x:,}"


def _pct(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.2f}%"


def size_category(rows: int) -> str:
    """The hub's size tag for a row count."""
    for lo, hi, tag in ((10**6, 10**7, "1M<n<10M"),
                        (10**7, 10**8, "10M<n<100M"),
                        (10**8, 10**9, "100M<n<1B")):
        if lo <= rows < hi:
            return tag
    raise ValueError(f"no size category for {rows}")


def rows() -> dict[str, str]:
    rec, prof, pos = _load(RECORD), _load(PROFILE), _load(POS)
    pin, prov = _load(PIN_JSON), _load(PROVENANCE_JSON)
    v1, census = _load(REPIN_JSON)["counts"], _load(CENSUS_JSON)
    audit = _load(AUDIT_RECONCILE_JSON)
    cfg = rec["rows_by_config"]
    U = prof["universe"]
    V, L = U["provenance"], U["limits"]
    total = cfg["universe"]
    files = {f["config"]: f for f in rec["files"]}
    containment = prov["measured"]["containment_by_layer"]
    pin_gb = sum(layer["gb_type"] for layer in containment.values())
    neither = V["provenance_class"]["neither"]
    generated = V["intake_kind"]["generated"]
    out = {
        "version": rec["version"],
        "dataset": rec["dataset"],
        "built_on": rec["built_on"],
        "canary": rec["canary"],
        "canary_string": f"CEOL UNIVERSE CANARY {rec['canary']}",
        "size_category": size_category(total),
        "rows_universe": _n(total),
        "rows_features": _n(cfg["features"]),
        "rows_panel_listed": _n(cfg["panel-listed"]),
        "rows_eol_valid": _n(cfg["eol-valid"]),
        "rows_spaced": _n(cfg["spaced"]),
        "rows_exceptions": _n(cfg["exceptions"]),
        "rows_pin": _n(rec["pin_counts"]["rows"]),
        "rows_restricted": _n(rec["pin_counts"]["restricted_rows"]),
        "pct_panel_listed": _pct(cfg["panel-listed"], total),
        "pct_eol_valid": _pct(cfg["eol-valid"], total),
        "columns_universe": str(len(files["universe"]["columns"])),
        "columns_features": str(len(files["features"]["columns"])),
        "feature_layer_columns": str(len(C.FEATURE_LAYER_COLUMNS)),
        "evidence_columns": str(len(C.EVIDENCE_LAYER_COLUMNS)),
        "panel_set_count": str(len(C.PANEL_SETS)),
        "detector_count": str(len(C.DETECTORS)),
        "exception_class_count": str(len(B.EXCEPTION_CLASSES)),
        "filter_count": str(len(B.FILTER_CONFIGS)),
        "block_count": str(len(C.UNIVERSE_BLOCKS)),
        "prov_neither": _n(neither),
        "prov_neither_pct": _pct(neither, total),
        "prov_channel_only": _n(V["provenance_class"]["channel_only"]),
        "prov_residual_without_reading": _n(
            prov["reconciliations"]["residual_without_the_ledger_reading"]),
        "prov_pin_residual": _n(prov["measured"]["rows_by_class"]["neither"]),
        "generated_rows": _n(generated),
        "generated_pct": _pct(generated, total),
        "inherited_rows": _n(L["inherited_rows"]),
        "limit_gb_inherited_no_panel": _n(
            L["gb_type_inherited_no_panel_set"]),
        "limit_gb_inherited_no_panel_pct": _pct(
            L["gb_type_inherited_no_panel_set"], total),
        "limit_gb_all": _n(L["gb_type_rows"]),
        "limit_gb_pin": _n(pin_gb),
        "limit_no_panel_no_corpus": _n(
            L["single_token_no_panel_set_no_corpus"]),
        "single_token_no_panel": _n(L["single_token_no_panel_set"]),
        "wordfreq_scored": _n(U["wordfreq_scored"]["true"]),
        "wordnet_listed": _n(pos["wordnet_listed_rows"]),
        "census_candidates": _n(census["inventory"]["total_candidates"]),
        "merge_rows": _n(v1["inherited_rows"] + v1["exceptions"]),
        "eol_universe_rows": _n(v1["inherited_rows"]),
        "c4_additions": _n(v1["c4_additions"]),
        # the audit's unexplained remainder (C-079 line 1, F3 and F12):
        # the sources' misses less the 2 parts research/audit/AUDIT.md
        # explains, rendered as a numeral
        "audit_remainder": _n(audit["miss_union"]
                              - audit["miss_in_frame_additions"]
                              - audit["miss_beyond_frame"]),
        "v1_rows": _n(v1["universe_rows"]),
        "pin_spaced": _n(pin["counts"]["spaced_additions"]),
        "ledger_words_checked": _n(rec["assertions"]["universe"]["AT-UR1-6"][
            "ledger_words_outside_the_pin_checked"]),
        "controls_checked": _n(rec["assertions"]["universe"]["AT-UR1-6"][
            "controls_checked"]),
    }
    out.update(_package_rows(rec, prof, pos, L))
    return out


def _package_rows(rec: dict, prof: dict, pos: dict, L: dict
                  ) -> dict[str, str]:
    files = "; ".join(
        f"{f['config']} {_n(f['rows'])} rows, {len(f['columns'])} columns, "
        f"{_n(f['bytes'])} bytes, sha256 {f['sha256'][:12]}…"
        for f in rec["files"])
    a = rec["assertions"]
    u = a["universe"]
    assertions = (
        f"the assertions on the written files ({rec['built_on']}): "
        f"restricted words checked {_n(u['AT-UR1-1']['restricted_words_checked'])}"
        f", hits 0 in each of {len(a)} files; distinct ids "
        f"{_n(u['AT-UR1-3']['distinct_ids'])} of {_n(u['AT-UR1-3']['rows'])}; "
        f"spaced rows null in {u['AT-UR1-4']['columns']} columns: "
        f"{_n(u['AT-UR1-4']['spaced_rows'])}; columns {u['AT-UR1-6']['columns']}"
        f"; controls checked {u['AT-UR1-6']['controls_checked']}, "
        f"ledger words outside the pin checked "
        f"{_n(u['AT-UR1-6']['ledger_words_outside_the_pin_checked'])}, hits 0; "
        f"the release layer re-derived on {_n(u['AT-UR1-10']['rows'])} rows; "
        f"each filter config equal to its predicate's filter")
    sources = "; ".join(f"{k} {v['sha256'][:12]}… ({v['record']}, "
                        f"{v['record_key']})"
                        for k, v in rec["sources"].items())
    profile = (f"the profile of {prof['version']}: {len(prof['plots'])} plots,"
               f" {_n(prof['universe']['rows'])} rows profiled, "
               f"{_n(pos['wordnet_listed_rows'])} WordNet-listed rows in the "
               f"part-of-speech estimate, WordNet {pos['wordnet_version']}")
    limit = (f"the limitation (reading R13): Google Books 1-gram types among "
             f"the release's rows {_n(L['gb_type_rows'])}; inherited from the "
             f"EOL {_n(L['gb_type_inherited_rows'])}; of those listed by no "
             f"panel set {_n(L['gb_type_inherited_no_panel_set'])}")
    hub = _load(UPLOAD)
    upload = (f"the upload ({hub['decision']}; {hub['uploaded']}): "
              f"{hub['repo_id']}, private {str(hub['private']).lower()}, "
              f"account {hub['account']}, revision before "
              f"{hub['revision_before'][:12]}…, commit {hub['commit'][:12]}…,"
              f" {len(hub['files'])} files; the hub's LFS sha256 equal to the "
              f"record's for {len(hub['hub_lfs_sha256'])} Parquet files")
    return {"as_built_files": f"the release files: {files}",
            "as_built_upload": upload,
            "as_built_assertions": assertions,
            "as_built_sources": f"the source layers: {sources}",
            "as_built_profile": profile, "as_built_limit": limit}


def tables() -> dict[str, list[str]]:
    rec = _load(RECORD)
    out: dict[str, list[str]] = {}
    lines = ["| Config | File on the hub | Rows | Predicate |",
             "|---|---|---:|---|"]
    for f in rec["files"]:
        lines.append(f"| `{f['config']}` | `data/{f['path']}` | "
                     f"{_n(f['rows'])} | {f['predicate']} |")
    out["configs"] = lines
    lines = ["| File | Bytes | Row-group rows | sha256 |",
             "|---|---:|---:|---|"]
    for f in rec["files"]:
        lines.append(f"| `data/{f['path']}` | {_n(f['bytes'])} | "
                     f"{_n(f['row_group_rows'])} | `{f['sha256']}` |")
    out["files"] = lines
    lines = ["| Layer | sha256 | Committed record |", "|---|---|---|"]
    for k, v in rec["sources"].items():
        lines.append(f"| {k} (`{v['path']}`) | `{v['sha256']}` | "
                     f"`{v['record']}`, `{v['record_key']}` |")
    out["sources"] = lines
    for key, (_title, cols) in C.TABLES.items():
        out[f"columns_{key}"] = C.markdown_table(cols)
    return out


_PLACE = re.compile(r"\{\{([a-z0-9_:]+)\}\}")


def render(template: str, row_values: dict[str, str],
           table_lines: dict[str, list[str]]) -> str:
    """The card: every placeholder replaced; an unknown name raises
    KeyError."""
    def fill(m: re.Match) -> str:
        name = m.group(1)
        if name.startswith("table:"):
            return "\n".join(table_lines[name[len("table:"):]])
        return row_values[name]
    return _PLACE.sub(fill, template)


_YEAR = r"(?:19|20)\d\d"
#: A comma-grouped number, or a percentage.
_GROUPED = re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?%")
#: An integer of 3 or more digits standing as a number: not inside a word,
#: an identifier, a path, or a decimal; a sentence's final period and a
#: preceding colon do not shelter it (C-079 line 1, F3).
_INTEGER = re.compile(r"(?<![\w.,\-/@])(\d{3,})(?![\w\-/%]|\.\d)")
#: A decimal: 2 or more dot-separated runs of digits, not a percentage.
_DECIMAL = re.compile(r"(?<![\d.])(\d+(?:\.\d+)+)(?![\d%])")
#: The token before a single space, the name a version number follows.
_NAME_BEFORE = re.compile(r"(?:^|(?<=\s))([A-Za-z][\w\-]*) $")


def _version_or_reference(text: str, start: int, end: int) -> bool:
    """Whether the decimal text[start:end] is a version, license, section,
    or identifier number rather than a figure, by this rule (C-079 line 1,
    F3; the rule, never a list of the current values):

    - immediately preceded by a letter or a hyphen (v3.0.2, LGPL-2.1,
      MPL-1.1, Apache-2.0, CC-BY-3.0, cc-by-sa-4.0);
    - immediately preceded by a section sign (a section number, §4.5);
    - beside a '/', a component of a path or an identifier (a DOI's
      prefix, a URL);
    - preceded by a single space after a name, a token that begins with a
      letter, where the decimal has a version's form (every component
      after the first a single digit) and either the name carries an
      uppercase letter or a hyphen (WordNet 3.0, CC-BY-SA 4.0) or the
      decimal has 3 or more components (wordfreq 3.1.1).

    Anything else is a figure: 0.16 of, a ratio of 1.5, 3.14."""
    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    if before.isalpha() or before in ("-", "§") or "/" in (before, after):
        return True
    parts = text[start:end].split(".")
    if before != " " or any(len(p) != 1 for p in parts[1:]):
        return False
    name = _NAME_BEFORE.search(text[:start])
    return bool(name) and (any(c.isupper() for c in name.group(1))
                           or "-" in name.group(1) or len(parts) >= 3)


def template_literals(template: str) -> list[str]:
    """The literal figures a template carries outside its placeholders: a
    comma-grouped number; a percentage; an integer of 3 or more digits that
    is not a year, including an integer at a sentence's end or after a
    colon; and a bare decimal that `_version_or_reference` does not except.

    The guard enforces this declared syntax and nothing more: a figure in a
    form it does not list (a number word, an integer under 100) passes it,
    and the prose audit of each rendering reads for those."""
    bare = _PLACE.sub("", template)
    found = _GROUPED.findall(bare)
    for m in _INTEGER.finditer(bare):
        if not re.fullmatch(_YEAR, m.group(1)):
            found.append(m.group(1))
    for m in _DECIMAL.finditer(bare):
        if not _version_or_reference(bare, m.start(1), m.end(1)):
            found.append(m.group(1))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args(argv)
    row_values = rows()
    if args.render:
        template = TEMPLATE.read_text(encoding="utf-8")
        literal = template_literals(template)
        if literal:
            print(f"[card] the template carries literal figures: {literal}",
                  file=sys.stderr)
            return 1
        CARD.write_text(render(template, row_values, tables()),
                        encoding="utf-8")
        print(f"[card] {CARD.relative_to(REPO)} rendered")
        return 0
    for name, value in row_values.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
