"""The consumer test of a public version: the dataset loaded in a clean
environment, exactly as a stranger would load it.

    python3 -m research.release.consumer_test --version v1.0
        the local run: the hub's layout staged from the release files
    python3 -m research.release.consumer_test --version v1.0 --hub REVISION --owner-word D-0NN
        the run on the hub, at the revision the upload recorded; only
        after the private upload, which is the owner's word at gate G3

It does 4 things, and a failure at any of them is reported, never skipped:

1. **Stages the hub's layout** in a scratch folder: `data/<config>.parquet`
   for every file the record names (each held to its sha256 first),
   `README.md` (the public card), `NOTICES.md`, and `croissant.json`. These
   are the files an upload at gate G3 sends (`hub_files`).
2. **Builds a clean environment** with uv: a new virtual environment on a
   Python already on this machine (uv may not download one), with
   `datasets` and `mlcroissant` installed from PyPI as a stranger installs
   them, resolved as of 14 days before the run so that nothing newer is
   taken. Nothing from this repository is on its path.
3. **Runs the stranger's script** (`consumer/stranger.py`) in that
   environment, in isolated mode (`-I`), from the scratch folder, with HOME
   and the Hugging Face folders in scratch, the hub's offline switches set,
   and every proxy variable pointed at a closed local port, so that a
   request the switches do not stop fails instead of going out. It loads
   every config the card declares. The receipt states the environment as it
   was passed (`stranger_env`, `stranger_command`), never as intended.
4. **Compares what it found with the release record** and writes the
   receipt `research/release/consumer_<version>.json`: counts, package
   versions, and each check's outcome, and no string of the dataset.

With `--hub`, step 1 is skipped and the stranger loads the private dataset
at the given revision, through the owner's own Hugging Face login: the
environment keeps the user's HOME, so a login kept under HF_HOME or in
HF_TOKEN elsewhere is not found and the run fails safe; the owner's key file is
never read; the hub's caches are in scratch. It refuses unless the run names
the owner's word (`--owner-word`, as the upload does) and the upload record
of the version exists with that revision as its commit; its receipt,
`research/release/consumer_<version>_hub.json`, holds the hub's hashes of
the files. The scratch folder is removed afterwards.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from ceol.ingest.common import sha256_file
from research.release import build_release as B
from research.release import documents as D
from research.release import public_card as P
from research.release import withholding as W

REPO = B.REPO
STRANGER = Path(__file__).resolve().parent / "consumer" / "stranger.py"
PACKAGES = ("datasets", "mlcroissant")
PYTHON = "3.11"
#: the switches that keep the Hugging Face libraries off the network
OFFLINE = ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE")
#: a closed local port, so that any other request fails (T1)
DEAD_PROXY = "http://127.0.0.1:9"
PROXIES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
           "https_proxy", "all_proxy")
#: the floor of free disk before the environment is downloaded (the owner's
#: limit), in bytes
DISK_FLOOR = 10 * 2**30


def receipt_path(version: str, hub: bool = False) -> Path:
    suffix = "_hub" if hub else ""
    return REPO / "research" / "release" / f"consumer_{version}{suffix}.json"


def hub_files(spec, card: Path | None = None,
              croissant: Path | None = None) -> dict[str, Path]:
    """The files an upload of a public version sends: path on the hub to the
    local file, each verified against the record. `spec` is the version's
    spec (or its name); the card and the Croissant file default to the
    version's committed ones."""
    spec = B.resolve(spec) if isinstance(spec, str) else spec
    version = spec.version
    record = json.loads(spec.record_out.read_text(encoding="utf-8"))
    out: dict[str, Path] = {}
    for prefix, entries in (("data/", record["files"]), ("", record["documents"])):
        for f in entries:
            path = spec.out_dir / f["path"]
            if sha256_file(path) != f["sha256"]:
                raise B.ReleaseError(f"{f['path']} is not the file the record "
                                     "names")
            out[prefix + f["path"]] = path
    out["README.md"] = card or P.CARD
    out["croissant.json"] = croissant or D.croissant_path(version)
    return out


def venv_command(uv: str, venv: Path) -> list[str]:
    """The clean environment's command: a Python already on this machine,
    never one uv downloads (note 7)."""
    return [uv, "venv", "--no-project", "--no-python-downloads", "--python",
            PYTHON, str(venv)]


def stranger_env(work: Path, venv: Path, revision: str | None) -> dict:
    """The stranger's environment: nothing of the run's own, HOME and the
    Hugging Face folders in scratch, offline, and every proxy at a closed
    port; on the hub, the user's HOME for the login, the caches in scratch."""
    env = {"PATH": f"{venv / 'bin'}:/usr/bin:/bin",
           "HF_HUB_DISABLE_TELEMETRY": "1",
           "HF_HUB_CACHE": str(work / "hf-hub"),
           "HF_DATASETS_CACHE": str(work / "hf-datasets")}
    if revision is None:
        env.update(HOME=str(work), HF_HOME=str(work / "hf"),
                   **{k: "1" for k in OFFLINE},
                   **{k: DEAD_PROXY for k in PROXIES})
    else:
        env.update(HOME=str(Path.home()))
    return env


