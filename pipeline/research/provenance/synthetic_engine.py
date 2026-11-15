"""
The engine of a generated string, INFERRED from its form (C-064 rulings 3
and 11; PACKAGE.md §4.6).

The EOL's synthetic generator is lost, and its own per-entry label
(`generation_method`) is null on every surviving entry. What is recorded
as the method is an inference of September 16, 2026,
confirmed by the maintainer without amendment: (A) blind affixation over the then-valid list,
(B) chemical substituent variation and short root-infix-suffix chains,
(C) medical and scientific prefixing, and Greek plurals. This module
states those rules as functions of the form alone, so that every
generated row carries a label of the shape `<engine>/<rule>` — an
inference, never the generator's record.

The base set is the pinned EOL valid list, the nearest surviving record
of "the then-valid list"; a form is never its own base. The affix
inventories below are the package's declared parameters: the substituent
and combining-form lists of that inference with their ordinary kin.
"""

from __future__ import annotations

from typing import Callable

VOWELS = frozenset("aeiou")

#: (B) substituent prefixes, with the multipliers that precede them.
SUBSTITUENT_PREFIXES = tuple(sorted((
    "fluoro", "chloro", "bromo", "iodo", "nitro", "nitroso", "amino",
    "hydroxy", "methyl", "ethyl", "propyl", "butyl", "pentyl", "hexyl",
    "phenyl", "benzyl", "benzo", "acetyl", "methoxy", "ethoxy", "cyano",
    "azido", "azo", "carboxy", "keto", "oxo", "oxy", "thio", "sulfo",
    "phospho", "cyclo", "iso", "neo", "di", "tri", "tetra", "penta",
    "hexa", "hepta", "octa", "nona", "deca", "bis", "tris", "mono",
    "poly"), key=len, reverse=True))

#: (B) the short chains: root, unsaturation infix, functional suffix.
CHAIN_ROOTS = ("meth", "eth", "prop", "but", "pent", "hex", "hept", "oct",
               "non", "dec")
CHAIN_INFIXES = ("an", "en", "yn")
CHAIN_SUFFIXES = ("amine", "amide", "oate", "oic", "one", "ol", "al", "yl",
                  "e")

#: (C) organ, system, and scientific combining forms.
DOMAIN_PREFIXES = tuple(sorted((
    "hepato", "neuro", "pneumo", "hyper", "hypo", "myo", "hemo", "hema",
    "hemato", "angio", "cardio", "gastro", "osteo", "dermato", "dermo",
    "psycho", "nephro", "broncho", "arthro", "chondro", "encephalo",
    "gyneco", "immuno", "cyto", "histo", "patho", "onco", "lympho",
    "entero", "cerebro", "cranio", "laryngo", "rhino", "oto", "ophthalmo",
    "uro", "reno", "vaso", "thrombo", "fibro", "adeno", "lipo", "glyco",
    "micro", "macro", "nano", "bio", "geo", "hydro", "thermo", "electro",
    "photo", "radio", "chemo", "magneto", "aero", "astro", "cryo", "pyro",
    "chrono", "seismo", "paleo", "phyto", "zoo", "eco", "endo", "exo",
    "ecto", "epi", "peri", "para", "hemi", "proto", "retro", "ortho",
    "tele", "iso"), key=len, reverse=True))

#: (A) the general prefixes of blind affixation.
GENERAL_PREFIXES = tuple(sorted((
    "non", "un", "re", "de", "dis", "pre", "post", "over", "under", "out",
    "sub", "super", "anti", "counter", "mis", "fore", "mid", "inter",
    "intra", "trans", "pseudo", "semi", "ultra", "meta", "auto", "co",
    "multi", "extra", "cyber", "quasi", "self"), key=len, reverse=True))

ENGINES = ("affixation", "chemical-variation",
           "medical-scientific-prefixing", "greek-plural", "unresolved")

RULES = (
    "affixation/plural", "affixation/verb-form",
    "affixation/comparative-or-agent", "affixation/superlative",
    "affixation/gerund-plural", "affixation/agent-plural",
    "chemical-variation/substituent-prefix", "chemical-variation/root-chain",
    "medical-scientific-prefixing/domain-prefix",
    "affixation/general-prefix", "greek-plural/-ses", "greek-plural/-des",
    "unresolved/none")


def _stems(stem: str, y_form: bool) -> tuple[str, ...]:
    """Bases a suffix-stripped stem can stand for: the stem, the stem
    plus a dropped e, the stem less a doubled final consonant, and — for
    an i-final stem — the stem with its y restored."""
    out = [stem, stem + "e"]
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in VOWELS:
        out.append(stem[:-1])
    if y_form and stem.endswith("i"):
        out.append(stem[:-1] + "y")
    return tuple(out)


