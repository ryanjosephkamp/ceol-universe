"""Every figure of the CEOL Universe's technical report
(research/release/report/REPORT.md) that release_calcs.py does not
already print, as a named row from committed records; the renderer
that writes the report from its template and the bibliography from the
report's citations; and the guards `check_release_report` in
research/verify_doc_numbers.py runs.

The report is the rendering of `REPORT.template.md`: a placeholder
`{{name}}` is a row of `rows()`, a placeholder `{{release.name}}` a row
of `release_calcs.rows()`, and the renderer writes each as a backticked
span, so every row the report quotes is quoted verbatim in backticks.
The template carries no figure outside its placeholders
(`stray_figures`): a figure is any digit that remains once the
identifiers of `_SET_ASIDE` and `_IDENTIFIER` are set aside, and no
number word of `_NUMBER_WORDS` stands alone outside a row
(PACKAGE_UP1.md readings R1, R2). The guard's promise is that declared
syntax (C-081 line 11): a number after an item word is set aside only
when it is unseparated and of at most 3 digits, and what the other
patterns set aside is read by the prose audit of every re-render
(PACKAGE_UP1.md §3). The number words are bounded: the cardinal words for
1 to 12, the teens (13 to 19), the tens (20 to 90), the magnitude words
for 10^2, 10^3, 10^6, and 10^9, and the word for a group of 12; every
hyphenated form is exempt, and the word for 0, the ordinals, and the
quantifiers are outside the list.

The rows read committed records only, so every row re-derives in a fresh
clone, and no row prints a word of any layer. A figure release_calcs.py
prints from a record field is quoted from its row and is not printed
here again (reading R5). The rows that describe the release name its
version from the release record (reading R6).

Run:  python3 -m research.release.report.report_calcs            (print the rows)
      python3 -m research.release.report.report_calcs --render   (write REPORT.md
                                                                  and REFERENCES.md)
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import re
import sys
from pathlib import Path

from ceol import grammar as G
from research.release import build_release as B
from research.archival import HELD, REFERENCE
from research.release import columns as C
from research.release import release_calcs as R

REPO = Path(__file__).resolve().parents[3]
REPORT_DIR = REPO / "research" / "release" / "report"
TEMPLATE = REPORT_DIR / "REPORT.template.md"
REPORT = REPORT_DIR / "REPORT.md"
REFERENCES = REPORT_DIR / "REFERENCES.md"
#: where a later package commits the literature pass's delivered
#: bibliography (PACKAGE_UP1.md reading R7); absent on this branch
LITERATURE_BIBLIOGRAPHY = REPORT_DIR / "BIBLIOGRAPHY_UL1.md"
MANIFEST = REFERENCE / "references" / "MANIFEST.csv"

CENSUS_JSON = REFERENCE / "research" / "census" / "census.json"
MERGE_JSON = REFERENCE / "research" / "merge" / "merge.json"
AUDIT_JSON = REFERENCE / "research" / "audit" / "audit.json"
RECONCILE_JSON = REFERENCE / "research" / "audit" / "reconcile.json"
#: held out of the repository; absent in a clone
AUDIT_MD = HELD / "research" / "audit" / "AUDIT.md"
UNIVERSE_JSON = REFERENCE / "research" / "universe" / "universe.json"
UNIVERSE_V2_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
SPACED_JSON = REPO / "research" / "universe_v2" / "spaced_applicability.json"
SPACE_CENSUS_JSON = (REFERENCE / "research" / "space_census"
                     / "space_census.json")
EVIDENCE_JSON = REPO / "research" / "evidence" / "evidence.json"
FEATURES_JSON = REPO / "research" / "features" / "features.json"
FEATURES_GATE_JSON = REPO / "research" / "features" / "features_gate.json"
PROVENANCE_JSON = REPO / "research" / "provenance" / "provenance.json"

#: every committed file a row, the renderer, or the check reads
#: (`check_release_report` requires each; hiding any fails the check)
RECORDS: tuple[Path, ...] = (
    TEMPLATE, REPORT, REFERENCES, Path(__file__).resolve(),
    REPO / "research" / "release" / "release_calcs.py",
    REPO / "research" / "release" / "build_release.py",
    REPO / "research" / "release" / "columns.py",
    REPO / "ceol" / "grammar.py", MANIFEST,
    CENSUS_JSON, MERGE_JSON, AUDIT_JSON, RECONCILE_JSON, AUDIT_MD,
    UNIVERSE_JSON, UNIVERSE_V2_JSON, SPACED_JSON, SPACE_CENSUS_JSON,
    EVIDENCE_JSON, FEATURES_JSON, FEATURES_GATE_JSON, PROVENANCE_JSON,
    R.RECORD, R.PROFILE, R.POS)

#: the rows of release_calcs.py the report quotes (reading R5); the check
#: holds the template's release placeholders to exactly this set
RELEASE_ROWS: tuple[str, ...] = (
    "version", "dataset", "built_on", "canary_string",
    "rows_universe", "rows_features", "rows_panel_listed", "rows_eol_valid",
    "rows_spaced", "rows_exceptions", "rows_pin", "rows_restricted",
    "pct_panel_listed", "columns_universe", "columns_features",
    "feature_layer_columns", "evidence_columns", "panel_set_count",
    "detector_count", "exception_class_count", "filter_count",
    "block_count", "prov_neither", "prov_neither_pct", "prov_channel_only",
    "prov_residual_without_reading", "prov_pin_residual", "generated_rows",
    "generated_pct", "inherited_rows", "limit_gb_inherited_no_panel",
    "limit_gb_inherited_no_panel_pct", "limit_gb_all", "limit_gb_pin",
    "limit_no_panel_no_corpus", "single_token_no_panel", "wordfreq_scored",
    "wordnet_listed", "census_candidates", "merge_rows",
    "eol_universe_rows", "c4_additions", "audit_remainder", "v1_rows",
    "pin_spaced", "ledger_words_checked", "controls_checked",
    "as_built_files", "as_built_assertions", "as_built_sources",
    "as_built_profile")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


_n = R._n
_pct = R._pct


def _pairs(counts: dict, keys) -> str:
    return "; ".join(f"{k} {_n(counts[k])}" for k in keys)


def _by_int_key(counts: dict) -> list[str]:
    return sorted(counts, key=int)


def _search(pattern: str, text: str, where: str) -> re.Match:
    m = re.search(pattern, text)
    if m is None:
        raise ValueError(f"{where}: the pattern {pattern!r} is absent")
    return m


# ---------------------------------------------------------------------
# The rows
# ---------------------------------------------------------------------

def rows() -> dict[str, str]:
    """The report's rows, by name, in the order the report quotes them."""
    rec, prof, pos = _load(R.RECORD), _load(R.PROFILE), _load(R.POS)
    v = rec["version"]
    out: dict[str, str] = {}
    out["figures_source"] = (
        f"the release record research/release/release_{v}.json, built "
        f"{rec['built_on']} over the pin of {rec['pin_entry']}")
    out.update(_grammar_rows())
    out.update(_construction_rows())
    out.update(_provenance_rows())
    out.update(_profile_rows(v, prof, pos))
    out.update(_release_rows(v, rec, prof))
    return out


