/**
 * The datasheet of a composed list: its definition in plain sentences, its
 * counts, the distribution of every dimension of the cube within it, the code
 * that reproduces it, and where it comes from. The page (/compose/datasheet/)
 * draws it; this module also writes it as Markdown and as CSV, and the list
 * download puts the Markdown beside the list. Every count is the cube's, as
 * the composer's are. No string of the list appears in it.
 */

import { full, pct } from '../charts/format';
import { CLASS_NAMES, INTAKE_KIND, INTAKE_LAYER, MOE_ORDER, MOE_SHORT, PROVENANCE, PROVENANCE_ORDER, SET_NAMES } from '../islands/labels';
import { codeFor, DATASET, VERSION, type Code } from './codegen';
import { FLAGS, PUBLISHED_SETS, type Cube, type Dim, type Selection } from './cube';
import { usDate } from './dates';

/** The English OpenList's valid list the dataset records (the composer's). */
export const EOL_REVISION = 'c1139698';

export interface SheetRow {
  readonly label: string;
  readonly value: number;
}

export interface SheetTable {
  readonly id: string;
  readonly title: string;
  readonly rows: readonly SheetRow[];
  /** the list's rows, which each share is of */
  readonly total: number;
  readonly note?: string;
  /** an ordered axis drawn as columns, or a breakdown drawn as bars */
  readonly kind: 'columns' | 'bars';
}

export interface LengthSummary {
  readonly shortest: string;
  readonly longest: string;
  readonly median: string;
  readonly lower: string;
  readonly upper: string;
}

export interface Sheet {
  readonly rows: number;
  readonly universe: number;
  readonly eolRows: number;
  readonly definition: readonly string[];
  readonly length: LengthSummary | null;
  readonly tables: readonly SheetTable[];
  readonly code: Code;
  readonly lengthCap: number;
}

export interface SheetMeta {
  readonly title: string;
  readonly author: string;
  readonly note: string;
  readonly made: Date;
  /** the address that reopens the list on the site */
  readonly link: string;
  /** how to cite the dataset: the card's section 15 */
  readonly citation: string;
  readonly file: { readonly path: string; readonly sha256: string };
}

export const DEFAULT_TITLE = 'A list from the CEOL Universe';

const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function joined(xs: readonly string[], word: 'and' | 'or'): string {
  if (xs.length <= 1) return xs.join('');
  if (xs.length === 2) return `${xs[0]} ${word} ${xs[1]}`;
  return `${xs.slice(0, -1).join(', ')}, ${word} ${xs[xs.length - 1]}`;
}

const tokenLabel = (t: string) => (t.endsWith('+') ? `${Number.parseInt(t, 10)} or more tokens` : t === '1' ? '1 token' : `${t} tokens`);
const BOOL3: Readonly<Record<string, string>> = { true: 'Yes', false: 'No', null: 'Not measured' };
const CORPORA: readonly [Dim, string][] = [
  ['gb_type', 'A Google Books 1-gram type'],
  ['wordfreq_scored', 'Scored by wordfreq'],
  ['wikt_title_any', 'A Wiktionary page title'],
];

/** The list's criteria, 1 plain sentence each. */
export function describeSelection(sel: Selection, lengthCap: number): string[] {
  const out: string[] = [];
  const v = sel.values ?? {};
  if (sel.minLists) out.push(`Listed by at least ${sel.minLists} of the 8 published lists.`);
  if (sel.listedBy?.length) {
    const names = sel.listedBy.map((s) => SET_NAMES[s] ?? s);
    out.push(names.length === 1 ? `Listed by ${names[0]}.` : `Listed by each of ${joined(names, 'and')}.`);
  }
  if (v.provenance_class?.length) {
    out.push(`Rests on ${joined(v.provenance_class.map((p) => (PROVENANCE[p]?.label ?? p).toLowerCase()), 'or')}.`);
  }
  const flags = sel.flags ?? {};
  if (flags.plain === 'with') out.push('Plain a to z: no spelling class.');
  if (flags.plain === 'without') out.push('Not plain a to z: at least 1 spelling class.');
  const withs = FLAGS.filter((f) => flags[f] === 'with').map((f) => CLASS_NAMES[f]);
  const withouts = FLAGS.filter((f) => flags[f] === 'without').map((f) => CLASS_NAMES[f]);
  if (withs.length) out.push(`${withs.length === 1 ? 'In the class' : 'In each of the classes'} ${joined(withs, 'and')}.`);
  if (withouts.length) out.push(`${withouts.length === 1 ? 'Not in the class' : 'In none of the classes'} ${joined(withouts, withouts.length === 1 ? 'and' : 'or')}.`);
  if (v.token_count?.length) out.push(`${joined(v.token_count.map(tokenLabel), 'or')}.`);
  const lo = sel.minLength != null && sel.minLength > 1 ? Math.min(sel.minLength, lengthCap) : null;
  const hi = sel.maxLength != null && sel.maxLength < lengthCap ? sel.maxLength : null;
  if (lo !== null && hi !== null) out.push(lo === hi ? `Exactly ${lo} characters long.` : `From ${lo} to ${hi} characters long.`);
  else if (lo !== null) out.push(`At least ${lo} characters long.`);
  else if (hi !== null) out.push(`At most ${hi} characters long.`);
  for (const [dim, label] of CORPORA) {
    const vals = v[dim];
    if (vals?.length && vals.length < 3) out.push(`${label}: ${joined(vals.map((x) => BOOL3[x] ?? x), 'or')}.`);
  }
  if (v.intake_layer?.length) out.push(`Came in through ${joined(v.intake_layer.map((x) => INTAKE_LAYER[x] ?? x), 'or')}.`);
  if (v.intake_kind?.length) out.push(`${sentence(joined(v.intake_kind.map((x) => INTAKE_KIND[x] ?? x), 'or'))}.`);
  if (v.model_or_engine?.length) out.push(`Model or engine: ${joined(v.model_or_engine.map((x) => (MOE_SHORT[x] ?? x).toLowerCase()), 'or')}.`);
  if (v.eol?.length === 1) {
    out.push(`${v.eol[0] === 'true' ? 'On' : 'Not on'} the English OpenList's valid list at revision ${EOL_REVISION}.`);
  }
  return out.length ? out : ['Every row of the universe: no criterion is set.'];
}

