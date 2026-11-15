> **Where this stands.** This study has not been run. It was designed in August and September 2026, and this page presents it as a proposal. No person and no model has labeled a candidate under it, and no part of it has been registered. A small calibration pilot ran on September 1 and 2, 2026. It tested the search tooling, set no parameter, and is summarized below in aggregate only.

## The question

The study asks how reliably language models follow a written, evidence-bounded procedure for deciding whether a candidate string is attested in use, when the procedure's answer can differ from the dictionary listings the models may have learned. Every answer must rest on recorded evidence that anyone can check afterward.

Checking English words is the test case, not the subject. The study does not argue for or against its definition of an in-the-wild word as a standard for English words. The [definition](/definitions/in-the-wild/) is the procedure the models are asked to follow.

### What changed on September 24, 2026

The study began with a different question: can a language model determine that a term is in use outside the project's listed sources, under a precise definition, with the author labeling a designed sample as the comparison? On September 24, 2026, the question was restated as above:

- The subject became the models' conduct under the procedure. The definition became the test bed, and its merit as a standard is no longer at issue.
- The author's labeling became a bounded audit of a sample of the items the models judged. A second human rater and any comparison of human with model performance became optional.
- Saved evidence became the main condition. Search results are collected once, dated, and kept, and every model judges the same saved results. A smaller set of items is also run with live searches and reported separately.
- The comparison with the dictionaries and word lists became context, reported after the model results.
- Whether a model follows the procedure against what it may have learned is measured through a guess each model locks before it sees any evidence. No claim is made about any model's training data.

The design document had not been rewritten for the new question when the work paused, and the plan for the model runs had not been written. Where this page describes a part that predates the refocus, it says so.

## What would be measured

In the order the results would be reported:

1. **Protocol compliance.** Whether each model's verdict is consistent with its own recorded evidence. The procedure's mechanical steps are re-run over the model's own record. No human label is needed.
2. **Evidence correspondence.** Whether the quotes, locations, and claims a model records are in the saved evidence. The interpretive part, such as whether a page uses a string or only mentions it, is what the human audit checks.
3. **The controls.** How often a model attests a made-up string, and how often it misses a string known to be in use but absent from every listed source.
4. **Following the procedure against a prior.** Where a model's own pre-evidence guess and the procedure's answer disagree, whether the model follows the procedure.
5. **Agreement with the audit sample.** Chance-corrected agreement between each model and the audit labels, per answer class and per stratum. Errors that change a verdict are counted apart from errors that do not.
6. **Consistency and cost.** How stable each model's decisions are across repeats and item orders, and what each verdict costs.
7. **Agreement among models** on the same saved evidence.
8. **The listed sources, as context.** Where the dictionaries and word lists overlap, and how their listings relate to the audited outcomes. A source's not listing a candidate is not treated as evidence against the candidate.
9. **Scale.** Whether per-stratum results hold as the sample grows, at what measured cost, and whether a larger run is justified. This step has its own decision point.

## The design

### Population

The population is the candidate list as pinned for the study: {{s:frame_rows}} candidates. A candidate is a string the project's grammar admits; being a candidate says nothing about use. 3 groups are kept out of every draw:

- the {{s:frame_restricted}} candidates whose only listings are in licensed lists that cannot be redistributed;
- the {{s:development_in_frame}} candidates already shown in an earlier development deck, which was never labeled, because anything shown in development stays development data;
- the {{s:probe_words}} candidates named in {{s:probe_batteries}} small probe sets that test specific rules (typos, typo-like forms that became words, fictional vocabulary, and name collisions), whose expected outcomes were written in advance and which run outside the human audit.

The {{s:s_final}} candidates that end in an apostrophe and s are outside the first study, because a possessive's evidence depends on its base form and the project has not ruled how to treat that class. The study frame holds {{s:study_frame}} candidates.

### Sampling

Most of the frame is strings that no listed source carries: of the {{s:frame_plain}} plain single-token candidates, {{s:frame_plain_unlisted}} are listed by none of the {{s:detector_sets}} word sets the project derives from its sources. A uniform sample would be almost entirely that class, so the design stratifies, into {{s:strata}} strata: {{s:partition_strata}} that partition the frame and the rest drawn as slices. The strata are built on how many of the sets list a candidate, which kind of source lists a candidate that only 1 set lists, the string's shape (hyphenated, apostrophe forms, accented forms), and, for multiword candidates, which of the 2 multiword sources lists them.

Every draw ranks eligible candidates by a SHA-256 hash of a pre-declared seed, the stratum, and the string, so anyone can reproduce it; the study kit's sampler uses the same rule. Results are reported per stratum, never as an average over the universe. A projection to the whole frame is planned and labeled as a projection.

