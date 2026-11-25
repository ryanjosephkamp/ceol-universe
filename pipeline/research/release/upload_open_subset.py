"""Upload the open subset to its public dataset, `ryanjosephkamp/ceol-universe-open`.

    python3 -m research.release.upload_open_subset --dry-run
    python3 -m research.release.upload_open_subset --owner-word "<his words>"

Before anything is sent it asserts, and a failure sends nothing:

  - every file's sha256 equals the record's (`open_subset_v1.0.json`), and
    the card and NOTICES are the committed copies;
  - no word column of any Parquet file holds a restricted word (the local
    restricted split), and no token of the card or NOTICES is one;
  - the authenticated account is the owner's, and the dataset exists.

Creating the dataset and choosing its visibility are the owner's (C-007):
this script never creates a dataset or changes its visibility. It sends the
files in 1 commit, then re-reads the dataset: the hub's LFS sha256 of every
Parquet file must equal the record's. The commit, the dataset's visibility
at the time, and the owner's words are written to
`research/release/hf_upload_open_v1.0.json`. `--dry-run` runs the local
checks only and touches no network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.release import open_subset as O

OWNER = "ryanjosephkamp"
REPO_ID = O.DATASET
OUT = O.RELEASE_DIR / f"hf_upload_open_{O.VERSION}.json"


class UploadRefused(RuntimeError):
    pass


def files(out_dir: Path) -> list[tuple[Path, str, str]]:
    """(local path, path in the repo, sha256 the record names)."""
    rec = json.loads(O.RECORD.read_text(encoding="utf-8"))
    pairs = [(out_dir / c["path"], c["path"], c["sha256"]) for c in rec["configs"]]
    pairs.append((out_dir / "README.md", "README.md", rec["documents"]["README.md"]["sha256"]))
    pairs.append((out_dir / "NOTICES.md", "NOTICES.md", rec["documents"]["NOTICES.md"]["sha256"]))
    return pairs


def preflight(out_dir: Path) -> list[tuple[Path, str, str]]:
    import pyarrow.parquet as pq
    from safeguards import restricted
    pairs = files(out_dir)
    for path, target, want in pairs:
        if not path.exists():
            raise UploadRefused(f"{target}: absent at {path}")
        if sha256_file(path) != want:
            raise UploadRefused(f"{target}: sha256 is not the record's")
    for committed, name in ((O.CARD_OUT, "README.md"), (O.NOTICES_OUT, "NOTICES.md")):
        if committed.read_bytes() != (out_dir / name).read_bytes():
            raise UploadRefused(f"{name} is not the committed copy")
    words = restricted.restricted_words()
    for path, target, _ in pairs:
        if path.suffix == ".parquet":
            col = set(pq.read_table(path, columns=["word"])["word"].to_pylist())
            if col & words:
                raise UploadRefused(f"{target}: {len(col & words)} restricted word(s)")
        else:
            tokens = set(re.findall(r"[\w'’-]+", path.read_text(encoding="utf-8").lower()))
            if tokens & words:
                raise UploadRefused(f"{target}: {len(tokens & words)} restricted token(s)")
    return pairs


def upload(owner_word: str, out_dir: Path, api=None) -> dict:
    if not owner_word.strip():
        raise UploadRefused("no owner's word: the upload runs only on it")
    pairs = preflight(out_dir)
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    user = api.whoami()["name"]
    if user != OWNER:
        raise UploadRefused(f"authenticated as {user!r}, not {OWNER!r}")
    info = api.dataset_info(REPO_ID)  # raises when the dataset is absent
    from huggingface_hub import CommitOperationAdd
    ops = [CommitOperationAdd(path_in_repo=t, path_or_fileobj=str(p)) for p, t, _ in pairs]
    commit = api.create_commit(REPO_ID, ops, repo_type="dataset",
                               commit_message=f"The CEOL Universe, open subset, {O.VERSION}")
    oid = commit.oid
    final = api.dataset_info(REPO_ID, revision=oid, files_metadata=True)
    lfs = {s.rfilename: (s.lfs.sha256 if s.lfs else None) for s in final.siblings}
    for _, target, want in pairs:
        if target.endswith(".parquet") and lfs.get(target) != want:
            raise UploadRefused(f"{target}: the hub's LFS sha256 is not the record's")
    out = {"generated_by": "research/release/upload_open_subset.py",
           "repo_id": REPO_ID, "account": OWNER, "commit": oid,
           "private": bool(final.private), "was_private_before": bool(info.private),
           "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "owner_word": owner_word,
           "files": [{"path": t, "sha256": w} for _, t, w in pairs]}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None, help="the built files' folder")
    ap.add_argument("--owner-word", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    out_dir = (args.out or O.default_out()).resolve()
    try:
        if args.dry_run:
            pairs = preflight(out_dir)
            print(f"[dry run] {len(pairs)} files pass the local checks; nothing sent")
            return 0
        rec = upload(args.owner_word, out_dir)
    except UploadRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"[hub] {rec['repo_id']} commit {rec['commit']} private={rec['private']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
