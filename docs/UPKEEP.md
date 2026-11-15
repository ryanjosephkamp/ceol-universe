# The CEOL Universe: the upkeep policy

**Adopted on October 18, 2026.** These are the rules for keeping the universe over time: what a version is, when a row may leave, how a source is added, removed, or restored, how often a checkpoint runs, and what is automated. They are written for a maintainer who has none of the conversations behind them. A later decision changes them; this page is not edited in place.

**Status: a design, partly built.** The release build, the withholding, the figure check, and the generated documents exist and are deterministic. The checkpoint command, the source registry file, and the listing-history table described below are planned and not implemented yet; where a section says what a checkpoint does, it describes what it will do.

## 1. Definitions

- **The universe:** the inventory of every candidate string ever admitted, with its evidence. Its private record holds every row; a public version is a projection of it.
- **A pin:** a fixed, hashed build of the universe that later steps read.
- **A version:** a released projection of a pin, such as v2.1. A released version never changes (rule 4). It may be withdrawn, never edited (§5.2).
- **A checkpoint:** the run that measures every source again and builds a new pin and version.
- **A source:** anything a row's evidence comes from. Each source has 1 kind:
  - a **panel source**, a whole, versioned word list measured against every row and published as a column;
  - a **comparison resource**, measured against every row, of which only counts are published, because its terms allow no more;
  - a **corpus**, whose values are features and which never admits a string;
  - a **screen**, a signal that is not containment (such as a title in any language's Wiktionary).
- **A listing:** the fact that a source, at a version, lists a string.
- **Withheld:** a source whose columns and labels a public version drops, while its rows can still ship.
- **Restricted:** a row that only withheld sources attest, which no public version carries.
- **A derived dataset:** a dataset built from a universe version under its own rule, with its own name and card.

## 2. The 3 principles

1. **The universe only grows.** A string admitted once stays in every later pin. The 1 exception is a string admitted by a build error (§3), which leaves the pin and stays in the private record of errors.
2. **Every listing is dated, so it never becomes false.** The record says "source S at version V lists this string", which stays true when S changes.
3. **A differently shaped universe is a derived dataset.** A stricter definition, a curated list, or a validated subset is built from a version and named on its own. The universe is never reshaped to suit 1 use.

## 3. When a row may leave a public version

2 events are kept apart:

- **A source stops listing a string.** The row stays, and that source's listing closes (§4). Sources do this often: in recent versions the tournament lists, Open English WordNet, the English Speller Database, the LibreOffice dictionaries, and FreeBSD's copy of web2 all removed entries.
- **A row leaves a public version.** This needs 1 of the 3 reasons below.

A row leaves a public version for exactly 3 reasons:

1. **A build error:** a string the grammar does not produce, or a pipeline fault that admitted it. The fix is a new version.
2. **A legal requirement:** a withholding that makes the row restricted, or a takedown (§7).
3. **The maintainer's ruling,** recorded with its reason in the project's decision record.

A source dropping a string is never a reason. A row that leaves stays in the private record with the version it left, the reason, and the entry or request behind it. The change log of the new version counts the rows that left, by reason. **It never lists them, and never lists their ids:** a row's `id` is a prefix of the sha256 of its string, and anyone with a word list can reverse a hash of a short string. A notice to holders of copies uses counts, or mixes the targets into a larger pool of ids so that none is singled out.

## 4. Listings over time

- **The columns of a version** show each source at the version that checkpoint pinned. An analysis of a version is therefore accurate for that version.
- **Each pinned source version records 3 things:** the source's own version string, verbatim (a date, an edition name, a commit, or the file's sha256 where it has none); the source's release date; and the date the project retrieved it.
- **The listing history** (planned) is an append-only table in long form: 1 row per string, source, source version, and event (opened, closed). From it come "first observed" and "last observed" per row and source. They are observations at pinned versions only: a yearly checkpoint skips the versions in between, so a string a source added and removed between 2 checkpoints is never seen. "Ever observed" and "listed now" are both available, and a source's churn is data for the analysis.
- **A change in how a source is extracted** is its own event class. A new extraction can open or close listings without the source changing, so the migration is verified before any listing closes. The English Wiktionary XML dumps the pipeline reads are scheduled to end in January 2027, and their replacement export has missed thousands of pages in a bug report still open; the first checkpoint after that date needs this step.
- **The history of a published source is public;** the history of a withheld source is withheld with its columns. A withheld source's first and last observed versions would reveal its membership just as its column would.
- **A source new to the universe** opens its listings at its first observed version, and the record marks that it was absent from earlier versions, so a gap is not read as an absence of listing.
- **A frozen source** (one that no longer changes, such as a fixed edition) keeps its pinned version and needs no re-measurement.
- **A source that disappears** keeps its last pinned version, marked frozen, with the date it was last reachable.
- **A single web page** used as evidence is never re-measured. Its archived copy is the evidence for its date; a link check may record when the live page disappears.
- **Each pinned download is archived privately** by the project where its license allows. Hosts keep old versions only for a limited time: Wikimedia keeps the English Wiktionary dump for a few months of runs, and Wikidata's entity dumps for some weeks. Without the archive, a past version cannot be rebuilt.
- **A source's identity is a stable id,** separate from its name, which can change (SCOWL's successor is the English Speller Database). Where a distributor edits its copy of a fixed work (FreeBSD still edits its copy of web2), the distributor and its commit define the version.

