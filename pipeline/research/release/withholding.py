"""The public projection: what a public version withholds from a row, and
which rows it holds back.

This module is the projection's rule. `build_release` applies it to build
v2.1 from the pinned layers, and the fixtures (`tools/build_fixtures.py`)
and the vetted example list (`safeguards/examples.py`) read it. It states:

- **The withheld lists:** NWL2023 and CSW21 (the archive's C-079 line 2(a)),
  SOWPODS (C-079 line 2(b); C-083 line 5), and web2 and web2a (C-083 line 5,
  its condition met: the 1961 renewal holds, the review's §1.2). Their
  evidence columns are dropped, and every label naming them is removed from
  `sources`, `intake_channels`, and `panel_sets`.
- **The withheld channel labels** (D-010 line 1, and D-012 line 2's 2,
  withheld for the same reason): removed from `intake_channels`. A row whose every
  channel label is withheld carries the single label `eol:channel-withheld`
  (D-011 line 3).
- **The withheld feature columns** (D-013): the 10 computed against a
  reference that holds web2 or web2a, and the 2 of the character model,
  whose training pool the withheld lists help choose.
- **The recomputation** (C-079 line 2(c)): `panel_sets`, `panel_count`, and
  `provenance_class` over the published fields. A row has a channel when a
  published label remains, that is a label other than
  `eol:phase1-unrecorded` and `eol:channel-withheld`; it has containment
  when a published panel set lists it or a corpus holds it.
- **The OpenList's intake** (`without_eol_intake`): no field of a row on the
  English OpenList's list may depend on how the OpenList took the word in.
  Its `eol:` channel labels go, except those of the intakes the OpenList's
  own records name, and a row left with none carries `eol:list`;
  `eol_phase1_tier` is `none`; the model values of `model_or_engine` are
  `none`; and `provenance_class` is computed again. The fixtures apply it
  to their rows.
- **The rows held back** (D-011 lines 1 and 2, D-012 line 1): a row with no
  public evidence (provenance class `neither` over the published fields)
  that had some over the full fields; and a census or audit row whose every
  `sources` label names a withheld list. It stays in the private record.
- **The reach guard's counts** (`project_and_measure`): for each published
  channel label, and each layer's shipped rows whose sources come out empty,
  how many rows each withheld list lists. The release build refuses where 1
  list lists `REACH_THRESHOLD` of them or more.

The rows only NWL2023 and CSW21 attest (C-009) are not in any projection;
`is_restricted` excludes them before this rule applies.
"""

from __future__ import annotations

from research.provenance import build_provenance as BP
from research.universe import repin
from research.release import columns

#: the withheld lists: C-079 line 2(a) and 2(b); C-083 line 5 (D-010)
WITHHELD_SETS: tuple[str, ...] = ("nwl2023", "csw21", "sowpods_legacy",
                                  "web2", "web2a")

#: the panel sets a public version names, in `panel_sets`' order
PUBLISHED_SETS: tuple[str, ...] = tuple(
    s for s in columns.PANEL_SETS if s not in WITHHELD_SETS)

#: the columns of the universe config a public version carries
PUBLISHED_UNIVERSE_COLUMNS: tuple[str, ...] = tuple(
    c for c in columns.UNIVERSE_COLUMNS if c not in WITHHELD_SETS)

#: the published columns that may hold a null, and those null exactly on
#: the spaced rows (AT-UR1-2, AT-UR1-4)
PUBLISHED_NULLABLE: frozenset[str] = columns.UNIVERSE_NULLABLE - set(WITHHELD_SETS)
PUBLISHED_SPACED_NULL: tuple[str, ...] = tuple(
    c for c in columns.SPACED_NULL if c not in WITHHELD_SETS)

#: the feature columns computed against a reference that holds a withheld
#: list (research/features/build_features.py: the base reference is WordNet
#: and web2, and the class-capable reference includes web2a). A value can
#: reveal whether web2 or web2a lists a string's OCR neighbor, its stem, or
#: its segments, so a public version withholds them (D-013 line 1).
WITHHELD_REFERENCE_FEATURES: tuple[str, ...] = (
    "ocr_neighbor_hits", "ocr_neighbor_freq_ratio", "ocr_apostrophe_ratio",
    "ocr_ligature_ratio", "ocr_hyphen_drop_ratio", "ocr_strip_ratio",
    "ocr_hyphen_junction_ratio", "morph_productivity_vn", "morph_has_parse",
    "segment_attested_fraction")

