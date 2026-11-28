/**
 * The open cube's engine against the open subset's record, which the
 * subset's build counted from its own file by other code: every count the
 * page derives from the cube must equal the record's. Then the page's own
 * parts on top of it: the breakdowns sum to the list, a shared address
 * reopens the same list, and the datasheet states the file, the commit, the
 * license, and the attribution. None of this needs the data files.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { usDate } from './dates';
import { OPEN_COMMIT, OPEN_PARQUET, openCodeFor } from './open-codegen';
import { OPEN_LISTS, OpenCube, SCOWL_SIZES, type OpenCubeFile, type OpenSelection } from './open-cube';
import { describeOpenSelection, openSheetMarkdown, type OpenSheetMeta } from './open-datasheet';
import { openRowTest } from './open-filter';
import {
  ALL_QUERY,
  STORE_KEY,
  initialOpenSelection,
  normalizeOpenSelection,
  openLink,
  openSelectionQuery,
  readOpenSelection,
  storeSelection,
  storedQuery,
} from './open-url';
import type { Layout } from './list-read';
import { fixedOpenSelections, randomOpenSelections } from './test-open-selections';

const REPO = resolve(__dirname, '../../..');
const RELEASE = resolve(REPO, 'pipeline/research/release');
const read = (name: string) => JSON.parse(readFileSync(resolve(RELEASE, name), 'utf-8'));
const cube = new OpenCube(read('open_cube_v1.0.json') as OpenCubeFile);
const layout = read('layout_open_v1.0.json') as Layout;
const record = read('open_subset_v1.0.json');
const counts = record.configs.find((c: { config: string }) => c.config === 'open-lists').counts;
const upload = read('hf_upload_open_v1.0.json');
const cap = cube.lengthCap;
const SINGLE: OpenSelection = { tokens: ['1'] };
const MULTI: OpenSelection = { tokens: ['2', '3', '4+'] };
const sum = (xs: Iterable<number>) => [...xs].reduce((a, b) => a + b, 0);

describe('the open cube', () => {
  it('holds every row of open-lists, from the file at the upload commit', () => {
    expect(cube.total).toBe(counts.rows);
    expect(cube.total).toBe(layout.rows);
    expect(cube.source.sha256).toBe(layout.sha256);
    expect(cube.commit).toBe(upload.commit);
    expect(OPEN_COMMIT).toBe(upload.commit);
    expect(upload.files.find((f: { path: string }) => f.path === layout.hub_path).sha256).toBe(layout.sha256);
  });

  it("states the record's counts of single and multiword rows, by list", () => {
    expect(cube.rows(SINGLE)).toBe(counts.single);
    expect(cube.rows(MULTI)).toBe(counts.multiword);
    const lists = cube.byList(SINGLE);
    for (const s of OPEN_LISTS) expect([s, lists.get(s)]).toEqual([s, counts.single_by_list[s]]);
    const byCount = cube.byListCount(SINGLE);
    for (const [k, n] of Object.entries(counts.single_by_list_count)) expect([k, byCount[Number(k)]]).toEqual([k, n]);
    expect(byCount[0]).toBe(0);
    const multi = cube.byList(MULTI);
    expect(multi.get('wordnet')).toBe(counts.multiword_by_listing.wordnet + counts.multiword_by_listing['wordnet;wiktionary_english']);
    expect(cube.rows({ ...MULTI, listedBy: ['wordnet', 'wiktionary_english'] })).toBe(counts.multiword_by_listing['wordnet;wiktionary_english']);
    expect(sum(['hunspell_en_US', 'hunspell_en_CA', 'hunspell_en_AU', 'scowl'].map((s) => multi.get(s as 'scowl')!))).toBe(0);
  });

  it("states the record's SCOWL sizes, Google Books types, classes, and properness signals", () => {
    const sizes = cube.byScowlSize(SINGLE);
    for (const s of SCOWL_SIZES) expect([s, sizes.get(s)]).toEqual([s, counts.single_by_scowl_size[String(s)]]);
    expect(cube.rows({ scowl: 70 })).toBe(counts.single_by_list.scowl);
    const gb = cube.byGbType();
    expect(gb.get('true')).toBe(counts.single_gb_type);
    expect(gb.get('null')).toBe(counts.multiword);
    expect(cube.rows({ gbType: 'without' })).toBe(counts.single - counts.single_gb_type);
    const flags = cube.byFlag(SINGLE);
    for (const [f, n] of Object.entries(counts.single_by_class)) expect([f, flags.get(f as 'plain')]).toEqual([f, n]);
    expect(cube.rows({ flags: { plain: 'with' } })).toBe(counts.single_by_class.plain);
    expect(cube.instances()).toBe(counts.multiword_true.wn_instance);
    expect(cube.properNouns()).toBe(counts.multiword_true.wk_proper_noun);
    expect(cube.rows({ noInstances: true })).toBe(counts.rows - counts.multiword_true.wn_instance);
  });

  it('breaks every list into parts that sum to it', () => {
    for (const sel of [...fixedOpenSelections(cube), ...randomOpenSelections(cube, 40)]) {
      const n = cube.rows(sel);
      const where = JSON.stringify(sel);
      expect([where, sum(cube.byLength(sel, true))]).toEqual([where, n]);
      expect([where, sum(cube.byTokens(sel, true).values())]).toEqual([where, n]);
      expect([where, sum(cube.byGbType(sel, true).values())]).toEqual([where, n]);
      expect([where, sum(cube.byListCount(sel, true))]).toEqual([where, n]);
      // the facet left out holds the list within it
      expect(sum(cube.byLength(sel))).toBeGreaterThanOrEqual(n);
      expect(sum(cube.byListCount(sel))).toBeGreaterThanOrEqual(n);
    }
  });

  it("states beside each choice what the page's notes say it states", () => {
    for (const sel of [...fixedOpenSelections(cube), ...randomOpenSelections(cube, 40)]) {
      const where = JSON.stringify(sel);
      const others = (patch: Partial<OpenSelection>) => cube.rows({ ...sel, ...patch });
      // a list: the rows it lists, with the lists checked set aside
      const sets = cube.byList(sel);
      for (const s of ['wordnet', 'wiktionary_english', 'hunspell_en_US', 'hunspell_en_CA', 'hunspell_en_AU'] as const) {
        expect([where, s, sets.get(s)]).toEqual([where, s, others({ listedBy: [s] })]);
      }
      // a SCOWL size, a least number of lists, a token count, Google Books:
      // the rows that choice leaves
      const sizes = cube.byScowlSize(sel);
      let upTo = 0;
      for (const size of SCOWL_SIZES) {
        upTo += sizes.get(size)!;
        expect([where, size, upTo]).toEqual([where, size, others({ scowl: size })]);
      }
      const lists = cube.byListCount(sel);
      for (let k = 1; k <= 6; k++) expect([where, k, sum(lists.slice(k))]).toEqual([where, k, others({ minLists: k })]);
      for (const [t, n] of cube.byTokens(sel)) expect([where, t, n]).toEqual([where, t, others({ tokens: [t] })]);
      const gb = cube.byGbType(sel);
      expect([where, gb.get('true'), gb.get('false')]).toEqual([where, others({ gbType: 'with' }), others({ gbType: 'without' })]);
      // a class: its members, with every class rule set aside
      for (const [f, n] of cube.byFlag(sel)) expect([where, f, n]).toEqual([where, f, others({ flags: { [f]: 'with' } })]);
      // a properness box: the rows it leaves out
      expect([where, cube.instances(sel)]).toEqual([where, others({ noInstances: false }) - others({ noInstances: true })]);
      expect([where, cube.properNouns(sel)]).toEqual([where, others({ noProperNouns: false }) - others({ noProperNouns: true })]);
    }
  });

  it('reads only the columns the layout holds', () => {
    for (const sel of [...fixedOpenSelections(cube), ...randomOpenSelections(cube, 40)]) {
      for (const c of openRowTest(sel, cap).columns) expect(layout.row_groups[0].columns[c], c).toBeDefined();
    }
  });
});

/** A device's storage, as the page reads and writes it. */
function memoryStorage(initial: Record<string, string> = {}) {
  const m = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
  };
}

