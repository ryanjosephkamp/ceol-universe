"""
P3 of the intake-provenance package (C-064): the layer.

data/universe_v2_provenance.parquet — one row per candidate of the C-016
pin, in the pin's order, joined by word; gitignored, because it holds
every row, the 1,985 restricted ones included. It records provenance in
the two senses C-064 names and keeps them apart:

  - the INTAKE CHANNEL through which a string entered the pool: for the
    9,653,999 inherited strings, read from the EOL's two dictionaries at
    revision c1139698 (the discovery log `candidate_source` and the
    `source` field) — recorded as the channel and never read as
    attestation, which is the reading the EOL's D-003 and C-008 forbid;
    for the CEOL's own layers, read from the pin's `sources` column;
  - the MEASURED CONTAINMENT in the thirteen panel sets and the two
    corpora, already held by data/evidence.parquet (C-010) and
    data/features.parquet (C-011).

Every row then falls into exactly one provenance class: channel and
containment, channel only, containment only, neither. Nothing here
labels validity, moves a stratum, or adds or removes a candidate; the
pin is read and never written.

research/provenance/provenance.json (committed) holds the counts and no
candidate word. `measure()` re-derives its measured block from the
parquet alone, which is what `check_provenance` runs.

Run:  python3 -m research.provenance.build_provenance
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ceol.ingest.common import sha256_file

from .build_eol_dictionaries_manifest import (DEMOTION_LEDGERS, LAYERS,
                                               demoted_generated_forms,
                                               intake_layers, read_ledger)
from .extract_eol_intake import INVALID, VALID
from .synthetic_engine import infer_engine

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
OUT_DIR = REPO / "research" / "provenance"
PIN_PARQUET = DATA_DIR / "universe_v2.parquet"
EVIDENCE_PARQUET = DATA_DIR / "evidence.parquet"
FEATURES_PARQUET = DATA_DIR / "features.parquet"
OUT_PARQUET = DATA_DIR / "universe_v2_provenance.parquet"
OUT_JSON = OUT_DIR / "provenance.json"
MANIFEST = OUT_DIR / "eol_dictionaries_manifest.json"
EVIDENCE_JSON = REPO / "research" / "evidence" / "evidence.json"
FEATURES_JSON = REPO / "research" / "features" / "features.json"
#: data/features.parquet has no committed hash record of its own; this
#: is the value recorded for it on September 16, 2026 and the one
#: the source breakdown was computed over.
FEATURES_SHA256 = \
    "c578289b61d7b957bba1c91b9e65d3dbfcde3c5d74098316f6993643f240b7c7"

KINDS = ("obtained", "derived", "generated")
CLASSES = ("channel_and_containment", "channel_only", "containment_only",
           "neither")
TIERS = ("valid", "unlikely", "mixed", "none")
RECORDS = ("valid-dict", "invalid-dict", "none")

#: The twelve binary detectors of data/evidence.parquet; with the SCOWL
#: tier they are the thirteen panel sets.
DETECTORS = ("wordnet", "wiktionary_english", "web2", "web2a",
             "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
             "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
             "csw21")

#: The discovery-log labels of AGENDA.md P3, tier suffix removed.
DISCOVERY_LABELS = ("google_ngrams", "wiktionary", "wikipedia",
                    "coca_frequency", "opensource", "linux", "nltk",
                    "libreoffice", "enable", "wordnet", "collins")
TIER_SUFFIXES = ("valid", "unlikely")

#: The EOL dictionaries' `source` values and their channel labels.
SOURCE_CHANNELS = {
    "twl_scrabble_dictionary": "eol:tournament-list",
    "synthetic_generation": "eol:synthetic-engine",
    "merriam-webster": "eol:dictionary-api:merriam-webster",
    "merriam-webster-medical": "eol:dictionary-api:merriam-webster",
    "free-dictionary": "eol:dictionary-api:free-dictionary",
    "authoritative_extracts": "eol:authoritative-extracts",
    "extended_domain_sources": "eol:extended-domain-sources",
    "invalid_list_recovery": "eol:invalid-list-recovery",
}
UNRECORDED = "eol:phase1-unrecorded"
SYNTHETIC_SOURCE = "synthetic_generation"

#: The `sources` names each CEOL layer's rows carry in the pin.
CENSUS_SOURCES = ("wiktionary_english", "hunspell_en_GB", "hunspell_en_US",
                  "hunspell_en_CA", "hunspell_en_AU", "scowl", "web2a",
                  "web2", "wordfreq")
AUDIT_SOURCES = ("wiktionary_english", "wordfreq", "scowl", "hunspell_en_GB",
                 "hunspell_en_AU", "hunspell_en_CA", "hunspell_en_US", "web2",
                 "csw21", "sowpods_legacy", "wordnet", "nwl2023", "enable1")
SPACED_SOURCES = ("wordnet", "wiktionary_english")
LEDGER_SOURCE, LEDGER_CHANNEL = "eol_ledger_d025", "ledger:d025"

VOCABULARY = frozenset(
    [f"eol:{name}" for name in DISCOVERY_LABELS]
    + list(SOURCE_CHANNELS.values()) + [UNRECORDED, LEDGER_CHANNEL]
    + [f"census:{s}" for s in CENSUS_SOURCES]
    + [f"audit:{s}" for s in AUDIT_SOURCES]
    + [f"spaced:{s}" for s in SPACED_SOURCES])

COLUMNS = ("word", "intake_layer", "intake_kind", "intake_channels",
           "eol_phase1_tier", "eol_record", "eol_synthetic_category",
           "eol_synthetic_engine_inferred", "panel_count", "gb_type",
           "wordfreq_scored", "wikt_title_any", "provenance_class")


# ---------------------------------------------------------------------------
# The assignment rules (PACKAGE.md §3, §4), as pure functions
# ---------------------------------------------------------------------------

def split_label(label: str) -> tuple[str, str]:
    """A discovery-log label is `<channel>_<tier>`; anything else is a
    hard error."""
    name, _, tier = label.rpartition("_")
    if tier not in TIER_SUFFIXES or name not in DISCOVERY_LABELS:
        raise ValueError(f"discovery-log label outside the vocabulary: "
                         f"{label!r}")
    return name, tier


def inherited_channels(candidate_source: str | None,
                       source: str | None) -> tuple[str, str]:
    """(intake_channels, eol_phase1_tier) of an inherited row, from its
    dictionary entry's fields (both None where it has no entry)."""
    labels = [x for x in (candidate_source or "").split(";") if x]
    parts = [split_label(x) for x in labels]
    channels = {f"eol:{name}" for name, _ in parts}
    if source is not None:
        if source not in SOURCE_CHANNELS:
            raise ValueError(f"`source` value outside the map: {source!r}")
        channels.add(SOURCE_CHANNELS[source])
    tiers = {tier for _, tier in parts}
    tier = "none" if not tiers else "mixed" if len(tiers) == 2 \
        else next(iter(tiers))
    return ";".join(sorted(channels)) or UNRECORDED, tier


