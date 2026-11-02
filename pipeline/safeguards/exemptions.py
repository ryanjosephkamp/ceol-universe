"""Exemptions from the scan, each bound to 1 exact file.

`exemptions.csv` beside this module names a path, the sha256 of the file,
the counts of hits the scan finds in it, and the reason. An exemption covers
a file only while its bytes hash to that sha256 and the scan finds exactly
those counts, so an edit to an exempt file is scanned as any other file is.
Each row is reviewed and carries its reason.

The file never names a term. It applies to the committable files and to the
commits of a push, never to commit messages.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

EXEMPTIONS_CSV = Path(__file__).resolve().parent / "exemptions.csv"


@dataclass(frozen=True)
class Exemption:
    path: str
    sha256: str
    walled: int
    restricted: int
    reason: str


def load(path: Path | None = None) -> dict[str, Exemption]:
    path = path or EXEMPTIONS_CSV
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {row["path"]: Exemption(row["path"], row["sha256"],
                                       int(row["walled"]), int(row["restricted"]),
                                       row["reason"])
                for row in csv.DictReader(f)}


def covers(exemption: Exemption | None, data: bytes, walled: int,
           restricted: int) -> bool:
    return (exemption is not None
            and hashlib.sha256(data).hexdigest() == exemption.sha256
            and walled == exemption.walled
            and restricted == exemption.restricted)
