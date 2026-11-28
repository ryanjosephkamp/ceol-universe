/**
 * The cube of the open subset (pipeline/research/release/open_compose.py):
 * the count of rows of its `open-lists` config for every combination of 8
 * dimensions. Every count on Compose from the open subset is computed here
 * from it, exactly; no row is fetched to count, and nothing is sampled.
 *
 * Two dimensions are decoded into what a reader filters by:
 * - `listed_by` (the open lists that list a row, ';'-joined) into a bit per
 *   list; the number of bits is the row's `list_count`, which the build
 *   asserts on every row;
 * - `classes` (the spelling classes, ';'-joined, or '' for a plain row) into
 *   a bit per class.
 */

import { FLAGS, type Flag, type FlagRule } from './cube';

export const OPEN_DIMENSIONS = [
  'listed_by',
  'scowl_size',
  'token_count',
  'length',
  'classes',
  'gb_type',
  'wn_instance',
  'wk_proper_noun',
] as const;

export type OpenDim = (typeof OPEN_DIMENSIONS)[number];

export interface OpenCubeFile {
  readonly version: string;
  readonly dataset: string;
  readonly commit: string;
  readonly source: { readonly config: string; readonly path: string; readonly sha256: string; readonly rows: number };
  readonly caps: Readonly<Record<string, number>>;
  readonly dimensions: readonly { readonly name: string; readonly values: readonly string[] }[];
  readonly cells: readonly (readonly number[])[];
}

/** The 6 open lists, in the order of `listed_by`. */
export const OPEN_LISTS = [
  'wordnet',
  'wiktionary_english',
  'hunspell_en_US',
  'hunspell_en_CA',
  'hunspell_en_AU',
  'scowl',
] as const;

export type OpenList = (typeof OPEN_LISTS)[number];

/** The lists a reader requires by name; SCOWL is required by its size. */
export const NAMED_LISTS = OPEN_LISTS.slice(0, 5) as readonly Exclude<OpenList, 'scowl'>[];

/** The SCOWL sizes `scowl_size` names, 10 to 70. */
export const SCOWL_SIZES = [10, 20, 35, 40, 50, 55, 60, 70] as const;

/** The spelling classes a reader filters by. `spaced` is left out: a row is
 *  spaced exactly when it has more than 1 token, which the tokens choose. */
export const OPEN_FLAGS = FLAGS.filter((f) => f !== 'spaced') as readonly Exclude<Flag, 'spaced'>[];

export type OpenFlag = (typeof OPEN_FLAGS)[number];

/** A selection of rows of the open subset. Every field left at its default
 *  selects every row. */
export interface OpenSelection {
  /** the open lists, other than SCOWL, that must all list a row */
  readonly listedBy?: readonly string[];
  /** SCOWL must list a row at a size of 10 to this; null: SCOWL is not required */
  readonly scowl?: number | null;
  /** the least number of the 6 open lists that list a row; 0 and 1 select every row */
  readonly minLists?: number;
  /** the token counts a row may have ('1', '2', '3', '4+'); missing or empty is any */
  readonly tokens?: readonly string[];
  /** 'with' keeps Google Books types, 'without' keeps the single words that are
   *  not; a multiword row is not measured, so either leaves it out */
  readonly gbType?: FlagRule;
  /** a rule per spelling class; 'plain' with 'with' keeps plain rows only */
  readonly flags?: Partial<Record<OpenFlag | 'plain', FlagRule>>;
  /** leaves out the multiword rows WordNet records as instances */
  readonly noInstances?: boolean;
  /** leaves out the multiword rows under a Wiktionary proper-noun heading */
  readonly noProperNouns?: boolean;
  /** the shortest and longest length, in characters; the last bucket holds
   *  every row at or above the cap */
  readonly minLength?: number | null;
  readonly maxLength?: number | null;
}

/** The parts of a selection a breakdown can leave out, so a facet counts
 *  under every other criterion. */
