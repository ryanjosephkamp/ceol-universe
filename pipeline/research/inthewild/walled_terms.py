"""The archive's module path for the study's wall list.

The imported code and tests import `research.inthewild.walled_terms`, as
they did in the archive. In this repository the lists are in `private/` and
the matcher is in `safeguards.wall`; this module re-exports it, so that the
imported files stay as the archive holds them.
"""

from safeguards.wall import (  # noqa: F401
    DISTINCT_PLACEHOLDER, PLACEHOLDER, all_terms, canon, find_hits, pattern,
    redact, walled_terms)