def ceol_channels(layer: str, sources: str) -> str:
    """intake_channels of a CEOL-layer row, from the pin's `sources`."""
    out = set()
    for name in sources.split(";"):
        if layer == "c1_exceptions":
            if name == LEDGER_SOURCE:
                out.add(LEDGER_CHANNEL)
                continue
            allowed, prefix = CENSUS_SOURCES, "census"
        elif layer == "c4_additions":
            name = name.removeprefix("eol:")
            allowed, prefix = AUDIT_SOURCES, "audit"
        elif layer == "spaced_c015":
            allowed, prefix = SPACED_SOURCES, "spaced"
        else:
            raise ValueError(f"{layer} is not a CEOL layer")
        if name not in allowed:
            raise ValueError(f"{layer}: source {name!r} outside the "
                             "vocabulary")
        out.add(f"{prefix}:{name}")
    return ";".join(sorted(out))


def labels_outside_vocabulary(labels) -> list[str]:
    """The labels that are not in the closed vocabulary (none, or the
    build stops and the test fails)."""
    return sorted(set(labels) - VOCABULARY)


def provenance_class(has_channel: bool, has_containment: bool) -> str:
    if has_channel:
        return CLASSES[0] if has_containment else CLASSES[1]
    return CLASSES[2] if has_containment else CLASSES[3]


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------

def _verified(path: Path, record: Path, *keys: str) -> str:
    want = json.loads(record.read_text(encoding="utf-8"))
    for key in keys:
        want = want[key]
    got = sha256_file(path)
    if got != want:
        raise RuntimeError(f"{path.name} sha256 {got} is not the recorded "
                           f"{want}")
    return got


def _map_distinct(pa, pc, keys, fn):
    """Apply a Python function once per distinct key and spread the
    results back over the rows (the key spaces here are a few thousand
    combinations over ten million rows)."""
    encoded = pc.dictionary_encode(keys)
    if isinstance(encoded, pa.ChunkedArray):
        encoded = encoded.combine_chunks()
    results = [None if k is None else fn(k)
               for k in encoded.dictionary.to_pylist()]
    columns = list(zip(*[r for r in results if r is not None]))
    out = []
    for position in range(len(columns)):
        values = pa.array([None if r is None else r[position]
                           for r in results], pa.string())
        out.append(values.take(encoded.indices))
    return out


