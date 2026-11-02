# The CEOL Universe, version {{version_name}}: an inventory of candidate English strings and the evidence for each

Ryan Kamp

*Technical report. Draft of {{built_on}}. Every figure in it is printed by
`pipeline/research/release/report/paper.py` from committed files.*

| | |
|---|---|
| Dataset | `{{dataset}}` on the Hugging Face hub, version {{version_name}} |
| Rows | {{rows_universe}} candidates, 1 per string, in {{config_count}} configs |
| Built | {{built_on}}, by `pipeline/research/release/build_release.py` at commit `{{code_commit}}` |
| License | the data CC BY-SA 4.0; this report CC BY 4.0 |
| Identifier | a DOI, minted at the release |
| Code and records | {{code_repository}} |
| Contact | {{contact_address}}, for requests to withhold, correct, or restore a source or a row |
| Documentation | the dataset card (the dataset's `README.md`), the data dictionary, and `NOTICES.md` |

## Abstract

The CEOL Universe is a public inventory of {{rows_universe}} candidate English strings. Each row records
which of {{published_set_count}} published word lists list the string, which lists cannot hold strings of
its spelling class, whether 2 corpora contain it, and how it entered the pool. No row says that a string is
a word. Of the {{rows_single}} single-token rows, {{rows_listed}} ({{rows_listed_pct}}) are listed by at
least 1 list and {{tier_corpus}} ({{tier_corpus_pct}}) rest on a corpus alone. Most listed rows are listed
by 1 family: {{alone_wiktionary_pct_of_listed}} of them by Wiktionary and by no other family. The inventory is a frame from which a reader derives a word list under a definition they
state.

## 1. Introduction

Word lists disagree. A spell-checker's dictionary, a tournament's word list, a lexical database, and a
corpus's vocabulary each draw the line around English somewhere else, and none is wrong by its own rule. A
study that needs to know whether a string "exists" usually builds its own check against 1 reference,
chosen for the occasion and not recorded with the result. The checks are hard to compare and hard to
repeat.

The CEOL Universe takes the other approach. It keeps every candidate string its sources gave, under 1
executable spelling grammar, and records each source's answer beside the string, dated by the source's
pinned version. A reader who wants a word list states a definition (for example, "listed by 2 or more
independent families, single tokens only, no string a language model decided") and obtains a list, a
count, and the code that reproduces both. The project's site turns that into an interface: a reader picks
criteria, sees the count over all rows at once, and copies the code.

This report describes version {{version_name}}, the first public version. Its contributions are:

- **The inventory:** {{rows_universe}} rows, each a candidate string with an identifier that depends on the
  string alone, so the same string has the same identifier in every version.
- **The evidence semantics:** a listing is 1 (listed), 0 (not listed), -1 (the list cannot hold strings of
  this class), or null (not measured). No figure in this report counts -1 or null as "not listed".
- **A comparison of the published lists over the same strings** (§7). Because every list is measured
  against every row, the report can state how far the lists contain one another, what each holds alone,
  and how listing depends on frequency, over the rows each list could hold.
- **The record of how each row came in** (§5 and §6), kept apart from the evidence for it.

**What the universe is not.** It is not a dictionary: it has no definitions, senses, or pronunciations. It
does not decide whether a string is a word, and its project text never calls a candidate valid. It is not
a sample of English text, and its counts are counts of strings, not of uses.

## 2. Related resources

{{related_resources}}

## 3. Design

### The candidate

A row of the universe is a **candidate**: a string that passes the spelling grammar, with the record of
where it came from. The grammar (`pipeline/ceol/grammar.py`) normalizes a source entry to lower case,
canonicalizes the typographic apostrophe and the no-break space, and admits it when every character is in
a charset of {{chars_total}} characters: the {{grammar_base}} letters a to z, {{grammar_accented}} accented
letters, {{grammar_ligatures}} ligatures, the hyphen, the apostrophe, and the space. A space separates tokens, so a multiword term is 1 candidate.

The grammar marks each candidate with its spelling classes. A candidate with no class is **plain**; the
classes are `accented`, `apostrophe-form`, `contraction`, `diaeresis`, `hyphenated`, `ligature`, `s-final`
(a form ending in an apostrophe and s), and `spaced`. A candidate can carry several. The site's Definitions
section runs the grammar on any typed string.

### The evidence semantics

For each published list, a single-token row holds 1 where the list lists the string, 0 where it does not,
and -1 where the list is structurally blind to the row's class (a list built without hyphens cannot hold a
hyphenated string). A multiword row is measured by the 2 lists that hold multiword terms, WordNet and
Wiktionary, and holds null in every other list's column. Null means "not measured by that source", never
"false". Every share in this report is computed over the rows the list in question could hold, and says
so.

The corpora contribute containment and features and never admit a string: Google Books' English 1-grams
and wordfreq's English list each record whether they hold a single-token row, and the feature layer
records how often.

### Families and tiers

The {{published_set_count}} published lists come from {{family_count}} source families: WordNet;
Wiktionary's English pages; hunspell, whose {{hunspell_dictionaries}} English dictionaries (American, British, Canadian,
and Australian) derive from 1 upstream and count as 1 family; ENABLE; and SCOWL. A family lists a row when any
of its lists does, and cannot hold it when none of its lists can. Independence is counted by family, so a
row that SCOWL and 2 hunspell dictionaries list counts as listed by 2 families.

