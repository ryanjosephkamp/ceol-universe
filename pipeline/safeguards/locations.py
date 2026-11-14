"""Where the ignored folders are.

`data/` and `private/` sit at the root of a checkout and are never committed.
In the main checkout `data/` is a link to the bootstrap package's data folder.
A worktree gets both by `make link`, which links them to the main checkout's.
The environment variables CEOL_DATA and CEOL_PRIVATE override either path.
"""

from __future__ import annotations

import os
from pathlib import Path

#: the root of this checkout (pipeline/safeguards/locations.py is 2 below it)
REPO = Path(__file__).resolve().parents[2]


def _located(name: str) -> Path:
    override = os.environ.get(f"CEOL_{name.upper()}")
    return Path(override) if override else REPO / name


def data_dir() -> Path:
    return _located("data")


def private_dir() -> Path:
    return _located("private")


#: the restricted words of the license split, 1 row per word
def restricted_csv() -> Path:
    return private_dir() / "restricted" / "universe_miss_restricted.csv"


#: the study's 4 walled lists, as tools/build_private.py wrote them
def wall_json() -> Path:
    return private_dir() / "wall" / "walled_terms.json"


#: the files held out of the repository because they list candidate strings
def held_dir() -> Path:
    return private_dir() / "held"
