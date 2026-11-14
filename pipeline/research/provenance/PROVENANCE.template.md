# The intake provenance of universe v2

**2026-09-17**, rebuilt November 13, 2026 · decision C-064 · built by
[`build_provenance.py`](build_provenance.py) over the C-016 pin, the
evidence matrix (C-010), the feature layer (C-011), and the EOL's two
dictionaries at revision `08ae92b8`, the revision the pin reads
([`repin.py`](../universe/repin.py)), pinned in
[`eol_dictionaries_manifest.json`](eol_dictionaries_manifest.json). This
file is rendered from [`PROVENANCE.template.md`](PROVENANCE.template.md):
every figure below is a row of [`provenance.json`](provenance.json), and
`check_provenance` in `research/verify_doc_numbers.py` re-renders the
file and re-derives the rows from the layer. The layer itself,
`data/universe_v2_provenance.parquet`, holds every row of the pin, the
{{pin.restricted_rows}} restricted rows included, and stays local and
gitignored under the license split. No candidate word is printed here.

The question this report answers is the maintainer's of 2026-09-16: for every
candidate in universe v2, where was it obtained, derived, or generated.
Nothing here says whether a candidate is valid. Validity is the
in-the-wild programme's to decide under its own definition (C-021);
universe membership, the strata, and the pin's bytes are untouched.

## 1. The residual, stated first

**{{measured.rows_by_class.neither}} of the {{measured.rows}} candidates
({{percentages.residual_of_the_universe}}) have no recorded intake
channel and no measured containment.** For these the record this package
can reach does not say how the string entered the EOL's pool, and none of
the thirteen panel sets and neither corpus the CEOL measures holds the
string. {{measured.residual.by_layer.eol_invalid}} of them are in the
EOL's invalid layer ({{percentages.residual_of_the_invalid_layer}} of
that layer) and {{measured.residual.by_layer.eol_valid}} are in its valid
layer. {{measured.residual.by_eol_record.invalid-dict}} have an entry in
the invalid dictionary and {{measured.residual.by_eol_record.valid-dict}}
in the valid one, each entry with no discovery-log label and no
`source`; {{measured.residual.by_eol_record.none}} have no dictionary
entry. {{measured.residual.a_wiktionary_title_in_some_language}} of the
residual rows are page titles in some language's Wiktionary, which is a
screen and not containment (C-010), so it is recorded and does not move a
row out of the residual.

Four limits on how far that statement reaches:

- **The residual depends on one reading of this seat's.**
  {{coverage.by_layer.eol_invalid.with_no_entry}} invalid strings have no
  entry in either dictionary. The EOL's own correction ledgers account
  for every one of them, and
  {{coverage.no_entry_strings_accounted_for.named_by_the_two_demotion_ledgers}}
  are generated forms the EOL demoted from its valid list on 2026-08-14.
  This layer labels those as generated from the ledgers (§7). Without
  that reading they would carry no recorded channel, and the residual
  would be {{reconciliations.residual_without_the_ledger_reading}}.
- **A recorded channel is not an attestation.**
  {{measured.rows_by_class.channel_only}} rows
  ({{percentages.channel_only_of_the_universe}}) have a recorded channel
  and no measured containment, and
  {{measured.generated.by_class.channel_only}} of them are generated
  strings whose only record is the engine that made them.
- **No recorded channel is not no origin.**
  {{measured.no_recorded_channel.rows}} inherited strings carry
  `eol:phase1-unrecorded`. {{measured.no_recorded_channel.listed_by_a_panel_set}}
  of them are listed by a panel set; {{measured.no_recorded_channel.a_gb_type}}
  are Google Books 1-gram types in the CEOL's re-stream
  ({{measured.no_recorded_channel.not_listed_and_a_gb_type}} of those
  listed by no panel set);
  {{measured.no_recorded_channel.not_listed_not_gb_and_wordfreq_scored}}
  more are scored by wordfreq alone; the remaining
  {{measured.no_recorded_channel.with_no_containment}} are the residual.
  The maintainer's statement in §6 is consistent with these counts and is not
  proved by them: containment shows that a corpus holds the string, not
  that the EOL took the string from it.