Counting families this way follows the analysis plan's definition of the public panel. It is generous to
SCOWL and hunspell: the American, Canadian, and Australian hunspell dictionaries come from SCOWL, as their
READMEs state. Counted as 1 family, SCOWL and hunspell leave {{strict_two_plus}} rows
({{strict_two_plus_pct}}) listed by 2 or more families, {{strict_two_plus_fewer}} fewer than the count
below. Every figure that counts families states which count it uses; the rest of this report uses the
plan's.

2 of the published lists also draw in part on word-game material, by their own documentation. ENABLE's
README says it reflects the changes to the Official Scrabble Players Dictionary in effect from January 1,
1998 [29], and SCOWL's lists at size 80 and above include the lists of the ENABLE supplement package [23],
which SCOWL's successor documents as holding additional and stale entries of that dictionary [25]. Where
those lists agree with a withheld game list, the agreement is not independent evidence.

Each single-token row falls in 1 of {{tier_count}} **evidence tiers**: listed by 2 or more families; by 1;
by none, with a corpus holding it ("corpus only"); or by none and no corpus ("no evidence"). The tiers are
shown, not averaged away, because most rows are in 1 tier.

{{table:tiers}}

### The identifier and the canary

`id` is the first 16 hexadecimal digits of the sha256 of the string's UTF-8 bytes. It depends on the
string alone, so a reader can join versions by `id` or by `word`, and the `sample` config, the rows whose
`id` begins with `{{sample_prefix}}`, holds the same strings in every version that holds them. The card
and each data file carry a canary string, recorded in the release record, so that a later test can ask
whether a model has memorized the dataset's documentation.

## 4. Sources, licenses, and the public projection

The build measured {{panel_set_count}} panel sets. Each source's terms were read at its
primary source, and the author ruled on the readings. {{withheld_list_count}} lists are withheld from the public
version, because their membership may not be published: NASPA Word List 2023 and Collins Scrabble Words
2021, which are proprietary; the legacy SOWPODS list, for which no license was found; and Webster's Second
International and its supplement of hyphenated terms, whose 1961 copyright renewal holds. Their columns
and labels are absent. Their rows still ship wherever published evidence supports them.

The withholding has measured effects, which the card states and this report repeats:

- **Restricted rows.** {{rows_restricted}} of the pin's {{rows_pin}} candidates are attested only by the 2
  proprietary lists and are in no version.
