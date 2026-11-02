/**
 * The cube of version 1.0 (pipeline/research/release/figures.py): the count of rows
 * for every combination of 12 dimensions, over every row of the universe
 * config. Every chart and count on the site that filters the universe is
 * computed here from it, exactly; nothing is sampled or estimated.
 *
 * Two dimensions are decoded into what a reader filters by:
 * - `panel_sets` (the published lists that list a row, ';'-joined) into a
 *   bit per published list and the count of lists;
 * - `class_explicit` (the spelling classes, ';'-joined, or 'plain') into a
 *   bit per class.
 */

export const DIMENSIONS = [
  'intake_layer',
  'intake_kind',
  'provenance_class',
  'eol',
  'panel_sets',
  'class_explicit',
  'token_count',
  'length',
  'gb_type',
  'wordfreq_scored',
  'wikt_title_any',
  'model_or_engine',
] as const;

export type Dim = (typeof DIMENSIONS)[number];

export interface CubeFile {
  readonly version: string;
  readonly dataset: string;
  readonly built_on: string;
  readonly caps: Readonly<Record<string, number>>;
  readonly dimensions: readonly { readonly name: string; readonly values: readonly string[] }[];
  readonly cells: readonly (readonly number[])[];
}

/** The 8 published lists, in the order of `panel_sets`. */
export const PUBLISHED_SETS = [
  'wordnet',
  'wiktionary_english',
  'hunspell_en_US',
  'hunspell_en_GB',
  'hunspell_en_CA',
  'hunspell_en_AU',
  'enable1',
  'scowl',
] as const;

/** The spelling classes a row can carry; a row with none is plain a to z. */
export const FLAGS = [
  'hyphenated',
  'accented',
  'diaeresis',
  'ligature',
  'apostrophe-form',
  'contraction',
  's-final',
  'spaced',
] as const;

export type Flag = (typeof FLAGS)[number];

/** 'any' ignores a class; 'with' keeps rows that carry it; 'without' drops them. */
export type FlagRule = 'any' | 'with' | 'without';

/** A selection of rows. Every field left at its default selects everything. */
export interface Selection {
  /** for a dimension, the values a row may take; missing or empty is any */
  readonly values?: Partial<Record<Dim, readonly string[]>>;
  /** the published lists that must all list a row */
  readonly listedBy?: readonly string[];
  /** the least number of published lists that list a row */
  readonly minLists?: number;
  /** a rule per spelling class; 'plain' with 'with' keeps plain rows only */
  readonly flags?: Partial<Record<Flag | 'plain', FlagRule>>;
  /** the shortest and longest length, in characters; the cube caps length,
   *  so the longest bucket holds every row at or above its value */
  readonly minLength?: number | null;
  readonly maxLength?: number | null;
}

/** The parts of a selection a breakdown can leave out, so a facet counts
 *  under every other filter. */
export type Facet = Dim | 'listedBy' | 'minLists' | 'flags' | 'length';

export class Cube {
  readonly version: string;
  readonly builtOn: string;
  readonly values: Readonly<Record<Dim, readonly string[]>>;
  readonly lengthCap: number;
  readonly total: number;
  readonly cells: number;
  private readonly idx: Readonly<Record<Dim, Uint16Array>>;
  private readonly count: Float64Array;
  private readonly setMask: Uint16Array;
  private readonly lists: Uint8Array;
  private readonly flagMask: Uint16Array;
  private readonly length: Uint8Array;

  constructor(file: CubeFile) {
    const names = file.dimensions.map((d) => d.name);
    if (names.join() !== DIMENSIONS.join()) {
      throw new Error(`the cube's dimensions are ${names.join(', ')}, not the ones this site reads`);
    }
    this.version = file.version;
    this.builtOn = file.built_on;
    this.lengthCap = file.caps.length;
    const values = {} as Record<Dim, readonly string[]>;
    DIMENSIONS.forEach((d, i) => (values[d] = file.dimensions[i].values));
    this.values = values;

    const n = file.cells.length;
    this.cells = n;
    const idx = {} as Record<Dim, Uint16Array>;
    for (const d of DIMENSIONS) idx[d] = new Uint16Array(n);
    this.count = new Float64Array(n);
    file.cells.forEach((cell, c) => {
      DIMENSIONS.forEach((d, i) => (idx[d][c] = cell[i]));
      this.count[c] = cell[DIMENSIONS.length];
    });
    this.idx = idx;
    this.total = this.count.reduce((a, b) => a + b, 0);

    // decode the 2 joined dimensions once per value, then per cell
    const setMaskOf = values.panel_sets.map((v) =>
      v.split(';').reduce((m, s) => {
        const at = PUBLISHED_SETS.indexOf(s as (typeof PUBLISHED_SETS)[number]);
        if (s && at < 0) throw new Error(`panel_sets names an unknown list '${s}'`);
        return s ? m | (1 << at) : m;
      }, 0),
    );
    const flagMaskOf = values.class_explicit.map((v) =>
      v === 'plain'
        ? 0
        : v.split(';').reduce((m, f) => {
            const at = FLAGS.indexOf(f as Flag);
            if (at < 0) throw new Error(`class_explicit names an unknown class '${f}'`);
            return m | (1 << at);
          }, 0),
    );
    const lengthOf = values.length.map((v) => Number.parseInt(v, 10));
    this.setMask = new Uint16Array(n);
    this.lists = new Uint8Array(n);
    this.flagMask = new Uint16Array(n);
    this.length = new Uint8Array(n);
    for (let c = 0; c < n; c++) {
      const m = setMaskOf[idx.panel_sets[c]];
      this.setMask[c] = m;
      this.lists[c] = popcount(m);
      this.flagMask[c] = flagMaskOf[idx.class_explicit[c]];
      this.length[c] = lengthOf[idx.length[c]];
    }
  }

