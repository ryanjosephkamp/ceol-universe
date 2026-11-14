"""
Universe v1, re-pinned to the English OpenList's revision 08ae92b8.

The archival v1 (reference/research/universe/) took the strings inherited
from the EOL from its universe at revision c1139698, which no longer
resolves. This module reads the EOL's two lists at revision 08ae92b8, each
checked against its hash, and writes data/universe.parquet from the archival
v1 (data/archival/universe.parquet, checked against the archival record):

  - an inherited row (`eol_universe`) stays where its string is in 1 of the
    2 lists at the revision, and leaves where it is in neither;
  - `eol` is read again: in the valid list at the revision;
  - the inherited rows' `sources` tag names the revision;
  - every other column, and every row of the CEOL's own layers, is the
    archival v1's.

It refuses where the lists hold a string the archival v1 does not inherit
(that string would need the census's classes, which this module does not
compute), where the 2 lists share a string, or where a CEOL layer's row is
in either list.

The proofs, from the written file: filtering it regenerates both lists
byte for byte (sha256 equal to the files'), and every kept row equals its
archival row but for `eol` and the tag. research/universe/repin.json holds
the counts and hashes, and no candidate string.

Run:  python3 -m research.universe.repin
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from ceol.ingest.common import sha256_file
from research import archival

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
OUT_DIR = REPO / "research" / "universe"
ARCHIVAL_PARQUET = DATA_DIR / "archival" / "universe.parquet"
ARCHIVAL_JSON = archival.REFERENCE / "research" / "universe" / "universe.json"
OUT_PARQUET = DATA_DIR / "universe.parquet"
OUT_JSON = OUT_DIR / "repin.json"

DATASET = "ryanjosephkamp/english-openlist"
#: the EOL's public revision the pin reads (published November 13, 2026)
EOL_REVISION = "08ae92b8b81caf12ef119d760793e49feb7e2244"
EOL_PUBLISHED = "2026-11-13"
#: the revision's files, kept under data/ at their hub names
EOL_DIR = DATA_DIR / "eol" / EOL_REVISION[:8]
EOL_FILES = {
    "valid_words": {
        "path": "data/merged_valid_words.txt",
        "bytes": 3_981_325,
        "sha256": "32b6562c6385989e187039740b251b8b8ef0e49b399411906a9b1797f4c2e672",
        #: a plain git file on the hub: its id is the git blob's
        "git_blob": "0e29077d6d22e999b7c88cfd6820b08ab6bf0104",
    },
    "invalid_words": {
        "path": "data/merged_invalid_words.txt",
        "bytes": 91_435_258,
        #: equal to the hub's LFS object id
        "sha256": "7e28a9dae4201b4773e426b252c3f4828d8bb8f619fa2c47aa35fe2ef4306d99",
    },
    "valid_dict": {
        "path": "data/merged_valid_dict.json",
        "bytes": 51_406_050,
        #: equal to the hub's LFS object id
        "sha256": "f2c9c5567d95a2ffa641ec7b6607a1d336207f0928e490da62e825d120123aed",
    },
}

#: the `sources` tag on every inherited string: the archival one, and the
#: one this pin writes
ARCHIVAL_TAG = "eol_universe@c1139698"
TAG = f"eol_universe@{EOL_REVISION[:8]}"

COLUMNS = ("word", "eol", "eol_universe", "classes", "sources",
           "intake_date", "c4_addition", "is_restricted")


def eol_file(key: str) -> Path:
    """The local copy of one of the revision's files, checked against its
    size and sha256."""
    spec = EOL_FILES[key]
    path = EOL_DIR / Path(spec["path"]).name
    if not path.exists():
        raise FileNotFoundError(f"{path} is not here: copy the revision's "
                                f"{spec['path']} there")
    if path.stat().st_size != spec["bytes"] or sha256_file(path) != spec["sha256"]:
        raise RuntimeError(f"{path.name} is not the file pinned at "
                           f"{EOL_REVISION[:8]}")
    return path


def read_list(key: str) -> list[str]:
    """One of the revision's 2 lists, a string per line, in file order."""
    text = eol_file(key).read_text(encoding="utf-8")
    words = text.split("\n")
    if words[-1] != "":
        raise RuntimeError(f"{key}: the file does not end in a newline")
    return words[:-1]