- **Held-back rows.** Of the {{rows_shippable}} shippable rows, {{held_back_rows}} are held back in the
  private record, because once the withheld lists and channels are taken away nothing published supports
  them.

{{table:held_back}}

- **Recomputed fields.** `panel_sets`, `panel_count`, and `provenance_class` count the
  {{published_set_count}} published lists alone, so a row with `panel_count` 0 may still be listed by a
  withheld list.
- **Withheld channel labels.** {{channel_withheld_rows}} rows carry `{{channel_withheld_label}}`: every
  intake channel recorded for them names a withheld list or a source whose terms do not allow publishing
  the label.
- **Withheld feature columns.** {{withheld_feature_count}} of the feature layer's columns are withheld.
  {{withheld_reference_feature_count}} were computed against a reference that holds Webster's
  Second, so a value could reveal whether that list holds a string's neighbor, stem, or segments. The
  other {{withheld_model_feature_count}} come from a character model fitted on strings that at least 2/3
  of their applicable panel sets list, the withheld lists among them; a test showed that their values,
  less those of the same model fitted on the published lists alone, rank strings by withheld listing well
  above chance (`docs/licenses/FEATURE_COLUMNS.md`).

The universe is licensed CC BY-SA 4.0, the share-alike floor of its Wiktionary-derived fields.
`NOTICES.md` carries every notice and credit the sources require.

## 5. Construction

Each step has a committed record, and the counts are those records'. The site's "How it was built" page
shows the same steps with their counts.

1. **The English OpenList's universe.** The English OpenList (EOL) is a word list with its own grammar and
   governance. Its valid and invalid lists at revision `c1139698` hold {{eol_universe_rows}} strings,
   every string it had taken in, whichever way it ruled.
2. **The census.** The pinned sources re-read under the grammar give {{census_candidates}} candidates in
   the exception classes the EOL's letters-only rule could not hold: hyphens, accents, a diaeresis,
   apostrophes, and ligatures.
3. **The merge.** The 2 sets merged give {{merge_rows}} rows, 1 per string. Filtering the merge by its EOL
   flag reproduces the EOL's pinned lists byte for byte.
4. **The audit.** Every source's coverage by the merged universe was reconciled to a remainder of
   {{audit_remainder}}: {{c4_additions}} strings a source listed and the merge lacked were added. The
   result is the single-token pin, {{v1_rows}} candidates.
5. **The spaced admission.** {{pin_spaced}} multiword candidates from WordNet and Wiktionary were admitted
   under the grammar's space rule. The pin, {{rows_pin}} rows, reproduces the single-token pin byte for
   byte as its single-token projection.
6. **The layers.** No row is added. Each row is measured against the panel lists (the evidence matrix),
   given its corpus features (the feature layer), and given its record of how it came in (the
   intake-provenance layer).
7. **The model-and-engine column,** derived from the EOL's valid dictionary at the pin
   ({{model_basis_entries}} entries).
8. **The release.** The restricted rows are dropped and the public projection applied (§4), leaving
   {{rows_universe}} rows. The build asserted, on each of its {{files_asserted}} written files, that none
   of the {{restricted_words_checked}} restricted rows' strings is present, that every `id` is distinct,
   that each filter config is its predicate's filter, that no withheld column, label, or held-back row is
   present, and that `provenance_class` and `model_or_engine` re-derive from the file's own fields.

The release record, `pipeline/research/release/release_{{version}}.json`, holds every file's rows,
columns, bytes, and sha256, and the counts of every assertion.

## 6. Contents

### Form

<!-- figure:F1 -->

**Length.** The median single-token row has {{len_corpus_p50}} characters in the corpus-only tier,
{{len_two_plus_p50}} in the tier listed by 2 or more families, {{len_one_p50}} in the tier listed by 1,
and {{len_none_p50}} in the tier with no evidence. Multiword rows have a median of {{len_multiword_p50}}
characters; {{mw_two_tokens}} of the {{rows_multiword}} multiword rows ({{mw_two_tokens_pct}}) have 2
tokens.

