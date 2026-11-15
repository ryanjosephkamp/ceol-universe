"""
S3 space census, stage 3: cross-source analysis.

Reads the two per-source extractions (built by run_wordnet_census.py and
run_wiktionary_stream.py, each with its C4-era anchor already asserted),
the pinned universe, the S6 posterior baseline, and the EOL valid list
(read-only, comparison use only), and produces the committed aggregate
research/space_census/space_census.json — the figure source for
SPACE_CENSUS.md and the S4 gate report, enforcer-checked.

Sections (AGENDA S3):
  - per-source counts and the two-source overlap matrix
  - token-count and character-length distributions, longest entries
  - Wiktionary POS and category profile (literal headings/links only)
  - part-membership profile against (a) the EOL valid list and (b) the
    S6 posterior baseline at p_word >= 0.5 — a correlate of the
    bound-token subclass only (CONTEXT precision note 2), reported as
    description, never an intake filter; 30 sha256-ranked examples per
    band, seed "c015-s3", ranked by sha256("c015-s3:<band>:<word>")
  - properness signals from both sources
  - variant families: spaced <-> hyphenated <-> closed joins against the
    existing universe
  - licence check: zero space-bearing entries in NWL2023/CSW21
    (structural — the game lists are single-token — but tested anyway;
    the restricted lists are read locally and never leave .cache)

Every sampled list is deterministic: sha256 ranking, never a library RNG.

Run:  python -m research.space_census.analyze_space_census
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from ceol.grammar import SPACE
from ceol.ingest.common import EOL_REPO

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / ".cache" / "space_census"
OUT = REPO / "research" / "space_census" / "space_census.json"

WN_JSONL = CACHE / "wordnet_spaced.jsonl"
WK_JSONL = CACHE / "wiktionary_spaced.jsonl"
WK_REJECTS = CACHE / "wiktionary_spaced_rejects.json"
WN_AGG = REPO / "research" / "space_census" / "wordnet_census.json"
WK_AGG = REPO / "research" / "space_census" / "wiktionary_census.json"

UNIVERSE = REPO / "data" / "universe.parquet"
POSTERIORS = REPO / "data" / "posteriors.parquet"
EOL_VALID = EOL_REPO / ".cache" / "hf" / "merged_valid_words.txt"
EOL_VALID_SHA = "aa8df4c5d4358b67119462a27accf29c919309814d8b33377b03c4bf0244f6e0"

#: EOL derived game lists (read-only, licence check only; pins from the
#: C3/C4 machinery). Contents never leave the local machine.
EOL_DERIVED = EOL_REPO / ".cache" / "sources" / "derived"
GAME_PINS = {
    "nwl2023": ("79de4b07ed6f38ad1bdb1bf874e42383815b78730b23a0edce511f3ef043058e", 196_601),
    "csw21": ("136332497985c48389f017064e7875ce49398ee10b5dc0fa4c701f7a5085985c", 279_077),
}

SEED = "c015-s3"
POSTERIOR_THRESHOLD = 0.5

POS_HEADINGS = {
    "Noun", "Verb", "Adjective", "Adverb", "Phrase", "Proverb",
    "Proper noun", "Prepositional phrase", "Preposition", "Conjunction",
    "Interjection", "Pronoun", "Determiner", "Numeral", "Particle",
    "Contraction", "Idiom", "Symbol", "Article", "Postposition",
    "Participle", "Letter",
}

#: The declared particle inventory for the phrasal-verb count (J3) — a
#: mechanical rule in the spirit of the contraction rule: a Verb-headed
#: entry whose final token is one of these. Deliberately narrower than a
#: linguist's inventory; the count sizes the class, the definition rules.
PHRASAL_PARTICLES = frozenset((
    "up", "down", "out", "off", "in", "on", "over", "away", "back",
    "around", "about", "through", "along", "across", "by", "forward",
    "together", "apart", "aside", "round", "under", "behind", "ahead",
    "past", "forth", "home",
))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rank_sample(words, stratum: str, n: int = 30) -> list[str]:
    """The project sampling rule: sha256(seed:stratum:word) ranking."""
    return sorted(
        words,
        key=lambda w: hashlib.sha256(
            f"{SEED}:{stratum}:{w}".encode("utf-8")).hexdigest())[:n]


def read_jsonl(path: Path) -> dict[str, dict]:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            out[rec["key"]] = rec
    return out


def main() -> None:
    wn = read_jsonl(WN_JSONL)
    wk = read_jsonl(WK_JSONL)
    wn_agg = json.loads(WN_AGG.read_text(encoding="utf-8"))
    wk_agg = json.loads(WK_AGG.read_text(encoding="utf-8"))
    wk_rej = json.loads(WK_REJECTS.read_text(encoding="utf-8"))
    for agg, name in ((wn_agg, "wordnet"), (wk_agg, "wiktionary")):
        for a in agg["anchor"].values() if name == "wiktionary" \
                else [agg["anchor"]]:
            assert a.get("status") == "reproduced", (name, a)

    keys_wn = set(wn)
    keys_wk = set(wk)
    both = keys_wn & keys_wk
    union = keys_wn | keys_wk

    # --- distributions over the union ------------------------------------
    tokc = Counter(k.count(SPACE) + 1 for k in union)
    lens = sorted(len(k) for k in union)
    length_pcts = {f"p{q}": lens[min(len(lens) - 1, len(lens) * q // 100)]
                   for q in (10, 25, 50, 75, 90, 99)}
    by_tokens_desc = sorted(union, key=lambda k: (-(k.count(SPACE) + 1), k))
    by_length_desc = sorted(union, key=lambda k: (-len(k), k))

    # --- Wiktionary POS / category profile -------------------------------
    pos_counter: Counter[str] = Counter()
    cat_counter: Counter[str] = Counter()
    for rec in wk.values():
        for h in rec["pos"]:
            if h in POS_HEADINGS:
                pos_counter[h] += 1
        for c in rec["cats"]:
            cat_counter[c] += 1

    def wk_with(pred) -> set[str]:
        return {k for k, r in wk.items() if pred(r)}

    buckets = {
        "noun": wk_with(lambda r: "Noun" in r["pos"]),
        "verb": wk_with(lambda r: "Verb" in r["pos"]),
        "adjective": wk_with(lambda r: "Adjective" in r["pos"]),
        "adverb": wk_with(lambda r: "Adverb" in r["pos"]),
        "phrase": wk_with(lambda r: "Phrase" in r["pos"]
                          or "Prepositional phrase" in r["pos"]),
        "proverb": wk_with(lambda r: "Proverb" in r["pos"]
                           or "English proverbs" in r["cats"]),
        "phrasebook": wk_with(lambda r: r.get("phrasebook", False)),
        "idiomatic_label": wk_with(lambda r: r.get("idiomatic", False)),
        "proper_noun": wk_with(lambda r: "Proper noun" in r["pos"]),
        "phrasal_verb": wk_with(
            lambda r: "Verb" in r["pos"]
            and r["key"].split(SPACE)[-1] in PHRASAL_PARTICLES),
        "taxonomic": wk_with(
            lambda r: any("axonomic" in c for c in r["cats"])),
    }
    pos_buckets = ("noun", "verb", "adjective", "adverb", "phrase",
                   "proverb", "proper_noun")
    covered = set().union(*(buckets[b] for b in pos_buckets))
    pos_any = wk_with(lambda r: any(h in POS_HEADINGS for h in r["pos"]))
    buckets_out = {
        name: {"count": len(members),
               "examples": rank_sample(members, f"bucket:{name}", 15)}
        for name, members in buckets.items()
    }
    buckets_out["other_no_bucket"] = {
        "count": len(keys_wk - covered),
        "examples": rank_sample(keys_wk - covered, "bucket:other", 15),
    }

    # --- token vocabulary and part-membership ----------------------------
    token_set: set[str] = set()
    for k in union:
        token_set.update(k.split(SPACE))

    got = sha256_file(EOL_VALID)
    assert got == EOL_VALID_SHA, f"EOL valid list drifted: {got}"
    with open(EOL_VALID, encoding="utf-8") as f:
        eol_valid = {line.rstrip("\n") for line in f if line.strip()}

    token_p: dict[str, float] = {}
    import pyarrow.parquet as pq
    for batch in pq.ParquetFile(POSTERIORS).iter_batches(
            batch_size=1_000_000, columns=["word", "p_word"]):
        words = batch.column("word").to_pylist()
        ps = batch.column("p_word").to_pylist()
        for w, p in zip(words, ps):
            if w in token_set:
                token_p[w] = p

    def fraction_bands(in_ref) -> dict:
        bands: dict[str, list[str]] = {
            "f0": [], "f_low": [], "f_half": [], "f_high": [], "f1": []}
        for k in union:
            toks = k.split(SPACE)
            f = sum(1 for t in toks if in_ref(t)) / len(toks)
            if f == 0:
                bands["f0"].append(k)
            elif f < 0.5:
                bands["f_low"].append(k)
            elif f == 0.5:
                bands["f_half"].append(k)
            elif f < 1:
                bands["f_high"].append(k)
            else:
                bands["f1"].append(k)
        return bands

    pm = {}
    for ref_name, member in (
            ("eol_valid", lambda t: t in eol_valid),
            ("s6_posterior",
             lambda t: token_p.get(t, 0.0) >= POSTERIOR_THRESHOLD)):
        bands = fraction_bands(member)
        pm[ref_name] = {
            "bands": {b: len(ws) for b, ws in bands.items()},
            "examples": {b: rank_sample(ws, f"pm:{ref_name}:{b}")
                         for b, ws in bands.items()},
        }
    pm["s6_posterior"]["threshold"] = POSTERIOR_THRESHOLD
    pm["note"] = ("correlate of the bound-token subclass only; "
                  "description, not an intake filter")

    # --- properness ------------------------------------------------------
    wk_proper = buckets["proper_noun"]
    wn_instance = {k for k, r in wn.items() if r["instance"]}
    wn_capitalized = {k for k, r in wn.items() if r["capitalized"]}
    properness = {
        "wordnet_instance": len(wn_instance),
        "wordnet_capitalized_in_data": len(wn_capitalized),
        "wordnet_both": len(wn_instance & wn_capitalized),
        "wiktionary_proper_noun_pos": len(wk_proper),
        "instance_examples": rank_sample(wn_instance, "prop:instance", 20),
        "wiktionary_proper_examples": rank_sample(wk_proper, "prop:wk", 20),
        "note": ("the D-031 lowercase-title convention already excludes "
                 "capitalized Wiktionary pages; WordNet properness is "
                 "attributed from instance hypernyms and data-file case, "
                 "never from the lowercased index"),
    }

    # --- variant families -------------------------------------------------
    closed_q: dict[str, list[str]] = {}
    hyphen_q: dict[str, list[str]] = {}
    for k in union:
        closed_q.setdefault(k.replace(SPACE, ""), []).append(k)
        hyphen_q.setdefault(k.replace(SPACE, "-"), []).append(k)
    closed_hits: set[str] = set()
    hyphen_hits: set[str] = set()
    for batch in pq.ParquetFile(UNIVERSE).iter_batches(
            batch_size=1_000_000, columns=["word"]):
        for w in batch.column("word").to_pylist():
            if w in closed_q:
                closed_hits.update(closed_q[w])
            if w in hyphen_q:
                hyphen_hits.update(hyphen_q[w])
    variants = {
        "closed_form_in_universe": len(closed_hits),
        "hyphen_form_in_universe": len(hyphen_hits),
        "both_forms_in_universe": len(closed_hits & hyphen_hits),
        "either_form_in_universe": len(closed_hits | hyphen_hits),
        "neither_form_in_universe": len(union - closed_hits - hyphen_hits),
        "examples_both": rank_sample(closed_hits & hyphen_hits,
                                     "var:both", 20),
        "examples_closed_only": rank_sample(closed_hits - hyphen_hits,
                                            "var:closed", 20),
        "examples_hyphen_only": rank_sample(hyphen_hits - closed_hits,
                                            "var:hyphen", 20),
    }

    # --- licence check ----------------------------------------------------
    licence = {}
    for src, (pin, count) in GAME_PINS.items():
        path = EOL_DERIVED / f"{src}.txt"
        got = sha256_file(path)
        assert got == pin, f"{src}: derived sha {got} != pin {pin}"
        n_space = n_rows = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n_rows += 1
                    if SPACE in line.rstrip("\n"):
                        n_space += 1
        assert n_rows == count, f"{src}: {n_rows} rows != pinned {count}"
        licence[src] = {"rows": n_rows, "space_bearing": n_space}
    assert all(v["space_bearing"] == 0 for v in licence.values())
    licence["spaced_candidates_only_attributable_to_game_lists"] = 0

    # --- assemble ---------------------------------------------------------
    universe_pin = 10_001_741
    out = {
        "generated_by": "research/space_census/analyze_space_census.py",
        "inputs": {
            "wordnet_spaced_jsonl_sha256": sha256_file(WN_JSONL),
            "wiktionary_spaced_jsonl_sha256": sha256_file(WK_JSONL),
            "eol_valid_sha256": EOL_VALID_SHA,
            "universe_parquet": str(UNIVERSE.relative_to(REPO)),
            "posteriors_parquet": str(POSTERIORS.relative_to(REPO)),
            "sampling": f"sha256('{SEED}:<stratum>:<word>') ranking",
        },
        "sources": {
            "wordnet": {"spaced": len(keys_wn),
                        "rejects": wn_agg["multiword_rejects"]["total"]},
            "wiktionary": {"spaced": len(keys_wk),
                           "english_all": wk_agg["english_entries_all"],
                           "rejects": wk_agg["spaced_rejects_total"]},
        },
        "overlap": {
            "both": len(both),
            "wordnet_only": len(keys_wn - keys_wk),
            "wiktionary_only": len(keys_wk - keys_wn),
            "union": len(union),
            "examples_both": rank_sample(both, "ov:both", 15),
            "examples_wordnet_only": rank_sample(keys_wn - keys_wk,
                                                 "ov:wn", 15),
            "examples_wiktionary_only": rank_sample(keys_wk - keys_wn,
                                                    "ov:wk", 15),
        },
        "token_count_distribution":
            {str(k): v for k, v in sorted(tokc.items())},
        "char_length_percentiles": length_pcts,
        "longest_by_tokens": by_tokens_desc[:10],
        "longest_by_chars": by_length_desc[:10],
        "wiktionary_pos_heading_counts": dict(sorted(pos_counter.items())),
        "wiktionary_pos_any_heading": len(pos_any),
        "wiktionary_top_categories": dict(cat_counter.most_common(40)),
        "wiktionary_buckets": buckets_out,
        "wiktionary_rejects": wk_rej,
        "part_membership": pm,
        "properness": properness,
        "variant_families": variants,
        "licence_check": licence,
        "doc_figures": {
            "wn_spaced": len(keys_wn),
            "wk_spaced": len(keys_wk),
            "overlap_both": len(both),
            "wn_only": len(keys_wn - keys_wk),
            "wk_only": len(keys_wk - keys_wn),
            "union_total": len(union),
            "two_token": tokc[2],
            "two_token_pct": round(100 * tokc[2] / len(union), 1),
            "three_token": tokc[3],
            "max_tokens": max(tokc),
            "tokens_ge10": sum(v for k, v in tokc.items() if k >= 10),
            "longest_chars": len(by_length_desc[0]),
            "len_p50": length_pcts["p50"],
            "len_p90": length_pcts["p90"],
            "len_p99": length_pcts["p99"],
            "wn_max_tokens": max(
                int(k) for k in wn_agg["token_count_distribution"]),
            "wn_max_chars": wn_agg["char_length"]["max"],
            "pos_any": len(pos_any),
            "pos_any_pct": round(100 * len(pos_any) / len(keys_wk), 2),
            "interjection": pos_counter["Interjection"],
            "no_pos_bucket": len(keys_wk - covered),
            "eol_half_tokens": pm["eol_valid"]["bands"]["f_half"],
            "eol_all_pct": round(
                100 * pm["eol_valid"]["bands"]["f1"] / len(union), 1),
            "s6_all_pct": round(
                100 * pm["s6_posterior"]["bands"]["f1"] / len(union), 1),
            "wn_both_properness": len(wn_instance & wn_capitalized),
            "variants_closed": variants["closed_form_in_universe"],
            "variants_hyphen": variants["hyphen_form_in_universe"],
            "variants_both": variants["both_forms_in_universe"],
            "game_nwl_rows": licence["nwl2023"]["rows"],
            "game_csw_rows": licence["csw21"]["rows"],
            "rej_wk_comma": wk_rej["by_reason"].get("comma", 0),
            "rej_wk_digit": wk_rej["by_reason"].get("digit", 0),
            "rej_wk_trailing_apostrophe":
                wk_rej["by_reason"].get("token_trailing_apostrophe", 0),
            "rej_wk_period": wk_rej["by_reason"].get("period", 0),
            "rej_wk_other": wk_rej["by_reason"].get("other", 0),
            "rej_wk_undeclared_letter":
                wk_rej["by_reason"].get("undeclared_letter", 0),
            "rej_wn_period":
                wn_agg["multiword_rejects"]["by_reason"].get("period", 0),
            "rej_wn_digit":
                wn_agg["multiword_rejects"]["by_reason"].get("digit", 0),
            "rej_wn_trailing_apostrophe":
                wn_agg["multiword_rejects"]["by_reason"].get(
                    "token_trailing_apostrophe", 0),
            "anchor_wn_plain": wn_agg["anchor"]["plain_count"],
            "anchor_wn_exceptions": wn_agg["anchor"]["exception_count"],
            "anchor_wk_all": wk_agg["anchor"]["english_all"]["count"],
            "anchor_wk_exceptions": wk_agg["anchor"]["exceptions"]["count"],
            "anchor_wk_nouns": wk_agg["anchor"]["nouns"]["count"],
            "pages_scanned": wk_agg["inputs"]["pages"],
            "wk_english_all": wk_agg["english_entries_all"],
            "wk_rejects_total": wk_agg["spaced_rejects_total"],
            "wn_rejects_total": wn_agg["multiword_rejects"]["total"],
            "nbsp_only_keys": wk_rej["nbsp_fold"]["keys_only_via_nbsp"],
            "wn_instance": len(wn_instance),
            "wn_capitalized": len(wn_capitalized),
            "wk_proper_noun_pos": len(wk_proper),
            "wk_phrasebook": len(buckets["phrasebook"]),
            "wk_phrasal_verb": len(buckets["phrasal_verb"]),
            "wk_idiomatic_label": len(buckets["idiomatic_label"]),
            "wk_proverb": len(buckets["proverb"]),
            "eol_valid_all_tokens": pm["eol_valid"]["bands"]["f1"],
            "eol_valid_no_tokens": pm["eol_valid"]["bands"]["f0"],
            "s6_all_tokens": pm["s6_posterior"]["bands"]["f1"],
            "s6_no_tokens": pm["s6_posterior"]["bands"]["f0"],
            "variants_either": variants["either_form_in_universe"],
            "variants_neither": variants["neither_form_in_universe"],
            "game_list_spaced": 0,
            "universe_pin": universe_pin,
            "union_pct_of_pin": round(100 * len(union) / universe_pin, 1),
        },
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    for k, v in out["doc_figures"].items():
        print(f"  {k} = {v:,}" if isinstance(v, int) else f"  {k} = {v}")


if __name__ == "__main__":
    main()