def stranger_command(python: Path, work: Path, revision: str | None,
                     hub: Path) -> list[str]:
    where = (["--path", str(hub)] if revision is None
             else ["--repo", B.DATASET, "--revision", revision])
    return [str(python), "-I", str(work / "stranger.py"), *where,
            "--expect", str(work / "expect.json"), "--work", str(work)]


def environment_as_passed(env: dict, command: list[str], work: Path) -> dict:
    """What the receipt states of the stranger's environment, read from the
    environment and the command actually passed (T1)."""
    return {"offline": [k for k in OFFLINE if env.get(k) == "1"],
            "isolated": "-I" in command,
            "proxies": sorted({env[k] for k in PROXIES if k in env}),
            "home_in_scratch": env.get("HOME", "").startswith(str(work)),
            "hf_token_passed": "HF_TOKEN" in env}


def hub_gate(version: str, revision: str, owner: str | None,
             decisions: str | None = None) -> dict:
    """`--hub` runs only on the owner's word, after the upload, at the
    upload's commit (T3); returns the upload record."""
    from research.release import upload_release as U
    spec = B.resolve(version)
    record_sha = sha256_file(spec.record_out)
    U.owner_word(owner, version, record_sha, decisions)
    record_path = U.upload_record(spec)
    if not record_path.exists():
        raise B.ReleaseError(f"{record_path.name} is absent: --hub follows the "
                             "upload of the version")
    upload = json.loads(record_path.read_text(encoding="utf-8"))
    if upload.get("commit") != revision or not upload.get("complete"):
        raise B.ReleaseError(f"--hub {revision} is not the commit of the "
                             "version's complete upload record")
    # the word is the one the upload ran on, for the build it sent (NB-2)
    if str(upload.get("decision", "")).split(",")[0] != owner or \
            upload.get("record_sha256") != record_sha:
        raise B.ReleaseError(f"{owner} is not the entry the upload record "
                             "names, or the record sent is not this build's")
    return upload


def expectations(version: str) -> dict:
    """What the stranger's findings are compared with, from the record."""
    record = json.loads(B.resolve(version).record_out.read_text(encoding="utf-8"))
    return {
        "version": version,
        "canary_string": f"CEOL UNIVERSE CANARY {record['canary']}",
        "configs": {f["config"]: {"rows": f["rows"], "columns": f["columns"]}
                    for f in record["files"]},
        "metadata": {k.decode(): v.decode("utf-8")
                     for k, v in B.file_metadata(version).items()},
        "withheld_columns": list(W.WITHHELD_SETS + W.WITHHELD_FEATURES),
        "withheld_labels": sorted(W.WITHHELD_LABELS | W.WITHHELD_CHANNEL_LABELS),
    }


