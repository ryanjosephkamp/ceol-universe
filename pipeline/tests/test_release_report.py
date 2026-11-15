"""UP-1, the report skeleton of the CEOL Universe (C-078 line 7;
research/release/report/PACKAGE_UP1.md §5): AT-UP1-1 to AT-UP1-5.

Each test runs the package's own functions on the committed files, and
each guard is shown able to fail on a constructed case whose planted token
is a digit token, never a candidate, since the grammar requires a letter
(C-053's fixture rule; the C-013 wall). Where a scan needs a gitignored
input (the restricted split, the pin's words), that half runs in the
repository environment the census routes, and an absent input fails the
test there; in a fresh clone the scan reads the committed candidate lists
instead, so no test skips in either environment. No word of any list is
printed: the scans count, and a failure names only the count.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import research.verify_doc_numbers as verify
from ceol import grammar as G
from research.archival import HELD, REFERENCE
from research.inthewild.walled_terms import all_terms, canon, find_hits
from research.provenance import build_provenance as BP
from research.release import build_release as B
from research.release import columns as C
from research.release import release_calcs as R
from research.release.report import report_calcs as RC

REPO = Path(__file__).resolve().parents[1]
IN_REPO = (REPO / "data" / "evidence.parquet").exists()
#: the planted token of every scan's own test: digits only, so never a
#: candidate of the grammar
PLANTED = "4815162342"
ANCHOR = "## 1. The mission and the datasets"
#: the records whose example lists the report quotes nothing of (C-081
#: line 8; PACKAGE_UP1.md readings R9 and R17)
EXAMPLE_RECORDS = ("research/census/census.json", "research/audit/audit.json",
                   "research/space_census/space_census.json")
#: the digit-only stand-ins of the example-list test's failure-output probe
#: (C-082 line 1; PACKAGE_UP1.md §10, F1), 2 for each record, built by rule
#: so that no source line a traceback shows spells a stand-in
STAND_INS = {rel: [str(10 ** 11 + 7919 * (2 * i + k)) for k in (1, 2)]
             for i, rel in enumerate(EXAMPLE_RECORDS)}


def _report() -> str:
    return RC.REPORT.read_text(encoding="utf-8")


def _row_values() -> list[str]:
    return list(RC.rows().values()) + list(R.rows().values())


# ---------------------------------------------------------------------------
# The scans of AT-UP1-2 (PACKAGE_UP1.md reading R9)
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    """Every token of `text` that begins and ends with a letter or a digit,
    lower-cased: the restricted scan's units."""
    return {canon(m.group(0)) for m in
            re.finditer(r"[^\W_](?:[\w'’\-]*[^\W_])?", text)}


def _outside_rows(text: str, row_values) -> str:
    values = set(row_values)
    return RC._SPAN.sub(lambda m: " " if m.group(1) in values else m.group(0),
                        text)


def _mention_spans(text: str, row_values) -> set[str]:
    """The backticked spans that are not rows and whose content reads as a
    word (letters, digits, apostrophes, hyphens, and spaces, no underscore,
    beginning with a letter or a digit): where a report could name a
    candidate."""
    values = set(row_values)
    return {canon(span) for span in RC._SPAN.findall(text)
            if span not in values and re.fullmatch(r"[^\W_][\w' \-]*", span)
            and "_" not in span}


def _letters_outside_az(text: str, row_values) -> int:
    """The count of letters outside a-z (in either case) that the text
    carries outside its rows."""
    return sum(1 for ch in _outside_rows(text, row_values)
               if ch.isalpha() and not ("a" <= ch.lower() <= "z"))


