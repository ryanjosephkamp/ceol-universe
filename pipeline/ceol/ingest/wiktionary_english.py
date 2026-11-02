"""
Wiktionary with the `== English ==` confirmation, under the CEOL grammar —
plus a Noun-heading capture that feeds the C1 possessive sizing.

Port of the EOL's research/ingest/wiktionary_english.py with three changes:

1. normalize() is the CEOL grammar, so hyphenated, accented and apostrophe
   titles now survive instead of dying at `^[a-z]+$`.
2. The case-sensitivity convention (EOL D-031) is enforced explicitly:
   already-lowercase titles only, checked BEFORE normalization — `Café`
   must not fold onto `café`'s page identity.
3. While inside a page's English section, `===Noun===` / `====Noun====`
   headings are recorded. `===Proper noun===` deliberately does not match.
   The noun set sizes the possessive class for the C1 gate.

The heading regexes carry the EOL's hard-won `(?:^|>)` prefix: a page whose
wikitext begins with its language heading puts `==English==` on the same
line as the `<text ...>` tag, and a line-start-only match silently loses
every English-first page (caught live EOL-side at a third of the expected
count).

Disk discipline: the 1.62 GB dump is downloaded, streamed once, deleted.

Run:  python -m ceol.ingest.wiktionary_english
"""

from __future__ import annotations

import bz2
import re
import sys
import time
import unicodedata

from ceol.grammar import normalize

from .common import RAW_DIR, sha256_file, write_derived
from .census_sources import PINS, SourceCensus

DUMP = RAW_DIR / "enwiktionary-20260804-pages-articles.xml.bz2"

TITLE = re.compile(r"<title>([^<]*)</title>")
ENGLISH = re.compile(r"(?:^|>)==\s*English\s*==\s*$")
LANG_L2 = re.compile(r"(?:^|>)==[^=]")          # any level-2 heading
NOUN = re.compile(r"(?:^|>)={3,4}\s*Noun\s*={3,4}\s*$")


def main() -> int:
    url, pin, _ = PINS["wiktionary_english"]
    if not DUMP.exists():
        print(f"[wikt-en] {DUMP} not present; download it first (pin {pin})",
              flush=True)
        return 1
    sha = sha256_file(DUMP)
    if sha != pin:
        print(f"[wikt-en] sha256 {sha} != pin {pin}; refusing to ingest",
              flush=True)
        return 1
    print(f"[wikt-en] artifact sha256 verified: {sha}", flush=True)

    census = SourceCensus("wiktionary_english")
    english: set[str] = set()
    nouns: set[str] = set()
    pages = 0
    cur_key: str | None = None       # grammar-valid title of the current page
    in_english = False
    t0 = time.time()

    with bz2.open(DUMP, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "<title>" in line:
                pages += 1
                if pages % 1_000_000 == 0:
                    print(f"[wikt-en] {pages:,} pages, {len(english):,} "
                          f"English entries ({len(census.words):,} exception"
                          f"-class), {len(nouns):,} nouns, "
                          f"{time.time()-t0:,.0f}s", flush=True)
                cur_key = None
                in_english = False
                m = TITLE.search(line)
                if m:
                    t = unicodedata.normalize("NFC", m.group(1))
                    if t == t.lower():          # case-sensitive convention
                        cur_key = normalize(t)
            elif cur_key is not None and "==" in line:
                stripped = line.rstrip("\n")
                if "English" in stripped and ENGLISH.search(stripped):
                    if cur_key not in english:
                        english.add(cur_key)
                        census.add(cur_key)
                    in_english = True
                elif in_english:
                    if NOUN.search(stripped):
                        nouns.add(cur_key)
                    elif LANG_L2.search(stripped) \
                            and not ENGLISH.search(stripped):
                        in_english = False

    meta = write_derived("wiktionary_english", census.words, meta={
        **census.stats(), "artifact_sha256": sha, "url": url,
        "pages_scanned": pages, "english_entries_all": len(english),
        "english_nouns_all": len(nouns)})

    out = RAW_DIR.parent / "derived"
    with open(out / "wiktionary_english_all.txt", "w", encoding="utf-8") as f:
        for w in sorted(english):
            f.write(w + "\n")
    with open(out / "wiktionary_english_nouns.txt", "w",
              encoding="utf-8") as f:
        for w in sorted(nouns):
            f.write(w + "\n")

    print(f"[wikt-en] DONE: {len(english):,} English entries "
          f"({meta['record_count']:,} exception-class, {len(nouns):,} nouns) "
          f"from {pages:,} pages in {time.time()-t0:,.0f}s", flush=True)

    DUMP.unlink()                      # 1.62 GB; the pin makes it re-fetchable
    print("[wikt-en] dump deleted", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
