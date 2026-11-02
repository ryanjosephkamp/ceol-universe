# The CEOL grammar

**The specification is executable: [`ceol/grammar.py`](ceol/grammar.py).**
This document describes it; where prose and code could ever disagree, the code
is the specification and the prose is the defect. The figures and inventories
below are re-derived from the code by `research/verify_doc_numbers.py`, which
runs in the test suite — a doc that drifts fails CI, not review.

The grammar admits one word-space, with the rules below.

---

## 1. The character inventory

Lowercase output over a **closed** charset — extended only by a decision-log
entry, never by an edit:

- The base alphabet `a`–`z` (26 letters).
- Accent inventory (19): á à â ä é è ê ë í î ï ñ ó ô ö ú û ü ç
- Ligatures (2): æ œ
- The hyphen `-` (U+002D HYPHEN-MINUS) — the only admitted hyphen.
- The apostrophe `'` (U+0027 APOSTROPHE) — the only admitted apostrophe.
- The space (U+0020 SPACE) — the only admitted word-space.

That is 47 letters and a 50-character charset in total. Digits and every
character outside the inventory are rejected — `mp3` and `7up` are out by
construction, and a space does not launder a digit (`mp 3` is out too).
The underscore is never a character: it decodes to space at the parse
layer of any source that documents underscore-as-space — today MediaWiki
titles and WordNet lemma fields — before the grammar sees the string.

## 2. The normalization pipeline

```
NFC  →  U+2019 → U+0027, U+00A0 → U+0020  →  lower()  →  NFC again
     →  structural validation
```

1. **NFC, never NFKC.** Compatibility decomposition would launder
   presentation ligatures (U+FB03 `ﬃ`) into letter sequences; the CEOL
   rejects them instead. The declared ligatures æ/œ are ordinary letters to
   Unicode and survive either normal form.
2. **Exactly two canonicalizations, each carried by its own decision:
   U+2019 RIGHT SINGLE QUOTATION MARK → U+0027 APOSTROPHE, and
   U+00A0 NO-BREAK SPACE → U+0020 SPACE.** The typographic
   apostrophe and the non-breaking space are the same word dressed
   differently; without these folds the affected words silently exist
   twice. Every other look-alike — U+2018, U+02BC, backtick, U+00B4, the
   dashes U+2010/U+2013/U+2014, the soft hyphen U+00AD, every other
   whitespace character (tab, line breaks, the U+2000-block spaces,
   U+3000, the zero-width characters) — is **rejected, not folded**.
   Folding an undeclared character would invent data.
3. **lower(), never casefold().** casefold() maps ß to `ss`, silently
   turning donor-language orthography (`straße`) into an English-looking
   string (`strasse`). lower() leaves undeclared letters in place to fail
   the charset check, which is the honest outcome. This deliberately
   diverges from the EOL's casefold — safe there because its `^[a-z]+$`
   rule rejected every transformed output anyway; unsafe here.
4. **NFC again**, because lower() can decompose: Turkish `İ` lowers to
   `i` + U+0307 COMBINING DOT ABOVE, which composes with nothing and must
   fail the charset check rather than slip through.

## 3. Structural rules

- Every character in the declared charset.
- **Spaces single and interior only**: no
  leading, no trailing, no doubling — every space-separated token is
  non-empty, and each token must satisfy the single-token rules below.
  For a spaceless string those rules are exactly the pre-space-extension grammar:
  `tests/test_no_space_projection.py` proves the no-space projection
  byte-identical over the full pinned universe.
- **At least one letter per token.**
- **Hyphens interior only** (per token): no leading (`-up`), no trailing
  (`self-` — the truncated-fragment class the EOL's audit deleted), no
  doubling (`a--b`), and every hyphen-separated segment non-empty and
  carrying a letter.
- **Apostrophes interior or leading** (per token), never a token's final
  character, never doubled. Leading covers the archaic-elision class:
  `'tis`, `'struth`. Interior covers `can't`, `how're`, `t'ang`,
  `sou'easter`. Because the rule is per token,
  `rock 'n' roll` (token `'n'` apostrophe-final) is rejected, with the
  token-trailing-apostrophe class folded into the pending possessive
  decision. One-directionality holds: those candidates wait, they
  are not condemned.
- **A trailing apostrophe is not admitted — yet.** Plural possessives
  (`dogs'`) belong to the possessive class, which is a pending decision.
  If the maintainer admits it, the extension lands as a documented change and a
  grammar change with its own tests, not as a quiet relaxation.

## 4. Census classes

Non-exclusive flags computed by `ceol.grammar.classes()`:

| Class | Definition | Examples |
|---|---|---|
| hyphenated | contains `-` | low-cut, co-owner |
| accented | any non-diaeresis accent letter | début, glacé, señora |
| diaeresis | any of ä ë ï ö ü | naïve, kümmel, zoöphagy |
| ligature | æ or œ | (no example on the vetted list) |
| spaced | contains a space | bee balm, red elm |
| apostrophe-form | contains `'` | ain't, alp's, 'tis |
| contraction | apostrophe-form with any token matching the declared pattern: ends `n't`, ends `'ll`/`'ve`/`'re`/`'d`/`'m`, or leading apostrophe | can't, how're, 'tis |

Flags compose: a string can be spaced and accented, or spaced,
apostrophe-form, and contraction at once. The positional flags
(contraction, s-final) are evaluated per token, which for a spaceless word
is exactly the pre-space-extension behavior. `ceol.grammar.token_count()` records
the space-separated token count. The six-class `CENSUS_CLASSES` tuple —
the C1 census and C4 artifact schema — deliberately excludes `spaced`:
the spaced class's per-source applicability is established by the S3
space census and enters the evidence semantics at the S5 merge, not
retroactively.

Two deliberate rulings inside that table: **medial elision** (`wheresoe'er`,
`whatsoe'er`) counts as apostrophe-form, not contraction — the mechanical rule
does not pretend to know that `wheresoe'er` is *wheresoever*; and **`'s`-final forms**
(`golf's`) are counted under a separate `s-final` diagnostic, never as
contractions, because `golf's` is "golf is" and "of golf" in one surface
form and a surface-form census cannot disambiguate. The s-final count is
input to the possessive decision.

## 5. What the trap tests pin down

`tests/test_grammar.py` carries one test per trap, written before any word
list existed: NFD composition, the U+2019 fold and every rejected
look-alike, eszett non-laundering, the Turkish-İ combining-dot residue,
titlecase digraphs, NFC-vs-NFKC ligature behavior, fullwidth letters, the
closed inventory, every structural rule, and the class flags. The space extension's
spaced-form section adds: the U+00A0 fold and every other whitespace
character rejected, the underscore never admitted, per-token structural
rules, NFC composition across a space, idempotence and lower-not-casefold
over spaced forms, and the composed class flags.
`tests/test_no_space_projection.py` holds the space gating invariant: a
frozen copy of the pre-space-extension implementation, agreement over an adversarial
spaceless set, and byte-identity over the full pinned universe.