{{table:lengths}}

**Characters.** All {{chars_used}} characters of the charset occur. Of the accented letters and ligatures, the least used
occurs in {{char_rows_nonbase_min}} rows and the most used in {{char_rows_nonbase_max}}; the
apostrophe occurs in {{char_rows_apostrophe}} rows, the hyphen in {{char_rows_hyphen}}, and the space in
the {{char_rows_space}} multiword rows. The site charts every character, by tier.

<!-- figure:F2 -->

**Classes.** {{flag_plain}} rows ({{flag_plain_pct}}) are plain. The other {{flag_any}} carry at least 1
class, in {{class_combinations}} combinations in all.

<!-- figure:F4 -->

{{table:flags}}

**Apostrophes.** Of the {{apos_rows}} rows with an apostrophe, {{apos_s_final}} end in an apostrophe and
s, {{apos_contraction}} are contractions, and {{apos_other}} are other forms.

**Multiword terms.** WordNet and Wiktionary both list {{mw_both}} of the multiword rows, WordNet alone
{{mw_wordnet_only}}, and Wiktionary alone {{mw_wiktionary_only}}; every multiword row is listed by at
least 1 of them, because they are its only sources.

**Variants.** {{var_groups}} groups of 2 or more rows ({{var_rows}} rows, {{var_rows_pct}} of all) are
equal once hyphens, spaces, apostrophes, and accents are removed. Most differ by an apostrophe
({{var_by_apostrophe}} groups), a space ({{var_by_space}}), or a hyphen ({{var_by_hyphen}}); the largest
group has {{var_max_size}} members. Of the {{var_pairs}} pairs, a published list holds both members in
{{var_pairs_both}}, 1 in {{var_pairs_one}}, and neither in {{var_pairs_none}}.

{{table:variants}}

### Lexical category

The universe records no part of speech, lemma, or inflection. WordNet lists {{list_wordnet_listed}}
single-token rows and {{mw_wordnet}} multiword rows, and those rows could take a part of speech from
WordNet's synsets; the rest have none. The plan for a later version adds a part-of-speech layer, lemma
and inflection relations, and WordNet's categories. The morphology measures of the feature layer are
among the withheld columns (§4).

### Frequency

wordfreq scores few rows: {{zipf_with_two_plus_pct}} of the tier listed by 2 or more families,
{{zipf_with_one_pct}} of the tier listed by 1, and {{zipf_with_corpus_pct}} of the corpus-only tier. Google
Books holds more: {{gb_with_two_plus_pct}}, {{gb_with_one_pct}}, and {{gb_with_corpus_pct}} of the same
tiers. Where a value exists, the median Zipf value is {{zipf_p50_two_plus}} in the first tier,
{{zipf_p50_one}} in the second, and {{zipf_p50_corpus}} in the corpus-only tier, and the median log10 count
of Google Books matches is {{gb_p50_two_plus}}, {{gb_p50_one}}, and {{gb_p50_corpus}}.

<!-- figure:U1 -->

Frequency rises with agreement. By the number of families that list a row, the median Google Books value
climbs from {{u5_gb_p50_k0}} for rows no family lists to {{u5_gb_p50_k5}} for the {{u5_rows_k5}} rows all
{{family_count}} families list.

{{table:u5}}

The span of years over which a string occurs in Google Books has a median of {{span_p50_two_plus}} years
in the first tier, {{span_p50_one}} in the second, and {{span_p50_corpus}} in the corpus-only tier. It is a
span in a corpus of scanned books, not a date of first use.

### Provenance

Every row records its **intake layer** (the step of §5 that brought it in), its **intake kind** (obtained
from a source, derived from pinned sources, or generated), and its first-seen **intake channels**, kept
apart from the evidence for it. A channel records where a string was first seen and is never an
attestation.

<!-- figure:P1 -->

{{table:flows}}

