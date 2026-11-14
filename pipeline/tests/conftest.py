"""Shared test configuration.

A clone holds neither `data/` nor `private/`. The imported tests skip
themselves where `data/` is absent. This file does the same for `private/`:
where the folder is absent, a test that fails only because a private list or
a held file is missing is reported as skipped, with the reason. Where
`private/` exists, a missing file inside it is a failure.
"""

from __future__ import annotations

import pytest

from safeguards import locations, restricted, wall


def _only_private_is_missing(excinfo) -> bool:
    if locations.private_dir().exists():
        return False
    if excinfo.errisinstance((wall.WallAbsent, restricted.RestrictedAbsent)):
        return True
    if excinfo.errisinstance(FileNotFoundError):
        name = str(getattr(excinfo.value, "filename", "") or "")
        return name.startswith(str(locations.private_dir()))
    return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.when in ("setup", "call") and call.excinfo is not None \
            and _only_private_is_missing(call.excinfo):
        report.outcome = "skipped"
        report.longrepr = (str(item.fspath), item.location[1] or 0,
                           "Skipped: private/ is absent in this environment "
                           "(make link)")
