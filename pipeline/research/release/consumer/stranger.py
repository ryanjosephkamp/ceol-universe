"""A stranger's load of the CEOL Universe.

This script runs in a clean environment that holds only what a stranger
installs (`datasets`, and `mlcroissant` to read the Croissant file). It
imports nothing from the CEOL Universe's repository: what it knows of the
dataset is the dataset itself, and an expectations file that
`consumer_test.py` writes from the release record, which it only compares
with. It loads every config the card declares, as the hub's dataset page
tells a reader to:

    from datasets import load_dataset
    ds = load_dataset("ryanjosephkamp/ceol-universe", "universe", split="candidates")

and reports, for each config, what it found: its rows, its columns and
their types, its distinct ids, the rows whose `panel_count` is not the
number of names in `panel_sets`, and any withheld column. It reads the
card's canary, the Parquet files' key-value metadata, `NOTICES.md`, and
the Croissant file. It prints 1 JSON object and no string of the dataset.

    python -I stranger.py --path DIR --expect EXPECT.json --work DIR
    python -I stranger.py --repo ryanjosephkamp/ceol-universe --revision SHA \\
        --expect EXPECT.json --work DIR          (on the hub; gate G3 only)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _versions() -> dict:
    import importlib.metadata as md
    out = {"python": sys.version.split()[0]}
    for name in ("datasets", "pyarrow", "huggingface_hub", "pandas",
                 "mlcroissant"):
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = None
    return out


def _text(source: str, name: str, local: bool, revision: str | None) -> str:
    if local:
        return (Path(source) / name).read_text(encoding="utf-8")
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(source, name, repo_type="dataset",
                                revision=revision)).read_text(encoding="utf-8")


def _metadata(source: str, path: str, local: bool, revision: str | None
              ) -> dict[str, str]:
    """A Parquet file's key-value metadata, read from its footer alone."""
    import pyarrow.parquet as pq
    if local:
        schema = pq.read_schema(Path(source) / path)
    else:
        from huggingface_hub import HfFileSystem
        fs = HfFileSystem()
        with fs.open(f"datasets/{source}@{revision}/{path}", "rb") as f:
            schema = pq.read_schema(f)
    return {k.decode(): v.decode("utf-8")
            for k, v in (schema.metadata or {}).items()
            if k.decode().startswith("ceol.")}


def _config(ds, expect: dict) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    t = ds.data.table
    out = {"rows": ds.num_rows, "columns": list(ds.column_names),
           "types": {k: str(v.dtype) if hasattr(v, "dtype") else str(v)
                     for k, v in ds.features.items()},
           "distinct_ids": int(pc.count_distinct(t["id"]).as_py()),
           "withheld_columns_present": [c for c in expect["withheld_columns"]
                                        if c in ds.column_names]}
    if "panel_sets" in ds.column_names:
        sets = t["panel_sets"]
        names = pc.cast(pc.list_value_length(pc.split_pattern(sets, ";")),
                        pa.int64())
        names = pc.if_else(pc.equal(sets, ""), pa.scalar(0, pa.int64()), names)
        out["panel_count_mismatches"] = int(pc.sum(pc.not_equal(
            names, pc.cast(t["panel_count"], pa.int64()))).as_py() or 0)
        labels = set()
        for field in ("panel_sets", "sources", "intake_channels"):
            for value in pc.unique(t[field]).to_pylist():
                labels.update((value or "").split(";"))
        out["withheld_labels_present"] = sorted(
            labels & set(expect["withheld_labels"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--path", help="a local folder laid out as the hub's")
    where.add_argument("--repo", help="the hub's dataset id (gate G3 only)")
    ap.add_argument("--revision")
    ap.add_argument("--expect", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True,
                    help="a scratch folder for the datasets cache")
    args = ap.parse_args(argv)
    expect = json.loads(args.expect.read_text(encoding="utf-8"))
    local = args.path is not None
    source = args.path or args.repo

    import datasets
    out: dict = {"versions": _versions(), "mode": "local" if local else "hub"}
    names = datasets.get_dataset_config_names(source, revision=args.revision)
    out["config_names"] = list(names)
    try:
        out["default_config"] = datasets.get_dataset_default_config_name(
            source, revision=args.revision)
    except Exception as exc:  # an older datasets has no such function
        out["default_config"] = f"unread: {type(exc).__name__}"
    out["configs"] = {}
    for name in names:
        cache = args.work / "cache" / name
        ds = datasets.load_dataset(source, name, split="candidates",
                                   revision=args.revision,
                                   cache_dir=str(cache))
        out["configs"][name] = _config(ds, expect)
        del ds
        shutil.rmtree(cache, ignore_errors=True)

    card = _text(source, "README.md", local, args.revision)
    out["card"] = {"canary_present": expect["canary_string"] in card,
                   "limitations_first": card.split("\n## ", 1)[1].startswith(
                       "1. Limitations") if "\n## " in card else False}
    notices = _text(source, "NOTICES.md", local, args.revision)
    out["notices"] = {"present": notices.startswith("# NOTICES"),
                      "bytes": len(notices.encode("utf-8"))}
    out["metadata"] = {f"data/{name}.parquet": _metadata(
        source, f"data/{name}.parquet", local, args.revision)
        for name in names}

    croissant = json.loads(_text(source, "croissant.json", local,
                                 args.revision))
    out["croissant"] = {"record_sets": [r["@id"] for r in
                                        croissant.get("recordSet", [])]}
    if local:
        # each file object's sha256 against the file loaded
        import hashlib
        mismatched = []
        for obj in croissant.get("distribution", []):
            data = (Path(source) / "data" / obj["@id"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != obj.get("sha256"):
                mismatched.append(obj["@id"])
        out["croissant"]["sha256_mismatches"] = mismatched
    else:
        # on the hub, each file object's sha256 against the hub's LFS sha256
        from huggingface_hub import HfApi
        objects = {f"data/{o['@id']}": o.get("sha256")
                   for o in croissant.get("distribution", [])}
        infos = HfApi().get_paths_info(source, list(objects), revision=args.revision,
                                       repo_type="dataset")
        hub = {i.path: (i.lfs.sha256 if getattr(i, "lfs", None) else None)
               for i in infos}
        out["croissant"]["sha256_mismatches"] = sorted(
            p for p, sha in objects.items() if hub.get(p) != sha)
    try:
        import mlcroissant as mlc
        path = args.work / "croissant.json"
        path.write_text(json.dumps(croissant), encoding="utf-8")
        mlc.Dataset(jsonld=str(path))
        out["croissant"]["mlcroissant"] = "validated"
    except ImportError:
        out["croissant"]["mlcroissant"] = "not installed"
    except Exception as exc:
        out["croissant"]["mlcroissant"] = f"refused: {type(exc).__name__}: " \
                                          f"{str(exc)[:400]}"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
