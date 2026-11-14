#!/usr/bin/env python3
"""Print the technical report's built page to PDF, beside the page.

    python3 tools/report_pdf.py

It serves `site/dist/` on a local port for the length of the run and has
Chrome, headless, print `/research/report/` with the page's print styles to
`site/dist/research/report/<name>.pdf`, the file the page links to. The PDF
is printed from the web page, so its text and figures are the page's; its
layout is the print styles', so each build's pages are looked at. It is
written into the build's output, never committed. It needs Chrome; where
Chrome is absent it says so and fails.
"""

from __future__ import annotations

import functools
import http.server
import shutil
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DIST = REPO / "site" / "dist"
PAGE = "/research/report/"
NAME = "ceol-universe-v1.0-report.pdf"
CHROME = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
)


def main() -> int:
    page = DIST / PAGE.strip("/") / "index.html"
    if not page.exists():
        print(f"[pdf] {page.relative_to(REPO)} is absent; build the site first", file=sys.stderr)
        return 1
    chrome = next((c for c in CHROME if c and Path(c).exists()), None)
    if not chrome:
        print("[pdf] Chrome is not installed here", file=sys.stderr)
        return 1
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

    handler = functools.partial(Quiet, directory=str(DIST))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    out = page.parent / NAME
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}{PAGE}"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=8000", f"--print-to-pdf={out}", url],
                       check=True, capture_output=True, timeout=180)
    finally:
        server.shutdown()
    if not out.exists() or out.stat().st_size < 10_000:
        print("[pdf] Chrome wrote no report", file=sys.stderr)
        return 1
    print(f"[pdf] {out.relative_to(REPO)}: {out.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
