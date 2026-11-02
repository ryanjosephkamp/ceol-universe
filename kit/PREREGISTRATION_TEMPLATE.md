# Preregistration template

> **This template registers nothing.** It is a form to fill in. Nothing in it files, uploads, or registers anything, and the CEOL Universe project has not registered a study with it. A preregistration exists only after a researcher files the completed form with a registry or an archive of their own choosing and receives a time-stamped record that cannot be changed. Until then, a filled copy is a plan.

How to use it: copy this file, fill each `[bracketed field]`, delete the guidance lines you do not need, and keep the headings. Fix the plan before you draw the sample or look at any label. Write about candidates and a stated definition, never about which strings "are words": a row of the CEOL Universe is a candidate string, and a label is a judgment under a definition.

| Field | Value |
|---|---|
| Status | not filed |
| Filed with | [registry or archive] |
| Filing date | [date] |
| Record identifier | [identifier] |
| SHA-256 of the file as filed | [hash] |

## 1. Study

| Field | Value |
|---|---|
| Title | [title] |
| Researchers and contact | [names, addresses] |
| Funding and conflicts of interest | [statement] |
| Plan version and date | [version, date] |

## 2. Question

- **Primary question:** [one sentence, about candidates and a stated definition]
- **Secondary questions:** [one sentence each, or none]

## 3. Hypotheses

Mark each as confirmatory (tested by the plan in §8) or exploratory (reported as such).

| # | Hypothesis | Direction | Test | What would count against it |
|---|---|---|---|---|
| H1 | [statement] | [direction] | [test or estimate] | [result] |
| H2 | [statement] | [direction] | [test or estimate] | [result] |

## 4. The definition under test

| Field | Value |
|---|---|
| Definition | [statement, or the codebook's §2] |
| Codebook | [version, and the sha256 of the file] |
| Who fixed it, and when | [name, date] |

## 5. Data

| Field | Value |
|---|---|
| Dataset | `ryanjosephkamp/ceol-universe` |
| Version | [version, such as v1.0] |
| Config | [config] |
| File and its sha256 | [path, hash; compare the hash with the card's table of files] |
| Date the file was read | [date] |
| Kit version | [the value of `ceolkit.__version__`] |
| Loading call | [code, such as `load("universe", "v1.0", source=...)`] |
| The frame | [the predicate that defines the rows sampled from, as code, and the row count the code prints] |
| Columns used as covariates | [columns; a -1 is "cannot hold" and a null is "not measured", and neither is recoded as 0] |

## 6. Sampling

The sampler ranks the rows of each stratum by the hex digest of `sha256(f"{seed}:{stratum}:{word}")`, in ascending order, and takes the first N of each. The sample is a function of the rows, the strata, the seed, and N.

| Field | Value |
|---|---|
| Seed | [a string; written here before the sample is drawn; say how it was chosen] |
| Stratum | [a name from `ceolkit.strata`, a column, or a function; paste its definition] |
| N for each stratum | [number, or a count for each label] |
| Why this N | [precision wanted, such as the half-width of an interval for a proportion, and the arithmetic] |
| Draw code | [paste] |
| Strata with fewer rows than N | [what happens: take all of them and report it, or drop the stratum] |
| Pilot or practice set | [its seed, its size, and how its ids are removed from the main frame] |
| Annotation order | [the order seed for each annotator] |
| Weights | [for each stratum, `available / selected` from the manifest] |
| Redraws | none; the sample is drawn once and not redrawn after any label is seen |

**The sampler's manifest** (paste it exactly as the sampler wrote it; it holds the rule, the seed, the stratum and its definition, N, the input row count, the rows available and selected in each stratum, and `selected_ids_sha256`):

```json
[paste the manifest here]
```

## 7. Labels

| Field | Value |
|---|---|
| Label set | [from the codebook's §4] |
| Annotators | [how many, who, what training] |
| What annotators see | [the codebook's §3; state any difference] |
| Independence and blinding | [what annotators may not see or discuss] |
| Overlap | [which candidates get more than 1 annotator, and how they are chosen] |
| Agreement coefficient | [Cohen's kappa, Fleiss' kappa, or Krippendorff's alpha] |
| Agreement threshold | [value, and the action if it is not met] |
| Adjudication | [who, and how] |
| `not_enough_information` | [open-world or closed-world rule; how the primary analysis treats it] |
| Any model that labels | [name, version, date, prompt; or none] |

## 8. Analysis

| Field | Value |
|---|---|
| Primary estimand | [such as the weighted share of candidates labeled `meets`, overall and in each stratum] |
| Estimator and weights | [formula] |
| Intervals | [method; for a bootstrap, the resampling unit (candidates within strata), the number of resamples, and the seed] |
| Secondary analyses | [what, with which covariates, with which model] |
| Several tests | [how multiple comparisons are handled] |
| `not_enough_information` | [primary treatment, and the sensitivity analyses: left out, and merged into each other label] |
| If annotators disagree | [the label used, and the analysis of agreement] |
| If agreement is below the threshold | [what is reported and what is not claimed] |
| Software and versions | [Python, `pyarrow`, `numpy`, `pandas`, the kit] |
| Analysis code | [where it is kept, and its commit or hash when this plan is filed] |

Decision rules:

| Result | Conclusion |
|---|---|
| [result] | [conclusion] |

## 9. Exclusions and deviations

| Field | Value |
|---|---|
| Candidates excluded, and why | [criteria written before labeling; for example, the pilot's ids] |
| Rows with a null or -1 in a covariate | [how handled; a null is "not measured" and a -1 is "cannot hold", so neither is a 0] |
| Annotators or labels excluded | [criteria, such as a failed quality check] |
| Missing labels | [handling] |
| Deviations from this plan | Each is reported with its reason and date, next to this plan, and no result is described as confirmatory if its analysis changed after labels were seen |

## 10. Contamination

Follow [`CONTAMINATION.md`](CONTAMINATION.md).

| Field | Value |
|---|---|
| Models used anywhere (labeling, filtering, analysis, or the object of study) | [name, version, training cutoff if known; or none] |
| `model_or_engine` | [rows kept, left out, or stratified, and why] |
| Strings shown to a model | [which, through what service, under what retention terms] |
| Canary check | [planned or not; how] |
| Candidates from the repository's pages | [whether the vetted example list is excluded from probes] |

## 11. Materials and timeline

| Field | Value |
|---|---|
| Timeline | [dates for pilot, freeze, labeling, analysis] |
| Where the manifest, the labels, and the code are kept | [places] |
| What is released, and when | [and the effect on later tests of models on the same candidates] |

## 12. Ethics and approvals

[approvals, consent for annotators, compensation, or "not applicable" with the reason]

## 13. Before you file

- [ ] Every bracketed field is filled or deleted on purpose.
- [ ] The seed and N are written in §6 and were fixed before the draw.
- [ ] The manifest is pasted, and its `selected_ids_sha256` matches the ids file.
- [ ] The codebook is frozen, and its version and hash are in §4.
- [ ] You filed this form yourself, with a registry or an archive you chose, and wrote the record's identifier at the top.

Filing is your act. This kit does not file, upload, or register anything.
