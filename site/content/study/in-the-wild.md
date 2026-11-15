> **Where this sits.** This is the definition written for the [proposed study](/research/study/), which has not been run. It says what evidence a recorded search must find before a candidate counts as used "in the wild": in use outside the project's own sources. Every example on this page is invented. "X", "Y", and "Z" stand for hypothetical strings, not candidates from the list, and the pages described are imaginary.

## In brief

A candidate is in the wild when a complete, recorded search finds it used for its meaning, in English running text, on a page outside the project's own sources, with a saved copy of the page and a date.

1 such use passes the first test. A second, stricter test needs uses from at least {{s:classes_k}} independent sources whose dates span at least {{s:span_days}} days.

Each test returns 1 of 3 answers: **attested**, **not found**, or **unsure**. Every answer is dated, and every answer can be checked against the record without searching again.

## The 2 tests

- **The once-attested test.** At least 1 qualifying use exists, dated on or before the date of the search. Once audited, the answer stands; only a correction of the project's own mistake reverses it.
- **The corroborated test.** The qualifying uses come from at least {{s:classes_k}} independent sources, their dates span at least {{s:span_days}} days, and 3 further floors are met. Each run of this test is a dated measurement.

## Before any condition: a complete search

The definition is tied to a written search procedure, the same for a person and for a model. For each candidate:

1. The queries are fixed by rule before any result is read: the exact string in quotes, and the bare string (for a multiword candidate, the phrase without quotes).
2. They run on fixed search channels.
3. The first R results of each query on each channel are reviewed. R is set in advance.
4. Every reviewed result gets exactly 1 disposition: an attestation, an excluded source, content copied from a source, a mention, an undecidable occurrence, unrelated, or unreachable.
5. Everything is recorded: the queries, how many results existed, a capture of each result list, and each result's disposition.

If any reviewed result lacks a disposition, there is no answer, only a record of an incomplete run.

*Example.* A search for string X returns 20 results on a channel, and 19 have dispositions. X gets no answer until the 20th has one, even if the first result already shows a clear use.

## The conditions, in order

The definition states the once-attested test's conditions as: a use rather than a mention, outside the sources, durable, and dated. This page takes them in a reading order, starting with the exact-string check the search procedure requires of every attestation, and then adds what the corroborated test needs.

### 1. The exact string is on the page

The string must be present in the page's own text, never only in the search engine's listing. Matching is on whole tokens: the candidate's full sequence of tokens must equal a sequence of whole tokens on the page, after the project's standard text normalization (for example, lowercase, and a curly apostrophe read as a straight one). A spelling, spacing, or hyphenation variant counts for the variant, never for the candidate.

*Examples.* Take a hypothetical hyphenated candidate X-Y.

- A page that writes "X-Y-free" contains the longer token X-Y-free, so it does not count for X-Y.
- A page that writes "X Y", with a space, is evidence for a different candidate, X Y.
- A listing whose snippet shows X-Y, for a page whose text does not contain it, is unrelated.

### 2. The page is outside the exclusion set

The exclusion set is the project's own sources: the dictionaries and word lists whose listings the project records for every candidate. They cannot vouch for themselves. The set is finite, named, and dated (its table is dated August 28, 2026), and it has 3 layers.

**Layer 1: the {{s:e_sources}} pinned sources,** each fixed by a file hash. By kind:

- an expert semantic lexicon;
- a community-edited dictionary, counted twice: its full list of page titles, and its pages with an English section;
- a 1934 dictionary word list distributed with some operating systems;
- spell-checker dictionaries for 4 varieties of English, and the word-list collection they are generated from;
- 4 word lists used in word games, 2 of them committee-maintained tournament lexicons;
- 2 frequency resources: a word-frequency library and a count of single words in scanned books.

**Layer 2: the {{s:e_sets}} word sets the project derives from those sources.** These include a supplement of hyphenated compounds distributed with the 1934 list. A page that reproduces a set's entries beyond the bare string, such as a definition copied word for word or a run of consecutive list entries, counts as that source. (The length of run that counts is not yet set.)

**Layer 3: each source's own hosting sites,** {{s:e_hosting}} entries across {{s:e_hosting_sources}} sources. A live site counts as the same source as its pinned file. The 1934 list has no website. The book-count resource's own search interface is excluded, but full-text search of the books themselves is an allowed channel.

**What is not in the set:**

- copies and derivatives of the sources elsewhere on the web;
- the larger dictionaries the sources draw on;
- sister projects run by the same organization as a source.

Copies are left out because they cannot be listed reliably. In a measurement on August 28, 2026, searches for {{s:mirror_words}} listed candidates returned {{s:mirror_results}} results in all. {{s:mirror_derived}} of them ({{s:mirror_derived_pct}}) were the sources' own pages or copies of them, and for {{s:mirror_top}} of the {{s:mirror_words}} candidates the top result was one. Condition 3 below treats a dictionary-style page as a mention wherever it is, and the independence rules of condition 6 handle copies of running text.