export type OpenFacet = 'listedBy' | 'scowl' | 'minLists' | 'tokens' | 'gbType' | 'flags' | 'noInstances' | 'noProperNouns' | 'length';

const TRI = ['true', 'false', 'null'] as const;
export type Tri = (typeof TRI)[number];

export class OpenCube {
  readonly version: string;
  readonly dataset: string;
  readonly commit: string;
  readonly source: OpenCubeFile['source'];
  readonly values: Readonly<Record<OpenDim, readonly string[]>>;
  readonly lengthCap: number;
  readonly total: number;
  readonly cells: number;
  private readonly count: Float64Array;
  private readonly listMask: Uint8Array;
  private readonly lists: Uint8Array;
  /** the SCOWL size, or 0 where SCOWL does not list the row */
  private readonly scowlSize: Uint8Array;
  private readonly token: Uint8Array;
  private readonly length: Uint8Array;
  private readonly flagMask: Uint16Array;
  private readonly gb: Uint8Array;
  private readonly inst: Uint8Array;
  private readonly proper: Uint8Array;

  constructor(file: OpenCubeFile) {
    const names = file.dimensions.map((d) => d.name);
    if (names.join() !== OPEN_DIMENSIONS.join()) {
      throw new Error(`the open cube's dimensions are ${names.join(', ')}, not the ones this page reads`);
    }
    this.version = file.version;
    this.dataset = file.dataset;
    this.commit = file.commit;
    this.source = file.source;
    this.lengthCap = file.caps.length;
    const values = {} as Record<OpenDim, readonly string[]>;
    OPEN_DIMENSIONS.forEach((d, i) => (values[d] = file.dimensions[i].values));
    this.values = values;

    const listMaskOf = values.listed_by.map((v) =>
      v.split(';').reduce((m, s) => {
        const at = OPEN_LISTS.indexOf(s as OpenList);
        if (at < 0) throw new Error(`listed_by names an unknown list '${s}'`);
        return m | (1 << at);
      }, 0),
    );
    const flagMaskOf = values.classes.map((v) =>
      v === ''
        ? 0
        : v.split(';').reduce((m, f) => {
            const at = FLAGS.indexOf(f as Flag);
            if (at < 0) throw new Error(`classes names an unknown class '${f}'`);
            return m | (1 << at);
          }, 0),
    );
    const sizeOf = values.scowl_size.map((v) => {
      const n = v === 'null' ? 0 : Number(v);
      return n > 0 ? n : 0;
    });
    const lengthOf = values.length.map((v) => Number.parseInt(v, 10));
    const triOf = (d: OpenDim) =>
      values[d].map((v) => {
        const at = TRI.indexOf(v as Tri);
        if (at < 0) throw new Error(`${d} holds an unknown value '${v}'`);
        return at;
      });
    const gbOf = triOf('gb_type');
    const instOf = triOf('wn_instance');
    const properOf = triOf('wk_proper_noun');

    const n = file.cells.length;
    this.cells = n;
    this.count = new Float64Array(n);
    this.listMask = new Uint8Array(n);
    this.lists = new Uint8Array(n);
    this.scowlSize = new Uint8Array(n);
    this.token = new Uint8Array(n);
    this.length = new Uint8Array(n);
    this.flagMask = new Uint16Array(n);
    this.gb = new Uint8Array(n);
    this.inst = new Uint8Array(n);
    this.proper = new Uint8Array(n);
    file.cells.forEach((cell, c) => {
      const [lb, sc, tk, ln, cl, gb, wi, pn, rows] = cell;
      this.count[c] = rows;
      this.listMask[c] = listMaskOf[lb];
      this.lists[c] = popcount(listMaskOf[lb]);
      this.scowlSize[c] = sizeOf[sc];
      this.token[c] = tk;
      this.length[c] = lengthOf[ln];
      this.flagMask[c] = flagMaskOf[cl];
      this.gb[c] = gbOf[gb];
      this.inst[c] = instOf[wi];
      this.proper[c] = properOf[pn];
    });
    this.total = this.count.reduce((a, b) => a + b, 0);
  }

