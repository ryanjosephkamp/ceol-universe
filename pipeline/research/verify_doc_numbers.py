"""
The figure check: every figure quoted in a document of `pipeline/` is
re-derived from committed code and pinned data, and a mismatch fails.

Run standalone, from `pipeline/`:  python3 -m research.verify_doc_numbers
It also runs in the test suite (tests/test_doc_numbers.py).

This module is the doc-numbers enforcer of the archive this repository grew
from, reduced to the checks of the documents this repository holds.

Two environments, as in the archive. Where `data/` holds the layers and
`private/` holds the lists, every check runs whole. In a clone that holds
neither, a check runs every part the committed files allow and declares
the rest as a deferral; a deferral this module does not declare for that
environment is a failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ceol import grammar
from safeguards import locations, wall

#: `pipeline/`: the root the imported code's paths are written against
REPO = Path(__file__).resolve().parents[1]

#: the archival records the live code reads (read-only; `reference/README.md`)
REFERENCE = locations.REPO / "reference"

EVIDENCE_JSON = REPO / "research" / "evidence" / "evidence.json"
EVIDENCE_DOC = REPO / "research" / "evidence" / "EVIDENCE.md"
FEATURES_JSON = REPO / "research" / "features" / "features.json"
FEATURES_DOC = REPO / "research" / "features" / "FEATURES.md"
FEATURES_GATE = REPO / "research" / "features" / "features_gate.json"
FEATURES_MANIFEST = REPO / "research" / "features" / "features_manifest.json"
GB_META = REPO / ".cache" / "derived" / "google_books_ceol.meta.json"
UNIVERSE_JSON = REFERENCE / "research" / "universe" / "universe.json"
SPACE_CENSUS_JSON = REFERENCE / "research" / "space_census" / "space_census.json"
UNIVERSE_V2_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
UNIVERSE_V2_DOC = REPO / "research" / "universe_v2" / "UNIVERSE_V2.md"
SPACED_APPLIC = REPO / "research" / "universe_v2" / "spaced_applicability.json"

#: The committed files each check requires. A path is relative to
#: `pipeline/`; an archival record is under `../reference/`.
REQUIRED_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "check_release_figures": (
        "research/release/figures.py",
        "research/release/figures/v1.0/figures.json",
        "research/release/figures/v1.0/cube.json",
        "research/release/release_v1.0.json",
    ),
    "check_public_release": (
        "research/release/CARD_v1.0.md",
        "research/release/CARD_v1.0.template.md",
        "research/release/public_card.py",
        "research/release/documents.py",
        "research/release/release_v1.0.json",
        "research/release/NOTICES_v1.0.md",
        "research/release/croissant_v1.0.json",
        "research/release/profile/v1.0/profile.json",
    ),
    "check_release_report": (
        "research/release/report/REPORT.template.md",
        "research/release/report/REPORT.md",
        "research/release/report/REFERENCES.md",
        "research/release/report/report_calcs.py",
        "research/release/release_calcs.py",
        "research/release/build_release.py",
        "research/release/columns.py",
        "ceol/grammar.py",
        "../reference/references/MANIFEST.csv",
        "../reference/research/census/census.json",
        "../reference/research/merge/merge.json",
        "../reference/research/audit/audit.json",
        "../reference/research/audit/reconcile.json",
        "../reference/research/universe/universe.json",
        "research/universe_v2/universe_v2.json",
        "research/universe_v2/spaced_applicability.json",
        "../reference/research/space_census/space_census.json",
        "research/evidence/evidence.json",
        "research/features/features.json",
        "research/features/features_gate.json",
        "research/provenance/provenance.json",
        "research/release/release_v2.0.json",
        "research/release/profile/profile.json",
        "research/release/profile/pos_estimate.json"),
    "check_release": (
        "research/release/CARD.md",
        "research/release/CARD.template.md",
        "research/release/release_calcs.py",
        "research/release/build_release.py",
        "research/release/columns.py",
        "research/release/release_v2.0.json",
        "research/release/hf_upload.json",
        "research/release/profile/profile.json",
        "research/release/profile/pos_estimate.json",
        "research/release/profile/universe_profile.py",
        "research/release/profile/pos_estimate.py",
        "research/release/profile/png_plot.py",
        "research/universe_v2/universe_v2.json",
        "research/evidence/evidence.json",
        "research/provenance/provenance.json",
        "../reference/research/census/census.json",
        "../reference/research/merge/merge.json",
        "../reference/research/universe/universe.json",
        "../reference/research/audit/reconcile.json"),
    "check_provenance": (
        "research/provenance/PROVENANCE.md",
        "research/provenance/PROVENANCE.template.md",
        "research/provenance/provenance.json",
        "research/provenance/eol_dictionaries_manifest.json",
        "research/provenance/build_provenance.py",
        "research/provenance/build_eol_dictionaries_manifest.py",
        "research/provenance/extract_eol_intake.py",
        "research/provenance/synthetic_engine.py",
        "research/universe_v2/universe_v2.json",
        "research/evidence/evidence.json",
        "research/features/features.json"),
}


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def check_inventory_lines() -> list[str]:
    failures: list[str] = []
    for doc in ("GRAMMAR.md",):
        text = _read(doc)
        m = re.search(r"Accent inventory \((\d+)\): (.+?)\s*$", text, re.M)
        if not m:
            failures.append(f"{doc}: no 'Accent inventory (N): …' line")
        else:
            n, listed = int(m.group(1)), set(m.group(2).split())
            if n != len(grammar.ACCENTED):
                failures.append(f"{doc}: accent count {n} != "
                                f"{len(grammar.ACCENTED)} derived from code")
            if listed != set(grammar.ACCENTED):
                failures.append(
                    f"{doc}: accent inventory differs from code: "
                    f"doc-only {sorted(listed - grammar.ACCENTED)}, "
                    f"code-only {sorted(grammar.ACCENTED - listed)}")
        m = re.search(r"Ligatures \((\d+)\): (.+?)\s*$", text, re.M)
        if not m:
            failures.append(f"{doc}: no 'Ligatures (N): …' line")
        else:
            n, listed = int(m.group(1)), set(m.group(2).split())
            if n != len(grammar.LIGATURES):
                failures.append(f"{doc}: ligature count {n} != "
                                f"{len(grammar.LIGATURES)}")
            if listed != set(grammar.LIGATURES):
                failures.append(f"{doc}: ligatures differ from code")
    return failures


def check_charset_counts() -> list[str]:
    failures: list[str] = []
    derived = {
        "letters": len(grammar.LETTERS),
        "charset": len(grammar.CHARSET),
    }
    for doc in ("GRAMMAR.md",):
        text = _read(doc)
        # The summary sentence quotes both totals together; "26 letters"
        # describing the base alphabet elsewhere must not satisfy this.
        m = re.search(r"(\d+) letters(?:,| and) a (\d+)-character charset",
                      text)
        if not m:
            failures.append(f"{doc}: no 'N letters … N-character charset' "
                            "summary sentence")
        else:
            if int(m.group(1)) != derived["letters"]:
                failures.append(f"{doc}: letter total {m.group(1)} != "
                                f"{derived['letters']} derived from code")
            if int(m.group(2)) != derived["charset"]:
                failures.append(f"{doc}: charset total {m.group(2)} != "
                                f"{derived['charset']} derived from code")
        m = re.search(r"`a`–`z` \((\d+) letters\)", text)
        if m and int(m.group(1)) != len(grammar.BASE):
            failures.append(f"{doc}: base-alphabet count {m.group(1)} != "
                            f"{len(grammar.BASE)}")
    return failures


def _check_figures_doc(json_path: Path, doc_path: Path,
                       label: str) -> list[str]:
    if not json_path.exists() and not doc_path.exists():
        return []            # phase not reached yet: nothing to enforce
    if json_path.exists() != doc_path.exists():
        return [f"{label}: {json_path.name} and {doc_path.name} must "
                "exist together"]
    figures = json.loads(json_path.read_text(encoding="utf-8"))
    # typographic minus in prose == ASCII minus in figures
    text = doc_path.read_text(encoding="utf-8").replace("\u2212", "-")
    failures: list[str] = []
    for name, value in figures.get("doc_figures", {}).items():
        want = f"{value:,}" if isinstance(value, int) else str(value)
        if want not in text:
            failures.append(f"{doc_path.name}: figure '{name}' = {want} "
                            "not found in the document")
    return failures


def check_evidence() -> list[str]:
    """C4 step 1: EVIDENCE.md figures, and the build's measured
    applicability held to the 2 structural rules of C-010. The archive's
    check also re-checks the applicability table and the WordNet counts
    that the archive's decision log quotes at C-010; that log is not in
    this repository, so those 2 parts stay with the archive."""
    failures = _check_figures_doc(EVIDENCE_JSON, EVIDENCE_DOC, "evidence")
    if not EVIDENCE_JSON.exists():
        return failures          # step not reached yet
    ev = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    applicability = {src: set(v) for src, v in ev["applicability"].items()}
    for name, app in applicability.items():
        if ("s-final" in app) != ("apostrophe-form" in app):
            failures.append(f"{name}: s-final does not rule with "
                            "apostrophe-form (C-010 claims it does)")
        if name != "screen" and ("plain" in app) == (name == "web2a"):
            failures.append(f"{name}: plain applicability contradicts C-010")
    return failures


def check_features() -> list[str]:
    """C4 step 2: FEATURES.md figures re-derived from the gate, the
    manifest, and the Google Books meta."""
    failures = _check_figures_doc(FEATURES_JSON, FEATURES_DOC, "features")
    if not FEATURES_JSON.exists():
        return failures          # step not reached yet
    text = FEATURES_DOC.read_text(encoding="utf-8")
    gate = json.loads(FEATURES_GATE.read_text(encoding="utf-8"))
    manifest = json.loads(FEATURES_MANIFEST.read_text(encoding="utf-8"))

    # admission table: every row's AUC interval, ratio and verdict
    for fam, row in gate["family_admission"].items():
        label = fam.replace("_", "-")
        sep = row["auc_oriented"]
        if sep is not None:
            want = (f"{sep['auc']:.4f} [{sep['lo']:.4f}, {sep['hi']:.4f}]")
            if want not in text:
                failures.append(f"FEATURES.md: {label} interval "
                                f"'{want}' missing")
        if f"{row['fire_ratio']}" not in text:
            failures.append(f"FEATURES.md: {label} fire ratio "
                            f"{row['fire_ratio']} missing")
        verdict = "admitted" if row["admitted"] else "rejected"
        if not re.search(rf"{label}.*{verdict}", text):
            failures.append(f"FEATURES.md: {label} verdict "
                            f"'{verdict}' missing")
    six = gate["separation"]["ocr"]["ocr_neighbor_freq_ratio_oriented"]
    if f"{six['auc']:.4f}" not in text:
        failures.append("FEATURES.md: six-pair oriented AUC missing")
    for feat, row in gate["sr3"]["per_feature"].items():
        if row is not None and f"{row['auc']:.4f}" not in text:
            failures.append(f"FEATURES.md: SR3 {feat} AUC missing")

    # per-class perplexities against the C-011 bounds
    for cls, ppl in manifest["charmodel"]["perplexity_by_class"].items():
        if cls.startswith("__"):
            continue
        if f"{ppl}" not in text:
            failures.append(f"FEATURES.md: perplexity {cls} = {ppl} missing")
        bound = manifest["charmodel"]["ppl_bounds"].get(cls)
        if bound is not None and ppl > bound:
            failures.append(f"features: class {cls} perplexity {ppl} "
                            f"breaches its bound {bound} but no NA "
                            "fallback recorded")

    # GB probe figures (cached meta; skip cleanly on clean clones)
    if GB_META.exists():
        gb = json.loads(GB_META.read_text(encoding="utf-8"))
        for k, v in gb["class_key_counts"].items():
            if k in ("plain", "s-final"):
                continue
            if f"{v:,}" not in text:
                failures.append(f"FEATURES.md: GB probe {k} = {v:,} missing")
        for v in (gb["record_count"], gb["parity"]["eol_keys"],
                  gb["parity"]["eol_only_keys"]):
            if f"{v:,}" not in text:
                failures.append(f"FEATURES.md: GB figure {v:,} missing")
        if gb["aggregate_sha256"] != manifest["gb"]["aggregate_sha256"]:
            failures.append("features: manifest GB sha != derived meta sha")
    return failures


def check_universe_v2() -> list[str]:
    """S5: universe v2's figures tie to v1, the census, and the shipped
    proofs; the applicability masks are measured zeros, never assumed."""
    failures = _check_figures_doc(UNIVERSE_V2_JSON, UNIVERSE_V2_DOC,
                                  "universe_v2")
    if not UNIVERSE_V2_JSON.exists():
        return failures
    v2 = json.loads(UNIVERSE_V2_JSON.read_text(encoding="utf-8"))
    v1 = json.loads(UNIVERSE_JSON.read_text(encoding="utf-8"))
    census = json.loads(
        SPACE_CENSUS_JSON.read_text(encoding="utf-8"))["doc_figures"]
    fig, fe = v2["doc_figures"], v2["filter_equivalence"]
    ties = (
        ("v2_rows", v1["counts"]["universe_rows"] + census["union_total"]),
        ("v1_rows", v1["counts"]["universe_rows"]),
        ("spaced_additions", census["union_total"]),
        ("wn_only", census["wn_only"]),
        ("wk_only", census["wk_only"]),
        ("both_sources", census["overlap_both"]),
        ("restricted_rows", v1["counts"]["restricted_rows"]),
    )
    for name, want in ties:
        if fig[name] != want:
            failures.append(f"universe_v2.json: {name} = {fig[name]:,} "
                            f"does not re-derive ({want:,})")
    if not (fe["valid_matches_pin"] and fe["invalid_matches_pin"]):
        failures.append("universe_v2.json: EOL filter-equivalence proof "
                        "not recorded as passing")
    if fe["no_space_projection_sha256"] \
            != v1["artifacts"]["canonical_content_sha256"] \
            or not fe["projection_matches_v1_canonical"]:
        failures.append("universe_v2.json: no-space projection does not "
                        "match v1's canonical content hash")
    # the doc quotes the artifact hashes in full
    if UNIVERSE_V2_DOC.exists():
        text = UNIVERSE_V2_DOC.read_text(encoding="utf-8")
        for key in ("universe_v2_parquet_sha256",
                    "canonical_content_sha256_v2", "v1_parquet_sha256"):
            if v2["artifacts"][key] not in text:
                failures.append(f"UNIVERSE_V2.md: {key} not quoted in full")
        if fe["no_space_projection_sha256"] not in text:
            failures.append("UNIVERSE_V2.md: projection hash not quoted")
    # applicability: measured, tied to the census, zeros everywhere else
    if not SPACED_APPLIC.exists():
        failures.append("universe_v2 recorded but spaced_applicability.json "
                        "missing")
        return failures
    ap = json.loads(SPACED_APPLIC.read_text(encoding="utf-8"))
    if sorted(ap["applicable"]) != ["wiktionary_english", "wordnet"]:
        failures.append("spaced_applicability.json: applicable set is not "
                        "exactly {wiktionary_english, wordnet}")
    for name in ap["not_applicable"]:
        det = ap["detectors"][name]
        if det["spaced_count"] != 0 or det["spaced_in_c4_derived"] != 0 \
                or not det.get("account"):
            failures.append(f"spaced_applicability.json: {name} NA cell "
                            "lacks a measured zero with an account")
    if ap["detectors"]["wordnet"]["spaced_count"] != census["wn_spaced"] \
            or ap["detectors"]["wiktionary_english"]["spaced_count"] \
            != census["wk_spaced"]:
        failures.append("spaced_applicability.json: applicable counts do "
                        "not match the census")
    for name, value in ap["doc_figures"].items():
        want = f"{value:,}" if isinstance(value, int) else str(value)
        if UNIVERSE_V2_DOC.exists() \
                and want not in UNIVERSE_V2_DOC.read_text(encoding="utf-8"):
            failures.append(f"UNIVERSE_V2.md: applicability figure "
                            f"'{name}' = {want} not found")
    return failures


#: Halves of checks that cannot run because a GITIGNORED artifact is
#: absent — a fresh clone holds the code and the documents but not the
#: built frames under `data/`. Recorded, never silent: `run()` clears
#: this and the checks append to it, and `codex_stop.py` compares the
#: result against the environment census, so a deferral that appears
#: where none is declared fails the build. C-034.
#:
#: This is not a licence to skip. A check may defer only the part that
#: needs an absent gitignored artifact, and must still run every part
#: it can.
ENVIRONMENT_DEFERRALS: list[str] = []


def _k6_rows_quoted(text: str, rows, name: str) -> list[str]:
    """The pure half of check_d4_spec_k6: every verification row quoted
    verbatim in backticks in the reconciliation (the D3 pattern),
    separated so the guard's ability to fail is tested directly
    (C-032 R7-e)."""
    norm = " ".join(text.split())
    failures: list[str] = []
    for row in rows:
        if f"`{' '.join(row.split())}`" not in norm:
            failures.append(f"{name}: row '{' '.join(row.split())[:48]}…' "
                            f"not quoted")
    return failures


def _provenance_report_failures(report: str, template: str, body: dict,
                                render) -> list[str]:
    """The pure half of check_provenance, separated so the guard's
    ability to fail is tested directly (C-032 R7-e): the report is the
    rendering of its template over provenance.json — so every figure of
    the report is a row of the JSON — and the template itself carries no
    literal comma-grouped figure and no literal percentage."""
    import re
    failures: list[str] = []
    bare = re.sub(r"\{\{[^{}]+\}\}", "", template)
    literal = re.findall(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?%", bare)
    if literal:
        failures.append(
            f"PROVENANCE.template.md carries {len(literal)} literal "
            f"figure(s) ({', '.join(literal[:3])}); every figure of the "
            f"report is a placeholder naming a row of provenance.json")
    try:
        want = render(body, template)
    except KeyError as exc:
        return failures + [
            f"PROVENANCE.template.md names a row provenance.json does "
            f"not hold: {exc}"]
    if want != report:
        failures.append(
            "PROVENANCE.md is not the rendering of its template over "
            "provenance.json (run python3 -m "
            "research.provenance.build_provenance --render)")
    return failures


def check_provenance() -> list[str]:
    """The intake-provenance layer (C-064; research/provenance/): the
    report is the rendering of its template over provenance.json; the
    JSON's blocks tie to the manifest, to the pin's record, to the
    evidence and feature records, and to one another (the four classes
    and the three kinds each partition the rows; the two classes without
    containment are the SR2 reading-B row; the generated rows are the
    EOL report's quoted count); and the measured block re-derives from
    data/universe_v2_provenance.parquet where data/ exists — a declared
    deferral in the clone environment the census routes, on the
    check_d4_instrument pattern (C-064 ruling 10)."""
    required = [REPO / rel for rel in REQUIRED_ARTIFACTS["check_provenance"]]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return [f"provenance: {', '.join(missing)} missing"]
    import importlib
    bp = importlib.import_module("research.provenance.build_provenance")
    importlib.reload(bp)
    ex = importlib.import_module("research.provenance.extract_eol_intake")
    from ceol.ingest.common import sha256_file
    pdir = REPO / "research" / "provenance"
    body = json.loads((pdir / "provenance.json").read_text(encoding="utf-8"))
    manifest_path = pdir / "eol_dictionaries_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = _provenance_report_failures(
        (pdir / "PROVENANCE.md").read_text(encoding="utf-8"),
        (pdir / "PROVENANCE.template.md").read_text(encoding="utf-8"),
        body, bp.render_report)

    m, inputs = body["measured"], body["inputs"]
    v2 = json.loads(UNIVERSE_V2_JSON.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    layers = m["rows_by_layer"]
    ties = (
        ("rows", m["rows"], v2["counts"]["v2_rows"]),
        ("eol_valid rows", layers.get("eol_valid"),
         v2["counts"]["eol_valid"]),
        ("eol_invalid rows", layers.get("eol_invalid"),
         v2["counts"]["eol_invalid"]),
        ("spaced_c015 rows", layers.get("spaced_c015"),
         v2["counts"]["spaced_additions"]),
        ("the layers' sum", sum(layers.values()), m["rows"]),
        ("the classes' sum", sum(m["rows_by_class"].values()), m["rows"]),
        ("the kinds' sum", sum(m["rows_by_kind"].values()), m["rows"]),
        ("the pin's sha256", inputs["universe_v2_parquet_sha256"],
         v2["artifacts"]["universe_v2_parquet_sha256"]),
        ("the evidence matrix's sha256", inputs["evidence_parquet_sha256"],
         evidence["artifacts"]["evidence_parquet_sha256"]),
        ("the manifest's sha256", inputs["eol_dictionaries_manifest_sha256"],
         sha256_file(manifest_path)),
        ("the valid dictionary's sha256", inputs["merged_valid_dict_sha256"],
         ex.VALID["sha256"]),
        ("the invalid dictionary's sha256",
         inputs["merged_invalid_dict_sha256"], ex.INVALID["sha256"]),
        ("the manifest's valid sha256",
         manifest["dictionaries"]["valid"]["sha256"], ex.VALID["sha256"]),
        ("the manifest's invalid sha256",
         manifest["dictionaries"]["invalid"]["sha256"],
         ex.INVALID["sha256"]),
        ("the hub's ETag as read",
         manifest["dictionaries"]["invalid"]["hub_etag_as_read"],
         ex.INVALID["sha256"]),
        ("the invalid dictionary's bytes",
         manifest["dictionaries"]["invalid"]["bytes"], ex.INVALID["bytes"]),
        ("the pin block", body["pin"], bp.pin_block()),
        ("the coverage block", body["coverage"], bp.coverage_block(manifest)),
        ("the percentages", body["percentages"], bp.percentages(m)),
        ("the reconciliations", body["reconciliations"],
         bp.reconciliations(m)),
        ("channel_only plus neither against SR2 reading B",
         body["reconciliations"]["channel_only_plus_neither"],
         body["reconciliations"]["sr2_reading_b_rows"]),
        ("the generated rows against the EOL's quoted count",
         m["generated"]["rows"],
         body["quoted"]["eol_phase2d_generated"]["value"]),
        ("the ledger-named generated rows",
         m["generated"]["by_eol_record"].get("none"),
         manifest["no_entry_strings_accounted_for"][
             "named_by_the_two_demotion_ledgers"]),
        ("the ledger cross-check's rows",
         body["ledger_cross_check"]["ledger_rows"],
         manifest["no_entry_strings_accounted_for"][
             "demotion_ledger_rows_in_all"]),
        ("the quoted figures",
         {k: v["value"] for k, v in body["quoted"].items()},
         {name: value for name, value, _ in bp.QUOTED}),
    )
    for name, got, want in ties:
        if got != want:
            failures.append(f"provenance.json: {name} does not tie "
                            f"({str(got)[:60]} against {str(want)[:60]})")
    if set(m["rows_by_class"]) - set(bp.CLASSES) \
            or set(m["rows_by_kind"]) - set(bp.KINDS):
        failures.append("provenance.json: a class or a kind outside the "
                        "declared values")
    stray = set(m["channel_label_rows"]) - set(bp.VOCABULARY)
    if stray:
        failures.append(f"provenance.json: {len(stray)} channel label(s) "
                        f"outside the closed vocabulary")

    # the half that needs the gitignored layer
    in_clone = not (REPO / "data" / "evidence.parquet").exists()
    if in_clone:
        ENVIRONMENT_DEFERRALS.append(
            "check_provenance: this is the clone environment the census "
            "routes (no data/evidence.parquet), which holds no "
            "data/universe_v2_provenance.parquet; re-deriving "
            "provenance.json's measured block from the layer is deferred "
            "(the report's rendering, the template's literals, and every "
            "tie between the committed records ran)")
    elif not bp.OUT_PARQUET.exists():
        failures.append("data/universe_v2_provenance.parquet is absent "
                        "where data/ exists; build it (python3 -m "
                        "research.provenance.build_provenance)")
    else:
        if sha256_file(bp.OUT_PARQUET) != body["artifact"]["sha256"]:
            failures.append("data/universe_v2_provenance.parquet is not "
                            "the file provenance.json records")
        fresh = bp.measure(bp.OUT_PARQUET)
        drift = sorted(k for k in set(fresh) | set(m)
                       if fresh.get(k) != m.get(k))
        if drift:
            failures.append("provenance.json's measured block does not "
                            "re-derive from the layer: "
                            + ", ".join(drift[:6]))
    return failures


_PQ_LD = re.compile(r"^- \*\*(PQ-LD-\d+) · [^.]+\.\*\*", re.M)


def _release_failures(card: str, template: str, row_values: dict,
                      table_lines: dict, render, literals, record: dict, expected: dict,
                      profile: dict, pos: dict, upload: dict) -> list[str]:
    """The pure half of check_release, separated so the guard's ability to
    fail is tested directly (C-032 R7-e; AT-UR1-7): the card is the
    rendering of its template over release_calcs.py's rows and tables,
    and the template carries no literal figure; the record's identities agree with the
    committed pin records and with the code (the source layers' hashes,
    the row counts by config, the columns, the predicates, the canary,
    every assertion block present with no hit); the profile and the
    part-of-speech estimate describe the files the record names; the upload
    record names the private dataset, the version, the record's files by the
    hub's LFS sha256, and the committed card and record as the uploaded
    ones.

    C-079 line 1 (F8): every assertion block carries exactly the fields
    `build_release.ASSERTION_FIELDS` declares for its config and AT
    identifier; `restricted_words_checked` is the pin record's restricted
    count, `controls_checked` the walled controls' count,
    `ledger_words_outside_the_pin_checked` the count recomputed from the
    intake ledger and the pin (`expected["ledger_outside"]`) or, where the
    ledger is absent (None, a clone), a record-internal consistency check
    only: every block repeats the universe block's count, which nothing
    outside the record confirms; `rows_in_pin_order` is the shippable rows,
    the features' `columns_without_nulls` the features columns, every hit
    0; and the upload's `files` are the record's files plus README.md, in
    order."""
    import re
    failures: list[str] = []
    literal = literals(template)
    if literal:
        failures.append(f"CARD.template.md carries {len(literal)} literal "
                        f"figure(s) ({', '.join(literal[:3])}); every figure "
                        f"of the card is a row of release_calcs.py")
    try:
        want = render(template, row_values, table_lines)
    except KeyError as exc:
        return failures + [f"CARD.template.md names a row release_calcs.py "
                           f"does not print: {exc}"]
    if want != card:
        failures.append("CARD.md is not the rendering of its template over "
                        "release_calcs.py (run python3 -m "
                        "research.release.release_calcs --render)")
    files = {f.get("config"): f for f in record.get("files", [])}
    ties = (
        ("the version", record.get("version"), expected["version"]),
        ("the dataset", record.get("dataset"), expected["dataset"]),
        ("the canary", record.get("canary"), expected["canary"]),
        ("the source layers' hashes",
         {k: v.get("sha256") for k, v in record.get("sources", {}).items()},
         expected["sources"]),
        ("the rows by config", record.get("rows_by_config"),
         {k: f.get("rows") for k, f in files.items()}),
        ("the configs", sorted(files), sorted(expected["predicates"])),
        ("the predicates", {k: f.get("predicate") for k, f in files.items()},
         expected["predicates"]),
        ("the universe's rows", files.get("universe", {}).get("rows"),
         expected["shippable_rows"]),
        ("the spaced rows", files.get("spaced", {}).get("rows"),
         expected["spaced_rows"]),
        ("the eol-valid rows", files.get("eol-valid", {}).get("rows"),
         expected["eol_valid"]),
        ("the features rows", files.get("features", {}).get("rows"),
         expected["single_token_shippable"]),
        ("the profile's version", profile.get("version"), expected["version"]),
        ("the profile's configs", profile.get("configs"),
         record.get("rows_by_config")),
        ("the profile's file hashes",
         {k: v.get("sha256") for k, v in profile.get("files", {}).items()},
         {k: f.get("sha256") for k, f in files.items()}),
        ("the estimate's version", pos.get("version"), expected["version"]),
        ("the estimate's rows", pos.get("universe_rows"),
         files.get("universe", {}).get("rows")),
        ("the upload's dataset", upload.get("repo_id"), expected["dataset"]),
        ("the upload's version", upload.get("version"), expected["version"]),
        ("the upload's visibility", upload.get("private"), True),
        ("the upload's files", upload.get("files"),
         [f"data/{f.get('path')}" for f in record.get("files", [])]
         + ["README.md"]),
        ("the upload's hub hashes", upload.get("hub_lfs_sha256"),
         {f"data/{f.get('path')}": f.get("sha256") for f in files.values()}),
        ("the uploaded card", upload.get("card_sha256"),
         expected["card_sha256"]),
        ("the uploaded record", upload.get("record_sha256"),
         expected["record_sha256"]),
    )
    for name, got, want in ties:
        if got != want:
            failures.append(f"release_{expected['version']}.json: {name} does "
                            f"not tie ({str(got)[:60]} against "
                            f"{str(want)[:60]})")
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}"
                        r"-[0-9a-f]{12}", str(record.get("canary"))):
        failures.append("the canary is not a version-4 UUID")
    for config, f in files.items():
        want_cols = expected["features_columns"] if config == "features" \
            else expected["universe_columns"]
        if f.get("columns") != want_cols:
            failures.append(f"release record: {config}'s columns are not the "
                            f"declared list")
        if not re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256"))):
            failures.append(f"release record: {config} carries no sha256")
    blocks = record.get("assertions", {})
    ledger = expected["ledger_outside"]
    if ledger is None:          # the ledger is absent: the record's own
        ledger = blocks.get("universe", {}).get("AT-UR1-6", {}).get(
            "ledger_words_outside_the_pin_checked")
    for config, schema in expected["assertion_fields"].items():
        have = blocks.get(config, {})
        if set(have) != set(schema):
            failures.append(f"release record: {config}'s assertions are "
                            f"{sorted(have)}, not {sorted(schema)}")
        tied = {"restricted_words_checked": expected["restricted_rows"],
                "controls_checked": expected["controls"],
                "ledger_words_outside_the_pin_checked": ledger,
                "rows_in_pin_order": expected["shippable_rows"]}
        if config == "features":
            tied["columns_without_nulls"] = len(expected["features_columns"])
        for at, fields in schema.items():
            block = have.get(at, {})
            missing = [k for k in fields if k not in block]
            if missing:
                failures.append(f"release record: {config} {at} lacks "
                                f"{', '.join(missing)}")
            extra = sorted(set(block) - set(fields))
            if extra:
                failures.append(f"release record: {config} {at} carries "
                                f"the undeclared {', '.join(extra)}")
            for k, v in block.items():
                if k.endswith("_hits"):
                    if v != 0:
                        failures.append(f"release record: {config} records "
                                        f"a hit ({at} {k} {v})")
                elif k in tied and v != tied[k]:
                    failures.append(f"release record: {config} {at} {k} is "
                                    f"{v}, not {tied[k]}")
    return failures


def _profile_failures(fresh_text: str, committed_text: str, plots_dir: Path,
                      decode_pixels) -> list[str]:
    """The profile comparison of check_release's data half, separated so
    that a fixture reaches it (C-079 line 1, F2; AT-UR1-9): the committed
    profile.json is the fresh computation over the release files, byte for
    byte, and each committed plot's pixels hash to the sha256 the committed
    profile records for it."""
    import hashlib
    failures: list[str] = []
    committed = json.loads(committed_text)
    if fresh_text != committed_text:
        fresh = json.loads(fresh_text)
        drift = sorted(k for k in set(fresh) | set(committed)
                       if fresh.get(k) != committed.get(k))
        failures.append(f"profile.json does not re-derive from the release "
                        f"files: {', '.join(drift[:6])}")
    for name, meta in committed.get("plots", {}).items():
        path = plots_dir / name
        if not path.exists() or hashlib.sha256(decode_pixels(
                path.read_bytes()).tobytes()).hexdigest() != \
                meta["pixels_sha256"]:
            failures.append(f"plots/{name} is not the plot profile.json "
                            f"records")
    return failures


def _release_inputs() -> dict:
    """The inputs check_release hands to `_release_failures`, as keyword
    arguments, read from the committed files with the release modules
    reloaded so that an edit is read; where data/ holds the intake ledger
    and the pin (the repository environment), the count of the ledger's
    words outside the pin is recomputed from them, and elsewhere it is None
    (C-079 line 1, F8). Separated so that AT-UR1-7 can alter 1 input at a
    time."""
    import importlib
    cols = importlib.reload(importlib.import_module("research.release.columns"))
    br = importlib.reload(importlib.import_module(
        "research.release.build_release"))
    calcs = importlib.reload(importlib.import_module(
        "research.release.release_calcs"))
    rdir = REPO / "research" / "release"
    version = calcs.VERSION
    record = json.loads(calcs.RECORD.read_text(encoding="utf-8"))
    v2 = json.loads(UNIVERSE_V2_JSON.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    provenance = json.loads((REPO / "research" / "provenance" /
                             "provenance.json").read_text(encoding="utf-8"))
    counts = v2["counts"]
    from ceol.ingest.common import sha256_file
    spec = br.resolve(version)
    pin = {x.name: x for x in spec.layers}["pin"].path
    ledger_outside = None
    if (REPO / "data" / "evidence.parquet").exists() and \
            spec.ledger_csv.exists() and pin.exists():
        import pyarrow.parquet as pq
        ledger_outside = len(br.ledger_outside_the_pin(
            spec, pq.read_table(pin, columns=["word"])["word"]))
    expected = {
        "version": version, "dataset": br.DATASET, "canary": br.CANARY,
        "card_sha256": sha256_file(rdir / "CARD.md"),
        "record_sha256": sha256_file(calcs.RECORD),
        "sources": {
            "pin": v2["artifacts"]["universe_v2_parquet_sha256"],
            "provenance": provenance["artifact"]["sha256"],
            "evidence": evidence["artifacts"]["evidence_parquet_sha256"],
            "features": provenance["inputs"]["features_parquet_sha256"]},
        "shippable_rows": counts["v2_rows"] - counts["restricted_rows"],
        "spaced_rows": counts["spaced_additions"],
        "eol_valid": counts["eol_valid"],
        "single_token_shippable": counts["v1_rows"] - counts["restricted_rows"],
        "predicates": {"universe": br.UNIVERSE_PREDICATE,
                       "features": br.FEATURES_PREDICATE,
                       **dict(br.FILTER_CONFIGS)},
        "universe_columns": list(cols.UNIVERSE_COLUMNS),
        "features_columns": list(cols.FEATURES_COLUMNS),
        "assertion_fields": {
            config: br.assertion_fields(config)
            for config in ("universe", "features",
                           *(name for name, _p in br.FILTER_CONFIGS))},
        "restricted_rows": counts["restricted_rows"],
        # the wall list is private: where it is absent, the record's own
        # count stands and check_release declares the deferral
        "controls": (len(br.read_controls()) if wall.available()
                     else record.get("assertions", {}).get("universe", {})
                     .get("AT-UR1-6", {}).get("controls_checked")),
        "ledger_outside": ledger_outside,
    }
    return dict(
        card=(rdir / "CARD.md").read_text(encoding="utf-8"),
        template=(rdir / "CARD.template.md").read_text(encoding="utf-8"),
        row_values=calcs.rows(), table_lines=calcs.tables(),
        render=calcs.render, literals=calcs.template_literals,
        record=record, expected=expected,
        profile=json.loads(calcs.PROFILE.read_text(encoding="utf-8")),
        pos=json.loads(calcs.POS.read_text(encoding="utf-8")),
        upload=json.loads(calcs.UPLOAD.read_text(encoding="utf-8")))


def check_release() -> list[str]:
    """UR-1, the release package of the CEOL Universe (C-078;
    research/release/): the card is the rendering of its template over
    release_calcs.py; the
    release record's identities tie to the committed pin records and the
    code, its assertion blocks carry their declared fields and counts, and
    the upload record's inventory is the record's (C-079 line 1, F8); the
    profile describes the recorded files (the pure half,
    `_release_failures`, over `_release_inputs`). Where data/ exists, the
    pinned layers' hashes equal the record's sources, the release files'
    hashes equal the record's, profile.json and pos_estimate.json
    re-derive from the release files, and each committed plot's pixels
    equal the profile's hash; in the clone environment the census routes,
    that half is a declared deferral (the census's clone allowlist, on the
    C-060 precedent)."""
    required = [REPO / rel for rel in REQUIRED_ARTIFACTS["check_release"]]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return [f"the release: {', '.join(missing)} missing"]
    import importlib
    from ceol.ingest.common import sha256_file
    inputs = _release_inputs()
    failures = _release_failures(**inputs)
    if not wall.available():
        ENVIRONMENT_DEFERRALS.append(
            "check_release: private/wall is absent, so the count of the "
            "walled controls the record is tied to is deferred (the "
            "record's own count stands in its place)")
    br = importlib.import_module("research.release.build_release")
    calcs = importlib.import_module("research.release.release_calcs")
    version = calcs.VERSION
    record = inputs["record"]

    # the half that needs the gitignored layers and release files
    if not (REPO / "data" / "evidence.parquet").exists():
        ENVIRONMENT_DEFERRALS.append(
            "check_release: this is the clone environment the census routes "
            "(no data/evidence.parquet), which holds no data/release/; "
            "comparing the release files and the layers with the record and "
            "re-deriving the profile from the release files is deferred (the "
            "card's rendering, the template's literals, the contract's rows, "
            "and every tie between the committed records ran)")
        return failures
    spec = br.resolve(version)
    if not spec.out_dir.exists():
        return failures + [f"{spec.out_dir.relative_to(REPO)} is absent where "
                           f"data/ exists; build it (python3 -m "
                           f"research.release.build_release --version "
                           f"{version})"]
    try:
        br.verify_layers(spec)
    except br.ReleaseError as exc:
        failures.append(f"the release's source layers: {exc}")
    for f in record["files"]:
        if sha256_file(spec.out_dir / f["path"]) != f["sha256"]:
            failures.append(f"data/release: {f['path']} is not the file the "
                            f"record names")
    up = importlib.reload(importlib.import_module(
        "research.release.profile.universe_profile"))
    pe = importlib.reload(importlib.import_module(
        "research.release.profile.pos_estimate"))
    png = importlib.reload(importlib.import_module(
        "research.release.profile.png_plot"))
    fresh, _plots = up.compute(spec.out_dir, version)
    failures += _profile_failures(
        up.dumps(fresh), calcs.PROFILE.read_text(encoding="utf-8"),
        up.PLOTS_DIR, png.decode_pixels)
    if pe.dumps(pe.compute(spec.out_dir, version)) != \
            calcs.POS.read_text(encoding="utf-8"):
        failures.append("pos_estimate.json does not re-derive from the "
                        "release files")
    return failures


def _release_report_failures(report: str, template: str, references: str,
                             report_rows: dict, release_rows: dict, calcs,
                             manifest: dict, delivered: str,
                             record_version: str) -> list[str]:
    """The pure half of check_release_report, separated so the guard's
    ability to fail is tested directly (C-032 R7-e; AT-UP1-5): the report is
    the rendering of its template over report_calcs.py's and
    release_calcs.py's rows, every row quoted verbatim in backticks; the
    template carries no figure outside its placeholders, quotes every row of
    report_calcs.py, and quotes exactly the release rows RELEASE_ROWS
    names; the report carries no figure outside its rows (AT-UP1-1); its
    version marker, and every version a row names, is the release
    record's (AT-UP1-4); every citation key resolves to a row of
    references/MANIFEST.csv or to the delivered bibliography, and
    REFERENCES.md is the rendering of the cited keys (AT-UP1-3)."""
    failures: list[str] = list(
        calcs.template_problems(template, report_rows, release_rows))
    try:
        want = calcs.render(template, report_rows, release_rows)
    except KeyError as exc:
        return failures + [f"REPORT.template.md names a row no calculator "
                           f"prints: {exc}"]
    if want != report:
        failures.append("REPORT.md is not the rendering of its template over "
                        "the calculators' rows (run python3 -m "
                        "research.release.report.report_calcs --render)")
    for name, value in report_rows.items():
        if f"`{value}`" not in report:
            failures.append(f"REPORT.md does not quote the row {name} "
                            f"verbatim in backticks")
    values = list(report_rows.values()) + list(release_rows.values())
    stray = calcs.stray_figures(report, values)
    if stray:
        failures.append(f"REPORT.md carries {len(stray)} figure(s) outside "
                        f"its rows ({', '.join(stray[:4])})")
    markers = calcs.version_markers(report)
    if markers != [record_version]:
        failures.append(f"REPORT.md's version marker is {markers}, not the "
                        f"release record's version {record_version!r}")
    stale = sorted(calcs.row_versions(values) - {record_version})
    if stale:
        failures.append(f"rows name versions other than the release "
                        f"record's: {', '.join(stale)}")
    keys = calcs.cited_keys(report)
    unresolved = calcs.unresolved_keys(keys, manifest, delivered)
    if unresolved:
        failures.append(f"REPORT.md cites keys with no row of "
                        f"references/MANIFEST.csv: {', '.join(unresolved)}")
    elif references != calcs.render_references(keys, manifest, delivered):
        failures.append("REFERENCES.md is not the rendering of the report's "
                        "citation keys (run python3 -m "
                        "research.release.report.report_calcs --render)")
    return failures


def _release_report_inputs() -> dict:
    """The inputs check_release_report hands to `_release_report_failures`,
    read from the committed files with the calculators reloaded so that an
    edit is read. Separated so that AT-UP1-5 can alter 1 input at a time."""
    import importlib
    importlib.reload(importlib.import_module("research.release.columns"))
    importlib.reload(importlib.import_module("research.release.build_release"))
    importlib.reload(importlib.import_module("research.release.release_calcs"))
    calcs = importlib.reload(importlib.import_module(
        "research.release.report.report_calcs"))
    release = importlib.import_module("research.release.release_calcs")
    record = json.loads(release.RECORD.read_text(encoding="utf-8"))
    return dict(
        report=calcs.REPORT.read_text(encoding="utf-8"),
        template=calcs.TEMPLATE.read_text(encoding="utf-8"),
        references=calcs.REFERENCES.read_text(encoding="utf-8"),
        report_rows=calcs.rows(), release_rows=release.rows(), calcs=calcs,
        manifest=calcs.manifest_rows(), delivered=calcs.delivered_entries(),
        record_version=record["version"])


def _public_release_failures(card: str, template: str, row_values: dict,
                             table_lines: dict, calcs, record: dict,
                             documents: dict, notices_sha: str,
                             commit_known: bool | None, br) -> list[str]:
    """The pure half of check_public_release, separated so that a test
    alters 1 input at a time: the public card is the rendering of its
    template, which carries no literal figure; each generated document
    equals what documents.py prints; the record's assertion blocks carry
    their declared fields, its NOTICES.md is the committed NOTICES file, its
    held-back rows sum by reason, and its code commit is in this
    repository's history (None where git cannot say)."""
    failures: list[str] = []
    literal = calcs.template_literals(template)
    if literal:
        failures.append(f"CARD_v1.0.template.md carries literal figures: "
                        f"{', '.join(literal[:4])}")
    try:
        want = calcs.render(template, row_values, table_lines)
    except KeyError as exc:
        return failures + [f"CARD_v1.0.template.md names a row no calculator "
                           f"prints: {exc}"]
    if want != card:
        failures.append("CARD_v1.0.md is not the rendering of its template "
                        "over public_card.py (run python3 -m "
                        "research.release.public_card --render)")
    for path, (committed, printed) in documents.items():
        if committed != printed:
            failures.append(f"{path} is not what documents.py prints (run "
                            f"python3 -m research.release.documents "
                            f"--version {record['version']})")
    for config, blocks in record["assertions"].items():
        want_fields = br.assertion_fields(config, True)
        got = {at: tuple(block) for at, block in blocks.items()}
        if got != want_fields:
            failures.append(f"release_{record['version']}.json: the {config} "
                            f"blocks are not the declared fields")
    if [d["sha256"] for d in record.get("documents", [])
            if d["path"] == "NOTICES.md"] != [notices_sha]:
        failures.append("the record's NOTICES.md is not the committed "
                        "NOTICES file")
    held = record["projection"]["held_back"]
    if sum(held["by_reason"].values()) != held["rows"]:
        failures.append("the record's held-back rows do not sum by reason")
    if commit_known is False:
        failures.append(f"the record's code commit {record['code']['commit']} "
                        f"is not in this repository's history")
    return failures


def _history_begins_after(day: str, repo: Path | None = None) -> bool:
    """Whether the repository's history begins after `day` (an ISO date), or
    there is no history: then a commit made by `day` cannot be in it, as in
    a repository published as 1 new commit of the product."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(repo or REPO), "log",
                              "--reverse", "--format=%cs"],
                             capture_output=True, text=True)
    except OSError:
        return True
    first = out.stdout.split()[:1]
    return out.returncode != 0 or not first or first[0] > day


def check_public_release() -> list[str]:
    """v1.0, the first public version (D-014; it holds v2.1's rows):
    the pure half, `_public_release_failures`, over the committed files.
    Where data/ exists, the release files' hashes equal the record's, the
    profile re-derives from them byte for byte, and each committed plot's
    pixels equal the profile's hash; in a clone that half is a declared
    deferral."""
    required = [REPO / rel for rel in REQUIRED_ARTIFACTS["check_public_release"]]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return [f"the public release: {', '.join(missing)} missing"]
    import importlib
    import subprocess
    from ceol.ingest.common import sha256_file
    importlib.reload(importlib.import_module("research.release.columns"))
    importlib.reload(importlib.import_module("research.release.withholding"))
    br = importlib.reload(importlib.import_module(
        "research.release.build_release"))
    calcs = importlib.reload(importlib.import_module(
        "research.release.release_calcs"))
    docs = importlib.reload(importlib.import_module(
        "research.release.documents"))
    card = importlib.reload(importlib.import_module(
        "research.release.public_card"))
    record = json.loads(card.RECORD.read_text(encoding="utf-8"))
    version = record["version"]
    documents = {p.relative_to(REPO.parent).as_posix(): (
        p.read_text(encoding="utf-8") if p.exists() else None, text)
        for p, text in docs.outputs(version).items()}
    try:
        commit_known = subprocess.run(
            ["git", "-C", str(REPO), "cat-file", "-e",
             f"{record['code']['commit']}^{{commit}}"],
            capture_output=True).returncode == 0
    except OSError:
        commit_known = None
    if commit_known is False and _history_begins_after(record["built_on"]):
        # a repository published as 1 new commit of the product cannot hold
        # the commit the release was built from; the record names it, and
        # this clone cannot check it (the G4 audit's F8)
        ENVIRONMENT_DEFERRALS.append(
            f"check_public_release: this repository's history begins after "
            f"the build of {record['built_on']}, so the build commit "
            f"{record['code']['commit'][:12]} cannot be in it; it stays the "
            f"record's declared identifier")
        commit_known = None
    failures = _public_release_failures(
        card=card.CARD.read_text(encoding="utf-8"),
        template=card.TEMPLATE.read_text(encoding="utf-8"),
        row_values=card.rows(), table_lines=card.tables(), calcs=calcs,
        record=record, documents=documents,
        notices_sha=sha256_file(REPO / "research" / "release"
                                / f"NOTICES_{version}.md"),
        commit_known=commit_known, br=br)
    if not (REPO / "data" / "evidence.parquet").exists():
        ENVIRONMENT_DEFERRALS.append(
            "check_public_release: this is the clone environment (no "
            "data/evidence.parquet), which holds no data/release/; comparing "
            "the release files with the record and re-deriving the profile "
            "from them is deferred (the card's rendering, the documents, and "
            "the record's ties ran)")
        return failures
    spec = br.resolve(version)
    if not spec.out_dir.exists():
        return failures + [f"{spec.out_dir.relative_to(REPO)} is absent where "
                           f"data/ exists; build it (python3 -m "
                           f"research.release.build_release --version "
                           f"{version})"]
    for f in record["files"] + record["documents"]:
        if sha256_file(spec.out_dir / f["path"]) != f["sha256"]:
            failures.append(f"data/release: {f['path']} is not the file the "
                            f"record names")
    up = importlib.reload(importlib.import_module(
        "research.release.profile.universe_profile"))
    png = importlib.reload(importlib.import_module(
        "research.release.profile.png_plot"))
    fresh, _plots = up.compute(spec.out_dir, version)
    failures += _profile_failures(
        up.dumps(fresh), card.PROFILE.read_text(encoding="utf-8"),
        card.PLOTS_DIR, png.decode_pixels)
    return failures


def _release_figures_failures(figures: dict, cube: dict, record: dict) -> list[str]:
    """The clone half of check_release_figures: the figures file and the cube
    are of the recorded version and file, and every figure the record states
    is the record's (the configs' rows, the pin's counts, the held-back rows
    by reason); the cube's cells sum to the universe's rows."""
    failures: list[str] = []
    value = {f["id"]: f["value"] for f in figures["figures"]}
    universe = next(f for f in record["files"] if f["config"] == "universe")
    for name, doc in (("figures.json", figures), ("cube.json", cube)):
        if doc["version"] != record["version"] or \
                doc["source"]["sha256"] != universe["sha256"]:
            failures.append(f"figures/{record['version']}/{name} is not of the "
                            f"recorded universe file")
    want = {f"config.{c}.rows": n for c, n in record["rows_by_config"].items()}
    pin = record["pin_counts"]
    want.update({"pin.rows": pin["rows"],
                 "pin.restricted_rows": pin["restricted_rows"],
                 "pin.shippable_rows": pin["shippable_rows"],
                 "rows": record["rows_by_config"]["universe"]})
    held = record["projection"]["held_back"]
    want["held_back.rows"] = held["rows"]
    want.update({f"held_back.{k}": n for k, n in held["by_reason"].items()})
    drift = sorted(k for k, n in want.items() if value.get(k) != n)
    if drift:
        failures.append(f"figures.json does not state the record's "
                        f"{', '.join(drift[:6])}")
    if sum(c[-1] for c in cube["cells"]) != record["rows_by_config"]["universe"]:
        failures.append("cube.json's cells do not sum to the universe's rows")
    return failures


def check_release_figures() -> list[str]:
    """The figures file and the cube the site and the kit read: the pure half,
    `_release_figures_failures`, ties them to the record. Where data/ exists,
    both are rebuilt from the release file by figures.py and must equal the
    committed text; in a clone that half is a declared deferral."""
    required = [REPO / rel for rel in REQUIRED_ARTIFACTS["check_release_figures"]]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return [f"the figures file: {', '.join(missing)} missing"]
    import importlib
    F = importlib.reload(importlib.import_module("research.release.figures"))
    record = json.loads((REPO / "research" / "release" / "release_v1.0.json")
                        .read_text(encoding="utf-8"))
    out = F.out_dir(record["version"])
    figures = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    cube = json.loads((out / "cube.json").read_text(encoding="utf-8"))
    failures = _release_figures_failures(figures, cube, record)
    if not (REPO / "data" / "evidence.parquet").exists():
        ENVIRONMENT_DEFERRALS.append(
            "check_release_figures: this is the clone environment (no "
            "data/evidence.parquet), which holds no data/release/; rebuilding "
            "figures.json and cube.json from the release file is deferred "
            "(their ties to the release record ran)")
        return failures
    for path, text in F.build(record["version"]).items():
        if path.read_text(encoding="utf-8") != text:
            failures.append(f"figures/{record['version']}/{path.name} is not what "
                            f"figures.py prints from the release file (run "
                            f"python3 -m research.release.figures --version "
                            f"{record['version']})")
    return failures


def check_release_report() -> list[str]:
    """UP-1, the report skeleton of the CEOL Universe (C-078 line 7;
    research/release/report/): REPORT.md is the rendering of its template
    over report_calcs.py and release_calcs.py, every figure a row quoted
    verbatim in backticks and no figure outside a row; the version marker
    is the release record's; every citation resolves to the references
    manifest and REFERENCES.md is their rendering (the pure half,
    `_release_report_failures`, over `_release_report_inputs`). Every input
    is committed, so the check runs whole in a clone and declares no
    deferral."""
    required = [REPO / rel
                for rel in REQUIRED_ARTIFACTS["check_release_report"]]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        return [f"the release report: {', '.join(missing)} missing"]
    from research.archival import HELD
    if not (HELD / "research" / "audit" / "AUDIT.md").exists():
        ENVIRONMENT_DEFERRALS.append(
            "check_release_report: private/held is absent, and the "
            "report's calculator reads 2 figures from the audit's held "
            "Markdown record, so the whole check is "
            "deferred")
        return []
    return _release_report_failures(**_release_report_inputs())


FEATURE_LEAK_JSON = REPO / "research" / "release" / "feature_leak_v2.1.json"
FEATURE_COLUMNS_DOC = locations.REPO / "docs" / "licenses" / "FEATURE_COLUMNS.md"


def check_feature_leak() -> list[str]:
    """The figures of the orthotactic columns' test: the document that
    explains it quotes every figure of its record, and the record's verdict
    is the projection's (a column the test finds revealing is withheld)."""
    from research.release import withholding as W
    failures = _check_figures_doc(FEATURE_LEAK_JSON, FEATURE_COLUMNS_DOC,
                                  "feature leak")
    if not FEATURE_LEAK_JSON.exists():
        return failures
    record = json.loads(FEATURE_LEAK_JSON.read_text(encoding="utf-8"))
    for column, reveals in record["reveals"].items():
        if reveals and column not in W.WITHHELD_FEATURES:
            failures.append(f"feature leak: {column} reveals a withheld "
                            "list and a public version ships it")
    return failures


def check_paper() -> list[str]:
    """The technical paper of the public version (D-015): its template
    carries no literal figure, the paper is the rendering of its template
    over paper.py's rows and tables, and the descriptive analysis it reads
    describes the release record's files and adds up (its tiers sum to the
    single-token rows, and the union of the lists is the listed tiers).
    Every input is committed, so the check runs whole in a clone; the
    analysis's rebuild from the release files is the test
    tests/test_descriptive.py, where data/ exists."""
    import importlib
    paper = importlib.reload(importlib.import_module("research.release.report.paper"))
    failures: list[str] = []
    for path in (paper.TEMPLATE, paper.PAPER, paper.ANALYSIS, paper.LITERATURE, paper.CLAIMS):
        if not path.exists():
            failures.append(f"the paper: {path.name} missing")
    if failures:
        return failures
    from research.release import release_calcs as calcs
    literal = calcs.template_literals(paper.TEMPLATE.read_text(encoding="utf-8"))
    if literal:
        failures.append(f"{paper.TEMPLATE.name} carries literal figures: {', '.join(literal[:6])}")
    try:
        text = paper.render()
    except (KeyError, ValueError) as exc:
        return failures + [f"{paper.TEMPLATE.name} does not render: {exc}"]
    if paper.PAPER.read_text(encoding="utf-8") != text:
        failures.append(f"{paper.PAPER.name} is not the rendering of its template (run python3 -m "
                        "research.release.report.paper --render)")
    doc = json.loads(paper.ANALYSIS.read_text(encoding="utf-8"))
    record = json.loads((REPO / "research" / "release" / f"release_{doc['version']}.json").read_text(encoding="utf-8"))
    files = {f["config"]: f for f in record["files"]}
    for config in ("universe", "features"):
        if doc["sources"][config]["sha256"] != files[config]["sha256"]:
            failures.append(f"analysis.json does not describe the recorded {config} file")
    rows = doc["rows"]
    if rows["all"] != files["universe"]["rows"] or rows["single_token"] != files["features"]["rows"]:
        failures.append("analysis.json's rows are not the record's")
    if sum(rows["by_tier"].values()) != rows["single_token"]:
        failures.append("analysis.json's tiers do not sum to the single-token rows")
    by_id = {e["id"]: e["data"] for e in doc["analyses"]}
    if by_id["S13"]["union_of_all"] != rows["by_tier"]["2+ families"] + rows["by_tier"]["1 family"]:
        failures.append("analysis.json's union of the lists is not its listed tiers")
    return failures


def _literature_failures(page: str, rows: list[dict], calcs) -> list[str]:
    """The pure half of check_literature, separated so that the guard's
    ability to fail is tested directly: every figure the page prints, once
    its citations and code spans are set aside, must be in a confirmed claim
    of a reference that its own sentence cites (or, where the sentence cites
    none, its own paragraph or table row), so that a figure cannot pass on a
    claim about another source (the G4 audit's F13). A year, a version or
    identifier number after a name (release_calcs' rule), and a number after
    "version" or "release" are not figures."""
    import re
    failures = [f"CLAIMS.csv: {r['claim_id']} is {r['status']}, not confirmed"
                for r in rows if r["status"] != "confirmed"]
    by_ref: dict[str, list[str]] = {}
    for r in rows:
        if r["status"] != "confirmed":
            continue
        head = r["source"].split('"')[0]
        for ref in re.findall(r"\[(\d+)\]", head):
            by_ref.setdefault(ref, []).append(r["claim"])
    cite = re.compile(r"\[(\d+(?:,\s*\d+)*)\]")
    figure = re.compile(r"(?<![\w.,/-])(\d{1,3}(?:,\d{3})+|\d+\.\d+%?|\d+%|\d{3,})(?![\w/-])")
    refs_of = lambda text: {n.strip() for m in cite.finditer(text) for n in m.group(1).split(",")}
    body = page.split("\n## References\n")[0]
    blocks = re.split(r"\n\s*\n|\n(?=\|)", body)
    for block in blocks:
        block_refs = refs_of(block)
        # a table row is 1 unit, its cells being no sentences; prose splits
        units = [block] if block.lstrip().startswith("|") else \
            re.split(r"(?<=[.;!?])\s+(?=[A-Z*(\[])", block)
        for sentence in units:
            refs = refs_of(sentence) or block_refs
            plain = re.sub(r"`[^`]*`", "", cite.sub("", sentence))
            for m in figure.finditer(plain):
                n = m.group(1)
                if re.fullmatch(r"(?:19|20)\d\d", n) or re.search(r"(?:version|release) $", plain[:m.start()], re.I):
                    continue
                if re.fullmatch(r"\d+(?:\.\d+)+", n) and calcs._version_or_reference(plain, m.start(1), m.end(1)):
                    continue
                if not refs:
                    failures.append(f"literature.md: the figure {n} has no citation in its sentence or paragraph")
                elif not any(n in claim for ref in refs for claim in by_ref.get(ref, [])):
                    failures.append(f"literature.md: the figure {n} is in no confirmed claim of the "
                                    f"reference(s) its sentence cites ({', '.join(sorted(refs, key=int))})")
    return failures


def check_literature() -> list[str]:
    """The literature page (site/content/research/literature.md), which is
    also the paper's section 2 (D-015 line 3): each figure it prints is in a
    confirmed claim of the claims ledger (research/release/report/CLAIMS.csv)
    of a reference its sentence cites, and every row of the ledger is
    confirmed (`_literature_failures`)."""
    import csv
    from research.release import release_calcs as calcs
    page = REPO.parent / "site" / "content" / "research" / "literature.md"
    ledger = REPO / "research" / "release" / "report" / "CLAIMS.csv"
    missing = [p.name for p in (page, ledger) if not p.exists()]
    if missing:
        return [f"the literature: {', '.join(missing)} missing"]
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    return _literature_failures(page.read_text(encoding="utf-8"), rows, calcs)

CHECKS = (check_inventory_lines, check_charset_counts, check_evidence,
          check_features, check_universe_v2, check_provenance,
          check_release,
          check_public_release, check_release_figures, check_release_report,
          check_feature_leak, check_paper, check_literature)

#: The checks that may defer a part in a clone, which holds no `data/` and
#: no `private/`. Where `data/` exists, no check may defer.
CLONE_DEFERRALS = frozenset({"check_provenance",
                             "check_release", "check_public_release",
                             "check_release_figures", "check_release_report"})


def in_clone() -> bool:
    return not (REPO / "data" / "evidence.parquet").exists()


def run() -> list[str]:
    """Every check, with a raising check reported rather than fatal: a
    check that cannot run is a failure, not a pass."""
    ENVIRONMENT_DEFERRALS.clear()
    failures: list[str] = []
    for check in CHECKS:
        try:
            failures.extend(check())
        except Exception as exc:
            failures.append(
                f"{check.__name__}: raised {type(exc).__name__}: "
                f"{str(exc)[:160]} — a check that cannot run is a "
                f"failure, not a pass")
    failures.extend(_undeclared_environment_deferrals())
    return failures


#: A deferral that comes from the repository's history, not from a missing
#: input, so it is declared wherever it arises: a repository published as
#: 1 new commit cannot hold the commit a release was built from.
HISTORY_DEFERRAL = "check_public_release: this repository's history begins after the build"


def _undeclared_environment_deferrals() -> list[str]:
    declared = CLONE_DEFERRALS if in_clone() else frozenset()
    return [f"undeclared environment deferral: {d} — this environment "
            f"does not declare it, so a check stopped covering "
            f"something without saying so"
            for d in ENVIRONMENT_DEFERRALS
            if d.split(":")[0] not in declared
            and not d.startswith(HISTORY_DEFERRAL)]


def main() -> int:
    failures = run()
    for line in failures:
        print(f"FAIL: {line}")
    for line in ENVIRONMENT_DEFERRALS:
        print(f"deferred: {line}")
    if not failures:
        print(f"verify_doc_numbers: {len(CHECKS)} checks, every quoted "
              f"figure re-derived clean"
              + (f", {len(ENVIRONMENT_DEFERRALS)} part(s) deferred in this "
                 f"clone" if ENVIRONMENT_DEFERRALS else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