  /** A test per cell for `sel`, leaving out the facet `skip`. */
  private compile(sel: Selection, skip: Facet | null): (c: number) => boolean {
    const tests: ((c: number) => boolean)[] = [];
    for (const d of DIMENSIONS) {
      const allowed = sel.values?.[d];
      if (d === skip || !allowed || allowed.length === 0) continue;
      const ok = new Uint8Array(this.values[d].length);
      for (const v of allowed) {
        const at = this.values[d].indexOf(v);
        if (at >= 0) ok[at] = 1;
      }
      const col = this.idx[d];
      tests.push((c) => ok[col[c]] === 1);
    }
    if (skip !== 'listedBy' && sel.listedBy && sel.listedBy.length) {
      const need = sel.listedBy.reduce(
        (m, s) => m | (1 << PUBLISHED_SETS.indexOf(s as (typeof PUBLISHED_SETS)[number])),
        0,
      );
      tests.push((c) => (this.setMask[c] & need) === need);
    }
    if (skip !== 'minLists' && sel.minLists) {
      const k = sel.minLists;
      tests.push((c) => this.lists[c] >= k);
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
    if (skip !== 'length') {
      const lo = sel.minLength ?? null;
      const hi = sel.maxLength ?? null;
      if (lo !== null) tests.push((c) => this.length[c] >= lo);
      // the top bucket holds every length at or above the cap
      if (hi !== null && hi < this.lengthCap) tests.push((c) => this.length[c] <= hi);
    }
    return (c) => {
      for (const t of tests) if (!t(c)) return false;
      return true;
    };
  }

  /** The rows `sel` selects. */
  rows(sel: Selection = {}): number {
    const pass = this.compile(sel, null);
    let n = 0;
    for (let c = 0; c < this.cells; c++) if (pass(c)) n += this.count[c];
    return n;
  }

  /** The rows of each value of a dimension, under `sel` with that
   *  dimension's own filter left out unless `keepOwn`. */
  by(dim: Dim, sel: Selection = {}, keepOwn = false): Map<string, number> {
    const pass = this.compile(sel, keepOwn ? null : dim);
    const out = new Map(this.values[dim].map((v) => [v, 0]));
    const col = this.idx[dim];
    const vals = this.values[dim];
    for (let c = 0; c < this.cells; c++) {
      if (pass(c)) out.set(vals[col[c]], out.get(vals[col[c]])! + this.count[c]);
    }
    return out;
  }

  /** The rows each published list lists, under `sel` without its own
   *  `listedBy` filter unless `keepOwn`. */
  byList(sel: Selection = {}, keepOwn = false): Map<string, number> {
    const pass = this.compile(sel, keepOwn ? null : 'listedBy');
    const out = new Map<string, number>(PUBLISHED_SETS.map((s) => [s, 0]));
    for (let c = 0; c < this.cells; c++) {
      if (!pass(c)) continue;
      const m = this.setMask[c];
      PUBLISHED_SETS.forEach((s, i) => {
        if (m & (1 << i)) out.set(s, out.get(s)! + this.count[c]);
      });
    }
    return out;
  }

  /** The rows by the number of published lists that list them, 0 to 8,
   *  under `sel` without its own least number unless `keepOwn`. */
  byListCount(sel: Selection = {}, keepOwn = false): number[] {
    const pass = this.compile(sel, keepOwn ? null : 'minLists');
    const out = new Array(PUBLISHED_SETS.length + 1).fill(0);
    for (let c = 0; c < this.cells; c++) if (pass(c)) out[this.lists[c]] += this.count[c];
    return out;
  }

  /** The rows carrying each spelling class, and the plain rows, under
   *  `sel` without its own class rules unless `keepOwn`. */
  byFlag(sel: Selection = {}, keepOwn = false): Map<Flag | 'plain', number> {
    const pass = this.compile(sel, keepOwn ? null : 'flags');
    const out = new Map<Flag | 'plain', number>([['plain', 0], ...FLAGS.map((f) => [f, 0] as [Flag, number])]);
    for (let c = 0; c < this.cells; c++) {
      if (!pass(c)) continue;
      const m = this.flagMask[c];
      if (m === 0) out.set('plain', out.get('plain')! + this.count[c]);
      FLAGS.forEach((f, i) => {
        if (m & (1 << i)) out.set(f, out.get(f)! + this.count[c]);
      });
    }
    return out;
  }

  /** The rows by length, 1 to the cap (the cap's bucket holds every longer
   *  row), under `sel` without its own length bounds unless `keepOwn`. */
  byLength(sel: Selection = {}, keepOwn = false): number[] {
    const pass = this.compile(sel, keepOwn ? null : 'length');
    const out = new Array(this.lengthCap).fill(0);
    for (let c = 0; c < this.cells; c++) if (pass(c)) out[this.length[c] - 1] += this.count[c];
    return out;
  }
}

function popcount(m: number): number {
  let n = 0;
  for (let x = m; x; x &= x - 1) n++;
  return n;
}