- **The label vocabulary is narrower than the EOL's own account.** The
  EOL's final report names SCOWL, CMU Dict, and Moby among its Phase-1
  sources; no discovery-log label in either dictionary names any of the
  three. The labels `opensource` and `libreoffice` occur in the
  dictionaries and are not in the report's tier table. The layer records
  the labels the dictionaries carry and infers nothing from the report.
- **At the pinned revision the EOL publishes less of its intake record.**
  An entry of its valid dictionary carries no discovery log, and names
  its intake only where the EOL publishes it (`source`, for 5 intakes);
  a row of the valid list whose entry names none carries `eol:list`, the
  list itself. Its invalid dictionary's discovery logs no longer carry
  the labels the CEOL's public versions withhold (`collins`,
  `coca_frequency`, `linux`, `nltk`), so a row whose only labels those
  were has no recorded channel.

## 2. Two senses of provenance, kept apart

**The intake channel** is the route by which a string entered the
candidate pool. For the {{pin.inherited_strings}} strings inherited from
the EOL it is read from the EOL's dictionaries: the `candidate_source`
list and the `source` field (a row of the valid list whose entry has
neither carries `eol:list`). The EOL ruled that list "a discovery log"
that "is never evidence" (its D-003: the field "records where a
candidate was first **seen**, not which sources **contain** it"), and
C-008 repudiated it as an attestation matrix. This layer reads it as
exactly what it is, a first-seen record of the channel, under a name
that says so, and never as a list of the sources that contain a string.
For the CEOL's own three layers the channel is the pin's `sources`
column, which C-008 made a containment list at intake.

**The measured containment** is what the evidence matrix and the feature
layer already hold for every single-token candidate: its listing in each
of the thirteen panel sets, and its presence in the CEOL's Google Books
re-stream and in wordfreq. A spaced candidate has two applicable sets
(C-016) and is not measured by the corpus layers, so its corpus columns
are null.

The two senses disagree wherever they can be set side by side, which is
why they are separate columns. Over the inherited strings the label
`google_ngrams` sits on
{{discovery_log_vs_containment.inherited_rows_labeled_google_ngrams}}
rows, every one of them a Google Books 1-gram type in the CEOL's
re-stream ({{discovery_log_vs_containment.of_them_not_a_gb_type}} are
not), while {{discovery_log_vs_containment.inherited_gb_types_without_the_label}}
further inherited strings are Google Books types and lack the label.

## 3. Every row, by layer, kind, and class

A row's **class** has two halves. It has a channel when
`intake_channels` holds any label other than `eol:phase1-unrecorded`. It
has containment when at least one of the thirteen panel sets lists it,
or it is a Google Books 1-gram type, or wordfreq scores it. Every row
has exactly one class.

{{table:class_by_layer}}

`channel_and_containment` is {{percentages.channel_and_containment_of_the_universe}}
of the universe and `containment_only` {{percentages.containment_only_of_the_universe}}.
The two classes without containment sum to
{{reconciliations.channel_only_plus_neither}}, which is the committed SR2
reading-B row of the feature layer ({{reconciliations.sr2_reading_b_rows}}
single-token candidates listed by no panel set and present in neither
corpus): this layer partitions that row and does not change it.

A row's **kind** is `obtained` (an inherited string taken in through a
channel), `derived` (a row of the CEOL's three layers, which the CEOL
derived from pinned sources under its grammar), or `generated` (made by
an engine, §7). A generated row is never derived.

{{table:kind_by_layer}}

## 4. The pinned inputs, and what they cover

| Input | Bytes | sha256 |
|---|---:|---|
| `merged_valid_dict.json` at `08ae92b8` (the local pinned file) | {{coverage.valid_dictionary_bytes}} | `{{inputs.merged_valid_dict_sha256}}` |
| `merged_invalid_dict.json` at `08ae92b8` (streamed once, never stored) | {{coverage.invalid_dictionary_bytes}} | `{{inputs.merged_invalid_dict_sha256}}` |

