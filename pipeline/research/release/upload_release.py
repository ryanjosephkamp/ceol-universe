"""
UR-1 (C-078 lines 3 and 7): upload a version of the CEOL Universe to the
PRIVATE dataset `ryanjosephkamp/ceol-universe`, on the pattern of
research/provenance/upload_universe_v2_shippable.py (C-064 ruling 5).

Before anything is sent it asserts, and a failure sends nothing:

  - every release file's sha256 equals the record's, and the card is the
    rendering check_release holds (its template carrying no literal
    figure);
  - no file holds a restricted word: no word column of a Parquet file and
    no token of the card is in the local restricted split (C-009);
  - the authenticated account is the owner's;
  - the dataset exists and is private.

It sends the files and the card in a single commit whose message names C-078
and the version, then re-reads the dataset: it must still be private, and
the hub's LFS sha256 of every Parquet file must equal the record's. The
revision is written to research/release/hf_upload.json. Nothing here can
create the dataset or change its visibility: an absent dataset, a public
dataset, or another account refuses the upload, because creation and
visibility are the owner's (C-007).

A public version (v2.1 on) is sent the same way, with its own card
(`public_card.py`) and the files the consumer test stages
(`consumer_test.hub_files`: the Parquet files, NOTICES.md, croissant.json,
and the card as README.md), and its upload is recorded in
`research/release/hf_upload_<version>.json`. Its upload happens only on the
owner's word at gate G3; the files left from an earlier version stay in
the hub's history until the owner's squash at the release.

No upload runs without the owner's word in the decision record: every run names, with `--owner-word D-0NN`, an entry
of the owner's decision record (the file `CEOL_DECISIONS` names; it is not in
this repository) that holds
exactly 1 line of the form

    **The owner's word for this upload:** "<his words>" (upload <version> to
    the private dataset <dataset>; release record sha256 <hex>)

(on 1 line), written only when the owner grants the upload, its sha256 that
of the release record about to be sent. The check comes before the
restricted list is read and before a hub client is made. A plain
invocation refuses, and so does an entry that defers, refuses, or names
another build. v2.0 has no such entry, so it is never sent again.

Run:  python3 -m research.release.upload_release --version v2.1 --owner-word D-0NN
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from ceol.ingest.common import sha256_file

from . import build_release as B
from . import release_calcs as R
from . import withholding as W

REPO = B.REPO
OWNER = "ryanjosephkamp"
REPO_ID = B.DATASET
UPLOAD_RECORD = REPO / "research" / "release" / "hf_upload.json"
#: the environment variable that names the owner's decision record
DECISIONS_ENV = "CEOL_DECISIONS"
#: what the hub's history holds after a public version's upload, until the
#: squash the release plan makes before any visibility change
HISTORY_HOLDS = ("v2.0's files: its 45 universe columns, the 5 withheld lists' "
                 f"columns among them, and the {len(W.WITHHELD_FEATURES)} "
                 "feature columns a public version withholds; the version's "
                 "tag keeps that history reachable, so delete the tag, squash "
                 "the history, and tag again before any visibility change")


class UploadRefused(RuntimeError):
    """A refusal before, or a failed check after, the upload."""


#: the line a decision entry carries only where the owner grants an upload,
#: and the only text the gate accepts: his words,
#: the version, the dataset, and the sha256 of the release record to be sent,
#: so that a word for 1 build does not carry over to a rebuilt version
WORD_LINE = re.compile(
    r"^\*\*The owner's word for this upload:\*\* \"(?P<words>[^\"\n]+)\" "
    r"\(upload (?P<version>v\d+(?:\.\d+)*) to the private dataset "
    r"(?P<dataset>[\w.-]+/[\w.-]+); release record sha256 "
    r"(?P<sha>[0-9a-f]{64})\)$", re.M)


def committed_decisions(root: Path | None = None) -> str:
    """The owner's decision record, read from the file that `CEOL_DECISIONS`
    names. The record is private and is not part of this repository, so there
    is no committed copy to read: with no file named, or none at the path, the
    upload is refused."""
    path = os.environ.get(DECISIONS_ENV)
    if not path:
        raise UploadRefused(f"{DECISIONS_ENV} must name the owner's decision "
                            "record; nothing is sent")
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise UploadRefused(f"the decision record cannot be read from "
                            f"{DECISIONS_ENV}: {type(exc).__name__}") from None


def owner_word(entry: str | None, version: str, record_sha256: str,
               decisions: str | None = None) -> str:
    """The decision entry that records the owner's word for uploading this
    build of `version`, or a refusal. The entry must hold exactly 1 line of
    `WORD_LINE`'s form, naming the version, the dataset, and the sha256 of
    the release record about to be sent. `decisions` is the record's text;
    by default the file `CEOL_DECISIONS` names (`committed_decisions`)."""
    if not entry:
        raise UploadRefused(f"an upload of {version} needs --owner-word D-0NN, "
                            "the decision entry that records the owner's word "
                            "for it; nothing is sent")
    if not re.fullmatch(r"D-\d{3}", entry):
        raise UploadRefused(f"{entry!r} is not a decision entry's name")
    text = committed_decisions() if decisions is None else decisions
    m = re.search(rf"^## {entry} ·.*?(?=^## D-|\Z)", text, re.M | re.S)
    if not m:
        raise UploadRefused(f"{entry} is not in the decision record")
    words = list(WORD_LINE.finditer(m.group(0)))
    if len(words) != 1:
        raise UploadRefused(f"{entry} carries no line of the owner's word for "
                            "an upload" if not words else
                            f"{entry} carries more than 1 line of the owner's "
                            "word")
    word = words[0]
    if word["version"] != version or word["dataset"] != REPO_ID:
        raise UploadRefused(f"{entry}'s word is for {word['version']} of "
                            f"{word['dataset']}, not {version} of {REPO_ID}")
    if word["sha"] != record_sha256:
        raise UploadRefused(f"{entry}'s word names another build of {version} "
                            "(its release record's sha256 differs)")
    return entry


def calculator(spec: B.VersionSpec):
    """The card's calculator of a version: v2.0's `release_calcs`, a public
    version's `public_card`. Each names CARD and TEMPLATE and prints rows()
    and tables()."""
    if spec.public:
        from . import public_card
        return public_card
    return R


def upload_record(spec: B.VersionSpec) -> Path:
    if spec.public:
        return REPO / "research" / "release" / f"hf_upload_{spec.version}.json"
    return UPLOAD_RECORD


def git_blob_id(path: Path) -> str:
    """The git object id the hub reports for a file it does not keep in LFS."""
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def preflight(spec: B.VersionSpec, record: dict, card_text: str,
              template: str, restricted: set[str]) -> list[tuple[Path, str]]:
    """The local assertions; returns (local path, path in the repo)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    calcs = calculator(spec)
    literal = R.template_literals(template)
    if literal:
        raise UploadRefused(f"the card's template carries literal figures "
                            f"{literal[:3]}")
    if R.render(template, calcs.rows(), calcs.tables()) != card_text:
        raise UploadRefused("the card is not the rendering the figure check "
                            f"holds; run {calcs.__name__} --render")
    hits = set(re.split(r"[^a-z]+", card_text.lower())) & restricted
    if hits:
        raise UploadRefused(f"the card holds {len(hits)} restricted word(s)")
    value_set = pa.array(sorted(restricted), pa.string())
    if spec.public:
        from .consumer_test import hub_files
        pairs = []
        for target, path in hub_files(spec).items():
            if target == "README.md":
                continue
            if path.suffix == ".parquet":
                words = pq.read_table(path, columns=["word"])["word"]
                found = pc.sum(pc.is_in(words, value_set=value_set)).as_py() or 0
            else:
                found = len(set(re.split(r"[^a-z]+", path.read_text(
                    encoding="utf-8").lower())) & restricted)
            if found:
                raise UploadRefused(f"{target} holds {found} restricted "
                                    "word(s)")
            pairs.append((path, target))
        return pairs
    pairs = []
    for f in record["files"]:
        path = spec.out_dir / f["path"]
        if sha256_file(path) != f["sha256"]:
            raise UploadRefused(f"{f['path']} is not the file the record "
                                "names")
        words = pq.read_table(path, columns=["word"])["word"]
        found = pc.sum(pc.is_in(words, value_set=value_set)).as_py() or 0
        if found:
            raise UploadRefused(f"{f['path']} holds {found} restricted "
                                "word(s)")
        pairs.append((path, f"data/{f['path']}"))
    return pairs


