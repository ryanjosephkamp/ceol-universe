# The intake provenance of universe v2

**2026-09-17** · decision C-064 · built by
[`build_provenance.py`](build_provenance.py) over the C-016 pin, the
evidence matrix (C-010), the feature layer (C-011), and the EOL's two
dictionaries at revision `c1139698`, pinned in
[`eol_dictionaries_manifest.json`](eol_dictionaries_manifest.json). This
file is rendered from [`PROVENANCE.template.md`](PROVENANCE.template.md):
every figure below is a row of [`provenance.json`](provenance.json), and
`check_provenance` in `research/verify_doc_numbers.py` re-renders the
file and re-derives the rows from the layer. The layer itself,
`data/universe_v2_provenance.parquet`, holds every row of the pin, the
1,985 restricted rows included, and stays local and
gitignored under the license split. No candidate word is printed here.

The question this report answers is the maintainer's of 2026-09-16: for every
candidate in universe v2, where was it obtained, derived, or generated.
Nothing here says whether a candidate is valid. Validity is the
in-the-wild programme's to decide under its own definition (C-021);
universe membership, the strata, and the pin's bytes are untouched.

## 1. The residual, stated first

**16,373 of the 10,296,606 candidates
(0.16%) have no recorded intake
channel and no measured containment.** For these the record this package
can reach does not say how the string entered the EOL's pool, and none of
the thirteen panel sets and neither corpus the CEOL measures holds the
string. 16,371 of them are in the
EOL's invalid layer (0.18% of
that layer) and 2 are in its valid
layer. 16,367 have an entry in
the invalid dictionary and 2
in the valid one, each entry with a null `candidate_source` and no
`source`; 4 have no dictionary
entry. 288 of the
residual rows are page titles in some language's Wiktionary, which is a
screen and not containment (C-010), so it is recorded and does not move a
row out of the residual.

Four limits on how far that statement reaches:

- **The residual depends on one reading of this seat's.**
  33,639 invalid strings have no
  entry in either dictionary. The EOL's own correction ledgers account
  for every one of them, and
  33,594
  are generated forms the EOL demoted from its valid list on 2026-08-14.
  This layer labels those as generated from the ledgers (§7). Without
  that reading they would carry no recorded channel, and the residual
  would be 46,185.
- **A recorded channel is not an attestation.**
  828,789 rows
  (8.05%) have a recorded channel
  and no measured containment, and
  320,521 of them are generated
  strings whose only record is the engine that made them.
- **No recorded channel is not no origin.**
  303,608 inherited strings carry
  `eol:phase1-unrecorded`. 8,456
  of them are listed by a panel set; 286,120
  are Google Books 1-gram types in the CEOL's re-stream
  (278,715 of those
  listed by no panel set);
  64
  more are scored by wordfreq alone; the remaining
  16,373 are the residual.
  The maintainer's statement in §6 is consistent with these counts and is not
  proved by them: containment shows that a corpus holds the string, not
  that the EOL took the string from it.
- **The label vocabulary is narrower than the EOL's own account.** The
  EOL's final report names SCOWL, CMU Dict, and Moby among its Phase-1
  sources; no discovery-log label in either dictionary names any of the
  three. The labels `coca_frequency`, `opensource`, `linux`, and
  `libreoffice` occur in the dictionaries and are not in the report's
  tier table. The layer records the labels the dictionaries carry and
  infers nothing from the report.

## 2. Two senses of provenance, kept apart

**The intake channel** is the route by which a string entered the
candidate pool. For the 9,653,999 strings inherited from
the EOL it is read from the EOL's dictionaries: the `candidate_source`
list and the `source` field. The EOL ruled that list "a discovery log"
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
why they are separate columns. Over the valid layer the label `wordnet`
sits on 3,443 rows
(2,127
at the valid tier, the figure C-008 quotes), where the WordNet panel set
lists 57,970.
Over the inherited strings the label `google_ngrams` sits on
8,060,854
rows, every one of them a Google Books 1-gram type in the CEOL's
re-stream (0 are
not), while 590,891
further inherited strings are Google Books types and lack the label.

## 3. Every row, by layer, kind, and class

