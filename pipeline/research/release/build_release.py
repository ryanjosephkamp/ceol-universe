"""
UR-1 (C-078 line 7): the release pipeline of the CEOL Universe, a
version at a time (research/release/PACKAGE_UR1.md).

A version is a projection of pinned layers and nothing else: the pin's
shippable rows (C-009), the intake-provenance layer (C-064) and the
evidence matrix (C-010) joined by word, the identifier and the
release-layer columns of C-078 line 4 added, the feature layer (C-011) as
a second config, and 4 filter configs of the same rows. Every layer is
hashed and compared with its committed record before it is read. The
files are written into a staging directory, re-read, and asserted
(PACKAGE_UR1.md §3); only when every assertion has passed are they moved
into place and the committed record written. A failure raises, writes
nothing further, and removes the staging directory, so a failed build
leaves no file (C-079 line 1, F1).

A public version (v2.1 on) is the same projection put through the public
projection of `withholding.py` (D-010, D-011): the withheld lists' columns
and labels removed, the withheld channel labels removed, `panel_sets`,
`panel_count`, and `provenance_class` recomputed over the published panel,
and the rows with no public evidence held back into a private file beside
the release, and the feature columns computed against a withheld list's
reference withheld. Each of its Parquet files carries the canary, the
license, and the attribution in its key-value metadata, and NOTICES.md
ships beside them (AT-UR1-12). It adds a `sample` config, and its record
names the commit of the code that built it.

Nothing here adds a row, changes a pinned layer, calls anything valid,
prints a word, or talks to the hub (upload_release.py does, after this).

Run:  python3 -m research.release.build_release --version v2.0
      python3 -m research.release.build_release --version v2.0 --out DIR
          (a reproduction: the files and the record go to DIR)
      python3 -m research.release.build_release --version v2.0 --record-only
          (the record of the files already built rewritten, each file's
          sha256 verified against it first; no file written; C-079 line 1)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ceol.ingest.common import sha256_file

from . import columns as C
from . import withholding as W

REPO = Path(__file__).resolve().parents[2]
DATASET = "ryanjosephkamp/ceol-universe"

#: The dataset's canary (C-078 line 4; PACKAGE_UR1.md reading R15): a
#: UUID generated once by uuid.uuid4() on 2026-09-26, recorded in the
#: record and the card so that memorization of the dataset can be tested
#: later. Never regenerated.
CANARY = "a8d1c96b-4b6e-413c-94a1-a6fa7066f992"

#: The license of the dataset (C-078 line 6) and the attribution each public
#: Parquet file carries in its key-value metadata beside the canary (D-010
#: line 5; the review's §1.4); NOTICES.md carries every notice in full.
LICENSE = "CC-BY-SA-4.0"
ATTRIBUTION = (
    "The CEOL Universe, licensed CC BY-SA 4.0. Its fields derive from the "
    "English Wiktionary (its contributors; CC BY-SA), WordNet 3.0 (Princeton "
    "University), SCOWL (Kevin Atkinson and the contributors its notice "
    "names), the LibreOffice hunspell dictionaries, ENABLE (Alan Beale and "
    "M. Cooper), wordfreq 3.1.1 (Robyn Speer; with the SUBTLEX word lists of "
    "Marc Brysbaert and colleagues), the Google Books Ngram corpus (CC BY "
    "3.0), and the English OpenList (its maintainer's contribution under "
    "MIT; its sources keep their own terms). NOTICES.md, beside this file, "
    "carries every notice and license the sources require.")
#: The key-value metadata keys of a public file (AT-UR1-12).
METADATA_KEYS = ("ceol.canary", "ceol.version", "ceol.license",
                 "ceol.attribution", "ceol.notices")


def file_metadata(version: str) -> dict[bytes, bytes]:
    """The key-value metadata every Parquet file of a public version
    carries."""
    values = (CANARY, version, LICENSE, ATTRIBUTION, "NOTICES.md")
    return {k.encode(): v.encode("utf-8") for k, v in zip(METADATA_KEYS, values)}

#: The size bounds (PACKAGE_UR1.md §2.6, reading R10): MAX_SHARD_SIZE
#: "500MB" and MAX_ROW_GROUP_SIZE "100MB" in the datasets library's
#: config.py, version 4.7.0 as installed here, read on 2026-09-26; the
#: library is not imported. That config describes both as uncompressed
#: sizes for its own writer; the build enforces the first on each file's
#: compressed bytes (C-079 line 9, SIZE_POLICY).
MAX_SHARD_BYTES = 500 * 10**6
MAX_ROW_GROUP_BYTES = 100 * 10**6
#: Row groups are a whole number of these rows, so small drifts in the
#: in-memory size never move a file's bytes.
ROW_GROUP_QUANTUM = 10_000
#: The size policy the record states in its bounds block (C-079 line 9;
#: C-079 line 1, F4).
SIZE_POLICY = (
    "the enforced bound is each file's compressed bytes on disk, which must "
    "be under max_shard_bytes (C-079 line 9); max_shard_bytes and "
    "max_row_group_bytes take the values of the datasets library's "
    "MAX_SHARD_SIZE and MAX_ROW_GROUP_SIZE, which that library's config "
    "describes as uncompressed sizes for its own writer and which are not "
    "a hub limit; max_row_group_bytes and row_group_quantum set each "
    "file's row-group row count from the table's mean in-memory bytes per "
    "row, a target and not an enforced bound; each file's "
    "measured_uncompressed_bytes and largest_row_group_uncompressed_bytes "
    "are read from its Parquet metadata and recorded, not bounded")

#: The 6 census classes of C-005, the exception classes (reading R7).
EXCEPTION_CLASSES = ("hyphenated", "accented", "contraction",
                     "apostrophe-form", "ligature", "diaeresis")

#: The filter configs: name, predicate as the record states it.
FILTER_CONFIGS: tuple[tuple[str, str], ...] = (
    ("panel-listed", "panel_count >= 1"),
    ("eol-valid", "eol == true"),
    ("spaced", "token_count > 1"),
    ("exceptions", "classes carries any of "
                   + ", ".join(EXCEPTION_CLASSES)),
)
#: The sample config a public version adds: the
#: rows whose id begins with these hexadecimal digits, about 1 row in 256.
#: An id is a function of its string alone, so the sample holds the same
#: strings in every version that holds them.
SAMPLE_PREFIX = "00"
SAMPLE_CONFIG: tuple[str, str] = (
    "sample", f"id starts with '{SAMPLE_PREFIX}' (about 1 row in 256)")
UNIVERSE_PREDICATE = "is_restricted == false over the pin"
FEATURES_PREDICATE = ("token_count == 1 over universe; id, word, and the "
                      "feature layer's columns")

_SHIPPABLE = ("rows", "restricted_words_checked", "restricted_hits")
_EXCLUDED = ("columns", "controls_checked", "control_hits",
             "ledger_words_outside_the_pin_checked", "ledger_hits")
#: The fields of each assertion block the build writes into the record,
#: by config and AT identifier (the filter configs share "filter"): the
#: schema check_release requires of a record, a missing or an undeclared
#: field failing it (C-079 line 1, F8). The build asserts its own blocks
#: against it before anything is kept.
ASSERTION_FIELDS: dict[str, dict[str, tuple[str, ...]]] = {
    "universe": {
        "AT-UR1-1": _SHIPPABLE,
        "AT-UR1-2": ("rows", "expected_rows", "columns_without_nulls",
                     "rows_in_pin_order"),
        "AT-UR1-3": ("rows", "distinct_ids"),
        "AT-UR1-4": ("spaced_rows", "columns"),
        "AT-UR1-6": _EXCLUDED,
        "AT-UR1-10": ("rows", "columns"),
    },
    "filter": {
        "AT-UR1-1": _SHIPPABLE,
        "AT-UR1-5": ("rows",),
        "AT-UR1-6": ("columns",),
    },
    "features": {
        "AT-UR1-1": _SHIPPABLE,
        "AT-UR1-2": ("rows", "single_token_rows_of_universe",
                     "columns_without_nulls"),
        "AT-UR1-3": ("rows", "distinct_ids"),
        "AT-UR1-4": ("spaced_rows",),
        "AT-UR1-6": _EXCLUDED,
    },
}


#: The public projection's block (AT-UR1-12), added to every config of a
#: public version.
PUBLIC_FIELDS: dict[str, tuple[str, ...]] = {
    "universe": ("withheld_columns_present", "withheld_labels_found",
                 "held_back_rows_present", "held_back_rows",
                 "provenance_class_rederived", "metadata_keys"),
    "filter": ("withheld_columns_present", "withheld_labels_found",
               "held_back_rows_present", "metadata_keys"),
    "features": ("withheld_columns_present", "held_back_rows_present",
                 "metadata_keys"),
}


#: The model-or-engine column's block (AT-UR1-13), on a public universe.
MODEL_FIELDS: tuple[str, ...] = ("rows_by_value", "generated_rows",
                                 "model_rows_outside_the_eol_valid_list")


def assertion_fields(config: str, public: bool = False
                     ) -> dict[str, tuple[str, ...]]:
    """The declared assertion blocks of a config and their fields."""
    names = [name for name, _p in FILTER_CONFIGS + (SAMPLE_CONFIG,)]
    kind = "filter" if config in names else config
    fields = dict(ASSERTION_FIELDS[kind])
    if public:
        fields["AT-UR1-12"] = PUBLIC_FIELDS[kind]
        if kind == "universe":
            fields["AT-UR1-13"] = MODEL_FIELDS
    return fields


def assert_schema(assertions: dict[str, dict], public: bool = False) -> None:
    """Every block the build wrote carries exactly its declared fields."""
    for config, blocks in assertions.items():
        want = assertion_fields(config, public)
        got = {at: tuple(block) for at, block in blocks.items()}
        if got != want:
            raise ReleaseError(f"{config}: the assertion blocks written are "
                               f"not ASSERTION_FIELDS' ({got} against "
                               f"{want})")


class ReleaseError(RuntimeError):
    """A refusal or a failed assertion: nothing further is written."""


@dataclass(frozen=True)
class Layer:
    """A pinned layer: its file, and where its committed hash lives."""
    name: str
    path: Path
    record: Path
    key: tuple[str, ...]


@dataclass(frozen=True)
class VersionSpec:
    version: str
    pin_entry: str
    pin_record: Path
    layers: tuple[Layer, ...]
    restricted_csv: Path
    ledger_csv: Path
    ledger_manifest: Path
    out_dir: Path
    record_out: Path
    #: "public" applies `withholding.py` (v2.1 on, and every version that
    #: does not say otherwise); "full" carries every column and row of the
    #: shippable projection, and only v2.0, the private rehearsal, says so
    projection: str = "public"
    #: a public version's NOTICES file; None for research/release/
    #: NOTICES_<version>.md
    notices: Path | None = None
    #: the smallest count a published cell may describe (docs/ANALYSIS_PLAN.md
    #: §9 rule 2); a held-back reason with fewer rows refuses the build
    suppression_floor: int = 10
    #: the reach guard's bound (withholding.REACH_THRESHOLD); a share at or
    #: above it, for a published channel label or a layer's emptied sources,
    #: refuses the build before anything is written
    reach_threshold: float = W.REACH_THRESHOLD

    @property
    def public(self) -> bool:
        return self.projection == "public"



@dataclass(frozen=True)
class Profile:
    """The columns a version's universe config carries, its nullable and
    spaced-null sets, the panel sets its `panel_sets` names, the feature
    layer's columns its features config carries, and its filter configs."""
    columns: tuple[str, ...]
    nullable: frozenset[str]
    spaced_null: tuple[str, ...]
    sets: tuple[str, ...]
    features: tuple[str, ...]
    filters: tuple[tuple[str, str], ...]

    @property
    def configs(self) -> list[str]:
        """Every config, in the record's order."""
        return ["universe", "features"] + [n for n, _ in self.filters]


