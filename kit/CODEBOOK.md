# Labeling codebook (template)

A template for annotators who label sampled candidates against a definition the researcher chooses. Copy it, fill every `[bracketed field]`, freeze it before the main labeling starts, and give each annotator the frozen copy.

The dataset holds no labels and supplies no definition. A row of the CEOL Universe is a candidate string with its provenance. A label made with this codebook is a judgment about a candidate under the definition in §2, and it is reported as that.

| Field | Value |
|---|---|
| Codebook version | [version] |
| Frozen on | [date] |
| Researcher | [name or contact] |
| Dataset version and sample manifest | [dataset version, and the `selected_ids_sha256` of the sampler's manifest] |

## 1. Who this is for

Annotators label candidates one at a time. The researcher uses the labels to answer the question in the preregistration. This codebook tells annotators what to decide, how to decide it, and what to write down, so that 2 annotators facing the same candidate make the same call for the same reason.

## 2. The definition under test

Annotators apply this definition and no other. They do not apply their own sense of what a word is.

| Part | Text |
|---|---|
| Name of the definition | [name] |
| Statement | [1 to 3 sentences] |
| A candidate meets it when | [criteria, numbered] |
| A candidate does not meet it when | [criteria, numbered] |
| Evidence rule | [open-world or closed-world, as §7 defines them] |
| Allowed sources | [the dictionaries, corpora, and reference works an annotator may consult, with versions] |
| Time for each candidate | [limit] |

## 3. What the annotator sees

The unit is 1 candidate: its `id` and its `word`. The annotation sheet holds those 2 columns and empty columns for the label and the evidence.

The sheet leaves out everything else the dataset records about the candidate: the stratum and rank it was drawn under, the evidence columns (which lists hold it, with their 1, 0, -1, and null), `provenance_class`, `model_or_engine`, and every other annotator's label. An annotator who sees that a candidate is listed by 3 dictionaries is no longer judging the candidate alone. If a study wants annotators to see list membership, that is a different design: the membership is then a treatment, and the preregistration says so.

## 4. The label set

Each candidate gets exactly 1 label.

| Label | Meaning |
|---|---|
| `meets` | on the evidence recorded, the candidate meets the definition in §2 |
| `does_not_meet` | on the evidence recorded, the candidate does not meet it |
| `not_enough_information` | the allowed sources and the time limit do not settle it (§7) |

There is no "maybe", and no label is split or partial. The researcher may add labels before the main labeling starts, and each added label needs a decision rule in §5.

## 5. Decision rules

### 5.1 General rules

1. Read the whole definition before the first candidate, and again after each break.
2. Decide on the candidate as a string under the definition. A list holding the string is evidence, not the decision. A list not holding it is not evidence against it, unless §2 sets a closed-world rule.
3. Work alone. Do not ask another annotator, and do not look at their labels, until the researcher opens adjudication.
4. Use only the allowed sources in §2. Record what you used (§6).
5. Do not change a label after submitting it. If you find an error, tell the researcher; the correction is logged, not overwritten.
6. When you cannot apply the definition because it is unclear, write `not_enough_information` with the reason `definition_gap`, and tell the researcher. Do not invent a rule.

### 5.2 Kinds of candidate to decide in advance

The dataset holds candidates of several kinds, and a definition rarely settles them all. Fill in what the definition does with each, before labeling starts.

| Kind of candidate | Rule |
|---|---|
| a hyphenated compound | [rule] |
| a string with an accented letter | [rule] |
| a spelling with a diaeresis or a ligature | [rule] |
| a contraction | [rule] |
| another apostrophe form, such as a possessive | [rule] |
| a multiword term | [rule] |
| an inflected form of another candidate | [rule] |
| an abbreviation or an acronym | [rule] |
| a proper noun or a name | [rule] |
| a spelling variety (US, GB, or another) | [rule] |
| a dialect, slang, archaic, or technical term | [rule] |
| a string from another language | [rule] |
| a string that looks like a fragment, a typo, or a machine-made form | [rule] |

The dataset records no part of speech, lemma, or variety label, so the annotator decides these from the allowed sources.

### 5.3 Order of checks

If the definition has several criteria, say in which order to apply them and what each outcome gives.

1. [check 1, and its outcomes]
2. [check 2, and its outcomes]
3. [check 3, and its outcomes]

## 6. Recording evidence

Every label carries its evidence, including `not_enough_information` (what you looked at and did not find).

| Column | What to write |
|---|---|
| `id` | already on the sheet |
| `annotator_id` | your code, not your name |
| `label` | 1 label from §4 |
| `evidence_type` | `own_knowledge` (no lookup), `dictionary`, `corpus`, `reference_work`, `usage` (a use of the string in a named text), or `none` (nothing found). The researcher may change this list before labeling starts |
| `evidence_ref` | what you consulted, so that another person can find the same thing: the source's name, its version or the date you accessed it, and the entry, the query, or the address. Quote no more than a short phrase; give the location instead of copying a passage |
| `note` | 1 sentence of reasons, and a reason code for `not_enough_information` (§7) |
| `confidence` | optional: 1 (low), 2, or 3 (high). It is not used in the analysis unless the preregistration says so |
| `date` | the date you made the label, as year-month-day |

A `does_not_meet` label needs an `evidence_ref` that says what you checked, or the words `closed-world rule` if §2 sets one.

If the protocol lets annotators consult a language model, the model counts as a source: write `model_output` in `evidence_type`, and record the model's name, its version, the date, and the question you asked. The researcher reads [`CONTAMINATION.md`](CONTAMINATION.md) before allowing it.

## 7. "Not enough information"

`not_enough_information` means that, with the allowed sources and within the time limit, the evidence neither shows that the candidate meets the definition nor shows that it does not. It is a result about the evidence, not a label for a hard case and not a default.

Use it when:

- you found no usable evidence in the allowed sources within the time limit (reason code `no_evidence`);
- the evidence you found conflicts, and the definition does not say which to follow (reason code `conflict`);
- the definition does not decide the candidate's kind (reason code `definition_gap`).

Do not use it when you found evidence and are only unsure. Decide, and write a low `confidence`.

**Open-world and closed-world rules.** Under an open-world rule, failing to find evidence that a candidate meets the definition gives `not_enough_information`. Under a closed-world rule, failing to find it in the named sources gives `does_not_meet`. The definition in §2 says which applies. The choice changes the labels, so it belongs in the preregistration.

**What the researcher does with it.**

- Report how many candidates got this label, overall and in each stratum, and the share of each reason code.
- Analyze it as its own category. Also run the analysis with those candidates left out and with them merged into each other label, as the preregistration plans. Do not drop them without saying so.
- A high rate means the definition or the sources are inadequate. Fix that in the pilot, not after the main labeling.

## 8. Procedure

1. **Pilot.** Draw a practice set from the same frame with a different seed, and remove its ids from the frame of the main sample, so that labels made under an older codebook never enter the main sample. Annotators label it, the researcher compares their labels, and the rules are revised. If the pilot is not meant to change anything, it may instead be the head of the main sample: the sampler's smaller sample is the first rows of a larger one.
2. **Freeze.** Fix the codebook version and date in the table at the top. Changes after this point go in §10 and may require relabeling.
3. **Order.** Give each annotator their own order, shuffled by a seed that includes their code (`02_draw_a_labeling_sample.ipynb` shows how).
4. **Overlap.** At least 2 annotators label every candidate in the overlap set: [all of the sample, or a subsample the researcher draws with a recorded seed].
5. **Repeats.** Show [a share of] the candidates a second time, unmarked, to the same annotator, to measure their consistency.
6. **Adjudication.** Where labels differ, [a third annotator, or a discussion] settles the final label. Keep every original label and the final one. Agreement is computed on the original labels, never on adjudicated ones.

## 9. Agreement

Agreement says how much the labels depend on the annotators. Plan it before labeling and report it with the results.

1. **What to report.** The number of candidates and annotators in the overlap; raw percent agreement; 1 chance-corrected coefficient chosen in advance; its confidence interval; the confusion matrix between annotators; the share of each label; and agreement for each stratum.
2. **Which coefficient.** Cohen's kappa for 2 annotators with no missing labels; Fleiss' kappa for a fixed number of more than 2; Krippendorff's alpha (nominal) for any number of annotators and for missing labels. Name it in the preregistration.
3. **Intervals.** Resample candidates with replacement, within strata when the sample is stratified, and report the interval of the coefficient over the resamples.
4. **With and without `not_enough_information`.** Report agreement with it as a label and with those candidates removed.
5. **Reading the number.** A chance-corrected coefficient falls when one label is rare, even when raw agreement is high, so report the prevalence of each label beside it. Cut-offs are conventions. One common convention (Krippendorff, *Content Analysis: An Introduction to Its Methodology*) reads an alpha of 0.800 or more as reliable and 0.667 to 0.800 as fit only for tentative conclusions. Set your threshold in the preregistration before labeling.
6. **If the threshold is not met.** Say what you will do: retrain, revise the codebook and relabel, or report the result as unreliable. Do not drop the candidates the annotators disagreed on.
7. **A model that labels** is an annotator. Compute its agreement with the humans the same way, and report its name, version, date, and the prompt.

## 10. Changes to this codebook

| Date | Version | What changed, and why | Candidates relabeled |
|---|---|---|---|
| [date] | [version] | [change] | [count or none] |

## 11. The annotation sheet

One row for each candidate for each annotator.

| Column | Filled by |
|---|---|
| `id`, `word` | the sampler (`sample[["id", "word"]]`) |
| `label`, `evidence_type`, `evidence_ref`, `note`, `confidence`, `date` | the annotator |
| `annotator_id` | the annotator, or the file name |

## 12. Instructions to annotators (copy this block)

> You will see a list of candidate strings. For each, decide whether it meets the definition in §2 of this codebook, and choose `meets`, `does_not_meet`, or `not_enough_information`. Use only the sources the codebook allows. For every candidate, write down what you consulted and one sentence of reasons. Work alone, and do not change a label once you have submitted it. If the definition does not tell you what to do, choose `not_enough_information`, write `definition_gap`, and tell the researcher. A candidate being listed somewhere is evidence, not an answer; a candidate being absent from a list is not evidence against it unless the codebook says so.