#: the feature columns of the character model, fitted on a pool that the
#: withheld lists help choose. Against a model fitted on the published sets
#: alone, their values pick out the rows the withheld lists list
#: (research/release/feature_leak.py and its record), so a public version
#: withholds them (D-013 line 2; docs/licenses/FEATURE_COLUMNS.md).
WITHHELD_MODEL_FEATURES: tuple[str, ...] = (
    "orthotactic_logp_total", "orthotactic_logp_per_char")

#: every feature column a public version withholds
WITHHELD_FEATURES: tuple[str, ...] = (WITHHELD_MODEL_FEATURES
                                      + WITHHELD_REFERENCE_FEATURES)

#: the feature layer's columns a public version carries
PUBLISHED_FEATURE_COLUMNS: tuple[str, ...] = tuple(
    c for c in columns.FEATURE_LAYER_COLUMNS if c not in WITHHELD_FEATURES)

#: the prefixes a label of `sources` or `intake_channels` may carry before
#: a set's name; the bare name is a label of `sources` on the CEOL's layers
LABEL_PREFIXES: tuple[str, ...] = ("", "eol:", "audit:", "census:", "spaced:")

WITHHELD_LABELS: frozenset[str] = frozenset(
    prefix + name for name in WITHHELD_SETS for prefix in LABEL_PREFIXES)

#: the channel labels withheld under the 6th question (D-010 line 1), and the
#: 2 that D-012 line 2 withholds for the same reason
WITHHELD_CHANNEL_LABELS: frozenset[str] = frozenset({
    BP.WITHHELD_SOURCE_LABEL, "eol:collins", "eol:coca_frequency",
    "eol:dictionary-api:merriam-webster", "eol:linux", "eol:nltk"})

#: the label the provenance layer gives a row with no recorded channel
UNRECORDED = "eol:phase1-unrecorded"

#: the label a public version gives a row whose every channel is withheld
#: (D-011 line 3)
CHANNEL_WITHHELD = "eol:channel-withheld"

CLASSES = ("channel_and_containment", "channel_only", "containment_only",
           "neither")

#: The tag the pin's `sources` carries on every string inherited from the EOL
#: (C-008; columns.PIN), in place of a per-source list.
INHERITED_SOURCES_TAG = repin.TAG

#: Every label a public version's `intake_channels` may carry: the provenance
#: layer's closed vocabulary (build_provenance.VOCABULARY) without the
#: withheld labels, and the marker. AT-UR1-12 holds a file to this allow
#: list, so a label form the projection misses fails the build instead of
#: passing it.
PUBLISHED_CHANNEL_LABELS: frozenset[str] = frozenset(
    (BP.VOCABULARY - WITHHELD_LABELS - WITHHELD_CHANNEL_LABELS)
    | {CHANNEL_WITHHELD, "eol:list"})

#: Every label a public version's `sources` may carry: the CEOL layers'
#: source names (bare, and `eol:`-prefixed on the audit's additions), the
#: intake ledger's source, and the inherited tag, without the withheld lists'.
PUBLISHED_SOURCE_LABELS: frozenset[str] = frozenset(
    (set(BP.CENSUS_SOURCES) | set(BP.AUDIT_SOURCES) | set(BP.SPACED_SOURCES)
     | {f"eol:{name}" for name in BP.AUDIT_SOURCES}
     | {BP.LEDGER_SOURCE, INHERITED_SOURCES_TAG}) - WITHHELD_LABELS)


class UncoveredRow(ValueError):
    """A row the projection would hold back for a reason D-011 does not
    rule: every listing withheld (line 1) or a withheld channel label its only
    evidence (line 2). The projection refuses rather than guess."""