FULL = Profile(C.UNIVERSE_COLUMNS, C.UNIVERSE_NULLABLE, C.SPACED_NULL,
               C.PANEL_SETS, C.FEATURE_LAYER_COLUMNS, FILTER_CONFIGS)
PUBLIC = Profile(W.PUBLISHED_UNIVERSE_COLUMNS + tuple(c[0] for c in C.MODEL),
                 W.PUBLISHED_NULLABLE, W.PUBLISHED_SPACED_NULL, W.PUBLISHED_SETS,
                 W.PUBLISHED_FEATURE_COLUMNS, FILTER_CONFIGS + (SAMPLE_CONFIG,))


def profile(spec: "VersionSpec") -> Profile:
    return PUBLIC if spec.public else FULL


def versions(repo: Path = REPO) -> dict[str, VersionSpec]:
    """The versions this pipeline knows. v3.0 is declared with the pin
    record its pin entry will commit (C-078 line 2); until that record
    exists the version is refused, and the v3 entry adds its layers."""
    rec = repo / "research"
    data = repo / "data"
    common = dict(
        restricted_csv=repo / ".cache" / "audit"
        / "universe_miss_restricted.csv",
        ledger_csv=data / "lexdev" / "intake_ledger.csv",
        ledger_manifest=rec / "lexdev" / "ledger_manifest.json")

    def layers(pin: Path, provenance: Path, evidence: Path,
               layer_data: Path) -> tuple:
        return (
            Layer("pin", layer_data / "universe_v2.parquet", pin,
                  ("artifacts", "universe_v2_parquet_sha256")),
            Layer("provenance", layer_data / "universe_v2_provenance.parquet",
                  provenance, ("artifact", "sha256")),
            Layer("evidence", layer_data / "evidence.parquet", evidence,
                  ("artifacts", "evidence_parquet_sha256")),
            # features.json holds no hash of the parquet (C-065 reading
            # R11); provenance.json's inputs block holds the full hash
            # (PACKAGE_UR1.md reading R14)
            Layer("features", layer_data / "features.parquet", provenance,
                  ("inputs", "features_parquet_sha256")),
        )

    pin_record = rec / "universe_v2" / "universe_v2.json"
    v2 = VersionSpec(
        version="v2.0", pin_entry="C-016", pin_record=pin_record,
        layers=layers(pin_record, rec / "provenance" / "provenance.json",
                      rec / "evidence" / "evidence.json", data),
        out_dir=data / "release" / "ceol-universe-v2.0",
        record_out=rec / "release" / "release_v2.0.json",
        projection="full", **common)
    v21 = VersionSpec(
        version="v2.1", pin_entry="C-016", pin_record=v2.pin_record,
        layers=v2.layers + (
            Layer("model_basis", data / "eol_valid_model_basis.parquet",
                  rec / "provenance" / "model_basis.json",
                  ("artifact", "sha256")),),
        out_dir=data / "release" / "ceol-universe-v2.1",
        record_out=rec / "release" / "release_v2.1.json",
        projection="public", **common)
    # the first public release, named 1.0: v2.1's
    # pin, layers, and projection under the public name, so its rows are
    # v2.1's and only the name its files carry differs
    v10 = VersionSpec(
        version="v1.0", pin_entry=v21.pin_entry, pin_record=v21.pin_record,
        layers=v21.layers,
        out_dir=data / "release" / "ceol-universe-v1.0",
        record_out=rec / "release" / "release_v1.0.json",
        projection="public", **common)
    v3 = VersionSpec(
        version="v3.0", pin_entry="the v3 pin entry (C-078 line 2)",
        pin_record=rec / "universe_v3" / "universe_v3.json",
        layers=(),
        out_dir=data / "release" / "ceol-universe-v3.0",
        record_out=rec / "release" / "release_v3.0.json", **common)
    return {v2.version: v2, v21.version: v21, v10.version: v10, v3.version: v3}


def resolve(version: str, repo: Path = REPO) -> VersionSpec:
    """The specification of a version, or a refusal (AT-UR1-11)."""
    known = versions(repo)
    if version not in known:
        raise ReleaseError(f"unknown version {version!r}; known: "
                           f"{', '.join(sorted(known))}")
    spec = known[version]
    if not spec.pin_record.exists():
        raise ReleaseError(
            f"version {version}: its pin record "
            f"{spec.pin_record.relative_to(repo).as_posix()} is absent; "
            f"the pipeline builds only over a pinned universe")
    if not spec.layers:
        raise ReleaseError(f"version {version}: no layers are declared")
    return spec


# ---------------------------------------------------------------------------
# The pure parts: the identifier, the release layer, the predicates
# ---------------------------------------------------------------------------

def word_id(word: str) -> str:
    """The identifier (PACKAGE_UR1.md §2.3)."""
    return hashlib.sha256(word.encode("utf-8")).hexdigest()[:16]


def ids(words):
    import pyarrow as pa
    return pa.array([word_id(w) for w in words.to_pylist()], pa.string())


def class_explicit(classes):
    import pyarrow.compute as pc
    return pc.if_else(pc.equal(classes, ""), "plain", classes)


def _spaced_listing(token_count, sources, name: str):
    """True on a spaced row whose pin `sources` names `name`."""
    import pyarrow.compute as pc
    listed = pc.match_substring_regex(sources, f"(^|;){name}(;|$)")
    return pc.and_(pc.greater(token_count, 1), listed)


def panel_sets(table, sets: tuple[str, ...] = C.PANEL_SETS):
    """The panel sets that list each row (§2.4): the evidence columns on
    a single-token row, the pin's `sources` on a spaced row; `sets` names
    the sets a version publishes, in `C.PANEL_SETS`' order.

    The names are joined from empty-or-name parts and the separators
    collapsed afterwards: pyarrow 22's `null_handling="skip"` drops a row
    whose parts are all null, which would shift every later row."""
    import pyarrow.compute as pc
    parts = []
    for name in sets:
        if name == "scowl":
            listed = pc.fill_null(pc.greater(table["scowl_tier"], 0), False)
        else:
            listed = pc.fill_null(pc.equal(table[name], 1), False)
            if name in ("wordnet", "wiktionary_english"):
                listed = pc.or_(listed, _spaced_listing(
                    table["token_count"], table["sources"], name))
        parts.append(pc.if_else(listed, name, ""))
    joined = pc.binary_join_element_wise(*parts, ";")
    joined = pc.utf8_trim(pc.replace_substring_regex(joined, ";+", ";"),
                          ";")
    if len(joined) != table.num_rows or joined.null_count:
        raise ReleaseError("panel_sets: the join lost or nulled a row")
    return joined