/** The median, the middle half, and the extremes of a length histogram
 *  (index i holds length i + 1; the last bucket holds the cap and above). */
export function lengthSummary(lengths: readonly number[], lengthCap: number): LengthSummary | null {
  const n = lengths.reduce((a, b) => a + b, 0);
  if (!n) return null;
  const label = (i: number) => (i + 1 >= lengthCap ? `${lengthCap} or more` : String(i + 1));
  const at = (p: number) => {
    const rank = Math.max(1, Math.ceil(p * n));
    let cum = 0;
    for (let i = 0; i < lengths.length; i++) {
      cum += lengths[i];
      if (cum >= rank) return label(i);
    }
    return label(lengths.length - 1);
  };
  const first = lengths.findIndex((x) => x > 0);
  let last = lengths.length - 1;
  while (lengths[last] === 0) last--;
  return { shortest: label(first), longest: label(last), median: at(0.5), lower: at(0.25), upper: at(0.75) };
}

/** Everything the datasheet states about `sel`. */
export function buildSheet(sel: Selection, cube: Cube): Sheet {
  const rows = cube.rows(sel);
  const cap = cube.lengthCap;
  const eolVals = sel.values?.eol;
  const eolRows = eolVals && eolVals.length && !eolVals.includes('true') ? 0 : cube.rows({ ...sel, values: { ...sel.values, eol: ['true'] } });
  const lengths = cube.byLength(sel, true);
  const by = (dim: Dim) => cube.by(dim, sel, true);
  const table = (id: string, title: string, entries: readonly SheetRow[], kind: SheetTable['kind'] = 'bars', note?: string): SheetTable => ({
    id,
    title,
    rows: entries,
    total: rows,
    kind,
    note,
  });
  const lists = cube.byListCount(sel, true);
  const sets = cube.byList(sel, true);
  const flags = cube.byFlag(sel, true);
  const tables: SheetTable[] = [
    table(
      'length',
      'Length, in characters',
      lengths.map((n, i) => ({ label: i + 1 >= cap ? `${cap} or more` : String(i + 1), value: n })),
      'columns',
      `The last column holds every length of ${cap} or more.`,
    ),
    table('provenance', 'What it rests on', PROVENANCE_ORDER.map((p) => ({ label: PROVENANCE[p].label, value: by('provenance_class').get(p) ?? 0 }))),
    table('lists', 'How many published lists list it', lists.map((n, k) => ({ label: `${k} of 8`, value: n }))),
    table(
      'listed_by',
      'Which published lists list it',
      PUBLISHED_SETS.map((s) => ({ label: SET_NAMES[s], value: sets.get(s) ?? 0 })),
      'bars',
      'A row that several lists list counts under each.',
    ),
    table(
      'spelling',
      'Spelling classes',
      (['plain', ...FLAGS] as const).map((f) => ({ label: CLASS_NAMES[f], value: flags.get(f) ?? 0 })),
      'bars',
      'A row can be in more than 1 class; a plain row is in none.',
    ),
    table('tokens', 'Tokens', cube.values.token_count.map((t) => ({ label: sentence(tokenLabel(t)), value: by('token_count').get(t) ?? 0 }))),
    ...CORPORA.map(([dim, title]) =>
      table(dim, title, ['true', 'false', 'null'].map((x) => ({ label: BOOL3[x], value: by(dim).get(x) ?? 0 })), 'bars', 'Multiword rows are not measured.'),
    ),
    table('layer', 'Layer', cube.values.intake_layer.map((x) => ({ label: sentence(INTAKE_LAYER[x] ?? x), value: by('intake_layer').get(x) ?? 0 }))),
    table('kind', 'Kind', cube.values.intake_kind.map((x) => ({ label: sentence(INTAKE_KIND[x] ?? x), value: by('intake_kind').get(x) ?? 0 }))),
    table('model_or_engine', 'Model or engine', MOE_ORDER.map((x) => ({ label: MOE_SHORT[x], value: by('model_or_engine').get(x) ?? 0 }))),
    table('eol', `The English OpenList's valid list, revision ${EOL_REVISION}`, [
      { label: 'On its list', value: by('eol').get('true') ?? 0 },
      { label: 'Not on it', value: by('eol').get('false') ?? 0 },
    ]),
  ];
  return {
    rows,
    universe: cube.total,
    eolRows,
    definition: describeSelection(sel, cap),
    length: lengthSummary(lengths, cap),
    tables,
    code: codeFor(sel, rows, cap),
    lengthCap: cap,
  };
}

