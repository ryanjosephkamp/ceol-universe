"""Every figure of the technical paper on the CEOL Universe
(research/release/report/PAPER_<version>.md), printed as a named row from
committed files: the descriptive analysis (`figures/<version>/analysis.json`,
research/analysis/descriptive.py), the card's calculator
(research/release/public_card.py), and the English OpenList's comparison
(`eol_subset_<version>.json`). The paper is the rendering of
`PAPER_<version>.template.md` by the card's renderer: a `{{name}}`
placeholder is a row of `rows()`, a `{{table:name}}` placeholder a table of
`tables()`, and the template carries no literal figure
(`release_calcs.template_literals`). Every input is committed, so the paper
re-derives in a fresh clone. No row prints a word of the universe.

    python3 -m research.release.report.paper            print the rows
    python3 -m research.release.report.paper --render   write the paper
    python3 -m research.release.report.paper --check    compare with it
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research.release import columns as C
from research.release import documents as D
from research.release import public_card as P
from research.release import release_calcs as R

VERSION = P.VERSION
REPORT_DIR = Path(__file__).resolve().parent
TEMPLATE = REPORT_DIR / f"PAPER_{VERSION}.template.md"
PAPER = REPORT_DIR / f"PAPER_{VERSION}.md"
ANALYSIS = P.RDIR / "figures" / VERSION / "analysis.json"
#: the related-work section and the references: the site's literature page,
#: whose every claim was confirmed at its source (CLAIMS.csv beside the paper
#: gives each claim's source, locator, and date); the paper and the page share
#: 1 text and 1 numbering of the references
LITERATURE = P.REPO.parent / "site" / "content" / "research" / "literature.md"
CLAIMS = REPORT_DIR / "CLAIMS.csv"

#: short keys for the template's row names
LIST_KEYS = {"WordNet": "wordnet", "Wiktionary (English)": "wiktionary", "hunspell en_US": "hunspell_us",
             "hunspell en_GB": "hunspell_gb", "hunspell en_CA": "hunspell_ca", "hunspell en_AU": "hunspell_au",
             "ENABLE": "enable", "SCOWL": "scowl"}
FAMILY_KEYS = {"WordNet": "wordnet", "Wiktionary": "wiktionary", "hunspell": "hunspell", "ENABLE": "enable",
               "SCOWL": "scowl"}
TIER_KEYS = {"2+ families": "two_plus", "1 family": "one", "corpus only": "corpus", "no evidence": "none",
             "multiword": "multiword"}
BAND_KEYS = {"no value": "none", "under 1": "b0_1", "1 to 2": "b1_2", "2 to 3": "b2_3", "3 to 4": "b3_4",
             "4 to 5": "b4_5", "5 and over": "b5plus"}
FLAG_KEYS = {f: f.replace("-", "_") for f in ("accented", "apostrophe-form", "contraction", "diaeresis",
                                              "hyphenated", "ligature", "s-final", "spaced")}


def _n(x: int) -> str:
    return f"{x:,}"


def _p(part: int, whole: int, digits: int = 1) -> str:
    return "n/a" if not whole else f"{100.0 * part / whole:.{digits}f}%"


def _s(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{100.0 * x:.{digits}f}%"


def _num(x) -> str:
    """A count, or a measure to 2 decimals; a measure that is a whole number
    (a span in years, say) is printed as one."""
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer()):
        return _n(int(x))
    return f"{x:.2f}"


def _card_limitations() -> str:
    """The card's limitations as rendered, below its first line, so the paper
    and the card state them in the same words."""
    card = P.CARD.read_text(encoding="utf-8")
    start = card.index("## 1. Limitations")
    end = card.index("\n## 2.", start)
    body = card[start:end].split("\n", 1)[1].strip()
    lines = body.split("\n")
    if lines and lines[0].startswith("Read these"):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    # the card's sections that its limitations cite, as the paper's sections
    for card_section, paper_section in (("§12", "§11"), ("§6", "§4"), ("§5", "§3")):
        text = text.replace(f"({card_section})", f"({paper_section})")
    return text


def _literature() -> tuple[str, str]:
    """The literature page as the paper's section 2, its headings a level
    down and its opening addressed to a section, and its references."""
    text = LITERATURE.read_text(encoding="utf-8")
    body = text.split("\n", 1)[1].strip()          # below the page's title
    body, refs = body.split("\n## References\n", 1)
    body = body.replace("This page sets", "This section sets", 1)
    lines = [("#" + line) if line.startswith("## ") or line.startswith("### ") else line
             for line in body.split("\n")]
    return "\n".join(lines).strip(), refs.strip()


def _analysis() -> tuple[dict, dict]:
    doc = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if doc["version"] != VERSION:
        raise ValueError(f"{ANALYSIS.name} is of {doc['version']}, not {VERSION}")
    return doc, {e["id"]: e["data"] for e in doc["analyses"]}


def rows() -> dict[str, str]:
    doc, A = _analysis()
    out = dict(P.rows())
    out["card_limitations"] = _card_limitations()
    out["related_resources"], out["references"] = _literature()
    single, multi = doc["rows"]["single_token"], doc["rows"]["multiword"]
    from ceol import grammar as G
    out["grammar_base"] = str(len(G.BASE))
    out["grammar_accented"] = str(len(G.ACCENTED))
    out["grammar_ligatures"] = str(len(G.LIGATURES))
    out["hunspell_dictionaries"] = str(len(doc["list_set"]["families"]["hunspell"]))
    out["family_count"] = str(len(FAMILY_KEYS))
    out["tier_count"] = str(len(doc["tiers"]))
    out["analysis_count"] = str(len(doc["analyses"]))
    out["rows_all"] = _n(doc["rows"]["all"])
    out["rows_single"] = _n(single)
    out["rows_multiword"] = _n(multi)
    out["rows_multiword_pct"] = _p(multi, doc["rows"]["all"])
    for tier, n in doc["rows"]["by_tier"].items():
        k = TIER_KEYS[tier]
        out[f"tier_{k}"] = _n(n)
        out[f"tier_{k}_pct"] = _p(n, single)
    strict = doc["rows"]["by_tier_scowl_and_hunspell_as_1_family"]
    out["strict_two_plus"] = _n(strict["2+ families"])
    out["strict_two_plus_pct"] = _p(strict["2+ families"], single)
    out["strict_two_plus_fewer"] = _n(doc["rows"]["by_tier"]["2+ families"] - strict["2+ families"])
    listed = doc["rows"]["by_tier"]["2+ families"] + doc["rows"]["by_tier"]["1 family"]
    out["rows_listed"] = _n(listed)
    out["rows_listed_pct"] = _p(listed, single)
    out["rows_unlisted"] = _n(single - listed)
    out["rows_unlisted_pct"] = _p(single - listed, single)
    # F1
    for g, v in A["F1"]["by_group"].items():
        k = TIER_KEYS[g]
        q = v["quantiles"]
        for name in ("p10", "p50", "p90", "p99", "max", "min"):
            out[f"len_{k}_{name}"] = _num(q[name])
    out["length_cap"] = str(A["F1"]["length_cap"])
    # F2
    chars = A["F2"]["characters"]
    out["chars_total"] = str(len(chars))
    out["chars_used"] = str(sum(1 for c in chars if sum(c["rows"])))
    for c in chars:
        if c["name"] in ("hyphen", "apostrophe", "space"):
            out[f"char_rows_{c['name']}"] = _n(sum(c["rows"]))
    accented = [c for c in chars if c["character"] not in "abcdefghijklmnopqrstuvwxyz-' "]
    out["char_rows_nonbase_min"] = _n(min(sum(c["rows"]) for c in accented))
    out["char_rows_nonbase_max"] = _n(max(sum(c["rows"]) for c in accented))
    # F4
    for f, v in A["F4"]["rows_by_flag"].items():
        out[f"flag_{FLAG_KEYS[f]}"] = _n(sum(v))
        out[f"flag_{FLAG_KEYS[f]}_pct"] = _p(sum(v), doc["rows"]["all"], 2)
    combos = A["F4"]["combinations"]
    out["class_combinations"] = str(len(combos))
    plain = next(c["rows"] for c in combos if c["classes"] == "plain")
    out["flag_plain"] = _n(plain)
    out["flag_plain_pct"] = _p(plain, doc["rows"]["all"])
    out["flag_any"] = _n(doc["rows"]["all"] - plain)
    # F6
    mw = A["F6"]
    for k, v in mw["sources"].items():
        out["mw_" + {"WordNet and Wiktionary": "both", "WordNet only": "wordnet_only",
                     "Wiktionary only": "wiktionary_only", "neither": "neither"}[k]] = _n(v)
    out["mw_len_p50"] = _num(mw["length_quantiles"]["p50"])
    two_tok = mw["tokens"]["counts"][0]
    out["mw_two_tokens"] = _n(two_tok)
    out["mw_two_tokens_pct"] = _p(two_tok, mw["rows"])
    # F8
    f8 = A["F8"]
    out["apos_rows"] = _n(f8["rows"])
    for k, v in f8["forms"].items():
        out["apos_" + {"contraction": "contraction", "ends in 's": "s_final", "other apostrophe form": "other"}[k]] = _n(sum(v))
    # F9
    f9 = A["F9"]
    out["var_groups"] = _n(f9["groups_of_2_or_more"])
    out["var_rows"] = _n(f9["rows_in_them"])
    out["var_rows_pct"] = _p(f9["rows_in_them"], doc["rows"]["all"])
    out["var_max_size"] = str(max(s["size"] for s in f9["group_sizes"]))
    pairs = f9["pairs_by_members_listed"]
    out["var_pairs"] = _n(sum(pairs.values()))
    out["var_pairs_both"] = _n(pairs["2"])
    out["var_pairs_one"] = _n(pairs["1"])
    out["var_pairs_none"] = _n(pairs["0"])
    for p in f9["patterns"]:
        # a group whose members carry the same kinds of mark in different places
        key = "_".join(p["varies_by"]) or "placement"
        out[f"var_by_{key}"] = _n(p["groups"])
    # S1
    for row in A["S1"]["lists"]:
        k = LIST_KEYS[row["list"]]
        out[f"list_{k}_listed"] = _n(row["listed"])
        out[f"list_{k}_listed_pct"] = _p(row["listed"], single, 2)
        out[f"list_{k}_blind"] = _n(row["cannot_hold"])
    out["mw_wordnet"] = _n(A["S1"]["multiword"]["WordNet"])
    out["mw_wiktionary"] = _n(A["S1"]["multiword"]["Wiktionary (English)"])
    # S2
    s2 = A["S2"]
    keys = [LIST_KEYS[x] for x in s2["lists"]]
    for a, ka in enumerate(keys):
        for b, kb in enumerate(keys):
            if a != b:
                out[f"cont_{ka}_in_{kb}"] = _s(s2["containment"][a][b])
                out[f"blind_{ka}_in_{kb}"] = _s(s2["blind_share"][a][b])
                out[f"jac_{ka}_{kb}"] = f"{s2['jaccard'][a][b]:.3f}" if s2["jaccard"][a][b] is not None else "n/a"
    # S3
    s3 = A["S3"]
    out["s3_rows"] = _n(s3["rows"])
    out["s3_combinations"] = str(len(s3["combinations"]))
    none = next(c["rows"] for c in s3["combinations"] if not c["families"])
    out["s3_none"] = _n(none)
    out["s3_none_pct"] = _p(none, s3["rows"])
    all5 = next((c["rows"] for c in s3["combinations"] if len(c["families"]) == 5), 0)
    out["s3_all5"] = _n(all5)
    out["s3_all5_pct_of_listed"] = _p(all5, s3["rows"] - none)
    wk_only = next((c["rows"] for c in s3["combinations"] if c["families"] == ["Wiktionary"]), 0)
    out["s3_wiktionary_only"] = _n(wk_only)
    # S4 and S13
    for fam, n in A["S4"]["by_family"].items():
        out[f"alone_{FAMILY_KEYS[fam]}"] = _n(n)
        out[f"alone_{FAMILY_KEYS[fam]}_pct_of_listed"] = _p(n, listed)
    for lst, n in A["S4"]["by_list"].items():
        out[f"alone_list_{LIST_KEYS[lst]}"] = _n(n)
    acc = A["S13"]["accumulation"]
    for a in acc:
        k = a["lists"]
        out[f"acc_mean_{k}"] = _n(round(a["mean"]))
        out[f"acc_min_{k}"] = _n(a["min"])
        out[f"acc_max_{k}"] = _n(a["max"])
    out["union_all"] = _n(A["S13"]["union_of_all"])
    # S5
    km = {(r["m"], r["k"]): r["rows"] for r in A["S5"]["overall"]}
    m5 = sum(n for (m, _k), n in km.items() if m == 5)
    out["m5_rows"] = _n(m5)
    for k in range(6):
        out[f"m5_k{k}"] = _n(km.get((5, k), 0))
        out[f"m5_k{k}_pct"] = _p(km.get((5, k), 0), m5)
    m5_listed = m5 - km.get((5, 0), 0)
    out["m5_listed"] = _n(m5_listed)
    out["m5_k1_pct_of_listed"] = _p(km.get((5, 1), 0), m5_listed)
    out["m5_k5_pct_of_listed"] = _p(km.get((5, 5), 0), m5_listed)
    # S6
    s6 = A["S6"]
    for b, n in zip(s6["bands"], s6["rows_per_band"]):
        out[f"band_{BAND_KEYS[b]}_rows"] = _n(n)
    for lst in s6["lists"]:
        k = LIST_KEYS[lst["list"]]
        for b in lst["bands"]:
            bk = BAND_KEYS[b["band"]]
            out[f"cov_{k}_{bk}"] = _s(b["share"])
            if "token_weighted_share" in b:
                out[f"covw_{k}_{bk}"] = _s(b["token_weighted_share"])
    # S8
    s8 = A["S8"]
    out["us_not_gb"] = _n(s8["us_not_gb"])
    out["gb_not_us"] = _n(s8["gb_not_us"])
    out["us_and_gb"] = _n(s8["both"])
    out["proxy_us_not_gb"] = _n(s8["variety_proxies"]["variety_us_not_gb"])
    out["proxy_gb_not_us"] = _n(s8["variety_proxies"]["variety_gb_not_us"])
    # S10
    s10 = A["S10"]
    out["core_rows"] = _n(s10["rows"])
    out["core_pct"] = _p(s10["rows"], single)
    for cls, n in s10["by_class"].items():
        out[f"core_{FLAG_KEYS.get(cls, cls)}"] = _n(n)
    for layer, n in s10["by_intake_layer"].items():
        out[f"core_layer_{layer}"] = _n(n)
    # S14
    s14 = A["S14"]
    out["freq3_unlisted"] = _n(s14["frequent_unlisted"]["zipf 3 and over"]["rows"])
    out["freq4_unlisted"] = _n(s14["frequent_unlisted"]["zipf 4 and over"]["rows"])
    out["listed_no_corpus"] = _n(s14["listed_absent_from_corpora"]["any_list"])
    out["listed_no_corpus_pct"] = _p(s14["listed_absent_from_corpora"]["any_list"], listed)
    # S15
    s15 = A["S15"]
    out["hun_rows"] = _n(s15["rows"])
    out["hun_all4"] = _n(s15["all_4"])
    out["hun_none"] = _n(s15["none"])
    out["hun_some"] = _n(s15["some"])
    out["hun_some_pct_of_listed"] = _p(s15["some"], s15["some"] + s15["all_4"])
    # U1, U3, U5
    for tier, v in A["U1"]["wordfreq_zipf"]["by_tier"].items():
        k = TIER_KEYS[tier]
        out[f"zipf_with_{k}"] = _n(v["with_value"])
        out[f"zipf_with_{k}_pct"] = _p(v["with_value"], v["rows"])
        out[f"zipf_p50_{k}"] = _num(v["quantiles"].get("p50", 0.0)) if v["with_value"] else "n/a"
    for tier, v in A["U1"]["gb_log10_match"]["by_tier"].items():
        k = TIER_KEYS[tier]
        out[f"gb_with_{k}"] = _n(v["with_value"])
        out[f"gb_with_{k}_pct"] = _p(v["with_value"], v["rows"])
        out[f"gb_p50_{k}"] = _num(v["quantiles"].get("p50", 0.0)) if v["with_value"] else "n/a"
    for tier, v in A["U3"]["year_span"]["by_tier"].items():
        k = TIER_KEYS[tier]
        out[f"span_p50_{k}"] = _num(v["quantiles"]["p50"]) if v["with_value"] else "n/a"
    for k, v in A["U5"]["by_families_listing"].items():
        out[f"u5_zipf_p50_k{k}"] = _num(v["wordfreq_zipf"].get("p50", 0.0))
        out[f"u5_gb_p50_k{k}"] = _num(v["gb_log10_match"].get("p50", 0.0))
        out[f"u5_rows_k{k}"] = _n(v["rows"])
    # P1, P2, P4, T3
    flows = A["P1"]["flows"]
    for layer, kinds in flows.items():
        out[f"p1_{layer}"] = _n(sum(sum(g.values()) for g in kinds.values()))
    p2 = A["P2"]
    out["p2_rows"] = _n(p2["rows"])
    for eng, groups in p2["by_engine"].items():
        key = eng.split("/")[-1].replace("-", "_")
        out[f"p2_{key}"] = _n(sum(groups.values()))
        out[f"p2_{key}_listed"] = _n(groups.get("2+ families", 0) + groups.get("1 family", 0))
    p2_listed = sum(g.get("2+ families", 0) + g.get("1 family", 0) for g in p2["by_engine"].values())
    out["p2_listed"] = _n(p2_listed)
    out["p2_listed_pct"] = _p(p2_listed, p2["rows"])
    p4 = A["P4"]
    out["p4_channels"] = str(p4["channels"])
    top = p4["shown"][0]
    out["p4_top_channel"] = top["channel"]
    out["p4_top_rows"] = _n(top["rows"])
    out["p4_top_listed_pct"] = _p(top["listed"], top["rows"])
    t3 = A["T3"]
    out["eol_last_list"] = _n(t3["last_list"])
    out["eol_list_at_pin"] = _n(t3["list_at_pin"])
    out["eol_public_dataset"] = _n(t3["public_dataset"])
    out["eol_held_back"] = _n(t3["of_which_held_back"])
    out["eol_last_revision"] = t3["last_list_revision"]
    return out


def _table(header: list[str], align: list[str], body: list[list[str]]) -> list[str]:
    return (["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
            + ["| " + " | ".join(r) + " |" for r in body])


def tables() -> dict[str, list[str]]:
    doc, A = _analysis()
    out = dict(P.tables())
    single = doc["rows"]["single_token"]
    out["tiers"] = _table(["Evidence tier", "Rows", "Share of single-token rows"], ["---", "---:", "---:"],
                          [[t, _n(n), _p(n, single)] for t, n in doc["rows"]["by_tier"].items()])
    f4 = A["F4"]
    total = doc["rows"]["all"]
    out["flags"] = _table(["Class flag", "Rows", "Share of all rows"], ["---", "---:", "---:"],
                          [[f"`{f}`", _n(sum(v)), _p(sum(v), total, 2)] for f, v in f4["rows_by_flag"].items()])
    out["lists"] = _table(["List", "Listed", "Cannot hold", "Listed, share of single-token rows"],
                          ["---", "---:", "---:", "---:"],
                          [[r["list"], _n(r["listed"]), _n(r["cannot_hold"]), _p(r["listed"], single, 2)]
                           for r in A["S1"]["lists"]])
    s2 = A["S2"]
    short = {"WordNet": "WN", "Wiktionary (English)": "Wikt", "hunspell en_US": "US", "hunspell en_GB": "GB",
             "hunspell en_CA": "CA", "hunspell en_AU": "AU", "ENABLE": "EN", "SCOWL": "SC"}
    out["containment"] = _table(["A, listed by B →"] + [short[x] for x in s2["lists"]], ["---"] + ["---:"] * 8,
                                [[short[a]] + ["—" if i == j else _s(s2["containment"][i][j], 0)
                                              for j in range(8)] for i, a in enumerate(s2["lists"])])
    out["s3"] = _table(["Families that list the row", "Rows"], ["---", "---:"],
                       [[", ".join(c["families"]) or "none", _n(c["rows"])] for c in A["S3"]["combinations"][:12]])
    out["alone"] = _table(["Family", "Rows only it lists", "Share of listed rows"], ["---", "---:", "---:"],
                          [[f, _n(n), _p(n, doc["rows"]["by_tier"]["2+ families"] + doc["rows"]["by_tier"]["1 family"])]
                           for f, n in A["S4"]["by_family"].items()])
    km = {(r["m"], r["k"]): r["rows"] for r in A["S5"]["overall"]}
    ms = sorted({m for m, _k in km})
    out["k_of_m"] = _table(["Families that can hold (m)"] + [f"k = {k}" for k in range(6)], ["---:"] + ["---:"] * 6,
                           [[str(m)] + [_n(km[(m, k)]) if (m, k) in km else "" for k in range(6)] for m in ms])
    s6 = A["S6"]
    bands = [b for b in s6["bands"] if b != "under 1" or any(x["bands"][1]["can_hold"] for x in s6["lists"])]
    def cell(lst, band, key):
        b = next(x for x in lst["bands"] if x["band"] == band)
        return _s(b.get(key), 0) if b.get(key) is not None else ""
    out["coverage"] = _table(["List"] + bands, ["---"] + ["---:"] * len(bands),
                             [[l["list"]] + [cell(l, b, "share") for b in bands] for l in s6["lists"]])
    out["coverage_weighted"] = _table(["List"] + bands[1:], ["---"] + ["---:"] * (len(bands) - 1),
                                      [[l["list"]] + [cell(l, b, "token_weighted_share") for b in bands[1:]]
                                       for l in s6["lists"]])
    out["band_rows"] = _table(["Zipf band", "Single-token rows"], ["---", "---:"],
                              [[b, _n(n)] for b, n in zip(s6["bands"], s6["rows_per_band"]) if n])
    out["accumulation"] = _table(["Lists", "Mean union", "Smallest", "Largest"], ["---:", "---:", "---:", "---:"],
                                 [[str(a["lists"]), _n(round(a["mean"])), _n(a["min"]), _n(a["max"])]
                                  for a in A["S13"]["accumulation"][1:]])
    out["variants"] = _table(["Varies by", "Groups"], ["---", "---:"],
                             [[", ".join(p["varies_by"]) or "the same marks, placed differently", _n(p["groups"])]
                              for p in A["F9"]["patterns"][:10]])
    out["u5"] = _table(["Families listing", "Rows", "Median Zipf", "Median log10 Google Books matches"],
                       ["---:", "---:", "---:", "---:"],
                       [[k, _n(v["rows"]), _num(v["wordfreq_zipf"].get("p50", 0.0)),
                         _num(v["gb_log10_match"].get("p50", 0.0))] for k, v in A["U5"]["by_families_listing"].items()])
    lengths = A["F1"]["by_group"]
    out["lengths"] = _table(["Group", "Rows", "10th percentile", "Median", "90th percentile", "Longest"],
                            ["---", "---:", "---:", "---:", "---:", "---:"],
                            [[g, _n(v["rows"]), _num(v["quantiles"]["p10"]), _num(v["quantiles"]["p50"]),
                              _num(v["quantiles"]["p90"]), _num(v["quantiles"]["max"])] for g, v in lengths.items()])
    p4 = A["P4"]
    out["channels"] = _table(["Intake channel", "Rows", "Listed by a family", "In a corpus"],
                             ["---", "---:", "---:", "---:"],
                             [[f"`{c['channel']}`", _n(c["rows"]), _p(c["listed"], c["rows"]), _p(c["in_a_corpus"], c["rows"])]
                              for c in p4["shown"][:12]])
    p2 = A["P2"]
    out["engines"] = _table(["Engine, as inferred", "Rows", "Listed by a family"], ["---", "---:", "---:"],
                            sorted(([e, _n(sum(g.values())), _n(g.get("2+ families", 0) + g.get("1 family", 0))]
                                    for e, g in p2["by_engine"].items()), key=lambda r: -int(r[1].replace(",", ""))))
    flows = A["P1"]["flows"]
    out["flows"] = _table(["Intake layer", "Kind", "2+ families", "1 family", "Corpus only", "No evidence", "Multiword"],
                          ["---", "---", "---:", "---:", "---:", "---:", "---:"],
                          [[f"`{layer}`", kind] + [_n(g.get(t, 0)) for t in ("2+ families", "1 family", "corpus only", "no evidence", "multiword")]
                           for layer, kinds in flows.items() for kind, g in kinds.items()])
    for key, (title, cols) in D.public_tables().items():
        out[f"columns_{key}"] = C.markdown_table(cols)
    out["columns_features"] = C.markdown_table(D.features_columns())
    return out


def render() -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    literal = R.template_literals(template)
    if literal:
        raise ValueError(f"the paper's template carries literal figures: {literal[:8]}")
    return R.render(template, rows(), tables())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.render or args.check:
        try:
            text = render()
        except (KeyError, ValueError) as exc:
            print(f"[paper] {exc}", file=sys.stderr)
            return 1
        if args.check:
            if not PAPER.exists() or PAPER.read_text(encoding="utf-8") != text:
                print(f"[paper] {PAPER.name} is not the rendering of its template", file=sys.stderr)
                return 1
            print(f"[paper] {PAPER.name} is the rendering of its template")
            return 0
        PAPER.write_text(text, encoding="utf-8")
        print(f"[paper] {PAPER.name} rendered, {len(text.split()):,} words")
        return 0
    for name, value in rows().items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