def panel_count_of(sets):
    """The number of names in a `panel_sets` value."""
    import pyarrow as pa
    import pyarrow.compute as pc
    n = pc.list_value_length(pc.split_pattern(sets, ";"))
    return pc.if_else(pc.equal(sets, ""), pa.scalar(0, n.type), n)


def varieties(gb, us):
    """The 2 variety proxies (§2.4): null where either hunspell column
    is -1 or null."""
    import pyarrow as pa
    import pyarrow.compute as pc
    g = pc.fill_null(gb, -2).to_numpy(zero_copy_only=False)
    u = pc.fill_null(us, -2).to_numpy(zero_copy_only=False)
    unknown = (g < 0) | (u < 0)
    gb_not_us = pa.array((g == 1) & (u == 0), pa.bool_(), mask=unknown)
    us_not_gb = pa.array((u == 1) & (g == 0), pa.bool_(), mask=unknown)
    return gb_not_us, us_not_gb


def predicate(name: str, table):
    """The mask a filter config selects from `universe`."""
    import pyarrow.compute as pc
    if name == "panel-listed":
        return pc.greater_equal(table["panel_count"], 1)
    if name == "eol-valid":
        return pc.equal(table["eol"], True)
    if name == "spaced":
        return pc.greater(table["token_count"], 1)
    if name == "exceptions":
        return pc.match_substring_regex(
            table["classes"], "(^|;)(" + "|".join(EXCEPTION_CLASSES)
            + ")(;|$)")
    if name == "sample":
        return pc.starts_with(table["id"], SAMPLE_PREFIX)
    raise ReleaseError(f"no predicate named {name!r}")


# ---------------------------------------------------------------------------
# The assertions (§3), each on a table re-read from a written file
# ---------------------------------------------------------------------------

def _hits(words, value_set) -> int:
    import pyarrow as pa
    import pyarrow.compute as pc
    if not value_set:
        return 0
    return pc.sum(pc.is_in(words, value_set=pa.array(sorted(value_set),
                                                     pa.string()))).as_py() \
        or 0


def assert_shippable(table, restricted: set[str], label: str) -> dict:
    """AT-UR1-1: no restricted row and no restricted word."""
    import pyarrow.compute as pc
    if "is_restricted" in table.column_names and \
            pc.any(table["is_restricted"]).as_py():
        raise ReleaseError(f"{label}: a row has is_restricted true")
    hits = _hits(table["word"], restricted)
    if hits:
        raise ReleaseError(f"{label}: {hits} restricted word(s)")
    return {"rows": table.num_rows, "restricted_words_checked":
            len(restricted), "restricted_hits": 0}


def assert_identifiers(table, label: str) -> dict:
    """AT-UR1-3: id is the 16-digit sha256 prefix of word, and unique."""
    import pyarrow.compute as pc
    if not pc.all(pc.equal(table["id"], ids(table["word"]))).as_py():
        raise ReleaseError(f"{label}: an id is not its word's sha256 "
                           "prefix")
    if pc.count_distinct(table["id"]).as_py() != table.num_rows:
        raise ReleaseError(f"{label}: the ids are not unique")
    return {"rows": table.num_rows, "distinct_ids": table.num_rows}


def assert_order(table, words, word_ids, label: str) -> dict:
    """AT-UR1-2 on the re-read file (C-079 line 1, F1): its `word` column
    is the pin's shippable words in order and its `id` column the
    assembled identifiers, both the arrays carried from assembly."""
    import pyarrow as pa
    if table.num_rows != len(words) or not table["word"].equals(
            pa.chunked_array(words) if isinstance(words, pa.Array)
            else words):
        raise ReleaseError(f"{label}: the written words are not the pin's "
                           "shippable words in order")
    if not table["id"].equals(pa.chunked_array(word_ids)
                              if isinstance(word_ids, pa.Array)
                              else word_ids):
        raise ReleaseError(f"{label}: the written ids are not the "
                           "assembled ids in order")
    return {"rows_in_pin_order": table.num_rows}


def assert_nulls(table, nullable: frozenset[str], label: str) -> dict:
    """AT-UR1-2's last clause: no null outside the declared set."""
    bad = [c for c in table.column_names
           if c not in nullable and table[c].null_count]
    if bad:
        raise ReleaseError(f"{label}: nulls in {', '.join(bad)}")
    return {"columns_without_nulls": len(table.column_names)
            - len([c for c in table.column_names if c in nullable])}


def assert_spaced_na(table, label: str,
                     spaced_null: tuple[str, ...] = C.SPACED_NULL) -> dict:
    """AT-UR1-4: the unmeasured columns are null exactly on spaced rows."""
    import pyarrow.compute as pc
    spaced = pc.greater(table["token_count"], 1)
    n_spaced = pc.sum(spaced).as_py() or 0
    for name in spaced_null:
        isnull = pc.is_null(table[name])
        if not pc.all(pc.equal(isnull, spaced)).as_py():
            raise ReleaseError(f"{label}: {name} is not null exactly on "
                               "the spaced rows")
    return {"spaced_rows": n_spaced, "columns": len(spaced_null)}


def assert_columns(table, expected: tuple[str, ...], label: str) -> dict:
    """AT-UR1-6's first clause: exactly the declared columns."""
    if tuple(table.column_names) != tuple(expected):
        extra = sorted(set(table.column_names) - set(expected))
        missing = sorted(set(expected) - set(table.column_names))
        raise ReleaseError(f"{label}: columns differ from the declared "
                           f"list (extra {extra}, missing {missing}, or "
                           "reordered)")
    return {"columns": len(expected)}


def assert_exclusions(table, controls: set[str], ledger_outside: set[str],
                      label: str) -> dict:
    """AT-UR1-6: no synthetic control and no unpinned ledger word."""
    c = _hits(table["word"], controls)
    if c:
        raise ReleaseError(f"{label}: {c} synthetic control(s) present")
    ledger = _hits(table["word"], ledger_outside)
    if ledger:
        raise ReleaseError(f"{label}: {ledger} intake-ledger word(s) "
                           "outside the pin present")
    return {"controls_checked": len(controls), "control_hits": 0,
            "ledger_words_outside_the_pin_checked": len(ledger_outside),
            "ledger_hits": 0}


def assert_release_layer(table, label: str,
                         sets: tuple[str, ...] = C.PANEL_SETS) -> dict:
    """AT-UR1-10: the release layer re-derives from the file's own
    columns."""
    import pyarrow.compute as pc
    checks = (
        ("class_explicit", class_explicit(table["classes"])),
        ("panel_sets", panel_sets(table, sets)),
    )
    for name, want in checks:
        if not pc.all(pc.equal(table[name], want)).as_py():
            raise ReleaseError(f"{label}: {name} does not re-derive")
    count = panel_count_of(table["panel_sets"])
    if not pc.all(pc.equal(pc.cast(count, table["panel_count"].type),
                           table["panel_count"])).as_py():
        raise ReleaseError(f"{label}: panel_count is not the number of "
                           "names in panel_sets")
    gb_not_us, us_not_gb = varieties(table["hunspell_en_GB"],
                                     table["hunspell_en_US"])
    for name, want in (("variety_gb_not_us", gb_not_us),
                       ("variety_us_not_gb", us_not_gb)):
        got = table[name]
        same_nulls = pc.all(pc.equal(pc.is_null(got),
                                     pc.is_null(want))).as_py()
        same = pc.all(pc.fill_null(pc.equal(got, want), True)).as_py()
        if not (same_nulls and same):
            raise ReleaseError(f"{label}: {name} does not re-derive")
    return {"rows": table.num_rows, "columns": 5}


def assert_config(config, universe, name: str) -> dict:
    """AT-UR1-5: the config is `universe` filtered by its predicate."""
    want = universe.filter(predicate(name, universe))
    if not config.equals(want):
        raise ReleaseError(f"{name}: not universe filtered by its "
                           "predicate")
    return {"rows": config.num_rows}