**How it is applied.** The check runs when the answer is decided, on the results the search actually returned. An excluded result stays in the record, marked and shown collapsed, so an auditor can see what was set aside and why. It is excluded from the counts, never hidden.

*Example.* Take a string X that appears only in a word-game list. A search returns the list's own hosting page (excluded by layer 3), a dictionary site's entry for X (not excluded, but a dictionary-style block, so a mention), and a puzzle-solver page that lists X among other words (also a mention). Nothing qualifies, and both tests return not found. A list can never vouch for a list.

### 3. The occurrence is a use, not a mention

A **use** puts the string to work for its meaning: the sentence is about something other than the word. A **mention** talks about the word itself: it quotes, defines, spells, or discusses it. Only uses count. Every use must carry a 1-line note of the meaning it deploys, so an auditor can check the call. Any English sense of the string counts.

The call is made in stages, and always on the block of the page that holds the occurrence.

**Stage 1: the block.** A block is the part of the page that holds the occurrence: an article body, a sidebar, a comment, a dictionary entry. A block that presents words as words is dictionary-style: definition entries, thesaurus and synonym lists, word lists, and spelling, solver, or anagram tools. Every occurrence in a dictionary-style block is a mention, whatever site it is on. A block that cannot be told apart or typed is unresolved, and its occurrences are unsure.

*Example.* A news article about a harbor has a word-of-the-day sidebar that defines X. The sidebar is dictionary-style, so its X is a mention. The article body is typed on its own.

**Stage 2: each occurrence, on its own sentence.** Every occurrence is typed by its own sentence, never by the page's title or opening.

*Examples.* A page reads, "Is X a word? It means a small fishing boat." That is a mention. A page reads, "We pulled the X up onto the beach before the storm." That is a use, with the meaning noted as a small fishing boat. A page that opens by discussing the word X and later says "My neighbor's X needs a new coat of paint" contributes a use from the later sentence.

Stage 2 has written sub-rules for the hard cases:

- **Names.** Text that uses a name for the thing it names, and says something about that thing, is a use: "X, the river town, floods most springs." A string that only brands something, with nothing said about it under that name, is an arbitrary label and counts as unrelated: "Introducing X™, our new font." Cases on the line are unsure, with the signs recorded.
- **No sentence.** An occurrence only in a page title, a tag, a link, a label, or a web address, with no sentence that uses it, is unsure. It blocks an answer when resolving it as a use would change the answer.
- **Language.** The sentence must be English running text. X inside a French sentence does not count. A fixed phrase of foreign origin used inside an English sentence does count.
- **Slips.** If the most plausible reading of the page is that the writer meant a different string, the occurrence is a production error, neither use nor mention, and the intended string is recorded. *Example:* "Please X the form and return it by Friday," on a page whose next line corrects it to Z. Cases that could be a slip or a deliberate new form are unsure.

**Stage 3: a lone definition.** A page that is not dictionary-style overall, but whose only appearance of the string is a definition, contributes a mention. *Example:* a cooking blog whose only X is a glossary line, "X: a thin wooden spatula."

The study also records, without letting it decide anything, whether every use of a string sits inside discussion of a single fictional world.

### 4. The evidence is durable

Every attestation needs a saved copy: either a public web-archive capture, or a complete local copy of the page identified by its hash. An attestation with neither is unresolved and cannot qualify, because no one could re-check it.

*Example.* A forum post uses X, but the page was fetched incompletely and no archive holds it. The post is recorded and cannot count.

### 5. The evidence is dated

Every attestation carries a content date and a confidence:

- **corroborated:** the page's own date is confirmed by an archive capture dated 0 to {{s:window_days}} days after it;
- **stated:** the page's own date, unconfirmed;
- **capture-only:** no stated date; a capture shows only that the page existed by then.

Every route to a date is read and recorded, and disagreements between routes are recorded. The content date must fall on or before the date of the search. Later evidence belongs to a later search.

*Example.* A page states March 3, 2021, and an archive capture is dated April 20, 2021, 48 days later: corroborated. A capture dated before the page's stated date confirms nothing; it is recorded as a disagreement.

**The once-attested test passes** on 1 attestation that meets conditions 1 to 5, on a complete record.

### 6. Independent sources

For the corroborated test, qualifying attestations are grouped into independence classes. 2 attestations are linked when either test finds a link:

- **Same origin:** the same author or account. A shared website links them only when the site has 1 publisher, such as a newsroom, a company, or a personal blog. On a forum or social platform, the account is the origin.
- **Derivation:** one page copies the other, or both copy a common source. Signs are syndication credits and reprint notices, quotation marks with an attribution, or a long run of words shared between the 2 pages, read over the sentence that holds the occurrence and the sentences on either side. The run length is set at {{s:l_incumbent}} tokens as a working value whose error rates have not yet been measured.