Before the refocus, the design proposed a development pool of {{s:pool_total}} stratified candidates ({{s:pool_single}} single-token and {{s:pool_spaced}} multiword). With the controls and {{s:repeats}} repeated items, the author would have labeled {{s:presentations}} presentations. Under the refocus, the full pool is no longer the human workload, and the size of the audit sample is open.

### Controls

2 kinds of control are mixed into the items, and no judge is told which items they are:

- **Made-up strings,** {{s:pseudo}} planned: {{s:pseudo_single}} single-token strings built by a published pseudoword method, and {{s:pseudo_spaced}} multiword strings built by rule. Each must pass the grammar, be absent from the whole candidate list and every source, and match nowhere in a pinned 2019 web corpus. The expected verdict is not found.
- **Strings known to be in use but absent from every source,** with a target of {{s:known_in_use}}, drawn from dated dictionary new-word announcements and dialect-society word votes. They measure how often the search misses a string that is there. Their known status rests on editors' judgment, which the design names as a proxy.

An attested made-up string is rechecked before it is scored: a genuine use by a real author is a collision and leaves the rate's denominator with its evidence kept. At the planned size, 0 false attestations among {{s:pseudo}} controls would put the exact 95% upper bound on the false-attestation rate at {{s:cp_upper_60}}, and a true rate of 5% would produce at least 1 event with probability {{s:power_60_5pct}}.

### Who or what judges

- **Model arms.** Each model gets the same instruction text, evidence format, and completion rule. Local open-weight models run first; models served through an interface are chosen later. Every model decision is repeated at least {{s:model_repeats}} times at a non-zero temperature, and the most common answer is taken. The share of repeats that agree is reported as consistency, never as confidence.
- **The audit sample.** The author labels a bounded, probability-sampled set of the items the models judged, on the same saved evidence, without seeing any model's answers. These are reference labels, not ground truth: the written definition is the instrument, and a person applying it can be wrong in the same recorded way a model can.
- **An optional second rater,** a person new to the project, trained only by the written rule book and a practice deck, labels a blinded sub-sample ({{s:rater_low}} to {{s:rater_high}} items in the design before the refocus), to test whether someone else can follow the rule.
- **Mechanical checks** re-run the procedure's deterministic steps over each model's own record.

### Evidence conditions

- **Saved evidence, the main condition.** Each item's evidence is collected once and dated: the result listings, page captures with hashes, ranks, timestamps, content dates, source identities, and any failures. Every model gets the same inputs. Source listings, sample roles, other judges' answers, and reference labels are withheld.
- **Live search, a secondary arm on a subset,** run end to end and never pooled with the saved-evidence results.
- **Closed-book,** the model's answer without evidence, kept as a baseline.

Before any evidence for an item is shown, the judge locks a 3-valued guess on whether the string has ever been used: attested, not attested, or unsure. For a model the guess is a separate call, and the call that judges the evidence never sees it. The study compares how often a verdict follows the procedure where the procedure and the guess disagree with how often it does where they agree. The analysis flags items for audit; on its own it proves nothing about training.

### Two rounds and the analysis

A development round may tune the rule book, the instrument, and the instruction text, with each change recorded. A confirmatory round uses fresh items, drawn by a mechanism that refuses any item from development, sized by a written rule over the development round, and runs exactly once under a written plan fixed before it starts.