## 5. The source registry and its protocols

The registry (planned) is 1 file listing every source: its id, name, kind, family, version, URL, sha256, license as its own text states it, status (active, frozen, withheld, retired), release cadence, and the decision entries that concern it.

### 5.1 Adding a source

1. **Read its license** at its primary source and record the reading (a reading, not legal advice). Decide its kind: panel source only if the terms allow publishing per-string membership.
2. **Declare its family:** independent, or part of an existing family (shared upstream).
3. **Pin it:** download it whole; hash it, using the provider's checksum where one exists; archive it privately.
4. **Derive its set** under the grammar, with its blindness accounts (the classes it cannot hold).
5. **Measure it against every row.** Its strings that the universe lacks enter as new candidates, through the grammar and with the source as their intake channel.
6. **Record it** in the registry, in the decision record, and in the NOTICES file, then build the next version.

### 5.2 Removing or withholding a source

For a takedown request, a license finding, or the maintainer's ruling:

1. **Record the request** privately: who, what, when, and the evidence of who they are.
2. **The maintainer rules.** By his answer of October 18, 2026, the source's columns, labels, and listing history leave, and a row leaves only where that source was its only attestation.
3. **Within 14 days,** build a new version that withholds the source's columns, labels, and listing history. Rows that only that source attested become restricted (§3).
4. **Mark the source** withheld in the registry, and write the decision entry.
5. **Earlier versions:** where the source's content must leave versions already released, withdraw them on every host, and leave a tombstone page with the reason, the citation, and a pointer to the replacement version. Keep their metadata and checksums public. A DataCite DOI cannot be deleted, only pointed at a tombstone. On the hub, a removed file stays in the repository's history, and erasing it needs either a support request or a squash of the history that cannot be undone and breaks the revision every earlier DOI records. The best protection is to ship nothing doubtful in the first place.
6. **The change log** says that a source was withheld and why, without restating its content.
7. **A permission revoked** (§5.3) is handled the same way.

### 5.3 Restoring a source with permission

1. **Record the grant** privately and in a decision entry: who granted it, its exact scope (strings only, membership columns, history, or redistribution), the attribution text it requires, whether it can be revoked, any limits on use, and the date. A grant that limits use (for example to non-commercial use) conflicts with the dataset's license, which allows commercial use; such a grant can cover a separate, gated derived dataset, never the universe itself.
2. **Build a new version** that carries what the grant allows. Restricted rows the grant covers ship again.
3. **Update** the registry, the NOTICES file, and the card's credits as the grant requires.

### 5.4 A source whose copyright ends

A withheld source can return when its term ends. Webster's Second (1934), if its 1961 renewal holds, can return in a version released on or after January 1, 2030. The registry records the date, and the first checkpoint after it proposes the restoration.

## 6. Checkpoints