def _grammar_rows() -> dict[str, str]:
    accented = sorted(G.ACCENTED)
    ligatures = sorted(G.LIGATURES)
    letters = len(G.BASE) + len(accented) + len(ligatures)
    if letters != len(G.LETTERS) or len(G.CHARSET) != letters + 3:
        raise ValueError("ceol/grammar.py: the inventory's parts do not sum")
    folds = ", ".join(f"U+{ord(k):04X} to U+{ord(w):04X}"
                      for k, w in sorted(G.CANONICALIZE.items()))
    return {"grammar_inventory": (
        f"the character inventory (C-001, C-015; ceol/grammar.py): "
        f"{len(G.BASE)} base letters a–z; {len(accented)} accented letters "
        f"({' '.join(accented)}), {len(G.DIAERESIS)} of them diaeresis "
        f"letters; {len(ligatures)} ligatures ({' '.join(ligatures)}); "
        f"{len(G.LETTERS)} letters; the hyphen U+002D, the apostrophe "
        f"U+0027, and the space U+0020; a {len(G.CHARSET)}-character "
        f"charset; {len(G.CANONICALIZE)} declared canonicalizations "
        f"({folds})")}


def _construction_rows() -> dict[str, str]:
    census, merge = _load(CENSUS_JSON), _load(MERGE_JSON)
    audit, rc = _load(AUDIT_JSON), _load(RECONCILE_JSON)
    uni, v2 = _load(UNIVERSE_JSON), _load(UNIVERSE_V2_JSON)
    space, spaced = _load(SPACE_CENSUS_JSON), _load(SPACED_JSON)
    ev, feat, gate = (_load(EVIDENCE_JSON), _load(FEATURES_JSON),
                      _load(FEATURES_GATE_JSON))
    out: dict[str, str] = {}

    inv, df = census["inventory"], census["doc_figures"]
    c, seeds = inv["by_class"], census["seeds"]
    out["census_crosschecks"] = (
        f"the census's re-ingest (CENSUS.md; census.json): the EOL's "
        f"tripwires, {_n(df['pages_scanned'])} Wiktionary pages scanned, "
        f"{_n(df['wikt_plain_az'])} English entries of plain letters, "
        f"{_n(df['wikt_titles_plain_az'])} lowercase titles of plain letters "
        f"in all languages, and {_n(df['web2_plain_az'])} web2 keys of plain "
        f"letters; under the CEOL grammar {_n(df['wikt_english_all'])} "
        f"English Wiktionary entries")
    out["census_classes"] = (
        f"the C1 census by class (C-005; census.json): hyphenated "
        f"{_n(c['hyphenated'])}, apostrophe-form {_n(c['apostrophe-form'])} "
        f"(of which s-final {_n(c['s-final'])}), accented "
        f"{_n(c['accented'])}, ligature {_n(c['ligature'])}, diaeresis "
        f"{_n(c['diaeresis'])}, contraction {_n(c['contraction'])}; from "
        f"{len([x for x in inv['sources'] if not x.startswith('eol_ledger')])} "
        f"sources and the seeds re-ruled from the EOL's deletion ledger "
        f"({seeds['accepted']} accepted, "
        f"{seeds['rejected_by_grammar']} rejected by the grammar); "
        f"{_n(inv['single_source'])} ({df['single_source_pct']}%) in "
        f"exactly 1 source")

    mc, fe = merge["counts"], merge["filter_equivalence"]
    both = fe["valid_matches_pin"] and fe["invalid_matches_pin"]
    out["merge_detail"] = (
        f"the merge (C-002; merge.json): of the inherited strings "
        f"{_n(mc['eol_valid'])} in the EOL's valid list and "
        f"{_n(mc['eol_invalid'])} in its invalid list at revision "
        f"{merge['eol_revision'][:8]}; {_n(mc['exceptions'])} census "
        f"candidates; {mc['overlap']} strings in both; filtering by the eol "
        f"column regenerates merged_valid_words.txt "
        f"({fe['regenerated_valid_sha256'][:8]}…) and merged_invalid_words.txt "
        f"({fe['regenerated_invalid_sha256'][:8]}…), "
        f"{'each equal to its pin' if both else 'NOT equal to the pins'}")

    cov = audit["coverage"]
    covs = sorted((s["coverage_pct"], k) for k, s in cov["sources"].items())
    exception_misses = sum(s["miss_exception"] for s in cov["sources"].values())
    out["audit_coverage"] = (
        f"the per-source coverage of merged v0 (C3; audit.json, "
        f"reconcile.json): from {covs[0][0]}% ({covs[0][1]}) and "
        f"{covs[1][0]}% ({covs[1][1]}) to {covs[-1][0]}% ({covs[-1][1]}), "
        f"wiktionary_english {cov['sources']['wiktionary_english']['coverage_pct']}% "
        f"over {len(covs)} sources; exception-class misses {exception_misses}; "
        f"the miss union {_n(rc['miss_union'])} ({_n(cov['miss_shippable'])} "
        f"attested by a redistributable source, {_n(cov['miss_restricted'])} "
        f"only by NWL2023 or CSW21): {_n(rc['miss_in_frame_additions'])} of "
        f"the EOL's {_n(rc['eol_frame_additions'])} frame additions, "
        f"{_n(rc['beyond_frame_wordfreq_only'])} wordfreq-only, and "
        f"{rc['beyond_frame_other']} SCOWL-visibility words")
    d = audit["drift"]
    days = (_dt.date.fromisoformat(d["retrieved"][:10])
            - _dt.date.fromisoformat(d["boundary"][:10])).days
    lo, hi = d["residual_ci95"]
    out["audit_drift"] = (
        f"the fresh-Wiktionary residual (C3; audit.json): over the {days} "
        f"days from the dump boundary to the retrieval, {_n(d['new_pages_ns0'])} "
        f"new pages, {_n(d['new_grammar_valid_not_in_universe'])} with "
        f"grammar-valid lowercase titles not in the universe, "
        f"{d['english_confirmed']} English in a sha256-ranked sample of "
        f"{_n(d['checked'])}; a residual estimate of "
        f"{d['residual_estimate']} English words (95% CI {lo} to {hi})")
    fr = audit["frontier"]
    out["audit_frontier"] = (
        f"the structural-plausibility frontier (C3; audit.json): a "
        f"{fr['model']}; of its top {_n(fr['top_k'])} non-empty completions "
        f"{_n(fr['attested_in_universe'])} ({fr['attested_pct']}%) already in "
        f"the universe and {fr['unattested']} unattested")
    audit_md = AUDIT_MD.read_text(encoding="utf-8")
    cover = _search(r"is ≥ (\d+)% covered by the pinned universe", audit_md,
                    "AUDIT.md, the stopping rule")
    resid = _search(r"residual under ~([\d,]+) words", audit_md,
                    "AUDIT.md, the stopping rule")
    out["audit_stopping_rule"] = (
        f"the stopping rule (C3; AUDIT.md): every curated reference at least "
        f"{cover.group(1)}% covered by the pinned universe with every miss "
        f"listed and attributed; the fresh-source residual under about "
        f"{resid.group(1)} English words; a standing channel for words no "
        f"reference holds")

    uc = uni["counts"]
    out["pin_v1_detail"] = (
        f"the C-009 pin's parts (universe.json; reconcile.json): merged v0 "
        f"{_n(uc['merged_rows'])} rows, and the additions: the EOL's "
        f"{_n(rc['eol_frame_additions'])} frame additions and "
        f"{rc['beyond_frame_other']} SCOWL-visibility words; "
        f"{_n(uc['restricted_rows'])} restricted rows, attested only by "
        f"NWL2023 or CSW21; {_n(rc['beyond_frame_wordfreq_only'])} "
        f"wordfreq-only strings held at the corpus boundary")

    sd, ov = space["doc_figures"], space["overlap"]
    lengths = space["char_length_percentiles"]
    wn = spaced["detectors"]["wordnet"]["spaced_count"]
    wk = spaced["detectors"]["wiktionary_english"]["spaced_count"]
    out["spaced_census"] = (
        f"the space census (C-015; space_census.json, "
        f"spaced_applicability.json): WordNet {_n(wn)} spaced entries and "
        f"Wiktionary {_n(wk)}, {_n(ov['both'])} in both, "
        f"{_n(ov['wordnet_only'])} in WordNet only, "
        f"{_n(ov['wiktionary_only'])} in Wiktionary only, {_n(ov['union'])} "
        f"in all; {_n(sd['two_token'])} ({sd['two_token_pct']}%) with 2 "
        f"tokens and at most {sd['max_tokens']} tokens; lengths p50 "
        f"{lengths['p50']}, p90 {lengths['p90']}, p99 {lengths['p99']} "
        f"characters")
    vc, vf = v2["counts"], v2["filter_equivalence"]
    projection = ("equal" if vf["projection_matches_v1_canonical"]
                  else "NOT equal")
    eol_views = ("each equal to its pin" if vf["valid_matches_pin"]
                 and vf["invalid_matches_pin"] else "NOT equal to the pins")
    out["pin_v2_detail"] = (
        f"the C-016 pin (universe_v2.json): {_n(vc['v2_rows'])} rows, the "
        f"v1 universe of {_n(vc['v1_rows'])} and the spaced admission "
        f"(WordNet only {_n(vc['wn_only'])}, Wiktionary only "
        f"{_n(vc['wk_only'])}, both {_n(vc['both_sources'])}); restricted "
        f"rows {_n(vc['restricted_rows'])}, unchanged from v1; the eol and "
        f"eol_universe projections {eol_views}; the single-token projection "
        f"over the v1 columns {projection} to v1's canonical content "
        f"({vf['v1_canonical_content_sha256'][:8]}…)")
    app, na = spaced["applicable"], spaced["not_applicable"]
    out["spaced_applicability"] = (
        f"the spaced class's detectors (C-016; spaced_applicability.json): "
        f"{len(app)} applicable ("
        + ", ".join(f"{k} {_n(spaced['detectors'][k]['spaced_count'])}"
                    for k in app)
        + f") and {len(na)} structurally not applicable, each zero measured "
        f"({', '.join(na)})")

    fires, nas = ev["fires"], ev["na_counts"]
    order = sorted(fires, key=lambda k: -fires[k])
    out["evidence_fires"] = (
        f"the evidence matrix over the v1 universe (C-010; evidence.json): "
        f"{_n(ev['universe_rows'])} rows; listed by "
        + "; ".join(f"{k} {_n(fires[k])}" for k in order)
        + f"; the SCOWL tier on {_n(ev['doc_figures']['scowl_total'])} "
        f"strings; the title screen on {_n(ev['screen_hits'])} rows")
    out["evidence_na"] = (
        f"the structurally blind cells of the evidence matrix (C-010; "
        f"evidence.json): "
        + "; ".join(f"{k} {_n(nas[k])}" for k in order)
        + f"; {ev['binary_pattern_count']} distinct binary patterns; "
        f"{ev['sr2']['reading_a_pct']}% of rows listed by no panel set, the "
        f"SCOWL tier included (SR2, reading A)")
    rep = ev["eol_reproduction"]
    shared = [k for k in rep if k != "scowl_tier_nonzero"]
    equal = [k for k in shared if rep[k]["eol"] == rep[k]["ceol_on_frame"]]
    scowl = rep["scowl_tier_nonzero"]
    out["evidence_reproduction"] = (
        f"the reproduction of the EOL's evidence matrix (C-010; "
        f"evidence.json, reconcile.json): {len(equal)} of {len(shared)} "
        f"shared detectors equal to the EOL's totals digit for digit on its "
        f"frame of {_n(rc['eol_frame_size'])} strings; SCOWL wider by "
        f"{_n(scowl['ceol_surplus_from_wider_inclusion'])} strings under the "
        f"census's inclusion rule ({_n(scowl['ceol_on_frame'])} against "
        f"{_n(scowl['eol'])})")

    fd = feat["doc_figures"]
    ppl, bounds = gate["perplexity"]["by_class"], gate["perplexity"]["bounds"]
    classes = [k for k in ppl if not k.startswith("_")]
    fam = gate["family_admission"]
    admitted = sorted(k for k, x in fam.items() if x["admitted"])
    rejected = sorted(k for k, x in fam.items() if not x["admitted"])
    sr2 = gate["sr2_reading_b"]
    out["features_corpus"] = (
        f"the feature layer's corpora (C-011; features.json): "
        f"{_n(fd['gb_types'])} Google Books types in the CEOL re-stream of "
        f"the 2020 English 1-grams; wordfreq Zipf values for "
        f"{_n(fd['wordfreq_scored'])} strings of wordfreq's own list; the "
        f"Zipf-Mandelbrot fit's alpha {fd['zipf_alpha']}")
    out["features_model"] = (
        f"the character model (C-011; features.json, features_gate.json): "
        f"{_n(fd['pool'])} strong positives by the pool rule "
        f"({_n(fd['pool_strict'])} under the strict variant), train "
        f"{_n(fd['train'])}, dev {_n(fd['dev'])}, test {_n(fd['test'])}; "
        f"held-out perplexity "
        + ", ".join(f"{k} {ppl[k]} (bound {bounds[k]})" for k in classes)
        + f"; {len(gate['perplexity']['class_na_fallback'])} classes on the "
        f"not-applicable fallback")
    out["features_gates"] = (
        f"the feature layer's gates (C-011; features_gate.json): "
        f"{len(admitted)} of {len(fam)} OCR-confusion families admitted "
        f"({', '.join(admitted)}), {len(rejected)} rejected "
        f"({', '.join(rejected)}); SR2 reading B {_n(sr2['rows'])} rows, "
        f"{sr2['pct']}% against a bar of {sr2['bar_pct']}%, "
        f"{'passed' if sr2['pass'] else 'FAILED'}")
    return out


