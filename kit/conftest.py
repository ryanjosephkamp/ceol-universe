"""Shared fixtures of the kit's tests: the kit's folder on the import path,
and the fixture files read once. No test needs the network or the private
data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

KIT = Path(__file__).resolve().parent
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

FIXTURES = KIT / "fixtures"


@pytest.fixture(scope="session")
def kit_dir() -> Path:
    return KIT


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def fixtures_manifest() -> dict:
    return json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def universe_table():
    return pq.read_table(FIXTURES / "universe_sample.parquet")


@pytest.fixture(scope="session")
def features_table():
    return pq.read_table(FIXTURES / "features_sample.parquet")


@pytest.fixture()
def universe_frame(universe_table):
    """A fresh pandas copy for each test."""
    return universe_table.to_pandas()
