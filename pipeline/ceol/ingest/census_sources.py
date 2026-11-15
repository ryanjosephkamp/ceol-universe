"""
C1 census ingests: the already-pinned EOL artifacts, re-read under the CEOL
grammar. Same bytes, wider rule — the whole premise of the census.

Pins are copied from the EOL's sources/MANIFEST.toml (revision-identical
artifacts) plus one new source: web2a, the hyphenated companion of web2 that
the EOL had no grammar to hold. Every ingest verifies its artifact's sha256
before reading a line.
"""

from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path

from .common import (RAW_DIR, SourceCensus, open_maybe_gzip, resolve_artifact,
                     sha256_file, write_derived)

#: (url, sha256, eol-relative cache path). The first eight pins are verbatim
#: from the EOL manifest; web2a is pinned fresh here (macOS 26 system file).
PINS = {
    "wiktionary_titles": (
        "https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-all-titles-in-ns0.gz",
        "468b58bc03f0d8e69b7df0c90c2ac3841be288acd5afe3b052939d70e44d633c",
        ".cache/wiktionary/all-titles.gz"),
    "wiktionary_english": (
        "https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2",
        "a0db4eeaea5e6b9940e21ea143eaecf93195610888d345333ae560b9a15527d1",
        None),
    "web2": ("file:///usr/share/dict/words",
             "be41ad97963bf8dabedd5871d5d691596175269d540956b0f9965a885c2bbab9",
             None),
    "web2a": ("file:///usr/share/dict/web2a",
              "9313e251fee3e56204db2b284346d61c3a80ce613d7a077c5674f15f9cb33ab3",
              None),
    "hunspell_en_US": (
        "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_US.dic",
        "f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
        ".cache/sources/raw/en_US.dic"),
    "hunspell_en_GB": (
        "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_GB.dic",
        "04e90f34f5263bf26780e9c4a442e9ad16584e227af49ddd1b3b21b01df5b29c",
        ".cache/sources/raw/en_GB.dic"),
    "hunspell_en_CA": (
        "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_CA.dic",
        "53096689870246a78fa408b1e7a8c49bc140bd466a84a384cfb509445fff7173",
        ".cache/sources/raw/en_CA.dic"),
    "hunspell_en_AU": (
        "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/en_AU.dic",
        "aa07c46571f306b79fc1bc534357ed357af15687381b26f891ba66e8a2caed89",
        ".cache/sources/raw/en_AU.dic"),
    "scowl": (
        "https://downloads.sourceforge.net/wordlist/scowl-2020.12.07.tar.gz",
        "5587667caa20c4891390c2d42dbb4d5c4c3f41bee77af1457ece3ba23fb859cc",
        ".cache/sources/raw/scowl-2020.12.07.tar.gz"),
}

#: wordfreq is pinned by package version (EOL manifest: 3.1.1), not URL.
WORDFREQ_VERSION_PIN = "3.1.1"


def _finish(census: SourceCensus, *, meta: dict) -> dict:
    """Persist the exception candidates (the census deliverable) AND the
    plain [a-z]+ set (the C3 coverage audit's input), both sorted+hashed."""
    from .common import DERIVED_DIR, sha256_file as _sha
    meta = write_derived(census.source_id, census.words,
                         meta={**census.stats(), **meta})
    plain_path = DERIVED_DIR / f"{census.source_id}_plain.txt"
    with open(plain_path, "w", encoding="utf-8") as f:
        for w in sorted(census.plain):
            f.write(w + "\n")
    meta["plain_sha256"] = _sha(plain_path)
    import json as _json
    with open(DERIVED_DIR / f"{census.source_id}.meta.json", "w",
              encoding="utf-8") as f:
        _json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


# ---------------------------------------------------------------------------
# Flat files
# ---------------------------------------------------------------------------

def ingest_web2() -> dict:
    url, sha, _ = PINS["web2"]
    path = resolve_artifact("web2", url=url, sha256=sha)
    census = SourceCensus("web2")
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip():
                census.add(line.strip())
    return _finish(census, meta={"artifact_sha256": sha, "url": url})


def ingest_web2a() -> dict:
    """web2's companion: the hyphenated supplement the EOL could not hold."""
    url, sha, _ = PINS["web2a"]
    path = resolve_artifact("web2a", url=url, sha256=sha)
    census = SourceCensus("web2a")
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip():
                census.add(line.strip())
    return _finish(census, meta={"artifact_sha256": sha, "url": url})


def ingest_wordfreq() -> dict:
    import importlib.metadata

    import wordfreq
    version = importlib.metadata.version("wordfreq")
    if version != WORDFREQ_VERSION_PIN:
        raise RuntimeError(f"wordfreq {version} != pin {WORDFREQ_VERSION_PIN}")
    census = SourceCensus("wordfreq")
    for token in wordfreq.iter_wordlist("en", wordlist="best"):
        census.add(token)
    return _finish(census, meta={"package_version": version,
                                 "url": "pypi:wordfreq"})


# ---------------------------------------------------------------------------
# SCOWL: words + contractions subcategories, every English variant category
# ---------------------------------------------------------------------------

#: Included: the {category}-{words,contractions}.{size} families — the
#: variant categories are where locale-variant and hyphenated forms live.
#: Excluded by mission, with counts recorded: abbreviations and upper
#: (exclusive-acronym territory), proper-names (exclusive-proper territory),
#: special-hacker and special-roman-numerals (not natural-language vocab).
SCOWL_SUBCATS = ("words", "contractions")
SCOWL_FILE = re.compile(
    r"scowl-2020\.12\.07/final/([a-z_0-9]+)-(words|contractions|abbreviations"
    r"|proper-names|upper)\.(\d+)$")
