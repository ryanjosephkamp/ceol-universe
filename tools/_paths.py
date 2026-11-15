"""Paths shared by the scripts in `tools/`. Importing this module also puts
`pipeline/` on the import path, so that a script can import `safeguards`,
`ceol`, and `research` as the pipeline's own modules do."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PIPELINE = REPO / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

#: the folder that holds the dataset's build inputs (what `data/` links to);
#: `CEOL_BOOTSTRAP` names another
BOOTSTRAP = Path(os.environ.get("CEOL_BOOTSTRAP", REPO / ".inputs" / "build-inputs"))

#: the archive repository; read-only, and read from `main`'s objects only
ARCHIVE = Path(os.environ.get("CEOL_ARCHIVE", REPO / ".inputs" / "archive"))
ARCHIVE_REF = "main"
