/**
 * A selection's test for 1 row of the open subset's `open-lists` file, for
 * the list download. It applies the terms the generated code writes
 * (open-codegen.ts) to the row's own columns, with SQL's rule for a missing
 * value: a comparison with a null is not true, so the row is left out, and
 * `IS NOT TRUE` keeps it. The rows it keeps are therefore the rows the code
 * returns; src/lib/open-download.test.ts holds the two equal, line for line,
 * on the subset's own file.
 */

import { charLength, type Row, type RowTest } from './list-filter';
import { OPEN_FLAGS, type OpenFlag, type OpenSelection } from './open-cube';

const missing = (v: unknown) => v === null || v === undefined;
const parts = (v: unknown) => (missing(v) ? null : String(v).split(';'));

export function openRowTest(sel: OpenSelection, lengthCap: number): RowTest {
  const cols = new Set<string>(['word']);
  const tests: ((r: Row) => boolean)[] = [];

  if (sel.minLists && sel.minLists > 1) {
    const n = sel.minLists;
    cols.add('list_count');
    tests.push((r) => !missing(r.list_count) && Number(r.list_count) >= n);
  }
  for (const s of sel.listedBy ?? []) {
    cols.add('listed_by');
    tests.push((r) => parts(r.listed_by)?.includes(s) ?? false);
  }
  if (sel.scowl != null) {
    const top = sel.scowl;
    cols.add('scowl_size');
    tests.push((r) => {
      if (missing(r.scowl_size)) return false;
      const n = Number(r.scowl_size);
      return n >= 10 && n <= top;
    });
  }
  if (sel.tokens?.length) {
    const exact = new Set(sel.tokens.filter((v) => !v.endsWith('+')).map(Number));
    const open = sel.tokens.find((v) => v.endsWith('+'));
    const atLeast = open ? Number.parseInt(open, 10) : Infinity;
    cols.add('token_count');
    tests.push((r) => {
      if (missing(r.token_count)) return false;
      const n = Number(r.token_count);
      return exact.has(n) || n >= atLeast;
    });
  }
  if (sel.gbType === 'with' || sel.gbType === 'without') {
    const want = sel.gbType === 'with';
    cols.add('gb_type');
    tests.push((r) => r.gb_type === want);
  }
  const flags = sel.flags ?? {};
  if (flags.plain === 'with' || flags.plain === 'without') {
    const want = flags.plain === 'with';
    cols.add('classes');
    tests.push((r) => !missing(r.classes) && (r.classes === '') === want);
  }
  for (const f of OPEN_FLAGS) {
    const rule = flags[f as OpenFlag];
    if (!rule || rule === 'any') continue;
    const want = rule === 'with';
    cols.add('classes');
    tests.push((r) => {
      const p = parts(r.classes);
      return p !== null && p.includes(f) === want;
    });
  }
  if (sel.noInstances) {
    cols.add('wn_instance');
    tests.push((r) => r.wn_instance !== true);
  }
  if (sel.noProperNouns) {
    cols.add('wk_proper_noun');
    tests.push((r) => r.wk_proper_noun !== true);
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
