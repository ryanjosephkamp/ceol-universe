"""Ready strata for the sampler.

A stratum is a function of a row that returns a label; the sampler draws the
same number of rows (or a number set per label) from each label. A row is a
mapping from column name to value, such as a row of the `universe` config.

Each stratum below states its definition in its `definition` text and names
the columns it reads. Nothing here lists a candidate.

The evidence columns follow the dataset card (§5):

- 1 means the source lists the row;
- 0 means the source does not list it;
- -1 means the source cannot hold the row's kind of string (a list without
  hyphens cannot hold a hyphenated string). It is never "not listed";
- null means the source was not measured over the row (every multiword row
  holds null in the evidence columns). It is never "not listed" either.

In a pandas frame, an integer column that holds nulls has NaN for each null,
and a boolean column that holds nulls has None. Every function here reads
both as null.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

Row = Mapping[str, Any]


def is_null(value: Any) -> bool:
    """Whether a cell is null: None, NaN, or pandas' NA."""
    return value is None or value is pd.NA or bool(value != value)


@dataclass(frozen=True)
class Stratum:
    """A named function from a row to a label.

    name        the stratum's name, as the sampler's manifest records it.
    columns     the columns the function reads.
    labels      the labels it returns on the rows of version 1.0.
    definition  what the labels mean, in words.
    label_of    the function of a row.
    vectorized  optionally, the same function over a whole pandas frame,
                which must return the labels `label_of` returns row by row.
    """

    name: str
    columns: tuple[str, ...]
    labels: tuple[str, ...]
    definition: str
    label_of: Callable[[Row], str]
    vectorized: Callable[[pd.DataFrame], Sequence[str]] | None = None

    def __call__(self, row: Row) -> str:
        return self.label_of(row)

    def label_frame(self, frame: pd.DataFrame) -> np.ndarray:
        """The label of every row of a pandas frame, as an object array.

        The function is called once for each distinct combination of the
        stratum's columns, not once for each row."""
        missing = [c for c in self.columns if c not in frame.columns]
        if missing:
            hint = (" Join the features config first (ceolkit.join_features)."
                    if "wordfreq_zipf" in missing else "")
            raise KeyError(f"the stratum {self.name} reads the column(s) "
                           f"{missing}, which the table does not have.{hint}")
        if self.vectorized is not None:
            return np.asarray(self.vectorized(frame), dtype=object)
        return label_distinct(frame, self.columns, self.label_of)


def label_distinct(frame: pd.DataFrame, columns: Sequence[str],
                   label_of: Callable[[Row], str]) -> np.ndarray:
    """Apply `label_of` to each distinct combination of `columns` and map the
    labels back to the rows."""
    sub = frame[list(columns)]
    if not len(sub):
        return np.empty(0, dtype=object)
    combined = np.zeros(len(sub), dtype=np.int64)
    capacity = 1
    for name in columns:
        codes, uniques = pd.factorize(sub[name])  # null becomes -1
        size = len(uniques) + 1
        capacity *= size
        if capacity >= 2 ** 62:  # the combined code would overflow
            rows = sub.to_dict("records")
            return np.array([label_of(r) for r in rows], dtype=object)
        combined = combined * size + (codes.astype(np.int64) + 1)
    _, first, inverse = np.unique(combined, return_index=True, return_inverse=True)
    representatives = sub.iloc[first].to_dict("records")
    labels = np.array([label_of(r) for r in representatives], dtype=object)
    return labels[inverse]


# ---------------------------------------------------------------------------
# The evidence tier
# ---------------------------------------------------------------------------

#: the 5 families of published lists. Hunspell is 1 family: it is held by
#: any of the 4 `hunspell_en_*` columns. SCOWL is read from `scowl_tier`.
FAMILIES: dict[str, tuple[str, ...]] = {
    "wordnet": ("wordnet",),
    "wiktionary_english": ("wiktionary_english",),
    "hunspell": ("hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
                 "hunspell_en_AU"),
    "enable1": ("enable1",),
    "scowl": ("scowl_tier",),
}

EVIDENCE_TIERS = ("listed_by_2_or_more", "listed_by_1", "none_with_corpus",
                  "none_no_corpus", "not_single_token", "not_measured",
                  "no_family_can_hold")


def _binary_cell(row: Row, column: str):
    """A binary evidence column's cell: None (null), -1, 0, or 1."""
    value = row[column]
    if is_null(value):
        return None
    if value not in (-1, 0, 1):
        raise ValueError(f"{column} holds {value!r}; the evidence columns "
                         "hold -1, 0, 1, or null")
    return int(value)


def family_cell(row: Row, family: str):
    """A family's cell for a row: 1 listed, 0 not listed, -1 the family
    cannot hold the row, None not measured.

    For a family of several columns (hunspell): 1 where any column is 1;
    otherwise None where any column is null; otherwise 0 where any column is
    0; otherwise -1. For SCOWL: 1 where `scowl_tier` is above 0, 0 where it
    is 0, -1 where it is -1, None where it is null."""
    if family == "scowl":
        tier = row["scowl_tier"]
        if is_null(tier):
            return None
        return 1 if tier > 0 else (0 if tier == 0 else -1)
    cells = [_binary_cell(row, c) for c in FAMILIES[family]]
    if 1 in cells:
        return 1
    if None in cells:
        return None
    return 0 if 0 in cells else -1