def _identifiers() -> set[str]:
    """The names the report may backtick, each declared in code: the
    columns, the configs, the panel sets, the census sources, the classes,
    and the provenance vocabularies."""
    census = json.loads((REFERENCE / "research" / "census" / "census.json")
                        .read_text(encoding="utf-8"))
    names = (set(C.UNIVERSE_COLUMNS) | set(C.FEATURES_COLUMNS)
             | set(C.PANEL_SETS) | {"universe", "features"}
             | {name for name, _predicate in B.FILTER_CONFIGS}
             | set(G.CENSUS_CLASSES) | {"spaced", "s-final", "plain"}
             | set(census["sources"]) | set(BP.CLASSES) | set(BP.KINDS))
    return {canon(n) for n in names}


def _members(tokens: set[str], words: set[str] | None = None) -> int:
    """How many of `tokens` are words: of `words` when given (a stand-in),
    else of the pin in the repository environment and of the committed
    candidate lists in a clone. The words themselves never leave here."""
    if not tokens:
        return 0
    if words is not None:
        return len(tokens & words)
    if IN_REPO:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        pin = REPO / "data" / "universe_v2.parquet"
        assert pin.exists(), "the pin is absent where data/ exists"
        column = pq.read_table(pin, columns=["word"])["word"]
        mask = pc.is_in(column, value_set=pa.array(sorted(tokens)))
        return int(pc.sum(mask).as_py() or 0)
    found: set[str] = set()
    for rel in ("research/census/candidates.csv",
                "research/audit/universe_miss_candidates.csv"):
        with (HELD / rel).open(encoding="utf-8", newline="") as f:
            found |= {r["word"] for r in csv.DictReader(f)
                      if r["word"] in tokens}
    return len(found)


def _a_listed_word() -> str:
    """A word of the list `_members` reads, never printed: the first row of
    the pin (the repository environment) or of the census list (a clone)."""
    if IN_REPO:
        import pyarrow.parquet as pq
        table = pq.read_table(REPO / "data" / "universe_v2.parquet",
                              columns=["word"])
        return table["word"][0].as_py()
    with (HELD / "research" / "census" / "candidates.csv").open(
            encoding="utf-8", newline="") as f:
        return next(csv.DictReader(f))["word"]


def _example_strings() -> dict[str, set[str]]:
    """By record, every string of a list of strings with a key on its path
    that names examples or the longest entries (reading R17). The strings
    never leave here."""
    out: dict[str, set[str]] = {}

    def walk(node, path: tuple, found: set) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, path + (str(key),), found)
        elif isinstance(node, list):
            if node and all(isinstance(x, str) for x in node):
                if any(re.search(r"example|longest", k) for k in path):
                    found.update(x for x in node if x.split())
            else:
                for x in node:
                    walk(x, path, found)

    for rel in EXAMPLE_RECORDS:
        out[rel] = set()
        walk(json.loads((HELD / rel).read_text(encoding="utf-8")), (),
             out[rel])
    return out


def _example_hits(text: str, strings) -> list[int]:
    """The line of each occurrence in `text` of a string of `strings` as a
    whole word or phrase, both lowercased (lower(), never casefold(): the
    CEOL lowercases and never case-folds), a run of whitespace
    matching a space: lines only, never a string."""
    low = text.lower()
    lines: list[int] = []
    for s in strings:
        pattern = (r"(?<![\w'’\-])" + r"\s+".join(map(re.escape,
                                                      s.lower().split()))
                   + r"(?![\w'’\-])")
        lines += [low.count("\n", 0, m.start()) + 1
                  for m in re.finditer(pattern, low)]
    return sorted(lines)


def _example_failures(strings, read=None) -> list[str]:
    """The example-list scan's file loop (C-081 line 8): for the report and
    for its template, a failure naming the file, the count, and the lines of
    the occurrences of `strings`; `read` gives a file's text, the committed
    file's when not given. File names, counts, and lines only, never a
    string."""
    read = read or (lambda path: path.read_text(encoding="utf-8"))
    failures = []
    for path in (RC.REPORT, RC.TEMPLATE):
        lines = _example_hits(read(path), strings)
        if lines:
            failures.append(f"{len(lines)} example string(s) of a record in "
                            f"{path.name}, at lines {lines}")
    return failures


