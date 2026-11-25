"""The open subset of a public version: its rows that open word lists list,
in the columns those lists and Google Books give.

    python3 -m research.release.open_subset --out DIR          build into DIR
    python3 -m research.release.open_subset --out DIR --check  rebuild in
                                                               memory and compare

It reads the version's `universe.parquet` and committed `NOTICES` file,
each held to the sha256 its release record names, and writes into DIR the
files of the Hugging Face dataset `ceol-universe-open`: `README.md` (the
card), `NOTICES.md`, and one Parquet file per config under `data/`. It
writes its own record, `research/release/open_subset_<version>.json`.

The open lists are WordNet 3.0, the English Wiktionary, the en_US, en_CA,
and en_AU hunspell dictionaries, and SCOWL's lists of sizes 10 to 70. A
row of the version is in the subset when one of them lists it. The version
supplies the candidate rows; within them, every column and every config's
predicate is a function of those lists and of Google Books' types, and no
other field of the version is read for a row's membership or values. (On a
multiword row, which list holds it is read from the column only that list
fills: `wn_instance` for WordNet, `wk_flags` for the English Wiktionary.)
The configs:

- `open-lists` (the default): every row of the version that an open list
  lists;
- `wordnet-wiktionary`: the rows WordNet or the English Wiktionary lists,
  in the columns derived from those 2 alone;
- `sample`: the rows of `open-lists` whose `id` begins with `00`.

The build asserts, on the files it wrote and re-read, that each config is
its predicate's filter of the version's rows and nothing else; that every
value but `scowl_size`, `list_count`, and `listed_by` equals the version's
value for that row; that `scowl_size` never names a size above 70; that
`listed_by` names exactly the lists the version's own columns name; that no
other column of the version is present; and that every id is distinct and
is the string's own hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from string import Template

from ceol.ingest.common import sha256_file

REPO = Path(__file__).resolve().parents[2]
RELEASE_DIR = REPO / "research" / "release"
DATA_RELEASE = REPO / "data" / "release"

VERSION = "v1.0"
DATASET = "ryanjosephkamp/ceol-universe-open"
BUILT_ON = "2026-11-25"

#: The subset's canary: a UUID generated once by uuid.uuid4() on
#: 2026-11-25 for this dataset's documentation. Never regenerated.
CANARY = "5d0f3e2a-7c1b-4f86-9a3e-2b8c6d41e957"
LICENSE = "CC-BY-SA-4.0"
ATTRIBUTION = (
    "The CEOL Universe, open subset, licensed CC BY-SA 4.0. Its fields "
    "derive from the English Wiktionary (its contributors; CC BY-SA), "
    "WordNet 3.0 (Princeton University), SCOWL (Kevin Atkinson and the "
    "contributors its notice names), the LibreOffice hunspell dictionaries "
    "en_US, en_CA, and en_AU, and the Google Books Ngram corpus (CC BY 3.0). "
    "NOTICES.md, beside this file, carries every notice and license the "
    "sources require.")
METADATA_KEYS = ("ceol.canary", "ceol.version", "ceol.license",
                 "ceol.attribution", "ceol.notices")

#: The open lists, in the order `listed_by` names them.
OPEN_LISTS = ("wordnet", "wiktionary_english", "hunspell_en_US",
              "hunspell_en_CA", "hunspell_en_AU", "scowl")
#: The lists of the `wordnet-wiktionary` config.
WN_WK_LISTS = ("wordnet", "wiktionary_english")
#: The binary list columns, as the version carries them (1 listed, 0 not
#: listed, -1 the list cannot hold the row's class, null on multiword rows).
BINARY_LISTS = OPEN_LISTS[:-1]
#: The largest SCOWL size the subset names. A list of size 80 or 95 is
#: never named: `scowl_size` is 0 on a row that only such a list holds.
SCOWL_MAX = 70
SCOWL_SIZES = (10, 20, 35, 40, 50, 55, 60, 70)

#: The version's columns the subset reads, and nothing else.
READ_COLUMNS = ("id", "word", "token_count", "classes", "wordnet",
                "wiktionary_english", "hunspell_en_US", "hunspell_en_CA",
                "hunspell_en_AU", "scowl_tier", "gb_type",
                "wn_instance", "wn_capitalized", "wk_proper_noun", "wk_flags")

#: The columns of each config, in order.
OPEN_COLUMNS = ("id", "word", "token_count", "classes", "wordnet",
                "wiktionary_english", "hunspell_en_US", "hunspell_en_CA",
                "hunspell_en_AU", "scowl_size", "gb_type", "list_count",
                "listed_by", "wn_instance", "wn_capitalized",
                "wk_proper_noun", "wk_flags")
WN_WK_COLUMNS = ("id", "word", "token_count", "classes", "wordnet",
                 "wiktionary_english", "list_count", "listed_by",
                 "wn_instance", "wn_capitalized", "wk_proper_noun", "wk_flags")

#: The configs: name, file, the lists their `listed_by` counts, columns,
#: and the predicate as the card and the record state it.
CONFIGS = (
    {"config": "open-lists", "path": "data/open-lists.parquet",
     "lists": OPEN_LISTS, "columns": OPEN_COLUMNS,
     "predicate": "list_count >= 1 over the version's rows: listed by "
                  "WordNet, the English Wiktionary, hunspell en_US, en_CA, "
                  "or en_AU, or SCOWL at a size of 10 to 70"},
    {"config": "wordnet-wiktionary", "path": "data/wordnet-wiktionary.parquet",
     "lists": WN_WK_LISTS, "columns": WN_WK_COLUMNS,
     "predicate": "list_count >= 1 over the version's rows, counting "
                  "WordNet and the English Wiktionary alone"},
    {"config": "sample", "path": "data/sample.parquet",
     "lists": OPEN_LISTS, "columns": OPEN_COLUMNS,
     "predicate": "the rows of open-lists whose id starts with '00'"},
)

#: Every column of the version a file of the subset may never carry. The
#: build asserts it from the version's own schema as well (every column of
#: the version not in READ_COLUMNS, and `scowl_tier`, which is read and
#: never written).
NEVER_WRITTEN = ("scowl_tier",)

ROW_GROUP_QUANTUM = 10_000
MAX_ROW_GROUP_BYTES = 100 * 10**6
MAX_FILE_BYTES = 500 * 10**6

TEMPLATE = RELEASE_DIR / "CARD_open.template.md"
RECORD = RELEASE_DIR / f"open_subset_{VERSION}.json"
#: the committed copies of the dataset's card and NOTICES, as the build
#: wrote them
CARD_OUT = RELEASE_DIR / f"CARD_open_{VERSION}.md"
NOTICES_OUT = RELEASE_DIR / f"NOTICES_open_{VERSION}.md"


def default_out() -> Path:
    """Where the dataset's files are written: beside the shared data
    folder, never inside it."""
    from safeguards import locations
    return (locations.data_dir().resolve().parent / "data-open"
            / f"ceol-universe-open-{VERSION}")


class OpenSubsetError(RuntimeError):
    pass


# -- inputs ------------------------------------------------------------------

def release_record() -> dict:
    return json.loads((RELEASE_DIR / f"release_{VERSION}.json")
                      .read_text(encoding="utf-8"))


def inputs() -> dict[str, Path]:
    """The version's universe file and committed NOTICES, each held to the
    sha256 its release record names."""
    rec = release_record()
    universe = DATA_RELEASE / f"ceol-universe-{VERSION}" / "universe.parquet"
    want = {f["path"]: f["sha256"] for f in rec["files"]}["universe.parquet"]
    got = sha256_file(universe)
    if got != want:
        raise OpenSubsetError(f"universe.parquet sha256 {got} is not the "
                              f"record's {want}")
    doc = {d["path"]: d for d in rec["documents"]}["NOTICES.md"]
    notices = REPO / doc["source"]
    got = sha256_file(notices)
    if got != doc["sha256"]:
        raise OpenSubsetError(f"{notices.name} sha256 {got} is not the "
                              f"record's {doc['sha256']}")
    return {"universe": universe, "notices": notices,
            "universe_sha256": want, "notices_sha256": doc["sha256"]}


# -- the columns -------------------------------------------------------------

def scowl_size(tier):
    """The SCOWL size the subset names: the version's tier where it is 10
    to 70; 0 where it is 0, 80, or 95; -1 and null unchanged."""
    import pyarrow as pa
    import pyarrow.compute as pc
    over = pc.greater(tier, SCOWL_MAX)
    return pc.if_else(pc.fill_null(over, False),
                      pa.scalar(0, pa.int16()), tier).cast(pa.int16())


#: On a multiword row, the column only that list fills: non-null exactly
#: when the list lists the row. `expected_listed_by` and
#: `expected_positions` read the other column each list fills, for an
#: independent check.
MULTIWORD_MARK = {"wordnet": "wn_instance", "wiktionary_english": "wk_flags"}
MULTIWORD_MARK_CHECK = {"wordnet": "wn_capitalized", "wiktionary_english": "wk_proper_noun"}


def listed(table, lists) -> dict[str, "object"]:
    """For each list, a boolean array: the list lists the row. On a single
    row, a binary column at 1 or `scowl_size` above 0; on a multiword row,
    the column only that list fills is non-null (WordNet and the English
    Wiktionary are the multiword rows' only lists)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    multi = pc.greater(table["token_count"], 1)
    out = {}
    for name in lists:
        if name == "scowl":
            single = pc.fill_null(pc.greater(table["scowl_size"], 0), False)
        else:
            single = pc.fill_null(pc.equal(table[name], 1), False)
        mark = MULTIWORD_MARK.get(name)
        in_multi = (pc.is_valid(table[mark]) if mark
                    else pa.array([False] * table.num_rows))
        out[name] = pc.if_else(multi, in_multi, single)
    return out


def flags(table, lists):
    """Per list, the rows it lists, as numpy booleans, and their count."""
    import numpy as np
    arrays = {k: v.to_numpy(zero_copy_only=False)
              for k, v in listed(table, lists).items()}
    count = np.zeros(table.num_rows, dtype=np.int8)
    for name in lists:
        count += arrays[name].astype(np.int8)
    return arrays, count


def project(table, config: dict):
    """A config's table: the version's rows its predicate keeps, in its
    columns."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    t = table.append_column("scowl_size", scowl_size(table["scowl_tier"]))
    arrays, count = flags(t, config["lists"])
    keep = count >= 1
    if config["config"] == "sample":
        keep &= pc.starts_with(t["id"], "00").to_numpy(zero_copy_only=False)
    idx = np.nonzero(keep)[0]
    t = t.take(pa.array(idx))
    names = [";".join(n for n in config["lists"] if arrays[n][i]) for i in idx]
    t = t.append_column("list_count", pa.array(count[idx], pa.int8()))
    t = t.append_column("listed_by", pa.array(names, pa.string()))
    return t.select(list(config["columns"]))


def expected_positions(version, config: dict):
    """The positions of the version's rows a config holds, computed apart
    from `project`: numpy over the version's own columns, with a multiword
    row's lists read from the other column each list fills."""
    import numpy as np
    tc = version["token_count"].to_numpy(zero_copy_only=False)
    single = tc == 1
    hit = np.zeros(version.num_rows, dtype=bool)
    for name in config["lists"]:
        if name == "scowl":
            v = version["scowl_tier"].fill_null(-2).to_numpy(zero_copy_only=False)
            hit |= single & (v >= 10) & (v <= SCOWL_MAX)
        else:
            v = version[name].fill_null(-2).to_numpy(zero_copy_only=False)
            hit |= single & (v == 1)
    for name, col in MULTIWORD_MARK_CHECK.items():
        if name in config["lists"]:
            hit |= ~single & version[col].is_valid().to_numpy(zero_copy_only=False)
    if config["config"] == "sample":
        ids = version["id"].to_pylist()
        hit &= np.array([i.startswith("00") for i in ids])
    return np.nonzero(hit)[0]


def file_metadata() -> dict[bytes, bytes]:
    values = (CANARY, f"open-{VERSION}", LICENSE, ATTRIBUTION, "NOTICES.md")
    return {k.encode(): v.encode("utf-8") for k, v in zip(METADATA_KEYS, values)}


def row_group_rows(table) -> int:
    per_row = max(1, table.nbytes // max(1, table.num_rows))
    fit = MAX_ROW_GROUP_BYTES // per_row
    quanta = max(1, fit // ROW_GROUP_QUANTUM) * ROW_GROUP_QUANTUM
    return max(1, min(table.num_rows, quanta))


def write(table, path: Path) -> dict:
    import pyarrow.parquet as pq
    path.parent.mkdir(parents=True, exist_ok=True)
    table = table.replace_schema_metadata(file_metadata())
    pq.write_table(table, path, compression="zstd",
                   row_group_size=row_group_rows(table))
    size = path.stat().st_size
    if size >= MAX_FILE_BYTES:
        raise OpenSubsetError(f"{path.name}: {size} bytes is over the bound")
    return {"rows": table.num_rows, "columns": list(table.column_names),
            "row_group_rows": pq.ParquetFile(path).metadata.row_group(0).num_rows,
            "bytes": size, "sha256": sha256_file(path)}


# -- the assertions ----------------------------------------------------------

def check_file(path: Path, config: dict, version, positions,
               full_names: list[str]) -> dict:
    """Re-read a written file and assert the properties the card states.
    Returns the counts the record and the card use."""
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    fail = []
    if tuple(t.column_names) != config["columns"]:
        fail.append(f"columns {t.column_names}")
    forbidden = (set(full_names) - set(READ_COLUMNS)) | set(NEVER_WRITTEN)
    if forbidden & set(t.column_names):
        fail.append(f"forbidden columns {sorted(forbidden & set(t.column_names))}")
    fail += metadata_problems(path)
    ids = t["id"].to_pylist()
    words = t["word"].to_pylist()
    if len(set(ids)) != len(ids):
        fail.append("ids not distinct")
    if any(hashlib.sha256(w.encode("utf-8")).hexdigest()[:16] != i
           for i, w in zip(ids, words)):
        fail.append("an id is not its string's hash")
    import pyarrow as pa
    if ids != version["id"].take(pa.array(positions)).to_pylist():
        fail.append("rows are not the predicate's filter of the version, "
                    "in its order")
    # the predicate, from the file's own columns
    if "scowl_size" in t.column_names:
        sizes = set(pc.unique(t["scowl_size"]).to_pylist())
        if not sizes <= {None, -1, 0, *SCOWL_SIZES}:
            fail.append(f"scowl_size values {sorted(s for s in sizes if s is not None)}")
    multi = pc.greater(t["token_count"], 1).to_numpy(zero_copy_only=False)
    names_out = t["listed_by"].to_pylist()
    want = expected_listed_by(version, positions, config["lists"])
    if names_out != want:
        fail.append("listed_by is not the lists the version's own columns name")
    for n in names_out:
        parts = n.split(";") if n else []
        if len(parts) != len(set(parts)):
            fail.append("listed_by names a list twice")
            break
    count = np.array([len(n.split(";")) if n else 0 for n in names_out], dtype=np.int16)
    if np.any(count != t["list_count"].to_numpy(zero_copy_only=False)):
        fail.append("list_count is not the number of names in listed_by")
    if np.any(count < 1):
        fail.append("a row no list of the config lists")
    # on a single row, each binary column agrees with listed_by
    for name in config["lists"]:
        if name == "scowl":
            single = pc.fill_null(pc.greater(t["scowl_size"], 0), False)
        else:
            single = pc.fill_null(pc.equal(t[name], 1), False)
        single = single.to_numpy(zero_copy_only=False)
        named = np.array([name in (s.split(";") if s else []) for s in names_out])
        if np.any(~multi & (single != named)):
            fail.append(f"{name}: listed_by disagrees with its column")
    # values equal the version's
    pos = positions
    for col in t.column_names:
        if col in ("list_count", "listed_by"):
            continue
        src = "scowl_tier" if col == "scowl_size" else col
        theirs = version[src].take(pa.array(pos))
        if col == "scowl_size":
            theirs = scowl_size(theirs)
        if not theirs.equals(t[col]):
            fail.append(f"{col}: a value differs from the version's")
    # nulls: the list columns and gb_type null exactly on multiword rows;
    # the multiword columns null on every single row
    for col in ("wordnet", "wiktionary_english", "hunspell_en_US",
                "hunspell_en_CA", "hunspell_en_AU", "scowl_size", "gb_type"):
        if col in t.column_names:
            nulls = pc.is_null(t[col]).to_numpy(zero_copy_only=False)
            if np.any(nulls != multi):
                fail.append(f"{col}: null is not exactly the multiword rows")
    for col, name in (("wn_instance", "wordnet"), ("wn_capitalized", "wordnet"),
                      ("wk_proper_noun", "wiktionary_english"),
                      ("wk_flags", "wiktionary_english")):
        valid = pc.is_valid(t[col]).to_numpy(zero_copy_only=False)
        if np.any(valid & ~multi):
            fail.append(f"{col}: a value on a single row")
        named = np.array([name in (n.split(";") if n else []) for n in names_out])
        if name in config["lists"] and np.any(multi & (valid != named)):
            fail.append(f"{col}: not null exactly where {name} lists the multiword row")
    if fail:
        raise OpenSubsetError(f"{path.name}: " + "; ".join(fail))
    return counts(t, config)


def expected_listed_by(version, positions, lists) -> list[str]:
    """`listed_by` for the version's rows at `positions`, from the version's
    own columns, row by row: on a single row, a binary column at 1 or a SCOWL
    tier of 10 to 70; on a multiword row, the list's other column non-null."""
    import pyarrow as pa
    cols = {c: version[c].take(pa.array(positions)).to_pylist()
            for c in ("token_count", "scowl_tier", *BINARY_LISTS,
                      *MULTIWORD_MARK_CHECK.values())}
    out = []
    for i in range(len(positions)):
        if cols["token_count"][i] > 1:
            out.append(";".join(n for n in lists if n in MULTIWORD_MARK_CHECK
                                and cols[MULTIWORD_MARK_CHECK[n]][i] is not None))
            continue
        names = []
        for n in lists:
            if n == "scowl":
                tier = cols["scowl_tier"][i]
                hit = tier is not None and 10 <= tier <= SCOWL_MAX
            else:
                hit = cols[n][i] == 1
            if hit:
                names.append(n)
        out.append(";".join(names))
    return out


def metadata_problems(path: Path) -> list[str]:
    """The file's key-value metadata is exactly the subset's 5 keys, beside
    the Arrow schema the writer adds, and no field carries metadata."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    kv = dict(pf.metadata.metadata or {})
    want = file_metadata()
    out = []
    if set(kv) - {b"ARROW:schema"} != set(want) or any(kv.get(k) != v for k, v in want.items()):
        out.append("the file's metadata is not exactly the subset's")
    if any(f.metadata for f in pf.schema_arrow):
        out.append("a field carries metadata")
    return out


def counts(t, config: dict) -> dict:
    """The figures the record and the card carry for a config."""
    import collections
    import pyarrow.compute as pc
    multi = pc.greater(t["token_count"], 1)
    out = {"rows": t.num_rows,
           "single": int(pc.sum(pc.invert(multi)).as_py() or 0),
           "multiword": int(pc.sum(multi).as_py() or 0)}
    names = t["listed_by"].to_pylist()
    tcount = t["token_count"].to_pylist()
    by_list = collections.Counter()
    by_list_multi = collections.Counter()
    only = collections.Counter()
    combos_multi = collections.Counter()
    for n, k in zip(names, tcount):
        parts = n.split(";")
        for p in parts:
            (by_list_multi if k > 1 else by_list)[p] += 1
        if len(parts) == 1 and k == 1:
            only[parts[0]] += 1
        if k > 1:
            combos_multi[n] += 1
    out["single_by_list"] = {n: by_list.get(n, 0) for n in config["lists"]}
    out["single_only_list"] = {n: only.get(n, 0) for n in config["lists"]}
    out["multiword_by_listing"] = dict(sorted(combos_multi.items()))
    lc = collections.Counter(zip(tcount, t["list_count"].to_pylist()))
    out["single_by_list_count"] = {str(c): lc.get((1, c), 0)
                                   for c in range(1, len(config["lists"]) + 1)}
    if "gb_type" in t.column_names:
        out["single_gb_type"] = int(pc.sum(pc.fill_null(t["gb_type"], False)).as_py() or 0)
    if "scowl_size" in t.column_names:
        sc = collections.Counter(t["scowl_size"].to_pylist())
        out["single_by_scowl_size"] = {str(s): sc.get(s, 0) for s in SCOWL_SIZES}
    cls = collections.Counter()
    for c, k in zip(t["classes"].to_pylist(), tcount):
        if k == 1:
            for f in (c.split(";") if c else ["plain"]):
                cls[f] += 1
    out["single_by_class"] = dict(sorted(cls.items()))
    flags = {}
    for col in ("wn_instance", "wn_capitalized", "wk_proper_noun"):
        flags[col] = int(pc.sum(pc.fill_null(t[col], False)).as_py() or 0)
    out["multiword_true"] = flags
    return out


# -- NOTICES -----------------------------------------------------------------

#: The sections of the version's NOTICES the subset carries, each with the
#: version's lead-in (which names the version's fields) and the subset's.
#: Everything after the lead-in is carried verbatim, but for the
#: paragraph each `drop` names.
NOTICE_SECTIONS = (
    {"heading": "## The English Wiktionary",
     "lead": ("The fields `wiktionary_english`, `wikt_title_screen`, "
              "`wikt_title_any`, `wk_proper_noun`, and `wk_flags`, and the "
              "listing of the spaced rows, are derived from the English "
              "Wiktionary's pages-articles dump and all-titles list of the "
              "run of August 1, 2026 (https://dumps.wikimedia.org/enwiktionary/)."),
     "new": ("The fields `wiktionary_english`, `wk_proper_noun`, and "
             "`wk_flags`, the name `wiktionary_english` in `listed_by`, and "
             "the listing of the multiword rows, are derived from the "
             "English Wiktionary's pages-articles dump of August 2026 (the "
             "file with sha256 `a0db4eeaea5e6b9940e21ea143eaecf93195610888d345333ae560b9a15527d1`; "
             "https://dumps.wikimedia.org/enwiktionary/)."),
     "drop": "The channel label `eol:dictionary-api:free-dictionary`"},
    {"heading": "## WordNet 3.0 (Princeton University)",
     "lead": ("The fields `wordnet`, `wn_instance`, and `wn_capitalized`, "
              "and the listing of the spaced rows, are derived from WordNet "
              "3.0, as nltk distributes it."),
     "new": ("The fields `wordnet`, `wn_instance`, and `wn_capitalized`, "
             "the name `wordnet` in `listed_by`, and the listing of the "
             "multiword rows, are derived from WordNet 3.0, as nltk "
             "distributes it."),
     "drop": None},
    {"heading": "## SCOWL 2020.12.07 (Kevin Atkinson), and the en_US, en_CA, and en_AU hunspell dictionaries",
     "lead": ("The field `scowl_tier` is derived from SCOWL 2020.12.07, and "
              "the fields `hunspell_en_US`, `hunspell_en_CA`, and "
              "`hunspell_en_AU` from the LibreOffice hunspell dictionaries, "
              "whose READMEs state that they come directly from SCOWL and "
              "are under SCOWL's copyright."),
     "new": ("The field `scowl_size` (SCOWL's lists of sizes 10 to 70) is "
             "derived from SCOWL 2020.12.07, and the fields "
             "`hunspell_en_US`, `hunspell_en_CA`, and `hunspell_en_AU` from "
             "the LibreOffice hunspell dictionaries, whose READMEs state "
             "that they come directly from SCOWL and are under SCOWL's "
             "copyright; with them, their names in `listed_by`."),
     "drop": None},
    {"heading": "## The Google Books Ngram corpus",
     "lead": ("The `gb_` fields of the features config, `zipf_log10_rank`, "
              "`zipf_resid`, and `gb_type` are aggregates per string of the "
              "Google Books Ngram corpus, English 1-grams, version 20200217 "
              "(googlebooks-eng-20200217; "
              "https://storage.googleapis.com/books/ngrams/books/datasetsv3.html)."),
     "new": ("The field `gb_type` is an aggregate per string of the Google "
             "Books Ngram corpus, English 1-grams, version 20200217 "
             "(googlebooks-eng-20200217; "
             "https://storage.googleapis.com/books/ngrams/books/datasetsv3.html)."),
     "drop": None},
)

NOTICES_PREAMBLE = """# NOTICES: the CEOL Universe, open subset, version 1.0

The open subset of the CEOL Universe is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License (https://creativecommons.org/licenses/by-sa/4.0/). Its fields are derived from the sources below. This file carries every notice, license, and credit those sources ask a copy of their data to carry, in the sources' own words where their terms require the text itself. Each section below is the section of the CEOL Universe version 1.0's NOTICES.md for that source, with its first sentence naming this subset's fields; the Wiktionary section also leaves out version 1.0's paragraph on a field this subset doesn't carry. The rest of each section, and every license text in it, is carried unchanged. Each list's membership also decides which rows are in this subset and their `list_count`. It was generated by `research/release/open_subset.py`.
"""


def sections(text: str) -> dict[str, str]:
    """The version's NOTICES split at its `## ` headings."""
    parts = re.split(r"(?m)^(?=## )", text)
    out = {}
    for p in parts[1:]:
        heading = p.splitlines()[0]
        out[heading] = p
    return out


def notices(version_text: str) -> tuple[str, list[dict]]:
    """The subset's NOTICES and, per section, what was carried."""
    have = sections(version_text)
    out = [NOTICES_PREAMBLE]
    carried = []
    for s in NOTICE_SECTIONS:
        body = have.get(s["heading"])
        if body is None:
            raise OpenSubsetError(f"NOTICES: no section {s['heading']!r}")
        if s["lead"] not in body:
            raise OpenSubsetError(f"NOTICES: {s['heading']!r} lead-in changed")
        new = body.replace(s["lead"], s["new"], 1)
        dropped = 0
        if s["drop"]:
            paras = new.split("\n\n")
            kept = [p for p in paras if not p.startswith(s["drop"])]
            dropped = len(paras) - len(kept)
            if dropped != 1:
                raise OpenSubsetError(f"NOTICES: {s['heading']!r} drop matched {dropped}")
            new = "\n\n".join(kept)
        out.append(new.rstrip("\n") + "\n")
        carried.append({"section": s["heading"][3:], "lead_in_replaced": True,
                        "paragraphs_dropped": dropped})
    return "\n".join(out), carried


def check_notices(version_text: str, subset_text: str) -> None:
    """Each carried section's verbatim blocks are the version's section's,
    the same blocks in the same order, byte for byte."""
    have, got = sections(version_text), sections(subset_text)
    for s in NOTICE_SECTIONS:
        old = verbatim_blocks(have[s["heading"]])
        new = verbatim_blocks(got.get(s["heading"], ""))
        if old != new:
            raise OpenSubsetError(f"NOTICES: {s['heading']!r}'s verbatim text is not the version's")
    if set(got) != {s["heading"] for s in NOTICE_SECTIONS}:
        raise OpenSubsetError("NOTICES: a section outside the carried ones")


def verbatim_blocks(text: str) -> list[str]:
    """The indented and fenced blocks of a NOTICES text: the texts that
    must travel verbatim."""
    blocks, cur, fence = [], [], None
    for line in text.splitlines():
        if fence is not None:
            fence.append(line)
            if line.startswith("```"):
                blocks.append("\n".join(fence))
                fence = None
            continue
        if line.startswith("```"):
            if any(l.strip() for l in cur):
                blocks.append("\n".join(cur).rstrip())
            cur, fence = [], [line]
            continue
        if line.startswith("    ") or (cur and line == ""):
            cur.append(line)
        else:
            if any(l.strip() for l in cur):
                blocks.append("\n".join(cur).rstrip())
            cur = []
    if any(l.strip() for l in cur):
        blocks.append("\n".join(cur).rstrip())
    return blocks


# -- the card ----------------------------------------------------------------

def fmt(n: int) -> str:
    return f"{n:,}"


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.2f}%"


def card_values(rec: dict) -> dict[str, str]:
    """The values the card template names, every one from the record."""
    c = {x["config"]: x for x in rec["configs"]}
    o, w, s = (c["open-lists"]["counts"], c["wordnet-wiktionary"]["counts"],
               c["sample"]["counts"])
    files = {x["config"]: x for x in rec["configs"]}
    v = {
        "version": VERSION, "dataset": DATASET, "built_on": "November 25, 2026",
        "canary": CANARY,
        "universe_rows": fmt(rec["version"]["universe_rows"]),
        "universe_sha256": rec["version"]["universe_sha256"],
        "open_rows": fmt(o["rows"]), "open_single": fmt(o["single"]),
        "open_multi": fmt(o["multiword"]),
        "open_share": pct(o["rows"], rec["version"]["universe_rows"]),
        "wnwk_rows": fmt(w["rows"]), "wnwk_single": fmt(w["single"]),
        "wnwk_multi": fmt(w["multiword"]),
        "sample_rows": fmt(s["rows"]),
        "only_wk": fmt(o["single_only_list"]["wiktionary_english"]),
        "only_wk_share": pct(o["single_only_list"]["wiktionary_english"], o["single"]),
        "single_gb": fmt(o["single_gb_type"]),
        "single_not_gb": fmt(o["single"] - o["single_gb_type"]),
        "count1": fmt(o["single_by_list_count"]["1"]),
        "multi_wk_only": fmt(o["multiword_by_listing"].get("wiktionary_english", 0)),
        "multi_wn_only": fmt(o["multiword_by_listing"].get("wordnet", 0)),
        "multi_both": fmt(o["multiword_by_listing"].get("wordnet;wiktionary_english", 0)),
        "multi_wk_proper": fmt(o["multiword_true"]["wk_proper_noun"]),
        "multi_wn_instance": fmt(o["multiword_true"]["wn_instance"]),
        "wn_gap": fmt(rec["outside"]["wordnet_not_rows"]),
        "left_out_listed": fmt(rec["version"]["listed_not_open"]),
        "scowl_zero_over70": fmt(rec["version"]["open_single_scowl_over_70"]),
    }
    for name in OPEN_LISTS:
        v[f"by_{name}"] = fmt(o["single_by_list"][name])
    for cfg in ("open-lists", "wordnet-wiktionary", "sample"):
        key = cfg.replace("-", "_")
        v[f"{key}_bytes"] = fmt(files[cfg]["bytes"])
        v[f"{key}_sha256"] = files[cfg]["sha256"]
        v[f"{key}_rg"] = fmt(files[cfg]["row_group_rows"])
    v["notices_bytes"] = fmt(rec["documents"]["NOTICES.md"]["bytes"])
    v["notices_sha256"] = rec["documents"]["NOTICES.md"]["sha256"]
    return v


def render_card(rec: dict) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    values = card_values(rec)
    out = Template(text).substitute(values)
    if "$" in out.replace("$$", ""):
        raise OpenSubsetError("card: an unresolved placeholder")
    return out


# -- the build ---------------------------------------------------------------

def build(out_dir: Path, write_files: bool = True) -> dict:
    import pyarrow.parquet as pq
    src = inputs()
    version = pq.read_table(src["universe"], columns=list(READ_COLUMNS))
    full_schema = pq.ParquetFile(src["universe"]).schema_arrow
    # each list fills its 2 multiword columns on the same rows, and every
    # multiword row has a list
    import pyarrow.compute as pc
    multi = version.filter(pc.greater(version["token_count"], 1))
    for name in WN_WK_LISTS:
        if not multi[MULTIWORD_MARK[name]].is_valid().equals(
                multi[MULTIWORD_MARK_CHECK[name]].is_valid()):
            raise OpenSubsetError(f"{name}: its 2 multiword columns disagree")
    if not pc.all(pc.or_(multi["wn_instance"].is_valid(),
                         multi["wk_flags"].is_valid())).as_py():
        raise OpenSubsetError("a multiword row no list holds")

    rec = {"generated_by": "research/release/open_subset.py",
           "dataset": DATASET, "subset_of": f"ryanjosephkamp/ceol-universe {VERSION}",
           "built_on": BUILT_ON, "canary": CANARY, "license": LICENSE,
           "version": {"universe_rows": version.num_rows,
                       "universe_sha256": src["universe_sha256"],
                       "notices_sha256": src["notices_sha256"],
                       "columns_read": list(READ_COLUMNS),
                       "columns_never_read": [c for c in full_schema.names
                                              if c not in READ_COLUMNS]},
           "open_lists": list(OPEN_LISTS), "scowl_max_size": SCOWL_MAX,
           "configs": []}
    out_dir.mkdir(parents=True, exist_ok=True)
    # NOTICES first: the card names its hash
    vtext = src["notices"].read_text(encoding="utf-8")
    ntext, carried = notices(vtext)
    check_notices(vtext, ntext)
    npath = out_dir / "NOTICES.md"
    if write_files:
        for target in (npath, NOTICES_OUT):
            target.write_text(ntext, encoding="utf-8")
            if target.read_text(encoding="utf-8") != ntext:
                raise OpenSubsetError(f"{target}: the written NOTICES reads back changed")
    nbytes = ntext.encode("utf-8")
    rec["documents"] = {"NOTICES.md": {"bytes": len(nbytes),
                                       "sha256": hashlib.sha256(nbytes).hexdigest(),
                                       "sections": carried}}
    open_ids = None
    for config in CONFIGS:
        t = project(version, config)
        path = out_dir / config["path"]
        entry = {"config": config["config"], "path": config["path"],
                 "predicate": config["predicate"],
                 "lists": list(config["lists"])}
        if write_files:
            entry.update(write(t, path))
            entry["counts"] = check_file(path, config, version,
                                         expected_positions(version, config),
                                         full_schema.names)
        else:
            # a check: the files' sizes and hashes are the record's, which
            # the caller compares with the files on disk
            entry["counts"] = counts(t, config)
            have = {c["config"]: c for c in json.loads(
                RECORD.read_text(encoding="utf-8"))["configs"]}[config["config"]]
            for k in ("rows", "columns", "row_group_rows", "bytes", "sha256"):
                entry[k] = have[k]
        if config["config"] == "open-lists":
            open_ids = t["id"].to_pylist()
        if config["config"] == "sample":
            want = [i for i in open_ids if i.startswith("00")]
            if t["id"].to_pylist() != want:
                raise OpenSubsetError("sample is not open-lists' rows with id 00")
        rec["configs"].append(entry)
    # the version's rows the subset leaves out though a list of the
    # version lists them, and those SCOWL lists only above size 70
    # read for 1 count only: the version's listed rows the subset leaves out
    full = pq.read_table(src["universe"], columns=["panel_count"])
    oc = {x["config"]: x for x in rec["configs"]}["open-lists"]["counts"]
    listed_rows = int(pc.sum(pc.greater_equal(full["panel_count"], 1)).as_py())
    rec["version"]["columns_read_for_a_count"] = ["panel_count"]
    rec["version"]["columns_never_read"].remove("panel_count")
    rec["version"]["listed_not_open"] = listed_rows - oc["rows"]
    rec["version"]["open_single_scowl_over_70"] = _over70(version)
    rec["outside"] = outside_counts(version, allow_recorded=not write_files)
    card = render_card(rec)
    cbytes = card.encode("utf-8")
    rec["documents"]["README.md"] = {"bytes": len(cbytes),
                                     "sha256": hashlib.sha256(cbytes).hexdigest()}
    if write_files:
        for target in (out_dir / "README.md", CARD_OUT):
            target.write_text(card, encoding="utf-8")
            if target.read_text(encoding="utf-8") != card:
                raise OpenSubsetError(f"{target}: the written card reads back changed")
    return rec


def _over70(version) -> int:
    """The open-lists single rows whose SCOWL tier is above 70, so that
    `scowl_size` is 0 though SCOWL lists them at a larger size."""
    import pyarrow.compute as pc
    t = version.append_column("scowl_size", scowl_size(version["scowl_tier"]))
    _, count = flags(t, OPEN_LISTS)
    single = pc.equal(t["token_count"], 1).to_numpy(zero_copy_only=False)
    over = pc.fill_null(pc.greater(t["scowl_tier"], SCOWL_MAX), False).to_numpy(zero_copy_only=False)
    return int(((count >= 1) & single & over).sum())


def outside_counts(version, allow_recorded: bool = False) -> dict:
    """The strings an open list holds under the grammar that are not rows
    of the version, counted from the derived source sets where this
    checkout has them; the committed count stands in a clone."""
    from ceol.ingest.common import DERIVED_DIR
    files = {"wordnet": ("wordnet.txt", "wordnet_plain.txt"),
             "wiktionary_english": ("wiktionary_english_all.txt",),
             "hunspell_en_US": ("hunspell_en_US.txt", "hunspell_en_US_plain.txt"),
             "hunspell_en_CA": ("hunspell_en_CA.txt", "hunspell_en_CA_plain.txt"),
             "hunspell_en_AU": ("hunspell_en_AU.txt", "hunspell_en_AU_plain.txt")}
    spaced = DERIVED_DIR.parent / "space_census"
    multi = {"wordnet": "wordnet_spaced.jsonl", "wiktionary_english": "wiktionary_spaced.jsonl"}
    if not all((DERIVED_DIR / f).exists() for fs in files.values() for f in fs) \
            or not all((spaced / f).exists() for f in multi.values()):
        if not allow_recorded:
            raise OpenSubsetError("the derived source files are absent; the gap count can't be computed")
        return json.loads(RECORD.read_text(encoding="utf-8"))["outside"]
    words = set(version["word"].to_pylist())
    out = {}
    for name, fs in files.items():
        s = set()
        for f in fs:
            with open(DERIVED_DIR / f, encoding="utf-8") as fh:
                s |= {l.rstrip("\n") for l in fh if l.strip()}
        if name in multi:
            with open(spaced / multi[name], encoding="utf-8") as fh:
                s |= {json.loads(l)["key"] for l in fh if l.strip()}
        out[name] = len(s - words)
    tiers = DERIVED_DIR / "scowl_tiers_ceol.tsv"
    with open(tiers, encoding="utf-8") as fh:
        sc = {l.split("\t")[0] for l in fh if 10 <= int(l.rstrip("\n").split("\t")[1]) <= SCOWL_MAX}
    out["scowl"] = len(sc - words)
    if any(v for k, v in out.items() if k != "wordnet"):
        raise OpenSubsetError("an open list other than WordNet holds strings "
                              "outside the version; the card says none does")
    return {"by_list": out, "wordnet_not_rows": out["wordnet"],
            "note": "strings each open list holds under the CEOL grammar "
                    "that are not rows of the version"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    out = (args.out or default_out()).resolve()
    shared = (REPO / "data").resolve()
    if out == shared or shared in out.parents:
        raise OpenSubsetError("write the subset outside the shared data/ folder")
    if args.check:
        rec = build(out, write_files=False)
        have = json.loads(RECORD.read_text(encoding="utf-8"))
        import pyarrow.parquet as pq
        src = inputs()
        version = pq.read_table(src["universe"], columns=list(READ_COLUMNS))
        full_names = pq.ParquetFile(src["universe"]).schema_arrow.names
        for config, c_new, c_old in zip(CONFIGS, rec["configs"], have["configs"]):
            if c_new["counts"] != c_old["counts"]:
                print(f"differs: {c_new['config']} counts")
                return 1
            path = out / c_old["path"]
            if not path.exists():
                print(f"absent: {path}")
                return 1
            if sha256_file(path) != c_old["sha256"]:
                print(f"differs: {c_old['path']} sha256")
                return 1
            if check_file(path, config, version, expected_positions(version, config),
                          full_names) != c_old["counts"]:
                print(f"differs: {c_old['path']} re-read")
                return 1
        for name, committed in (("NOTICES.md", NOTICES_OUT), ("README.md", CARD_OUT)):
            if rec["documents"][name]["sha256"] != have["documents"][name]["sha256"]:
                print(f"differs: {name} as rendered")
                return 1
            for path in (out / name, committed):
                if not path.exists():
                    print(f"absent: {path}")
                    return 1
                if sha256_file(path) != have["documents"][name]["sha256"]:
                    print(f"differs: {path}")
                    return 1
        check_notices(src["notices"].read_text(encoding="utf-8"),
                      (out / "NOTICES.md").read_text(encoding="utf-8"))
        print("open subset: the record re-derives")
        return 0
    rec = build(out)
    RECORD.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    for c in rec["configs"]:
        print(f"{c['config']}: {c['rows']:,} rows, {c['bytes']:,} bytes")
    print(f"record: {RECORD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
