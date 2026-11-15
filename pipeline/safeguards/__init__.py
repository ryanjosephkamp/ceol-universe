"""The local safeguards of the CEOL Universe repository.

Two sets of strings never enter this repository (PLAN.md §2, rules 2 and 7):
the restricted words of the license split, and the study's private items.
The sets themselves live under `private/`, which git ignores. This package
reads them from there and checks files against them.

    locations    where `data/` and `private/` are
    restricted   the restricted words and their matcher
    wall         the study's wall list and its matcher
    scan         the scan run before every push
    examples     the builder of the vetted example list
"""
