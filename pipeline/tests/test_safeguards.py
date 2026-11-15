"""The local safeguards (PLAN.md §2, rules 2 and 7): the 2 matchers, the
scan's readers, the scan over a push, and the exemptions.

Every test but the last 3 runs on stand-ins built here, so that it runs in a
clone that holds no private list. A stand-in is assembled from pieces at run
time, so that this file never spells one whole. The last 3 tests read the
real lists and are skipped where `private/` is absent.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess

import pytest

from safeguards import exemptions, locations, restricted, scan, wall

#: stand-ins for walled terms: a plain token, a hyphenated token, a token
#: with a leading apostrophe, a phrase, and a token that starts with a digit
PLAIN = "zq" + "vex"
HYPHEN = "zq" + "-" + "vox"
LEADING = "'" + "zqv"
PHRASE = "zqa" + " " + "zqb"
DIGIT = "7" + "zqd"
TERMS = {PLAIN, HYPHEN, LEADING, PHRASE, DIGIT}

#: stand-ins for restricted words
WORDS = {"zq" + "wab", "zq" + "wob"}

TEXTS = [
    f"a line with {PLAIN} in it",
    f"{PLAIN}",
    f"x{PLAIN}",                       # inside a longer word: no hit
    f"{PLAIN}y",
    f"({PLAIN})",
    f"{PLAIN}'s and {PLAIN}-like and {PLAIN}_x and {PLAIN}9",
    f"A LINE WITH {PLAIN.upper()}",
    f"{HYPHEN} and x{HYPHEN} and {HYPHEN}y",
    f"quoted \"{LEADING}\" and she{LEADING}",
    f"{PHRASE}",
    f"{PHRASE.replace(' ', '   ')}",
    f"{PHRASE.replace(' ', chr(10))}",  # a phrase across a line break
    f"{PHRASE.replace(' ', '-')}",      # a hyphen is not whitespace: no hit
    f"{DIGIT} and x{DIGIT} and 1{DIGIT}",
    "nothing here",
    "",
]


def test_the_matcher_returns_what_the_archive_matcher_returns():
    matcher = wall.Matcher(TERMS)
    for text in TEXTS:
        assert matcher.hits(text) == wall.find_hits(text, TERMS)
    assert matcher.hits("\n".join(TEXTS)) == wall.find_hits("\n".join(TEXTS), TERMS) == TERMS
    # the cases, stated: a letter directly before or after blocks a match;
    # an apostrophe, a hyphen, an underscore, or a digit does not
    assert matcher.hits(f"x{PLAIN}") == set() and matcher.hits(f"{PLAIN}y") == set()
    assert matcher.hits(f"{PLAIN}'s") == {PLAIN} and matcher.hits(f"{PLAIN}_x") == {PLAIN}
    assert matcher.hits(f"she{LEADING}") == set()
    assert matcher.hits(PHRASE.replace(" ", "\n")) == {PHRASE}
    assert matcher.hits(PHRASE.replace(" ", "-")) == set()


def test_the_matcher_names_lines_and_never_terms():
    matcher = wall.Matcher(TERMS)
    text = f"first\nsecond {PLAIN}\nthird\nfourth {PHRASE}\n"
    assert matcher.hit_lines(text) == [2, 4]


def test_redaction_leaves_no_term_and_keeps_the_rest():
    text = f"Keep THIS. Drop {PLAIN.upper()} and {PHRASE}. Keep x{PLAIN}."
    out, count = wall.redact(text, TERMS)
    assert count == 2 and wall.find_hits(out, TERMS) == set()
    assert out == f"Keep THIS. Drop {wall.PLACEHOLDER} and {wall.PLACEHOLDER}. Keep x{PLAIN}."
    distinct, _n = wall.redact(f"{PLAIN} {PLAIN} {HYPHEN}", TERMS, distinct=True)
    labels = wall.DISTINCT_PLACEHOLDER.findall(distinct)
    assert len(labels) == 3 and labels[0] == labels[1] != labels[2]


def test_the_restricted_matcher_splits_on_everything_outside_a_to_z():
    one, two = sorted(WORDS)
    assert restricted.find_hits(f"{one.upper()}, x{one}; {two}9 and {two}_{one}", WORDS) == WORDS
    assert restricted.find_hits(f"x{one} {one}x", WORDS) == set()
    assert restricted.hit_lines(f"a\n{one}\nb\n{two}-x\n", WORDS) == [2, 4]


def test_the_scan_reads_parquet_gzip_and_text_and_refuses_what_it_cannot_read(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = tmp_path / "rows.parquet"
    pq.write_table(pa.table({"word": ["plain", PLAIN], "n": [1, 2]}), path)
    text, kind = scan.read_as_text("rows.parquet", path.read_bytes())
    assert kind == "parquet" and wall.Matcher(TERMS).hits(text) == {PLAIN}
    text, kind = scan.read_as_text("a.json.gz", gzip.compress(PLAIN.encode()))
    assert kind == "text" and text == PLAIN
    assert scan.read_as_text("a.png", b"\x89PNG\xff") == (None, "unread")
    assert scan.read_as_text("a.bin", b"\xff\xfe\x00") == (None, "unreadable")


def _scanner() -> scan.Scanner:
    return scan.Scanner(TERMS, WORDS)


def test_the_scan_counts_hits_in_a_file_and_in_its_path():
    report = scan.Report()
    word = sorted(WORDS)[0]
    items = [
        ("clean.md", "clean.md", b"nothing here\n"),
        ("doc.md", "doc.md", f"one\n{PLAIN} and {word}\nthree {PLAIN}\n".encode()),
        (f"{PLAIN}.md", f"{PLAIN}.md", b"the path holds the term\n"),
        ("blob.bin", "blob.bin", b"\xff\xfe\x00"),
        ("pic.png", "pic.png", b"\x89PNG\xff"),
    ]
    scan.scan_items(_scanner(), items, report)
    assert (report.read, report.unread, report.unreadable) == (3, 1, ["blob.bin"])
    by_where = {f.where: f for f in report.findings}
    assert set(by_where) == {"doc.md", f"{PLAIN}.md"}
    doc = by_where["doc.md"]
    assert (doc.walled, doc.restricted) == (1, 1)
    assert doc.walled_lines == [2, 3] and doc.restricted_lines == [2]
    assert by_where[f"{PLAIN}.md"].walled_lines == [0]      # line 0 is the path
    assert PLAIN not in doc.line() and word not in doc.line()
    assert report.status() == 1


def test_an_exemption_covers_one_exact_file_only():
    data = f"spec: {PLAIN}\n".encode()
    row = exemptions.Exemption("spec.py", hashlib.sha256(data).hexdigest(), 1, 0, "a stand-in")
    for exempt, content, clean in (
            ({"spec.py": row}, data, True),
            ({"spec.py": row}, data + b"# edited\n", False),            # the bytes changed
            ({"spec.py": row}, f"spec: {PLAIN} {HYPHEN}\n".encode(), False),
            ({"other.py": row}, data, False)):                           # another path
        report = scan.Report()
        scan.scan_items(_scanner(), [("spec.py", "spec.py", content)], report, exempt)
        assert (report.findings == []) is clean
        assert report.exempt == (1 if clean else 0)


def test_the_exemptions_file_names_files_that_exist_with_their_hashes():
    for row in exemptions.load().values():
        path = locations.REPO / row.path
        assert path.is_file(), row.path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row.sha256, row.path
        assert row.reason.strip()


def test_the_pushed_ranges_follow_the_hook_lines():
    a, b = "a" * 40, "b" * 40
    lines = (f"refs/heads/x {a} refs/heads/x {b}\n"
             f"refs/heads/new {a} refs/heads/new {scan.ZERO}\n"
             f"(delete) {scan.ZERO} refs/heads/gone {b}\n")
    assert scan.pushed_ranges(locations.REPO, lines) == [
        [a, f"^{b}"], [a, "--not", "--remotes"]]


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c",
                    "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


@pytest.fixture
def repo_with_lists(tmp_path, monkeypatch):
    """A temporary repository scanned against the stand-in lists."""
    private = tmp_path / "private"
    (private / "wall").mkdir(parents=True)
    (private / "restricted").mkdir()
    (private / "wall" / "walled_terms.json").write_text(json.dumps({"lists": {
        "ledger": sorted(TERMS), "controls": [PLAIN], "probes": [HYPHEN],
        "pilot": [PHRASE]}}), encoding="utf-8")
    (private / "restricted" / "universe_miss_restricted.csv").write_text(
        "word\n" + "\n".join(sorted(WORDS)) + "\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    monkeypatch.setenv("CEOL_PRIVATE", str(private))
    monkeypatch.setattr(locations, "REPO", repo)
    monkeypatch.setattr(exemptions, "EXEMPTIONS_CSV", tmp_path / "none.csv")
    return repo


def test_the_scan_of_a_checkout_reads_what_a_commit_could_capture(repo_with_lists, capsys):
    repo = repo_with_lists
    (repo / ".gitignore").write_text("ignored.txt\n")
    (repo / "tracked.md").write_text("clean\n")
    (repo / "ignored.txt").write_text(f"{PLAIN}\n")          # ignored: not read
    _git(repo, "add", "-A")
    assert scan.run([]) == 0
    (repo / "untracked.md").write_text(f"{PLAIN}\n")         # untracked: read
    assert scan.run([]) == 1
    out = capsys.readouterr().out
    assert "FAIL untracked.md" in out and PLAIN not in out


def test_the_scan_of_a_push_reads_every_commit_and_every_message(repo_with_lists, capsys):
    repo = repo_with_lists
    (repo / "a.md").write_text("clean\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a clean commit")
    assert scan.run(["--history"]) == 0
    # a term committed and then removed is still in what a push sends
    (repo / "a.md").write_text(f"{PLAIN}\n")
    _git(repo, "commit", "-q", "-am", "adds a line")
    (repo / "a.md").write_text("clean again\n")
    _git(repo, "commit", "-q", "-am", "removes the line")
    assert scan.run([]) == 0                                 # the checkout is clean
    assert scan.run(["--history"]) == 1                      # the history is not
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    hook_line = f"refs/heads/main {head} refs/heads/main {scan.ZERO}\n"
    assert scan.run(["--push"], hook_lines=hook_line) == 1
    out = capsys.readouterr().out
    assert "a.md@" in out and PLAIN not in out


def test_the_scan_reads_commit_messages(repo_with_lists, capsys):
    repo = repo_with_lists
    (repo / "a.md").write_text("clean\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"a message that names {PLAIN}")
    assert scan.run(["--history"]) == 1
    out = capsys.readouterr().out
    assert "the message of commit" in out and PLAIN not in out


def test_the_scan_cannot_run_without_the_lists(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CEOL_PRIVATE", str(tmp_path / "absent"))
    assert scan.run([]) == 2
    assert "could not run" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# The real lists: skipped where private/ is absent
# ---------------------------------------------------------------------------

needs_private = pytest.mark.skipif(
    not (wall.available() and restricted.available()),
    reason="private/ is absent in this environment (make link)")


@needs_private
def test_the_private_lists_load_as_the_archive_module_returned_them():
    lists = wall.walled_terms()
    assert set(lists) == set(wall.LISTS) and lists["controls"] <= lists["ledger"]
    body = json.loads(locations.wall_json().read_text(encoding="utf-8"))
    assert {name: len(terms) for name, terms in lists.items()} == body["counts"]
    assert len(wall.all_terms()) == body["distinct_terms"]
    assert restricted.restricted_words()


@needs_private
def test_no_restricted_word_and_no_study_item_in_the_committable_files():
    assert scan.run([]) == 0


@needs_private
def test_the_matcher_equals_the_archive_matcher_on_this_repository():
    terms = wall.all_terms()
    matcher = wall.Matcher(terms)
    compared = 0
    for _label, path, data in scan.committable(locations.REPO):
        text, kind = scan.read_as_text(path, data)
        if kind != "text" or len(text) > 20_000:
            continue
        compared += 1
        same = matcher.hits(text) == wall.find_hits(text, terms)
        assert same, path
    assert compared > 0
