"""Where the archival material is, seen from the pipeline.

The archive kept its construction code and its records beside the live code
under 1 root. This repository keeps them apart: the live code is under
`pipeline/`, the archival code and records are under `reference/`
(read-only), and the files that list candidate strings are under
`private/held/` (never committed). The live modules that read an archival
record take its path from here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

#: the root of the checkout (`pipeline/research/archival.py` is 2 below it)
ROOT = Path(__file__).resolve().parents[2]

#: archival code and records, at the paths the archive gave them
REFERENCE = ROOT / "reference"

#: the held files, at the paths the archive gave them; absent in a clone
HELD = ROOT / "private" / "held"


def load(rel: str) -> ModuleType:
    """An archival module, loaded from `reference/` by its path. The module
    is read for a constant; nothing of the archival code is run beyond its
    import."""
    path = REFERENCE / rel
    name = "reference_" + rel.removesuffix(".py").replace("/", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