def _provenance_rows() -> dict[str, str]:
    p = _load(PROVENANCE_JSON)
    m, pc, cov = p["measured"], p["percentages"], p["coverage"]
    rc = p["reconciliations"]
    res, nr, gen = m["residual"], m["no_recorded_channel"], m["generated"]
    layers = m["rows_by_layer"]
    cls, kinds = m["rows_by_class"], m["rows_by_kind"]
    out: dict[str, str] = {}
    out["provenance_residual_detail"] = (
        f"the residual over the pin (C-064, C-065; provenance.json): "
        f"{pc['residual_of_the_universe']} of the pin's rows; "
        f"{_n(res['by_layer']['eol_invalid'])} in the EOL's invalid layer "
        f"({pc['residual_of_the_invalid_layer']} of that layer) and "
        f"{res['by_layer']['eol_valid']} in its valid layer; "
        f"{_n(res['by_eol_record']['invalid-dict'])} with an entry in the "
        f"invalid dictionary and {res['by_eol_record']['valid-dict']} in the "
        f"valid dictionary, each recording no channel, and "
        f"{res['by_eol_record']['none']} with no dictionary entry; "
        f"{res['a_wiktionary_title_in_some_language']} of them page titles "
        f"in some language's Wiktionary, a screen and not containment")
    out["provenance_classes_pin"] = (
        f"the provenance classes over the pin (C-064; provenance.json): "
        f"channel_and_containment {_n(cls['channel_and_containment'])} "
        f"({pc['channel_and_containment_of_the_universe']}), channel_only "
        f"{_n(cls['channel_only'])} ({pc['channel_only_of_the_universe']}), "
        f"containment_only {_n(cls['containment_only'])} "
        f"({pc['containment_only_of_the_universe']}); the kinds: obtained "
        f"{_n(kinds['obtained'])}, derived {_n(kinds['derived'])}, generated "
        f"{_n(kinds['generated'])} ({pc['generated_of_the_universe']}); the "
        f"layers: " + _pairs(layers, sorted(layers)))
    out["provenance_unrecorded"] = (
        f"the strings with no recorded channel (C-064; provenance.json): "
        f"{_n(nr['rows'])} inherited strings carry eol:phase1-unrecorded; "
        f"{_n(nr['listed_by_a_panel_set'])} of them listed by a panel set, "
        f"{_n(nr['a_gb_type'])} Google Books 1-gram types "
        f"({_n(nr['not_listed_and_a_gb_type'])} of those listed by no panel "
        f"set), {nr['not_listed_not_gb_and_wordfreq_scored']} more scored by "
        f"wordfreq alone, and {_n(nr['with_no_containment'])} with no "
        f"containment; {pc['inherited_with_a_recorded_channel']} of the "
        f"inherited strings have a recorded channel")
    dl = p["discovery_log_vs_containment"]
    out["provenance_discovery_log"] = (
        f"the discovery log against containment (C-008, C-064; "
        f"provenance.json): the label wordnet on "
        f"{_n(dl['valid_rows_labeled_wordnet'])} rows of the EOL's valid "
        f"list ({_n(dl['valid_rows_labeled_wordnet_at_the_valid_tier'])} at "
        f"the valid tier) where the WordNet panel set lists "
        f"{_n(dl['valid_rows_listed_by_the_wordnet_panel_set'])}; the label "
        f"google_ngrams on {_n(dl['inherited_rows_labeled_google_ngrams'])} "
        f"inherited rows, {dl['of_them_not_a_gb_type']} of them not a Google "
        f"Books type, while {_n(dl['inherited_gb_types_without_the_label'])} "
        f"further inherited Google Books types lack the label")
    eng, xc = gen["by_engine"], p["ledger_cross_check"]
    out["provenance_generated"] = (
        f"the generated strings (C-064 rulings 3 and 11; C-065 ruling 2; "
        f"provenance.json): the record of generation in "
        f"{_n(rc['generated_in_the_valid_dictionary'])} entries of the valid "
        f"dictionary, {_n(rc['generated_in_the_invalid_dictionary'])} of the "
        f"invalid dictionary, and "
        f"{_n(rc['generated_named_by_the_demotion_ledgers_only'])} strings "
        f"that only the EOL's demotion ledgers name; "
        f"{pc['generated_with_no_containment']} with no measured containment; "
        f"{gen['with_a_discovery_log_label_too']} with a discovery-log label; "
        f"the engine inferred from the form: "
        + ", ".join(f"{k} {_n(eng[k])}"
                    for k in sorted(eng, key=lambda k: -eng[k]))
        + f" ({pc['generated_inferred_as_affixation']} affixation); the "
        f"inferred rule agreeing with the form the ledger claims on "
        f"{_n(xc['agreeing_rows'])} of {_n(xc['ledger_rows'])} ledger rows")
    out["provenance_inputs"] = (
        f"the EOL's dictionaries at revision c1139698 (C-064 ruling 2; "
        f"C-065 ruling 3; provenance.json): the valid dictionary "
        f"{_n(cov['valid_dictionary_bytes'])} bytes, "
        f"{_n(cov['valid_dictionary_entries'])} entries "
        f"(sha256 {p['inputs']['merged_valid_dict_sha256'][:8]}…); the "
        f"invalid dictionary {_n(cov['invalid_dictionary_bytes'])} bytes, "
        f"streamed once and never stored, {_n(cov['invalid_dictionary_entries'])} "
        f"entries parsed over {_n(cov['invalid_dictionary_lines'])} lines "
        f"(sha256 {p['inputs']['merged_invalid_dict_sha256'][:8]}…)")
    return out