A row's **class** has two halves. It has a channel when
`intake_channels` holds any label other than `eol:phase1-unrecorded`. It
has containment when at least one of the thirteen panel sets lists it,
or it is a Google Books 1-gram type, or wordfreq scores it. Every row
has exactly one class.

| Intake layer | Rows | `channel_and_containment` | `channel_only` | `containment_only` | `neither` |
|---|---:|---:|---:|---:|---:|
| `eol_valid` | 345,103 | 315,191 | 28,451 | 1,459 | 2 |
| `eol_invalid` | 9,308,896 | 8,206,427 | 800,322 | 285,776 | 16,371 |
| `c1_exceptions` | 213,867 | 213,851 | 16 | 0 | 0 |
| `c4_additions` | 133,875 | 133,875 | 0 | 0 | 0 |
| `spaced_c015` | 294,865 | 294,865 | 0 | 0 | 0 |
| **universe v2** | 10,296,606 | 9,164,209 | 828,789 | 287,235 | 16,373 |

`channel_and_containment` is 89.00%
of the universe and `containment_only` 2.79%.
The two classes without containment sum to
845,162, which is the committed SR2
reading-B row of the feature layer (845,162
single-token candidates listed by no panel set and present in neither
corpus): this layer partitions that row and does not change it.

A row's **kind** is `obtained` (an inherited string taken in through a
channel), `derived` (a row of the CEOL's three layers, which the CEOL
derived from pinned sources under its grammar), or `generated` (made by
an engine, §7). A generated row is never derived.

| Intake layer | `obtained` | `derived` | `generated` |
|---|---:|---:|---:|
| `eol_valid` | 313,860 | 0 | 31,243 |
| `eol_invalid` | 9,009,753 | 0 | 299,143 |
| `c1_exceptions` | 0 | 213,867 | 0 |
| `c4_additions` | 0 | 133,875 | 0 |
| `spaced_c015` | 0 | 294,865 | 0 |
| **universe v2** | 9,323,613 | 642,607 | 330,386 |

## 4. The pinned inputs, and what they cover

| Input | Bytes | sha256 |
|---|---:|---|
| `merged_valid_dict.json` at `c1139698` (the local pinned file) | 282,080,828 | `20e5baedf4ac7731e3d2c51d5d3e357c14680a5b493c68eeaf4503484b46af2a` |
| `merged_invalid_dict.json` at `c1139698` (streamed once, never stored) | 12,237,976,092 | `8ccfccdf16c39f87ea091a46e27c0b746260bf4cd019a9b5ae9e9faea3aba703` |

The valid dictionary's hash equals the checksum ritual's value. The
invalid dictionary's hash was computed over the single stream and equals
the hub's ETag for the file. The value C-064 ruling 2 quotes as that
ETag, `1c921f6b…`, is the hub's Xet content hash of the same file, which
is not a sha256 of its bytes; the manifest records both. The stream
parsed 9,275,414 entries over
9,275,416 lines under the one-entry-per-line
layout, with a hard error armed for any line outside it; none occurred.

| Coverage | Valid dictionary | Invalid dictionary |
|---|---:|---:|
| Entries | 345,103 | 9,275,414 |
| Entries with a non-empty channel list | 136,236 | 8,707,758 |
| Entries with a `source` value | 207,406 | 265,549 |
| Entries with neither | 1,461 | 302,107 |
| Strings of its own layer | 345,103 | 9,308,896 |
| — with an entry in it | 345,103 | 9,275,257 |
| — with no entry in either dictionary | 0 | 33,639 |

157 entries of the
invalid dictionary are keyed by a string of the valid list; a row is
looked up in its own layer's dictionary first, so those rows read their
valid entry. 0 entries of
the invalid dictionary and 0
of the valid one fall outside the inherited strings.

The 33,639
invalid strings with no entry are accounted for in full by four
correction ledgers of the EOL repository, read and never written, each
pinned by sha256 in the manifest:
33,594
by its two demotion ledgers (every row an action `demote_to_invalid`
whose reason opens with the word "synthetic"),
8
by its single-letter ledger,
37
by its form-rule ledger as added candidates, and
0 by
none. The first group is generated (§7). The closed vocabulary holds no
label for a ledger action, so the other two groups carry
`eol:phase1-unrecorded`.

