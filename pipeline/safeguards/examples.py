"""The builder of the vetted example list (PLAN.md §2: "Example strings on
public pages come only from a vetted list: shippable rows that are not study
items"). The rule is the owner's, the floor
per class is his too (D-008, line 1), and so are the source families (D-010,
line 6).

A string is eligible when all 3 hold:

1. it is a row of the shippable projection, the universe config of the
   release named by `--version`;
2. at least `MIN_FAMILIES` source families list it, among the published
   panel sets (`research.release.withholding.PUBLISHED_SETS`: the panel
   without the withheld lists). SCOWL and the en_US, en_CA, and en_AU
   hunspell dictionaries are 1 family, because those 3 "come directly from
   SCOWL" (their READMEs); every
   other published set, en_GB included, is a family of its own;
3. the scan finds nothing in it: no item of the study's wall list as a whole
   word or phrase, and no restricted word as a piece.

    python3 -m safeguards.examples            from pipeline/; or `make examples`
    python3 -m safeguards.examples --check    rebuild in memory and compare

What is built:

- **The whole list,** in `private/examples/`, which git ignores, with a
  summary of its size.
- **The repository's list,** `examples/vetted_examples.txt` with
  `examples/MANIFEST.json`: the first `SUBSET` strings of a hash ranking of
  the whole list, then a floor per class. The eligible strings are ranked by
  `sha256(key:STRATUM:string)` in ascending order, with a random key kept in
  `private/keys/` (`safeguards.keys`; D-012 line 3): with a public seed,
  anyone could recompute the ranking and find the strings the scan passed
  over. The draw takes the first
  `SUBSET`; then, for every class (`class_explicit`) the draw holds fewer
  than `FLOOR` of, the next strings of the same ranking are added until the
  class holds `FLOOR`, or all of its strings where the whole list holds
  fewer. Lines 1 to `SUBSET` are the draw, and the lines after them are the
  floor's strings; the floor's strings lie further down the ranking than any
  drawn string, so the whole file keeps the ranking's order. A string is
  passed over where the file, read as 1 text the way the scan reads it,
  would spell a walled phrase across 2 lines; a phrase that would start in
  the draw and end in the floor passes over the floor's string.

The command prints counts and never a string.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from safeguards import keys, locations, restricted, wall

#: the public version whose universe the list is drawn from (D-012 line 3:
#: the list is drawn again from the files v2.1 ships)
VERSION = "v2.1"
MIN_FAMILIES = 2
SUBSET = 5_000
#: the strings of each class the file holds at least, or all of the class's
#: strings where the whole list holds fewer (D-008, line 1)
FLOOR = 20
#: the stated rule; the key itself is private (D-012 line 3)
RULE = ("the eligible strings ranked by sha256(key:stratum:string) in "
        "ascending order, with a random key kept privately; the first N taken; "
        "a string passed over where the file, read as 1 text, would spell a "
        "walled phrase across 2 lines")
#: the ranking has the form of the kit's sampler, with 1 stratum
STRATUM = "all"

LIST_REL = "examples/vetted_examples.txt"
MANIFEST_REL = "examples/MANIFEST.json"

#: a line that no term can match across: neither a letter nor whitespace
_FENCE = "|"


def clean_mask(strings: list[str], terms: set[str], words: set[str]) -> list[bool]:
    """For each string, whether the scan finds nothing in it. The strings
    are read as 1 text with a fence line between them, so that a spaced term
    cannot match across 2 rows."""
    text = f"\n{_FENCE}\n".join(strings)
    dirty: set[int] = set()
    for line in wall.Matcher(terms).hit_lines(text):
        dirty.add((line - 1) // 2)
    for line in restricted.hit_lines(wall.canon(text), words):
        dirty.add((line - 1) // 2)
    return [i not in dirty for i in range(len(strings))]


#: the published panel sets of the SCOWL family: SCOWL and the 3 hunspell
#: dictionaries built from it (D-010, line 6)
SCOWL_FAMILY: tuple[str, ...] = ("scowl", "hunspell_en_US", "hunspell_en_CA",
                                 "hunspell_en_AU")


def family(panel_set: str) -> str:
    """The source family of a panel set. SCOWL and the en_US, en_CA, and en_AU
    dictionaries are 1 family, named `scowl`: the 3 dictionaries are SCOWL's
    own lists. en_GB, which began from Kevin Atkinson's list and has been
    extensively changed by others since, is its own family (D-010, line 6)."""
    return "scowl" if panel_set in SCOWL_FAMILY else panel_set


def families(panel_sets: str) -> set[str]:
    """The source families of a row's published sets."""
    return {family(name) for name in panel_sets.split(";") if name}


