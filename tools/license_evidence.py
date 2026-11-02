#!/usr/bin/env python3
"""The license review's evidence: the size and sha256 of each saved text.

The license review (kept outside the repository) quotes license and terms texts read at their
primary sources. Each text the review rests on was saved as it was served, and
the saved files are kept outside the repository, in the private research
folder, because they are third-party texts and some of them list strings.
`docs/licenses/EVIDENCE.csv` names each file with its source, the date it was
read, its size, and its sha256. The source and the date are entered by hand;
this script writes and checks the size and the hash.

    python3 tools/license_evidence.py            check the hashes against the files
    python3 tools/license_evidence.py --write    fill in the size and the hash
    python3 tools/license_evidence.py --dir DIR  read the files from DIR

Exit status: 0 every row matches its file, or the folder is absent (a clone,
where the check is a declared deferral); 1 a mismatch, a row without its file,
or a file without its row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_PATH = REPO / "docs" / "licenses" / "EVIDENCE.csv"
EVIDENCE_DIR = Path(os.environ.get("CEOL_EVIDENCE_DIR", REPO / ".inputs" / "license-evidence"))

FIELDS = ("file", "question", "source", "read_utc", "bytes", "sha256")


def read_rows(path: Path = CSV_PATH) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise SystemExit(f"{path.name}: the header is not {','.join(FIELDS)}")
        return list(reader)


def write_rows(rows: list[dict], path: Path = CSV_PATH) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def measure(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def saved_files(folder: Path) -> set[str]:
    """Every file under the folder, as a path relative to it."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*")
            if p.is_file() and p.name != ".DS_Store"}


def check(rows: list[dict], folder: Path) -> list[str]:
    problems = []
    listed = {row["file"] for row in rows}
    if len(listed) != len(rows):
        problems.append("a file is named in more than 1 row")
    for row in rows:
        path = folder / row["file"]
        if not path.is_file():
            problems.append(f"{row['file']}: no such file")
            continue
        size, digest = measure(path)
        if (str(size), digest) != (row["bytes"], row["sha256"]):
            problems.append(f"{row['file']}: the size or the hash differs from the row")
    for name in sorted(saved_files(folder) - listed):
        problems.append(f"{name}: a saved file with no row")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true", help="fill in the size and the hash")
    parser.add_argument("--dir", type=Path, default=EVIDENCE_DIR, help="the folder of saved texts")
    args = parser.parse_args(argv)
    rows = read_rows()
    if not args.dir.is_dir():
        print(f"license evidence: {len(rows)} rows; the folder of saved texts is absent "
              f"here, so the hashes are not checked (a declared deferral)")
        return 0
    if args.write:
        for row in rows:
            path = args.dir / row["file"]
            if path.is_file():
                size, digest = measure(path)
                row["bytes"], row["sha256"] = str(size), digest
        write_rows(rows)
    problems = check(rows, args.dir)
    for line in problems:
        print(line)
    print(f"license evidence: {len(rows)} rows, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