def check_hub(api) -> str:
    """The account and the dataset; returns the revision before."""
    from huggingface_hub.errors import RepositoryNotFoundError
    user = api.whoami()["name"]
    if user != OWNER:
        raise UploadRefused(f"authenticated as {user!r}, not {OWNER!r}; "
                            "refusing")
    try:
        info = api.repo_info(REPO_ID, repo_type="dataset")
    except RepositoryNotFoundError:
        raise UploadRefused(f"{REPO_ID} does not exist; creating it is the "
                            "owner's (C-007), so nothing is sent") from None
    if not info.private:
        raise UploadRefused(f"{REPO_ID} is PUBLIC; refusing — C-078 line 3 "
                            "and C-007 require the private dataset")
    return info.sha


def upload(version: str, api=None, *, owner: str | None = None,
           decisions: str | None = None, repo: Path = REPO,
           record_out: Path | None = None) -> dict:
    """Assert, send, re-check, record. `api` is an HfApi or a stand-in. The
    owner's word is checked first, before the restricted list is read or a
    client made; `decisions` is the decision record's text (by default
    the file `CEOL_DECISIONS` names)."""
    spec = B.resolve(version, repo)
    entry = owner_word(owner, version, sha256_file(spec.record_out), decisions)
    calcs = calculator(spec)
    record_out = record_out or upload_record(spec)
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    card = calcs.CARD.read_text(encoding="utf-8")
    template = calcs.TEMPLATE.read_text(encoding="utf-8")
    restricted = B.read_restricted(spec,
                                   record["pin_counts"]["restricted_rows"])
    pairs = preflight(spec, record, card, template, restricted)
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    before = check_hub(api)
    if spec.public:
        # a re-upload never moves the version's tag silently (NS-2)
        tags = {t.name for t in api.list_repo_refs(REPO_ID,
                                                   repo_type="dataset").tags}
        if version in tags:
            raise UploadRefused(f"the hub's tag {version} exists; moving it is "
                                "the owner's, so nothing is sent")

    from huggingface_hub import CommitOperationAdd
    operations = [CommitOperationAdd(path_in_repo=target,
                                     path_or_fileobj=str(path))
                  for path, target in pairs]
    operations.append(CommitOperationAdd(path_in_repo="README.md",
                                         path_or_fileobj=str(calcs.CARD)))
    rows = record["rows_by_config"]["universe"]
    message = (f"Gate G3: the CEOL Universe {version}, uploaded privately for "
               f"the consumer test ({rows:,} rows in universe; no restricted "
               f"row)" if spec.public else
               f"C-078 lines 3 and 7: the CEOL Universe {version}, a private "
               f"rehearsal ({rows:,} rows in universe; no restricted row)")
    commit = api.create_commit(REPO_ID, operations, repo_type="dataset",
                               commit_message=message)
    try:
        final, hub, blobs = after_commit(api, spec, calcs, pairs, record,
                                         commit.oid)
        if spec.public:
            # the version's tag, which the Croissant file's addresses name
            api.create_tag(REPO_ID, tag=version, revision=commit.oid,
                           repo_type="dataset")
    except BaseException as exc:
        # the commit landed: whatever failed, a partial record keeps it
        # (T7, NS-2)
        record_out.write_text(json.dumps({
            "repo_id": REPO_ID, "version": version, "decision": entry,
            "commit": commit.oid, "complete": False,
            "failed_check": repr(exc)[:600],
            "uploaded": date.today().isoformat()}, indent=2) + "\n",
            encoding="utf-8")
        raise
    out = {
        "repo_id": REPO_ID,
        "version": version,
        "decision": f"{entry}, the owner's word for this upload",
        "account": OWNER,
        "private": final.private,
        "uploaded": date.today().isoformat(),
        "revision_before": before,
        "commit": commit.oid,
        "final_revision": final.sha,
        "files": [t for _p, t in pairs] + ["README.md"],
        "hub_lfs_sha256": dict(sorted(hub.items())),
        **({"hub_git_blob_ids": dict(sorted(blobs.items()))}
           if spec.public else {}),
        "card_sha256": sha256_file(calcs.CARD),
        "record_sha256": sha256_file(spec.record_out),
        **({"tag": version, "history_holds": HISTORY_HOLDS}
           if spec.public else {}),
        "complete": True,
    }
    record_out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def after_commit(api, spec, calcs, pairs, record, oid: str):
    """The checks after the commit (T7): the dataset still private; every
    file sent, the card included, the local file by its LFS sha256 or its
    git object id; and the tree holding the sent files and nothing else but
    .gitattributes. Returns the final info, the LFS hashes, and the ids."""
    final = api.repo_info(REPO_ID, repo_type="dataset")
    if not final.private:
        raise UploadRefused("the dataset is not private after the upload; "
                            "report it to the owner at once")
    sent = [(p, t) for p, t in pairs] + [(calcs.CARD, "README.md")]
    infos = api.get_paths_info(REPO_ID, [t for _p, t in sent], revision=oid,
                               repo_type="dataset")
    by_path = {i.path: i for i in infos}
    want = {f"data/{f['path']}": f["sha256"] for f in record["files"]}
    hub, blobs = {}, {}
    for path, target in sent:
        info = by_path.get(target)
        if info is None:
            raise UploadRefused(f"{target} is not on the hub after the commit")
        lfs = getattr(info, "lfs", None)
        if target in want:
            hub[target] = lfs.sha256 if lfs else None
        elif lfs:
            # a text file the hub keeps in LFS is held by its sha256
            if lfs.sha256 != sha256_file(path):
                raise UploadRefused(f"{target}: the hub's sha256 is not the "
                                    "local file's")
            blobs[target] = f"lfs sha256 {lfs.sha256}"
        else:
            if info.blob_id != git_blob_id(path):
                raise UploadRefused(f"{target}: the hub's object id is not the "
                                    "local file's")
            blobs[target] = info.blob_id
    if hub != want:
        raise UploadRefused("the hub's sha256 of the uploaded files is not "
                            "the record's")
    tree = set(api.list_repo_files(REPO_ID, revision=oid, repo_type="dataset"))
    extra = sorted(tree - {t for _p, t in sent} - {".gitattributes"})
    if extra:
        raise UploadRefused(f"the hub's tree holds paths beyond the files sent: "
                            f"{extra}")
    return final, hub, blobs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--owner-word", metavar="D-0NN",
                    help="the decision entry that records the owner's word "
                         "for this upload")
    args = ap.parse_args(argv)
    try:
        out = upload(args.version, owner=args.owner_word)
    except (UploadRefused, B.ReleaseError) as exc:
        print(f"[hub] refused: {exc}", file=sys.stderr)
        return 1
    print(f"[hub] {out['repo_id']} private={out['private']} "
          f"revision={out['final_revision']} files={len(out['files'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
