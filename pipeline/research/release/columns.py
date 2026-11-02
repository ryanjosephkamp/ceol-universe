"""The columns of the CEOL Universe release (C-078 line 4;
research/release/PACKAGE_UR1.md §2.2): their order, their Arrow types,
their meanings, and their null semantics, stated once.

`build_release.py` takes the column lists and the nullable sets from here;
the card (`CARD.template.md` through `release_calcs.py`) and the profile
page (`profile/build_profile_page.py`) render their column tables from
`TABLES`, so the card quotes the page's tables and both quote this file.
No figure is stated here: counts belong to the calculator.
"""

from __future__ import annotations

#: A column: its name, its Arrow type, what it holds, what a null means.
#: A group entry names several columns that share a meaning.
Column = tuple[str, str, str, str]

KEY: tuple[Column, ...] = (
    ("id", "string",
     "the first 16 hexadecimal digits of the sha256 of the word's UTF-8 "
     "bytes; a function of the string alone, so the same string carries the "
     "same id in every version",
     "never null"),
    ("word", "string",
     "the candidate string, the output of the C-001 grammar: lower case, "
     "the 50-character charset, spaces single and interior; the join key "
     "of every layer",
     "never null"),
)

PIN: tuple[Column, ...] = (
    ("eol", "bool",
     "in the EOL's valid list at the pinned revision c1139698: a historical "
     "fact at a pin, carried as a covariate, never a CEOL verdict",
     "never null"),
    ("eol_universe", "bool",
     "in the EOL's pinned candidate universe (its valid or its invalid "
     "list); false for the CEOL's own 3 layers",
     "never null"),
    ("classes", "string",
     "the grammar's non-exclusive class flags joined by ';' (hyphenated, "
     "accented, diaeresis, ligature, apostrophe-form, contraction, s-final, "
     "spaced); the empty string on a plain-letter string",
     "never null"),
    ("sources", "string",
     "C-008 provenance at intake: for the CEOL's own layers the sources "
     "whose derived sets contain the string, joined by ';'; for the strings "
     "inherited from the EOL the dataset-level tag eol_universe@c1139698 "
     "(their per-source listedness is the evidence columns')",
     "never null"),
    ("intake_date", "string",
     "the date the row entered a CEOL artifact: 2026-08-17 the EOL "
     "universe at the pinned revision, 2026-08-20 the C1 exceptions and "
     "the C-009 audited additions, 2026-08-26 the C-016 spaced candidates",
     "never null"),
    ("c4_addition", "bool",
     "a row of the audited additions of the C-009 pin",
     "never null"),
    ("is_restricted", "bool",
     "attested only by NWL2023 or CSW21 (C-009); false on every row of "
     "this dataset, because those rows never ship",
     "never null"),
    ("token_count", "int32",
     "the number of space-separated tokens (C-015)",
     "never null"),
    ("c015_addition", "bool",
     "a row of the spaced candidates admitted at C-016",
     "never null"),
    ("wn_instance", "bool",
     "WordNet instance-synset membership, a properness signal recorded and "
     "never filtered on (C-016)",
     "null unless WordNet attests the row; measured on the spaced layer "
     "only; null means not measured, never false"),
    ("wn_capitalized", "bool",
     "WordNet data-file capitalization, a properness signal",
     "null unless WordNet attests the row; measured on the spaced layer "
     "only"),
    ("wk_proper_noun", "bool",
     "a Wiktionary Proper-noun heading, a properness signal",
     "null unless Wiktionary attests the row; measured on the spaced layer "
     "only"),
    ("wk_flags", "string",
     "Wiktionary's category flags joined by ';' (idiomatic, phrasal-verb, "
     "phrasebook, proverb); may be the empty string",
     "null unless Wiktionary attests the row; measured on the spaced layer "
     "only"),
)