def published_families() -> dict[str, list[str]]:
    """Each source family with the published panel sets it holds."""
    from research.release import withholding
    out: dict[str, list[str]] = {}
    for name in withholding.PUBLISHED_SETS:
        out.setdefault(family(name), []).append(name)
    return out


def eligible(release_dir: Path, terms: set[str], words: set[str]) -> tuple[list[dict], dict]:
    """The eligible rows, in the release's order, and the counts at each
    step of the rule."""
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from research.release import withholding

    table = pq.read_table(release_dir / "universe.parquet", columns=[
        "word", "panel_sets", "token_count", "class_explicit", "is_restricted"])
    counts = {"rows_of_the_universe_config": table.num_rows,
              "restricted_rows": int(pc.sum(table["is_restricted"]).as_py() or 0)}
    encoded = pc.dictionary_encode(table["panel_sets"]).combine_chunks()
    published = [withholding.published_panel_sets(v)
                 for v in encoded.dictionary.to_pylist()]
    n_families = np.array([len(families(v)) for v in published])
    listed = n_families[encoded.indices.to_numpy(zero_copy_only=False)] >= MIN_FAMILIES
    listed &= ~table["is_restricted"].to_numpy(zero_copy_only=False)
    counts[f"listed_by_at_least_{MIN_FAMILIES}_source_families"] = int(listed.sum())
    index = np.flatnonzero(listed)
    kept = table.take(index)
    strings = kept["word"].to_pylist()
    mask = clean_mask(strings, terms, words)
    counts["removed_by_the_scan"] = mask.count(False)
    counts["eligible"] = mask.count(True)
    published_of_row = [published[i] for i in
                        encoded.indices.to_numpy(zero_copy_only=False)[index]]
    rows = [{"word": w, "token_count": t, "class_explicit": c, "panel_sets": p}
            for w, t, c, p, ok in zip(strings, kept["token_count"].to_pylist(),
                                      kept["class_explicit"].to_pylist(),
                                      published_of_row, mask) if ok]
    return rows, counts


def ranking_key(string: str, key: str | None = None) -> bytes:
    key = key or keys.key("examples")
    return hashlib.sha256(f"{key}:{STRATUM}:{string}".encode("utf-8")).digest()


def ranked(rows: list[dict]) -> list[dict]:
    """The rows in ascending order of their ranking keys."""
    key = keys.key("examples")
    return sorted(rows, key=lambda r: ranking_key(r["word"], key))


def draw(strings: list[str], n: int, terms: set[str],
         path: str = LIST_REL) -> tuple[list[int], int]:
    """The positions in `strings`, a ranking, of the first `n` strings the
    scan passes as 1 file, and the count of strings passed over.

    Each string is clean by itself. Read as 1 text, 2 or more lines in a row
    can still spell a spaced term, and the scan reads the file's path as the
    line before the first. The string on whose line such a match starts is
    passed over (the first string, where the match starts in the path), and
    the next string of the ranking is taken."""
    matcher = wall.Matcher(terms)
    taken = list(range(min(n, len(strings))))
    upcoming = len(taken)
    passed_over = 0
    while True:
        text = wall.canon(path + "\n" + "\n".join(strings[i] for i in taken))
        drop: set[int] = set()
        for start, end, _term in matcher.spans(text):
            first, last = text.count("\n", 0, start), text.count("\n", 0, end)
            if first == last:
                raise ValueError("the scan finds a term inside 1 line of the "
                                 "list: the path, or a string that is not clean")
            drop.add(max(first, 1) - 1)
        if not drop:
            break
        for position in sorted(drop, reverse=True):
            del taken[position]
        passed_over += len(drop)
        while len(taken) < n and upcoming < len(strings):
            taken.append(upcoming)
            upcoming += 1
    if len(taken) < n:
        raise ValueError(f"the ranking holds fewer than {n} strings the scan passes")
    return taken, passed_over