def _profile_rows(v: str, prof: dict, pos: dict) -> dict[str, str]:
    u = prof["universe"]
    tok = u["eol_by_token_count"]
    out: dict[str, str] = {}
    out["profile_tokens"] = (
        f"the rows of {v} by tokens (profile.json): "
        + "; ".join(f"{k} {'token' if k == '1' else 'tokens'} "
                    f"{_n(tok[k]['rows'])}" for k in _by_int_key(tok))
        + f"; the EOL's valid list {_n(tok['1']['eol'])} rows of 1 token "
        f"and {sum(tok[k]['eol'] for k in tok if k != '1')} of more")
    ch = u["character_use"]
    out["profile_characters"] = (
        f"the characters of {v}'s rows (profile.json): letters a–z only "
        f"{_n(ch['ascii_letters_only'])}; an apostrophe "
        f"{_n(ch['apostrophe'])}; a hyphen {_n(ch['hyphen'])}; a space "
        f"{_n(ch['space'])}; an accented letter {_n(ch['accented_letter'])}; "
        f"a ligature {_n(ch['ligature'])}")
    lab, per = u["classes_per_label"], u["classes_per_row"]
    out["profile_classes"] = (
        f"the class flags of {v}'s rows (profile.json): "
        + _pairs(lab, sorted(lab, key=lambda k: -lab[k]))
        + "; rows by the number of flags: "
        + "; ".join(f"{k} {_n(per[k])}" for k in _by_int_key(per)))
    q = u["length"]["quantiles"]
    out["profile_length"] = (
        f"the lengths of {v}'s rows in characters (profile.json): minimum "
        f"{q['q']['min']:.0f}, p5 {q['q']['p5']:.0f}, p25 {q['q']['p25']:.0f}, "
        f"median {q['q']['p50']:.0f}, p75 {q['q']['p75']:.0f}, p95 "
        f"{q['q']['p95']:.0f}, p99 {q['q']['p99']:.0f}, maximum "
        f"{q['q']['max']:.0f}; mean {q['mean']:.2f}")
    pan = u["eol_by_panel_count"]
    out["profile_panel"] = (
        f"the rows of {v} by the number of panel sets listing them, with the "
        f"EOL's valid list among them (profile.json): "
        + "; ".join(f"{k} {'set' if k == '1' else 'sets'} "
                    f"{_n(pan[k]['rows'])} ({_n(pan[k]['eol'])})"
                    for k in _by_int_key(pan)))
    lst = u["evidence"]["listed"]
    out["profile_listings"] = (
        f"the single-token rows of {v} each panel set lists (profile.json): "
        + _pairs(lst, sorted(lst, key=lambda k: -lst[k])))
    P = u["provenance"]
    out["profile_intake"] = (
        f"the rows of {v} by intake (profile.json): by date "
        + _pairs(u["intake_date"], sorted(u["intake_date"]))
        + "; by layer " + _pairs(P["intake_layer"], sorted(P["intake_layer"]))
        + f"; by kind obtained {_n(P['intake_kind']['obtained'])}, derived "
        f"{_n(P['intake_kind']['derived'])}; by class channel_and_containment "
        f"{_n(P['provenance_class']['channel_and_containment'])}, "
        f"containment_only {_n(P['provenance_class']['containment_only'])}")
    out["profile_properness"] = (
        f"the properness signals and flags of {v} (C-016; profile.json): "
        + "; ".join(f"{k} true {_n(u[k]['true'])}, false {_n(u[k]['false'])}, "
                    f"null {_n(u[k]['null'])}"
                    for k in ("wn_instance", "wn_capitalized", "wk_proper_noun"))
        + "; wk_flags " + _pairs(u["wk_flags_per_label"],
                                 sorted(u["wk_flags_per_label"])))
    out["profile_variety"] = (
        f"the variety proxies of {v} (profile.json): variety_gb_not_us true "
        f"{_n(u['variety_gb_not_us']['true'])}; variety_us_not_gb true "
        f"{_n(u['variety_us_not_gb']['true'])}; null on "
        f"{_n(u['variety_gb_not_us']['null'])} rows each")
    out["profile_corpora"] = (
        f"the corpus and screen columns of {v} (profile.json): gb_type false "
        f"{_n(u['gb_type']['false'])}; wordfreq_scored false "
        f"{_n(u['wordfreq_scored']['false'])}; wikt_title_any true "
        f"{_n(u['wikt_title_any']['true'])}; each null on the "
        f"{_n(u['gb_type']['null'])} spaced rows")
    vals = u["evidence"]["values"]
    det = sorted({int(k) for d in C.DETECTORS for k in vals[d] if k != "null"})
    tiers = sorted(int(k) for k in vals["scowl_tier"] if k != "null")
    screen = sorted(int(k) for k in vals["wikt_title_screen"] if k != "null")
    out["evidence_values"] = (
        f"the evidence columns' values in {v} (C-010; profile.json): each "
        f"detector column {', '.join(map(str, det))} (1 listed, 0 not "
        f"listed, -1 structurally blind to the row's class); scowl_tier "
        f"{', '.join(map(str, [t for t in tiers if t <= 0]))} and the tiers "
        f"{min(t for t in tiers if t > 0)} to {max(tiers)}; "
        f"wikt_title_screen {', '.join(map(str, screen))}; each null on "
        f"{_n(u['nulls']['wordnet'])} spaced rows")
    anyp = pos["pos_any"]
    names = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb"}
    out["profile_pos"] = (
        f"the part-of-speech coverage estimate of {v} (pos_estimate.json): "
        f"WordNet {pos['wordnet_version']} lists {_n(pos['wordnet_listed_single_token'])} "
        f"single-token rows and {_n(pos['wordnet_listed_spaced'])} spaced "
        f"rows; with a "
        + ", ".join(f"{names[k]} sense {_n(anyp[k])}" for k in ("n", "v", "a", "r"))
        + f"; {_n(pos['multi_pos_rows'])} with senses in more than 1 part of "
        f"speech; read under nltk {pos['nltk_version']} (corpus sha256 "
        f"{pos['wordnet_corpus_sha256'][:8]}…)")
    return out