  /** A test per cell for `sel`, leaving out the facet `skip`. */
  private compile(sel: OpenSelection, skip: OpenFacet | null): (c: number) => boolean {
    const tests: ((c: number) => boolean)[] = [];
    if (skip !== 'listedBy' && sel.listedBy?.length) {
      const need = sel.listedBy.reduce((m, s) => m | (1 << OPEN_LISTS.indexOf(s as OpenList)), 0);
      tests.push((c) => (this.listMask[c] & need) === need);
    }
    if (skip !== 'scowl' && sel.scowl != null) {
      const top = sel.scowl;
      tests.push((c) => this.scowlSize[c] > 0 && this.scowlSize[c] <= top);
    }
    if (skip !== 'minLists' && sel.minLists && sel.minLists > 1) {
      const k = sel.minLists;
      tests.push((c) => this.lists[c] >= k);
    }
    if (skip !== 'tokens' && sel.tokens?.length) {
      const ok = new Uint8Array(this.values.token_count.length);
      for (const v of sel.tokens) {
        const at = this.values.token_count.indexOf(v);
        if (at >= 0) ok[at] = 1;
      }
      tests.push((c) => ok[this.token[c]] === 1);
    }
    if (skip !== 'gbType' && sel.gbType && sel.gbType !== 'any') {
      const want = sel.gbType === 'with' ? 0 : 1;
      tests.push((c) => this.gb[c] === want);
    }
    if (skip !== 'flags' && sel.flags) {
      let need = 0;
      let refuse = 0;
      let plain: FlagRule = 'any';
      for (const [f, rule] of Object.entries(sel.flags)) {
        if (!rule || rule === 'any') continue;
        if (f === 'plain') {
          plain = rule;
          continue;
        }
        const bit = 1 << FLAGS.indexOf(f as Flag);
        if (rule === 'with') need |= bit;
        else refuse |= bit;
      }
      if (need || refuse) tests.push((c) => (this.flagMask[c] & need) === need && (this.flagMask[c] & refuse) === 0);
      if (plain === 'with') tests.push((c) => this.flagMask[c] === 0);
      if (plain === 'without') tests.push((c) => this.flagMask[c] !== 0);
    }
    if (skip !== 'noInstances' && sel.noInstances) tests.push((c) => this.inst[c] !== 0);
    if (skip !== 'noProperNouns' && sel.noProperNouns) tests.push((c) => this.proper[c] !== 0);
    if (skip !== 'length') {
      const lo = sel.minLength ?? null;
      const hi = sel.maxLength ?? null;
      if (lo !== null && lo > 1) tests.push((c) => this.length[c] >= lo);
      // the top bucket holds every length at or above the cap
      if (hi !== null && hi < this.lengthCap) tests.push((c) => this.length[c] <= hi);
    }
    return (c) => {
      for (const t of tests) if (!t(c)) return false;
      return true;
    };
  }

  /** Sums the rows `sel` selects, without the facet `skip`, into `size`
   *  buckets by `key`; a key below 0 counts in none. */
  private tally(sel: OpenSelection, skip: OpenFacet | null, size: number, key: (c: number) => number): number[] {
    const pass = this.compile(sel, skip);
    const out = new Array<number>(size).fill(0);
    for (let c = 0; c < this.cells; c++) {
      if (!pass(c)) continue;
      const k = key(c);
      if (k >= 0) out[k] += this.count[c];
    }
    return out;
  }

  /** The rows `sel` selects. */
  rows(sel: OpenSelection = {}): number {
    return this.tally(sel, null, 1, () => 0)[0];
  }

  /** The rows each open list lists, under `sel` without its own lists
   *  rule unless `keepOwn`; SCOWL's count keeps the SCOWL size chosen. */
  byList(sel: OpenSelection = {}, keepOwn = false): Map<OpenList, number> {
    const pass = this.compile(sel, keepOwn ? null : 'listedBy');
    const out = new Map<OpenList, number>(OPEN_LISTS.map((s) => [s, 0]));
    for (let c = 0; c < this.cells; c++) {
      if (!pass(c)) continue;
      const m = this.listMask[c];
      OPEN_LISTS.forEach((s, i) => {
        if (m & (1 << i)) out.set(s, out.get(s)! + this.count[c]);
      });
    }
    return out;
  }