describe('a link and a stored list', () => {
  const ORIGIN = 'https://example.test';
  const search = (link: string) => new URL(link).search;

  it('reopens every row from a link to every row, whatever the recipient stored', () => {
    const theirs = memoryStorage({ [STORE_KEY]: '?tok=1' });
    expect(cube.rows(initialOpenSelection('', theirs))).toBe(counts.single);
    const link = openLink(ORIGIN, {});
    expect(search(link)).toBe(ALL_QUERY);
    expect(cube.rows(normalizeOpenSelection(initialOpenSelection(search(link), theirs), cube))).toBe(cube.total);
  });

  it('reopens each list from its link, whatever the recipient stored, and a bare address the stored list', () => {
    const theirs = memoryStorage({ [STORE_KEY]: '?scowl=10&f.plain=with' });
    const stored = normalizeOpenSelection(initialOpenSelection('', theirs), cube);
    expect(cube.rows(stored)).toBe(cube.rows({ scowl: 10, flags: { plain: 'with' } }));
    for (const sel of [{}, ...fixedOpenSelections(cube), ...randomOpenSelections(cube, 40)]) {
      const norm = normalizeOpenSelection(sel, cube);
      const opened = normalizeOpenSelection(initialOpenSelection(search(openLink(ORIGIN, norm)), theirs), cube);
      expect([openSelectionQuery(norm), cube.rows(opened)]).toEqual([openSelectionQuery(opened), cube.rows(norm)]);
    }
  });

  it('stores the last list, and every row as no entry', () => {
    const mine = memoryStorage({ [STORE_KEY]: '?tok=1' });
    storeSelection(mine, { scowl: 35 });
    expect(storedQuery(mine)).toBe('?scowl=35');
    storeSelection(mine, {});
    expect(storedQuery(mine)).toBe('');
    expect(cube.rows(initialOpenSelection('', mine))).toBe(cube.total);
    // storage refused, as in a private window
    const refused = { getItem: () => { throw new Error('denied'); } };
    expect(storedQuery(refused)).toBe('');
  });
});