def _release_rows(v: str, rec: dict, prof: dict) -> dict[str, str]:
    u = prof["universe"]
    ev = _load(EVIDENCE_JSON)
    lst, src = u["evidence"]["listed"], u["sources_per_label"]
    chan = u["provenance"]["intake_channels_per_label"]
    fires = ev["fires"]
    lists = ("nwl2023", "csw21", "sowpods_legacy")
    out: dict[str, str] = {}
    out["withheld_columns"] = (
        f"the game lists' columns and labels C-079 line 2 rules on for the "
        f"public flip, "
        f"as {v} carries them "
        f"(profile.json, evidence.json): "
        + "; ".join(f"{k} marks {_n(lst[k])} rows of the release and lists "
                    f"{_n(fires[k])} rows of the pin ({_pct(lst[k], fires[k])})"
                    for k in lists)
        + "; the labels eol:nwl2023 on " + _n(src["eol:nwl2023"])
        + ", eol:csw21 on " + _n(src["eol:csw21"])
        + ", eol:sowpods_legacy on " + _n(src["eol:sowpods_legacy"])
        + " rows in sources, and audit:nwl2023 on " + _n(chan["audit:nwl2023"])
        + ", audit:csw21 on " + _n(chan["audit:csw21"])
        + ", audit:sowpods_legacy on " + _n(chan["audit:sowpods_legacy"])
        + " rows in intake_channels")
    out["identifier"] = (
        f"the identifier (C-078 line 4; build_release.word_id): the first "
        f"{len(B.word_id('0'))} hexadecimal digits of the sha256 of the "
        f"word's UTF-8 bytes, a function of the string alone")
    b, sw = rec["bounds"], rec["software"]
    out["size_policy"] = (
        f"the size policy of {v} (C-079 line 9; release_{v}.json): each "
        f"file's compressed bytes under {_n(b['max_shard_bytes'])}; row "
        f"groups sized toward {_n(b['max_row_group_bytes'])} uncompressed "
        f"bytes in multiples of {_n(b['row_group_quantum'])} rows")
    out["software"] = (
        f"the software of the {v} build (release_{v}.json): Python "
        f"{sw['python']}, pyarrow {sw['pyarrow']}")
    return out