#: the failure-output probe's module (C-082 line 1; PACKAGE_UP1.md §10, F1):
#: pytest runs it in a subprocess, where the example-list test's own
#: assertions are rewritten as in the suite, over the stand-ins written
#: beside it; each of its 3 tests drives the example-list test into a
#: failing path: a record emptied; the matcher forced to find nothing (an
#: empty list); the matcher forced to return no value, which pytest
#: explains with the arguments of the call that gave it, where a list
#: compared with a list is explained by its diff alone
_PROBE_MODULE = '''\
import json
import sys
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name("probe.json").read_text())
sys.path.insert(0, CONFIG["tests"])

import test_release_report as T  # noqa: E402


def _stand_ins(emptied=None):
    return {rel: set() if rel == emptied else set(strings)
            for rel, strings in CONFIG["stand_ins"].items()}


def test_a_record_emptied(monkeypatch, tmp_path):
    monkeypatch.setattr(T, "_example_strings",
                        lambda: _stand_ins(T.EXAMPLE_RECORDS[0]))
    monkeypatch.setattr(T, "_probe_output", lambda path: "")
    T.test_at_up1_2_no_example_string_of_a_record_is_in_the_report(tmp_path)


def test_the_matcher_forced_to_find_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(T, "_example_strings", _stand_ins)
    monkeypatch.setattr(T, "_example_hits", lambda text, strings: [])
    monkeypatch.setattr(T, "_probe_output", lambda path: "")
    T.test_at_up1_2_no_example_string_of_a_record_is_in_the_report(tmp_path)


def test_the_matcher_forced_to_return_no_value(monkeypatch, tmp_path):
    monkeypatch.setattr(T, "_example_strings", _stand_ins)
    monkeypatch.setattr(T, "_example_hits", lambda text, strings: None)
    monkeypatch.setattr(T, "_probe_output", lambda path: "")
    T.test_at_up1_2_no_example_string_of_a_record_is_in_the_report(tmp_path)
'''


def _probe_output(path: Path) -> str:
    """The whole output of pytest run in a subprocess under the repository's
    pytest.ini over the probe module written to `path`, the stand-ins in a
    file beside it (C-082 line 1; PACKAGE_UP1.md §10, F1). The child runs
    at -vv, which turns off pytest's truncation of a long assertion
    explanation, so that the output holds every line an explanation can
    print. It keeps its temporary files under `path` and writes no cache
    and no bytecode, and an inherited PYTEST_ADDOPTS is dropped, as the
    stop condition drops it, so that no option of the parent's run (a JUnit
    report's path among them) reaches the child."""
    (path / "probe.json").write_text(json.dumps(
        {"tests": str(REPO / "tests"), "stand_ins": STAND_INS}),
        encoding="utf-8")
    module = path / "test_example_probe.py"
    module.write_text(_PROBE_MODULE, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-vv", "-rf",
         "-p", "no:cacheprovider",
         "-c", str(REPO / "pytest.ini"), "--rootdir", str(REPO),
         "--basetemp", str(path / "basetemp"), str(module)],
        cwd=REPO, env=dict(env, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=300)
    return run.stdout + run.stderr


def _planted(inputs: dict, sentence: str) -> str:
    """The template with `sentence` planted after the mission's heading."""
    assert ANCHOR in inputs["template"]
    return inputs["template"].replace(ANCHOR, f"{ANCHOR}\n\n{sentence}", 1)


def _synchronized(inputs: dict, template: str | None = None,
                  report_rows: dict | None = None) -> list[str]:
    """The whole pure check over a mutated template or mutated rows, the
    report re-rendered from them so that the rendering clause holds and
    only the guards can fail (C-081 line 11; PACKAGE_UP1.md §9)."""
    template = inputs["template"] if template is None else template
    rows = inputs["report_rows"] if report_rows is None else report_rows
    report = RC.render(template, rows, inputs["release_rows"])
    return verify._release_report_failures(**dict(
        inputs, template=template, report=report, report_rows=rows))


