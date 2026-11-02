# C4 step 1 — the evidence matrix

**Every cell is an attestation lookup, never a verdict.** Built by
`research/evidence/build_evidence.py` over the pinned universe
(10,001,741 rows) under the C-010 semantics: three-valued evidence
E ∈ {1, 0, NA}, exact CEOL-normalized key equality, NA where a detector
is structurally blind to a word's class. Every figure lives in
`evidence.json`; the applicability table in C-010 is re-checked
cell-by-cell against the build by the doc-numbers enforcer.

## The detectors

Twelve binary detectors — the EOL's eleven plus **web2a**, promoted from
census source (its 31,213 hyphenated compounds are the deepest hyphen
authority after Wiktionary) — plus the SCOWL ordinal tier and the
all-languages title screen. WordNet was **re-derived under the CEOL
grammar** (parity with the EOL's pinned set asserted on the plain split):
its 5,173 hyphenated, 136 apostrophe-form and 3 contraction lemmas enter
evidence for the first time.

| detector | fires | NA rows |
|---|---:|---:|
| wiktionary_english | 831,973 | 0 |
| wordnet | 81,029 | 8,147 |
| web2 | 234,456 | 135,680 |
| web2a | 31,213 | 9,923,554 |
| hunspell_en_US | 121,252 | 88,348 |
| hunspell_en_GB | 262,413 | 1,940 |
| hunspell_en_CA | 120,947 | 88,348 |
| hunspell_en_AU | 121,490 | 88,348 |
| enable1 | 172,823 | 213,867 |
| sowpods_legacy | 267,751 | 213,867 |
| nwl2023 | 196,601 | 213,867 |
| csw21 | 279,077 | 213,867 |

SCOWL tier: 518,438 words carry a tier (ten values, 10–95); the screen
fires on 1,504,118 rows. The Scrabble lists' NA count is exactly the
exception inventory (213,867) — a-z formats are blind to every exception
class; web2a's NA count is the complement of the hyphenated-only rows it
can see.

## Determinism and reproduction

- **All twelve shared detectors reproduce the EOL evidence matrix's
  per-detector totals digit-for-digit on the shared 9,787,841-word
  frame** (`eol_reproduction` in `evidence.json`) — two pipelines, one
  measurement, same discipline as the census tripwires.
- SCOWL is wider **by ruled design**, not drift: the census's C-005
  inclusion (words + contractions, every variant category) adds 3,051
  plain words on the shared frame over the EOL's six-family rule
  (435,936 both ways like-for-like); tier values agree on every shared
  word, asserted at ingest.
- Every derived set is hash-verified against its recorded pin before
  use; a drifted source breaks the build, not the semantics.

## What the matrix shows

- **545 distinct binary patterns** over twelve detectors — the pattern
  table the model contest fits over (fewer than the EOL's 677: NA masks
  collapse patterns the a-z world kept distinct).
- **SR2 (reading A analogue): 88.64%** of rows carry no positive binary
  evidence (EOL: 90.50% — the wider sources bite). **Reading B upper
  bound: 87.33%** — all-zero AND absent from wordfreq. The operative
  reading-B gate (≤ 50%, D-032 analogue) is **evaluated at step 2**,
  when Google Books presence exists; the EOL precedent collapsed the
  same bound from 90.50% to 8.63%, and the upper bound can only shrink.
- **1,703 WordNet exception lemmas sit outside the pinned universe**
  (`wordnet_beyond_frame.txt`, committed — wordnet-attested, hence
  redistributable). They are **intake candidates for the open channel,
  not frame members**: the pin is settled (C-009), and nothing enters by
  side effect. The other 3,526 of WordNet's 5,229 exception lemmas were
  already in the universe via the census sources.

## Licence

The matrix carries `is_restricted` forward; `data/evidence.parquet` is
gitignored and the committed `wordnet_beyond_frame.txt` was scanned by
the permanent license test like every committable file.