def assert_public(table, label: str, held_back: set[str] | None,
                  version: str, *, rederive_class: bool = False) -> dict:
    """AT-UR1-12, on a re-read file of a public version: no withheld
    column; no label naming a withheld list and no withheld channel label
    in `sources`, `intake_channels`, or `panel_sets`, and the withheld
    channel's label only alone; no held-back row; on the universe config,
    `provenance_class` re-derived from the file's own published fields;
    the key-value metadata the version's files carry; and no census or audit
    row with empty sources (D-012 line 1)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    present = [c for c in W.WITHHELD_SETS + W.WITHHELD_FEATURES
               if c in table.column_names]
    if present:
        raise ReleaseError(f"{label}: withheld columns {present}")
    out = {"withheld_columns_present": 0}
    if "intake_channels" in table.column_names:
        # an allow list, never the projection's own deny list: a label
        # outside the published vocabulary fails
        allowed = {"sources": W.PUBLISHED_SOURCE_LABELS,
                   "intake_channels": W.PUBLISHED_CHANNEL_LABELS,
                   "panel_sets": frozenset(W.PUBLISHED_SETS)}
        for field, vocabulary in allowed.items():
            for value in pc.unique(table[field]).to_pylist():
                labels = [x for x in (value or "").split(";") if x]
                if set(labels) - vocabulary or (W.CHANNEL_WITHHELD in labels
                                                and len(labels) > 1):
                    raise ReleaseError(f"{label}: {field} names a withheld "
                                       "list or label, or a label outside the "
                                       "published vocabulary")
        # a row whose every channel is withheld had a channel in the full
        # projection, so D-011 holds it back if nothing public is left
        if pc.any(pc.and_(pc.equal(table["intake_channels"], W.CHANNEL_WITHHELD),
                          pc.equal(table["provenance_class"], W.CLASSES[3]))
                  ).as_py():
            raise ReleaseError(f"{label}: a row marked {W.CHANNEL_WITHHELD} "
                               "has no public evidence and should be held back")
        # D-012 line 1: no shipped census or audit row has empty sources
        if "intake_layer" in table.column_names and pc.any(pc.and_(
                pc.is_in(table["intake_layer"], value_set=pa.array(
                    list(W.SOURCE_LISTING_LAYERS))),
                pc.equal(table["sources"], ""))).as_py():
            raise ReleaseError(f"{label}: a census or audit row ships with "
                               "empty sources, which D-012 line 1 holds back")
        out["withheld_labels_found"] = 0
    hits = _hits(table["word"], held_back or set())
    if hits:
        raise ReleaseError(f"{label}: {hits} held-back row(s) present")
    out["held_back_rows_present"] = 0
    if rederive_class:
        out["held_back_rows"] = len(held_back or ())
        want = W.classes_of(table["intake_channels"], table["panel_count"],
                            table["gb_type"], table["wordfreq_scored"])
        if not pc.all(pc.equal(table["provenance_class"], want)).as_py():
            raise ReleaseError(f"{label}: provenance_class does not re-derive "
                               "from the published fields")
        out["provenance_class_rederived"] = table.num_rows
    meta = table.schema.metadata or {}
    if dict(meta) != file_metadata(version):
        raise ReleaseError(f"{label}: the key-value metadata is not the "
                           "version's")
    out["metadata_keys"] = len(METADATA_KEYS)
    return out


def universe_assertions(written, words, word_ids, expected_rows: int,
                        restricted: set[str], controls: set[str],
                        ledger_outside: set[str], prof: Profile = FULL,
                        public: dict | None = None) -> dict:
    """The universe config's assertion blocks, on its re-read file;
    `public` (held_back, version) adds AT-UR1-12."""
    if written.num_rows != expected_rows:
        raise ReleaseError("universe: the written row count drifted")
    in_order = assert_order(written, words, word_ids, "universe")
    out = {
        "AT-UR1-1": assert_shippable(written, restricted, "universe"),
        "AT-UR1-2": {"rows": written.num_rows,
                     "expected_rows": expected_rows,
                     **assert_nulls(written, prof.nullable, "universe"),
                     **in_order},
        "AT-UR1-3": assert_identifiers(written, "universe"),
        "AT-UR1-4": assert_spaced_na(written, "universe", prof.spaced_null),
        "AT-UR1-6": {**assert_columns(written, prof.columns, "universe"),
                     **assert_exclusions(written, controls, ledger_outside,
                                         "universe")},
        "AT-UR1-10": assert_release_layer(written, "universe", prof.sets),
    }
    if public is not None:
        out["AT-UR1-12"] = assert_public(written, "universe",
                                         public["held_back"],
                                         public["version"],
                                         rederive_class=True)
        out["AT-UR1-13"] = assert_model_column(written, public["basis"],
                                               "universe")
    return out


def filter_assertions(config, universe, name: str,
                      restricted: set[str], prof: Profile = FULL,
                      public: dict | None = None) -> dict:
    """A filter config's assertion blocks, on its re-read file."""
    out = {
        "AT-UR1-1": assert_shippable(config, restricted, name),
        "AT-UR1-5": assert_config(config, universe, name),
        "AT-UR1-6": assert_columns(config, prof.columns, name),
    }
    if public is not None:
        out["AT-UR1-12"] = assert_public(config, name, public["held_back"],
                                         public["version"])
    return out


def features_assertions(fwritten, universe, restricted: set[str],
                        controls: set[str], ledger_outside: set[str],
                        public: dict | None = None,
                        prof: Profile = FULL) -> dict:
    """The features config's assertion blocks, on its re-read file: no
    column holds a null (C-079 line 1, F1; the feature layer's NaN is a
    float value, not a null, so the nullable set is empty), then 1 row per
    single-token row of `universe`, in its order."""
    import pyarrow.compute as pc
    no_nulls = assert_nulls(fwritten, frozenset(), "features")
    single = universe.filter(pc.equal(universe["token_count"], 1))
    if fwritten.num_rows != single.num_rows or not pc.all(
            pc.equal(fwritten["word"], single["word"])).as_py():
        raise ReleaseError("features: not 1 row per single-token row of "
                           "universe, in its order")
    if pc.any(pc.match_substring(fwritten["word"], " ")).as_py():
        raise ReleaseError("features: a spaced row is present")
    out = {
        "AT-UR1-1": assert_shippable(fwritten, restricted, "features"),
        "AT-UR1-2": {"rows": fwritten.num_rows,
                     "single_token_rows_of_universe": single.num_rows,
                     **no_nulls},
        "AT-UR1-3": assert_identifiers(fwritten, "features"),
        "AT-UR1-4": {"spaced_rows": 0},
        "AT-UR1-6": {**assert_columns(fwritten, ("id", "word") + prof.features,
                                      "features"),
                     **assert_exclusions(fwritten, controls, ledger_outside,
                                         "features")},
    }
    if public is not None:
        out["AT-UR1-12"] = assert_public(fwritten, "features",
                                         public["held_back"],
                                         public["version"])
    return out


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------

def _record_value(record: Path, key: tuple[str, ...]):
    value = json.loads(record.read_text(encoding="utf-8"))
    for k in key:
        value = value[k]
    return value


def verify_layers(spec: VersionSpec) -> dict[str, dict]:
    """Every layer's bytes against its committed record, before any read."""
    out = {}
    for layer in spec.layers:
        want = _record_value(layer.record, layer.key)
        got = sha256_file(layer.path)
        if got != want:
            raise ReleaseError(f"{layer.name}: {layer.path.name} sha256 "
                               f"{got} is not the recorded {want}")
        out[layer.name] = {"path": _rel(layer.path), "sha256": got,
                           "record": _rel(layer.record),
                           "record_key": ".".join(layer.key)}
    return out


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        try:
            return path.relative_to(REPO).as_posix()
        except ValueError:
            return path.name


def read_restricted(spec: VersionSpec, expected: int) -> set[str]:
    with open(spec.restricted_csv, encoding="utf-8") as f:
        words = {row["word"] for row in csv.DictReader(f)}
    if len(words) != expected:
        raise ReleaseError(f"the restricted split holds {len(words)} "
                           f"words, not the pin's {expected}")
    return words


def read_ledger_words(spec: VersionSpec) -> set[str]:
    """The intake ledger's words (the file has no header line; its columns
    are the manifest's)."""
    cols = json.loads(spec.ledger_manifest.read_text(
        encoding="utf-8"))["columns"]
    at = cols.index("word")
    with open(spec.ledger_csv, newline="", encoding="utf-8") as f:
        return {row[at] for row in csv.reader(f) if row}


def read_controls() -> set[str]:
    from research.inthewild.walled_terms import walled_terms
    return walled_terms()["controls"]


def ledger_outside_the_pin(spec: VersionSpec, pin_words) -> set[str]:
    """The intake ledger's words that are not words of the pin (C-078
    line 4: intake-ledger rows not yet pinned are not shipped)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    ledger = pa.array(sorted(read_ledger_words(spec)), pa.string())
    in_pin = pc.is_in(ledger, value_set=pin_words).to_numpy(
        zero_copy_only=False)
    return set(ledger.filter(pa.array(~in_pin)).to_pylist())


def _join_positions(keys, layer_words, label: str):
    """Positions of `keys` in a layer's word column (-1 where absent),
    after asserting the layer's keys unique."""
    import pyarrow.compute as pc
    if pc.count_distinct(layer_words).as_py() != len(layer_words):
        raise ReleaseError(f"{label}: the layer's words are not unique")
    pos = pc.index_in(keys, value_set=layer_words)
    return pc.fill_null(pos, -1).to_numpy(zero_copy_only=False)