#: the reasons a row is held back, as the release record counts them
HELD_BACK_REASONS = {
    "tier_2": "D-011 line 1: every listing a withheld list, and no public "
              "evidence left",
    "withheld_channel": "D-011 line 2: a withheld channel label its only "
                        "evidence, and no public evidence left",
    "withheld_sources": "D-012 line 1: a census or audit row whose every "
                        "source label names a withheld list",
}

#: the CEOL's own layers whose `sources` names the sources that contain the
#: string, so that a row whose every label is withheld would show that a
#: withheld list holds it (D-012 line 1)
SOURCE_LISTING_LAYERS: tuple[str, ...] = ("c1_exceptions", "c4_additions")

#: the published fields whose counts a reader could difference between v2.0
#: and a public version, so that every held-back count they show is 0 or at
#: least the floor
DIFFERENCED: tuple[str, ...] = ("intake_layer", "intake_kind", "class_explicit")

#: the reach guard's bound: no
#: published channel label, and no layer's rows whose sources come out
#: empty, may have this share or more of its rows listed by 1 withheld list
REACH_THRESHOLD = 0.99


def published_labels(joined: str | None) -> str | None:
    """A ';'-joined label field without the labels that name a withheld
    list. A null stays a null."""
    if joined is None:
        return None
    return ";".join(label for label in joined.split(";")
                    if label and label not in WITHHELD_LABELS)


def published_channels(joined: str | None) -> str | None:
    """`intake_channels` without the labels that name a withheld list and
    without the withheld channel labels; `eol:channel-withheld` where every
    label was withheld. A null stays a null."""
    if joined is None:
        return None
    labels = [label for label in joined.split(";") if label]
    kept = [label for label in labels if label not in WITHHELD_LABELS
            and label not in WITHHELD_CHANNEL_LABELS]
    if kept:
        return ";".join(kept)
    return CHANNEL_WITHHELD if labels else ""


def published_panel_sets(joined: str) -> str:
    return ";".join(name for name in joined.split(";")
                    if name and name not in WITHHELD_SETS)


def has_channel(intake_channels: str | None) -> bool:
    """Whether a published channel label remains."""
    return bool(intake_channels) and intake_channels not in (UNRECORDED,
                                                             CHANNEL_WITHHELD)


def provenance_class(intake_channels: str, panel_count: int,
                     gb_type: bool | None, wordfreq_scored: bool | None) -> str:
    """The provenance layer's class (`build_provenance.provenance_class`),
    over the published fields: a published channel, and containment by a
    published panel set or by a corpus."""
    channel = has_channel(intake_channels)
    contained = panel_count >= 1 or bool(gb_type) or bool(wordfreq_scored)
    if channel:
        return CLASSES[0] if contained else CLASSES[1]
    return CLASSES[2] if contained else CLASSES[3]


def only_withheld_listings(full_panel_sets: str | None) -> bool:
    """Whether a row's full `panel_sets` names 1 or more sets, all withheld
    (tier 2); the 1 test both forms of the projection use."""
    listed = [s for s in (full_panel_sets or "").split(";") if s]
    return bool(listed) and all(s in WITHHELD_SETS for s in listed)


def carries_a_withheld_channel(full_channels: str | None) -> bool:
    """Whether a row's full `intake_channels` holds a label of D-010 line 1."""
    return bool(set((full_channels or "").split(";")) & WITHHELD_CHANNEL_LABELS)


def emptied_sources(intake_layer: str | None, full_sources: str | None) -> bool:
    """Whether a census or audit row's every `sources` label names a withheld
    list (D-012 line 1)."""
    return (intake_layer in SOURCE_LISTING_LAYERS and bool(full_sources)
            and published_labels(full_sources) == "")