def left_strings() -> set[str]:
    """The archival v1's inherited strings that are in neither of the EOL's
    lists at the revision: the strings the re-pin removed. The evidence
    build allows a panel set to list these outside the pin, and no other."""
    import pyarrow.parquet as pq

    old = pq.read_table(ARCHIVAL_PARQUET, columns=["word", "eol_universe"])
    inherited = set(old.filter(old["eol_universe"])["word"].to_pylist())
    return inherited - set(read_list("valid_words")) \
        - set(read_list("invalid_words"))


def build() -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    archival_meta = json.loads(ARCHIVAL_JSON.read_text(encoding="utf-8"))
    want = archival_meta["artifacts"]["universe_parquet_sha256"]
    if sha256_file(ARCHIVAL_PARQUET) != want:
        raise RuntimeError(f"{ARCHIVAL_PARQUET} is not the archival v1")

    valid = read_list("valid_words")
    invalid = read_list("invalid_words")
    valid_set, invalid_set = set(valid), set(invalid)
    if len(valid_set) != len(valid) or len(invalid_set) != len(invalid):
        raise RuntimeError("a list repeats a string")
    if valid_set & invalid_set:
        raise RuntimeError("the 2 lists share a string")

    old = pq.read_table(ARCHIVAL_PARQUET)
    if tuple(old.column_names) != COLUMNS:
        raise RuntimeError("the archival v1's columns moved")
    inherited = old["eol_universe"]
    words = old["word"]
    in_valid = pc.is_in(words, value_set=pa.array(valid, pa.string()))
    in_invalid = pc.is_in(words, value_set=pa.array(invalid, pa.string()))
    in_lists = pc.or_(in_valid, in_invalid)

    # every string of the 2 lists is an inherited row of the archival v1
    found = pc.sum(pc.and_(in_lists, inherited)).as_py() or 0
    if found != len(valid) + len(invalid):
        raise RuntimeError(f"{len(valid) + len(invalid) - found:,} strings of "
                           "the lists are not inherited rows of the archival v1")
    if pc.any(pc.and_(in_lists, pc.invert(inherited))).as_py():
        raise RuntimeError("a CEOL layer's row is in the EOL's lists")
    if not pc.all(pc.equal(pc.if_else(inherited, old["sources"], TAG),
                           pc.if_else(inherited, ARCHIVAL_TAG, TAG))).as_py():
        raise RuntimeError(f"an inherited row's sources is not {ARCHIVAL_TAG}")

    keep = pc.or_(pc.invert(inherited), in_lists)
    left = old.num_rows - (pc.sum(keep).as_py() or 0)
    was_valid = old["eol"]
    new = old.filter(keep)
    new_valid = pc.is_in(new["word"], value_set=pa.array(valid, pa.string()))
    became_valid = pc.sum(pc.and_(new_valid, pc.invert(
        old["eol"].filter(keep)))).as_py() or 0
    stopped_valid = pc.sum(pc.and_(pc.invert(new_valid),
                                   old["eol"].filter(keep))).as_py() or 0
    left_valid = pc.sum(pc.and_(was_valid, pc.invert(keep))).as_py() or 0
    new = new.set_column(COLUMNS.index("eol"), "eol", new_valid)
    new = new.set_column(
        COLUMNS.index("sources"), "sources",
        pc.if_else(new["eol_universe"], TAG, new["sources"]))
    # 1 chunk per column, as the archival builder wrote it: the archival
    # merge and v1 builders, run at the revision, write this file's bytes
    pq.write_table(new.combine_chunks(), OUT_PARQUET, compression="zstd")

    # ---- proofs, from the written file -------------------------------------
    written = pq.read_table(OUT_PARQUET)
    kept_old = old.filter(keep)
    for name in COLUMNS:
        if name in ("eol", "sources"):
            continue
        if not written[name].equals(kept_old[name]):
            raise RuntimeError(f"{name} differs from the archival v1's")
    other = pc.invert(written["eol_universe"])
    if not pc.all(pc.equal(written["sources"].filter(other),
                           kept_old["sources"].filter(other))).as_py():
        raise RuntimeError("a CEOL layer's sources moved")
    if pc.any(pc.and_(written["eol"], other)).as_py():
        raise RuntimeError("a CEOL layer's row says eol")

    counts = {"valid": 0, "invalid": 0, "exceptions": 0, "additions": 0,
              "restricted": 0}
    h_valid, h_invalid = hashlib.sha256(), hashlib.sha256()
    canonical = hashlib.sha256()
    prev = None
    for batch in written.to_batches():
        cols = [batch.column(i).to_pylist() for i in range(len(COLUMNS))]
        for row in zip(*cols):
            w, eol, uni, _, _, _, c4, restr = row
            if prev is not None and w <= prev:
                raise RuntimeError(f"order or duplicate violation at {w!r}")
            prev = w
            canonical.update(
                ("\t".join(str(x) for x in row) + "\n").encode("utf-8"))
            if eol:
                counts["valid"] += 1
                h_valid.update(w.encode("utf-8") + b"\n")
            elif uni:
                counts["invalid"] += 1
                h_invalid.update(w.encode("utf-8") + b"\n")
            elif c4:
                counts["additions"] += 1
            else:
                counts["exceptions"] += 1
            if restr:
                counts["restricted"] += 1
    proof = {
        "regenerated_valid_sha256": h_valid.hexdigest(),
        "regenerated_invalid_sha256": h_invalid.hexdigest(),
        "valid_matches_pin":
            h_valid.hexdigest() == EOL_FILES["valid_words"]["sha256"],
        "invalid_matches_pin":
            h_invalid.hexdigest() == EOL_FILES["invalid_words"]["sha256"],
    }
    if not (proof["valid_matches_pin"] and proof["invalid_matches_pin"]):
        raise RuntimeError(f"FILTER-EQUIVALENCE FAILED: {proof}")
    archival_counts = archival_meta["counts"]
    for key, name in (("additions", "c4_additions"),
                      ("restricted", "restricted_rows"),
                      ("exceptions", "exceptions")):
        if counts[key] != archival_counts[name]:
            raise RuntimeError(f"{key} {counts[key]:,} != the archival "
                               f"{archival_counts[name]:,}")

    record = {
        "generated_by": "research/universe/repin.py",
        "eol": {
            "dataset": DATASET,
            "revision": EOL_REVISION,
            "published": EOL_PUBLISHED,
            "files": EOL_FILES,
            "valid_rows": len(valid),
            "invalid_rows": len(invalid),
        },
        "archival": {
            "record": "reference/research/universe/universe.json",
            "universe_parquet_sha256": want,
            "rows": old.num_rows,
            "tag": ARCHIVAL_TAG,
        },
        "counts": {
            "universe_rows": written.num_rows,
            "inherited_rows": counts["valid"] + counts["invalid"],
            "eol_valid": counts["valid"],
            "eol_invalid": counts["invalid"],
            "exceptions": counts["exceptions"],
            "c4_additions": counts["additions"],
            "restricted_rows": counts["restricted"],
            "left_in_neither_list": left,
            "left_valid_at_archival_pin": left_valid,
            "valid_now_not_at_archival_pin": became_valid,
            "valid_at_archival_pin_not_now": stopped_valid,
        },
        "filter_equivalence": proof,
        "artifacts": {
            "universe_parquet_sha256": sha256_file(OUT_PARQUET),
            "canonical_content_sha256": canonical.hexdigest(),
        },
        "tag": TAG,
    }
    record["doc_figures"] = {
        "universe_rows": written.num_rows,
        "inherited_rows": counts["valid"] + counts["invalid"],
        "eol_valid": counts["valid"],
        "eol_invalid": counts["invalid"],
        "left_in_neither_list": left,
        "valid_now_not_at_archival_pin": became_valid,
    }
    OUT_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    r = build()
    c = r["counts"]
    print(f"[repin] {c['universe_rows']:,} rows: {c['inherited_rows']:,} "
          f"inherited at {EOL_REVISION[:8]} ({c['eol_valid']:,} valid), "
          f"{c['left_in_neither_list']:,} left")
    print(f"[repin] sha256 {r['artifacts']['universe_parquet_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