- **Cadence:** once a year, on a fixed cut date that pins the latest version of each source available on that date, plus versions out of cycle for build errors and takedowns. The yearly rhythm matches Open English WordNet's editions. It is slower than Wiktionary and the LibreOffice dictionaries (monthly) and Wikidata (weekly), and faster than the tournament lists (2 to 3 years). A 2nd checkpoint in a year is possible, and costs mostly compute.
- **The run:** fetch each active source at its new version, verify and archive it, derive its set, measure every row, append the listing history, rebuild the pin and the release, assert every property the card states, re-run the analysis, and render the documents.
- **Automated (planned):** every step above is to be deterministic code and needs no AI, run as 1 command, by hand or on a schedule. Today the release build and the document renderers are such code; the checkpoint command is not yet written. The same pinned inputs and the same code give byte-identical outputs, checked by sha256, and each release records the code's commit, the input pins, and the output checksums.
- **Comparisons across versions** use measures that do not depend on the universe's own size: containment and the Jaccard index over the strings both sides can hold. A measure that counts the strings neither list holds (phi, odds ratios, kappa) is reported for 1 version at a time, because that count moves whenever the universe's admission rules change.
- **Needs a person:** reading a new source's license, a takedown request, or a permission; the decision entries; the review of the change log. AI may assist with these, never decide them.

## 7. Takedown requests

- **Contact:** the card and the site name 1 address for requests (ryanjosephkamp@gmail.com). The hub's own copyright process also reaches the dataset.
- **Acknowledge** within 7 days; act under §5.2 within 14 days of verifying the request.
- **Record** every request and its outcome privately, and the decision in the decision record.
- **Withdraw nothing silently:** each version's change log records every withholding, as counts.
- **No squash after the first DOI,** except under §5.2. The squash that the release plan makes before the dataset goes public is safe only because no DOI exists yet.

## 8. Versions and their numbers

Versions are numbered `vMAJOR.MINOR.PATCH`, counted from 1.0 (`v1.0`), the first public version. v2.0 and v2.1 were internal builds and are never public; 1.0 holds v2.1's rows under its public name.

- **MAJOR, a new pin or a breaking change:** a checkpoint that adds rows; rows leaving under §3; a column removed or renamed, which includes a source withheld. A user's code may need to change.
- **MINOR, the same pin, nothing removed:** a new source's column, a new layer (such as parts of speech), or corrected values in a column.
- **PATCH, the same files:** documentation and metadata only, such as a corrected sentence of the card. It changes no data file.

Every version, PATCH included, is a new release with its own record of files and hashes, its own change log entry, and a git tag naming the code that built it; nothing released is edited (rule 4). From the first public version on, each MAJOR and MINOR version gets its own DOI, linked to the version before it (DataCite's "is new version of" relation). Each source keeps its own version string verbatim in the listing record; the universe's numbers never replace it.

**Notice to users:** a MAJOR version is announced in the change log and on the site at least 2 weeks before it replaces the current one, except when a takedown cannot wait. Wikidata's interface policy, with its notice period and its tag for breaking changes, is the model.

**The derived datasets** are numbered on their own track, and each names the universe version it was built from.

## 9. Derived datasets

- **Named** `ceol-<rule>-<version>`, such as a consensus list or a validated subset. Each names the universe version it was built from.
- **Each has its own card**, its own rule, and its own versions. A change of rule is a new derived dataset or a new version of it, never a change to the universe.
- **A validated subset** made by a model applying a written definition is a derived dataset too, refreshed at each checkpoint if its makers choose.

## 10. Where each event is recorded

| Event | Record |
|---|---|
| A decision on a source, a row, or this policy | the project's decision record |
| A change a reader of the dataset sees | `CHANGELOG.md` and the card's change log |
| A source's status and version | the source registry |
| A takedown request, a grant, the rows that left | the private record |
| A version's files and their hashes | the release record of that version |

## 11. The maintainer's answers (October 18, 2026)

1. **Takedowns:** acknowledged within 7 days, acted on within 14 (§7).
2. **The listing history** of the published sources is public; the withheld sources' history is private (§4).
3. **The address for requests:** ryanjosephkamp@gmail.com (§7).
4. **A takedown that names a source:** its columns, labels, and history leave; a row leaves only where that source was its only attestation (§5.2).
5. **The Wiktionary dumps:** the pinned run and the latest complete run are archived privately now, before the XML dumps end in January 2027 (§4).
6. **Notice before a MAJOR version:** 2 weeks (§8).
