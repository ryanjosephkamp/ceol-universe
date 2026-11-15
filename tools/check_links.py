#!/usr/bin/env python3
"""The link check: every relative link in a tracked Markdown file leads to a
file that exists, and every link to a heading leads to a heading that exists.

    python3 tools/check_links.py              the relative links
    python3 tools/check_links.py --external   also request each external link

What is read: Markdown inline links and images (`[text](target)`), reference
definitions (`[name]: target`), and HTML `href` and `src` attributes inside
Markdown. A link inside a code span or a fenced code block is not a link.

A root-relative link (`/research/study/`) in the site's own text,
`site/content/`, is a page of the site: it must name a page that
`site/src/pages/` builds.

What is left out, by path (`EXCLUDED`): the archival material, which is kept
as the archive holds it and whose links name files of the archive.

External links are requested only with `--external`, so that the default
check needs no network and gives the same answer everywhere.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: path prefixes whose Markdown is not checked
EXCLUDED = ("reference/", "pipeline/research/")

_FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.M | re.S)
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_INLINE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?\s*$", re.M)
_HTML = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""")
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)


def tracked_markdown() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--cached",
                          "--others", "--exclude-standard", "*.md"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return sorted(rel for rel in filter(None, out.split("\0"))
                  if not rel.startswith(EXCLUDED) and (REPO / rel).is_file())


def strip_code(text: str) -> str:
    return _CODE_SPAN.sub("", _FENCE.sub("", text))


def targets(text: str) -> list[str]:
    bare = strip_code(text)
    return (_INLINE.findall(bare) + _REFERENCE.findall(bare)
            + _HTML.findall(bare))


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped,
    spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    for heading in _HEADING.findall(_FENCE.sub("", path.read_text(encoding="utf-8"))):
        base = slug(heading)
        name, k = base, 0
        while name in found:
            k += 1
            name = f"{base}-{k}"
        found.add(name)
    return found


SITE_CONTENT = "site/content/"
PAGES = REPO / "site" / "src" / "pages"


def site_page_exists(route: str) -> bool:
    """Whether `site/src/pages/` builds the page at `route`: its own file,
    its folder's index, or a rest route of its section."""
    parts = [p for p in route.strip("/").split("/") if p]
    base = PAGES.joinpath(*parts) if parts else PAGES
    if (base / "index.astro").is_file() or (parts and base.with_suffix(".astro").is_file()):
        return True
    return bool(parts) and any((PAGES.joinpath(*parts[:k]) / "[...slug].astro").is_file()
                               for k in range(len(parts) + 1))


def check_file(rel: str) -> tuple[list[str], list[str]]:
    """(the problems of a file's relative links, its external links)."""
    source = REPO / rel
    problems, external = [], []
    for target in targets(source.read_text(encoding="utf-8")):
        if re.match(r"[a-z][a-z0-9+.\-]*:", target, re.I):
            if target.startswith(("http://", "https://")):
                external.append(target)
            continue                       # mailto:, and other schemes
        path_part, _, fragment = target.partition("#")
        if rel.startswith(SITE_CONTENT) and path_part.startswith("/"):
            if not site_page_exists(path_part):
                problems.append(f"{rel}: no page of the site at {target}")
            continue
        if path_part:
            dest = (REPO / path_part.lstrip("/")) if path_part.startswith("/") \
                else (source.parent / path_part)
            if not dest.exists():
                problems.append(f"{rel}: no file at {target}")
                continue
        else:
            dest = source
        if fragment and dest.is_file() and dest.suffix == ".md" \
                and fragment.lower() not in anchors(dest):
            problems.append(f"{rel}: no heading for {target}")
    return problems, external


def request(url: str) -> str | None:
    """None where the link answers, else what went wrong."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": "ceol-universe link check"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status < 400:
                    return None
        except urllib.error.HTTPError as exc:
            if method == "GET" or exc.code not in (403, 405, 501):
                return f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            if method == "GET":
                return type(exc).__name__
    return "no answer"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--external", action="store_true",
                    help="also request each external link")
    args = ap.parse_args(argv)
    files = tracked_markdown()
    problems: list[str] = []
    external: dict[str, list[str]] = {}
    links = 0
    for rel in files:
        text = (REPO / rel).read_text(encoding="utf-8")
        links += len(targets(text))
        found, outside = check_file(rel)
        problems += found
        for url in outside:
            external.setdefault(url, []).append(rel)
    if args.external:
        for url in sorted(external):
            wrong = request(url)
            if wrong:
                problems.append(f"{external[url][0]}: {url} ({wrong})")
    for line in problems:
        print(f"FAIL {line}")
    print(f"links: {len(files)} Markdown file(s), {links} link(s), "
          f"{len(external)} external "
          f"({'requested' if args.external else 'not requested'}): "
          f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