def _restricted() -> set[str] | None:
    """The restricted split in the repository environment; None in a
    clone, which does not hold it."""
    if not IN_REPO:
        return None
    path = REPO / ".cache" / "audit" / "universe_miss_restricted.csv"
    assert path.exists(), "the restricted split is absent where data/ exists"
    with path.open(encoding="utf-8", newline="") as f:
        return {r["word"] for r in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

def test_at_up1_1_every_backticked_figure_is_a_calculator_row():
    """AT-UP1-1: every backticked span that carries a figure is a row of
    report_calcs.py or release_calcs.py, and no figure stands outside a
    row; a planted comma-grouped count, an all-digit run, a small count, a
    backticked figure that is no row, and a number word are each caught,
    and an identifier is not a figure."""
    report, values = _report(), _row_values()
    figure_spans = [s for s in RC._SPAN.findall(report)
                    if RC.stray_figures(f"`{s}`")]
    assert figure_spans, "no backticked figure found: the scan is broken"
    assert [s for s in figure_spans if s not in values] == []
    assert RC.stray_figures(report, values) == []
    assert ANCHOR in report
    for planted, figure in (
            ("A planted 4,321,987 candidates.", "4,321,987"),
            ("The count is 7654321 rows.", "7654321"),
            ("The panel has 12 sets.", "12"),
            ("A span `2048 rows` that is no row.", "2048"),
            ("The panel has two sets.", "two")):
        mutated = report.replace(ANCHOR, f"{ANCHOR}\n\n{planted}")
        assert figure in RC.stray_figures(mutated, values), (
            f"the planted figure {figure} was not caught")
    for exempt in ("C-016 line 4, §4.1, 2026-09-26, U+0020, sha256, v2.0",
                   "WordNet 3.0 (1934), since 2006, the 2020 release"):
        mutated = report.replace(ANCHOR, f"{ANCHOR}\n\n{exempt}.")
        assert RC.stray_figures(mutated, values) == []


def test_at_up1_1_a_synchronized_figure_fails_the_whole_check():
    """AT-UP1-1, the fix package (C-081 line 11; PACKAGE_UP1.md §9, F1):
    with the template mutated and the report re-rendered from it, a
    comma-grouped count after an item word and a number of 4 digits after
    an item word each make the whole pure check fail, in the template's
    clause and the report's, the rendering clause holding."""
    inputs = verify._release_report_inputs()
    assert _synchronized(inputs) == []
    for planted, figure in (
            ("The items 4,321,987 of the pin were read.", "4,321,987"),
            ("The count stands after line 4815 of the record.", "4815")):
        failures = _synchronized(inputs, template=_planted(inputs, planted))
        assert not any("not the rendering" in f for f in failures)
        assert any(f.startswith("REPORT.template.md carries") and figure in f
                   for f in failures), f"{figure} passed the template clause"
        assert any(f.startswith("REPORT.md carries") and figure in f
                   for f in failures), f"{figure} passed the report clause"


def test_at_up1_1_the_declared_exemptions_hold_through_the_whole_check():
    """AT-UP1-1, the fix package (C-081 line 11; PACKAGE_UP1.md §3, §9,
    reading R15): the declared exemptions hold through the synchronized
    check (a line reference, a cited year, a codepoint, a version, a hash,
    a path, a citation key, an item number of 3 digits), and so do the
    forms the declared patterns keep, which the prose audit of every
    re-render reads and the guard does not catch: a year-like count
    directly after a capitalized word, a slash ratio, and a letter-initial
    token that carries a digit. A narrowing of those patterns is the
    owner's to rule, and this test changes with it."""
    inputs = verify._release_report_inputs()
    key = RC.cited_keys(inputs["report"])[0]
    exempt = (f"C-081 line 11, (1934), U+0020, v2.0, sha256 4a8cb3ad, "
              f"research/release/report/REPORT.md, a claim [@{key}], and "
              f"line 175.")
    assert _synchronized(inputs, template=_planted(inputs, exempt)) == []
    for kept, pattern in (
            ("Of 1985 rows, some were read.", "the author and year"),
            ("The share is 10/12 of the rows.", "the path"),
            ("A count of x2 rows.", "the name")):
        mutated = _planted(inputs, kept)
        assert RC.stray_figures(mutated) == [], f"{pattern} pattern"
        assert _synchronized(inputs, template=mutated) == [], (
            f"{pattern} pattern")


def test_at_up1_2_the_report_names_no_candidate_restricted_or_walled_word():
    """AT-UP1-2 (reading R9): no walled term; no restricted word (the
    repository environment); no candidate word in a mention context and no
    letter outside a-z outside the rows; the planted digit token found by
    each scan's own test."""
    report, values = _report(), _row_values()
    planted_text = f"{report}\nA planted `{PLANTED}` token.\n"

    # the walled lists
    assert find_hits(report, all_terms()) == set(), (
        "a walled term is in REPORT.md")
    assert find_hits(planted_text, {PLANTED}) == {PLANTED}

    # the restricted split
    assert _tokens(planted_text) & {PLANTED} == {PLANTED}
    restricted = _restricted()
    if restricted is not None:
        pin = json.loads((REPO / "research" / "universe_v2" /
                          "universe_v2.json").read_text(encoding="utf-8"))
        assert len(restricted) == pin["counts"]["restricted_rows"]
        hits = len(_tokens(report) & restricted)
        assert hits == 0, f"{hits} restricted word(s) in REPORT.md"

    # the mention contexts
    names = _identifiers()
    mentions = _mention_spans(report, values) - names
    planted = _mention_spans(planted_text, values) - names
    assert PLANTED in planted and PLANTED not in mentions
    assert _members(planted, {PLANTED}) == 1
    lookup_works = _members({canon(_a_listed_word())}) == 1
    assert lookup_works, "the membership lookup found no listed word"
    named = _members(mentions)
    assert named == 0, f"{named} candidate word(s) named in REPORT.md"
    assert _letters_outside_az(report, values) == 0, (
        "a letter outside a-z stands outside the rows of REPORT.md")
    assert _letters_outside_az(planted_text + "\u00f8", values) == 1


def test_at_up1_2_no_example_string_of_a_record_is_in_the_report(tmp_path):
    """AT-UP1-2, the fix packages (C-081 line 8, C-082 line 1;
    PACKAGE_UP1.md readings R9 and R17, §9 and §10): no example string of
    census.json, audit.json, or space_census.json appears in the report or
    its template, ordinary use included, as a whole word or phrase, matched
    lowercase (lower(), never casefold()), a run of whitespace
    matching a space; planted digit tokens added to the lists are found at
    their lines, a phrase wrapped across a line break among them, and a
    token planted in the template alone, the report clean, fails the scan's
    own file loop (F2). Every assertion reads a value computed first, the
    records that gave no string, lines, or a count, and a failure-output
    probe drives the failing paths under pytest's assertion rewriting with
    digit-only stand-ins and finds none of them in the output (F1): a
    failure names counts, record names, and lines only."""
    by_record = _example_strings()
    empty = [rel for rel, found in by_record.items() if not found]
    assert empty == [], f"{len(empty)} record(s) gave no example string"
    strings = set().union(*by_record.values())
    failures = _example_failures(strings)
    assert failures == []

    # planted digit tokens in the report, a wrapped phrase among them
    report = _report()
    wrapped = "4815 162342"
    planted = (f"{report}\nA planted {PLANTED} token.\n"
               f"A planted 4815\n162342 phrase.\n")
    first = planted.count("\n", 0, planted.index(PLANTED)) + 1
    lines = [_example_hits(planted, strings),
             _example_hits(planted, strings | {PLANTED, wrapped})]
    assert lines == [[], [first, first + 1]], "the planted tokens, by line"

    # a digit token planted in the template alone, the report clean, fails
    # the scan's own file loop (F2)
    template = f"{RC.TEMPLATE.read_text(encoding='utf-8')}\n{PLANTED}\n"
    line = template.count("\n", 0, template.index(PLANTED)) + 1
    texts = {RC.REPORT: report, RC.TEMPLATE: template}
    failures = _example_failures(strings | {PLANTED}, texts.__getitem__)
    assert failures == [f"1 example string(s) of a record in "
                        f"{RC.TEMPLATE.name}, at lines [{line}]"]

    # the matcher lowercases both sides and never case-folds (F3): U+00DF
    # lowercases to itself and case-folds to a doubled letter
    sharp = "\u00df4815"
    assert sharp.lower() == sharp != sharp.casefold()
    lines = [_example_hits(text, {s}) for text, s in (
        ("A planted X4815 token.", "x4815"),
        ("A planted x4815 token.", "X4815"),
        (f"A planted {sharp.casefold().upper()} token.", sharp))]
    assert lines == [[1], [1], []], "the matcher's normalization"

    # the failure-output probe (F1): no stand-in in the failure text, the 3
    # failing paths reached, and the assertion rewritten (a plain assertion
    # prints its message alone)
    output = _probe_output(tmp_path)
    leaked = sum(output.count(s) for stand_ins in STAND_INS.values()
                 for s in stand_ins)
    assert leaked == 0, f"{leaked} stand-in(s) in the failure output"
    explained = [bool(re.search(rf"^E +assert \[{value}, {value}\] == ",
                                output, re.M))
                 for value in (r"\[\]", "None")]
    reached = [re.findall(r"\b(\d+) failed\b", output),
               "record(s) gave no example string" in output,
               "the planted tokens, by line" in output, *explained]
    assert reached == [["3"], True, True, True, True], (
        "the probe's failing paths")


def test_at_up1_3_every_cited_reference_is_a_manifest_row():
    """AT-UP1-3: every citation key of the report is a row of
    references/MANIFEST.csv (or, once committed, of the literature pass's
    delivered bibliography), and REFERENCES.md is the rendering of the
    cited keys; an unknown key is caught."""
    report = _report()
    keys = RC.cited_keys(report)
    assert keys, "the report cites nothing: the reader is broken"
    manifest, delivered = RC.manifest_rows(), RC.delivered_entries()
    assert RC.unresolved_keys(keys, manifest, delivered) == []
    references = RC.REFERENCES.read_text(encoding="utf-8")
    assert references == RC.render_references(keys, manifest, delivered)
    for key in keys:
        assert manifest[key]["sha256"] in references
    unknown = "nosuch9999_reference"
    assert RC.unresolved_keys(keys + [unknown], manifest, delivered) == [
        unknown]
    failures = verify._release_report_failures(**dict(
        verify._release_report_inputs(),
        report=report.replace(ANCHOR, f"{ANCHOR}\n\nA claim [@{unknown}].")))
    assert any(unknown in f for f in failures)


def test_at_up1_4_the_version_marker_is_the_release_records_version():
    """AT-UP1-4: the report's version marker equals the release record's
    version, read independently of the calculator, and every version a row
    names is the record's; a changed marker is caught."""
    report = _report()
    record = json.loads(R.RECORD.read_text(encoding="utf-8"))
    marker = re.search(r"^\*\*The version of the figures:\*\* `([^`]+)`",
                       report, re.M)
    assert marker and marker.group(1) == record["version"]
    assert RC.version_markers(report) == [record["version"]]
    assert RC.row_versions(_row_values()) == {record["version"]}
    inputs = verify._release_report_inputs()
    first = inputs["report"].index(f"`{record['version']}`")
    assert first == marker.start(1) - 1
    inputs["report"] = inputs["report"].replace(
        f"`{record['version']}`", "`v9.9`", 1)
    failures = verify._release_report_failures(**inputs)
    assert any("version marker" in f for f in failures)


def test_at_up1_4_a_three_part_version_in_a_row_fails_the_whole_check():
    """AT-UP1-4, the fix package (C-081 line 11; PACKAGE_UP1.md §9, F2 and
    reading R16): the marker and the row clause read 1 version grammar; a
    row given a version of 3 parts, with the report re-rendered from the
    rows, fails the version clause; a version that closes a sentence in a
    row is found, and a pin's name of a single part is not a version."""
    assert f"({RC.VERSION})" in RC.MARKER.pattern
    assert RC.VERSION in RC._VERSION.pattern
    inputs = verify._release_report_inputs()
    version = inputs["record_version"]
    assert re.fullmatch(RC.VERSION, version)
    rows = dict(inputs["report_rows"])
    rows["software"] = f"{rows['software']}, the writer v9.9.1"
    failures = _synchronized(inputs, report_rows=rows)
    assert not any("not the rendering" in f for f in failures)
    assert any(f.startswith("rows name versions other than the release "
                            "record's") and "v9.9.1" in f for f in failures)
    assert RC.row_versions([f"the rows of {version}."]) == {version}
    assert RC.row_versions(["the v1 universe and the v3 pin"]) == set()


def test_at_up1_5_the_check_can_fail_on_a_changed_row(monkeypatch):
    """AT-UP1-5: the check passes on the committed files and fails when a
    report row's value is altered, a release row's value is altered, a row
    is left unquoted, a figure is planted in the template, or a required
    artifact is absent; its required artifacts are the calculator's
    records."""
    assert verify.check_release_report() == []
    # an archival record is under ../reference/; the audit's Markdown record
    # is held and the check defers where it is absent
    assert set(verify.REQUIRED_ARTIFACTS["check_release_report"]) == {
        Path(os.path.relpath(p, REPO)).as_posix() for p in RC.RECORDS
        if not p.is_relative_to(HELD)}
    assert [p for p in RC.RECORDS if p.is_relative_to(HELD)] == [RC.AUDIT_MD]
    inputs = verify._release_report_inputs()
    assert verify._release_report_failures(**inputs) == []

    def digit_bumped(value: str) -> str:
        i = next(i for i, ch in enumerate(value) if ch.isdigit())
        return value[:i] + str((int(value[i]) + 1) % 10) + value[i + 1:]

    rows = dict(inputs["report_rows"])
    rows["census_classes"] = digit_bumped(rows["census_classes"])
    failures = verify._release_report_failures(**dict(inputs,
                                                      report_rows=rows))
    assert any("not the rendering" in f for f in failures)
    assert any("census_classes" in f for f in failures)

    release = dict(inputs["release_rows"])
    release["rows_universe"] = digit_bumped(release["rows_universe"])
    failures = verify._release_report_failures(**dict(inputs,
                                                      release_rows=release))
    assert any("not the rendering" in f for f in failures)

    unquoted = inputs["template"].replace("{{identifier}}", "the identifier",
                                          1)
    failures = verify._release_report_failures(**dict(inputs,
                                                      template=unquoted))
    assert any("does not quote" in f for f in failures)

    planted = inputs["template"].replace(
        ANCHOR, f"{ANCHOR}\n\nA planted 4,321,987 rows.", 1)
    failures = verify._release_report_failures(**dict(inputs,
                                                      template=planted))
    assert any("4,321,987" in f for f in failures)

    required = verify.REQUIRED_ARTIFACTS["check_release_report"]
    monkeypatch.setitem(verify.REQUIRED_ARTIFACTS, "check_release_report",
                        required + ("research/release/report/ABSENT.md",))
    assert verify.check_release_report() != []