def held_back_reason(full_class: str, full_panel_sets: str,
                     public_class: str, full_channels: str | None,
                     intake_layer: str | None, full_sources: str | None
                     ) -> str | None:
    """Why a row is held back (a key of HELD_BACK_REASONS), or None where it
    ships: it has no public evidence and had some over the full fields
    (D-011), or it is a census or audit row whose every source label is
    withheld (D-012 line 1). The reason is checked, never assumed: a row
    with no public evidence that is neither tier 2 nor carries a withheld
    channel label raises UncoveredRow."""
    if public_class == CLASSES[3] and full_class != CLASSES[3]:
        if only_withheld_listings(full_panel_sets):
            return "tier_2"
        if carries_a_withheld_channel(full_channels):
            return "withheld_channel"
        # D-012 line 1 rules on a census or audit row whose channel is a
        # withheld list's census or audit label
        if emptied_sources(intake_layer, full_sources):
            return "withheld_sources"
        raise UncoveredRow("a row would be held back for a reason D-011 and "
                           "D-012 do not rule")
    if emptied_sources(intake_layer, full_sources):
        return "withheld_sources"
    return None


def published_row(row: dict) -> dict | None:
    """A row of v2.0's universe config as a public version carries it, or
    None where the row is held back."""
    out = {name: row[name] for name in PUBLISHED_UNIVERSE_COLUMNS}
    out["sources"] = published_labels(row["sources"])
    out["intake_channels"] = published_channels(row["intake_channels"])
    out["panel_sets"] = published_panel_sets(row["panel_sets"])
    out["panel_count"] = len(out["panel_sets"].split(";")) if out["panel_sets"] else 0
    out["provenance_class"] = provenance_class(
        out["intake_channels"], out["panel_count"], row["gb_type"],
        row["wordfreq_scored"])
    if held_back_reason(row["provenance_class"], row["panel_sets"],
                        out["provenance_class"], row["intake_channels"],
                        row["intake_layer"], row["sources"]):
        return None
    return without_eol_intake(out)


#: The `eol:` channel labels a row on the English OpenList's list keeps: the
#: intakes the OpenList's own records name (its synthetic engine, its domain
#: extracts, the Free Dictionary API, and its nightly promotions).
EOL_PUBLISHED_INTAKE_CHANNELS: frozenset[str] = frozenset({
    "eol:synthetic-engine", "eol:authoritative-extracts",
    "eol:extended-domain-sources", "eol:dictionary-api:free-dictionary",
    "eol:invalid-list-recovery"})

#: The label a row on the OpenList's list carries when none of those remain:
#: the string came in with the OpenList's list, and the row says no more.
EOL_LIST = "eol:list"

#: The `model_or_engine` values a row on the OpenList's list keeps; a model
#: value is a fact of how the OpenList took the string in, and becomes `none`.
PUBLISHED_MODEL_OR_ENGINE: frozenset[str] = frozenset({"engine_generated", "none"})


def list_row_channels(joined: str | None) -> str:
    """`intake_channels` of a row on the OpenList's list: its `eol:` labels
    without those the OpenList's records don't name, and `eol:list` where
    no `eol:` label remains. A CEOL layer's own labels stay."""
    labels = [label for label in (joined or "").split(";") if label]
    kept = [label for label in labels
            if not label.startswith("eol:") or label in EOL_PUBLISHED_INTAKE_CHANNELS]
    if not any(label.startswith("eol:") for label in kept):
        kept.append(EOL_LIST)
    return ";".join(kept)


def without_eol_intake(row: dict) -> dict:
    """A published row with no field that depends on how the English
    OpenList took in a word on its list (`eol` true). Its `eol:` channel
    labels go, except those of the intakes the OpenList's records name;
    a row left with none carries `eol:list`. `eol_phase1_tier` is `none`, a
    model value of `model_or_engine` is `none`, and `provenance_class` is
    computed again. The OpenList's own records follow the same rule. A row
    not on the list (a candidate, or a CEOL layer's row) is returned as it
    is. Edits and returns `row`."""
    if not row.get("eol"):
        return row
    row["intake_channels"] = list_row_channels(row.get("intake_channels"))
    if "eol_phase1_tier" in row:
        row["eol_phase1_tier"] = "none"
    if row.get("model_or_engine") not in (None, *PUBLISHED_MODEL_OR_ENGINE):
        row["model_or_engine"] = "none"
    row["provenance_class"] = provenance_class(
        row["intake_channels"], row["panel_count"], row["gb_type"],
        row["wordfreq_scored"])
    return row


