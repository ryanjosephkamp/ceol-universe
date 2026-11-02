# C4 step 2 — the feature channels over the wider alphabet

**Features are detectors with unknown reliability; nothing here is a
verdict.** Built by `research/features/google_books.py` +
`build_features.py` under C-011; gated by `gate_report.py`. Every figure
lives in `features.json` / `features_manifest.json` /
`features_gate.json` and is re-checked by the doc-numbers enforcer.
Output: `data/features.parquet` over 10,001,741 rows.

## The Google Books re-stream and the tokenization probe

All 24 pinned shards re-streamed under the CEOL grammar (one at a time,
hash-verified against the EOL manifest, deleted after aggregation):
**15,628,267 CEOL types** vs the EOL's 14,808,627 a-z types. The probe
that rules per-class applicability (C-010): accented 244,970 keys ·
apostrophe-form 465,587 · diaeresis 97,568 · contraction 34,407 ·
ligature 14,002 · **hyphenated 4,031** — every class is measured
non-zero, so Google Books features apply everywhere, with hyphenated
flagged *tokenizer-near-blind* (the corpus splits most compounds; its
missingness indicator carries that). **Parity: the plain subset is
contained in the EOL aggregate exactly**; the 398 EOL-only keys are the
casefold-laundered mass (straße→strasse) the C-001 grammar refuses to
invent — the divergence, measured.

## The training pool and the character model

The C-011 pool rule (fires ≥ ⌈2/3 · applicable⌉, the EOL's 8-of-12 on
plain words) yields **127,043 strong positives** (strict-¾ variant:
87,178) → train 89,059 / dev 12,595 / test 25,389 by sha256 hash-range.
Interpolation collapses onto the order-4 history (λ₄ = 0.851), and the
**per-class held-out perplexity clears every pre-declared bound — no NA
fallback anywhere**:

| class | held-out perplexity | C-011 bound |
|---|---:|---:|
| plain | 7.148 | 9.0 |
| apostrophe-form | 5.684 | 25.0 |
| ligature | 7.511 | 25.0 |
| hyphenated | 10.628 | 25.0 |
| accented | 13.446 | 25.0 |

The EOL achieved 7.034 on its 27-symbol space; 7.148 on the 50-symbol
space says the wider inventory cost almost nothing on plain words.
Contraction and diaeresis test cells sit under the 25-item evaluation
floor: no per-class gate is evaluable there — they are scored by a model
that passed every evaluable class, and the C5 deck's class strata
measure them by adjudication (recorded, not hidden).

## Negative controls and the admission gate

Six-pair typed OCR core, oriented AUC on the frequency ratio: **0.9904**
[0.9859, 0.9949] — corruption fire rate 52.9% vs 0.46% on held-out strong
positives (strings the pool rule selects), the Phase-2 asymmetry reproduced on the wider frame. Orthotactic
separation: foreign-accented 0.9871 (the alphabet extension earns its
keep against donor-language spillover), foreign-plain 0.9036, OCR
family 0.899; pseudo-words 0.5289 — near-chance by construction, they
are drawn from the model itself.

**Family admission (C-011 rule: AUC lower-95 ≥ 0.60 AND fire ratio
≥ 5×) — three admitted, two rejected, each rejection a finding:**

| family | oriented AUC [95%] | fire ratio | verdict |
|---|---|---:|---|
| apostrophe-loss | 0.9903 [0.9856, 0.9950] | 5.46 | **admitted** |
| ligature-expansion | 0.7899 [0.6913, 0.8886] | 254.55 | **admitted** |
| hyphen-drop | 0.7219 [0.6403, 0.8034] | 21.47 | **admitted** |
| diacritic-strip | unevaluable (2 corruptions) | 160.0 | rejected |
| hyphen-junction | unevaluable (real fires < 10) | 15.35 | rejected |

The diacritic-strip rejection is the variant confound *measured in the
control's own construction*: of ~123 accented held-out positives, all
but 2 strip to forms some source already attests — stripped accents are
overwhelmingly real variant spellings, exactly the failure C-011
predicted for ligatures. Hyphen-junction is unevaluable at the current
hyphenated test mass (801 pool words) and is partially carried by
`segment_attested_fraction` regardless. Neither ships (the columns exist,
flagged inadmissible; the contest reads only the admitted list).

## The rest of the channels

Realized productivity V/N recomputed over the CEOL aggregate (525,391
frame words parse to a productive suffix on a stem the source pool lists); the
GB-2020 floor of 40 holds in the re-stream, so Baayen's P remains
non-computable and the zero hapax columns stay visible. Dispersion: the
six year-level proxies. Zipf–Mandelbrot over the full aggregate:
α = 1.5573, β = 100.0. wordfreq Zipf for 303,511 words in its own
derived set (NA elsewhere; NA on hyphenated per C-010). Reference
lexicons: base 259,043 (wordnet ∪ web2, CEOL derivations); class-capable
accent 3,811 / hyphen 82,123 / apostrophe 121,177 / ligature 1,926 —
the detector overlap declared in the manifest for the contest's
conditioning.

## Gates

- **SR2 reading B, FINAL: 845,162 rows = 8.45% — PASS** (bar ≤ 50%,
  D-032 reading-B governance). The corpus arm breaks the all-zero
  stratum on the CEOL universe as it did on the EOL frame (8.63%).
- **SR3 does not fire**: every corpus feature separates GB-contained
  OCR corruptions from rare listed words — ratio 0.9883, log-volume
  0.8119, zipf-residual 0.7761, tokens-per-volume 0.6869, span-fill
  0.6821 (979 contained corruptions vs 5,269 bottom-quartile listed words).