The headline is chance-corrected agreement (Scott's π or Krippendorff's α, with Cohen's κ as a diagnostic), each with a bootstrap interval over items, per answer class and per stratum. Every rate is reported with its count, its denominator, its population, and its interval. Contamination is assumed, not prevented: the study assumes every model has seen the listed sources and never certifies a model clean.

## The instrument, in summary

The instrument's specification was accepted on September 7, 2026. Its parts:

1. **The search instrument.** For each candidate it generates the {{s:queries_per_candidate}} required queries by rule and logs them before any result appears; runs them on {{s:channels}} required channels, a general web search interface whose terms allow storing results and full-text search of digitized books; takes the first results per query, at most {{s:r_max}}; fetches every web result itself at a slow, fixed rate, keeping the raw bytes with a hash; checks that the exact string is on the page, never trusting the result listing; marks results from the excluded sources; reads each page's dates by several routes; and stops a channel at a bot challenge rather than answering it.
2. **The record layer:** the definition's 2 record types, field by field, with conformance tests on every record, and an append-only event log in which a correction is a new event, never an edit.
3. **The labeling app:** a private, local-first app that shows the candidate alone until the guess is locked, then the prepared evidence. It derives the verdict from the dispositions and refuses a confirmed verdict that contradicts its own record. Judges see the candidate and nothing else.
4. **The screening harness,** which generates the made-up controls and screens them against the pinned corpus.
5. **The re-measurement runner,** which re-runs the pilot's 2 calibration measurements on the real instrument.
6. **The model-arm harness,** to be specified with the plan for the model runs.

Building the instrument began in September 2026, and no study item has been labeled with it.

## The pilot

### What was piloted

Before setting 2 of the procedure's numbers, the design ran a calibration pilot on September 1 and 2, 2026, on a provisional web search backend with direct page retrieval:

- **Measurement A, for the search depth.** For strings known to be in use but absent from every source, can the procedure reach {{s:classes_k}} independent sources, and how deep in the results does that evidence sit?
- **Measurement B, for the overlap length.** On pairs of news pages known to be derived from one another or written independently, how often does the overlap rule, at lengths around its working value of {{s:l_incumbent}} tokens, call derivation wrongly?

Both measurements had refusal rules written in advance: if the evidence showed that the instrument, not the strings, limited the result, the rule would refuse to set a number.

### What came back

- **Measurement A** sampled {{s:pilot_words}} strings from a pool of {{s:pool_known}}. Its {{s:pilot_queries}} queries recorded {{s:pilot_rows}} result rows and {{s:pilot_attestations}} attestations; {{s:pilot_queries_short}} of the queries ran out below the planned depth of {{s:pilot_depth}}.
- Before any judgment, {{s:pilot_charset_excluded}} of the {{s:pilot_retrieved}} retrieved pages ({{s:pilot_charset_pct}}) were set aside because they declared no usable character set, and {{s:pilot_not_retrieved}} fetch attempts got no page.
- {{s:pilot_attained}} of the {{s:pilot_words}} strings reached {{s:classes_k}} independent sources ({{s:pilot_attained_pct}}; exact 95% interval {{s:pilot_attained_low}} to {{s:pilot_attained_high}}). The median string reached {{s:pilot_median}}.
- **Measurement B** covered {{s:pilot_topics}} dated news topics, {{s:pilot_pages}} captured pages, and {{s:pilot_pairs_considered}} candidate page pairs, of which {{s:pilot_pairs_qualified}} qualified against a target of {{s:pilot_pairs_target}}. It could not build its group of derived pairs: {{s:pilot_resolver_attempts}} searches for wire-service originals returned {{s:pilot_resolver_results}} results and none on a wire service's own site. The scored pairs produced no derivation call at any overlap length from {{s:l_low}} to {{s:l_high}} tokens, so no error rate could be estimated.
- Both refusal rules fired, and no number was set from the pilot. The run took {{s:pilot_hours}} hours against a {{s:pilot_bound}}-hour bound.

### What it taught

- **The backend, not the vocabulary, was the binding limit.** Both numbers moved to a re-measurement on the real instrument, and no second pilot runs on that backend.
- **The real instrument's requirements came from the pilot:** at least {{s:r_max}} results per query or the engine's own signal that the list ended; verification on the page, never the listing; reach to wire services' own sites; dates read from citation metadata as well as structured data; and tests on every record's format.
- **Rule-book rules came from a spot audit of the pilot:** type each occurrence on its own sentence, never by the page's opening or title; treat an undecidable occurrence in a title or tag as blocking a verdict when resolving it would change the answer; match hyphenated strings on whole tokens only; and give each floor of the stricter test a "not applicable" value when no independent source was counted.
- **Where an evidence window is centered matters.** The same page pair can fall on either side of the overlap line depending on which occurrence anchors the window, so the scored window is the first occurrence's.

The re-measurement has not run. Each refusal names a repair to the instrument, and the measurement is re-run after the repair; the rules are never adjusted to pass.

## Open questions

- **The models:** which ones, chosen by what criteria, beyond local open-weight models first.
- **The arms:** the closed-book, saved-evidence, and live-search conditions, and the size of the live subset.
- **The audit sample's size,** set by the precision needed on agreement.
- **The endpoints:** how errors are counted per step, per item, and per final verdict, and how refusals, timeouts, malformed output, and exhausted budgets enter the denominators.
- **The 2 unset numbers,** the search depth and the overlap length, which wait on the re-measurement.
- **The bar for a larger run:** what a sufficiently low, audited error rate means as a number, stated before any projection.
- **Rules not yet hardened:** whether the multiword unit test ever gates anything; a policy for vocabulary used only inside fiction; and the threshold for the language flag, which has no measured basis.

### Limits stated in advance

- Not found is a statement about the search, never about the string.
- Web text after 2021 may be machine-generated, and the procedure has no test for authorship.
- 1 planted, archived post outside the sources is enough to pass the once-attested test. The corroborated test costs more to fake, but patient planting across several sites over a year remains possible.
- The judgment rules (use or mention, names, page blocks, language, and the multiword unit) are calls. The study measures how reliably they are made; it does not assume it.