Each dictionary's hash equals the hub's LFS object id for the file at
the revision; the invalid dictionary's was computed over the single
stream. The manifest also records the hub's Xet content hash of the
invalid dictionary, which is not a sha256 of its bytes. The stream
parsed {{coverage.invalid_dictionary_entries}} entries over
{{coverage.invalid_dictionary_lines}} lines under the one-entry-per-line
layout, with a hard error armed for any line outside it; none occurred.

| Coverage | Valid dictionary | Invalid dictionary |
|---|---:|---:|
| Entries | {{coverage.valid_dictionary_entries}} | {{coverage.invalid_dictionary_entries}} |
| Entries with a non-empty channel list | {{coverage.valid_entries_with_a_non_empty_channel_list}} | {{coverage.invalid_entries_with_a_non_empty_channel_list}} |
| Entries with a `source` value | {{coverage.valid_entries_with_a_source_value}} | {{coverage.invalid_entries_with_a_source_value}} |
| Entries with neither | {{coverage.valid_entries_with_neither}} | {{coverage.invalid_entries_with_neither}} |
| Strings of its own layer | {{coverage.by_layer.eol_valid.rows}} | {{coverage.by_layer.eol_invalid.rows}} |
| — with an entry in it | {{coverage.by_layer.eol_valid.with_an_entry_in_its_own_dictionary}} | {{coverage.by_layer.eol_invalid.with_an_entry_in_its_own_dictionary}} |
| — with no entry in either dictionary | {{coverage.by_layer.eol_valid.with_no_entry}} | {{coverage.by_layer.eol_invalid.with_no_entry}} |

{{coverage.invalid_entries_keyed_by_a_valid_string}} entries of the
invalid dictionary are keyed by a string of the valid list; a row is
looked up in its own layer's dictionary first, so those rows read their
valid entry. {{coverage.invalid_entries_outside_the_universe}} entries of
the invalid dictionary and {{coverage.valid_entries_outside_the_universe}}
of the valid one fall outside the inherited strings.

The {{coverage.no_entry_strings_accounted_for.inherited_strings_with_no_entry}}
invalid strings with no entry are accounted for in full by four
correction ledgers of the EOL repository, read and never written, each
pinned by sha256 in the manifest:
{{coverage.no_entry_strings_accounted_for.named_by_the_two_demotion_ledgers}}
by its two demotion ledgers (every row an action `demote_to_invalid`
whose reason opens with the word "synthetic"),
{{coverage.no_entry_strings_accounted_for.named_by_the_single_letter_ledger}}
by its single-letter ledger,
{{coverage.no_entry_strings_accounted_for.named_by_the_form_rule_ledger_as_added_candidates}}
by its form-rule ledger as added candidates, and
{{coverage.no_entry_strings_accounted_for.named_by_none_of_the_four}} by
none. The first group is generated (§7). The closed vocabulary holds no
label for a ledger action, so the other two groups carry
`eol:phase1-unrecorded`. Of the demotion ledgers' rows,
{{coverage.no_entry_strings_accounted_for.demotion_ledger_words_that_do_have_an_entry}}
have an entry, in the valid dictionary: the EOL took those forms back
into its valid list, and that entry is their record.

## 5. The channel table

The controlled vocabulary is the one C-064 ruling 8 adopted from the
package's agenda. For an inherited row a label is a discovery-log label
with its tier suffix removed, or the label of the entry's `source`
value; one row can carry several. At the pinned revision the invalid
dictionary carries seven discovery-log labels and the valid dictionary
none.

{{table:eol_channels}}

For the CEOL's own layers the label is the namespace of the layer and
the name the pin's `sources` column carries (`census:` for the C1
exceptions, `audit:` for the C4 additions, `spaced:` for the C-015
spaced candidates, `ledger:d025` for the seeds re-ruled from the EOL's
D-025 deletions). The audit's own `eol:` prefix on the five EOL-derived
detector sets is removed, so that the `eol:` namespace holds the EOL's
intake record and nothing else.

{{table:ceol_channels}}