SCOWL_SPECIAL = re.compile(r"scowl-2020\.12\.07/final/special-[a-z-]+\.\d+$")


def ingest_scowl() -> dict:
    url, sha, eol_rel = PINS["scowl"]
    path = resolve_artifact("scowl-2020.12.07.tar.gz", url=url, sha256=sha,
                            eol_relative=eol_rel)
    census = SourceCensus("scowl")
    included: list[str] = []
    excluded: dict[str, int] = {}
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if SCOWL_SPECIAL.match(member.name):
                excluded["special"] = excluded.get("special", 0) + 1
                continue
            m = SCOWL_FILE.match(member.name)
            if not m:
                continue
            subcat = m.group(2)
            if subcat not in SCOWL_SUBCATS:
                excluded[subcat] = excluded.get(subcat, 0) + 1
                continue
            included.append(member.name.split("/final/")[1])
            fh = tar.extractfile(member)
            assert fh is not None
            # SCOWL ships ISO-8859-1; under the CEOL grammar the accented
            # entries now COUNT instead of failing the form rule.
            for line in io.TextIOWrapper(fh, encoding="latin-1"):
                if line.strip():
                    census.add(line.strip())
    return _finish(census, meta={
        "artifact_sha256": sha, "url": url,
        "files_included": sorted(included),
        "files_excluded_counts": dict(sorted(excluded.items()))})


# ---------------------------------------------------------------------------
# hunspell: .dic + .aff expanded to surface forms with spylls — the EOL's
# D-022 expansion, verbatim in behaviour
# ---------------------------------------------------------------------------

def _expand_hunspell(dic_path: Path) -> set[str]:
    """Unmunch stems x affix rules -> surface forms. Port of the EOL's
    research/ingest/sources.py:_expand_hunspell, unchanged in behaviour."""
    from spylls.hunspell import Dictionary
    d = Dictionary.from_files(str(dic_path.with_suffix("")))
    aff = d.aff

    def rule_applies(rule, stem: str) -> bool:
        regex = getattr(rule, "cond_regexp", None)
        return True if regex is None else bool(regex.search(stem))

    def apply_suffix(rule, stem: str) -> str | None:
        if not rule_applies(rule, stem):
            return None
        base = stem[: len(stem) - len(rule.strip)] if rule.strip else stem
        return base + rule.add

    def apply_prefix(rule, stem: str) -> str | None:
        if not rule_applies(rule, stem):
            return None
        base = stem[len(rule.strip):] if rule.strip else stem
        return rule.add + base

    forms: set[str] = set()
    for word in d.dic.words:
        stem = word.stem
        flags = word.flags or set()
        forms.add(stem)
        suffixed: list[tuple[str, object]] = []
        for flag in flags:
            for sfx in aff.SFX.get(flag, []):
                out = apply_suffix(sfx, stem)
                if out is None:
                    continue
                forms.add(out)
                suffixed.append((out, sfx))
                for cont_flag in getattr(sfx, "flags", ()) or ():
                    for sfx2 in aff.SFX.get(cont_flag, []):
                        out2 = apply_suffix(sfx2, out)
                        if out2 is not None:
                            forms.add(out2)
        for flag in flags:
            for pfx in aff.PFX.get(flag, []):
                out = apply_prefix(pfx, stem)
                if out is None:
                    continue
                forms.add(out)
                if getattr(pfx, "crossproduct", False):
                    for suf_form, sfx in suffixed:
                        if getattr(sfx, "crossproduct", False):
                            both = apply_prefix(pfx, suf_form)
                            if both is not None:
                                forms.add(both)
    return forms


def ingest_hunspell(locale: str) -> dict:
    source_id = f"hunspell_{locale}"
    url, sha, eol_rel = PINS[source_id]
    dic_path = resolve_artifact(f"{locale}.dic", url=url, sha256=sha,
                                eol_relative=eol_rel)
    # spylls reads {basename}.dic + {basename}.aff from one directory; the
    # EOL cache carries both. The dic is the pinned artifact; the aff's hash
    # is recorded in the meta for the census's own reproducibility.
    aff_src = dic_path.with_suffix(".aff")
    if not aff_src.exists():
        raise RuntimeError(f"{aff_src} missing beside the pinned dic; "
                           "fetch the pair before ingesting")
    census = SourceCensus(source_id)
    raw_forms = _expand_hunspell(dic_path)
    for form in raw_forms:
        census.add(form)
    return _finish(census, meta={
        "artifact_sha256": sha, "url": url,
        "aff_sha256": sha256_file(aff_src),
        "expansion": "spylls", "raw_form_count": len(raw_forms)})


# ---------------------------------------------------------------------------
# Wiktionary all-languages title screen (the 27.8 MB index, on disk)
# ---------------------------------------------------------------------------

def ingest_wiktionary_titles() -> dict:
    """A SCREEN, not a verdict: a title hit means SOME language uses the
    spelling. Case-sensitive source (EOL D-031): already-lowercase titles
    only — polish and Polish are different pages, and lowering Polish onto
    polish would launder proper-noun pages into common-word keys."""
    import unicodedata
    url, sha, eol_rel = PINS["wiktionary_titles"]
    path = resolve_artifact("all-titles.gz", url=url, sha256=sha,
                            eol_relative=eol_rel)
    census = SourceCensus("wiktionary_titles")
    with open_maybe_gzip(path, errors="ignore") as f:
        next(f, None)                       # header line
        for line in f:
            t = line.rstrip("\n")
            if "\t" in t:
                t = t.split("\t")[-1]
            t = unicodedata.normalize("NFC", t)
            if t != t.lower():
                continue                    # case-sensitive convention
            census.add(t)
    return _finish(census, meta={"artifact_sha256": sha, "url": url,
                                 "role": "screen",
                                 "case_convention": "lowercase titles only"})