def _has(base: str, form: str, in_base: Callable[[str], bool]) -> bool:
    return len(base) >= 2 and base != form and in_base(base)


def _plural(form: str, in_base) -> bool:
    if form.endswith("s") and _has(form[:-1], form, in_base):
        return True
    if form.endswith("es") and _has(form[:-2], form, in_base):
        return True
    if form.endswith("ies") and _has(form[:-3] + "y", form, in_base):
        return True
    if form.endswith("a") and _has(form[:-1] + "um", form, in_base):
        return True
    if form.endswith("i") and _has(form[:-1] + "us", form, in_base):
        return True
    return False


def _suffixed(form: str, suffixes: tuple[str, ...], in_base) -> bool:
    """A full suffix (ed, ing, er, est) on any stem variant, or its
    e-final short form (d, r, st) on a base that ends in e."""
    for suffix in suffixes:
        if not form.endswith(suffix) or len(form) <= len(suffix) + 1:
            continue
        stem = form[:-len(suffix)]
        if suffix in ("d", "r", "st"):
            if stem.endswith("e") and _has(stem, form, in_base):
                return True
            continue
        for base in _stems(stem, y_form=suffix.startswith("e")):
            if _has(base, form, in_base):
                return True
    return False


def _verb_form(form: str, in_base) -> bool:
    return _suffixed(form, ("ing", "ed", "d"), in_base)


def _er_form(form: str, in_base) -> bool:
    return _suffixed(form, ("er", "r"), in_base)


def _est_form(form: str, in_base) -> bool:
    return _suffixed(form, ("est", "st"), in_base)


def affixation_suffix_rule(form: str, in_base) -> str | None:
    """Rules 1 to 4 of PACKAGE.md §4.6, first match."""
    if _plural(form, in_base):
        return "affixation/plural"
    if _verb_form(form, in_base):
        return "affixation/verb-form"
    if _er_form(form, in_base):
        return "affixation/comparative-or-agent"
    if _est_form(form, in_base):
        return "affixation/superlative"
    if form.endswith("ings") and _suffixed(form[:-1], ("ing",), in_base):
        return "affixation/gerund-plural"
    if form.endswith("ers") and _er_form(form[:-1], in_base):
        return "affixation/agent-plural"
    return None


def _resolves(rest: str, form: str, in_base) -> bool:
    """A prefix's remainder: a base word, or a rule-1-to-4 form of one."""
    return len(rest) >= 3 and (
        _has(rest, form, in_base)
        or affixation_suffix_rule(rest, in_base) is not None)


def _prefixed(form: str, prefixes: tuple[str, ...], in_base,
              depth: int) -> bool:
    for prefix in prefixes:
        if form.startswith(prefix) and len(form) > len(prefix) + 2:
            rest = form[len(prefix):]
            if _resolves(rest, form, in_base):
                return True
            if depth > 1 and _prefixed(rest, prefixes, in_base, depth - 1):
                return True
    return False


def _root_chain(form: str) -> bool:
    """Optional substituent prefixes, then root + infix + suffix, with an
    optional final s."""
    bodies = (form[:-1], form) if form.endswith("s") else (form,)
    for body in bodies:
        rest = body
        while True:
            if _chain_tail(rest):
                return True
            for prefix in SUBSTITUENT_PREFIXES:
                if rest.startswith(prefix) and len(rest) > len(prefix):
                    rest = rest[len(prefix):]
                    break
            else:
                break
    return False


def _chain_tail(rest: str) -> bool:
    for root in CHAIN_ROOTS:
        if rest.startswith(root):
            after = rest[len(root):]
            for infix in CHAIN_INFIXES:
                if after.startswith(infix) \
                        and after[len(infix):] in CHAIN_SUFFIXES:
                    return True
    return False


def infer_engine(form: str, in_base: Callable[[str], bool]) -> str:
    """`<engine>/<rule>` for one generated form. `in_base(s)` answers
    whether s is in the base set; the form itself is never its base."""
    rule = affixation_suffix_rule(form, in_base)
    if rule is not None:
        return rule
    if _prefixed(form, SUBSTITUENT_PREFIXES, in_base, depth=2):
        return "chemical-variation/substituent-prefix"
    if _root_chain(form):
        return "chemical-variation/root-chain"
    if _prefixed(form, DOMAIN_PREFIXES, in_base, depth=2):
        return "medical-scientific-prefixing/domain-prefix"
    if _prefixed(form, GENERAL_PREFIXES, in_base, depth=1):
        return "affixation/general-prefix"
    if form.endswith("ses"):
        return "greek-plural/-ses"
    if form.endswith("des"):
        return "greek-plural/-des"
    return "unresolved/none"