RELEASE: tuple[Column, ...] = (
    ("class_explicit", "string",
     "the pin's classes with the value 'plain' in place of the empty "
     "string; otherwise the flags unchanged",
     "never null"),
    ("panel_sets", "string",
     "the panel sets that list the row, joined by ';' in the order wordnet, "
     "wiktionary_english, web2, web2a, hunspell_en_US, hunspell_en_GB, "
     "hunspell_en_CA, hunspell_en_AU, enable1, sowpods_legacy, nwl2023, "
     "csw21, scowl; on a single-token row a binary set lists the row where "
     "its evidence column is 1 and SCOWL where scowl_tier is above 0; on a "
     "spaced row the sets are the pin's sources; the empty string where "
     "none lists the row",
     "never null"),
    ("variety_gb_not_us", "bool",
     "true where hunspell_en_GB is 1 and hunspell_en_US is 0: a proxy for "
     "a variety difference between the 2 dictionaries, never a variety "
     "label",
     "null where either hunspell column is -1 or null"),
    ("variety_us_not_gb", "bool",
     "true where hunspell_en_US is 1 and hunspell_en_GB is 0: the reverse "
     "proxy",
     "null where either hunspell column is -1 or null"),
)

PROVENANCE: tuple[Column, ...] = (
    ("intake_layer", "string",
     "the layer the row entered by: eol_valid, eol_invalid, c1_exceptions, "
     "c4_additions, spaced_c015",
     "never null"),
    ("intake_kind", "string",
     "obtained (an inherited string taken in through a channel), derived "
     "(a row of a CEOL layer derived from pinned sources), or generated "
     "(made by the EOL's lost synthetic engine)",
     "never null"),
    ("intake_channels", "string",
     "the first-seen channel labels joined by ';': the EOL's discovery log "
     "with its tiers removed, and the CEOL layers' own namespaces census:, "
     "audit:, spaced:, ledger:; a record of where a string was first seen, "
     "never an attestation (C-064)",
     "never null"),
    ("eol_phase1_tier", "string",
     "the tier suffix the EOL's labels on the row share: valid, unlikely, "
     "or none (C-064 declares mixed for labels that disagree)",
     "never null"),
    ("eol_record", "string",
     "which EOL dictionary holds the row's entry: valid-dict, invalid-dict, "
     "none",
     "never null"),
    ("eol_synthetic_category", "string",
     "the category recorded on a generated string (a domain label, or the "
     "EOL validation step's judgment)",
     "null on every row that is not generated"),
    ("eol_synthetic_engine_inferred", "string",
     "the engine and rule inferred from a generated string's form "
     "(affixation, chemical-variation, greek-plural, "
     "medical-scientific-prefixing, unresolved); an inference, so named",
     "null on every row that is not generated"),
    ("panel_count", "int16",
     "the number of the 13 panel sets that list the row (the number "
     "of names in panel_sets, asserted equal on every row)",
     "never null"),
    ("gb_type", "bool",
     "the string is a Google Books English 1-gram type in the CEOL "
     "re-stream (C-011)",
     "null on spaced rows, which the corpora do not measure"),
    ("wordfreq_scored", "bool",
     "wordfreq 3.1.1 scores the string",
     "null on spaced rows, which the corpora do not measure"),
    ("wikt_title_any", "bool",
     "some language's Wiktionary has a page titled with the string: a "
     "screen, not containment (C-010)",
     "null on spaced rows"),
    ("provenance_class", "string",
     "exactly 1 of channel_and_containment, channel_only, "
     "containment_only, neither: whether the row has a recorded intake "
     "channel and whether a panel set or a corpus contains it",
     "never null"),
)

#: The column a public version adds after the others (v2.1 on): which rows a model decided or an engine generated.
MODEL: tuple[Column, ...] = (
    ("model_or_engine", "string",
     "engine_generated on a row the EOL's synthetic engine made (intake_kind "
     "generated); on a row of the EOL's valid list, model_pipeline where the "
     "EOL listed it through its verification pipeline, which used a language "
     "model, and model_alone where a language model's verdict is its only "
     "basis; none on every other row. A record of how the EOL decided, never "
     "a verdict of this dataset's; the EOL's invalid list is not marked",
     "never null"),
)

#: The 12 binary detectors of the evidence matrix, in its order.
DETECTORS: tuple[str, ...] = (
    "wordnet", "wiktionary_english", "web2", "web2a", "hunspell_en_US",
    "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU", "enable1",
    "sowpods_legacy", "nwl2023", "csw21")

#: The 13 panel sets, in panel_sets' canonical order.
PANEL_SETS: tuple[str, ...] = DETECTORS + ("scowl",)