def family_cells(row: Row) -> dict[str, int | None]:
    """The 5 families' cells for a row, by family name."""
    return {family: family_cell(row, family) for family in FAMILIES}


def _evidence_tier(row: Row) -> str:
    if row["token_count"] > 1:
        return "not_single_token"
    cells = list(family_cells(row).values())
    listed = cells.count(1)
    if listed >= 2:
        return "listed_by_2_or_more"
    if None in cells:
        return "not_measured"
    if listed == 1:
        return "listed_by_1"
    if all(c == -1 for c in cells):
        return "no_family_can_hold"
    corpora = (row["gb_type"], row["wordfreq_scored"])
    if any(not is_null(c) and bool(c) for c in corpora):
        return "none_with_corpus"
    if any(is_null(c) for c in corpora):
        return "not_measured"
    return "none_no_corpus"


evidence_tier = Stratum(
    name="evidence_tier",
    columns=("token_count", "wordnet", "wiktionary_english", "hunspell_en_US",
             "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU", "enable1",
             "scowl_tier", "gb_type", "wordfreq_scored"),
    labels=EVIDENCE_TIERS,
    definition=(
        "For a single-token row, how many of the 5 published list families "
        "list it: WordNet (wordnet), Wiktionary (wiktionary_english), "
        "hunspell (any of the 4 hunspell_en_* columns), ENABLE (enable1), and "
        "SCOWL (scowl_tier above 0). listed_by_2_or_more: 2 or more families "
        "list it. listed_by_1: exactly 1 does, and no family is unmeasured. "
        "none_with_corpus: no family lists it, and Google Books (gb_type) or "
        "wordfreq (wordfreq_scored) holds it. none_no_corpus: no family lists "
        "it and neither corpus holds it. A family cell of -1 means the "
        "family cannot hold the row's kind of string: it counts as no "
        "listing and not as a 'not listed'. not_single_token: the row has "
        "more than 1 token, and the single-token sources were not measured "
        "over it. not_measured: a null cell leaves the tier undecided (the "
        "card gives a single-token row no null evidence cell). "
        "no_family_can_hold: every family cell is -1. "
        "A family here is not a source family of the vetted example list, "
        "which counts SCOWL and the en_US, en_CA, and en_AU dictionaries as "
        "1 family."),
    label_of=_evidence_tier)


# ---------------------------------------------------------------------------
# The spelling class
# ---------------------------------------------------------------------------

#: the flags in the order the spelling class takes the first one a row
#: carries: the rarer flags come first, so that they keep a stratum of their
#: own. `s-final` is a subclass of `apostrophe-form` and takes its label.
SPELLING_PRIORITY: tuple[tuple[str, str], ...] = (
    ("spaced", "spaced"), ("diaeresis", "diaeresis"),
    ("contraction", "contraction"), ("ligature", "ligature"),
    ("accented", "accented"), ("hyphenated", "hyphenated"),
    ("apostrophe-form", "apostrophe-form"), ("s-final", "apostrophe-form"))
SPELLING_FLAGS = frozenset(flag for flag, _ in SPELLING_PRIORITY) | {"plain"}
SPELLING_CLASSES = ("plain", "spaced", "diaeresis", "contraction", "ligature",
                    "accented", "hyphenated", "apostrophe-form")


def _spelling_class(row: Row) -> str:
    value = row["class_explicit"]
    if is_null(value):
        raise ValueError("class_explicit is null; the release never leaves it null")
    flags = set(filter(None, str(value).split(";")))
    unknown = flags - SPELLING_FLAGS
    if unknown:
        raise ValueError(f"class_explicit holds the unknown flag(s) {sorted(unknown)}")
    for flag, label in SPELLING_PRIORITY:
        if flag in flags:
            return label
    return "plain"


spelling_class = Stratum(
    name="spelling_class",
    columns=("class_explicit",),
    labels=SPELLING_CLASSES,
    definition=(
        "One label from the row's class flags (class_explicit), which are not "
        "exclusive. The label is the first of these flags the row carries, in "
        "this order: spaced, diaeresis, contraction, ligature, accented, "
        "hyphenated, apostrophe-form (which includes s-final). plain: the "
        "flags are only 'plain'. To stratify by the exact set of flags, pass "
        "the column name class_explicit to the sampler instead."),
    label_of=_spelling_class)


# ---------------------------------------------------------------------------
# The length band
# ---------------------------------------------------------------------------

#: the largest length of each band but the last
LENGTH_UPPER = (4, 6, 8, 10, 12, 16)
LENGTH_BANDS = ("01-04", "05-06", "07-08", "09-10", "11-12", "13-16", "17+")