The EOL's invalid list contributes {{p1_eol_invalid}} rows, its valid list {{p1_eol_valid}}, the census
{{p1_c1_exceptions}}, the audit {{p1_c4_additions}}, and the spaced admission {{p1_spaced_c015}}. The
largest channel, `{{p4_top_channel}}`, is the first-seen channel of {{p4_top_rows}} rows, of which a
published family lists {{p4_top_listed_pct}}. The site lists all {{p4_channels}} channels.

{{table:channels}}

**The synthetic engine.** {{p2_rows}} rows were made by the EOL's synthetic engine. Its code does not
survive, and its own per-row record of the method is empty, but its author describes the methods:
affixes applied without a part-of-speech filter to the list as it then stood (plurals, past tenses,
gerunds, agent nouns, comparatives and superlatives, and prefixed forms); chemical names varied by
substituent, and short chains of root, infix, and suffix, made by substitution over a hand-written list
of substituents and roots, with no tool that derives a name from a formula; medical and scientific
prefixes; and Greek plurals. It gave each base word a domain label, and it used NLTK, lemminflect, and
spaCy. Each row carries the method inferred from its form. A published family lists {{p2_listed}} of
them ({{p2_listed_pct}}).

{{table:engines}}

**Provenance classes.** Over the published fields, {{prov_channel_and_containment}} rows have both a
recorded channel and containment in a list or a corpus, {{prov_channel_only}} a channel only,
{{prov_containment_only}} containment only, and {{prov_neither}} neither.

**The EOL since its pin.** The EOL's last published list (revision `{{eol_last_revision}}`) holds
{{eol_last_list}} entries: the {{eol_list_at_pin}} of its list at the pin and {{eol_added_after_pin}}
added after it. The universe's `eol-valid` config, which is the EOL's public dataset, holds
{{eol_public_dataset}}; the license rules hold back the other {{eol_held_back}}.

## 7. The sources compared

This section is the one no single list can write, because none measures the same strings against the
others. It covers the single-token rows, where all {{published_set_count}} lists are measured.

**Methods.** The main pair measure is directed containment: of the strings list A lists that list B could
hold, the share B lists. It is computed over the jointly eligible rows, with A's rows that B cannot hold
reported beside it as a difference of scope, not of judgment. The Jaccard index appears as a secondary
measure only, because it cannot exceed the smaller list's size over the larger's. Agreement is counted as
k of m: the families that list a row out of the families that could. The report makes no significance
test, because at this size every test is significant and the null hypothesis is false by construction,
and it makes no estimate of how many English strings no list holds: the lists derive from one another,
listing tracks frequency, and the target is open-ended.

### Sizes and blind classes

{{table:lists}}

Wiktionary lists the most single-token rows, {{list_wiktionary_listed}}, and is blind to no class.
WordNet lists the fewest, {{list_wordnet_listed}}. ENABLE cannot hold {{list_enable_blind}} rows, every row
with an exception class, and each hunspell dictionary but the British cannot hold {{list_hunspell_us_blind}}.

### Containment

<!-- figure:S2 -->

{{table:containment}}

The heat map's asymmetry shows nesting. ENABLE's rows that SCOWL can hold are {{cont_enable_in_scowl}}
listed by SCOWL, and SCOWL's that ENABLE can hold are {{cont_scowl_in_enable}} listed by ENABLE: ENABLE is
nearly a subset. The American hunspell dictionary's rows are {{cont_hunspell_us_in_hunspell_ca}} listed by
the Canadian. WordNet's rows are {{cont_wordnet_in_scowl}} listed by SCOWL and {{cont_wordnet_in_wiktionary}}
by Wiktionary, while Wiktionary's are {{cont_wiktionary_in_wordnet}} listed by WordNet and
{{cont_wiktionary_in_scowl}} by SCOWL: Wiktionary holds much the others do not.

### Combinations and what each family holds alone

