"""Load a config of the CEOL Universe at a pinned version.

The dataset is the Hugging Face dataset `ryanjosephkamp/ceol-universe`. It
is private until its release, which is the author's decision. Until then the
hub path below works only in an environment that is already signed in to the
hub, and nothing in this package asks for, reads, or stores a credential. A
reader without access passes `source=`, a local copy of the Parquet file or
of a folder that holds it.

Every function here returns Arrow tables or pandas frames and never prints a
candidate.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

#: the dataset on the Hugging Face hub
DATASET = "ryanjosephkamp/ceol-universe"
#: the dataset version this kit describes
DATASET_VERSION = "v1.0"
#: the configs of version 1.0 (`pipeline/research/release/CARD_v1.0.md`, §4)
CONFIGS = ("universe", "features", "panel-listed", "eol-valid", "spaced",
           "exceptions", "sample")

#: the kit's folder (`kit/`) and the repository's root
KIT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = KIT_ROOT.parent

_VERSION = re.compile(r"v[0-9]+(\.[0-9]+)*")


def hub_path(config: str = "universe", version: str = DATASET_VERSION) -> str:
    """The hub path of a config's Parquet file at a version (a revision tag
    of the dataset)."""
    _check(config, version)
    return f"hf://datasets/{DATASET}@{version}/data/{config}.parquet"


def load(config: str = "universe", version: str = DATASET_VERSION,
         columns=None, source=None) -> pa.Table:
    """Read a config of the dataset at a pinned version as an Arrow table.

    config   one of `CONFIGS`; `universe` holds every row.
    version  the dataset version, such as "v1.0". A released version never
             changes, so a version and a config name one file.
    columns  the columns to read, or None for all; the Parquet reader reads
             only these.
    source   a local path. A file is read as it is, whatever the config. A
             folder is searched for `data/<config>.parquet`, then
             `<config>.parquet`, then `<config>_sample.parquet` (the names
             of the kit's fixtures). Without `source`, the file is read from
             `hf://datasets/ryanjosephkamp/ceol-universe@<version>/data/<config>.parquet`
             through `huggingface_hub`'s file system, if that package is
             installed.

    The dataset is private until its release; see the module's text. No
    login is done or required here.

    Each Parquet file carries its version in its metadata (`ceol.version`).
    A file whose version differs from the one asked for is refused, so a
    local copy of another version cannot be read as this one.
    """
    _check(config, version)
    wanted = None if columns is None else list(columns)
    if source is None:
        where = hub_path(config, version)
        table = _read_hub(where, config, wanted)
    else:
        path = _local_file(Path(source), config)
        where = str(path)
        table = pq.read_table(path, columns=wanted)
    found = (table.schema.metadata or {}).get(b"ceol.version")
    if found is not None and found.decode("utf-8") != version:
        raise ValueError(f"{where} is version {found.decode('utf-8')}, not the "
                         f"version asked for, {version}")
    return table


def to_frame(table, columns=None) -> pd.DataFrame:
    """A pandas frame of an Arrow table or a pandas frame, with the named
    columns only if `columns` is given. An Arrow integer or boolean column
    that holds nulls becomes a float or object column in pandas, with NaN or
    None for the null."""
    if isinstance(table, pa.Table):
        selected = table if columns is None else table.select(list(columns))
        return selected.to_pandas()
    if isinstance(table, pd.DataFrame):
        return table if columns is None else table[list(columns)]
    raise TypeError("expected a pyarrow.Table or a pandas.DataFrame, "
                    f"not {type(table).__name__}")


def join_features(universe, features, columns=None) -> pd.DataFrame:
    """The `universe` rows with columns of the `features` config, joined on
    `id`, as a pandas frame in the universe's row order.

    `columns` names the feature columns to add; None adds all but `id` and
    `word`. A universe row with no features row (a multiword row, which the
    features config does not hold) gets NaN in each added column. NaN in a
    feature column means the channel does not observe the string, not that
    the value is zero.
    """
    left = to_frame(universe)
    right = to_frame(features)
    added = [c for c in right.columns if c not in ("id", "word")] \
        if columns is None else list(columns)
    clash = [c for c in added if c in left.columns]
    if clash:
        raise ValueError(f"the universe table already has the column(s) {clash}")
    return left.merge(right[["id", *added]], on="id", how="left",
                      validate="one_to_one")


@functools.lru_cache(maxsize=None)
def _figures(version: str, path: str | None) -> dict:
    where = Path(path) if path else (
        REPO_ROOT / "pipeline" / "research" / "release" / "figures" / version
        / "figures.json")
    try:
        record = json.loads(where.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{where} is not there. The figures file is written by the "
            "pipeline (pipeline/research/release/figures.py) into the "
            "repository; pass path= if you hold a copy elsewhere") from None
    return {f["id"]: f["value"] for f in record["figures"]}


def figures(version: str = DATASET_VERSION, path=None) -> dict:
    """The release's published counts, by figure id, from `figures.json` of
    the repository (or at `path`). Every count a document or notebook quotes
    is read from here, not typed."""
    _check("universe", version)
    return dict(_figures(version, None if path is None else str(path)))


def figure(figure_id: str, version: str = DATASET_VERSION, path=None):
    """One published count by its figure id, such as `config.universe.rows`."""
    found = figures(version, path)
    if figure_id not in found:
        raise KeyError(f"no figure {figure_id!r} in the figures file of {version}")
    return found[figure_id]


def _check(config: str, version: str) -> None:
    if config not in CONFIGS:
        raise ValueError(f"unknown config {config!r}; the configs are "
                         f"{', '.join(CONFIGS)}")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError(f"a version looks like 'v1.0', not {version!r}")


def _local_file(source: Path, config: str) -> Path:
    if source.is_file():
        return source
    if source.is_dir():
        names = (f"data/{config}.parquet", f"{config}.parquet",
                 f"{config}_sample.parquet")
        for name in names:
            if (source / name).is_file():
                return source / name
        raise FileNotFoundError(f"{source} holds none of {', '.join(names)}")
    raise FileNotFoundError(f"{source} is not a file or a folder")


def _read_hub(where: str, config: str, columns) -> pa.Table:
    try:
        from huggingface_hub import HfFileSystem
    except ImportError as error:
        raise ImportError(
            "Reading from the hub needs the huggingface_hub package "
            "(pip install huggingface_hub). Without it, download "
            f"data/{config}.parquet and pass the file or its folder as "
            "source=.") from error
    try:
        with HfFileSystem().open(where, "rb") as handle:
            return pq.read_table(handle, columns=columns)
    except Exception as error:
        raise RuntimeError(
            f"could not read {where}: {error}. The dataset is private until "
            "its release, and this code does not sign in; before then, pass a "
            "local copy as source=.") from error