# ---------------------------------------------------------------------
# The renderer
# ---------------------------------------------------------------------

_PLACE = re.compile(r"\{\{(release\.)?([a-z0-9_]+)\}\}")


def placeholders(template: str) -> list[tuple[str, str]]:
    """Each placeholder as (namespace, name), namespace 'release' or
    'report', in order."""
    return [("release" if m.group(1) else "report", m.group(2))
            for m in _PLACE.finditer(template)]


def render(template: str, report_rows: dict[str, str],
           release_rows: dict[str, str]) -> str:
    """The report: every placeholder replaced by its row in backticks; an
    unknown name raises KeyError."""
    def fill(m: re.Match) -> str:
        table = release_rows if m.group(1) else report_rows
        return f"`{table[m.group(2)]}`"
    return _PLACE.sub(fill, template)


# ---------------------------------------------------------------------
# The figure guard (PACKAGE_UP1.md reading R2)
# ---------------------------------------------------------------------

_YEAR = r"(?:19|20)\d\d"
#: a number after an item word: unseparated and of at most 3 digits (a
#: line, an item, or a ruling number), with an optional letter or
#: lettered part, so that a count after an item word is a figure (C-081
#: line 11; PACKAGE_UP1.md §3 and §9, F1)
_ITEM_NUMBER = r"\d{1,3}(?!\d|[,.]\d)[a-z]?(?:\([a-z]\))?"
#: the identifiers set aside before a digit counts as a figure; each is a
#: declared pattern, never a list of the current values. The guard's
#: promise is this syntax (PACKAGE_UP1.md §3, reading R2): what these
#: patterns set aside, a year-like number after a capitalized word, a
#: slash-joined token, or a letter-initial token among them, is read by
#: the prose audit of every re-render and not caught here (reading R15)
_SET_ASIDE = re.compile("|".join((
    r"\[@[^\]\n]*\]",                                   # a citation key
    r"\]\([^)\s]*\)",                                   # a link's target
    r"https?://\S+",                                    # a URL
    r"\S*/\S*",                                         # a path, a DOI
    r"\bU\+[0-9A-F]{4,6}\b",                             # a codepoint
    r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z)?\b",  # a date, a time
    r"§\s?\d+(?:\.\d+)*[a-z]?",                          # a section
    r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,64}\b",             # a hash
    r"^#{1,6}[ \t]+\d+(?:\.\d+)*\.?(?=[ \t])",       # a heading's number
    r"^[ \t]*\d+\.(?=[ \t])",                       # a list's marker
    # a ruling's line, an item, or a part of a record, with its numbers
    r"\b(?:lines?|rulings?|items?|questions?|steps?|chapters?|readings?"
    r"|findings?|rounds?|drafts?|revisions?|phases?|sections?)\s+"
    + _ITEM_NUMBER + r"(?:(?:,\s*|\s+(?:and|to|or)\s+)" + _ITEM_NUMBER
    + r")*",
    r"\(" + _YEAR + r"\)",                               # a year, cited
    r"\b(?:in|since|before|after|until)[ \t]+" + _YEAR + r"\b",
    r"\b" + _YEAR + r"[ \t]+(?:release|dump|edition|archive|snapshot)\b",
    r"\b(?:et al\.|[A-Z][a-z]+)[ \t]+" + _YEAR + r"\b",  # an author and year
    r"\b(?:WordNet|wordfreq|nltk|Python|pyarrow|CC-BY-SA|CC-BY|Apache|LGPL"
    r"|MPL)[ \t-]\d+(?:\.\d+)+(?:-or-later)?\b",         # a name's version
    r"\b1-grams?\b",
)), re.MULTILINE)
#: a token that begins with a letter and carries a digit is a name, not a
#: figure (sha256, C-016, v2.0, U+0020, AT-UP1-1, nwl2023, LGPL-2.1-or-later,
#: PACKAGE_UP1.md); a possessive ending is not part of the name
_IDENTIFIER = re.compile(r"[A-Za-z][\w+\-]*(?:\.[\w+\-]+)*")
_UNITS = ("one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine")
#: the teens and the tens are built by rule, so that no list here spells a
#: term the walled lists hold (the C-013 wall; PACKAGE_UP1.md reading R2)
_NUMBER_WORDS = _UNITS + ("ten", "eleven", "twelve") + tuple(
    f"{stem}teen" for stem in ("thir", "four", "fif", "six", "seven", "eigh",
                               "nine")) + tuple(
    f"{stem}ty" for stem in ("twen", "thir", "for", "fif", "six", "seven",
                             "eigh", "nine")) + (
    "hundred", "thousand", "million", "billion", "dozen")
