/**
 * The datasheet of a list composed from the open subset, as Markdown: its
 * definition in plain sentences, its count, its distributions, the code that
 * reproduces it, the file and commit it comes from, and its license with the
 * attribution the file's own metadata carries. The list download puts it in
 * the zip beside the list, and the page saves it alone. Every count is the
 * cube's, as the page's are. No string of the list appears in it.
 */

import { full, pct } from '../charts/format';
import { CLASS_NAMES, SET_NAMES } from '../islands/labels';
import { usDate } from './dates';
import { OPEN_COMMIT, OPEN_CONFIG, OPEN_DATASET, openCodeFor } from './open-codegen';
import { NAMED_LISTS, OPEN_FLAGS, OPEN_LISTS, SCOWL_SIZES, type OpenCube, type OpenSelection } from './open-cube';

export interface OpenSheetMeta {
  readonly made: Date;
  /** the address that reopens the list on the site */
  readonly link: string;
  /** how to cite the subset: its card's section 10 */
  readonly citation: string;
  /** the file the list is read from, with its metadata */
  readonly file: {
    readonly path: string;
    readonly bytes: number;
    readonly sha256: string;
    readonly license: string;
    readonly attribution: string;
  };
}

export const OPEN_TITLE = "A list from the CEOL Universe's open subset";

export const OPEN_LICENSE_TEXT =
  'The open subset is licensed CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). A list drawn from it is shared under the same license, with NOTICES.md, which carries the notices and licenses its sources require.';

export const OPEN_CANDIDATE_TEXT = 'Each row is a candidate string that an open list lists. Nothing here judges whether a string is a word.';

const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function joined(xs: readonly string[], word: 'and' | 'or'): string {
  if (xs.length <= 1) return xs.join('');
  if (xs.length === 2) return `${xs[0]} ${word} ${xs[1]}`;
  return `${xs.slice(0, -1).join(', ')}, ${word} ${xs[xs.length - 1]}`;
}

export const tokenLabel = (t: string) => (t.endsWith('+') ? `${Number.parseInt(t, 10)} or more tokens` : t === '1' ? '1 token' : `${t} tokens`);

/** SCOWL's sizes up to `n`, as a phrase. */
export const scowlPhrase = (n: number) => (n === SCOWL_SIZES[0] ? `at size ${n}` : `at a size of ${SCOWL_SIZES[0]} to ${n}`);

/** The list's criteria, 1 plain sentence each. */
export function describeOpenSelection(sel: OpenSelection, lengthCap: number): string[] {
  const out: string[] = [];
  if (sel.minLists && sel.minLists > 1) out.push(`Listed by at least ${sel.minLists} of the ${OPEN_LISTS.length} open lists.`);
  const named = NAMED_LISTS.filter((s) => sel.listedBy?.includes(s)).map((s) => SET_NAMES[s]);
  if (named.length) out.push(named.length === 1 ? `Listed by ${named[0]}.` : `Listed by each of ${joined(named, 'and')}.`);
  if (sel.scowl != null) out.push(`Listed by SCOWL ${scowlPhrase(sel.scowl)}.`);
  if (sel.tokens?.length) out.push(`${sentence(joined(sel.tokens.map(tokenLabel), 'or'))}.`);
  if (sel.gbType === 'with') out.push('A Google Books 1-gram type.');
  if (sel.gbType === 'without') out.push('A single word that is not a Google Books 1-gram type (multiword rows are not measured, so none is kept).');
  const flags = sel.flags ?? {};
  if (flags.plain === 'with') out.push('Plain a to z: no spelling class, so a single word.');
  if (flags.plain === 'without') out.push('Not plain a to z: at least 1 spelling class (every multiword row is in the class Multiword).');
  const withs = OPEN_FLAGS.filter((f) => flags[f] === 'with').map((f) => CLASS_NAMES[f]);
  const withouts = OPEN_FLAGS.filter((f) => flags[f] === 'without').map((f) => CLASS_NAMES[f]);
  if (withs.length) out.push(`${withs.length === 1 ? 'In the class' : 'In each of the classes'} ${joined(withs, 'and')}.`);
  if (withouts.length) out.push(`${withouts.length === 1 ? 'Not in the class' : 'In none of the classes'} ${joined(withouts, withouts.length === 1 ? 'and' : 'or')}.`);
  if (sel.noInstances) out.push('Not a multiword row that WordNet records as an instance.');
  if (sel.noProperNouns) out.push('Not a multiword row under a Wiktionary proper-noun heading.');
  const lo = sel.minLength != null && sel.minLength > 1 ? Math.min(sel.minLength, lengthCap) : null;
  const hi = sel.maxLength != null && sel.maxLength < lengthCap ? sel.maxLength : null;
  if (lo !== null && hi !== null) out.push(lo === hi ? `Exactly ${lo} characters long.` : `From ${lo} to ${hi} characters long.`);
  else if (lo !== null) out.push(`At least ${lo} characters long.`);
  else if (hi !== null) out.push(`At most ${hi} characters long.`);
  return out.length ? out : ['Every row of the open subset: no criterion is set.'];
}

