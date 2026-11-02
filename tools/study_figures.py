#!/usr/bin/env python3
"""The figures of the proposed study's pages (site/content/study/), printed
by the study's own calculator in the archive.

    python3 tools/study_figures.py            write site/content/study/figures.json
    python3 tools/study_figures.py --check    compare with it

The study was designed in a private archive repository (`ARCHIVE` below),
which is read-only here. This script exports the archive's committed tree at
the commit the study export names (`private/study-export/MANIFEST.csv`) into
a temporary folder, runs the overview's calculator
(`research/inthewild/study_overview_calcs.py`, every row read from the
archive's committed records) in a separate interpreter there, and lifts each
figure the pages quote out of its row by an anchored pattern. A row that
changes so that a pattern no longer matches stops the script. The figures are
counts, shares, sizes, and the definition's parameters; no study item, label,
or verdict is read or written, and no string of the universe.

In a clone without the archive the committed file stands, and the check says
so.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = Path(os.environ.get("CEOL_ARCHIVE", REPO / ".inputs" / "archive"))
COMMIT = "5faa780b3c9f6f9d7933a8bff60add4163234d90"
CALCULATOR = "research/inthewild/study_overview_calcs.py"
OUT = REPO / "site" / "content" / "study" / "figures.json"

#: (id, the start of the row, the pattern; its first group is the figure)
FIGURES: tuple[tuple[str, str, str], ...] = (
    ("frame_rows", "the study frame", r"\): ([\d,]+) rows;"),
    ("frame_restricted", "the study frame", r"rows; ([\d,]+) restricted rows outside every pool"),
    ("frame_plain", "the study frame", r"plain single-token ([\d,]+), of which"),
    ("frame_plain_unlisted", "the study frame", r"of which ([\d,]+) are listed by none of the"),
    ("detector_sets", "the study frame", r"none of the (\d+) derived detector sets"),
    ("development_in_frame", "the study frame", r"the development ledger [\d,]+ rows, ([\d,]+) in the frame"),
    ("study_frame", "the study frame", r"\(d\) ([\d,]+) rows over"),
    ("partition_strata", "the study frame", r"rows over (\d+) partition strata"),
    ("s_final", "the study frame", r"apostrophe class of ([\d,]+) outside study 1"),
    ("probe_batteries", "the probe batteries", r"\): (\d+) batteries"),
    ("probe_words", "the probe batteries", r"; (\d+) distinct named words"),
    ("pool_single", "development pool proposal", r"proposal: (\d+) single-token"),
    ("pool_spaced", "development pool proposal", r"\+ (\d+) spaced ="),
    ("pool_total", "development pool proposal", r"= (\d+) stratified candidates over"),
    ("strata", "development pool proposal", r"candidates over (\d+) strata"),
    ("pseudo", "development pool proposal", r"\+ (\d+) screened pseudoword controls"),
    ("pseudo_single", "development pool proposal", r"controls \((\d+) single-token"),
    ("pseudo_spaced", "development pool proposal", r"single-token, (\d+) spaced\)"),
    ("known_in_use", "development pool proposal", r"\+ (\d+) panel-absent real-word controls"),
    ("repeats", "development pool proposal", r"\+ (\d+) intra-rater repeats"),
    ("presentations", "development pool proposal", r"repeats = (\d+);"),
    ("rater_low", "development pool proposal", r"sub-sample: (\d+)–\d+ items"),
    ("rater_high", "development pool proposal", r"sub-sample: \d+–(\d+) items"),
    ("pool_known_a", "panel-absent pool arithmetic", r"pool (\d+) A \+"),
    ("pool_known_b", "panel-absent pool arithmetic", r"A \+ (\d+) B;"),
    ("cp_upper_60", "CP95 0/60", r"\[0\.0%, ([\d.]+%)\]"),
    ("power_60_5pct", "P(at least one event in n=60 | true rate 5%)", r"= ([\d.]+%)$"),
    ("pilot_words", "the pilot's outcome", r"Measurement A — (\d+) of \d+ words"),
    ("pilot_attained", "the pilot's outcome", r"words, (\d+) attain k = 3"),
    ("pilot_attained_pct", "the pilot's outcome", r"attain k = 3 on C_min \(([\d.]+%)\)"),
    ("pilot_queries_short", "the pilot's outcome", r"(\d+) of \d+ queries exhausted"),
    ("pilot_queries", "the pilot's outcome", r"\d+ of (\d+) queries exhausted"),
    ("pilot_depth", "the pilot's outcome", r"below R_pilot = (\d+)"),
    ("pilot_rows", "the pilot's outcome", r"(\d+) ledger rows"),
    ("pilot_attestations", "the pilot's outcome", r"(\d+) attestations;"),
    ("pilot_median", "the pilot's outcome", r"median C_min\(10\) = (\d+)"),
    ("pilot_topics", "the pilot's outcome", r"Measurement B — (\d+) of \d+ topics"),
    ("pilot_pages", "the pilot's outcome", r"(\d+) pages captured"),
    ("pilot_pairs_considered", "the pilot's outcome", r"(\d+) candidate pairs considered"),
    ("pilot_pairs_qualified", "the pilot's outcome", r"(\d+) pairs qualified against"),
    ("pilot_pairs_target", "the pilot's outcome", r"against the (\d+)-pair target"),
    ("pilot_resolver_attempts", "the pilot's outcome", r"resolver (\d+) attempts"),
    ("pilot_resolver_results", "the pilot's outcome", r"(\d+) results returned"),
    ("pilot_hours", "the pilot's outcome", r"wall clock ([\d.]+) h"),
    ("pilot_bound", "the pilot's outcome", r"of the (\d+) h bound"),
    ("pilot_retrieved", "the pilot's pre-attestation exclusion", r"fetches, (\d+) retrieved"),
    ("pilot_charset_excluded", "the pilot's pre-attestation exclusion", r"(\d+) excluded for want"),
    ("pilot_not_retrieved", "the pilot's pre-attestation exclusion", r"(\d+) not retrieved"),
    ("pilot_charset_pct", "the pilot's pre-attestation exclusion", r"of retrieved \(([\d.]+%)\)"),
    ("e_sources", "the exclusion set E", r"\): (\d+) pinned manifest sources"),
    ("e_sets", "the exclusion set E", r"(\d+) derived detector sets \(L2\)"),
    ("e_hosting", "the exclusion set E", r"(\d+) per-source hosting entries"),
    ("e_hosting_sources", "the exclusion set E", r"entries \(L3\) over (\d+) sources"),
    ("mirror_words", "the mirror measurement", r"\): (\d+) panel-listed words"),
    ("mirror_results", "the mirror measurement", r"words, (\d+) results"),
    ("mirror_derived", "the mirror measurement", r"panel-derived (\d+) \("),
    ("mirror_derived_pct", "the mirror measurement", r"panel-derived \d+ \(([\d.]+%)"),
    ("mirror_top", "the mirror measurement", r"panel-derived for (\d+) of \d+ words"),
    ("classes_k", "the ruled parameter slate", r"needs k = (\d+) independence classes"),
    ("span_days", "the ruled parameter slate", r"span t = (\d+) days"),
    ("r_max", "the ruled parameter slate", r"R_max = (\d+)"),
    ("l_incumbent", "the ruled parameter slate", r"L = (\d+) the incumbent"),
    ("l_low", "the ruled parameter slate", r"swept (\d+)\.\.\d+"),
    ("l_high", "the ruled parameter slate", r"swept \d+\.\.(\d+)"),
    ("window_days", "the ruled parameter slate", r"corroboration window (\d+) days"),
    ("queries_per_candidate", "the ruled parameter slate", r"(\d+) queries per candidate"),
    ("channels", "the ruled parameter slate", r"on (\d+) mandatory channels"),
    ("model_repeats", "the ruled parameter slate", r"repeated at least (\d+) times"),
)

#: the figures the script computes from the calculator's own functions
RUNNER = r"""
import json, sys
from research.inthewild import study_overview_calcs as S
from research.inthewild import pilot_design_calcs as P
lo, hi = P.clopper_pearson(int(sys.argv[1]), int(sys.argv[2]))
print(json.dumps({"rows": S.rows(), "attained_interval": [lo, hi]}))
"""


def _export(where: Path) -> None:
    if not (ARCHIVE / ".git").exists():
        raise SystemExit(f"[study] the archive is not at {ARCHIVE}")
    proc = subprocess.run(["git", "-C", str(ARCHIVE), "archive", COMMIT], check=True, capture_output=True)
    tar = where / "archive.tar"
    tar.write_bytes(proc.stdout)
    with tarfile.open(tar) as t:
        t.extractall(where / "tree", filter="data")


def _run(tree: Path, attained: int, words: int) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    proc = subprocess.run([sys.executable, "-B", "-c", RUNNER, str(attained), str(words)], cwd=tree,
                          env=env, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def _value(text: str):
    plain = text.replace(",", "")
    if plain.endswith("%"):
        return {"value": float(plain[:-1]) / 100, "text": text}
    if re.fullmatch(r"\d+", plain):
        return {"value": int(plain), "text": f"{int(plain):,}"}
    return {"value": float(plain), "text": text}


def compute() -> dict:
    with tempfile.TemporaryDirectory(prefix="ceol-study-") as tmp:
        tmp = Path(tmp)
        _export(tmp)
        first = _run(tmp / "tree", 0, 1)
        rows = first["rows"]
        out = []
        found: dict[str, dict] = {}
        for fid, start, pattern in FIGURES:
            row = next((r for r in rows if r.startswith(start)), None)
            if row is None:
                raise SystemExit(f"[study] no row of the calculator starts with {start!r}")
            m = re.search(pattern, row)
            if not m:
                raise SystemExit(f"[study] {fid}: the pattern does not match its row")
            v = _value(m.group(1))
            found[fid] = v
            out.append({"id": fid, **v, "row": start})
        ci = _run(tmp / "tree", found["pilot_attained"]["value"], found["pilot_words"]["value"])["attained_interval"]
    for fid, x in (("pilot_attained_low", ci[0]), ("pilot_attained_high", ci[1])):
        out.append({"id": fid, "value": round(x, 6), "text": f"{100 * x:.1f}%",
                    "row": "pilot_design_calcs.clopper_pearson over pilot_attained of pilot_words"})
    known = found["pool_known_a"]["value"] + found["pool_known_b"]["value"]
    out.append({"id": "pool_known", "value": known, "text": f"{known:,}", "row": "pool_known_a + pool_known_b"})
    return {
        "generated_by": "tools/study_figures.py",
        "what": "the figures of the proposed study's pages, each lifted from a row of the study's calculator",
        "archive": "common-english-openlist (private, read-only)",
        "commit": COMMIT,
        "calculator": CALCULATOR,
        "figures": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if not (ARCHIVE / ".git").exists():
        print(f"[study] the archive is absent here; {OUT.relative_to(REPO)} stands as committed (a declared deferral)")
        return 0
    doc = compute()
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    rel = OUT.relative_to(REPO)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"[study] {rel} does not re-derive", file=sys.stderr)
            return 1
        print(f"[study] {rel} re-derives")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"[study] {rel} written: {len(doc['figures'])} figures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