def compare(found: dict, expect: dict) -> dict[str, list[str]]:
    """Each check's failures, by name; an empty list is a pass."""
    checks: dict[str, list[str]] = {}
    want = expect["configs"]
    checks["configs_declared"] = [] if sorted(found["config_names"]) == \
        sorted(want) else [f"the card declares {sorted(found['config_names'])}"]
    checks["default_config"] = [] if found.get("default_config") == "universe" \
        else [f"the default config is {found.get('default_config')!r}"]
    rows, cols, ids, panel, withheld = [], [], [], [], []
    for name, w in want.items():
        got = found["configs"].get(name)
        if got is None:
            rows.append(f"{name}: not loaded")
            continue
        if got["rows"] != w["rows"]:
            rows.append(f"{name}: {got['rows']} rows, not {w['rows']}")
        if got["columns"] != w["columns"]:
            cols.append(f"{name}: its columns are not the record's")
        if got["distinct_ids"] != got["rows"]:
            ids.append(f"{name}: {got['rows'] - got['distinct_ids']} repeated ids")
        if got.get("panel_count_mismatches"):
            panel.append(f"{name}: {got['panel_count_mismatches']} rows")
        if got["withheld_columns_present"] or got.get("withheld_labels_present"):
            withheld.append(f"{name}: a withheld column or label is present")
    checks.update(rows_by_config=rows, columns_by_config=cols,
                  ids_distinct=ids, panel_count_is_the_names_in_panel_sets=panel,
                  nothing_withheld=withheld)
    checks["metadata"] = [f"{path}: not the version's metadata"
                          for path, meta in found["metadata"].items()
                          if meta != expect["metadata"]]
    checks["card"] = [k for k in ("canary_present", "limitations_first")
                      if not found["card"][k]]
    checks["notices"] = [] if found["notices"]["present"] else ["NOTICES.md"]
    checks["croissant"] = [] if found["croissant"]["mlcroissant"] == "validated" \
        and found["croissant"]["record_sets"] == list(want) \
        and not found["croissant"].get("sha256_mismatches") \
        else [str(found["croissant"])[:400]]
    return checks


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run(version: str, today: date | None = None,
        revision: str | None = None, owner: str | None = None) -> dict:
    today = today or date.today()
    exclude_newer = (today - timedelta(days=14)).isoformat()
    upload = hub_gate(version, revision, owner) if revision is not None else None
    files = hub_files(version)
    expect = expectations(version)
    free = shutil.disk_usage(REPO).free
    if free < DISK_FLOOR:
        raise B.ReleaseError(f"{free / 2**30:.1f} GiB free, under the "
                             f"{DISK_FLOOR / 2**30:.0f} GiB floor")
    uv = shutil.which("uv")
    if not uv:
        raise B.ReleaseError("uv is not installed")
    work = Path(tempfile.mkdtemp(prefix="ceol-consumer-"))
    try:
        hub = work / "hub"
        if revision is None:
            for target, source in files.items():
                dest = hub / target
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(source, dest)
        venv = work / "venv"
        made = _run(venv_command(uv, venv))
        if made.returncode:
            raise B.ReleaseError(f"uv venv failed: {made.stderr[-400:]}")
        python = venv / "bin" / "python"
        install = _run([uv, "pip", "install", "--python", str(python),
                        "--exclude-newer", exclude_newer, *PACKAGES])
        if install.returncode:
            raise B.ReleaseError(f"the install failed: {install.stderr[-600:]}")
        (work / "expect.json").write_text(json.dumps(expect), encoding="utf-8")
        env = stranger_env(work, venv, revision)
        command = stranger_command(python, work, revision, hub)
        passed = environment_as_passed(env, command, work)
        shutil.copyfile(STRANGER, work / "stranger.py")
        loaded = _run(command, cwd=work, env=env)
        if loaded.returncode:
            raise B.ReleaseError(f"the stranger's load failed: "
                                 f"{loaded.stderr[-1200:]}")
        found = json.loads(loaded.stdout)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    checks = compare(found, expect)
    return {
        "generated_by": "pipeline/research/release/consumer_test.py",
        "version": version,
        "mode": ("local: the hub's layout staged from the release files, "
                 "loaded offline" if revision is None else
                 f"hub: {B.DATASET} at revision {revision}"),
        "run_on": today.isoformat(),
        "environment": {"uv": _run([uv, "--version"]).stdout.strip(),
                        "python": PYTHON, "installed": list(PACKAGES),
                        "exclude_newer": exclude_newer,
                        "versions": found["versions"],
                        **{k: v for k, v in passed.items()
                           if k != "home_in_scratch"},
                        "home_in_scratch": passed["home_in_scratch"]},
        "files": ({t: sha256_file(p) for t, p in sorted(files.items())}
                  if upload is None else
                  {**upload["hub_lfs_sha256"], **upload["hub_git_blob_ids"]}),
        **({"upload_commit": upload["commit"]} if upload else {}),
        "configs": {name: {"rows": c["rows"], "columns": len(c["columns"]),
                           "distinct_ids": c["distinct_ids"],
                           **({"panel_count_mismatches":
                               c["panel_count_mismatches"]}
                              if "panel_count_mismatches" in c else {})}
                    for name, c in found["configs"].items()},
        "types": found["configs"]["universe"]["types"],
        "croissant": found["croissant"],
        "checks": checks,
        "passed": not any(checks.values()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--hub", metavar="REVISION",
                    help="load the private dataset at this revision (gate G3 "
                         "only, after the owner's upload)")
    ap.add_argument("--owner-word", metavar="D-0NN",
                    help="with --hub: the decision entry that records the "
                         "owner's word for the upload")
    args = ap.parse_args(argv)
    from research.release.upload_release import UploadRefused
    try:
        receipt = run(args.version, revision=args.hub, owner=args.owner_word)
    except (B.ReleaseError, UploadRefused) as exc:
        print(f"[consumer] refused: {exc}", file=sys.stderr)
        return 1
    out = receipt_path(args.version, hub=args.hub is not None)
    out.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    failed = {k: v for k, v in receipt["checks"].items() if v}
    print(f"[consumer] {args.version}: {len(receipt['checks'])} checks, "
          f"{len(failed)} failed; receipt {out.relative_to(REPO)}")
    for k, v in failed.items():
        print(f"[consumer] FAILED {k}: {'; '.join(v)[:400]}", file=sys.stderr)
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
