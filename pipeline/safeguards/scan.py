"""The scan run before every push (PLAN.md §2, rules 2 and 7).

It fails where a restricted word or an item of the study's wall list stands
in anything a push would send. It prints paths, counts, and line numbers,
and never the string that matched.

    python3 -m safeguards.scan               the files a commit of this
                                             checkout could capture
    python3 -m safeguards.scan --push        the commits a push would send;
                                             reads the pre-push hook's lines
    python3 -m safeguards.scan --history     every commit reachable from HEAD
    python3 -m safeguards.scan PATH ...      the named files and folders

Run from `pipeline/`, or through `make scan`. `.githooks/pre-push` runs the
`--push` form.

What is read:

- a text file as UTF-8, and its path as text;
- a Parquet file through its string columns;
- a gzip file after decompression;
- in the `--push` and `--history` forms, each commit's message.

Images and fonts pass unread and are counted. Any other file that is not
UTF-8 text fails the scan, because the scan cannot say what it holds.

Exit status: 0 clean; 1 a hit; 2 the private lists are absent, so the scan
could not run; 3 a file the scan could not read.
"""

from __future__ import annotations

import argparse
import gzip
import io
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from safeguards import exemptions, locations, restricted, wall

#: file types that pass unread: they hold pixels or glyphs, not text
UNREAD_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".pdf"})

ZERO = "0" * 40


@dataclass
class Finding:
    where: str
    walled: int = 0
    restricted: int = 0
    walled_lines: list[int] = field(default_factory=list)
    restricted_lines: list[int] = field(default_factory=list)

    def line(self) -> str:
        parts = []
        if self.walled:
            parts.append(f"{self.walled} walled term(s) on line(s) "
                         f"{_lines(self.walled_lines)}")
        if self.restricted:
            parts.append(f"{self.restricted} restricted word(s) on line(s) "
                         f"{_lines(self.restricted_lines)}")
        return f"{self.where}: {'; '.join(parts)}"


def _lines(numbers: list[int]) -> str:
    shown = ", ".join(str(n) for n in numbers[:12])
    return shown + (f", and {len(numbers) - 12} more" if len(numbers) > 12 else "")


class Scanner:
    """The 2 matchers over 1 text at a time."""

    def __init__(self, terms: set[str], words: set[str]):
        self.matcher = wall.Matcher(terms)
        self.words = words

    def text(self, where: str, text: str) -> Finding | None:
        walled = self.matcher.hits(text)
        hit_words = restricted.find_hits(text, self.words)
        if not walled and not hit_words:
            return None
        return Finding(
            where, len(walled), len(hit_words),
            self.matcher.hit_lines(text) if walled else [],
            restricted.hit_lines(text, self.words) if hit_words else [])