interface Table {
  readonly title: string;
  readonly note?: string;
  readonly rows: readonly { readonly label: string; readonly value: number }[];
}

/** The list's distributions, each under the list's own criteria. */
export function openTables(sel: OpenSelection, cube: OpenCube): Table[] {
  const cap = cube.lengthCap;
  const lists = cube.byListCount(sel, true);
  const sets = cube.byList(sel, true);
  const sizes = cube.byScowlSize(sel, true);
  const tokens = cube.byTokens(sel, true);
  const flags = cube.byFlag(sel, true);
  const gb = cube.byGbType(sel, true);
  return [
    {
      title: 'Length, in characters',
      note: `The last row holds every length of ${cap} or more.`,
      rows: cube.byLength(sel, true).map((n, i) => ({ label: i + 1 >= cap ? `${cap} or more` : String(i + 1), value: n })),
    },
    {
      title: 'How many open lists list it',
      rows: lists.slice(1).map((n, k) => ({ label: `${k + 1} of ${OPEN_LISTS.length}`, value: n })),
    },
    {
      title: 'Which open lists list it',
      note: 'A row that several lists list counts under each.',
      rows: OPEN_LISTS.map((s) => ({ label: SET_NAMES[s], value: sets.get(s) ?? 0 })),
    },
    {
      title: "SCOWL's smallest size that lists it",
      note: 'The rows SCOWL lists at a size of 10 to 70; a row counts under the smallest size that holds it.',
      rows: SCOWL_SIZES.map((s) => ({ label: `Size ${s}`, value: sizes.get(s) ?? 0 })),
    },
    {
      title: 'Tokens',
      rows: cube.values.token_count.map((t) => ({ label: sentence(tokenLabel(t)), value: tokens.get(t) ?? 0 })),
    },
    {
      title: 'Spelling classes',
      note: 'A row can be in more than 1 class; a plain row is in none.',
      rows: (['plain', ...OPEN_FLAGS] as const).map((f) => ({ label: CLASS_NAMES[f], value: flags.get(f) ?? 0 })),
    },
    {
      title: 'A Google Books 1-gram type',
      note: 'Multiword rows are not measured.',
      rows: [
        { label: 'Yes', value: gb.get('true') ?? 0 },
        { label: 'No', value: gb.get('false') ?? 0 },
        { label: 'Not measured', value: gb.get('null') ?? 0 },
      ],
    },
  ];
}

/** The datasheet as Markdown. */
export function openSheetMarkdown(sel: OpenSelection, cube: OpenCube, meta: OpenSheetMeta): string {
  const rows = cube.rows(sel);
  const total = cube.total;
  const code = openCodeFor(sel, rows, cube.lengthCap);
  const out: string[] = [
    `# ${OPEN_TITLE}`,
    '',
    `Made ${usDate(meta.made)} from the CEOL Universe's open subset, version 1.0, at commit \`${OPEN_COMMIT}\`.`,
    '',
    '## The list',
    '',
    `${full(rows)} rows: ${rows === total ? 'all' : pct(rows, total)} of the open subset's ${full(total)}, 1 string per line in \`list.txt\`, in the code's order.`,
    '',
    OPEN_CANDIDATE_TEXT,
    '',
    '## Its definition',
    '',
    ...describeOpenSelection(sel, cube.lengthCap).map((s) => `- ${s}`),
    '',
    '## Distributions',
    '',
  ];
  for (const t of openTables(sel, cube)) {
    out.push(`### ${t.title}`, '');
    if (t.note) out.push(t.note, '');
    out.push('| Value | Rows | Share |', '|---|---:|---:|');
    for (const r of t.rows) out.push(`| ${r.label} | ${full(r.value)} | ${pct(r.value, rows)} |`);
    out.push('');
  }
  out.push(
    '## Reproduce it',
    '',
    `Reopen it on the site: ${meta.link}`,
    '',
    `Each form below reads the open subset from the Hugging Face hub at commit \`${OPEN_COMMIT}\` and returns ${full(rows)} rows.`,
    '',
    '### DuckDB',
    '',
    '```sql',
    code.duckdb,
    '```',
    '',
    '### Polars',
    '',
    '```python',
    code.polars,
    '```',
    '',
    '### pandas',
    '',
    '```python',
    code.pandas,
    '```',
    '',
    '## Where it comes from',
    '',
    `- The dataset: \`${OPEN_DATASET}\` on the Hugging Face hub, its \`${OPEN_CONFIG}\` config, at commit \`${OPEN_COMMIT}\`.`,
    `- The file: \`${meta.file.path}\`, ${full(meta.file.bytes)} bytes, SHA-256 \`${meta.file.sha256}\`.`,
    `- The counts: the open subset's cube, which counts every row of \`${OPEN_CONFIG}\`, not a sample.`,
    '',
    '## License',
    '',
    OPEN_LICENSE_TEXT,
    '',
    `The file's metadata gives its license as \`${meta.file.license}\` and its attribution as:`,
    '',
    `> ${meta.file.attribution}`,
    '',
    '## How to cite it',
    '',
    meta.citation,
    '',
  );
  return out.join('\n');
}
