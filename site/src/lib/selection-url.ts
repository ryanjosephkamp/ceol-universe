/** A selection in the page's address, so a composed list can be shared:
 *  `d.<dimension>` for the values of a dimension, `lists` for the least
 *  number of published lists, `by` for the lists that must list a row,
 *  `f.<class>` for a class rule, and `len` for a length range. */

import { DIMENSIONS, FLAGS, PUBLISHED_SETS, type Cube, type Dim, type FlagRule, type Selection } from './cube';

const split = (v: string | null) => (v ? v.split('~').filter(Boolean) : []);

export function readSelection(search: string): Selection {
  const p = new URLSearchParams(search);
  const values: Partial<Record<Dim, string[]>> = {};
  for (const d of DIMENSIONS) {
    const v = split(p.get(`d.${d}`));
    if (v.length) values[d] = v;
  }
  const flags: Record<string, FlagRule> = {};
  for (const f of ['plain', ...FLAGS]) {
    const r = p.get(`f.${f}`);
    if (r === 'with' || r === 'without') flags[f] = r;
  }
  const lists = Number(p.get('lists'));
  const [lo, hi] = (p.get('len') ?? '').split('-').map((x) => (x ? Number(x) : null));
  return {
    values,
    flags,
    listedBy: split(p.get('by')).filter((s) => (PUBLISHED_SETS as readonly string[]).includes(s)),
    minLists: Number.isInteger(lists) && lists > 0 && lists <= PUBLISHED_SETS.length ? lists : 0,
    minLength: lo && Number.isFinite(lo) ? lo : null,
    maxLength: hi && Number.isFinite(hi) ? hi : null,
  };
}

/** `sel` as the cube can count it and the generated code can select it, so
 *  that a shared address gives the same rows in both: a dimension keeps only
 *  the values the cube holds (lengths are chosen by the length range, not by
 *  the length dimension), and the length range is held inside the cube's
 *  buckets, whose last one holds every length at or above the cap. */
export function normalizeSelection(sel: Selection, cube: Pick<Cube, 'values' | 'lengthCap'>): Selection {
  const values: Partial<Record<Dim, string[]>> = {};
  for (const [d, v] of Object.entries(sel.values ?? {}) as [Dim, readonly string[]][]) {
    if (d === 'length' || !v) continue;
    const known = v.filter((x) => cube.values[d].includes(x));
    if (known.length) values[d] = known;
  }
  const cap = cube.lengthCap;
  let lo = sel.minLength ?? null;
  let hi = sel.maxLength ?? null;
  if (lo !== null && lo > cap) lo = cap;
  if (hi !== null && hi >= cap) hi = null;
  if (lo !== null && hi !== null && lo > hi) [lo, hi] = [null, null];
  return { ...sel, values, minLength: lo, maxLength: hi };
}

/** The address's query for `sel`, with its leading '?', or '' for none. */
export function selectionQuery(sel: Selection): string {
  const p = new URLSearchParams();
  for (const [d, v] of Object.entries(sel.values ?? {})) if (v && v.length) p.set(`d.${d}`, v.join('~'));
  if (sel.minLists) p.set('lists', String(sel.minLists));
  if (sel.listedBy?.length) p.set('by', sel.listedBy.join('~'));
  for (const [f, r] of Object.entries(sel.flags ?? {})) if (r && r !== 'any') p.set(`f.${f}`, r);
  if (sel.minLength != null || sel.maxLength != null) p.set('len', `${sel.minLength ?? ''}-${sel.maxLength ?? ''}`);
  const search = p.toString();
  return search ? `?${search}` : '';
}

export function writeSelection(sel: Selection): void {
  const q = selectionQuery(sel);
  window.history.replaceState(null, '', q || window.location.pathname);
}
