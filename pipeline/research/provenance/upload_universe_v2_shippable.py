"""
P0 of the intake-provenance package (C-064 ruling 5): push the config
`universe_v2_shippable` to the PRIVATE dataset, by the pattern of
research/merge/upload_hf.py.

The config is the shippable layer of universe v2 and nothing else: the
10,294,621 rows of data/universe_v2.parquet whose `is_restricted` is
false, with the fourteen columns of the C-016 pin. The 1,985 restricted
rows (words attested only by NWL2023/CSW21, C-009) never leave this
machine, private dataset or not; they are re-derivable locally from the
EOL's pinned game lists. The assertions run BEFORE the upload, on the
file that is uploaded, and a failure uploads nothing:

  - the pin's sha256 equals universe_v2.json's record;
  - the filtered row count equals v2_rows - restricted_rows;
  - the written file, re-read, carries no `is_restricted == true` row;
  - no word of the local restricted split is in the written file;
  - the account is the owner's and the dataset exists and is private.

Nothing here can create the dataset or flip its visibility. The written
parquet is deleted after hashing (the project's rules); it is
re-derivable from the pin by this script.

Run:  python3 -m research.provenance.upload_universe_v2_shippable
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.archival import REFERENCE

REPO = Path(__file__).resolve().parents[2]
PIN_PARQUET = REPO / "data" / "universe_v2.parquet"
PIN_JSON = REPO / "research" / "universe_v2" / "universe_v2.json"
RESTRICTED_CSV = REPO / ".cache" / "audit" / "universe_miss_restricted.csv"
WORK_DIR = REPO / ".cache" / "provenance"
OUT_PARQUET = WORK_DIR / "universe_v2_shippable.parquet"
MERGE_DIR = REFERENCE / "research" / "merge"
CARD = MERGE_DIR / "hf_card.md"
RECORD = MERGE_DIR / "hf_upload.json"

REPO_ID = "ryanjosephkamp/common-english-openlist"
CONFIG = "universe_v2_shippable"
PATH_IN_REPO = f"data/{CONFIG}.parquet"


def build_shippable() -> dict:
    """Write the shippable layer and assert it holds no restricted row."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    meta = json.loads(PIN_JSON.read_text(encoding="utf-8"))
    want_sha = meta["artifacts"]["universe_v2_parquet_sha256"]
    got_sha = sha256_file(PIN_PARQUET)
    if got_sha != want_sha:
        raise RuntimeError(f"universe_v2.parquet sha256 {got_sha} != the "
                           f"C-016 pin {want_sha}")
    want_rows = meta["counts"]["v2_rows"] - meta["counts"]["restricted_rows"]

    table = pq.read_table(PIN_PARQUET)
    if table.column_names != meta["schema_columns"]:
        raise RuntimeError("the pin's columns are not the fourteen recorded")
    shippable = table.filter(pc.invert(table["is_restricted"]))
    if shippable.num_rows != want_rows:
        raise RuntimeError(f"shippable rows {shippable.num_rows:,} != "
                           f"{want_rows:,}")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    pq.write_table(shippable, OUT_PARQUET, compression="zstd")

    # the assertions of record run on the file that is uploaded
    written = pq.read_table(OUT_PARQUET)
    if written.num_rows != want_rows:
        raise RuntimeError("the written file's row count drifted")
    if pc.any(written["is_restricted"]).as_py():
        raise RuntimeError("the written file carries a restricted row")
    with open(RESTRICTED_CSV, encoding="utf-8") as f:
        restricted = [row["word"] for row in csv.DictReader(f)]
    if len(restricted) != meta["counts"]["restricted_rows"]:
        raise RuntimeError("the local restricted split is not the 1,985")
    import pyarrow as pa
    hits = pc.sum(pc.is_in(written["word"],
                           value_set=pa.array(restricted))).as_py()
    if hits:
        raise RuntimeError(f"{hits} restricted word(s) in the written file")
    return {
        "rows": written.num_rows,
        "columns": written.column_names,
        "restricted_rows_excluded": len(restricted),
        "parquet_sha256": sha256_file(OUT_PARQUET),
        "parquet_bytes": OUT_PARQUET.stat().st_size,
        "source_pin_sha256": got_sha,
    }


def main() -> int:
    from huggingface_hub import HfApi

    built = build_shippable()
    # the card's figures for this config are the pin's record's
    counts = json.loads(PIN_JSON.read_text(encoding="utf-8"))["counts"]
    card = CARD.read_text(encoding="utf-8")
    for needle in (f"config_name: {CONFIG}", PATH_IN_REPO,
                   f"{built['rows']:,}", f"{counts['v2_rows']:,}",
                   f"{counts['restricted_rows']:,}",
                   f"{counts['spaced_additions']:,}"):
        if needle not in card:
            raise RuntimeError(f"the dataset card does not state {needle!r}")

    api = HfApi()
    user = api.whoami()["name"]
    if user != "ryanjosephkamp":
        raise RuntimeError(f"authenticated as {user!r}; refusing")
    info = api.repo_info(REPO_ID, repo_type="dataset")
    if not info.private:
        raise RuntimeError(f"{REPO_ID} is PUBLIC; refusing to upload — "
                           "C-007 and C-064 ruling 5 require private")
    before = info.sha

    data_commit = api.upload_file(
        repo_id=REPO_ID, repo_type="dataset",
        path_or_fileobj=str(OUT_PARQUET), path_in_repo=PATH_IN_REPO,
        commit_message="C-064 ruling 5: universe v2, the shippable layer "
                       f"({built['rows']:,} rows; no restricted row)")
    card_commit = api.upload_file(
        repo_id=REPO_ID, repo_type="dataset",
        path_or_fileobj=str(CARD), path_in_repo="README.md",
        commit_message=f"C-064 ruling 5: the {CONFIG} config on the card "
                       "(private; candidates only)")
    final = api.repo_info(REPO_ID, repo_type="dataset")
    if not final.private:
        raise RuntimeError("the dataset is not private after the upload")

    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record[CONFIG] = {
        "decision": "C-064 ruling 5",
        "private": final.private,
        "uploaded": date.today().isoformat(),
        "revision_before": before,
        "data_commit": data_commit.oid,
        "card_commit": card_commit.oid,
        "final_revision": final.sha,
        "files": [PATH_IN_REPO, "README.md"],
        **built,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    OUT_PARQUET.unlink()                 # re-derivable; hashed above
    print(f"[hf] {REPO_ID} private={final.private} "
          f"revision={final.sha} rows={built['rows']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