def reveals_a_withheld_list(row: dict) -> list[str]:
    """The fields of a published row that still name a withheld list or a
    withheld channel label; empty for every row `published_row` returns."""
    found = [name for name in WITHHELD_SETS if name in row]
    for field in ("sources", "intake_channels", "panel_sets"):
        labels = set((row.get(field) or "").split(";"))
        if labels & (WITHHELD_LABELS | set(WITHHELD_SETS) | WITHHELD_CHANNEL_LABELS):
            found.append(field)
    return found


# ---------------------------------------------------------------------------
# The projection over a whole table (pyarrow), for the release build
# ---------------------------------------------------------------------------

def _map(column, fn):
    """A low-cardinality string column through `fn`, value by distinct value."""
    import pyarrow as pa
    import pyarrow.compute as pc
    encoded = pc.dictionary_encode(column)
    if isinstance(encoded, pa.ChunkedArray):
        encoded = encoded.combine_chunks()
    values = pa.array([fn(v) for v in encoded.dictionary.to_pylist()],
                      pa.string())
    return values.take(encoded.indices)


def classes_of(channels, panel_count, gb_type, wordfreq_scored):
    """`provenance_class` over published fields, for whole columns (the
    vector form of `provenance_class`)."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    channel = _map(channels, lambda v: "1" if has_channel(v) else "")
    channel = pc.equal(channel, "1").to_numpy(zero_copy_only=False)
    contained = (pc.fill_null(panel_count, 0).to_numpy(zero_copy_only=False) >= 1) \
        | pc.fill_null(gb_type, False).to_numpy(zero_copy_only=False) \
        | pc.fill_null(wordfreq_scored, False).to_numpy(zero_copy_only=False)
    klass = np.where(channel, np.where(contained, 0, 1),
                     np.where(contained, 2, 3))
    return pa.array(np.array(CLASSES, dtype=object)[klass], pa.string())


def project(table):
    """The public projection of a full universe table (the columns of
    `columns.UNIVERSE_COLUMNS`, in its order).

    Returns the public table (the rows that ship, the columns of
    `PUBLISHED_UNIVERSE_COLUMNS` and any columns the table carries after
    them, the projected fields replaced) and the held-back rows' words and
    reasons as a table."""
    public, held, _reach = project_and_measure(table, measure=False)
    return public, held


def project_and_measure(table, measure: bool = True):
    """`project`, and the reach the release build's guard reads: for each
    published channel label, and for each layer's shipped rows whose sources
    come out empty, its rows and how many of them each withheld list lists
    (in the full `panel_sets`). Counts only; they belong in a private
    receipt, never in a committed file."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    sources = _map(table["sources"], published_labels)
    channels = _map(table["intake_channels"], published_channels)
    sets = _map(table["panel_sets"], published_panel_sets)
    count = pc.list_value_length(pc.split_pattern(sets, ";"))
    count = pc.cast(pc.if_else(pc.equal(sets, ""), 0, count), pa.int16())
    public_class = classes_of(channels, count, table["gb_type"],
                              table["wordfreq_scored"])
    public_neither = pc.equal(public_class, CLASSES[3]).to_numpy(
        zero_copy_only=False)
    full_neither = pc.equal(table["provenance_class"], CLASSES[3]).to_numpy(
        zero_copy_only=False)
    held = public_neither & ~full_neither
    tier2 = _map(table["panel_sets"],
                 lambda v: "1" if only_withheld_listings(v) else "")
    tier2 = pc.equal(tier2, "1").to_numpy(zero_copy_only=False)
    channel = _map(table["intake_channels"],
                   lambda v: "1" if carries_a_withheld_channel(v) else "")
    channel = pc.equal(channel, "1").to_numpy(zero_copy_only=False)
    # D-012 line 1: a census or audit row whose every source label is withheld
    emptied = (pc.is_in(table["intake_layer"], value_set=pa.array(
        list(SOURCE_LISTING_LAYERS))).to_numpy(zero_copy_only=False)
        & pc.not_equal(table["sources"], "").to_numpy(zero_copy_only=False)
        & pc.equal(sources, "").to_numpy(zero_copy_only=False))
    uncovered = held & ~tier2 & ~channel & ~emptied
    if uncovered.any():
        raise UncoveredRow(f"{int(uncovered.sum())} row(s) would be held back "
                           "for a reason D-011 and D-012 do not rule")
    reason = np.where(held & tier2, "tier_2",
                      np.where(held & channel, "withheld_channel",
                               "withheld_sources"))
    held = held | emptied

    # the OpenList's intake (`without_eol_intake`), on the rows of its list;
    # applied after the rows held back are decided, so it ships no row the
    # projection holds back and holds back none it ships
    on_list = pc.fill_null(pc.cast(table["eol"], pa.bool_()), False)
    channels = pc.if_else(on_list, _map(channels, list_row_channels), channels)
    public_class = classes_of(channels, count, table["gb_type"],
                              table["wordfreq_scored"])
    replaced = {"sources": sources, "intake_channels": channels,
                "panel_sets": sets, "panel_count": count,
                "provenance_class": public_class}
    if "model_or_engine" in table.column_names:
        moe = pc.cast(table["model_or_engine"], pa.string())
        kept = pc.fill_null(pc.is_in(moe, value_set=pa.array(
            sorted(PUBLISHED_MODEL_OR_ENGINE))), True)
        replaced["model_or_engine"] = pc.if_else(
            pc.and_(on_list, pc.invert(kept)), pa.scalar("none"), moe)
    if "eol_phase1_tier" in table.column_names:
        replaced["eol_phase1_tier"] = pc.if_else(
            on_list, pa.scalar("none"), pc.cast(table["eol_phase1_tier"], pa.string()))
    names = list(PUBLISHED_UNIVERSE_COLUMNS) + [
        c for c in table.column_names if c not in columns.UNIVERSE_COLUMNS]
    public = pa.table({name: replaced.get(name, table[name]) for name in names})
    keep = pa.array(~held)
    mask = pa.array(held)
    # the private file: the word, the reason, and the published fields by
    # which v2.0's and v2.1's counts could be differenced (N-12's floor)
    held_rows = pa.table({
        "word": table["word"].filter(mask),
        "reason": pa.array(reason[held], pa.string()),
        **{name: table[name].filter(mask) for name in DIFFERENCED
           if name in table.column_names}})
    reach = _reach(table, channels, sources, ~held) if measure else None
    return public.filter(keep), held_rows, reach


