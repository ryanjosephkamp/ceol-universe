"""
C3: the sufficiency audit v2 — is the merged universe sufficiently complete
under the CEOL grammar?

Three instruments, one report (AUDIT.md + audit.json, enforcer-checked):

  --coverage   Per-source coverage of the merged universe: every census
               source's full CEOL-valid set, plus the EOL's binary detector
               sources (read-only, hash-verified). Misses are split into
               plain [a-z]+ (candidates for C4's universe pin) and
               exception-class (must be zero by construction).

  --drift      The fresh-Wiktionary residual. No dump newer than the pinned
               2026-08-04 run exists, so instead of sampling a stale dump
               the audit EXACTLY enumerates ns0 page creations since the
               dump boundary via the free MediaWiki recentchanges API,
               then checks the grammar-valid, non-universe subset for
               `== English ==` sections (batched revisions API; sha256-
               ranked sampling only if the subset exceeds the cap). A live
               instrument: reproducible in method, its population moves —
               so the enumerated snapshot is persisted and hashed, and the
               retrieval window is recorded.

  --frontier   The structural-plausibility frontier, v0: an interpolated
               character n-gram (orders 1..5, Witten-Bell) trained on the
               pinned valid list, enumerated EXACTLY in descending
               probability by best-first search (monotone: every extension
               adds log p <= 0). Reports how much of the top-K most
               plausible string mass the universe already holds; the
               unattested remainder is the frontier's first yield. v0 is
               deliberately [a-z]-only (trained on validated words, and
               only the EOL's words are validated); C4's retrained model
               supersedes it.

Everything is a measurement; no universe changes, nothing published.

Run:  python -m research.audit.run_audit --coverage --drift --frontier --assemble
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ceol.grammar import classes as class_flags
from ceol.grammar import normalize
from ceol.ingest.common import DERIVED_DIR, EOL_REPO, sha256_file

REPO = Path(__file__).resolve().parents[2]
AUDIT_DIR = REPO / "research" / "audit"
AUDIT_CACHE = REPO / ".cache" / "audit"
MERGED_PARQUET = REPO / "data" / "merged.parquet"

#: The dump boundary: the pinned all-titles artifact's Last-Modified.
DUMP_BOUNDARY = "2026-08-04T22:33:23Z"

#: EOL binary detector sources: derived sets read READ-ONLY from the EOL
#: cache, verified against the EOL manifest's derived_sha256 pins.
EOL_BINARY = {
    "wordnet": ("266b875d86cb132cb924490626140e8c104b7170db5c5e14d2e117fd3a32bed2", 77503),
    "enable1": ("3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89", 172823),
    "sowpods_legacy": ("5a855b21aa2bef5b98be71c719668337b3ceeaa6cb1cc08efab2a8ff0759a38f", 267751),
    "nwl2023": ("79de4b07ed6f38ad1bdb1bf874e42383815b78730b23a0edce511f3ef043058e", 196601),
    "csw21": ("136332497985c48389f017064e7875ce49398ee10b5dc0fa4c701f7a5085985c", 279077),
}

CENSUS_SOURCES = ("wiktionary_english", "hunspell_en_US", "hunspell_en_GB",
                  "hunspell_en_CA", "hunspell_en_AU", "scowl", "web2",
                  "web2a", "wordfreq")

API = "https://en.wiktionary.org/w/api.php"
USER_AGENT = ("common-english-openlist/0.1 "
              "(https://huggingface.co/datasets/ryanjosephkamp/"
              "common-english-openlist; C3 sufficiency audit)")
ENGLISH = re.compile(r"(?:^|>)==\s*English\s*==\s*$", re.M)
DRIFT_EXACT_CAP = 2000        # above this, sha256-sample instead
DRIFT_SAMPLE = 1000

FRONTIER_K = 10000
FRONTIER_MAX_LEN = 24
FRONTIER_MAX_POPS = 20_000_000


def _read_lines(path: Path) -> set[str]:
    with open(path, encoding="utf-8") as f:
        return {line.rstrip("\n") for line in f if line.strip()}


def load_universe() -> set[str]:
    import pyarrow.parquet as pq
    t = pq.read_table(MERGED_PARQUET, columns=["word"])
    return set(t.column("word").to_pylist())


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

def _full_source_set(source: str) -> set[str]:
    if source == "wiktionary_english":
        return _read_lines(DERIVED_DIR / "wiktionary_english_all.txt")
    return (_read_lines(DERIVED_DIR / f"{source}.txt")
            | _read_lines(DERIVED_DIR / f"{source}_plain.txt"))


def run_coverage(universe: set[str]) -> dict:
    rows = {}
    miss_pool: dict[str, set[str]] = {}
    for source in CENSUS_SOURCES:
        words = _full_source_set(source)
        misses = words - universe
        miss_plain = {w for w in misses if not class_flags(w)}
        miss_exc = misses - miss_plain
        if miss_exc:
            raise RuntimeError(
                f"{source}: {len(miss_exc)} exception-class words missing "
                f"from the universe — the census inventory is broken: "
                f"{sorted(miss_exc)[:5]}")
        rows[source] = {
            "total": len(words), "in_universe": len(words) - len(misses),
            "coverage_pct": round(100 * (len(words) - len(misses))
                                  / len(words), 2),
            "miss_plain": len(miss_plain), "miss_exception": len(miss_exc),
        }
        if miss_plain:
            miss_pool[source] = miss_plain

    for source, (pin, count) in EOL_BINARY.items():
        path = EOL_REPO / ".cache" / "sources" / "derived" / f"{source}.txt"
        got = sha256_file(path)
        if got != pin:
            raise RuntimeError(f"{source}: EOL derived sha {got} != pin")
        words = _read_lines(path)
        if len(words) != count:
            raise RuntimeError(f"{source}: {len(words)} != pinned {count}")
        misses = words - universe
        rows[f"eol:{source}"] = {
            "total": len(words), "in_universe": len(words) - len(misses),
            "coverage_pct": round(100 * (len(words) - len(misses))
                                  / len(words), 2),
            "miss_plain": len(misses), "miss_exception": 0,
        }
        if misses:
            miss_pool[f"eol:{source}"] = misses

    union_misses = sorted(set().union(*miss_pool.values())) if miss_pool \
        else []

    # Provenance per miss word (C-008): which sources attest it.
    attribution: dict[str, list[str]] = {}
    for source, words in miss_pool.items():
        for w in words:
            attribution.setdefault(w, []).append(source)

    # Licence split. NWL2023 and CSW21 are redistributable=False in the EOL
    # manifest, which is why its ingest keeps their derived files in
    # gitignored .cache/ and never ships them. A miss word attested ONLY by
    # those two would be redistributed by committing this file, so it is
    # written to the gitignored cache instead — present for the C4 pin,
    # absent from the repository and from any remote.
    proprietary = {"eol:nwl2023", "eol:csw21"}
    shippable, restricted = [], []
    for w in union_misses:
        (restricted if set(attribution[w]) <= proprietary else
         shippable).append(w)

    out = AUDIT_DIR / "universe_miss_candidates.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "sources"])
        for w in shippable:
            writer.writerow([w, ";".join(sorted(attribution[w]))])

    AUDIT_CACHE.mkdir(parents=True, exist_ok=True)
    held = AUDIT_CACHE / "universe_miss_restricted.csv"
    with open(held, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "sources"])
        for w in restricted:
            writer.writerow([w, ";".join(sorted(attribution[w]))])

    return {"sources": rows,
            "miss_union": len(union_misses),
            "miss_by_source": {k: len(v) for k, v in sorted(miss_pool.items())},
            "miss_shippable": len(shippable),
            "miss_restricted": len(restricted),
            "restricted_note": "attested only by nwl2023/csw21 "
                               "(redistributable=false); held in gitignored "
                               ".cache/audit/, never committed or pushed",
            "miss_file_sha256": sha256_file(out),
            "restricted_file_sha256": sha256_file(held)}


# ---------------------------------------------------------------------------
# Drift (the fresh-Wiktionary residual)
# ---------------------------------------------------------------------------

def _api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))
    # throttling handled by caller


def enumerate_new_pages() -> list[str]:
    """Every ns0 non-redirect page created since the dump boundary —
    exhaustive, newest-first, paginated."""
    titles: list[str] = []
    cont: dict = {}
    while True:
        data = _api({"action": "query", "list": "recentchanges",
                     "rcnamespace": 0, "rctype": "new", "rcshow": "!redirect",
                     "rclimit": 500, "rcprop": "title|timestamp",
                     "rcend": DUMP_BOUNDARY, **cont})
        batch = data.get("query", {}).get("recentchanges", [])
        titles.extend(rc["title"] for rc in batch)
        cont = data.get("continue", {})
        if not cont:
            return titles
        time.sleep(0.15)


def check_english(titles: list[str]) -> dict[str, bool]:
    """Batched wikitext fetch, 50 titles per request; a page is English iff
    its current wikitext carries a level-2 English heading."""
    verdicts: dict[str, bool] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = _api({"action": "query", "prop": "revisions",
                     "rvprop": "content", "rvslots": "main",
                     "titles": "|".join(batch)})
        pages = data.get("query", {}).get("pages", {})
        got = {}
        for page in pages.values():
            revs = page.get("revisions")
            text = (revs[0]["slots"]["main"].get("*", "")
                    if revs else "")
            got[page.get("title", "")] = bool(ENGLISH.search(text))
        # API may normalize titles; map back case-insensitively is unsafe —
        # only exact matches count, missing pages count as not-English.
        for t in batch:
            verdicts[t] = got.get(t, False)
        time.sleep(0.15)
    return verdicts


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - spread) / denom, (centre + spread) / denom)


def run_drift(universe: set[str]) -> dict:
    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_new = enumerate_new_pages()

    AUDIT_CACHE.mkdir(parents=True, exist_ok=True)
    snap = AUDIT_CACHE / "rc_new_titles.txt"
    with open(snap, "w", encoding="utf-8") as f:
        for t in all_new:
            f.write(t + "\n")

    candidates: list[str] = []
    for t in all_new:
        t_nfc = unicodedata.normalize("NFC", t)
        if t_nfc != t_nfc.lower():
            continue                       # case-sensitive convention
        key = normalize(t_nfc)
        if key is not None and key not in universe:
            candidates.append(t_nfc)
    candidates = sorted(set(candidates))

    if len(candidates) <= DRIFT_EXACT_CAP:
        checked, mode = candidates, "exact"
    else:
        checked = sorted(
            candidates,
            key=lambda w: hashlib.sha256(
                f"c3-drift:{w}".encode()).hexdigest())[:DRIFT_SAMPLE]
        mode = "sha256-sample"
    verdicts = check_english(checked)
    english = sorted(t for t, v in verdicts.items() if v)

    with open(AUDIT_DIR / "drift_checked.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "english"])
        for t in checked:
            w.writerow([t, "yes" if verdicts[t] else "no"])

    if mode == "exact":
        estimate, lo, hi = len(english), len(english), len(english)
    else:
        p_lo, p_hi = _wilson(len(english), len(checked))
        estimate = round(len(candidates) * len(english) / len(checked))
        lo, hi = (round(len(candidates) * p_lo),
                  round(len(candidates) * p_hi))

    return {
        "boundary": DUMP_BOUNDARY, "retrieved": retrieved,
        "new_pages_ns0": len(all_new),
        "new_grammar_valid_not_in_universe": len(candidates),
        "checked": len(checked), "mode": mode,
        "english_confirmed": len(english),
        "residual_estimate": estimate,
        "residual_ci95": [lo, hi],
        "snapshot_sha256": sha256_file(snap),
        "limitation": "counts page CREATIONS since the boundary; pages that "
                      "existed at dump time and gained an English section "
                      "since are not counted",
    }


# ---------------------------------------------------------------------------
# Frontier v0
# ---------------------------------------------------------------------------

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
END = "$"
MAX_ORDER = 5


def train_model(words: set[str]):
    counts: list[dict[str, Counter]] = [dict() for _ in range(MAX_ORDER + 1)]
    for w in words:
        seq = w + END
        for i, c in enumerate(seq):
            for order in range(0, MAX_ORDER + 1):
                if i < order:
                    continue
                ctx = seq[i - order:i] if order else ""
                counts[order].setdefault(ctx, Counter())[c] += 1
    return counts


def make_logp(counts):
    symbols = ALPHABET + END
    uniform = 1.0 / len(symbols)
    cache: dict[str, dict[str, float]] = {}

    def dist(ctx: str) -> dict[str, float]:
        if ctx in cache:
            return cache[ctx]
        # Witten-Bell interpolation, recursive down the orders.
        if ctx == "":
            c = counts[0].get("", Counter())
            n, t = sum(c.values()), len(c)
            lam = n / (n + t) if n else 0.0
            d = {s: lam * (c.get(s, 0) / n if n else 0.0)
                 + (1 - lam) * uniform for s in symbols}
        else:
            lower = dist(ctx[1:])
            c = counts[len(ctx)].get(ctx, Counter())
            n, t = sum(c.values()), len(c)
            lam = n / (n + t) if n else 0.0
            d = {s: lam * (c.get(s, 0) / n if n else 0.0)
                 + (1 - lam) * lower[s] for s in symbols}
        cache[ctx] = d
        return d

    def logp(prefix: str, c: str) -> float:
        ctx = prefix[-MAX_ORDER:]
        return math.log(dist(ctx)[c])

    return logp


def run_frontier(universe: set[str]) -> dict:
    valid_path = EOL_REPO / ".cache" / "hf" / "merged_valid_words.txt"
    pin = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"
    if sha256_file(valid_path) != pin:
        raise RuntimeError("valid list does not match pin; refusing")
    valid = _read_lines(valid_path)
    logp = make_logp(train_model(valid))

    # Best-first enumeration: monotone, therefore exact top-K.
    heap = [(0.0, "")]           # (-logprob, prefix); "" = start
    results: list[tuple[float, str]] = []
    pops = 0
    while heap and len(results) < FRONTIER_K and pops < FRONTIER_MAX_POPS:
        neg, prefix = heapq.heappop(heap)
        pops += 1
        if prefix.endswith(END):
            results.append((-neg, prefix[:-1]))
            continue
        if len(prefix) >= FRONTIER_MAX_LEN:
            continue
        for c in ALPHABET + END:
            heapq.heappush(heap, (neg - logp(prefix, c), prefix + c))

    words = [(lp, w) for lp, w in results if w]
    attested = [(lp, w) for lp, w in words if w in universe]
    unattested = [(lp, w) for lp, w in words if w not in universe]
    with open(AUDIT_DIR / "frontier_v0.txt", "w", encoding="utf-8") as f:
        f.write("# top unattested strings, exact descending probability; "
                "candidates only, most are junk — that is the point\n")
        for lp, w in unattested[:1000]:
            f.write(f"{w}\t{lp:.4f}\n")
    return {
        "model": "char n-gram, orders 1-5, Witten-Bell, trained on "
                 "valid@c1139698 (a-z only, v0)",
        "top_k": len(words), "pops": pops,
        "attested_in_universe": len(attested),
        "unattested": len(unattested),
        "attested_pct": round(100 * len(attested) / len(words), 1),
        "top_unattested_examples": [w for _, w in unattested[:15]],
        "frontier_file_sha256": sha256_file(AUDIT_DIR / "frontier_v0.txt"),
    }


# ---------------------------------------------------------------------------
# Reconciliation against the EOL's D-026 frame
# ---------------------------------------------------------------------------

def run_reconcile(universe: set[str]) -> dict:
    """
    The EOL's research frame (evidence.parquet, 9,787,841 words) is the
    published universe plus 133,842 source-contributed strings (its D-026).
    The coverage audit's miss-union should decompose exactly into (a) those
    frame additions and (b) strings only the census's wider visibility sees
    (wordfreq — a corpus source the EOL's D-030 kept out of frame
    membership — plus SCOWL's variant/contraction files and any newer-dump
    drift). This computes that decomposition; an unexplained remainder
    would mean one of the two pipelines is wrong.
    """
    import pyarrow.parquet as pq
    fc = json.loads((EOL_REPO / "research" / "data" /
                     "frame_contributions.json").read_text(encoding="utf-8"))
    t = pq.read_table(EOL_REPO / "research" / "data" / "evidence.parquet",
                      columns=["word"])
    frame = set(t.column("word").to_pylist())
    if len(frame) != fc["frame_size"]:
        raise RuntimeError(f"EOL frame {len(frame)} != recorded "
                           f"{fc['frame_size']}")
    additions = frame - universe
    az_universe = {w for w in universe if not class_flags(w)}
    if not az_universe >= (frame & universe):
        raise RuntimeError("universe/frame overlap is not plain a-z")

    misses = set()
    for path in (AUDIT_DIR / "universe_miss_candidates.csv",
                 AUDIT_CACHE / "universe_miss_restricted.csv"):
        with open(path, encoding="utf-8") as f:
            misses |= {row["word"] for row in csv.DictReader(f)}
    in_frame = misses & additions
    beyond_frame = misses - additions

    wordfreq_full = _full_source_set("wordfreq")
    beyond_wordfreq_only = set()
    for w in beyond_frame:
        others = False
        for source in CENSUS_SOURCES:
            if source == "wordfreq":
                continue
            # cheap membership: the miss lists per source were not kept, so
            # re-test containment in the full source sets
            if w in _FULL_CACHE.setdefault(source, _full_source_set(source)):
                others = True
                break
        if not others and w in wordfreq_full:
            beyond_wordfreq_only.add(w)
    return {
        "eol_frame_size": len(frame),
        "eol_frame_additions": len(additions),
        "miss_union": len(misses),
        "miss_in_frame_additions": len(in_frame),
        "miss_beyond_frame": len(beyond_frame),
        "beyond_frame_wordfreq_only": len(beyond_wordfreq_only),
        "beyond_frame_other": len(beyond_frame) - len(beyond_wordfreq_only),
        "frame_additions_not_missed":
            len(additions) - len(in_frame),
        "note": "beyond_frame_other = SCOWL variant/contraction visibility "
                "the EOL's six-category ingest did not read; "
                "frame_additions_not_missed would be nonzero only if a "
                "frame addition were an exception-class word (impossible "
                "under ^[a-z]+$) or a source shrank",
    }


_FULL_CACHE: dict[str, set[str]] = {}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def assemble() -> None:
    parts = {}
    for name in ("coverage", "drift", "frontier", "reconcile"):
        p = AUDIT_DIR / f"{name}.json"
        if not p.exists():
            raise RuntimeError(f"{p} missing; run --{name} first")
        parts[name] = json.loads(p.read_text(encoding="utf-8"))
    audit = {
        "generated_by": "research/audit/run_audit.py",
        "universe": "data/merged.parquet (9,867,866 rows incl. exceptions)",
        **parts,
    }
    cov = parts["coverage"]
    worst = min(cov["sources"].values(), key=lambda r: r["coverage_pct"])
    audit["doc_figures"] = {
        "miss_union": cov["miss_union"],
        "miss_shippable": cov["miss_shippable"],
        "miss_restricted": cov["miss_restricted"],
        "worst_coverage_pct": str(worst["coverage_pct"]),
        "drift_new_pages": parts["drift"]["new_pages_ns0"],
        "drift_candidates":
            parts["drift"]["new_grammar_valid_not_in_universe"],
        "drift_english": parts["drift"]["english_confirmed"],
        "residual_estimate": parts["drift"]["residual_estimate"],
        "frontier_attested_pct": str(parts["frontier"]["attested_pct"]),
        "frontier_unattested": parts["frontier"]["unattested"],
        "eol_frame_additions": parts["reconcile"]["eol_frame_additions"],
        "miss_in_frame_additions":
            parts["reconcile"]["miss_in_frame_additions"],
        "beyond_frame_wordfreq_only":
            parts["reconcile"]["beyond_frame_wordfreq_only"],
        "beyond_frame_other": parts["reconcile"]["beyond_frame_other"],
    }
    merge = json.loads((REPO / "research" / "merge" / "merge.json")
                       .read_text(encoding="utf-8"))
    audit["doc_figures"]["c4_recommended_pin"] = (
        merge["doc_figures"]["merged_total"]
        + parts["reconcile"]["miss_in_frame_additions"]
        + parts["reconcile"]["beyond_frame_other"])
    for src, row in cov["sources"].items():
        audit["doc_figures"][f"cov_{src}"] = str(row["coverage_pct"])
    (AUDIT_DIR / "audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print("[audit] assembled -> research/audit/audit.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    for flag in ("coverage", "drift", "frontier", "reconcile", "assemble"):
        ap.add_argument(f"--{flag}", action="store_true")
    args = ap.parse_args()
    AUDIT_DIR.mkdir(exist_ok=True)
    universe = None
    for name, fn in (("coverage", run_coverage), ("drift", run_drift),
                     ("frontier", run_frontier), ("reconcile", run_reconcile)):
        if getattr(args, name):
            if universe is None:
                print("[audit] loading universe …", flush=True)
                universe = load_universe()
            print(f"[audit] running {name} …", flush=True)
            result = fn(universe)
            (AUDIT_DIR / f"{name}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"[audit] {name} done")
    if args.assemble:
        assemble()
    return 0


if __name__ == "__main__":
    sys.exit(main())