export const LICENSE_TEXT =
  "The CEOL Universe's data is under CC BY-SA 4.0. A list drawn from it is shared under the same license, with its sources' notices (NOTICES.md, in the dataset and in the list download).";

export const CANDIDATE_TEXT = 'Each row is a candidate string, listed by its sources. Nothing here judges whether a string is a word.';

/** The datasheet as Markdown. */
export function sheetMarkdown(sheet: Sheet, meta: SheetMeta): string {
  const title = meta.title.trim() || DEFAULT_TITLE;
  const by = meta.author.trim() ? `By ${meta.author.trim()}. ` : '';
  const out: string[] = [
    `# ${title}`,
    '',
    `${by}Made ${usDate(meta.made)} from the CEOL Universe, version ${VERSION.slice(1)}.`,
  ];
  if (meta.note.trim()) out.push('', meta.note.trim());
  out.push(
    '',
    '## The list',
    '',
    `${full(sheet.rows)} rows: ${sheet.rows === sheet.universe ? 'all' : pct(sheet.rows, sheet.universe)} of the universe's ${full(sheet.universe)}. ${full(sheet.eolRows)} of them are on the English OpenList's valid list.`,
    '',
    '## Its definition',
    '',
    ...sheet.definition.map((s) => `- ${s}`),
  );
  if (sheet.length) {
    const l = sheet.length;
    out.push('', '## Length', '', `Median ${l.median} characters; the middle half ${l.lower} to ${l.upper}; the shortest ${l.shortest}, the longest ${l.longest}.`);
  }
  out.push('', '## Distributions', '');
  for (const t of sheet.tables) {
    out.push(`### ${t.title}`, '');
    if (t.note) out.push(t.note, '');
    out.push('| Value | Rows | Share |', '|---|---:|---:|');
    for (const r of t.rows) out.push(`| ${r.label} | ${full(r.value)} | ${pct(r.value, t.total)} |`);
    out.push('');
  }
  out.push(
    '## Reproduce it',
    '',
    `Reopen it on the site: ${meta.link}`,
    '',
    `Each form below reads version ${VERSION.slice(1)} from the Hugging Face hub at its tag and returns ${full(sheet.rows)} rows.`,
    '',
    '### DuckDB',
    '',
    '```sql',
    sheet.code.duckdb,
    '```',
    '',
    '### Polars',
    '',
    '```python',
    sheet.code.polars,
    '```',
    '',
    '### pandas',
    '',
    '```python',
    sheet.code.pandas,
    '```',
    '',
    '## Where it comes from',
    '',
    `- The dataset: \`${DATASET}\` on the Hugging Face hub, at the tag \`${VERSION}\`.`,
    `- The file the code reads: \`${meta.file.path}\`, SHA-256 \`${meta.file.sha256}\`.`,
    `- The counts: the cube of version ${VERSION.slice(1)}, which counts every row of the universe, not a sample.`,
    '',
    '## How to cite it',
    '',
    meta.citation,
    '',
    '## License',
    '',
    LICENSE_TEXT,
    '',
    CANDIDATE_TEXT,
    '',
  );
  return out.join('\n');
}

const csvField = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);

/** Every table of the datasheet in 1 CSV: the list's own row first, then a
 *  row per value; `share` is of the list (of the universe, for the list). */
export function sheetCsv(sheet: Sheet): string {
  const lines = ['table,value,rows,share'];
  const share = (part: number, whole: number) => (whole ? (part / whole).toFixed(6) : '0');
  lines.push(['list', 'rows of the universe', String(sheet.rows), share(sheet.rows, sheet.universe)].map(csvField).join(','));
  for (const t of sheet.tables) {
    for (const r of t.rows) lines.push([t.title, r.label, String(r.value), share(r.value, t.total)].map(csvField).join(','));
  }
  return lines.join('\n') + '\n';
}

/** A file name from a title: lowercase words joined by hyphens. */
export function fileStem(title: string): string {
  const stem = title
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
  return stem || 'ceol-universe-list';
}