#: a number word standing alone; "one-directionality" (C-003) is a term
_NUMBER_WORD = re.compile(r"(?<![\w\-])(?:" + "|".join(_NUMBER_WORDS)
                          + r")(?![\w\-])", re.IGNORECASE)
_SPAN = re.compile(r"`([^`\n]*)`")
_OPEN = "([{\"'“‘*_<>`"
_CLOSE = ".,;:)]}\"'”’…*_`!?"


def stray_figures(text: str, row_values=()) -> list[str]:
    """Every figure `text` carries outside its rows: a backticked span equal
    to a row value is set aside whole, as is a template placeholder; then
    the declared identifiers; then any token that still carries a digit
    and is not a name is a figure, and so is every number word."""
    values = set(row_values)
    bare = _SPAN.sub(lambda m: " " if m.group(1) in values else m.group(0),
                     text)
    bare = _PLACE.sub(" ", bare)
    bare = _SET_ASIDE.sub(" ", bare)
    found: list[str] = []
    for token in re.split(r"[\s–—]+", bare):
        token = re.sub(r"['’]s$", "", token.lstrip(_OPEN).rstrip(_CLOSE))
        if not any(ch.isdigit() for ch in token):
            continue
        if _IDENTIFIER.fullmatch(token):
            continue
        found.append(token)
    found += [m.group(0) for m in _NUMBER_WORD.finditer(bare)]
    return found


def template_problems(template: str, report_rows: dict[str, str],
                      release_rows: dict[str, str]) -> list[str]:
    """What stops a template from rendering into a report the check holds:
    a figure outside a placeholder, an unknown placeholder, a report row
    the template does not quote, a release placeholder outside
    RELEASE_ROWS or a declared release row it does not quote, and a
    backtick beside a placeholder (the renderer writes the backticks)."""
    problems: list[str] = []
    literal = stray_figures(template)
    if literal:
        problems.append(f"REPORT.template.md carries {len(literal)} figure(s) "
                        f"outside its placeholders ({', '.join(literal[:4])})")
    used = placeholders(template)
    report_used = {n for ns, n in used if ns == "report"}
    release_used = {n for ns, n in used if ns == "release"}
    unknown = sorted(report_used - set(report_rows)) + sorted(
        f"release.{n}" for n in release_used - set(release_rows))
    if unknown:
        problems.append(f"REPORT.template.md names rows no calculator "
                        f"prints: {', '.join(unknown)}")
    unquoted = sorted(set(report_rows) - report_used)
    if unquoted:
        problems.append(f"report_calcs.rows() prints rows the report does "
                        f"not quote: {', '.join(unquoted)}")
    if release_used != set(RELEASE_ROWS):
        extra = sorted(release_used - set(RELEASE_ROWS))
        missing = sorted(set(RELEASE_ROWS) - release_used)
        problems.append(f"the template's release rows differ from "
                        f"RELEASE_ROWS (outside it: {', '.join(extra) or 'none'}; "
                        f"not quoted: {', '.join(missing) or 'none'})")
    if re.search(r"`\{\{|\}\}`", template):
        problems.append("REPORT.template.md sets a backtick beside a "
                        "placeholder; the renderer writes the backticks")
    return problems


