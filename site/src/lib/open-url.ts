/** An open-subset selection in the page's address, so a composed list can be
 *  shared: `by` for the lists that must list a row, `scowl` for SCOWL's
 *  largest size, `lists` for the least number of lists, `tok` for the token
 *  counts, `gb` for the Google Books rule, `f.<class>` for a class rule,
 *  `drop` for the multiword rows left out, and `len` for a length range. */

import type { FlagRule } from './cube';
import { NAMED_LISTS, OPEN_FLAGS, OPEN_LISTS, SCOWL_SIZES, type OpenCube, type OpenSelection } from './open-cube';

const split = (v: string | null) => (v ? v.split('~').filter(Boolean) : []);
const rule = (v: string | null): FlagRule | undefined => (v === 'with' || v === 'without' ? v : undefined);

export function readOpenSelection(search: string): OpenSelection {
  const p = new URLSearchParams(search);
  const flags: Record<string, FlagRule> = {};
  for (const f of ['plain', ...OPEN_FLAGS]) {
    const r = rule(p.get(`f.${f}`));
    if (r) flags[f] = r;
  }
  const lists = Number(p.get('lists'));
  const scowl = Number(p.get('scowl'));
  const drop = split(p.get('drop'));
  const [lo, hi] = (p.get('len') ?? '').split('-').map((x) => (x ? Number(x) : null));
  return {
    listedBy: split(p.get('by')).filter((s) => (NAMED_LISTS as readonly string[]).includes(s)),
    scowl: (SCOWL_SIZES as readonly number[]).includes(scowl) ? scowl : null,
    minLists: Number.isInteger(lists) && lists > 1 && lists <= OPEN_LISTS.length ? lists : 0,
    tokens: split(p.get('tok')),
    gbType: rule(p.get('gb')) ?? 'any',
    flags,
    noInstances: drop.includes('instances'),
    noProperNouns: drop.includes('proper-nouns'),
    minLength: lo && Number.isFinite(lo) ? lo : null,
    maxLength: hi && Number.isFinite(hi) ? hi : null,
  };
}

/** `sel` as the cube can count it and the generated code can select it, so
 *  that a shared address gives the same rows in both: token counts keep only
 *  the values the cube holds, and the length range is held inside the cube's
 *  buckets, whose last one holds every length at or above the cap. */
export function normalizeOpenSelection(sel: OpenSelection, cube: Pick<OpenCube, 'values' | 'lengthCap'>): OpenSelection {
  const tokens = (sel.tokens ?? []).filter((t) => cube.values.token_count.includes(t));
  const cap = cube.lengthCap;
  let lo = sel.minLength ?? null;
  let hi = sel.maxLength ?? null;
  if (lo !== null && lo <= 1) lo = null;
  if (lo !== null && lo > cap) lo = cap;
  if (hi !== null && hi >= cap) hi = null;
  if (lo !== null && hi !== null && lo > hi) [lo, hi] = [null, null];
  return { ...sel, tokens: [...new Set(tokens)], minLength: lo, maxLength: hi };
}

/** The query of a link to every row. A bare address reopens the list
 *  stored on the visitor's device, so a link to the whole subset names it. */
export const ALL_QUERY = '?all=1';

/** The query a link to `sel` carries, which reopens `sel` on any device:
 *  its criteria, or ALL_QUERY for none. readOpenSelection reads ALL_QUERY as
 *  no criterion. */
export function openShareQuery(sel: OpenSelection): string {
  return openSelectionQuery(sel) || ALL_QUERY;
}

/** The address of the page with `sel`, for Copy the link and the datasheet. */
export const openLink = (origin: string, sel: OpenSelection) => `${origin}/compose/open/${openShareQuery(sel)}`;

/** Where the last list composed on a device is kept. */
export const STORE_KEY = 'ceol-compose-open';

/** The query of the list stored on this device, or '' (also when storage is
 *  refused, as in a private window). */
export function storedQuery(storage: Pick<Storage, 'getItem'> | null): string {
  try {
    return storage?.getItem(STORE_KEY) ?? '';
  } catch {
    return '';
  }
}

/** Keeps `sel` as this device's last list; every row is kept as no entry. */
export function storeSelection(storage: Pick<Storage, 'setItem' | 'removeItem'> | null, sel: OpenSelection): void {
  try {
    const q = openSelectionQuery(sel);
    if (q) storage?.setItem(STORE_KEY, q);
    else storage?.removeItem(STORE_KEY);
  } catch {
    // storage refused: the address still holds the list
  }
}

/** The list the page opens with: the address's, and on a bare address the
 *  one stored on this device. */
export function initialOpenSelection(search: string, storage: Pick<Storage, 'getItem'> | null): OpenSelection {
  return readOpenSelection(search || storedQuery(storage));
}

/** The address's query for `sel`, with its leading '?', or '' for none. */
export function openSelectionQuery(sel: OpenSelection): string {
  const p = new URLSearchParams();
  if (sel.listedBy?.length) p.set('by', sel.listedBy.join('~'));
  if (sel.scowl != null) p.set('scowl', String(sel.scowl));
  if (sel.minLists && sel.minLists > 1) p.set('lists', String(sel.minLists));
  if (sel.tokens?.length) p.set('tok', sel.tokens.join('~'));
  if (sel.gbType && sel.gbType !== 'any') p.set('gb', sel.gbType);
  for (const [f, r] of Object.entries(sel.flags ?? {})) if (r && r !== 'any') p.set(`f.${f}`, r);
  const drop = [sel.noInstances && 'instances', sel.noProperNouns && 'proper-nouns'].filter(Boolean);
  if (drop.length) p.set('drop', drop.join('~'));
  if (sel.minLength != null || sel.maxLength != null) p.set('len', `${sel.minLength ?? ''}-${sel.maxLength ?? ''}`);
  const search = p.toString();
  return search ? `?${search}` : '';
}