describe('a shared address', () => {
  it('reopens the same list', () => {
    for (const sel of [...fixedOpenSelections(cube), ...randomOpenSelections(cube, 40)]) {
      const norm = normalizeOpenSelection(sel, cube);
      const again = normalizeOpenSelection(readOpenSelection(openSelectionQuery(norm)), cube);
      expect([openSelectionQuery(norm), cube.rows(again)]).toEqual([openSelectionQuery(again), cube.rows(sel)]);
    }
  });

  it('holds what the cube and the code cannot select inside what they can', () => {
    const past = normalizeOpenSelection(readOpenSelection('?len=30-'), cube);
    expect(past.minLength).toBe(cap);
    expect(cube.rows(past)).toBe(cube.byLength()[cap - 1]);
    expect(readOpenSelection('?scowl=45').scowl).toBeNull();
    expect(normalizeOpenSelection(readOpenSelection('?tok=1~9'), cube).tokens).toEqual(['1']);
    expect(readOpenSelection('?by=enable1~wordnet').listedBy).toEqual(['wordnet']);
    expect(openSelectionQuery({ minLists: 1, gbType: 'any', flags: { plain: 'any' } })).toBe('');
  });
});

describe('the code and the datasheet', () => {
  it('read the file at the upload commit', () => {
    expect(OPEN_PARQUET).toBe(`hf://datasets/ryanjosephkamp/ceol-universe-open@${upload.commit}/data/open-lists.parquet`);
    const code = openCodeFor({ scowl: 35, noInstances: true }, 12, cap);
    expect(code.duckdb).toContain(OPEN_PARQUET);
    expect(code.duckdb).toContain('scowl_size BETWEEN 10 AND 35');
    expect(code.duckdb).toContain('wn_instance IS NOT TRUE');
    expect(code.pandas).toContain(`revision="${upload.commit}"`);
    expect(code.pandas).toContain('"open-lists"');
    expect(code.pandas).toContain('select_columns(["word", "scowl_size", "wn_instance"])');
    expect(code.pandas).toContain('][["word"]]');
    expect(openCodeFor({}, 1, cap).pandas).toContain('rows = df[["word"]]');
  });

  it('describe every criterion', () => {
    const sel: OpenSelection = {
      minLists: 2,
      listedBy: ['wordnet', 'hunspell_en_US'],
      scowl: 50,
      tokens: ['1'],
      gbType: 'without',
      flags: { plain: 'with', hyphenated: 'without' },
      noInstances: true,
      noProperNouns: true,
      minLength: 3,
      maxLength: 9,
    };
    const lines = describeOpenSelection(sel, cap);
    expect(lines).toHaveLength(10);
    expect(lines.join(' ')).toContain('SCOWL at a size of 10 to 50');
    expect(describeOpenSelection({}, cap)).toEqual(['Every row of the open subset: no criterion is set.']);
  });

  it("states the list's count, its source, its license, and the file's attribution", () => {
    const meta: OpenSheetMeta = {
      made: new Date(2026, 10, 27),
      link: 'https://example.test/compose/open/?scowl=35',
      citation: 'The card says how to cite it.',
      file: {
        path: layout.hub_path,
        bytes: layout.bytes,
        sha256: layout.sha256,
        license: layout.metadata!['ceol.license'],
        attribution: layout.metadata!['ceol.attribution'],
      },
    };
    const sel: OpenSelection = { scowl: 35 };
    const md = openSheetMarkdown(sel, cube, meta);
    expect(md).toContain(`${cube.rows(sel).toLocaleString('en-US')} rows`);
    expect(md).toContain(usDate(meta.made));
    expect(md).toContain(upload.commit);
    expect(md).toContain(layout.sha256);
    expect(md).toContain('ryanjosephkamp/ceol-universe-open');
    expect(md).toContain('CC BY-SA 4.0');
    expect(layout.metadata!['ceol.license']).toBe(record.license);
    expect(md).toContain(`> ${layout.metadata!['ceol.attribution']}`);
    expect(md).toContain(meta.citation);
    expect(md).toContain(meta.link);
    expect(md).toContain('Listed by SCOWL at a size of 10 to 35.');
  });
});