def _take(column, positions):
    import pyarrow as pa
    idx = pa.array(positions, pa.int64(), mask=positions < 0)
    return column.take(idx)


def assemble_universe(pin, provenance, evidence, expected_rows: int):
    """The universe config's table (§2.2) from the 3 layers, joined by
    word, with the identifier and the release layer."""
    import pyarrow as pa
    import pyarrow.compute as pc

    if tuple(pin.column_names) != C.PIN_LAYER_COLUMNS:
        raise ReleaseError("the pin's columns are not the 14 recorded")
    ship = pin.filter(pc.invert(pin["is_restricted"]))
    if ship.num_rows != expected_rows:
        raise ReleaseError(f"shippable rows {ship.num_rows} != the pin "
                           f"record's {expected_rows}")
    words = ship["word"]
    if pc.count_distinct(words).as_py() != ship.num_rows:
        raise ReleaseError("the pin's words are not unique")
    single = (ship["token_count"].to_numpy(zero_copy_only=False) == 1)

    pv = _join_positions(words, provenance["word"], "provenance")
    if (pv < 0).any():
        raise ReleaseError(f"provenance: {(pv < 0).sum()} row(s) without "
                           "a provenance row")
    ev = _join_positions(words, evidence["word"], "evidence")
    if ((ev < 0) & single).any():
        raise ReleaseError(f"evidence: {((ev < 0) & single).sum()} "
                           "single-token row(s) without an evidence row")
    if ((ev >= 0) & ~single).any():
        raise ReleaseError("evidence: a spaced row found an evidence row")

    cols: dict[str, object] = {"id": ids(words), "word": words}
    for name in C.PIN_LAYER_COLUMNS[1:]:
        cols[name] = ship[name]
    ev_cols = {name: _take(evidence[name], ev)
               for name in C.EVIDENCE_LAYER_COLUMNS}
    pv_cols = {name: _take(provenance[name], pv)
               for name in C.PROVENANCE_LAYER_COLUMNS[1:]}
    staged = pa.table({**{k: cols[k] for k in ("token_count", "sources")},
                       **ev_cols})
    cols["class_explicit"] = class_explicit(ship["classes"])
    cols["panel_sets"] = panel_sets(staged)
    cols["variety_gb_not_us"], cols["variety_us_not_gb"] = varieties(
        ev_cols["hunspell_en_GB"], ev_cols["hunspell_en_US"])
    cols.update(pv_cols)
    cols.update(ev_cols)
    table = pa.table({name: cols[name] for name in C.UNIVERSE_COLUMNS})
    count = panel_count_of(table["panel_sets"])
    if not pc.all(pc.equal(pc.cast(count, pa.int16()),
                           table["panel_count"])).as_py():
        raise ReleaseError("the provenance layer's panel_count is not the "
                           "number of names in panel_sets (reading R1)")
    return table


def model_or_engine(universe, basis):
    """The model-or-engine column (columns.MODEL): engine_generated where
    the provenance layer's intake_kind is generated; the model-basis
    layer's value, joined by word, on the rows of the EOL's valid list it
    holds; none elsewhere."""
    import pyarrow as pa
    import pyarrow.compute as pc
    from research.provenance import model_basis as M
    pos = _join_positions(universe["word"], basis["word"], "model_basis")
    if int((pos >= 0).sum()) != basis.num_rows:
        raise ReleaseError("model_basis: a layer row matches no row of the "
                           "universe")
    value = _take(basis["model_basis"], pos)
    generated = pc.equal(universe["intake_kind"], "generated")
    if pc.any(pc.and_(generated, pc.is_valid(value))).as_py():
        raise ReleaseError("model_basis: a generated row carries a model basis")
    if pc.any(pc.and_(pc.is_valid(value), pc.invert(universe["eol"]))).as_py():
        raise ReleaseError("model_basis: a row outside the EOL's valid list "
                           "carries a model basis")
    out = pc.if_else(generated, pa.scalar(M.VALUES[0]),
                     pc.fill_null(value, M.VALUES[-1]))
    return pc.cast(out, pa.string())


def assert_model_column(table, basis, label: str) -> dict:
    """AT-UR1-13, on the re-read universe of a public version: the column
    re-derives from the file's own intake_kind and eol and the verified
    model-basis layer."""
    import collections
    import pyarrow as pa
    import pyarrow.compute as pc
    from research.provenance import model_basis as M
    want = model_or_engine(table, basis.filter(pc.is_in(
        basis["word"], value_set=table["word"])))
    # a public version keeps engine_generated and none only
    # (withholding.without_eol_intake): a model value is a fact of how the
    # EOL took a word in
    kept = pc.is_in(want, value_set=pa.array(sorted(W.PUBLISHED_MODEL_OR_ENGINE)))
    want = pc.if_else(kept, want, pa.scalar("none"))
    if not pc.all(pc.equal(table["model_or_engine"], want)).as_py():
        raise ReleaseError(f"{label}: model_or_engine does not re-derive")
    counts = collections.Counter(table["model_or_engine"].to_pylist())
    if set(counts) - set(M.VALUES):
        raise ReleaseError(f"{label}: model_or_engine holds an undeclared value")
    outside = pc.sum(pc.and_(pc.is_in(table["model_or_engine"], value_set=
                     pa.array(list(M.VALUES[1:3]), pa.string())),
                     pc.invert(table["eol"]))).as_py() or 0
    return {"rows_by_value": {v: counts.get(v, 0) for v in M.VALUES
                              if v in W.PUBLISHED_MODEL_OR_ENGINE},
            "generated_rows": int(pc.sum(pc.equal(table["intake_kind"],
                                                  "generated")).as_py() or 0),
            "model_rows_outside_the_eol_valid_list": outside}


def assemble_features(universe, features,
                      names: tuple[str, ...] = C.FEATURE_LAYER_COLUMNS):
    """The features config: the universe's single-token rows, keyed by id
    and word, with the feature layer's columns `names` joined by word."""
    import pyarrow as pa
    import pyarrow.compute as pc
    rows = universe.filter(pc.equal(universe["token_count"], 1))
    pos = _join_positions(rows["word"], features["word"], "features")
    if (pos < 0).any():
        raise ReleaseError(f"features: {(pos < 0).sum()} single-token "
                           "row(s) without a feature row")
    cols = {"id": rows["id"], "word": rows["word"]}
    for name in names:
        cols[name] = _take(features[name], pos)
    return pa.table(cols)