Over the {{s3_rows}} rows every family can hold, the rows fall in {{s3_combinations}} combinations of
families. {{s3_none}} ({{s3_none_pct}}) are listed by no family. Of the rest, {{s3_wiktionary_only}} are
listed by Wiktionary alone, and {{s3_all5}} ({{s3_all5_pct_of_listed}}) by all {{family_count}}.

<!-- figure:S3 -->

{{table:s3}}

Over all single-token rows, the rows only 1 family lists are:

{{table:alone}}

### Agreement

Among the rows all {{family_count}} families can hold, {{m5_listed}} are listed by at least 1. Of those,
{{m5_k1_pct_of_listed}} are listed by exactly 1 family and {{m5_k5_pct_of_listed}} by all
{{family_count}}.

<!-- figure:S5 -->

{{table:k_of_m}}

### Coverage by frequency

<!-- figure:S6 -->

For each band of wordfreq's Zipf value, the share of the rows a list could hold that it lists. Rows
wordfreq does not score form their own band, which holds most rows. Coverage rises with frequency for
every list. In the band of Zipf 5 and over, hunspell's American dictionary lists {{cov_hunspell_us_b5plus}}
and WordNet {{cov_wordnet_b5plus}}; weighted by tokens, WordNet's share there falls to
{{covw_wordnet_b5plus}}: WordNet holds only nouns, verbs, adjectives, and adverbs, and the most frequent
strings include function words.

{{table:band_rows}}

By strings:

{{table:coverage}}

Weighted by tokens:

{{table:coverage_weighted}}

### The varieties, the core, and the tails

**American and British spellings.** {{us_not_gb}} rows are in the American hunspell dictionary and not the
British, {{gb_not_us}} in the British and not the American, and {{us_and_gb}} in both. The 4 hunspell
dictionaries all list {{hun_all4}} rows; of the rows at least 1 of them lists, {{hun_some_pct_of_listed}}
are listed by some and not all.

**The consensus core.** {{core_rows}} rows ({{core_pct}}) are listed by 2 or more families. The EOL's valid
list contributes {{core_layer_eol_valid}} of them and its invalid list {{core_layer_eol_invalid}},
strings the EOL ruled out that 2 or more independent families list.

**The tails.** {{freq3_unlisted}} rows with a Zipf value of 3 or more are listed by no family. In the other
direction, {{listed_no_corpus}} listed rows ({{listed_no_corpus_pct}} of the listed rows) are in neither
corpus.

### What each list adds

<!-- figure:S13 -->

Without a given list, the rows only it lists would be unlisted (§7). As lists are added in every order,
the union grows from a mean of {{acc_mean_1}} rows for 1 list to {{union_all}} for all
{{published_set_count}}; the order matters, as the range at each step shows.

{{table:accumulation}}

## 8. Limitations

{{card_limitations}}

**What the universe does not record:** part of speech; lemma and inflection relations; definitions and
senses; pronunciation, syllables, etymology, and a first attestation year; variety and register labels
(the 2 variety columns are proxies); a frequency drawn from many kinds of text for most rows (wordfreq scores
few; the Google Books counts cover most single-token rows, but from scanned books alone); and validity, by
design.

## 9. Uses and out-of-scope uses

Studies that build lists of real or invented words each check existence against a reference of their own,
and none stores a per-item, per-reference result. The universe stores one. It supports, with these
caveats:

1. **A "listed by 0 of N lists" screen for invented stimuli,** never a "not a word" verdict. N is the
   published lists of the version, here {{published_set_count}}.
2. **Auditing pseudoword generators:** finding generated strings that a list holds, or that are variants
   of a listed string (§6).
3. **Graded existence per list,** with "not measured" kept apart from "not listed".
4. **A reproducible frame for choosing items** in rating and norming studies: a stated filter over a
   pinned version, with its code.
5. **Control of regional spellings** through the variety proxies.
6. **Frequency matching in the very low range,** with missing values explicit.
7. **A dated exclusion list** for benchmarks of novel words, re-run at each version.
8. **Stratified pools** for vocabulary tests.

