"""Render the profile page of a version of the CEOL Universe from
`profile.json`, `pos_estimate.json`, and the column tables of
`research/release/columns.py` (C-078 line 10; PACKAGE_UR1.md §5).

Every figure on the page is read from the 2 JSON files, which
universe_profile.py and pos_estimate.py computed from the release files;
nothing numeric is typed here. The plots are referenced as files under
`plots/` beside the page, never embedded as data. No word of the universe
appears: the JSON holds counts and labels only. The page is written to the
path given and is neither committed nor published by the release seat
(reading R17).

Run:  python3 -m research.release.profile.build_profile_page --version v2.0 --out PAGE.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from research.release import columns as C

HERE = Path(__file__).resolve().parent


def n(x) -> str:
    return f"{x:,.3f}" if isinstance(x, float) else f"{x:,}"


def pct(a: int, b: int) -> str:
    return f"{100.0 * a / b:.2f}%" if b else "n/a"


def esc(s) -> str:
    return html.escape(str(s))


def table(headers, rows) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = ""
    for r in rows:
        cells = []
        for c in r:
            numeric = isinstance(c, (int, float)) or (
                isinstance(c, str) and re.fullmatch(r"[0-9,.%\- ]+", c or "x"))
            text = n(c) if isinstance(c, (int, float)) else c
            cells.append(("<td class=\"n\">" if numeric else "<td>")
                         + esc(text) + "</td>")
        body += "<tr>" + "".join(cells) + "</tr>"
    return (f'<div class="scroller"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def dist(d: dict, total: int | None = None, numeric: bool = False) -> list:
    items = list(d.items())
    if numeric:
        items.sort(key=lambda kv: float(kv[0]) if re.fullmatch(
            r"-?[0-9.]+", kv[0]) else 1e18)
    else:
        items.sort(key=lambda kv: (-kv[1], kv[0]))
    return [[k if k != "" else "(empty)", v]
            + ([pct(v, total)] if total else []) for k, v in items]


def img(profile: dict, name: str) -> str:
    if name not in profile["plots"]:
        return ""           # a plot of a column the version withholds
    title = profile["plots"][name]["title"]
    return (f'<figure><img src="plots/{esc(name)}" alt="{esc(title)}" '
            f'loading="lazy"><figcaption>{esc(title)}</figcaption></figure>')


def column_table(key: str) -> str:
    title, cols = C.TABLES[key]
    return f"<h3>{esc(title)}</h3>" + table(
        ["column", "type", "meaning", "null"], [list(c) for c in cols])


CSS = """
:root{--bg:#FBFBF9;--ink:#20272E;--muted:#5B6670;--rule:#E2E5E3;--accent:#0B6E68;--card:#F3F5F3;--chip:#E6F2F1;--warn:#8A5A00;--warnbg:#FBF1DC}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15191C;--ink:#DCE2E5;--muted:#A3ADB5;--rule:#2A3136;--accent:#54B8B1;--card:#1B2024;--chip:#1B2A2A;--warn:#E3B45A;--warnbg:#2A2415;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#15191C;--ink:#DCE2E5;--muted:#A3ADB5;--rule:#2A3136;--accent:#54B8B1;--card:#1B2024;--chip:#1B2A2A;--warn:#E3B45A;--warnbg:#2A2415;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:"Source Serif 4",Georgia,serif;font-size:17px;line-height:1.55;padding-inline:clamp(16px,4vw,40px);padding-block:32px 64px;margin:0}
main{max-width:50rem;margin:0 auto}
h1,h2,h3{font-weight:600;line-height:1.2;margin:0}
h1{font-size:clamp(1.8rem,4.5vw,2.4rem);margin-top:0.4rem}
h2{font-size:1.35rem;margin-top:2.6rem;padding-top:0.9rem;border-top:1px solid var(--rule)}
h3{font-size:1.05rem;margin-top:1.5rem}
p{margin:0.75rem 0;max-width:68ch}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:0.76rem;letter-spacing:0.08em;text-transform:uppercase;color:var(--muted)}
code{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:0.86em;background:var(--card);padding:0.05em 0.3em;border-radius:3px;overflow-wrap:anywhere}
.chips{list-style:none;padding:0;margin:1rem 0 0;display:flex;flex-wrap:wrap;gap:0.4rem}
.chips li{background:var(--chip);font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:0.78rem;padding:0.3rem 0.6rem;border-radius:3px;white-space:normal;overflow-wrap:anywhere}
.chips li.warn{background:var(--warnbg);color:var(--warn)}
.callout{background:var(--card);border-left:3px solid var(--accent);padding:0.8rem 1rem;margin:1.2rem 0}
.scroller{overflow-x:auto;margin:0.8rem 0 1.2rem;border:1px solid var(--rule);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:0.86rem}
th,td{padding:0.4rem 0.6rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}
td.n{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:0.82rem;text-align:right}
thead th{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-weight:500;font-size:0.72rem;letter-spacing:0.05em;text-transform:uppercase;color:var(--muted);background:var(--card);white-space:nowrap}
figure{margin:1rem 0;max-width:100%}
figure img{max-width:100%;height:auto;border:1px solid var(--rule);border-radius:6px;background:#fff}
figcaption{font-size:0.82rem;color:var(--muted);margin-top:0.3rem}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--rule);font-size:0.86rem;color:var(--muted)}
"""


def render(profile: dict, pos: dict) -> str:
    U, F, cfg = profile["universe"], profile["features"], profile["configs"]
    V, E, L = U["provenance"], U["evidence"], U["limits"]
    rows = U["rows"]
    version = profile["version"]
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CEOL Universe Profile</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style></head><body><main>
<div class="eyebrow">The CEOL Universe · version {esc(version)} · profiled from its release files</div>
<h1>The CEOL Universe, Profiled</h1>
<p>What version {esc(version)} of the CEOL Universe holds, column by column, computed from the release files by <code>universe_profile.py</code> and <code>pos_estimate.py</code> and rendered from their JSON, so every figure here was computed and none was typed. The universe is a candidate inventory: being a row says a string was listed by a pinned source or inherited from the EOL, and nothing here says a string is valid. No word of the universe appears on this page.</p>
<ul class="chips">
<li>{n(rows)} rows, {n(U["distinct_words"])} distinct strings, {n(U["columns"])} columns</li>
<li>{n(U["token_count"]["1"])} single-token rows; {n(cfg["spaced"])} multiword rows</li>
<li>{n(cfg["eol-valid"])} in the EOL valid list at the pin ({pct(cfg["eol-valid"], rows)})</li>
<li>{n(cfg["panel-listed"])} rows listed by a panel set</li>
<li>{n(V["intake_kind"]["generated"])} rows made by the EOL's lost engine, each labeled</li>
<li class="warn">{n(L["gb_type_inherited_no_panel_set"])} inherited single-token rows are Google Books types that no panel set lists</li>
</ul>"""]
    fr = [[name, f["rows"], f["columns"], f["bytes"], f["sha256"][:16] + "…"]
          for name, f in profile["files"].items()]
    parts.append("<h2>1. The files</h2>" + table(
        ["config", "rows", "columns", "bytes", "sha256"], fr))
    parts.append("<h2>2. The columns</h2>" + "".join(
        column_table(k) for k in ("key", "pin", "release", "provenance",
                                  "evidence")))
    parts.append("<h3>Nulls per column</h3>" + table(
        ["column", "null rows", "share"],
        [[k, v, pct(v, rows)] for k, v in U["nulls"].items() if v]))
    parts.append("<h3>The boolean columns</h3>" + table(
        ["column", "true", "false", "null"],
        [[c, U[c].get("true", 0), U[c].get("false", 0), U[c].get("null", 0)]
         for c in ("eol", "eol_universe", "c4_addition", "is_restricted",
                   "c015_addition", "wn_instance", "wn_capitalized",
                   "wk_proper_noun", "variety_gb_not_us",
                   "variety_us_not_gb", "gb_type", "wordfreq_scored",
                   "wikt_title_any")]))
    parts.append("<h3>Tokens per row</h3>" + table(
        ["tokens", "rows", "of which in the EOL valid list"],
        [[k, v["rows"], v["eol"]] for k, v in sorted(
            U["eol_by_token_count"].items(), key=lambda kv: int(kv[0]))])
        + img(profile, "token_count.png"))
    parts.append("<h3>Intake dates</h3>" + table(
        ["intake_date", "rows"], dist(U["intake_date"]))
        + img(profile, "intake_date.png"))
    parts.append("<h3>The grammar classes</h3>" + table(
        ["class flag", "rows carrying it"], dist(U["classes_per_label"]))
        + table(["class_explicit", "rows", "of which in the EOL valid list"],
                [[k, v["rows"], v["eol"]] for k, v in sorted(
                    U["eol_by_class_explicit"].items(),
                    key=lambda kv: (-kv[1]["rows"], kv[0]))])
        + img(profile, "classes.png"))
    parts.append("<h3>The sources column</h3>" + table(
        ["source label", "rows"], dist(U["sources_per_label"]))
        + table(["labels on the row", "rows"],
                dist(U["sources_per_row"], numeric=True))
        + img(profile, "sources_per_label.png")
        + img(profile, "sources_per_row.png"))
    q = U["length"]["quantiles"]["q"]
    cu = U["character_use"]
    parts.append("<h2>3. The shape of the strings</h2>" + table(
        ["measure", "value"],
        [["length in characters, mean", U["length"]["quantiles"]["mean"]],
         ["median", f"{q['p50']:.0f}"],
         ["p5 / p95 / p99", f"{q['p5']:.0f} / {q['p95']:.0f} / "
                            f"{q['p99']:.0f}"],
         ["minimum / maximum", f"{q['min']:.0f} / {q['max']:.0f}"]])
        + img(profile, "length_by_eol.png") + table(
        ["rows whose string contains", "rows", "share"],
        [["only the letters a to z", cu["ascii_letters_only"],
          pct(cu["ascii_letters_only"], rows)],
         ["a space", cu["space"], pct(cu["space"], rows)],
         ["a hyphen", cu["hyphen"], pct(cu["hyphen"], rows)],
         ["an apostrophe", cu["apostrophe"], pct(cu["apostrophe"], rows)],
         ["an accented letter", cu["accented_letter"],
          pct(cu["accented_letter"], rows)],
         ["a ligature", cu["ligature"], pct(cu["ligature"], rows)]])
        + img(profile, "first_char.png"))
    parts.append("<h2>4. The panel sets and the evidence</h2>" + table(
        ["panel set", "single-token rows listed", "share"],
        [[k, E["listed"][k], pct(E["listed"][k], E["rows"])]
         for k in C.PANEL_SETS]) + img(profile, "per_detector.png")
        + table(["panel sets listing the row", "rows",
                 "of which in the EOL valid list"],
                [[k, v["rows"], v["eol"]] for k, v in sorted(
                    U["eol_by_panel_count"].items(),
                    key=lambda kv: int(kv[0]))])
        + img(profile, "panel_sets.png"))
    parts.append("<h2>5. The intake provenance</h2>" + table(
        ["intake layer", "rows", "share"], dist(V["intake_layer"], rows))
        + table(["provenance class", "rows", "share"],
                dist(V["provenance_class"], rows))
        + table(["layer", "obtained", "derived", "generated"],
                [[k, d.get("obtained", 0), d.get("derived", 0),
                  d.get("generated", 0)]
                 for k, d in V["layer_by_kind"].items()])
        + img(profile, "prov_layer.png") + img(profile, "prov_kind.png")
        + img(profile, "prov_class.png")
        + table(["channel label", "rows"],
                dist(V["intake_channels_per_label"])))
    frows = []
    for c, v in F["columns"].items():
        qq = v.get("quantiles")
        if qq:
            frows.append([c, v["type"], qq["n"], f"{qq['mean']:.3f}",
                          f"{qq['q']['p50']:.3f}",
                          f"{qq['q']['min']:.3f} to {qq['q']['max']:.3f}"])
        else:
            frows.append([c, v["type"], "", "", "", "; ".join(
                f"{k} {n(x)}" for k, x in v["values"].items())])
    parts.append("<h2>6. The features config</h2>" + column_table("features")
                 + table(["column", "type", "rows with a value", "mean",
                          "median", "range or values"], frows)
                 + img(profile, "feature_wordfreq_zipf.png")
                 + img(profile, "feature_gb_log10_match.png")
                 + img(profile, "feature_orthotactic_logp_per_char.png"))
    pcmb = pos["pos_combination"]
    parts.append(
        "<h2>7. Parts of speech: what a single pinned source would cover</h2>"
        f"<p>The universe records no part of speech. From WordNet "
        f"{esc(pos['wordnet_version'])} alone, over the "
        f"{n(pos['wordnet_listed_rows'])} rows WordNet lists "
        f"({pct(pos['wordnet_listed_rows'], rows)} of the rows):</p>"
        + table(["part-of-speech set", "rows", "of which in the EOL valid "
                 "list"], [[k, v, pos["pos_combination_eol"].get(k, 0)]
                           for k, v in sorted(pcmb.items(),
                                              key=lambda kv: (-kv[1],
                                                              kv[0]))]))
    parts.append(
        "<h2>8. The limitation stated first</h2><p>"
        f"{n(L['gb_type_inherited_no_panel_set'])} single-token rows are "
        "strings inherited from the EOL that are Google Books 1-gram types "
        "and that none of the 13 panel sets lists; "
        f"{n(L['gb_type_rows'])} rows in all are Google Books types. "
        f"{n(L['single_token_no_panel_set_no_corpus'])} single-token rows "
        "are listed by no panel set and are in neither corpus.</p>")
    parts.append(
        f"<footer>Rendered by <code>build_profile_page.py</code> from the "
        f"profile of version {esc(version)}. No candidate word, control, "
        "probe item, or pilot word is printed on this page.</footer>"
        "</main></body></html>")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--profile-dir", type=Path, default=HERE)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    profile = json.loads((args.profile_dir / "profile.json").read_text(
        encoding="utf-8"))
    pos = json.loads((args.profile_dir / "pos_estimate.json").read_text(
        encoding="utf-8"))
    if profile["version"] != args.version or pos["version"] != args.version:
        print(f"[page] the profile is not version {args.version}",
              file=sys.stderr)
        return 1
    args.out.write_text(render(profile, pos), encoding="utf-8")
    print(f"[page] {args.out.stat().st_size:,} bytes written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