## 5. The channel table

The controlled vocabulary is the one C-064 ruling 8 adopted from the
package's agenda. For an inherited row a label is a discovery-log label
with its tier suffix removed, or the label of the entry's `source`
value; one row can carry several. Both dictionaries carry the same
eleven discovery-log labels and no other.

| Channel label | `eol_valid` | `eol_invalid` |
|---|---:|---:|
| `eol:authoritative-extracts` | 259 | 0 |
| `eol:coca_frequency` | 14,063 | 797,522 |
| `eol:collins` | 2 | 20 |
| `eol:dictionary-api:free-dictionary` | 143 | 0 |
| `eol:dictionary-api:merriam-webster` | 78 | 0 |
| `eol:enable` | 3,791 | 2,740 |
| `eol:extended-domain-sources` | 175 | 0 |
| `eol:google_ngrams` | 119,295 | 7,941,559 |
| `eol:invalid-list-recovery` | 7 | 0 |
| `eol:libreoffice` | 4,738 | 34,168 |
| `eol:linux` | 18,892 | 104,483 |
| `eol:nltk` | 18,889 | 104,478 |
| `eol:opensource` | 26,218 | 145,037 |
| `eol:phase1-unrecorded` | 1,461 | 302,147 |
| `eol:synthetic-engine` | 31,243 | 299,143 |
| `eol:tournament-list` | 175,501 | 0 |
| `eol:wikipedia` | 38,654 | 1,552,389 |
| `eol:wiktionary` | 83,403 | 551,742 |
| `eol:wordnet` | 3,443 | 14,180 |

For the CEOL's own layers the label is the namespace of the layer and
the name the pin's `sources` column carries (`census:` for the C1
exceptions, `audit:` for the C4 additions, `spaced:` for the C-015
spaced candidates, `ledger:d025` for the seeds re-ruled from the EOL's
D-025 deletions). The audit's own `eol:` prefix on the five EOL-derived
detector sets is removed, so that the `eol:` namespace holds the EOL's
intake record and nothing else.

| Channel label | Layer | Rows |
|---|---:|---:|
| `audit:csw21` | `c4_additions` | 86,064 |
| `audit:enable1` | `c4_additions` | 413 |
| `audit:hunspell_en_AU` | `c4_additions` | 2,810 |
| `audit:hunspell_en_CA` | `c4_additions` | 1,994 |
| `audit:hunspell_en_GB` | `c4_additions` | 15,275 |
| `audit:hunspell_en_US` | `c4_additions` | 1,872 |
| `audit:nwl2023` | `c4_additions` | 8,846 |
| `audit:scowl` | `c4_additions` | 90,637 |
| `audit:sowpods_legacy` | `c4_additions` | 84,334 |
| `audit:web2` | `c4_additions` | 34,267 |
| `audit:wiktionary_english` | `c4_additions` | 104,848 |
| `audit:wordfreq` | `c4_additions` | 10,191 |
| `audit:wordnet` | `c4_additions` | 4,564 |
| `census:hunspell_en_AU` | `c1_exceptions` | 33,293 |
| `census:hunspell_en_CA` | `c1_exceptions` | 33,111 |
| `census:hunspell_en_GB` | `c1_exceptions` | 86,480 |
| `census:hunspell_en_US` | `c1_exceptions` | 33,276 |
| `census:scowl` | `c1_exceptions` | 79,418 |
| `census:web2` | `c1_exceptions` | 2 |
| `census:web2a` | `c1_exceptions` | 31,213 |
| `census:wiktionary_english` | `c1_exceptions` | 56,104 |
| `census:wordfreq` | `c1_exceptions` | 21,587 |
| `ledger:d025` | `c1_exceptions` | 170 |
| `spaced:wiktionary_english` | `spaced_c015` | 250,893 |
| `spaced:wordnet` | `spaced_c015` | 63,483 |

The layer holds 804 distinct
combinations of labels. The Phase-1 tier is the suffix the labels of an
entry share (`_valid` or `_unlikely`; no entry mixes the two), and the
record column names the dictionary that holds the row's entry:

