"""The private ranking keys.

A sample drawn from a public file by a public rule, with the strings the scan
finds passed over, shows where those strings are: anyone who can recompute
the ranking sees which ranked rows are missing. So the fixtures and the
vetted example list are ranked with a random key that lives in `private/`,
which git ignores, and the committed files state the rule without the key.

A key is 32 random bytes in hexadecimal, made once (`python3 -m
safeguards.keys`, which calls `make`) and never overwritten: the file is
created exclusively, so 2 runs at once cannot leave 1 key while a draw used
another. `key` reads it, and refuses where it is absent (a clone), so a draw
can never fall back to a guessable value. No message prints a key.

    python3 -m safeguards.keys fixtures examples   make the keys that are absent
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from safeguards import locations

NAMES = ("fixtures", "examples")


def path(name: str) -> Path:
    if name not in NAMES:
        raise ValueError(f"no ranking key named {name!r}")
    return locations.private_dir() / "keys" / f"{name}.key"


def available(name: str) -> bool:
    return path(name).exists()


def key(name: str) -> str:
    """The key `name`, or a refusal where private/ does not hold it."""
    p = path(name)
    if not p.exists():
        raise FileNotFoundError(f"the ranking key {name!r} is absent from "
                                "private/keys/ (python3 -m safeguards.keys)")
    value = p.read_text(encoding="ascii").strip()
    if len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"private/keys/{name}.key is not a 32-byte hex key")
    return value


def make(name: str) -> bool:
    """Make the key `name` where it is absent; True where it was made. An
    existing key is never overwritten."""
    p = path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(secrets.token_hex(32) + "\n")
    return True


def main(argv: list[str] | None = None) -> int:
    names = (argv if argv is not None else sys.argv[1:]) or list(NAMES)
    for name in names:
        print(f"[keys] {name}: {'made' if make(name) else 'kept'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