  /** The rows SCOWL lists at each size, by the smallest size that holds
   *  them, under `sel` without its own SCOWL rule unless `keepOwn`. */
  byScowlSize(sel: OpenSelection = {}, keepOwn = false): Map<number, number> {
    const counts = this.tally(sel, keepOwn ? null : 'scowl', SCOWL_SIZES.length, (c) =>
      SCOWL_SIZES.indexOf(this.scowlSize[c] as (typeof SCOWL_SIZES)[number]),
    );
    return new Map(SCOWL_SIZES.map((s, i) => [s, counts[i]]));
  }

  /** The rows by the number of open lists that list them, 0 to 6 (0 is
   *  always empty), under `sel` without its own least number unless `keepOwn`. */
  byListCount(sel: OpenSelection = {}, keepOwn = false): number[] {
    return this.tally(sel, keepOwn ? null : 'minLists', OPEN_LISTS.length + 1, (c) => this.lists[c]);
  }

  /** The rows by token count, in the cube's values, under `sel` without its
   *  own tokens rule unless `keepOwn`. */
  byTokens(sel: OpenSelection = {}, keepOwn = false): Map<string, number> {
    const counts = this.tally(sel, keepOwn ? null : 'tokens', this.values.token_count.length, (c) => this.token[c]);
    return new Map(this.values.token_count.map((v, i) => [v, counts[i]]));
  }

  /** The rows that are a Google Books type, are not, and are not measured,
   *  under `sel` without its own rule unless `keepOwn`. */
  byGbType(sel: OpenSelection = {}, keepOwn = false): Map<Tri, number> {
    const counts = this.tally(sel, keepOwn ? null : 'gbType', 3, (c) => this.gb[c]);
    return new Map(TRI.map((v, i) => [v, counts[i]]));
  }

  /** The rows carrying each spelling class, and the plain rows, under `sel`
   *  without its own class rules unless `keepOwn`. */
  byFlag(sel: OpenSelection = {}, keepOwn = false): Map<OpenFlag | 'plain', number> {
    const pass = this.compile(sel, keepOwn ? null : 'flags');
    const out = new Map<OpenFlag | 'plain', number>([['plain', 0], ...OPEN_FLAGS.map((f) => [f, 0] as [OpenFlag, number])]);
    for (let c = 0; c < this.cells; c++) {
      if (!pass(c)) continue;
      const m = this.flagMask[c];
      if (m === 0) out.set('plain', out.get('plain')! + this.count[c]);
      OPEN_FLAGS.forEach((f) => {
        if (m & (1 << FLAGS.indexOf(f))) out.set(f, out.get(f)! + this.count[c]);
      });
    }
    return out;
  }

  /** The multiword rows WordNet records as instances, under `sel` without
   *  its own rule leaving them out. */
  instances(sel: OpenSelection = {}): number {
    return this.tally(sel, 'noInstances', 1, (c) => (this.inst[c] === 0 ? 0 : -1))[0];
  }

  /** The multiword rows under a Wiktionary proper-noun heading, under `sel`
   *  without its own rule leaving them out. */
  properNouns(sel: OpenSelection = {}): number {
    return this.tally(sel, 'noProperNouns', 1, (c) => (this.proper[c] === 0 ? 0 : -1))[0];
  }

  /** The rows by length, 1 to the cap (the cap's bucket holds every longer
   *  row), under `sel` without its own length bounds unless `keepOwn`. */
  byLength(sel: OpenSelection = {}, keepOwn = false): number[] {
    return this.tally(sel, keepOwn ? null : 'length', this.lengthCap, (c) => this.length[c] - 1);
  }
}

function popcount(m: number): number {
  let n = 0;
  for (let x = m; x; x &= x - 1) n++;
  return n;
}