**How to check a made-up string.** Look it up on the site or in the `universe` config; read its listing in
each list, remembering that -1 means the list cannot hold it; and treat a listing as a listing, not as use,
and absence from every list as absence from the lists, not from text. A multiword string is checked
against 2 lists only.

**Out of scope:** calling a string a word or not a word; using the universe as a dictionary; proper names;
and any claim about what a model was trained on.

## 10. Maintenance and versions

A released version never changes; a correction comes as a new version with a change log
(`docs/UPKEEP.md`). A row leaves a public version only under the rules of that policy, and a version may be
withdrawn, never edited. A request to withhold, correct, or restore a source or a row is acknowledged
within 7 days and acted on within 14 days of its verification, and each version's change log records every
withholding, as counts. Each version records the commit of the code that built it, and a checkpoint
measures every source again and builds a new pin and version.

## 11. Responsible use and disclosures

- **The study's material stays private.** The project published the design of a study of words in use as
  a proposal; it has not been run. Its development ledger, synthetic controls, probe batteries, pilot
  items, and every label and verdict stay private, and the build asserts that none of the synthetic
  controls is in any file.
- **Language models.** No language model decided any row the CEOL added. The EOL decided some rows of its
  valid list with a language model, Google Gemini 3 Flash Preview by its per-entry record, and
  `model_or_engine` marks those rows, so a list can keep them or leave them out.
- **Offensive and personal content.** The universe holds strings its sources hold, and some are offensive.
  This version does not measure their share: the analysis plan's measure needs an offensive-term lexicon
  whose license allows the use, which the project has not chosen. No string is printed in this report.
- **Contamination.** The release's date, file hashes, and canary are recorded, so that a later question
  of whether a model saw the dataset can be dated. The project's own pages mention strings; they are
  mentions, not uses.

## 12. Availability and reproducibility

The dataset is `{{dataset}}` on the Hugging Face hub, at the tag of its version, with a Croissant file
carrying its responsible-AI fields. The code and every committed record are at {{code_repository}}. The
release rebuilds from its pinned layers with `python3 -m research.release.build_release --version
{{version}}`, the descriptive analysis with `python3 -m research.analysis.descriptive --version
{{version}}`, and this report with `python3 -m research.release.report.paper --render`. The analysis is
deterministic: its check rebuilds `analysis.json` and compares it byte for byte. The pinned layers
themselves are private, because they hold the withheld lists; anyone who holds the same versions of the
sources can rebuild them from the archived inputs the records name.

**Appendix A**, the comparison over all {{panel_set_count}} lists of the private universe, waits for the
license review's confirmation that the terms under which the project holds each withheld list allow
publishing aggregate counts.

## Appendix B. The columns

The `universe` config carries {{columns_universe}} columns and the `features` config {{columns_features}}.

**The key**

{{table:columns_key}}

**The pin's columns**

{{table:columns_pin}}

**The release layer**

{{table:columns_release}}

**The intake-provenance layer**

{{table:columns_provenance}}

**The evidence matrix**

{{table:columns_evidence}}

**Model and engine**

{{table:columns_model}}

**The feature layer**

{{table:columns_features}}

## Glossary

- **Candidate:** a string that passes the spelling grammar; every row is one.
- **Listed:** a list, at its pinned version, includes the string.
- **Cannot hold (blind):** a list structurally excludes strings of the row's class.
- **Family:** the lists that derive from 1 upstream; hunspell's 4 dictionaries are 1 family.
- **Evidence tier:** a single-token row's count of listing families, with "corpus only" and "no evidence"
  for rows no family lists.
- **Intake channel:** where a string was first seen; never an attestation.
- **Withheld list:** a list whose columns and labels the public version drops.
- **Restricted row:** a row only the withheld proprietary lists attest; it is in no version.
- **Held-back row:** a shippable row with no published evidence once the withholding is applied.

## References

{{references}}