def _length_label(row: Row) -> str:
    word = row["word"]
    if is_null(word) or not len(word):
        raise ValueError("the word column holds a null or an empty string")
    return LENGTH_BANDS[int(np.searchsorted(LENGTH_UPPER, len(word), side="left"))]


def _length_labels(frame: pd.DataFrame) -> np.ndarray:
    lengths = frame["word"].str.len()
    if lengths.isna().any() or (lengths < 1).any():
        raise ValueError("the word column holds a null or an empty string")
    index = np.searchsorted(LENGTH_UPPER, lengths.to_numpy(), side="left")
    return np.array(LENGTH_BANDS, dtype=object)[index]


length_band = Stratum(
    name="length_band",
    columns=("word",),
    labels=LENGTH_BANDS,
    definition=(
        "The number of characters of the string, as the card counts them "
        "(code points; spaces, hyphens, and apostrophes count), in bands: "
        "1 to 4, 5 to 6, 7 to 8, 9 to 10, 11 to 12, 13 to 16, and 17 or "
        "more, labeled 01-04, 05-06, 07-08, 09-10, 11-12, 13-16, and 17+."),
    label_of=_length_label,
    vectorized=_length_labels)


# ---------------------------------------------------------------------------
# The frequency band
# ---------------------------------------------------------------------------

#: the lower edge of each Zipf band above the first
FREQUENCY_EDGES = (2.0, 3.0, 4.0, 5.0)
NO_VALUE = "no_value"
FREQUENCY_BANDS = ("zipf_below_2", "zipf_2_to_3", "zipf_3_to_4", "zipf_4_to_5",
                   "zipf_5_or_more", NO_VALUE)


def _frequency_band(row: Row) -> str:
    value = row["wordfreq_zipf"]
    if is_null(value):
        return NO_VALUE
    return FREQUENCY_BANDS[int(np.searchsorted(FREQUENCY_EDGES, value, side="right"))]


frequency_band = Stratum(
    name="frequency_band",
    columns=("wordfreq_zipf",),
    labels=FREQUENCY_BANDS,
    definition=(
        "The wordfreq Zipf frequency of the string (the features config's "
        "wordfreq_zipf, a base-10 logarithm of occurrences per billion "
        "words), in half-open bands: below 2, 2 up to 3, 3 up to 4, 4 up to "
        "5, and 5 or more. no_value: the features config holds NaN, because "
        "wordfreq's list does not hold the string (and on every hyphenated "
        "string), or the row has no features row because it has more than 1 "
        "token. The universe config does not carry wordfreq_zipf: join it "
        "with ceolkit.join_features."),
    label_of=_frequency_band)


# ---------------------------------------------------------------------------
# Columns used as they are
# ---------------------------------------------------------------------------

def _column_label(column: str) -> Callable[[Row], str]:
    def label_of(row: Row) -> str:
        value = row[column]
        if is_null(value):
            raise ValueError(f"{column} is null; the release never leaves it null")
        return str(value)
    return label_of


intake_layer = Stratum(
    name="intake_layer",
    columns=("intake_layer",),
    labels=("c1_exceptions", "c4_additions", "eol_invalid", "eol_valid",
            "spaced_c015"),
    definition=("The layer the row entered by: the value of intake_layer. "
                "It is the stratum of the kit's fixtures."),
    label_of=_column_label("intake_layer"))

model_or_engine = Stratum(
    name="model_or_engine",
    columns=("model_or_engine",),
    labels=("engine_generated", "none"),
    definition=(
        "Whether the English OpenList's synthetic engine made the row: the "
        "value of model_or_engine. engine_generated: made by the EOL's "
        "synthetic engine. none: every other row. A published row says "
        "nothing else about how the OpenList took a word in "
        "(research/release/withholding.py, without_eol_intake)."),
    label_of=_column_label("model_or_engine"))


# ---------------------------------------------------------------------------
# The registry, and strata combined
# ---------------------------------------------------------------------------

STRATA: dict[str, Stratum] = {s.name: s for s in (
    evidence_tier, spelling_class, length_band, frequency_band, intake_layer,
    model_or_engine)}


def combine(*parts: Stratum, name: str | None = None) -> Stratum:
    """A stratum whose label is the labels of `parts` joined by '|', such as
    `combine(evidence_tier, length_band)`: one stratum for each pair."""
    if len(parts) < 2:
        raise ValueError("combine needs 2 or more strata")
    columns = tuple(dict.fromkeys(c for p in parts for c in p.columns))

    def label_of(row: Row) -> str:
        return "|".join(p.label_of(row) for p in parts)

    def vectorized(frame: pd.DataFrame) -> list[str]:
        each = [p.label_frame(frame) for p in parts]
        return ["|".join(labels) for labels in zip(*each)]

    return Stratum(
        name=name or "+".join(p.name for p in parts),
        columns=columns,
        labels=(),
        definition="the labels of " + ", ".join(p.name for p in parts)
                   + " joined by '|'",
        label_of=label_of,
        vectorized=vectorized)