_DETECTOR_SOURCES = {
    "wordnet": "WordNet 3.0's lemmas, re-derived under the CEOL grammar",
    "wiktionary_english": "Wiktionary pages with an English section "
                          "(the 2026-08-04 dump)",
    "web2": "Webster's Second International (1934), the system word list",
    "web2a": "web2's supplemental list of hyphenated terms and phrases",
    "hunspell_en_US": "the LibreOffice hunspell en_US dictionary, expanded",
    "hunspell_en_GB": "the LibreOffice hunspell en_GB dictionary, expanded",
    "hunspell_en_CA": "the LibreOffice hunspell en_CA dictionary, expanded",
    "hunspell_en_AU": "the LibreOffice hunspell en_AU dictionary, expanded",
    "enable1": "the ENABLE word list",
    "sowpods_legacy": "the legacy SOWPODS list",
    "nwl2023": "NASPA Word List 2023 (a restricted source, C-009)",
    "csw21": "Collins Scrabble Words 2021 (a restricted source, C-009)",
}

EVIDENCE: tuple[Column, ...] = tuple(
    (name, "int8",
     f"listed by {_DETECTOR_SOURCES[name]}: 1 listed, 0 not listed, -1 "
     f"structurally blind to the row's class (C-010)",
     "null on spaced rows, which the single-token sets were not measured "
     "over (C-016)")
    for name in DETECTORS) + (
    ("scowl_tier", "int16",
     "the SCOWL size tier (10 to 95) of the smallest SCOWL list holding the "
     "string; 0 not listed; -1 not applicable to the row's class",
     "null on spaced rows"),
    ("wikt_title_screen", "int8",
     "1 where some language's Wiktionary has a page titled with the "
     "string, else 0: a screen, never a detector (C-010)",
     "null on spaced rows"),
)

FEATURES: tuple[Column, ...] = (
    ("orthotactic_logp_total", "float",
     "the log-probability of the string under the C-011 character model "
     "(an interpolated order-4 model over the 50-symbol alphabet, trained "
     "on the strong-positive pool)",
     "never null"),
    ("orthotactic_logp_per_char", "float",
     "the same log-probability per character",
     "never null"),
    ("ocr_neighbor_hits", "int8",
     "the number of the string's neighbours under the 6 typed OCR "
     "confusions that the base reference (WordNet and web2) lists, capped "
     "at 127",
     "never null"),
    ("ocr_neighbor_freq_ratio", "float",
     "the largest log10 ratio of a neighbour's Google Books match count to "
     "the string's (each plus 1)",
     "NaN where the string has no neighbour"),
    ("ocr_apostrophe_ratio", "float",
     "on a plain string, the largest log10 frequency ratio of an "
     "apostrophe restoration a class-capable reference lists (an admitted "
     "family)",
     "NaN where no restoration is listed or the string is not plain"),
    ("ocr_ligature_ratio", "float",
     "on a plain string, the same for a ligature restoration (admitted)",
     "NaN where no restoration is listed or the string is not plain"),
    ("ocr_hyphen_drop_ratio", "float",
     "on a plain string, the same for a hyphen restoration (admitted)",
     "NaN where no restoration is listed or the string is not plain"),
    ("ocr_strip_ratio", "float",
     "on a plain string, the same for an accent restoration (a family the "
     "C-011 gate rejected; the column exists, flagged inadmissible)",
     "NaN where no restoration is listed or the string is not plain"),
    ("ocr_hyphen_junction_ratio", "float",
     "on a hyphenated string, the ratio for its junction concatenation (a "
     "family the gate rejected; flagged inadmissible)",
     "NaN where none is listed or the string is not hyphenated"),
    ("morph_productivity_vn", "float",
     "the realized productivity V/N of the productive suffix the string "
     "parses to on an attested stem",
     "NaN where the string has no such parse"),
    ("morph_has_parse", "bool",
     "whether that parse exists",
     "never null"),
    ("segment_attested_fraction", "float",
     "on a hyphenated string, the fraction of its hyphen-separated "
     "segments the base reference lists",
     "NaN on a string that is not hyphenated"),
    ("gb_year_span", "int16",
     "the years from the first to the last in which the string occurs in "
     "the Google Books English 1-grams (the 2020 release), inclusive",
     "0 where the string is not a 1-gram type"),
    ("gb_span_fill", "float",
     "the share of the span's years in which the string occurs",
     "NaN where the string is not a 1-gram type"),
    ("gb_tokens_per_volume", "float",
     "the total match count over the total volume count",
     "NaN where no volume carries the string"),
    ("gb_volumes_per_year", "float",
     "the total volume count over the years in which the string occurs",
     "NaN where the string is not a 1-gram type"),
    ("gb_log10_match", "float",
     "log10 of the total match count",
     "NaN where the string is not a 1-gram type"),
    ("gb_log10_volume", "float",
     "log10 of the total volume count",
     "NaN where no volume carries the string"),
    ("zipf_log10_rank", "float",
     "log10 of the string's frequency rank among the aggregate's types",
     "NaN where the string is not a 1-gram type"),
    ("zipf_resid", "float",
     "log10 of the match count minus the Zipf-Mandelbrot fit's prediction "
     "at that rank",
     "NaN where the string is not a 1-gram type"),
    ("wordfreq_zipf", "float",
     "the wordfreq 3.1.1 Zipf frequency (English) where wordfreq's list "
     "holds the string",
     "NaN elsewhere, and on every hyphenated string (C-010: wordfreq is "
     "hyphen-blind)"),
)