def floor_additions(order: list[dict], positions: list[int], terms: set[str],
                    floor: int = FLOOR, path: str = LIST_REL) -> tuple[list[int], int]:
    """The positions in `order`, a ranking of rows, of the strings the floor
    adds after the draw at `positions`, and the count of strings passed over.

    A class the draw holds fewer than `floor` of gets the next strings of the
    ranking, after the draw's last position, until it holds `floor` or every
    string of the class that the ranking holds after that position. The file, read as 1 text with its path first, must
    spell no walled phrase across 2 lines; where a phrase reaches into the
    floor's lines, the floor's string on the first such line is passed over
    and the next of its class is taken. The draw's lines never change."""
    have = Counter(order[i]["class_explicit"] for i in positions)
    start = max(positions) + 1 if positions else 0
    # the strings the floor may take: those after the draw's last position
    after = Counter(r["class_explicit"] for r in order[start:])
    need = {c: min(floor - have[c], n) for c, n in after.items() if have[c] < floor}
    drawn_text = path + "\n" + "\n".join(order[i]["word"] for i in positions)
    matcher = wall.Matcher(terms)
    excluded: set[int] = set()
    while True:
        added: list[int] = []
        filled: Counter = Counter()
        for i in range(start, len(order)):
            if not need or all(filled[c] >= n for c, n in need.items()):
                break
            c = order[i]["class_explicit"]
            if i not in excluded and filled[c] < need.get(c, 0):
                added.append(i)
                filled[c] += 1
        short = {c: n - filled[c] for c, n in need.items() if filled[c] < n}
        if short:
            raise ValueError(f"the floor cannot be met for {len(short)} class(es)")
        text = wall.canon(drawn_text + "".join("\n" + order[i]["word"] for i in added))
        drop: set[int] = set()
        for begin, end, _term in matcher.spans(text):
            first, last = text.count("\n", 0, begin), text.count("\n", 0, end)
            if first == last:
                raise ValueError("the scan finds a term inside 1 line of the "
                                 "list: the path, or a string that is not clean")
            floor_lines = [line for line in range(max(first, 1), last + 1)
                           if line > len(positions)]
            if not floor_lines:
                raise ValueError("the scan finds a phrase across the draw's "
                                 "own lines, which the draw passes over")
            drop.add(added[floor_lines[0] - len(positions) - 1])
        if not drop:
            return added, len(excluded)
        excluded |= drop


def _tokens(row: dict) -> str:
    return "1" if row["token_count"] == 1 else \
        "2" if row["token_count"] == 2 else "3 or more"


def _count(values) -> dict[str, int]:
    """The count of each value, the largest first and then by name."""
    return dict(sorted(Counter(values).items(), key=lambda kv: (-kv[1], kv[0])))


def sizes(rows: list[dict]) -> dict:
    """The size of a list of rows by class, by token count, and by the
    source families that list each row."""
    return {
        "strings": len(rows),
        "by_class": _count(r["class_explicit"] for r in rows),
        "by_token_count": dict(sorted(Counter(map(_tokens, rows)).items())),
        "by_source_family_count": dict(sorted(Counter(
            str(len(families(r["panel_sets"]))) for r in rows).items())),
        "by_source_families": _count(
            ";".join(sorted(families(r["panel_sets"]))) for r in rows),
    }


def summary(rows: list[dict], counts: dict, version: str) -> dict:
    """The size of the whole list, for `private/examples/`."""
    return {
        "what": "the size of the whole vetted example list as built; the "
                "list is private/examples/vetted_examples.txt, and the "
                f"repository holds a subset of it ({LIST_REL})",
        "release": version,
        "rule": {"min_source_families": MIN_FAMILIES,
                 "source_families": published_families()},
        "counts": counts,
        **sizes(rows),
    }