def row_group_rows(table) -> int:
    """Whole quanta of rows under the row-group bound (§2.6)."""
    per_row = max(1, table.nbytes // max(1, table.num_rows))
    fit = MAX_ROW_GROUP_BYTES // per_row
    quanta = max(1, fit // ROW_GROUP_QUANTUM) * ROW_GROUP_QUANTUM
    return max(1, min(table.num_rows, quanta))


def bounds() -> dict:
    """The record's bounds block, with the policy it enforces."""
    return {"max_shard_bytes": MAX_SHARD_BYTES,
            "max_row_group_bytes": MAX_ROW_GROUP_BYTES,
            "row_group_quantum": ROW_GROUP_QUANTUM,
            "policy": SIZE_POLICY}


def first_group_rows(path: Path) -> int:
    """A written file's first row group's rows, read from its metadata; 0
    for a file with no row group (an empty config)."""
    import pyarrow.parquet as pq
    meta = pq.ParquetFile(path).metadata
    return meta.row_group(0).num_rows if meta.num_row_groups else 0


def parquet_sizes(path: Path) -> dict:
    """A written file's uncompressed sizes, from its Parquet metadata
    (C-079 line 1, F4): the total over its row groups, and its largest
    row group's."""
    import pyarrow.parquet as pq
    meta = pq.ParquetFile(path).metadata
    groups = [meta.row_group(i).total_byte_size
              for i in range(meta.num_row_groups)]
    return {"measured_uncompressed_bytes": sum(groups),
            "largest_row_group_uncompressed_bytes": max(groups, default=0)}


def write_file(table, path: Path, metadata: dict | None = None) -> dict:
    import pyarrow.parquet as pq
    if metadata:
        table = table.replace_schema_metadata(
            {**(table.schema.metadata or {}), **metadata})
    rg = row_group_rows(table)
    pq.write_table(table, path, compression="zstd", row_group_size=rg)
    size = path.stat().st_size
    if size >= MAX_SHARD_BYTES:
        raise ReleaseError(f"{path.name}: {size} compressed bytes is over "
                           f"the shard bound {MAX_SHARD_BYTES}; sharding is "
                           "not implemented (reading R10)")
    return {"rows": table.num_rows, "columns": list(table.column_names),
            "row_group_rows": first_group_rows(path), "bytes": size,
            "sha256": sha256_file(path), **parquet_sizes(path)}


@dataclass
class Prepared:
    """What a build reads before it writes (`prepare`)."""
    sources: dict
    counts: dict
    expected: int
    restricted: set
    controls: set
    ledger_outside: set
    layer: dict
    universe: object
    #: a public version's held-back rows (word, reason); None for "full"
    held: object = None
    #: a public version's model-basis layer; None for "full"
    basis: object = None
    #: a public version's reach counts (withholding.project_and_measure),
    #: for the private receipt only; None for "full"
    reach: object = None

    @property
    def shipped(self) -> int:
        """The rows the universe config carries."""
        return self.expected - (self.held.num_rows if self.held is not None
                                else 0)


def prepare(spec: VersionSpec, controls: set[str] | None = None,
            log=print) -> Prepared:
    """Everything the build reads before it writes, in the build's order:
    the layers verified against their committed records before any read,
    the pin record and its schema, the restricted split, the controls, the
    intake ledger's words outside the pin, and the universe assembled from
    the layers. `build` and `record_only` both start here."""
    import pyarrow.parquet as pq
    sources = verify_layers(spec)
    log(f"[release] {spec.version}: {len(sources)} layers equal their "
        "committed records")

    pin_record = json.loads(spec.pin_record.read_text(encoding="utf-8"))
    counts = pin_record["counts"]
    if pin_record["schema_columns"] != list(C.PIN_LAYER_COLUMNS):
        raise ReleaseError("the pin record's schema is not the 14 "
                           "columns this version carries")
    expected = counts["v2_rows"] - counts["restricted_rows"]
    restricted = read_restricted(spec, counts["restricted_rows"])
    controls = read_controls() if controls is None else controls
    layer = {x.name: x for x in spec.layers}
    pin = pq.read_table(layer["pin"].path)
    ledger_outside = ledger_outside_the_pin(spec, pin["word"])

    provenance = pq.read_table(layer["provenance"].path,
                               columns=list(C.PROVENANCE_LAYER_COLUMNS))
    evidence = pq.read_table(layer["evidence"].path,
                             columns=["word", *C.EVIDENCE_LAYER_COLUMNS])
    universe = assemble_universe(pin, provenance, evidence, expected)
    del pin, provenance, evidence
    log(f"[release] universe assembled: {universe.num_rows:,} rows, "
        f"{universe.num_columns} columns")
    held = basis = reach = None
    if spec.public:
        basis = pq.read_table(layer["model_basis"].path)
        universe = universe.append_column(
            C.MODEL[0][0], model_or_engine(universe, basis))
        try:
            universe, held, reach = W.project_and_measure(universe)
        except W.UncoveredRow as exc:
            raise ReleaseError(f"the public projection: {exc}") from None
        log(f"[release] public projection: {universe.num_rows:,} rows ship, "
            f"{held.num_rows:,} held back")
        # the reach guard: no published channel label and no layer's emptied
        # sources may be a withheld list's copy; the counts stay in a private
        # receipt
        breaches = W.reach_breaches(reach, spec.reach_threshold)
        if breaches:
            raise ReleaseError(
                f"the reach guard: 1 withheld list lists {spec.reach_threshold:.0%} "
                f"or more of the rows of {'; '.join(breaches)}")
    return Prepared(sources, counts, expected, restricted, controls,
                    ledger_outside, layer, universe, held, basis, reach)


def refuse_a_committed_tree(path: Path) -> None:
    """A private file of a public version (the held-back rows, their sidecar,
    the reach receipt) is written only under the ignored data/ or private/
    folders: `--out DIR` anywhere else, a
    committed folder or another checkout or a temporary folder, is refused."""
    from safeguards import locations
    where = path.parent.resolve()
    for root in (locations.data_dir().resolve(),
                 locations.private_dir().resolve()):
        if where == root or root in where.parents:
            return
    raise ReleaseError(f"{path.name} would be written outside data/ and "
                       "private/; build into data/")


def _remove(path: Path) -> list[str]:
    """Remove a file or a directory tree; return the failures, so that a
    failed removal is reported and never ignored (C-080 line 2, F2)."""
    errors: list[str] = []
    if path.is_dir() and not path.is_symlink():
        def note(_func, where, exc_info):
            errors.append(f"{where}: {exc_info[1]}")
        shutil.rmtree(path, onerror=note)
    elif path.exists() or path.is_symlink():
        try:
            path.unlink()
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    return errors


def code_identity(repo: Path = REPO) -> dict:
    """The commit of the code that builds a version, and whether the
    pipeline's tracked files differ from it (docs/UPKEEP.md §6: each
    release records the code's commit)."""
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    try:
        commit = git("rev-parse", "HEAD")
        changed = git("status", "--porcelain", "--untracked-files=no", "--",
                      ".")
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "tracked_files_changed": None}
    return {"commit": commit, "tracked_files_changed": bool(changed)}


def notices_source(spec: VersionSpec) -> Path:
    """The committed NOTICES file of a public version (`notices.py` writes
    it from the pinned sources)."""
    path = spec.notices or (REPO / "research" / "release"
                            / f"NOTICES_{spec.version}.md")
    if not path.exists():
        raise ReleaseError(f"{_rel(path)} is absent; write it with "
                           "python3 -m research.release.notices")
    if spec.notices is None:
        # the generated file ships only as its generator prints it from the
        # pinned inputs, which the build machine holds; a stand-in NOTICES (a test's) is taken as given
        from . import notices as N
        try:
            text = N.render(spec.version, N.inputs())
        except N.InputAbsent as exc:
            raise ReleaseError(f"NOTICES cannot be checked against its "
                               f"generator: {exc}") from None
        if path.read_text(encoding="utf-8") != text:
            raise ReleaseError(f"{_rel(path)} is not what notices.py prints; "
                               "run python3 -m research.release.notices")
    return path


def differenced_cells(held, floor: int) -> list[str]:
    """The held-back counts a reader could find by differencing v2.0's and
    this version's published counts by layer, kind, and class that are more than 0 and fewer than `floor`, as "field=value"
    (no count)."""
    import collections
    out = []
    for name in W.DIFFERENCED:
        if name not in held.column_names:
            continue
        for value, n in collections.Counter(held[name].to_pylist()).items():
            if 0 < n < floor:
                out.append(f"{name}={value}")
    return sorted(out)


def projection_block(held, floor: int = 10,
                     threshold: float = W.REACH_THRESHOLD) -> dict:
    """The record's account of the public projection (D-010, D-011). The
    held-back rows are counted by reason and never listed; the record holds
    no hash of their private file, which would confirm a guessed set (the
    lead's review of PR 4, S1). A reason with fewer rows than `floor`, but
    more than none, refuses the build (docs/ANALYSIS_PLAN.md §9 rule 2: the
    record also states the total, so a small cell could not be suppressed)."""
    import collections
    reasons = collections.Counter(held["reason"].to_pylist())
    by_reason = {k: reasons.get(k, 0) for k in W.HELD_BACK_REASONS}
    small = [k for k, n in by_reason.items() if 0 < n < floor]
    if small:
        raise ReleaseError(f"the held-back reasons {small} count fewer than "
                           f"{floor} rows; the record cannot publish them")
    cells = differenced_cells(held, floor)
    if cells:
        raise ReleaseError(f"the held-back rows of {cells} count fewer than "
                           f"{floor}, and v2.0's published counts less this "
                           "version's would show them")
    prefixes = ", ".join(p or "''" for p in W.LABEL_PREFIXES)
    return {
        "rule": "research/release/withholding.py",
        "decisions": ["C-079 line 2", "C-083 line 5", "D-010", "D-011",
                      "D-012"],
        "withheld_columns": list(W.WITHHELD_SETS),
        "withheld_feature_columns": list(W.WITHHELD_FEATURES),
        "withheld_labels": "every label naming a withheld list, under the "
                           f"prefixes {prefixes}",
        "withheld_channel_labels": sorted(W.WITHHELD_CHANNEL_LABELS),
        "channel_withheld_label": W.CHANNEL_WITHHELD,
        "recomputed": ["panel_sets", "panel_count", "provenance_class"],
        "held_back": {
            "rule": "a row with no public evidence that had some over the "
                    "full fields (D-011), or a census or audit row whose "
                    "every source label names a withheld list (D-012 line 1)",
            "rows": held.num_rows,
            "by_reason": by_reason,
            "reasons": dict(W.HELD_BACK_REASONS),
            "private_file": "beside the release directory, with its sha256 "
                            "in a private sidecar beside it; never committed "
                            "or uploaded",
        },
        "reach_guard": {
            "rule": "no published channel label, and no layer's shipped rows "
                    "whose sources come out empty, has this share or more of "
                    "its rows listed by any 1 withheld list",
            "threshold": threshold,
            "counts": "in a private receipt beside the held-back file; never "
                      "committed or uploaded",
        },
        "metadata_keys": list(METADATA_KEYS),
    }


def build(spec: VersionSpec, out_dir: Path | None = None,
          record_out: Path | None = None, *, replace: bool = False,
          controls: set[str] | None = None, today: str | None = None,
          log=print) -> dict:
    """Build a version; return its record (written last)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir = out_dir or spec.out_dir
    record_out = record_out or spec.record_out
    if out_dir.exists() and not replace:
        raise ReleaseError(f"{out_dir} exists; pass --replace to rebuild "
                           "it, or --out to build elsewhere")
    code = code_identity() if spec.public else None
    ready = prepare(spec, controls, log)
    sources, counts, expected = ready.sources, ready.counts, ready.expected
    restricted, controls = ready.restricted, ready.controls
    ledger_outside, layer, universe = (ready.ledger_outside, ready.layer,
                                       ready.universe)
    held, shipped, reach = ready.held, ready.shipped, ready.reach
    public = ({"held_back": set(held["word"].to_pylist()),
               "version": spec.version, "basis": ready.basis}
              if spec.public else None)
    del ready
    prof = profile(spec)
    # the projection's account, its small-cell guard before anything is
    # written (N2)
    block = projection_block(held, spec.suppression_floor,
                             spec.reach_threshold) if spec.public \
        else None
    meta = file_metadata(spec.version) if spec.public else None
    notices = notices_source(spec) if spec.public else None
    # the private file of the rows a public version holds back: beside the
    # release directory, never in it
    held_out = out_dir.parent / f"{out_dir.name}.held-back.parquet"
    held_staged = out_dir.parent / f".staging-{held_out.name}"
    held_sidecar = out_dir.parent / f"{out_dir.name}.held-back.json"
    reach_receipt = out_dir.parent / f"{out_dir.name}.reach.json"
    if spec.public:
        refuse_a_committed_tree(held_out)
    # the expected arrays the written universe is held to (F1)
    words, word_ids = universe["word"], universe["id"]

    staging = out_dir.parent / f".staging-{out_dir.name}"
    if staging.exists():
        leftover = _remove(staging)
        if leftover:
            raise ReleaseError("a staging directory from an earlier build "
                               f"could not be removed: {'; '.join(leftover)}")
    staging.mkdir(parents=True)
    promoted = False
    files: list[dict] = []
    assertions: dict[str, dict] = {}

    record_tmp = record_out.with_name(record_out.name + ".tmp")
    # a failure from here on removes the staging directory before it
    # raises, so a failed build leaves no file (C-079 line 1, F1); the
    # record is written only after the files are in place
    try:
        # the universe config, re-read and asserted before anything else
        info = write_file(universe, staging / "universe.parquet", meta)
        del universe
        written = pq.read_table(staging / "universe.parquet")
        assertions["universe"] = universe_assertions(
            written, words, word_ids, shipped, restricted, controls,
            ledger_outside, prof, public)
        del words, word_ids
        files.append({"config": "universe", "path": "universe.parquet",
                      "predicate": UNIVERSE_PREDICATE, **info})
        log(f"[release] universe.parquet asserted ({info['bytes']:,} "
            "bytes)")

        # the filter configs, each re-read and compared with its predicate
        for name, pred in prof.filters:
            path = staging / f"{name}.parquet"
            info = write_file(written.filter(predicate(name, written)), path,
                              meta)
            config = pq.read_table(path)
            assertions[name] = filter_assertions(config, written, name,
                                                 restricted, prof, public)
            files.append({"config": name, "path": path.name,
                          "predicate": pred, **info})
            log(f"[release] {path.name} asserted: {info['rows']:,} rows")
            del config

        # the features config
        feats = pq.read_table(layer["features"].path,
                              columns=["word", *prof.features])
        table = assemble_features(written, feats, prof.features)
        del feats
        path = staging / "features.parquet"
        info = write_file(table, path, meta)
        del table
        fwritten = pq.read_table(path)
        assertions["features"] = features_assertions(
            fwritten, written, restricted, controls, ledger_outside, public,
            prof)
        files.append({"config": "features", "path": "features.parquet",
                      "predicate": FEATURES_PREDICATE, **info})
        log(f"[release] features.parquet asserted: {info['rows']:,} rows")
        del fwritten, written
        assert_schema(assertions, spec.public)
        documents = []
        if spec.public:
            target = staging / "NOTICES.md"
            shutil.copyfile(notices, target)
            documents.append({"path": target.name, "source": _rel(notices),
                              "bytes": target.stat().st_size,
                              "sha256": sha256_file(target)})
            pq.write_table(held, held_staged, compression="zstd")

        # every assertion passed: move the files into place, still inside
        # the protected block (C-080 line 2, F2), then write the record
        if out_dir.exists():
            leftover = _remove(out_dir)
            if leftover:
                raise ReleaseError(f"{_rel(out_dir)} could not be removed "
                                   f"before the promotion: {'; '.join(leftover)}")
        staging.rename(out_dir)
        promoted = True
        if spec.public:
            held_staged.replace(held_out)
            # the held-back file's identity, kept private beside it (S1)
            held_sidecar.write_text(json.dumps(
                {"version": spec.version, "path": _rel(held_out),
                 "rows": held.num_rows, "sha256": sha256_file(held_out)},
                indent=2) + "\n", encoding="utf-8")
            # the reach guard's counts, private beside it
            reach_receipt.write_text(json.dumps(
                {"version": spec.version, "threshold": spec.reach_threshold,
                 **reach}, indent=1) + "\n", encoding="utf-8")
        # the record, inside the protected block, so that a failure while it
        # is built or written removes the promoted files too (G4 audit, F7)
        order = prof.configs
        files.sort(key=lambda f: order.index(f["config"]))
        record = {
            "generated_by": "research/release/build_release.py",
            "dataset": DATASET,
            "version": spec.version,
            "decision": "C-078",
            "pin_entry": spec.pin_entry,
            "visibility": ("private until the owner's word (rule 1)"
                           if spec.public else
                           "private (C-078 line 3: never made public at this "
                           "version)"),
            "built_on": today or date.today().isoformat(),
            **({"code": code} if spec.public else {}),
            "canary": CANARY,
            "sources": sources,
            "pin_counts": {"rows": counts["v2_rows"],
                           "restricted_rows": counts["restricted_rows"],
                           "shippable_rows": expected,
                           "spaced_rows": counts["spaced_additions"],
                           "eol_valid": counts["eol_valid"]},
            **({"projection": block} if spec.public else {}),
            "rows_by_config": {f["config"]: f["rows"] for f in files},
            "files": files,
            **({"documents": documents} if spec.public else {}),
            "release_layer": {
                "id": "sha256(word as UTF-8)[:16]",
                "class_explicit": "classes, with 'plain' for the empty string",
                "panel_sets": "the panel sets listing the row, ';'-joined in "
                              "the order " + ", ".join(prof.sets),
                "panel_count": ("the number of names in panel_sets, recomputed "
                                "over the published panel" if spec.public else
                                "the provenance layer's panel_count, equal to "
                                "the number of names in panel_sets"),
                "variety_gb_not_us": "hunspell_en_GB == 1 and hunspell_en_US "
                                     "== 0; null where either is -1 or null",
                "variety_us_not_gb": "hunspell_en_US == 1 and hunspell_en_GB "
                                     "== 0; null where either is -1 or null",
                **({"model_or_engine": "engine_generated where intake_kind is "
                    "generated; else none (the model-basis layer's values are "
                    "not published: withholding.without_eol_intake)"}
                   if spec.public else {}),
            },
            "bounds": bounds(),
            "assertions": assertions,
            "software": {"python": platform.python_version(),
                         "pyarrow": pa.__version__},
        }
        record_out.parent.mkdir(parents=True, exist_ok=True)
        record_tmp.write_text(json.dumps(record, indent=2) + "\n",
                              encoding="utf-8")
        record_tmp.replace(record_out)
    except BaseException as exc:
        # a failed build leaves no file (C-079 line 1, F1): the staging, the
        # held-back file, and a promoted directory whose record was never
        # written are removed, and a removal that fails is reported
        failed = _remove(staging) + _remove(held_staged) + _remove(record_tmp)
        if promoted:
            failed += (_remove(out_dir) + _remove(held_out)
                       + _remove(held_sidecar) + _remove(reach_receipt))
        if failed:
            raise ReleaseError(f"the build failed ({exc!r}), and these could "
                               f"not be removed: {'; '.join(failed)}") from exc
        raise

    log(f"[release] {spec.version} written to {_rel(out_dir)}; record "
        f"{_rel(record_out)}")
    return record


def record_only(spec: VersionSpec, out_dir: Path | None = None,
                record_out: Path | None = None, *,
                controls: set[str] | None = None, today: str | None = None,
                log=print) -> dict:
    """Rewrite the record of a version already built, and write no file
    (C-079 line 1, F4). Every file the record names is re-read and its
    sha256 must equal the record's, or nothing is written; then, as the
    build does, the layers are verified and the universe assembled, and
    the assertions re-run on the existing files; every count and identity
    the record states must re-derive. The record is rewritten with each
    file's measured uncompressed sizes, the size policy, and the
    assertion blocks the build now writes (the recorded fields unchanged,
    the fields added since kept beside them); its build date stays, and
    the rewrite's date is recorded. The files are hashed again before the
    record is written."""
    import pyarrow.parquet as pq
    out_dir = out_dir or spec.out_dir
    record_out = record_out or spec.record_out
    if not record_out.exists():
        raise ReleaseError(f"{_rel(record_out)} is absent; --record-only "
                           "rewrites the record of files already built")
    record = json.loads(record_out.read_text(encoding="utf-8"))
    if record.get("version") != spec.version:
        raise ReleaseError(f"{_rel(record_out)} records version "
                           f"{record.get('version')!r}, not {spec.version}")
    # the file inventory against the build's configs (C-080 line 2, F1)
    configs = sorted(profile(spec).configs)
    named = [f.get("config") for f in record.get("files", [])]
    if sorted(named) != configs:
        raise ReleaseError(f"the record's file inventory {sorted(named)} is "
                           f"not the build's configs {configs}")
    for f in record["files"]:
        if f.get("path") != f"{f['config']}.parquet":
            raise ReleaseError(f"{f['config']}: the record names the file "
                               f"{f.get('path')!r}, not {f['config']}.parquet")
    hashes: dict[str, str] = {}
    for f in record["files"]:
        path = out_dir / f["path"]
        got = sha256_file(path) if path.exists() else None
        if got != f["sha256"]:
            raise ReleaseError(f"{f['path']} is not the file the record "
                               f"names (sha256 {got}); --record-only "
                               "rewrites the record of the files it names "
                               "and never a file")
        hashes[f["path"]] = got
    log(f"[release] {spec.version}: {len(hashes)} files equal the record")

    ready = prepare(spec, controls, log)
    if ready.sources != record["sources"]:
        raise ReleaseError("the layers' identities are not the record's")
    # the pin's counts re-derive from the pin record (C-080 line 2, F1)
    pin_counts = {"rows": ready.counts["v2_rows"],
                  "restricted_rows": ready.counts["restricted_rows"],
                  "shippable_rows": ready.expected,
                  "spaced_rows": ready.counts["spaced_additions"],
                  "eol_valid": ready.counts["eol_valid"]}
    if record.get("pin_counts") != pin_counts:
        raise ReleaseError("the recorded pin_counts do not re-derive from the "
                           "pin record")
    if spec.public and record.get("projection", {}).get("held_back", {}).get(
            "rows") != ready.held.num_rows:
        raise ReleaseError("the recorded held-back rows do not re-derive")
    prof = profile(spec)
    public = ({"held_back": set(ready.held["word"].to_pylist()),
               "version": spec.version, "basis": ready.basis}
              if spec.public else None)
    if spec.public:
        # the projection block re-derives from the projection, and the
        # private file is the one its sidecar names (S6)
        if record.get("projection") != projection_block(
                ready.held, spec.suppression_floor, spec.reach_threshold):
            raise ReleaseError("the recorded projection does not re-derive")
        held_out = out_dir.parent / f"{out_dir.name}.held-back.parquet"
        sidecar = out_dir.parent / f"{out_dir.name}.held-back.json"
        if not held_out.exists() or not sidecar.exists() or json.loads(
                sidecar.read_text(encoding="utf-8"))["sha256"] != \
                sha256_file(held_out):
            raise ReleaseError("the held-back file is not the one its private "
                               "sidecar names")
    words, word_ids = ready.universe["word"], ready.universe["id"]
    ready.universe = None
    written = pq.read_table(out_dir / "universe.parquet")
    assertions = {"universe": universe_assertions(
        written, words, word_ids, ready.shipped, ready.restricted,
        ready.controls, ready.ledger_outside, prof, public)}
    del words, word_ids
    for name, _pred in prof.filters:
        assertions[name] = filter_assertions(
            pq.read_table(out_dir / f"{name}.parquet"), written, name,
            ready.restricted, prof, public)
    fwritten = pq.read_table(out_dir / "features.parquet")
    assertions["features"] = features_assertions(
        fwritten, written, ready.restricted, ready.controls,
        ready.ledger_outside, public, prof)
    del fwritten, written
    assert_schema(assertions, spec.public)
    for doc in record.get("documents", []):
        if sha256_file(out_dir / doc["path"]) != doc["sha256"]:
            raise ReleaseError(f"{doc['path']} is not the document the "
                               "record names")

    order = list(record["assertions"])
    if set(order) != set(assertions):
        raise ReleaseError("the record's configs are not the build's")
    for config in order:
        for at, block in record["assertions"][config].items():
            fresh = assertions[config].get(at, {})
            drift = sorted(k for k, v in block.items() if fresh.get(k) != v)
            if drift:
                raise ReleaseError(f"{config} {at}: the recorded "
                                   f"{', '.join(drift)} do not re-derive")
    files = []
    for f in record["files"]:
        path = out_dir / f["path"]
        parquet = pq.ParquetFile(path)
        meta = parquet.metadata
        got = {"rows": meta.num_rows,
               "columns": list(parquet.schema_arrow.names),
               "row_group_rows": first_group_rows(path),
               "bytes": path.stat().st_size}
        sizes = parquet_sizes(path)
        if got != {k: f[k] for k in got} or any(
                f.get(k, v) != v for k, v in sizes.items()):
            raise ReleaseError(f"{f['path']}: the recorded rows, columns, "
                               "row groups, bytes, or sizes do not "
                               "re-derive")
        files.append({**f, **sizes})
    # the rows by config re-derive from the files (C-080 line 2, F1)
    if record.get("rows_by_config") != {f["config"]: f["rows"] for f in files}:
        raise ReleaseError("the recorded rows_by_config do not re-derive from "
                           "the files")

    rewritten = dict(record)
    rewritten["files"] = files
    rewritten["bounds"] = bounds()
    rewritten["assertions"] = {config: assertions[config]
                               for config in order}
    rewritten["record_rewritten_on"] = today or date.today().isoformat()
    for f in record["files"]:
        if sha256_file(out_dir / f["path"]) != hashes[f["path"]]:
            raise ReleaseError(f"{f['path']} changed while its record was "
                               "rewritten")
    record_out.write_text(json.dumps(rewritten, indent=2) + "\n",
                          encoding="utf-8")
    log(f"[release] {spec.version}: record {_rel(record_out)} rewritten; "
        "no file written")
    return rewritten


def documents_only(spec: VersionSpec, out_dir: Path | None = None,
                   record_out: Path | None = None, *, root: Path | None = None,
                   today: str | None = None, log=print) -> dict:
    """Carry a corrected document (NOTICES.md) into a version already built,
    and change nothing else (D-018 line 2). Every data file the record names
    must still hash to the record's sha256, or nothing is written; then each
    document is copied again from its committed source, and the record is
    rewritten with the documents' new bytes and sha256 and the date of the
    rewrite. The data files, their counts, and their assertions stay as
    recorded."""
    out_dir = out_dir or spec.out_dir
    record_out = record_out or spec.record_out
    root = root or REPO
    if not record_out.exists():
        raise ReleaseError(f"{_rel(record_out)} is absent; --documents-only "
                           "rewrites the record of a version already built")
    record = json.loads(record_out.read_text(encoding="utf-8"))
    for f in record["files"]:
        if sha256_file(out_dir / f["path"]) != f["sha256"]:
            raise ReleaseError(f"{f['path']} is not the file the record "
                               "names; --documents-only changes no data file")
    documents = []
    for doc in record.get("documents", []):
        target = out_dir / doc["path"]
        shutil.copyfile(root / doc["source"], target)
        documents.append({**doc, "bytes": target.stat().st_size,
                          "sha256": sha256_file(target)})
    rewritten = dict(record)
    rewritten["documents"] = documents
    rewritten["documents_rewritten_on"] = today or date.today().isoformat()
    record_out.write_text(json.dumps(rewritten, indent=2) + "\n",
                          encoding="utf-8")
    log(f"[release] {spec.version}: {len(documents)} document(s) carried "
        f"again; record {_rel(record_out)} rewritten; no data file written")
    return rewritten


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", type=Path, default=None,
                    help="build into this directory (a reproduction); the "
                         "record is written beside the files")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_true",
                      help="rebuild over an existing output directory")
    mode.add_argument("--documents-only", action="store_true",
                      help="carry corrected documents (NOTICES.md) into a "
                           "version already built and rewrite their hashes "
                           "in its record; no data file is written (D-018)")
    mode.add_argument("--record-only", action="store_true",
                      help="rewrite the record of files already built: "
                           "each file's sha256 verified against the "
                           "record, the assertions re-run, no file written "
                           "(C-079 line 1, F4)")
    args = ap.parse_args(argv)
    try:
        spec = resolve(args.version)
        if args.documents_only:
            if args.out is not None:
                documents_only(spec, args.out, args.out / spec.record_out.name)
            else:
                documents_only(spec)
        elif args.record_only:
            if args.out is not None:
                record_only(spec, args.out, args.out / spec.record_out.name)
            else:
                record_only(spec)
        elif args.out is not None:
            build(spec, args.out, args.out / spec.record_out.name,
                  replace=args.replace)
        else:
            build(spec, replace=args.replace)
    except ReleaseError as exc:
        print(f"[release] refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