#: The blocks of the universe config, in order (PACKAGE_UR1.md §2.2).
UNIVERSE_BLOCKS: tuple[tuple[str, tuple[Column, ...]], ...] = (
    ("key", KEY), ("pin", PIN), ("release", RELEASE),
    ("provenance", PROVENANCE), ("evidence", EVIDENCE))

UNIVERSE_COLUMNS: tuple[str, ...] = tuple(
    c[0] for _block, cols in UNIVERSE_BLOCKS for c in cols)
FEATURES_COLUMNS: tuple[str, ...] = tuple(c[0] for c in KEY + FEATURES)

#: The columns of the source layers the release carries unchanged.
PIN_LAYER_COLUMNS: tuple[str, ...] = ("word",) + tuple(c[0] for c in PIN)
PROVENANCE_LAYER_COLUMNS: tuple[str, ...] = ("word",) + tuple(
    c[0] for c in PROVENANCE)
EVIDENCE_LAYER_COLUMNS: tuple[str, ...] = DETECTORS + (
    "scowl_tier", "wikt_title_screen")
FEATURE_LAYER_COLUMNS: tuple[str, ...] = tuple(c[0] for c in FEATURES)

#: Columns allowed to hold a null in the universe config (§2.5); every
#: other column holding a null fails the joins' assertion.
UNIVERSE_NULLABLE: frozenset[str] = frozenset(
    {"wn_instance", "wn_capitalized", "wk_proper_noun", "wk_flags",
     "variety_gb_not_us", "variety_us_not_gb", "eol_synthetic_category",
     "eol_synthetic_engine_inferred", "gb_type", "wordfreq_scored",
     "wikt_title_any"} | set(EVIDENCE_LAYER_COLUMNS))

#: Null only on spaced rows and on every spaced row (AT-UR1-4).
SPACED_NULL: tuple[str, ...] = EVIDENCE_LAYER_COLUMNS + (
    "gb_type", "wordfreq_scored", "wikt_title_any")

#: The tables the card and the profile page render, in order.
TABLES: dict[str, tuple[str, tuple[Column, ...]]] = {
    "key": ("The key", KEY),
    "pin": ("The pin's columns (C-016)", PIN),
    "release": ("The release layer (C-078 line 4)", RELEASE),
    "provenance": ("The intake-provenance layer (C-064)", PROVENANCE),
    "evidence": ("The evidence matrix (C-010)", EVIDENCE),
    "features": ("The feature layer, the features config (C-011)",
                 FEATURES),
    "model": ("Model and engine (v2.1 on)", MODEL),
}


def markdown_table(columns: tuple[Column, ...]) -> list[str]:
    """A column table in Markdown, a line per column."""
    lines = ["| Column | Type | Meaning | Null |", "|---|---|---|---|"]
    for name, kind, meaning, nulls in columns:
        lines.append(f"| `{name}` | {kind} | {meaning} | {nulls} |")
    return lines
