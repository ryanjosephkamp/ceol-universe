/**
 * A composed list's test for 1 row of the universe file, for the list
 * download. It applies the terms the generated code writes (codegen.ts) to the
 * row's own columns, with SQL's rule for a missing value: a comparison with a
 * null is not true, so the row is left out. The rows it keeps are therefore
 * the rows the code returns; src/lib/list-download.test.ts holds the two
 * equal, line for line, on version 1.0's own file.
 */

import { FLAGS, type Dim, type Flag, type Selection } from './cube';

export type Row = Readonly<Record<string, unknown>>;

export interface RowTest {
  /** the columns the test reads, `word` first */
  readonly columns: readonly string[];
  readonly test: (row: Row) => boolean;
}

const BOOLEANS: readonly Dim[] = ['eol'];
const NULLABLE: readonly Dim[] = ['gb_type', 'wordfreq_scored', 'wikt_title_any'];
const NUMBERED: readonly Dim[] = ['token_count'];

const missing = (v: unknown) => v === null || v === undefined;
const parts = (v: unknown) => (missing(v) ? null : String(v).split(';'));

/** The length of a string in characters (code points), as DuckDB's
 *  `length`, Polars' `len_chars`, and Python's `len` count it. */
export function charLength(s: string): number {
  let n = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c < 0xd800 || c > 0xdbff) n++;
  }
  return n;
}

export function rowTest(sel: Selection, lengthCap: number): RowTest {
  const cols = new Set<string>(['word']);
  const tests: ((r: Row) => boolean)[] = [];

  if (sel.minLists) {
    const n = sel.minLists;
    cols.add('panel_count');
    tests.push((r) => !missing(r.panel_count) && Number(r.panel_count) >= n);
  }
  for (const s of sel.listedBy ?? []) {
    cols.add('panel_sets');
    tests.push((r) => parts(r.panel_sets)?.includes(s) ?? false);
  }
  const flags = sel.flags ?? {};
  if (flags.plain === 'with' || flags.plain === 'without') {
    const want = flags.plain === 'with';
    cols.add('class_explicit');
    tests.push((r) => !missing(r.class_explicit) && (r.class_explicit === 'plain') === want);
  }
  for (const f of FLAGS) {
    const rule = flags[f as Flag];
    if (!rule || rule === 'any') continue;
    const want = rule === 'with';
    cols.add('class_explicit');
    tests.push((r) => {
      const p = parts(r.class_explicit);
      return p !== null && p.includes(f) === want;
    });
  }
  for (const [dim, vals] of Object.entries(sel.values ?? {}) as [Dim, readonly string[]][]) {
    if (!vals || vals.length === 0 || dim === 'length') continue;
    if (BOOLEANS.includes(dim)) {
      if (vals.length === 2) continue;
      const want = vals[0] === 'true';
      cols.add(dim);
      tests.push((r) => r[dim] === want);
    } else if (NULLABLE.includes(dim)) {
      if (vals.length === 3) continue;
      const ok = new Set(vals);
      cols.add(dim);
      tests.push((r) => {
        const v = r[dim];
        return missing(v) ? ok.has('null') : ok.has(v === true ? 'true' : 'false');
      });
    } else if (NUMBERED.includes(dim)) {
      const exact = new Set(vals.filter((v) => !v.endsWith('+')).map(Number));
      const open = vals.find((v) => v.endsWith('+'));
      const atLeast = open ? Number.parseInt(open, 10) : Infinity;
      cols.add(dim);
      tests.push((r) => {
        if (missing(r[dim])) return false;
        const n = Number(r[dim]);
        return exact.has(n) || n >= atLeast;
      });
    } else {
      const ok = new Set(vals);
      cols.add(dim);
      tests.push((r) => !missing(r[dim]) && ok.has(String(r[dim])));
    }
  }
  const lo = sel.minLength != null && sel.minLength > 1 ? sel.minLength : null;
  const hi = sel.maxLength != null && sel.maxLength < lengthCap ? sel.maxLength : null;
  if (lo !== null || hi !== null) {
    tests.push((r) => {
      if (typeof r.word !== 'string') return false;
      const n = charLength(r.word);
      return (lo === null || n >= lo) && (hi === null || n <= hi);
    });
  }
  return {
    columns: [...cols],
    test: (r) => {
      for (const t of tests) if (!t(r)) return false;
      return true;
    },
  };
}