| Inherited layer | tier `valid` | tier `unlikely` | tier `mixed` | tier `none` | record `valid-dict` | record `invalid-dict` | record `none` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `eol_valid` | 131,226 | 5,010 | 0 | 208,867 | 345,103 | 0 | 0 |
| `eol_invalid` | 8,631,529 | 76,077 | 0 | 601,290 | 0 | 9,275,257 | 33,639 |

96.86% of the inherited
strings have a recorded channel.

## 6. The accounts of others, quoted as theirs

**The EOL's own account** (its final report and its commit history, read
and not re-derived here). Phase 1 built a foundation of
9,823,196 unique entries from tiered sources — Tier 1
Collins, WordNet, Wiktionary; Tier 2 SCOWL, Google Ngrams; Tier 3 NLTK,
CMU Dict, ENABLE; Tier 4 Moby, Wikipedia titles — of which
9,640,238 were "provisionally valid based
on source" and 182,958 "requiring further
verification". It calls Wiktionary "The largest single contributor" and
describes Google Books Ngrams as "Frequency-validated data used to
prioritize candidates". Phase 2d: "three synthetic engines generated
candidates" — inflection, chemical, and scientific — and
"330,386 synthetic candidates generated", of
which 64,837 were validated. The EOL's later
commits record that it demoted 16,476
comparatives and superlatives "built by blind affixation", found
2,636 surviving forms with no
stem in its list, and then demoted the
17,118 non-plural forms and kept the
28,605 plurals. Its decision log states: "The
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
from its form. There are 330,386
(3.21% of the universe), which is
the EOL report's own count of generated candidates:

| Where the record of generation lies | Rows |
|---|---:|
| An entry of the valid dictionary with `source: synthetic_generation` | 31,243 |
| An entry of the invalid dictionary with `source: synthetic_generation` | 265,549 |
| No dictionary entry; a row of the EOL's two demotion ledgers | 33,594 |
| **All generated rows** | 330,386 |

97.01% of them have no measured
containment. No generated row carries a discovery-log label
(0).

**The method is an inference, recorded with that status.** The EOL's
generator script is lost, the EOL repository never held it, and the
entry field that would have named the method (`generation_method`) is
null on every entry of both dictionaries. What is recorded as the method
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

| Inferred engine | `eol_valid` | `eol_invalid` | All |
|---|---:|---:|---:|
| `affixation` | 28,684 | 298,705 | 327,389 |
| `chemical-variation` | 1,363 | 231 | 1,594 |
| `greek-plural` | 846 | 108 | 954 |
| `medical-scientific-prefixing` | 330 | 8 | 338 |
| `unresolved` | 20 | 91 | 111 |
| **generated rows** | 31,243 | 299,143 | 330,386 |

99.09% of the generated rows
read as affixation. By rule:

| Inferred rule | Rows |
|---|---:|
| `affixation/plural` | 149,416 |
| `affixation/verb-form` | 117,315 |
| `affixation/superlative` | 30,682 |
| `affixation/comparative-or-agent` | 29,940 |
| `chemical-variation/substituent-prefix` | 903 |
| `greek-plural/-ses` | 812 |
| `chemical-variation/root-chain` | 691 |
| `medical-scientific-prefixing/domain-prefix` | 338 |
| `greek-plural/-des` | 142 |
| `unresolved/none` | 111 |
| `affixation/general-prefix` | 36 |

One check of the inference against a record it did not use: each row of
the EOL's two demotion ledgers states the form the EOL took the string
to be. On all 33,594 of the
33,594 ledger rows the inferred rule agrees
with that statement. The comparison is made at the level of the three
forms the ledgers' reasons open with (a comparative, a plural, a verb
form): the ledgers' finer wording — the plural of a gerund, the plural
of an agent noun — is not compared, and the `gerund-plural` and
`agent-plural` rules match no row of the layer, because the plural rule
matches first (C-065 ruling 9).

| The form the ledger claims | Inferred rule | Rows |
|---|---:|---:|
| comparative | `affixation/comparative-or-agent` | 8,440 |
| comparative | `affixation/superlative` | 8,036 |
| plural | `affixation/plural` | 9,174 |
| verb form | `affixation/verb-form` | 7,944 |