def build(version: str = VERSION) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """The repository's files and the private files, as bytes keyed by their
    paths under the repository and under `private/`."""
    release_dir = locations.data_dir() / "release" / f"ceol-universe-{version}"
    record = json.loads((locations.REPO / "pipeline" / "research" / "release" /
                         f"release_{version}.json").read_text(encoding="utf-8"))
    universe = {f["config"]: f for f in record["files"]}["universe"]
    universe_sha = hashlib.sha256(
        (release_dir / "universe.parquet").read_bytes()).hexdigest()
    if universe_sha != universe["sha256"]:
        raise SystemExit("data/release: universe.parquet is not the file the "
                         "release record names")
    terms, words = wall.all_terms(), restricted.restricted_words()
    rows, counts = eligible(release_dir, terms, words)
    if counts["rows_of_the_universe_config"] != universe["rows"] \
            or counts["restricted_rows"]:
        raise SystemExit("the universe config is not the shippable projection")

    whole = "\n".join(sorted(r["word"] for r in rows)) + "\n"
    whole_summary = summary(rows, counts, version)
    whole_summary["list_sha256"] = hashlib.sha256(whole.encode("utf-8")).hexdigest()

    order = ranked(rows)
    positions, passed_over = draw([r["word"] for r in order], SUBSET, terms)
    subset = [order[i] for i in positions]
    added, floor_passed_over = floor_additions(order, positions, terms)
    floor_rows = [order[i] for i in added]
    listed = subset + floor_rows
    listing = ("\n".join(r["word"] for r in listed) + "\n").encode("utf-8")
    # the file as the scan will read it: its path, then its text
    hits = wall.Matcher(terms).hits(LIST_REL + "\n" + listing.decode("utf-8"))
    hits |= restricted.find_hits(LIST_REL + "\n" + listing.decode("utf-8"), words)
    if hits:
        raise SystemExit("the scan finds a term in the list as built")

    from research.release import withholding
    manifest = {
        "what": "the vetted example list of the repository: the only strings "
                "a page may show as examples (the project's example rule). "
                "A string of the list is a candidate, listed "
                "by the sources its rule names",
        "built_by": "pipeline/safeguards/examples.py (make examples)",
        "source": {"version": version, "config": "universe",
                   "sha256": universe_sha, "rows": universe["rows"]},
        "rule": {
            "row": "a row of the shippable projection",
            "min_source_families": MIN_FAMILIES,
            "source_families": published_families(),
            "not_counted": list(withholding.WITHHELD_SETS),
            "scan": "the scan finds nothing in the string: no item of the "
                    "study's wall list as a whole word or phrase, and no "
                    "restricted word as a piece",
        },
        "counts": counts,
        "whole_list": {"where": "private/examples/vetted_examples.txt, never "
                                "committed", **sizes(rows)},
        "sampling": {
            "rule": RULE, "key": "private (D-012 line 3)",
            "stratum": STRATUM, "strings": SUBSET,
            "strings_passed_over": passed_over,
            "order": "lines 1 to N are the draw, in the ranking's order",
        },
        "drawn": sizes(subset),
        "floor": {
            "rule": "for every class the draw holds fewer than the floor of, "
                    "the next strings of the same ranking, until the class "
                    "holds the floor or all of its strings; lines 1 to N stay "
                    "as drawn, the floor's strings follow in the ranking's "
                    "order, and a phrase reaching into the floor's lines "
                    "passes over the floor's string",
            "per_class": FLOOR, "strings_added": len(floor_rows),
            "strings_passed_over": floor_passed_over,
            "by_class_added": _count(r["class_explicit"] for r in floor_rows),
        },
        "list": sizes(listed),
        "file": {"name": Path(LIST_REL).name,
                 "sha256": hashlib.sha256(listing).hexdigest(),
                 "bytes": len(listing), "lines": len(listed)},
    }
    repository = {
        LIST_REL: listing,
        MANIFEST_REL: (json.dumps(manifest, indent=1, ensure_ascii=False)
                       + "\n").encode("utf-8"),
    }
    private = {
        "examples/vetted_examples.txt": whole.encode("utf-8"),
        "examples/vetted_examples.json":
            (json.dumps(whole_summary, indent=1) + "\n").encode("utf-8"),
    }
    return repository, private


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", default=VERSION)
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the "
                         "repository's files")
    args = ap.parse_args(argv)
    repository, private = build(args.version)
    differing = []
    for rel, data in sorted(repository.items()):
        path = locations.REPO / rel
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                differing.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if not args.check:
        for rel, data in sorted(private.items()):
            path = locations.private_dir() / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(repository[MANIFEST_REL].decode("utf-8"), end="")
    for rel in differing:
        print(f"DIFFERS {rel}")
    return 1 if differing else 0


if __name__ == "__main__":
    raise SystemExit(main())