def _reach(table, channels, sources, shipped) -> dict:
    """The counts the reach guard reads (see `project_and_measure`)."""
    import collections
    import pyarrow as pa
    import pyarrow.compute as pc
    withheld = _map(table["panel_sets"], lambda v: ";".join(
        s for s in WITHHELD_SETS if s in (v or "").split(";")))
    empty = pc.equal(sources, "")
    frame = pa.table({"channels": channels, "withheld": withheld,
                      "layer": table["intake_layer"], "empty": empty}
                     ).filter(pa.array(shipped))
    groups = frame.group_by(["channels", "withheld", "layer", "empty"]
                            ).aggregate([([], "count_all")]).to_pylist()
    labels: dict = collections.defaultdict(collections.Counter)
    cells: dict = collections.defaultdict(collections.Counter)
    for g in groups:
        n, lists = g["count_all"], [s for s in g["withheld"].split(";") if s]
        for label in filter(None, (g["channels"] or "").split(";")):
            labels[label]["rows"] += n
            for s in lists:
                labels[label][s] += n
        if g["empty"]:
            cell = f"{g['layer']} with empty sources"
            cells[cell]["rows"] += n
            for s in lists:
                cells[cell][s] += n
    return {"labels": {k: dict(v) for k, v in sorted(labels.items())},
            "empty_sources": {k: dict(v) for k, v in sorted(cells.items())}}


def reach_breaches(reach: dict, threshold: float = REACH_THRESHOLD
                   ) -> list[str]:
    """The labels and cells of which 1 withheld list lists `threshold` or
    more of the rows, as "name: list" (no count)."""
    out = []
    for kind in ("labels", "empty_sources"):
        for name, counts in reach[kind].items():
            rows = counts.get("rows", 0)
            for s in WITHHELD_SETS:
                if rows and counts.get(s, 0) / rows >= threshold:
                    out.append(f"{name}: {s}")
    return out
