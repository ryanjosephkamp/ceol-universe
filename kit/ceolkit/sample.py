"""The deterministic stratified sampler.

    sample, manifest = draw(table, stratum, n, seed)

The rule, stated once (`RULE`): within each stratum, the rows are ranked in
ascending order by the hex digest of `sha256(f"{seed}:{stratum}:{word}")`,
and the first N of each stratum are taken. `stratum` is the stratum's label
and `word` is the candidate string. Anyone holding the same rows, the same
stratum labels, and the same seed gets the same sample, in any row order.

The seed is public. Choose it and write it down before looking at the data
(`PREREGISTRATION_TEMPLATE.md`); do not pick it by trying seeds.

The sample is the head of the ranking, so a sample of N rows for a stratum
is the first N rows of a sample of any larger N. That lets a pilot be the
head of the main sample. The sampler never prints a candidate.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
import pyarrow as pa

from . import __version__
from .load import to_frame
from .strata import Stratum, is_null

RULE = ("within each stratum, rows are ranked in ascending order by the hex "
        "digest of sha256(f\"{seed}:{stratum}:{word}\".encode(\"utf-8\")), and "
        "the first N of each stratum are taken")

#: the columns the sampler adds to the rows it returns
STRATUM_COLUMN = "sample_stratum"
RANK_COLUMN = "sample_rank"


def rank_key(seed: str, stratum: str, word: str) -> str:
    """The key a row is ranked by: the hex digest of
    sha256(f"{seed}:{stratum}:{word}"), UTF-8 encoded."""
    return hashlib.sha256(f"{seed}:{stratum}:{word}".encode("utf-8")).hexdigest()


def label_text(value: Any) -> str:
    """A stratum label as text. Text stays as it is; a boolean is "true" or
    "false"; an integer, or a float with an integer value, is its decimal
    digits; null (None or NaN) is "null"; another float is its repr."""
    if is_null(value):
        return "null"
    if isinstance(value, (bool, np.bool_)):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return str(int(value)) if float(value).is_integer() else repr(float(value))
    return str(value)


def draw(table, stratum, n, seed: str, *, id_column: str = "id",
         word_column: str = "word", source: Mapping | None = None):
    """Draw a stratified sample. Returns `(sample, manifest)`.

    table    a pyarrow.Table or a pandas.DataFrame with one row for each
             candidate: a word column, and an id column if it has one (an
             id is computed from the word otherwise: the first 16 hex digits
             of its sha256).
    stratum  how to label each row: the name of a column (the label is the
             column's value as `label_text` gives it), a `Stratum` from
             `ceolkit.strata`, or a function of a row that returns a label.
             A function receives a dict of the whole row; null arrives as
             None or NaN.
    n        the rows to take from each stratum: an int, or a dict from a
             label to a count. With a dict, a stratum it does not name is not
             sampled, and a label the table does not have is an error. A
             stratum with fewer rows than asked for gives all of them, and
             the manifest says so.
    seed     the seed, a non-empty string.
    source   optionally, a dict that describes where the rows came from
             (the dataset version, the config, the file's sha256); it is
             recorded in the manifest as it is.

    The sample holds the selected rows, with every column of the input and
    two more, `sample_stratum` and `sample_rank` (1 for the first row of its
    stratum). It is ordered by stratum label, then by rank, so it does not
    depend on the order of the input. It is the same kind of table as the
    input.

    The manifest records everything that fixes the sample, and no candidate:
    the rule, the seed, the stratum, N, the rows of the input, the rows
    available and selected in each stratum, and `selected_ids_sha256`, the
    sha256 of the selected ids sorted and joined by newlines.
    """
    if not isinstance(seed, str) or not seed:
        raise ValueError("the seed must be a non-empty string")
    if isinstance(table, pa.Table):
        kind = "arrow"
    elif isinstance(table, pd.DataFrame):
        kind = "pandas"
    else:
        raise TypeError("expected a pyarrow.Table or a pandas.DataFrame, "
                        f"not {type(table).__name__}")
    if not isinstance(n, Mapping):
        _check_count(n)
    else:
        for count in n.values():
            _check_count(count)

    names = set(table.column_names if kind == "arrow" else table.columns)
    if word_column not in names:
        raise KeyError(f"the table has no column {word_column!r}")
    clash = [c for c in (STRATUM_COLUMN, RANK_COLUMN) if c in names]
    if clash:
        raise ValueError(f"the table already has the column(s) {clash}, "
                         "which the sampler adds")

    name, definition, labels = _labels(table, stratum, kind, names)
    words = to_frame(table, [word_column])[word_column].tolist()
    if any(not isinstance(w, str) for w in words):
        raise ValueError(f"the {word_column} column holds a value that is not text")
    if id_column in names:
        ids = to_frame(table, [id_column])[id_column].tolist()
    else:
        ids = [hashlib.sha256(w.encode("utf-8")).hexdigest()[:16] for w in words]
    if len(set(ids)) != len(ids):
        raise ValueError("the table holds the same id twice; the sampler "
                         "takes 1 row for each candidate")

    codes, uniques = pd.factorize(pd.Series(labels, dtype=object), sort=True)
    available = np.bincount(codes, minlength=len(uniques))
    if isinstance(n, Mapping):
        absent = sorted(set(n) - set(uniques))
        if absent:
            raise ValueError(f"n names strata the table does not have: {absent}")
    order = np.argsort(codes, kind="stable")
    starts = np.concatenate(([0], np.cumsum(available)))

    positions: list[int] = []
    strata_of: list[str] = []
    ranks: list[int] = []
    per_stratum: dict[str, dict[str, int]] = {}
    short: list[str] = []
    for code, label in enumerate(uniques):
        want = n.get(label, 0) if isinstance(n, Mapping) else n
        members = order[starts[code]:starts[code + 1]].tolist()
        chosen = _first(seed, label, words, ids, members, want)
        positions.extend(chosen)
        strata_of.extend([label] * len(chosen))
        ranks.extend(range(1, len(chosen) + 1))
        per_stratum[label] = {"available": int(available[code]),
                              "selected": len(chosen)}
        if len(chosen) < want:
            short.append(label)

    selected_ids = sorted(ids[p] for p in positions)
    manifest = {
        "kit": "ceolkit",
        "kit_version": __version__,
        "rule": RULE,
        "seed": seed,
        "stratum": name,
        "stratum_definition": definition,
        "n": ({k: int(v) for k, v in n.items()} if isinstance(n, Mapping)
              else int(n)),
        "input_rows": len(words),
        "strata": per_stratum,
        "short_strata": short,
        "selected_rows": len(positions),
        "selected_ids_sha256": hashlib.sha256(
            "\n".join(selected_ids).encode("utf-8")).hexdigest(),
    }
    if source is not None:
        manifest["source"] = json.loads(json.dumps(dict(source)))

    if kind == "arrow":
        sample = table.take(pa.array(positions, type=pa.int64()))
        sample = sample.append_column(STRATUM_COLUMN, pa.array(strata_of, pa.string()))
        sample = sample.append_column(RANK_COLUMN, pa.array(ranks, pa.int32()))
    else:
        sample = table.iloc[positions].reset_index(drop=True)
        sample[STRATUM_COLUMN] = pd.Series(strata_of, dtype=object)
        sample[RANK_COLUMN] = pd.Series(ranks, dtype="int32")
    return sample, manifest


def _check_count(count: Any) -> None:
    if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
        raise ValueError(f"n must be a non-negative integer, not {count!r}")


def _first(seed: str, label: str, words: list[str], ids: list[str],
           members: list[int], want: int) -> list[int]:
    """The positions of the first `want` rows of a stratum in rank order.
    Rows are compared by the digest's bytes, which order as its hex form
    does, then by id."""
    if want <= 0:
        return []
    prefix = f"{seed}:{label}:"
    keyed = ((hashlib.sha256((prefix + words[p]).encode("utf-8")).digest(),
              ids[p], p) for p in members)
    return [p for _, _, p in heapq.nsmallest(want, keyed)]


def _labels(table, stratum, kind: str, names: set):
    """The stratum's name, its definition, and every row's label as text."""
    if isinstance(stratum, str):
        if stratum not in names:
            raise KeyError(f"the table has no column {stratum!r}")
        series = to_frame(table, [stratum])[stratum]
        return (stratum, f"the value of the column {stratum}",
                [label_text(v) for v in series.tolist()])
    if isinstance(stratum, Stratum):
        frame = to_frame(table, [c for c in stratum.columns if c in names])
        labels = stratum.label_frame(frame)
        return stratum.name, stratum.definition, [label_text(v) for v in labels]
    if callable(stratum):
        rows = to_frame(table).to_dict("records")
        label_of: Callable = stratum
        doc = (getattr(stratum, "__doc__", None) or "").strip().split("\n")[0]
        return (getattr(stratum, "__name__", "function"),
                doc or "a function of the row",
                [label_text(label_of(row)) for row in rows])
    raise TypeError("stratum must be a column name, a Stratum, or a function "
                    f"of a row, not {type(stratum).__name__}")