# ---------------------------------------------------------------------
# The version marker (PACKAGE_UP1.md reading R6)
# ---------------------------------------------------------------------

#: the version grammar the marker and the rows share (C-081 line 11;
#: PACKAGE_UP1.md §9, F2 and reading R16): "v", a number, and 1 or more
#: dotted numeric parts (v2.0, v3.0, a version of 3 parts); a token of a
#: single part (v1, v2, v3) names a universe pin, not a release
VERSION = r"v\d+(?:\.\d+)+"
MARKER = re.compile(r"^\*\*The version of the figures:\*\* `(" + VERSION
                    + r")`", re.M)
#: a version a row names: the whole dotted run, never part of a name or of
#: a longer dotted token; a period that closes a sentence is not a part
_VERSION = re.compile(r"(?<![\w.])" + VERSION + r"(?!\w|\.\d)")


def version_markers(text: str) -> list[str]:
    return MARKER.findall(text)


def row_versions(row_values) -> set[str]:
    """Every version token a row names."""
    return {m.group(0) for value in row_values
            for m in _VERSION.finditer(value)}


# ---------------------------------------------------------------------
# The citations (PACKAGE_UP1.md §4, reading R7)
# ---------------------------------------------------------------------

_CITE = re.compile(r"\[@([^\]\n]+)\]")
_KEY = re.compile(r"[A-Za-z0-9_\-]+")


def cited_keys(text: str) -> list[str]:
    """The citation keys of `text` in the order of their first citation;
    a malformed key is returned as written so the check can name it."""
    keys: list[str] = []
    for m in _CITE.finditer(text):
        for part in m.group(1).split(";"):
            key = part.strip().lstrip("@").strip()
            if key not in keys:
                keys.append(key)
    return keys


def manifest_rows(path: Path = MANIFEST) -> dict[str, dict]:
    """The manifest's rows by the stem of their filename."""
    with path.open(encoding="utf-8", newline="") as f:
        return {r["filename"][:-len(".pdf")]: r for r in csv.DictReader(f)
                if r["filename"].endswith(".pdf")}


def delivered_entries(path: Path = LITERATURE_BIBLIOGRAPHY) -> str:
    """The literature pass's bibliography, once a later package commits it
    (reading R7); the empty string while it is absent."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def unresolved_keys(keys, manifest: dict, delivered: str) -> list[str]:
    return [k for k in keys
            if not _KEY.fullmatch(k)
            or (k not in manifest and f"[@{k}]" not in delivered)]


def _locator(doi_or_url: str) -> str:
    return (f"https://doi.org/{doi_or_url}" if doi_or_url.startswith("10.")
            else doi_or_url)


def render_references(keys, manifest: dict, delivered: str = "") -> str:
    """REFERENCES.md: an entry per cited key, from its manifest row (or,
    for a key the delivered bibliography carries, a pointer to it), in the
    order of the keys sorted."""
    lines = [
        "# References",
        "",
        "Rendered by `python3 -m research.release.report.report_calcs "
        "--render` from the citation keys of `REPORT.md` and the rows of "
        "`references/MANIFEST.csv` (`PACKAGE_UP1.md` §4). A key is the stem "
        "of the filename the manifest records; every entry names the "
        "manifest's authors, year, title, and locator, and the sha256 of the "
        "PDF the repository holds under `references/` (gitignored, "
        "acquired lawfully by the owner; `references/README.md`). No PDF is "
        "added by this package.",
        "",
        "## Cited",
        "",
    ]
    for key in sorted(keys):
        if key in manifest:
            r = manifest[key]
            lines.append(
                f"- **[@{key}]** {r['authors']} ({r['year']}). {r['title']}. "
                f"{_locator(r['doi_or_url'])}. Held as "
                f"`references/{r['filename']}`, sha256 `{r['sha256']}`; "
                f"access {r['access']}.")
        else:
            lines.append(f"- **[@{key}]** delivered by the literature pass; "
                         f"the entry is in `BIBLIOGRAPHY_UL1.md`.")
    lines += [
        "",
        "## Awaiting the literature pass (UL-1)",
        "",
        "The literature pass reviews comparable lexical resources, the "
        "documentation standards for datasets, the publication venues and "
        "their data-availability requirements, the canary and answer-key "
        "practice, and the sources' licenses (its prompt, questions 1 to 6). "
        "The report cites none of that work yet: an entry the pass delivers "
        "joins this list when a later package commits its bibliography to "
        "`research/release/report/BIBLIOGRAPHY_UL1.md` (`PACKAGE_UP1.md` "
        "reading R7), and a PDF joins `references/MANIFEST.csv` by a later "
        "package on the manifest's pattern.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args(argv)
    report_rows, release_rows = rows(), R.rows()
    if args.render:
        template = TEMPLATE.read_text(encoding="utf-8")
        problems = template_problems(template, report_rows, release_rows)
        if problems:
            for p in problems:
                print(f"[report] {p}", file=sys.stderr)
            return 1
        text = render(template, report_rows, release_rows)
        manifest, delivered = manifest_rows(), delivered_entries()
        keys = cited_keys(text)
        missing = unresolved_keys(keys, manifest, delivered)
        if missing:
            print(f"[report] citations with no manifest row: "
                  f"{', '.join(missing)}", file=sys.stderr)
            return 1
        REPORT.write_text(text, encoding="utf-8")
        REFERENCES.write_text(render_references(keys, manifest, delivered),
                              encoding="utf-8")
        print(f"[report] {REPORT.relative_to(REPO)} and "
              f"{REFERENCES.relative_to(REPO)} rendered")
        return 0
    for name, value in report_rows.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