def _parquet_text(data: bytes) -> str:
    """The string columns of a Parquet file as text, 1 value per line, with
    the schema's metadata."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pq.read_table(io.BytesIO(data))
    lines: list[str] = []
    for key, value in (table.schema.metadata or {}).items():
        lines.append(key.decode("utf-8", "replace"))
        lines.append(value.decode("utf-8", "replace"))
    for name in table.column_names:
        lines.append(name)
        column = table.column(name)
        if pa.types.is_string(column.type) or pa.types.is_large_string(column.type):
            lines.extend(v for v in column.to_pylist() if v is not None)
    return "\n".join(lines)


def read_as_text(path: str, data: bytes) -> tuple[str | None, str]:
    """The text the scan reads for a file, or None with the reason."""
    suffix = Path(path).suffix.lower()
    if suffix in UNREAD_SUFFIXES:
        return None, "unread"
    if suffix == ".parquet":
        return _parquet_text(data), "parquet"
    if suffix == ".gz":
        data = gzip.decompress(data)
    try:
        return data.decode("utf-8"), "text"
    except UnicodeDecodeError:
        return None, "unreadable"


@dataclass
class Report:
    read: int = 0
    unread: int = 0
    exempt: int = 0
    messages: int = 0
    findings: list[Finding] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)

    def status(self) -> int:
        if self.findings:
            return 1
        if self.unreadable:
            return 3
        return 0


def scan_items(scanner: Scanner, items, report: Report,
               exempt: dict[str, exemptions.Exemption] | None = None) -> None:
    """`items` yields (label, path, bytes). The path is read as text too."""
    exempt = exempt or {}
    for label, path, data in items:
        text, kind = read_as_text(path, data)
        if kind == "unread":
            report.unread += 1
            text = ""
        elif kind == "unreadable":
            report.unreadable.append(label)
            continue
        else:
            report.read += 1
        finding = scanner.text(label, path + "\n" + text)
        if finding is None:
            continue
        # line numbers are the file's own: the path is the text's line 0
        finding.walled_lines = [n - 1 for n in finding.walled_lines]
        finding.restricted_lines = [n - 1 for n in finding.restricted_lines]
        if exemptions.covers(exempt.get(path), data, finding.walled,
                             finding.restricted):
            report.exempt += 1
            continue
        report.findings.append(finding)


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], input=stdin,
                          capture_output=True, check=True).stdout


def committable(repo: Path):
    """The files a commit of this checkout could capture: tracked files and
    untracked files that are not ignored."""
    listed = _git(repo, "ls-files", "-z", "--cached", "--others",
                  "--exclude-standard").decode("utf-8").split("\0")
    for rel in sorted(filter(None, listed)):
        path = repo / rel
        if path.is_symlink() or not path.is_file():
            continue
        yield rel, rel, path.read_bytes()


def named(paths: list[str]):
    for given in paths:
        root = Path(given)
        files = [root] if root.is_file() else sorted(
            p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
        for path in files:
            if path.name == ".DS_Store":
                continue
            yield str(path), str(path), path.read_bytes()


def _blobs(repo: Path, rev_args: list[str]):
    """Every blob of the named commits, once per (blob, path)."""
    listing = _git(repo, "rev-list", "--objects", *rev_args).decode("utf-8")
    entries = [line.split(" ", 1) for line in listing.splitlines() if " " in line]
    if not entries:
        return
    kinds = _git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                 stdin="\n".join(sha for sha, _p in entries).encode()).decode()
    is_blob = {line.split()[0] for line in kinds.splitlines()
               if line.endswith(" blob")}
    for sha, path in entries:
        if sha in is_blob and path:
            yield f"{path}@{sha[:10]}", path, _git(repo, "cat-file", "blob", sha)


def _messages(repo: Path, rev_args: list[str]):
    out = _git(repo, "log", "--format=%H%x00%B%x01", *rev_args).decode(
        "utf-8", "replace")
    for record in filter(str.strip, out.split("\x01")):
        sha, _, body = record.strip().partition("\0")
        yield f"the message of commit {sha[:10]}", body


def pushed_ranges(repo: Path, hook_lines: str) -> list[list[str]]:
    """The rev-list arguments for each ref the pre-push hook names. A new
    branch sends every commit no remote-tracking ref already holds."""
    ranges = []
    for line in hook_lines.splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = fields
        if local_sha == ZERO:
            continue                      # a deletion sends nothing
        if remote_sha == ZERO:
            ranges.append([local_sha, "--not", "--remotes"])
        else:
            ranges.append([local_sha, f"^{remote_sha}"])
    return ranges


def run(argv: list[str] | None = None, hook_lines: str | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--push", action="store_true",
                    help="the commits a push would send (the hook's lines "
                         "on standard input)")
    ap.add_argument("--history", action="store_true",
                    help="every commit reachable from HEAD")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args(argv)
    repo = locations.REPO
    try:
        terms, words = wall.all_terms(), restricted.restricted_words()
    except (wall.WallAbsent, restricted.RestrictedAbsent) as exc:
        print(f"scan: could not run: {exc}", file=sys.stderr)
        return 2
    scanner = Scanner(terms, words)
    exempt = exemptions.load()
    report = Report()
    if args.paths:
        scan_items(scanner, named(args.paths), report)
    elif args.push or args.history:
        if args.history:
            ranges = [["HEAD"]]
        else:
            lines = sys.stdin.read() if hook_lines is None else hook_lines
            ranges = pushed_ranges(repo, lines)
        for rev_args in ranges:
            scan_items(scanner, _blobs(repo, rev_args), report, exempt)
            for label, body in _messages(repo, rev_args):
                report.messages += 1
                finding = scanner.text(label, body)
                if finding:
                    report.findings.append(finding)
    else:
        scan_items(scanner, committable(repo), report, exempt)
    for finding in report.findings:
        print(f"FAIL {finding.line()}")
    for label in report.unreadable:
        print(f"FAIL {label}: not UTF-8 text and not a type the scan reads")
    print(f"scan: {len(terms)} walled terms and {len(words)} restricted words "
          f"against {report.read} file(s) read, {report.unread} passed unread "
          f"(images and fonts), {report.exempt} exempt by hash, "
          f"{report.messages} commit message(s): "
          f"{len(report.findings)} with a hit, "
          f"{len(report.unreadable)} unreadable")
    return report.status()


if __name__ == "__main__":
    raise SystemExit(run())