The layer holds {{measured.distinct_channel_combinations}} distinct
combinations of labels. The Phase-1 tier is the suffix the labels of an
entry share (`_valid` or `_unlikely`; no entry mixes the two), and the
record column names the dictionary that holds the row's entry:

{{table:tier_and_record}}

{{percentages.inherited_with_a_recorded_channel}} of the inherited
strings have a recorded channel.

## 6. The accounts of others, quoted as theirs

**The EOL's own account** (its final report and its commit history, read
and not re-derived here). Phase 1 built a foundation of
{{quoted.eol_phase1_entries}} unique entries from tiered sources — Tier 1
Collins, WordNet, Wiktionary; Tier 2 SCOWL, Google Ngrams; Tier 3 NLTK,
CMU Dict, ENABLE; Tier 4 Moby, Wikipedia titles — of which
{{quoted.eol_phase1_provisionally_valid}} were "provisionally valid based
on source" and {{quoted.eol_phase1_raw_candidates}} "requiring further
verification". It calls Wiktionary "The largest single contributor" and
describes Google Books Ngrams as "Frequency-validated data used to
prioritize candidates". Phase 2d: "three synthetic engines generated
candidates" — inflection, chemical, and scientific — and
"{{quoted.eol_phase2d_generated}} synthetic candidates generated", of
which {{quoted.eol_phase2d_validated}} were validated. The EOL's later
commits record that it demoted {{quoted.eol_demoted_comparatives}}
comparatives and superlatives "built by blind affixation", found
{{quoted.eol_forms_with_no_stem_in_the_list}} surviving forms with no
stem in its list, and then demoted the
{{quoted.eol_demoted_non_plural_forms}} non-plural forms and kept the
{{quoted.eol_plurals_kept}} plurals. Its decision log states: "The
candidate universe was built from scanned text, and so was Google
Books."

**The maintainer's statements** (2026-09-16; C-064 ruling 6). The EOL universe
relied largely on the Google Books 1-gram types, taken from the primary
Google Books Ngram source. A non-synthetic EOL string without a specific
recorded source came from the Google Books 1-gram types unless it seems
likely to have come from the Tier-3 or Tier-4 channels. The Google
Trillion Word Corpus was considered and, to the maintainer's recollection,
not used; no channel is named for it, and none of the dictionaries'
labels refers to it. These are recorded as the maintainer's statements; the
dictionaries' own labels decide the channel a row carries.

## 7. The generated strings

**Every generated string stays a candidate** (C-064 ruling 3; C-003,
C-004) and carries `intake_kind = generated`, the channel
`eol:synthetic-engine`, its category as recorded, and an engine inferred
from its form. There are {{measured.generated.rows}}
({{percentages.generated_of_the_universe}} of the universe). The EOL
report's own count of generated candidates is
{{quoted.eol_phase2d_generated}}; the difference is the
{{ledger_cross_check.ledger_rows_taken_back_into_the_valid_list}}
demoted forms the EOL later took back into its valid list, whose entries
there name another intake:

| Where the record of generation lies | Rows |
|---|---:|
| An entry of the valid dictionary with `source: synthetic_generation` | {{reconciliations.generated_in_the_valid_dictionary}} |
| An entry of the invalid dictionary with `source: synthetic_generation` | {{reconciliations.generated_in_the_invalid_dictionary}} |
| No dictionary entry; a row of the EOL's two demotion ledgers | {{reconciliations.generated_named_by_the_demotion_ledgers_only}} |
| **All generated rows** | {{reconciliations.generated_in_all}} |

{{percentages.generated_with_no_containment}} of them have no measured
containment. No generated row carries a discovery-log label
({{measured.generated.with_a_discovery_log_label_too}}).

**The method is an inference, recorded with that status.** The EOL's
generator script is lost, the EOL repository never held it, and the
entry field that would have named the method (`generation_method`) is
null or absent on every entry of both dictionaries. What is recorded as the method
is an inference of September 16, 2026 from the surviving forms
and the EOL's own history, confirmed by the
maintainer without amendment (C-064 ruling 11): blind affixation over the
then-valid list — plurals, past tenses, gerunds, agent nouns,
comparatives and superlatives, and prefixed forms, with no
part-of-speech filter; chemical substituent variation and short
root-infix-suffix chains; medical and scientific prefixing; Greek
plurals; and a domain label per base word. **The tools are the maintainer's
recollection**, not a record: NLTK for certain, lemminflect and spaCy
with high confidence, the assignment of tools to engines not recalled;
the chemical engine was list-driven substitution over a hand-written
list of substituents and roots, with no formula-to-name tool.