The category is recorded as found. In the valid dictionary it reads as a
domain label. In the invalid dictionary most synthetic entries carry
`Nonsense` or a similar value, which reads as the judgment of the EOL's
validation step and not as a label of the generator; for a ledger-named
row the category is the one the ledger carries.

| Category, as recorded | Rows |
|---|---:|
| Nonsense | 254,780 |
| General | 35,163 |
| Science | 18,221 |
| Medical | 10,957 |
| Chemical | 10,708 |
| General/Nonsense | 160 |
| Medical/Nonsense | 68 |
| Science/Nonsense | 52 |
| Unknown | 51 |
| Malformed | 48 |
| Misspelling | 43 |
| Malformed inflection | 37 |
| Science, Nonsense | 31 |
| Chemical/Nonsense | 14 |
| Structurally impossible | 11 |
| Biochemical | 8 |
| Chemical, Nonsense | 8 |
| Chemical/Science | 7 |
| Medical/Science | 6 |
| General/Science | 5 |
| Medical/Chemical | 4 |
| Medical, Nonsense | 3 |
| Technical | 1 |

A `generated` slice for the study is a later proposal to the maintainer, not
made here.

## 8. Measured containment, by layer

| Intake layer | Rows | Listed by a panel set | Google Books 1-gram type | wordfreq-scored | With containment | Wiktionary title, any language (the screen) |
|---|---:|---:|---:|---:|---:|---:|
| `eol_valid` | 345,103 | 268,159 | 298,050 | 100,429 | 316,650 | 258,413 |
| `eol_invalid` | 9,308,896 | 527,656 | 8,353,695 | 171,304 | 8,492,203 | 1,079,705 |
| `c1_exceptions` | 213,867 | 206,611 | 14,454 | 21,587 | 213,851 | 58,079 |
| `c4_additions` | 133,875 | 133,875 | 97,700 | 10,191 | 133,875 | 107,921 |
| `spaced_c015` | 294,865 | 294,865 | 0 | 0 | 294,865 | 0 |

Every spaced candidate is listed by WordNet, by Wiktionary, or by both,
and the corpus layers do not measure spaced terms (C-016).

## 9. Reproduction

```
python3 -m research.provenance.extract_eol_intake
python3 -m research.provenance.build_eol_dictionaries_manifest
python3 -m research.provenance.build_provenance
python3 -m research.provenance.build_provenance --render
```

The first command streams the invalid dictionary again, by the manifest's
URL, and stops if its hash differs. Inputs and output, by sha256:

| File | sha256 |
|---|---|
| `data/universe_v2.parquet` (the C-016 pin, read only) | `adaa1232b6bc4d9ead97f5e19a005b264bb6db8db77b6374fe66cdd1d2aca9dd` |
| `data/evidence.parquet` | `e4c86cc4a0caf3f01996e0abb50cedfd525ee7e08183679f154884bf7250d6ee` |
| `data/features.parquet` | `c578289b61d7b957bba1c91b9e65d3dbfcde3c5d74098316f6993643f240b7c7` |
| `.cache/provenance/eol_valid_intake.parquet` | `5b5a1bc593d4602eec158ca349fb1f04d2c2dd7e859863052bdf594c22953daf` |
| `.cache/provenance/eol_invalid_intake.parquet` | `ca608042cf2f5e5c9cdaea59e01f443cdf56bcd1a4fade2129a09dbb0889c09b` |
| `eol_dictionaries_manifest.json` | `3ac740d75d807cc8c31cc63b6e4ed624d5cb463046c97a9c17109ad91482a9cf` |
| `data/universe_v2_provenance.parquet` (the layer) | `7c9dc6284bf6393769eec3b26c27b8c77fa68dcf08cb5ef77148c2b7f07bec1b` |

## 10. What this layer does not do

It validates nothing and re-labels nothing. It adds and removes no
candidate, changes no stratum, and does not touch
`data/universe_v2.parquet`, whose two filter-equivalence proofs stand
over the same bytes. It changes nothing in the EOL: the EOL's files were
read, and a later EOL-side field, if the maintainer adopts one, is derived
from this table under the EOL's own governance (C-064 ruling 4). It
reads the discovery log as a record of the channel and never as
attestation.
