/**
 * The site's build-time data. Every figure on a page is read here, from the
 * files the pipeline writes, and a figure the files do not hold fails the
 * build. Nothing in this module is typed by hand.
 *
 * - the figures file of the version: pipeline/research/release/figures/<v>/
 * - the site's sample rows: site/fixtures/rows.jsonl (tools/build_fixtures.py)
 * - the vetted example list: examples/vetted_examples.txt, the only strings a
 *   page may show as examples
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/** The version the site describes: 1.0, the first public release. */
export const VERSION = 'v1.0';

/** The repository's root: the site builds from `site/`. */
const REPO = resolve(process.cwd(), '..');

const read = (rel: string) => readFileSync(resolve(REPO, rel), 'utf-8');

export interface Figure {
  readonly id: string;
  readonly value: number;
  readonly what: string;
  readonly source: string;
}

interface FiguresFile {
  readonly version: string;
  readonly dataset: string;
  readonly built_on: string;
  readonly generated_by: string;
  readonly figures: readonly Figure[];
}

export const FIGURES_PATH = `pipeline/research/release/figures/${VERSION}/figures.json`;

const figuresFile: FiguresFile = JSON.parse(read(FIGURES_PATH));
if (figuresFile.version !== VERSION) {
  throw new Error(`${FIGURES_PATH} is version ${figuresFile.version}, not ${VERSION}`);
}
const byId = new Map(figuresFile.figures.map((f) => [f.id, f]));

/** The figure `id` of the version's figures file. An id the file does not
 *  hold stops the build: no figure reaches a page without a source. */
export function fig(id: string): Figure {
  const f = byId.get(id);
  if (!f) throw new Error(`no figure '${id}' in ${FIGURES_PATH}; a page may show only figures the file holds`);
  return f;
}

export const release = {
  version: figuresFile.version,
  /** the name a reader sees: "1.0" for v1.0 */
  name: figuresFile.version.replace(/^v/, ''),
  dataset: figuresFile.dataset,
  builtOn: figuresFile.built_on,
  figuresPath: FIGURES_PATH,
};

/** The universe file of the version, as its release record names it and
 *  as the hub holds it (data/<file>): what the generated code reads. */
const releaseRecord = JSON.parse(read(`pipeline/research/release/release_${VERSION}.json`)) as {
  files: { config: string; path: string; sha256: string; bytes: number }[];
};
const universeEntry = releaseRecord.files.find((f) => f.config === 'universe');
if (!universeEntry) throw new Error(`the release record of ${VERSION} names no universe file`);
export const universeFile = { path: `data/${universeEntry.path}`, sha256: universeEntry.sha256, bytes: universeEntry.bytes };

export const formatCount = (n: number) => n.toLocaleString('en-US');

/** A share of 2 figures, as a percentage with `digits` decimals. */
export function share(part: Figure, whole: Figure, digits = 1): string {
  return `${((100 * part.value) / whole.value).toFixed(digits)}%`;
}

// ---------------------------------------------------------------------------
// The vetted example list
// ---------------------------------------------------------------------------

export const VETTED_PATH = 'examples/vetted_examples.txt';

/** The vetted example list, in its file's order. */
export const vetted: readonly string[] = read(VETTED_PATH)
  .split('\n')
  .map((l) => l.replace(/\r$/, ''))
  .filter((l) => l && !l.startsWith('#'));

const vettedSet = new Set(vetted);

/** Whether a page may show `s` as an example. */
export const isVetted = (s: string) => vettedSet.has(s);

// ---------------------------------------------------------------------------
// The sample rows
// ---------------------------------------------------------------------------

export const SAMPLE_PATH = 'site/fixtures/rows.jsonl';

export interface SampleRow {
  readonly id: string;
  readonly word: string;
  readonly classes: string;
  readonly token_count: number;
  readonly panel_sets: string;
  readonly panel_count: number;
  readonly provenance_class: string;
  readonly intake_layer: string;
  readonly intake_kind: string;
  readonly intake_channels: string;
  readonly intake_date: string | null;
  readonly sources: string;
  readonly eol: boolean;
  readonly eol_record: string;
  readonly model_or_engine: string;
  readonly gb_type: boolean | null;
  readonly wordfreq_scored: boolean | null;
}

export const sampleRows: readonly SampleRow[] = read(SAMPLE_PATH)
  .split('\n')
  .filter(Boolean)
  .map((line) => JSON.parse(line) as SampleRow);

interface FixturesManifest {
  readonly source: { readonly version: string; readonly rows: number };
  readonly published_sets: readonly string[];
}

export const sampleManifest: FixturesManifest = JSON.parse(read('site/fixtures/MANIFEST.json'));
if (sampleManifest.source.version !== VERSION) {
  throw new Error(`the sample rows are drawn from ${sampleManifest.source.version}, not ${VERSION}`);
}

/** The 8 published panel sets, in `panel_sets`' order. */
export const publishedSets: readonly string[] = sampleManifest.published_sets;

// ---------------------------------------------------------------------------
// The card's rows (pipeline/research/release/site_rows.py)
// ---------------------------------------------------------------------------

export const CARD_ROWS_PATH = `pipeline/research/release/figures/${VERSION}/card_rows.json`;

interface CardRowsFile {
  readonly version: string;
  readonly rows: Readonly<Record<string, { readonly value: number | string; readonly text: string }>>;
}

const cardRows: CardRowsFile = JSON.parse(read(CARD_ROWS_PATH));
if (cardRows.version !== VERSION) throw new Error(`${CARD_ROWS_PATH} is version ${cardRows.version}, not ${VERSION}`);

/** A count of the card's calculator, by its row's name. A name the file does
 *  not hold, or a row that is not a count, stops the build. */
/** A row of the card's calculator as its text, for a row that is not a count. */
export function cardText(name: string): string {
  const row = cardRows.rows[name];
  if (!row) throw new Error(`no card row '${name}' in ${CARD_ROWS_PATH}`);
  return row.text;
}

export function cardCount(name: string): number {
  const row = cardRows.rows[name];
  if (!row) throw new Error(`no card row '${name}' in ${CARD_ROWS_PATH}`);
  if (typeof row.value !== 'number') throw new Error(`the card row '${name}' is not a count`);
  return row.value;
}
