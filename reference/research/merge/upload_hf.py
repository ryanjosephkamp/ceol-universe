"""
C2 upload: create the PRIVATE dataset and push the two configs (C-007).

Creation and every upload are private. The dataset goes public only on the
owner's explicit later instruction — nothing here can flip visibility.

Run:  python -m research.merge.upload_hf
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from huggingface_hub import HfApi

from .build_merge import DATA_DIR, MERGE_DIR

REPO_ID = "ryanjosephkamp/common-english-openlist"


def main() -> int:
    api = HfApi()
    user = api.whoami()["name"]
    if user != "ryanjosephkamp":
        raise RuntimeError(f"authenticated as {user!r}; refusing")

    api.create_repo(REPO_ID, repo_type="dataset", private=True,
                    exist_ok=True)
    info = api.repo_info(REPO_ID, repo_type="dataset")
    if not info.private:
        raise RuntimeError(f"{REPO_ID} exists and is PUBLIC; refusing to "
                           "upload — C-007 requires private")

    commit = api.upload_folder(
        repo_id=REPO_ID, repo_type="dataset",
        folder_path=str(DATA_DIR), path_in_repo="data",
        allow_patterns=["exceptions.parquet", "merged.parquet"],
        commit_message="C2 v0: exceptions + merged candidate inventories "
                       "(filter-equivalence proven against EOL pin "
                       "c1139698)")
    api.upload_file(
        repo_id=REPO_ID, repo_type="dataset",
        path_or_fileobj=str(MERGE_DIR / "hf_card.md"),
        path_in_repo="README.md",
        commit_message="C2 v0: dataset card (private; candidates only)")
    final = api.repo_info(REPO_ID, repo_type="dataset")

    record = {
        "repo_id": REPO_ID, "private": final.private,
        "uploaded": date.today().isoformat(),
        "data_commit": commit.oid,
        "final_revision": final.sha,
        "files": ["data/exceptions.parquet", "data/merged.parquet",
                  "README.md"],
    }
    (MERGE_DIR / "hf_upload.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"[hf] {REPO_ID} private={final.private} revision={final.sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