**The engine per row is inferred from the form alone** by the rules of
[`synthetic_engine.py`](synthetic_engine.py), first match, against the
pinned valid list as the base set: a plural or other inflection of a
word on the EOL's valid list; a substituent prefix or a root-infix-suffix chain; an organ,
system, or scientific combining form; a general prefix; a Greek plural;
otherwise unresolved. The value is recorded in the column
`eol_synthetic_engine_inferred`. It is never the generator's own label,
which does not exist.

{{table:generated_by_engine}}

{{percentages.generated_inferred_as_affixation}} of the generated rows
read as affixation. By rule:

{{table:generated_by_rule}}

One check of the inference against a record it did not use: each row of
the EOL's two demotion ledgers states the form the EOL took the string
to be. On {{ledger_cross_check.agreeing_rows}} of the
{{ledger_cross_check.ledger_rows}} ledger rows that are generated rows
the inferred rule agrees with that statement; the rules read the pinned
valid list as their base set, so the inference moves with the pin. The comparison is made at the level of the three
forms the ledgers' reasons open with (a comparative, a plural, a verb
form): the ledgers' finer wording — the plural of a gerund, the plural
of an agent noun — is not compared, and the `gerund-plural` and
`agent-plural` rules match no row of the layer, because the plural rule
matches first (C-065 ruling 9).

{{table:ledger_cross_check}}

The category is recorded as found. At the pinned revision the valid
dictionary records none. In the invalid dictionary most synthetic entries carry
`Nonsense` or a similar value, which reads as the judgment of the EOL's
validation step and not as a label of the generator; for a ledger-named
row the category is the one the ledger carries.

{{table:generated_by_category}}

A `generated` slice for the study is a later proposal to the maintainer, not
made here.

## 8. Measured containment, by layer

{{table:containment_by_layer}}

Every spaced candidate is listed by WordNet, by Wiktionary, or by both,
and the corpus layers do not measure spaced terms (C-016).

## 9. Reproduction

```
python3 -m research.universe.repin
python3 -m research.universe_v2.build_universe_v2
python3 -m research.provenance.extract_eol_intake
python3 -m research.provenance.build_eol_dictionaries_manifest
python3 -m research.provenance.build_provenance
python3 -m research.provenance.build_provenance --render
```

The first command streams the invalid dictionary again, by the manifest's
URL, and stops if its hash differs. Inputs and output, by sha256:

| File | sha256 |
|---|---|
| `data/universe_v2.parquet` (the C-016 pin, read only) | `{{inputs.universe_v2_parquet_sha256}}` |
| `data/evidence.parquet` | `{{inputs.evidence_parquet_sha256}}` |
| `data/features.parquet` | `{{inputs.features_parquet_sha256}}` |
| `.cache/provenance/eol_valid_intake.parquet` | `{{inputs.eol_valid_intake_parquet_sha256}}` |
| `.cache/provenance/eol_invalid_intake.parquet` | `{{inputs.eol_invalid_intake_parquet_sha256}}` |
| `eol_dictionaries_manifest.json` | `{{inputs.eol_dictionaries_manifest_sha256}}` |
| `data/universe_v2_provenance.parquet` (the layer) | `{{artifact.sha256}}` |

## 10. What this layer does not do

It validates nothing and re-labels nothing. It adds and removes no
candidate, changes no stratum, and does not touch
`data/universe_v2.parquet`, whose two filter-equivalence proofs stand
over the same bytes. It changes nothing in the EOL: the EOL's files were
read, and a later EOL-side field, if the maintainer adopts one, is derived
from this table under the EOL's own governance (C-064 ruling 4). It
reads the discovery log as a record of the channel and never as
attestation.
