"""Upload the open subset to its public dataset, `ryanjosephkamp/ceol-universe-open`.

    python3 -m research.release.upload_open_subset --dry-run
    python3 -m research.release.upload_open_subset \\
        --owner-word "<his words>" --confirm ryanjosephkamp/ceol-universe-open@<record sha256>

The record and each file are read once, into memory; every check runs on
those bytes, those bytes are what is sent, and the record's digest from that
one read is what `--confirm` must name and what the receipt records. Before anything is sent it asserts, and a
failure sends nothing:

  - every file's sha256 equals the record's (`open_subset_v1.0.json`), and
    the card and NOTICES are byte for byte the committed copies;
  - no word column of any Parquet file holds a restricted word, and the
    card and NOTICES hold none (`safeguards.restricted.find_hits`);
  - `--confirm` names this dataset and the sha256 of this record, so the
    owner's word is tied to these files;
  - the authenticated account is the owner's, and the dataset exists.

The owner's word is an attestation the session records: the script can't
tell who typed it. It runs only on the owner's word given in the session
that runs it, under the owner's own credential on his machine. Creating the
dataset and choosing its visibility are the owner's (C-007): this script
never creates a dataset or changes its visibility.

It sends the files in 1 commit and writes the receipt,
`research/release/hf_upload_open_v1.0.json`, as soon as the commit returns
(verification `pending`). It then re-reads the dataset at that revision:
every Parquet file's LFS sha256 and every other file's git blob id must
equal those of the bytes sent; the receipt is updated with the result.
`--dry-run` runs the local checks only and touches no network.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from research.release import open_subset as O

OWNER = "ryanjosephkamp"
REPO_ID = O.DATASET
OUT = O.RELEASE_DIR / f"hf_upload_open_{O.VERSION}.json"


class UploadRefused(RuntimeError):
    pass


def record_snapshot() -> dict:
    """The record, read once: its digest, and its manifest parsed from the
    same bytes (a record that doesn't parse is refused)."""
    data = O.RECORD.read_bytes()
    snap = {"sha256": hashlib.sha256(data).hexdigest(), "data": data}
    try:
        snap["manifest"] = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        snap["manifest"] = None
        snap["error"] = f"the record doesn't parse: {type(e).__name__}"
    return snap


def manifest(snap: dict) -> dict:
    if snap["manifest"] is None:
        raise UploadRefused(snap["error"])
    return snap["manifest"]


def record_sha256() -> str:
    return record_snapshot()["sha256"]


def payloads(out_dir: Path, snap: dict) -> list[dict]:
    """Each file to send, read once: its path in the repo, its bytes, and
    the sha256 the record snapshot names."""
    rec = manifest(snap)
    want = [(c["path"], c["sha256"]) for c in rec["configs"]]
    want += [(name, rec["documents"][name]["sha256"]) for name in ("README.md", "NOTICES.md")]
    out = []
    for target, sha in want:
        path = out_dir / target
        if not path.exists():
            raise UploadRefused(f"{target}: absent at {path}")
        out.append({"target": target, "data": path.read_bytes(), "sha256": sha})
    return out


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def document_hits(data: bytes, words: set[str]) -> set[str]:
    """The restricted words in a document, by the repository's own matcher."""
    from safeguards import restricted
    return restricted.find_hits(data.decode("utf-8"), words)


def preflight(items: list[dict]) -> None:
    """The checks, on the bytes that will be sent."""
    import pyarrow.parquet as pq
    from safeguards import restricted
    for it in items:
        if hashlib.sha256(it["data"]).hexdigest() != it["sha256"]:
            raise UploadRefused(f"{it['target']}: sha256 is not the record's")
    by = {it["target"]: it["data"] for it in items}
    for committed, name in ((O.CARD_OUT, "README.md"), (O.NOTICES_OUT, "NOTICES.md")):
        if committed.read_bytes() != by[name]:
            raise UploadRefused(f"{name} is not the committed copy")
    words = restricted.restricted_words()
    for it in items:
        if it["target"].endswith(".parquet"):
            col = set(pq.read_table(io.BytesIO(it["data"]), columns=["word"])["word"].to_pylist())
            if col & words:
                raise UploadRefused(f"{it['target']}: {len(col & words)} restricted word(s)")
        elif document_hits(it["data"], words):
            raise UploadRefused(f"{it['target']}: a restricted word")


def write_receipt(rec: dict) -> None:
    text = json.dumps(rec, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8")
    if OUT.read_bytes() != text.encode("utf-8"):
        raise UploadRefused("the receipt reads back changed")


def upload(owner_word: str, confirm: str, out_dir: Path, api=None) -> dict:
    if not owner_word.strip():
        raise UploadRefused("no owner's word: the upload runs only on it")
    snap = record_snapshot()
    if confirm != f"{REPO_ID}@{snap['sha256']}":
        raise UploadRefused("--confirm must name the dataset and this record's sha256")
    items = payloads(out_dir, snap)
    preflight(items)
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    user = api.whoami()["name"]
    if user != OWNER:
        raise UploadRefused(f"authenticated as {user!r}, not {OWNER!r}")
    before = api.dataset_info(REPO_ID)  # raises when the dataset is absent
    from huggingface_hub import CommitOperationAdd
    ops = [CommitOperationAdd(path_in_repo=it["target"], path_or_fileobj=it["data"])
           for it in items]
    commit = api.create_commit(REPO_ID, ops, repo_type="dataset",
                               commit_message=f"The CEOL Universe, open subset, {O.VERSION}")
    receipt = {"generated_by": "research/release/upload_open_subset.py",
               "repo_id": REPO_ID, "account": OWNER, "commit": commit.oid,
               "record_sha256": snap["sha256"],
               "private_before": bool(before.private),
               "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "owner_word": owner_word,
               "files": [{"path": it["target"], "sha256": it["sha256"],
                          "git_blob_id": git_blob_id(it["data"])} for it in items],
               "verification": "pending"}
    write_receipt(receipt)
    try:
        final = api.dataset_info(REPO_ID, revision=commit.oid, files_metadata=True)
        remote = {s.rfilename: s for s in final.siblings}
        problems = []
        for it in items:
            s = remote.get(it["target"])
            if s is None:
                problems.append(f"{it['target']}: absent at the revision")
            elif it["target"].endswith(".parquet"):
                if not s.lfs or s.lfs.sha256 != it["sha256"]:
                    problems.append(f"{it['target']}: LFS sha256 differs")
            elif s.blob_id != git_blob_id(it["data"]):
                problems.append(f"{it['target']}: blob id differs")
        receipt["private_after"] = bool(final.private)
        receipt["verification"] = "verified" if not problems else "failed: " + "; ".join(problems)
    except Exception as e:  # the commit stands; the receipt says what is unknown
        receipt["verification"] = f"failed: {type(e).__name__}: {e}"
    write_receipt(receipt)
    if receipt["verification"] != "verified":
        raise UploadRefused(f"the commit {commit.oid} was sent, but {receipt['verification']}")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None, help="the built files' folder")
    ap.add_argument("--owner-word", default="")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    out_dir = (args.out or O.default_out()).resolve()
    try:
        if args.dry_run:
            snap = record_snapshot()
            items = payloads(out_dir, snap)
            preflight(items)
            print(f"[dry run] {len(items)} files pass the local checks; nothing sent. "
                  f"To send: --confirm {REPO_ID}@{snap['sha256']}")
            return 0
        rec = upload(args.owner_word, args.confirm, out_dir)
    except UploadRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"[hub] {rec['repo_id']} commit {rec['commit']} verification {rec['verification']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