def build() -> dict:
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pin_words, layer, pin_sha = intake_layers()
    n = len(layer)
    evidence_sha = _verified(EVIDENCE_PARQUET, EVIDENCE_JSON, "artifacts",
                             "evidence_parquet_sha256")
    features_sha = sha256_file(FEATURES_PARQUET)
    if features_sha != FEATURES_SHA256:
        raise RuntimeError(f"features.parquet sha256 {features_sha} is not "
                           f"the recorded {FEATURES_SHA256}")
    intake_sha = {}
    for label, spec in (("valid", VALID), ("invalid", INVALID)):
        want = manifest["dictionaries"][label]["intake_parquet_sha256"]
        got = sha256_file(spec["out"])
        if got != want:
            raise RuntimeError(f"{spec['out'].name} is not the extraction "
                               "the manifest records")
        intake_sha[label] = got

    pin = pq.read_table(PIN_PARQUET, columns=["word", "sources",
                                              "token_count"])
    if not pc.all(pc.equal(pin["word"], pin_words)).as_py():
        raise RuntimeError("the pin's word column moved between reads")
    single = pin["token_count"].to_numpy(zero_copy_only=False) == 1
    if not np.array_equal(single, layer != 4):
        raise RuntimeError("token_count and c015_addition disagree")

    # ---- measured containment (C-010, C-011) -----------------------------
    ev = pq.read_table(EVIDENCE_PARQUET,
                       columns=["word", *DETECTORS, "scowl_tier",
                                "wikt_title_screen"])
    ft = pq.read_table(FEATURES_PARQUET,
                       columns=["word", "gb_log10_match", "wordfreq_zipf"])
    single_words = pc.filter(pin_words, pa.array(single))
    for name, table in (("evidence", ev), ("features", ft)):
        if table.num_rows != int(single.sum()) or not pc.all(
                pc.equal(table["word"], single_words)).as_py():
            raise RuntimeError(f"{name}.parquet is not aligned with the "
                               "pin's single-token rows")
    listed = sum((ev[d].to_numpy(zero_copy_only=False) == 1).astype(np.int16)
                 for d in DETECTORS)
    listed += (ev["scowl_tier"].to_numpy(zero_copy_only=False) > 0)
    sources = pin["sources"].to_numpy(zero_copy_only=False)
    panel_count = np.zeros(n, dtype=np.int16)
    panel_count[single] = listed
    spaced_idx = np.flatnonzero(~single)
    panel_count[spaced_idx] = [len(sources[i].split(";"))
                               for i in spaced_idx]

    def spread(values):
        out = np.zeros(n, dtype=bool)
        out[single] = values
        return out

    gb_type = spread(~np.isnan(
        ft["gb_log10_match"].to_numpy(zero_copy_only=False)))
    wordfreq_scored = spread(~np.isnan(
        ft["wordfreq_zipf"].to_numpy(zero_copy_only=False)))
    wikt_title_any = spread(
        ev["wikt_title_screen"].to_numpy(zero_copy_only=False) == 1)
    wordnet_listed = spread(
        ev["wordnet"].to_numpy(zero_copy_only=False) == 1)
    del ev, ft

    # ---- the EOL record: own dictionary first, the other second ----------
    tables, rows_in = {}, {}
    for label, spec in (("valid", VALID), ("invalid", INVALID)):
        t = pq.read_table(spec["out"], columns=["word", "candidate_source",
                                                "source", "category"])
        pos = pc.index_in(t["word"].combine_chunks(), value_set=pin_words) \
            .fill_null(-1).to_numpy(zero_copy_only=False).astype(np.int64)
        at = np.full(n, -1, dtype=np.int64)
        at[pos[pos >= 0]] = np.flatnonzero(pos >= 0)
        tables[label], rows_in[label] = t, at
    inherited = layer <= 1
    has_v, has_i = rows_in["valid"] >= 0, rows_in["invalid"] >= 0
    use_valid = inherited & np.where(layer == 0, has_v, ~has_i & has_v)
    use_invalid = inherited & ~use_valid & has_i
    eol_record = np.where(use_valid, "valid-dict",
                          np.where(use_invalid, "invalid-dict", "none"))
    both = pa.concat_tables([tables["valid"], tables["invalid"]])
    at = np.where(use_valid, rows_in["valid"],
                  np.where(use_invalid,
                           rows_in["invalid"] + tables["valid"].num_rows, -1))
    entry_row = pa.array(at, mask=at < 0)

    candidate_source, source, category = (
        both[column].combine_chunks().take(entry_row)
        for column in ("candidate_source", "source", "category"))
    del tables, both

    # ---- the generated forms the EOL demoted (PACKAGE.md §7, R9) ----------
    # They have no entry in either dictionary; the EOL's two demotion
    # ledgers are their record, and carry the category the dictionary
    # entry recorded before the demotion removed it.
    ledger = demoted_generated_forms()
    ledger_words = pa.array(list(ledger), pa.string())
    ledger_category = pa.array(list(ledger.values()), pa.string())
    at_ledger = pc.index_in(pin_words, value_set=ledger_words)
    demoted = pc.is_valid(at_ledger).to_numpy(zero_copy_only=False)
    if int(demoted.sum()) != len(ledger):
        raise RuntimeError("a demoted form is not a row of the pin")
    if not (demoted <= ((layer == 1) & (eol_record == "none"))).all():
        raise RuntimeError("a demoted form is outside the invalid layer or "
                           "has a dictionary entry")
    source = pc.if_else(pa.array(demoted), SYNTHETIC_SOURCE, source)
    category = pc.if_else(pa.array(demoted),
                          ledger_category.take(at_ledger), category)

    # ---- channels and tier ------------------------------------------------
    layer_names = pa.array(np.array(LAYERS, dtype=object)[layer])
    sep = "\x1f"
    inherited_key = pc.binary_join_element_wise(
        pc.fill_null(candidate_source, ""), pc.fill_null(source, sep), sep)
    inherited_key = pc.if_else(pa.array(inherited), inherited_key,
                               pa.scalar(None, pa.string()))

    def inherited_fn(key: str):
        labels, _, src = key.partition(sep)
        return inherited_channels(labels or None,
                                  None if src == sep else src)

    eol_channels, tier = _map_distinct(pa, pc, inherited_key, inherited_fn)
    ceol_key = pc.if_else(
        pa.array(~inherited),
        pc.binary_join_element_wise(layer_names, pin["sources"], sep),
        pa.scalar(None, pa.string()))
    (ceol_chan,) = _map_distinct(
        pa, pc, ceol_key,
        lambda key: (ceol_channels(*key.split(sep)),))
    intake_channels = pc.coalesce(eol_channels, ceol_chan)
    tier = pc.fill_null(tier, "none")
    if intake_channels.null_count:
        raise RuntimeError("a row without a channel value")
    stray = labels_outside_vocabulary(
        label for combo in pc.unique(intake_channels).to_pylist()
        for label in combo.split(";"))
    if stray:
        raise RuntimeError(f"labels outside the vocabulary: {stray}")

    # ---- kind, category, engine ------------------------------------------
    generated = pc.fill_null(pc.equal(source, SYNTHETIC_SOURCE), False) \
        .to_numpy(zero_copy_only=False) & inherited
    kind = np.where(generated, "generated",
                    np.where(inherited, "obtained", "derived"))
    category = pc.if_else(pa.array(generated), category,
                          pa.scalar(None, pa.string()))
    base = set(pc.filter(pin_words, pa.array(layer == 0)).to_pylist())
    engine_values: list = [None] * n
    gen_idx = np.flatnonzero(generated)
    for i, form in zip(gen_idx, pin_words.take(pa.array(gen_idx)).to_pylist()):
        engine_values[i] = infer_engine(form, base.__contains__)
    del base
    engine = pa.array(engine_values, pa.string())

    # ---- the class ---------------------------------------------------------
    has_channel = pc.not_equal(intake_channels, UNRECORDED) \
        .to_numpy(zero_copy_only=False)
    has_containment = (panel_count >= 1) | gb_type | wordfreq_scored
    klass = np.where(
        has_channel,
        np.where(has_containment, CLASSES[0], CLASSES[1]),
        np.where(has_containment, CLASSES[2], CLASSES[3]))

    def nullable(values):
        return pa.array(values, pa.bool_(), mask=~single)

    table = pa.table({
        "word": pin_words,
        "intake_layer": layer_names,
        "intake_kind": pa.array(kind, pa.string()),
        "intake_channels": intake_channels,
        "eol_phase1_tier": tier,
        "eol_record": pa.array(eol_record, pa.string()),
        "eol_synthetic_category": category,
        "eol_synthetic_engine_inferred": engine,
        "panel_count": pa.array(panel_count, pa.int16()),
        "gb_type": nullable(gb_type),
        "wordfreq_scored": nullable(wordfreq_scored),
        "wikt_title_any": nullable(wikt_title_any),
        "provenance_class": pa.array(klass, pa.string()),
    })
    assert tuple(table.column_names) == COLUMNS
    # low-cardinality strings dictionary-encoded on disk by parquet itself
    pq.write_table(table, OUT_PARQUET, compression="zstd")

    measured = measure(OUT_PARQUET)
    if measured["rows"] != n:
        raise RuntimeError("the written layer lost or gained a row")
    body = {
        "generated_by": "research/provenance/build_provenance.py",
        "decision": "C-064",
        "inputs": {
            "universe_v2_parquet_sha256": pin_sha,
            "evidence_parquet_sha256": evidence_sha,
            "features_parquet_sha256": features_sha,
            "eol_valid_intake_parquet_sha256": intake_sha["valid"],
            "eol_invalid_intake_parquet_sha256": intake_sha["invalid"],
            "eol_dictionaries_manifest_sha256": sha256_file(MANIFEST),
            "merged_valid_dict_sha256":
                manifest["dictionaries"]["valid"]["sha256"],
            "merged_invalid_dict_sha256":
                manifest["dictionaries"]["invalid"]["sha256"],
        },
        "artifact": {
            "path": "data/universe_v2_provenance.parquet (gitignored)",
            "sha256": sha256_file(OUT_PARQUET),
            "columns": list(COLUMNS),
        },
        "pin": pin_block(),
        "measured": measured,
        "percentages": percentages(measured),
        "coverage": coverage_block(manifest),
        "ledger_cross_check": _ledger_cross_check(table),
        "discovery_log_vs_containment": _log_vs_containment(
            table, layer, wordnet_listed),
        "reconciliations": reconciliations(measured),
        "quoted": quoted_figures(),
    }
    OUT_JSON.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return body