Links carry through: if A links to B and B links to C, all 3 form 1 class. A further test removes any page whose content reproduces a source's data.

The burden is on the answer. 2 attestations count as separate classes only when both tests were run between them and found no link. When a test cannot be run, for example because a page shows no byline, the procedure works out the fewest and the most classes the record allows, and gives an answer only if it is the same across that whole range.

*Examples.* A wire story that uses X, reprinted on 40 sites, is 1 class. 1 writer who uses X on a personal blog and again in a forum post signed with the same name is 1 class. A blog post that quotes a magazine's sentence using X, when the magazine page is also in the record, forms 1 class with it.

### 7. At least {{s:classes_k}} classes over at least {{s:span_days}} days

The corroborated test needs at least {{s:classes_k}} independence classes, and the content dates of the counted uses must span at least {{s:span_days}} days, latest minus earliest, counted in days. Exactly {{s:classes_k}} classes and exactly {{s:span_days}} days both pass. The first study adds no requirement that the evidence be recent.

*Example.* X has 3 independent classes dated January 10, 2019, June 2, 2019, and January 10, 2020. The span is exactly 365 days, so it passes.

### 8. The 3 floors

The corroborated test also checks 3 floors:

- **Platform diversity:** the counted classes are not all on 1 website domain. 3 accounts on 1 forum site do not suffice.
- **An archived class:** at least 1 counted class holds an attestation with a public archive capture.
- **Date confidence:** both ends of the span are better than capture-only.

Each floor is met, not met, unknown (an archive lookup failed), or not applicable (no class was counted).

## How the answer is assigned

On a complete record, the first rule that matches decides:

1. **Attested:** the test's criterion is met on resolved evidence. For the corroborated test, that includes every floor being met.
2. **Unsure:** something unresolved could change the answer (an undecidable occurrence, an untyped block, an unresolved link between sources, or a floor whose archive lookup failed), or, for the corroborated test, the record holds 1 or 2 classes.
3. **Not found:** everything else. That includes no qualifying evidence, evidence that is all mentions, and, for the corroborated test, enough classes whose dates fail the span, or a floor that is not met on resolved evidence.

An incomplete search gets no answer at all. The reason for every answer is shown and kept on the record.

*Examples.* X has 1 qualifying use: the once-attested test returns attested, and the corroborated test returns unsure, with 1 class. Y has 3 independent classes spanning 2 years, all on 1 forum domain: the corroborated test returns not found, with the platform-diversity floor named as the reason. Z appears only in dictionary-style blocks: both tests return not found.

## What "not found" means

Not found is a statement about the search, never a claim that a string is unused. The record shows what was found. Under the project's one-way rule, a candidate that is not found waits and is never removed; a later, better search may find it.

## Multiword candidates: a separate question

For a candidate that contains a space, a separate unit test asks whether it works as a single word: yes, no, or unsure. It is decided from the recorded sentences: is the meaning in at least 1 attested use more than the sum of its parts? 2 further signs, whether it fills 1 grammatical slot and whether its form is fixed, are recorded but never decide. With no qualifying sentence, the answer is unsure. In the first study, nothing depends on this test.

*Example.* A hypothetical X Y, attested in sentences where it carries a meaning that neither X nor Y carries on its own, would be a unit. A hypothetical pairing used only as the plain sum of its 2 words would not.

## Why a search and not a fixed corpus

The definition rests on retrieval, not on counts in a fixed text collection. A fixed corpus is reproducible to the byte, but it cannot see anything written after its snapshot, it is expected (though not yet measured) to contain copies of the sources themselves, and its cleaning steps quietly decide what an occurrence is. A pinned 2019 web corpus is kept beside the definition as a cross-check. A disagreement between the 2 is a flag to examine, never an error in either.

## Known limits

- **Not found is relative to the search.** Pages decay, and engines change. The answer is frozen at the date of the search, and a new search is a new, dated measurement.
- **Machine-written text.** Web text after 2021 may be machine-generated. The procedure has no test for authorship and claims none.
- **Planting.** 1 planted, archived post outside the sources passes the once-attested test. The corroborated test and its floors raise the cost of faking, but patient planting across several sites over a year is not ruled out.
- **Judgment calls.** Use or mention, the name rule, page blocks, language, and the multiword unit test are calls a person or a model makes. The study measures how reliably they are made, task by task.
- **The numbers are conventions.** 3 classes over 1 year follows the one public, numeric attestation rule the project located, whose own community calls its numbers somewhat arbitrary. That rule belongs to one of the project's own sources, so the definition borrows its structure, not its authority. The study reports how its answers change at 2 and 4 classes.