# ---------------------------------------------------------------------------
# The measurement — from the parquet alone (check_provenance re-runs it)
# ---------------------------------------------------------------------------

def _crosstab(pc, table, *columns: str) -> dict:
    grouped = table.group_by(list(columns)).aggregate([([], "count_all")])
    out: dict = {}
    for row in grouped.to_pylist():
        node = out
        for column in columns[:-1]:
            node = node.setdefault(_key(row[column]), {})
        node[_key(row[columns[-1]])] = row["count_all"]
    return _sorted(out)


def _key(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _sorted(node):
    if isinstance(node, dict):
        return {k: _sorted(node[k]) for k in sorted(node)}
    return node


def measure(path: Path = OUT_PARQUET) -> dict:
    """Every count of provenance.json, from the layer's parquet alone."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    t = pq.read_table(path, columns=[c for c in COLUMNS if c != "word"])
    n = t.num_rows
    out: dict = {"rows": n}
    out["rows_by_layer"] = _crosstab(pc, t, "intake_layer")
    out["rows_by_kind"] = _crosstab(pc, t, "intake_kind")
    out["rows_by_class"] = _crosstab(pc, t, "provenance_class")
    out["rows_by_layer_and_kind"] = _crosstab(pc, t, "intake_layer",
                                              "intake_kind")
    out["rows_by_layer_and_class"] = _crosstab(pc, t, "intake_layer",
                                               "provenance_class")
    out["rows_by_kind_and_class"] = _crosstab(pc, t, "intake_kind",
                                              "provenance_class")
    out["eol_phase1_tier_by_layer"] = _crosstab(pc, t, "intake_layer",
                                                "eol_phase1_tier")
    out["eol_record_by_layer"] = _crosstab(pc, t, "intake_layer",
                                           "eol_record")

    # channel labels: rows carrying each label, by layer
    combos = t.group_by(["intake_layer", "intake_channels"]).aggregate(
        [([], "count_all")]).to_pylist()
    labels: dict = {}
    n_labels: dict = {}
    for row in combos:
        parts = row["intake_channels"].split(";")
        for label in parts:
            by_layer = labels.setdefault(label, {})
            by_layer[row["intake_layer"]] = \
                by_layer.get(row["intake_layer"], 0) + row["count_all"]
        per = n_labels.setdefault(row["intake_layer"], {})
        count = 0 if parts == [UNRECORDED] else len(parts)
        per[str(count)] = per.get(str(count), 0) + row["count_all"]
    out["channel_label_rows_by_layer"] = _sorted(labels)
    out["channel_label_rows"] = {k: sum(v.values())
                                 for k, v in sorted(labels.items())}
    out["rows_by_layer_and_channel_count"] = _sorted(n_labels)
    out["distinct_channel_combinations"] = len(
        {row["intake_channels"] for row in combos})

    # containment, by layer
    listed = pc.greater_equal(t["panel_count"], 1)
    gb = pc.fill_null(t["gb_type"], False)
    wf = pc.fill_null(t["wordfreq_scored"], False)
    title = pc.fill_null(t["wikt_title_any"], False)
    contained = pc.or_(pc.or_(listed, gb), wf)
    flags = t.append_column("listed", listed).append_column("gb", gb) \
        .append_column("wf", wf).append_column("title", title) \
        .append_column("contained", contained)
    containment: dict = {}
    for name in LAYERS:
        sub = flags.filter(pc.equal(flags["intake_layer"], name))
        containment[name] = {
            "rows": sub.num_rows,
            "listed_by_a_panel_set": pc.sum(sub["listed"]).as_py() or 0,
            "gb_type": pc.sum(sub["gb"]).as_py() or 0,
            "wordfreq_scored": pc.sum(sub["wf"]).as_py() or 0,
            "wikt_title_any": pc.sum(sub["title"]).as_py() or 0,
            "with_containment": pc.sum(sub["contained"]).as_py() or 0,
            "measured_by_the_corpus_layers":
                sub.num_rows - sub["gb_type"].null_count,
        }
    out["containment_by_layer"] = containment
    out["panel_count_histogram"] = _crosstab(pc, t, "panel_count")

    # the generated rows
    gen = t.filter(pc.equal(t["intake_kind"], "generated"))
    engine_name = pc.replace_substring_regex(
        gen["eol_synthetic_engine_inferred"], r"/.*$", "")
    gen = gen.append_column("engine", engine_name)
    out["generated"] = {
        "rows": gen.num_rows,
        "by_layer": _crosstab(pc, gen, "intake_layer"),
        "by_class": _crosstab(pc, gen, "provenance_class"),
        "by_category": _crosstab(pc, gen, "eol_synthetic_category"),
        "by_engine": _crosstab(pc, gen, "engine"),
        "by_rule": _crosstab(pc, gen, "eol_synthetic_engine_inferred"),
        "by_layer_and_engine": _crosstab(pc, gen, "intake_layer", "engine"),
        "by_layer_and_class": _crosstab(pc, gen, "intake_layer",
                                        "provenance_class"),
        "by_eol_record": _crosstab(pc, gen, "eol_record"),
        "by_eol_record_and_class": _crosstab(pc, gen, "eol_record",
                                             "provenance_class"),
        "with_a_discovery_log_label_too": gen.filter(pc.not_equal(
            gen["eol_phase1_tier"], "none")).num_rows,
    }

    # the residual: no recorded channel and no measured containment
    res = flags.filter(pc.equal(flags["provenance_class"], "neither"))
    out["residual"] = {
        "rows": res.num_rows,
        "by_layer": _crosstab(pc, res, "intake_layer"),
        "by_eol_record": _crosstab(pc, res, "eol_record"),
        "a_wiktionary_title_in_some_language":
            pc.sum(res["title"]).as_py() or 0,
    }
    # the rows with no recorded channel, whatever their containment
    unrec = flags.filter(pc.equal(flags["intake_channels"], UNRECORDED))
    out["no_recorded_channel"] = {
        "rows": unrec.num_rows,
        "by_layer": _crosstab(pc, unrec, "intake_layer"),
        "by_eol_record": _crosstab(pc, unrec, "eol_record"),
        "listed_by_a_panel_set": pc.sum(unrec["listed"]).as_py() or 0,
        "a_gb_type": pc.sum(unrec["gb"]).as_py() or 0,
        "not_listed_and_a_gb_type": pc.sum(pc.and_(
            pc.invert(unrec["listed"]), unrec["gb"])).as_py() or 0,
        "not_listed_not_gb_and_wordfreq_scored": pc.sum(pc.and_(pc.and_(
            pc.invert(unrec["listed"]), pc.invert(unrec["gb"])),
            unrec["wf"])).as_py() or 0,
        "with_no_containment": pc.sum(
            pc.invert(unrec["contained"])).as_py() or 0,
    }
    return out


# ---------------------------------------------------------------------------
# The blocks of provenance.json beside the measurement
# ---------------------------------------------------------------------------

def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.2f}%"


def percentages(measured: dict) -> dict:
    """Every percentage the report prints, from the measured block."""
    rows = measured["rows"]
    by_class = measured["rows_by_class"]
    inherited = measured["rows_by_layer"]["eol_valid"] \
        + measured["rows_by_layer"]["eol_invalid"]
    unrecorded = measured["no_recorded_channel"]["rows"]
    gen = measured["generated"]
    return {
        "residual_of_the_universe": _pct(by_class["neither"], rows),
        "residual_of_the_invalid_layer": _pct(
            measured["residual"]["by_layer"].get("eol_invalid", 0),
            measured["rows_by_layer"]["eol_invalid"]),
        "channel_and_containment_of_the_universe": _pct(
            by_class["channel_and_containment"], rows),
        "channel_only_of_the_universe": _pct(by_class["channel_only"], rows),
        "containment_only_of_the_universe": _pct(
            by_class["containment_only"], rows),
        "inherited_with_a_recorded_channel": _pct(inherited - unrecorded,
                                                  inherited),
        "generated_of_the_universe": _pct(gen["rows"], rows),
        "generated_with_no_containment": _pct(
            gen["by_class"].get("channel_only", 0), gen["rows"]),
        "generated_inferred_as_affixation": _pct(
            gen["by_engine"].get("affixation", 0), gen["rows"]),
    }


def pin_block() -> dict:
    """The C-016 pin's own record, for the rows the report quotes."""
    counts = json.loads((REPO / "research" / "universe_v2"
                         / "universe_v2.json").read_text(
                             encoding="utf-8"))["counts"]
    return {"v2_rows": counts["v2_rows"],
            "restricted_rows": counts["restricted_rows"],
            "inherited_strings": counts["eol_valid"] + counts["eol_invalid"]}


def coverage_block(manifest: dict) -> dict:
    """The P2 coverage figures, copied from the manifest (the enforcer
    ties the two)."""
    d = manifest["dictionaries"]
    return {
        "valid_dictionary_bytes": d["valid"]["bytes"],
        "valid_dictionary_entries": d["valid"]["entries"],
        "valid_entries_with_a_non_empty_channel_list":
            d["valid"]["entries_with_a_non_empty_channel_list"],
        "valid_entries_with_a_source_value":
            d["valid"]["entries_with_a_source_value"],
        "valid_entries_with_neither": d["valid"]["entries_with_neither"],
        "valid_entries_outside_the_universe":
            d["valid"]["entries_by_the_layer_of_their_key"][
                "outside_the_universe"],
        "invalid_dictionary_bytes": d["invalid"]["bytes"],
        "invalid_dictionary_lines": d["invalid"]["lines"],
        "invalid_dictionary_entries": d["invalid"]["entries"],
        "invalid_entries_keyed_by_a_valid_string":
            d["invalid"]["entries_by_the_layer_of_their_key"]["eol_valid"],
        "invalid_entries_outside_the_universe":
            d["invalid"]["entries_by_the_layer_of_their_key"][
                "outside_the_universe"],
        "invalid_entries_with_a_non_empty_channel_list":
            d["invalid"]["entries_with_a_non_empty_channel_list"],
        "invalid_entries_with_a_source_value":
            d["invalid"]["entries_with_a_source_value"],
        "invalid_entries_with_neither": d["invalid"]["entries_with_neither"],
        "by_layer": manifest["coverage"],
        "no_entry_strings_accounted_for":
            manifest["no_entry_strings_accounted_for"],
    }


def _ledger_cross_check(table) -> dict:
    """The inferred rule against the form each row of the EOL's two
    demotion ledgers claims (its reason field: a synthetic comparative, a
    synthetic plural, a synthetic verb form). The ledgers' labels are the
    EOL's stage-3 and stage-4 framing, not the generator's own."""
    import pyarrow as pa
    import pyarrow.compute as pc

    claimed: dict[str, str] = {}
    for name in DEMOTION_LEDGERS:
        for row in read_ledger(name):
            claimed[row["word"]] = row["reason"].split(" of ")[0] \
                .removeprefix("synthetic ")
    at = pc.index_in(pa.array(list(claimed), pa.string()),
                     value_set=table["word"].combine_chunks())
    rules = table["eol_synthetic_engine_inferred"].combine_chunks() \
        .take(at).to_pylist()
    agree_with = {
        "comparative": ("affixation/comparative-or-agent",
                        "affixation/superlative"),
        "plural": ("affixation/plural", "affixation/gerund-plural",
                   "affixation/agent-plural"),
        "verb form": ("affixation/verb-form",),
    }
    cells: dict = {}
    agree = 0
    for form, rule in zip(claimed.values(), rules):
        row = cells.setdefault(form, {})
        row[rule] = row.get(rule, 0) + 1
        agree += rule in agree_with.get(form, ())
    return {"ledger_rows": len(claimed), "agreeing_rows": agree,
            "claimed_form_by_inferred_rule": _sorted(cells)}


def _log_vs_containment(table, layer, wordnet_listed) -> dict:
    """The discovery log beside measured containment, where the two can
    be set side by side: the label `wordnet` against the WordNet panel
    set over the valid layer (C-008's example), and the label
    `google_ngrams` against the CEOL's Google Books re-stream over the
    inherited strings. A first-seen label is a record of the channel; it
    was never a list of the sources that contain the string."""
    import pyarrow.compute as pc

    channels = table["intake_channels"]
    tier = table["eol_phase1_tier"].to_numpy(zero_copy_only=False)

    def labeled(name: str):
        return pc.match_substring_regex(
            channels, rf"(^|;)eol:{name}(;|$)").to_numpy(
                zero_copy_only=False)

    valid = layer == 0
    inherited = layer <= 1
    wn = labeled("wordnet")
    gn = labeled("google_ngrams")
    gb = pc.fill_null(table["gb_type"], False).to_numpy(
        zero_copy_only=False)
    return {
        "valid_rows_labeled_wordnet": int((valid & wn).sum()),
        "valid_rows_labeled_wordnet_at_the_valid_tier":
            int((valid & wn & (tier == "valid")).sum()),
        "valid_rows_listed_by_the_wordnet_panel_set":
            int((valid & wordnet_listed).sum()),
        "valid_rows_both": int((valid & wn & wordnet_listed).sum()),
        "inherited_rows_labeled_google_ngrams": int((inherited & gn).sum()),
        "of_them_a_gb_type": int((inherited & gn & gb).sum()),
        "of_them_not_a_gb_type": int((inherited & gn & ~gb).sum()),
        "inherited_gb_types_without_the_label":
            int((inherited & gb & ~gn).sum()),
        "inherited_gb_types": int((inherited & gb).sum()),
    }


def reconciliations(measured: dict) -> dict:
    """Ties between this layer and the committed record."""
    features = json.loads(FEATURES_JSON.read_text(encoding="utf-8"))
    by_class = measured["rows_by_class"]
    gen = measured["generated"]
    return {
        "sr2_reading_b_rows": features["doc_figures"]["sr2_b_rows"],
        "channel_only_plus_neither":
            by_class["channel_only"] + by_class["neither"],
        "generated_in_the_valid_dictionary":
            gen["by_eol_record"].get("valid-dict", 0),
        "generated_in_the_invalid_dictionary":
            gen["by_eol_record"].get("invalid-dict", 0),
        "generated_named_by_the_demotion_ledgers_only":
            gen["by_eol_record"].get("none", 0),
        "generated_in_all": gen["rows"],
        # reading R9 undone: the ledger-named forms would carry no
        # recorded channel, and those without containment would join
        # the residual
        "residual_without_the_ledger_reading":
            by_class["neither"] + gen["by_eol_record_and_class"]
            .get("none", {}).get("channel_only", 0),
    }


#: Figures the report quotes from another party's account. They are not
#: measured here; the build confirms that each stands in the source it is
#: quoted from (the EOL repository, read and never written).
_EOL_REPORT = "docs/ENGLISH_OPENLIST_FINAL_COMPREHENSIVE_REPORT.md"
QUOTED = (
    ("eol_phase1_entries", 9_823_196, _EOL_REPORT),
    ("eol_phase1_provisionally_valid", 9_640_238, _EOL_REPORT),
    ("eol_phase1_raw_candidates", 182_958, _EOL_REPORT),
    ("eol_phase2d_generated", 330_386, _EOL_REPORT),
    ("eol_phase2d_validated", 64_837, _EOL_REPORT),
    ("eol_demoted_comparatives", 16_476, "commit 721854d"),
    ("eol_forms_with_no_stem_in_the_list", 2_636, "commit 538c36b"),
    ("eol_demoted_non_plural_forms", 17_118, "commit 50d2b1a"),
    ("eol_plurals_kept", 28_605, "commit 50d2b1a"),
)


def quoted_figures() -> dict:
    import subprocess

    from ceol.ingest.common import EOL_REPO

    out = {}
    for name, value, source in QUOTED:
        if source.startswith("commit "):
            text = subprocess.run(
                ["git", "-C", str(EOL_REPO), "show", "-s", "--format=%B",
                 source.split()[1]], capture_output=True, text=True).stdout
        else:
            text = (EOL_REPO / source).read_text(encoding="utf-8")
        if f"{value:,}" not in text:
            raise RuntimeError(f"the quoted figure {name} = {value:,} does "
                               f"not stand in {source}")
        out[name] = {"value": value, "basis": "quoted, not measured here",
                     "source": f"the EOL repository, {source}"}
    return out


# ---------------------------------------------------------------------------
# The report: PROVENANCE.md is PROVENANCE.template.md with every figure
# filled from provenance.json, so every figure of the report is a row of
# the JSON by construction; check_provenance re-renders and compares.
# ---------------------------------------------------------------------------

TEMPLATE = OUT_DIR / "PROVENANCE.template.md"
REPORT = OUT_DIR / "PROVENANCE.md"


def _fmt(value) -> str:
    return f"{value:,}" if isinstance(value, int) else str(value)


def _lookup(body: dict, path: str):
    node = body
    for part in path.split("."):
        node = node[part]
    if isinstance(node, dict) and set(node) >= {"value", "basis"}:
        node = node["value"]
    if isinstance(node, (dict, list)):
        raise KeyError(f"{path} is not a figure")
    return node


def _table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    lines += ["| " + " | ".join(_fmt(c) for c in row) + " |" for row in rows]
    return lines


def tables(body: dict) -> dict[str, list[str]]:
    m = body["measured"]
    gen = m["generated"]
    out: dict[str, list[str]] = {}

    by_lc = m["rows_by_layer_and_class"]
    out["class_by_layer"] = _table(
        ["Intake layer", "Rows", *[f"`{c}`" for c in CLASSES]],
        [[f"`{name}`", m["rows_by_layer"][name],
          *[by_lc[name].get(c, 0) for c in CLASSES]] for name in LAYERS]
        + [["**universe v2**", m["rows"],
            *[m["rows_by_class"][c] for c in CLASSES]]])

    by_lk = m["rows_by_layer_and_kind"]
    out["kind_by_layer"] = _table(
        ["Intake layer", *[f"`{k}`" for k in KINDS]],
        [[f"`{name}`", *[by_lk[name].get(k, 0) for k in KINDS]]
         for name in LAYERS]
        + [["**universe v2**", *[m["rows_by_kind"][k] for k in KINDS]]])

    labels = m["channel_label_rows_by_layer"]
    out["eol_channels"] = _table(
        ["Channel label", "`eol_valid`", "`eol_invalid`"],
        [[f"`{label}`", by.get("eol_valid", 0), by.get("eol_invalid", 0)]
         for label, by in labels.items() if label.startswith("eol:")])
    out["ceol_channels"] = _table(
        ["Channel label", "Layer", "Rows"],
        [[f"`{label}`", f"`{layer}`", count]
         for label, by in labels.items() if not label.startswith("eol:")
         for layer, count in by.items()])

    tiers, records = m["eol_phase1_tier_by_layer"], m["eol_record_by_layer"]
    out["tier_and_record"] = _table(
        ["Inherited layer", *[f"tier `{t}`" for t in TIERS],
         *[f"record `{r}`" for r in RECORDS]],
        [[f"`{name}`", *[tiers[name].get(t, 0) for t in TIERS],
          *[records[name].get(r, 0) for r in RECORDS]]
         for name in ("eol_valid", "eol_invalid")])

    cont = m["containment_by_layer"]
    out["containment_by_layer"] = _table(
        ["Intake layer", "Rows", "Listed by a panel set",
         "Google Books 1-gram type", "wordfreq-scored", "With containment",
         "Wiktionary title, any language (the screen)"],
        [[f"`{name}`", cont[name]["rows"],
          cont[name]["listed_by_a_panel_set"], cont[name]["gb_type"],
          cont[name]["wordfreq_scored"], cont[name]["with_containment"],
          cont[name]["wikt_title_any"]] for name in LAYERS])

    engines = gen["by_layer_and_engine"]
    names = sorted(gen["by_engine"], key=lambda e: -gen["by_engine"][e])
    out["generated_by_engine"] = _table(
        ["Inferred engine", "`eol_valid`", "`eol_invalid`", "All"],
        [[f"`{e}`", engines.get("eol_valid", {}).get(e, 0),
          engines.get("eol_invalid", {}).get(e, 0), gen["by_engine"][e]]
         for e in names]
        + [["**generated rows**", gen["by_layer"]["eol_valid"],
            gen["by_layer"]["eol_invalid"], gen["rows"]]])
    out["generated_by_rule"] = _table(
        ["Inferred rule", "Rows"],
        [[f"`{r}`", n] for r, n in sorted(gen["by_rule"].items(),
                                          key=lambda x: -x[1])])
    out["generated_by_category"] = _table(
        ["Category, as recorded", "Rows"],
        [[c, n] for c, n in sorted(gen["by_category"].items(),
                                   key=lambda x: (-x[1], x[0]))])

    cross = body["ledger_cross_check"]["claimed_form_by_inferred_rule"]
    out["ledger_cross_check"] = _table(
        ["The form the ledger claims", "Inferred rule", "Rows"],
        [[form, f"`{rule}`", n] for form, by in cross.items()
         for rule, n in by.items()])
    return out


def render_report(body: dict, template: str) -> str:
    import re

    rendered_tables = tables(body)

    def fill(match):
        key = match.group(1).strip()
        if key.startswith("table:"):
            return "\n".join(rendered_tables[key[len("table:"):]])
        return _fmt(_lookup(body, key))

    return re.sub(r"\{\{([^{}]+)\}\}", fill, template)


def main() -> int:
    if "--render" in sys.argv:
        body = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        REPORT.write_text(render_report(
            body, TEMPLATE.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"[provenance] {REPORT.name} rendered from {TEMPLATE.name}")
        return 0
    body = build()

    m = body["measured"]
    print(f"[provenance] {m['rows']:,} rows; classes {m['rows_by_class']}")
    print(f"[provenance] residual {m['residual']['rows']:,}; generated "
          f"{m['generated']['rows']:,}")
    print(f"[provenance] sha256 {body['artifact']['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
