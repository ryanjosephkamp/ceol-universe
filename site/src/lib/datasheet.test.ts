/**
 * The datasheet states the composer's counts: every breakdown of a list sums
 * to the list's rows where a row falls in exactly 1 value, the definition says
 * each criterion, and the Markdown and the CSV carry the same figures.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { Cube, type CubeFile, type Selection } from './cube';
import { usDate } from './dates';
import { buildSheet, describeSelection, fileStem, lengthSummary, sheetCsv, sheetMarkdown, type SheetMeta } from './datasheet';
import { fixedSelections, randomSelections } from './test-selections';

const REPO = resolve(__dirname, '../../..');
const cube = new Cube(
  JSON.parse(readFileSync(resolve(REPO, 'pipeline/research/release/figures/v1.0/cube.json'), 'utf-8')) as CubeFile,
);
const cap = cube.lengthCap;
const meta: SheetMeta = {
  title: '',
  author: 'A team',
  note: 'For a word game.',
  made: new Date(2026, 9, 26),
  link: 'https://example.test/compose/?lists=4',
  citation: 'The card says how to cite it.',
  file: { path: 'data/universe.parquet', sha256: 'abc' },
};

// the breakdowns in which every row falls in exactly 1 value
const EXCLUSIVE = ['length', 'provenance', 'lists', 'tokens', 'gb_type', 'wordfreq_scored', 'wikt_title_any', 'layer', 'kind', 'model_or_engine', 'eol'];

describe('the datasheet', () => {
  it("states the cube's count and sums each exclusive breakdown to it", () => {
    for (const sel of [...fixedSelections(cube), ...randomSelections(cube, 24)]) {
      const sheet = buildSheet(sel, cube);
      expect(sheet.rows).toBe(cube.rows(sel));
      for (const t of sheet.tables) {
        expect(t.total).toBe(sheet.rows);
        if (EXCLUSIVE.includes(t.id)) expect(t.rows.reduce((a, r) => a + r.value, 0), `${t.id} of ${JSON.stringify(sel)}`).toBe(sheet.rows);
      }
      expect(sheet.tables.map((t) => t.id)).toEqual(expect.arrayContaining(EXCLUSIVE));
    }
  });

  it('says each criterion in a plain sentence', () => {
    expect(describeSelection({}, cap)).toEqual(['Every row of the universe: no criterion is set.']);
    const sel: Selection = {
      minLists: 4,
      listedBy: ['wordnet', 'scowl'],
      flags: { plain: 'with', hyphenated: 'without' },
      values: { token_count: ['1'], eol: ['true'], gb_type: ['true', 'null'] },
      minLength: 3,
      maxLength: 8,
    };
    expect(describeSelection(sel, cap)).toEqual([
      'Listed by at least 4 of the 8 published lists.',
      'Listed by each of WordNet and SCOWL.',
      'Plain a to z: no spelling class.',
      'Not in the class Hyphenated.',
      '1 token.',
      'From 3 to 8 characters long.',
      'A Google Books 1-gram type: Yes or Not measured.',
      "On the English OpenList's valid list at revision 08ae92b8.",
    ]);
    // a choice of every value filters nothing, as in the code
    expect(describeSelection({ values: { eol: ['true', 'false'] } }, cap)).toHaveLength(1);
  });

  it('summarizes lengths by rank, the top bucket as "or more"', () => {
    expect(lengthSummary([0, 2, 1, 1], 4)).toEqual({ shortest: '2', longest: '4 or more', median: '2', lower: '2', upper: '3' });
    expect(lengthSummary([0, 0, 0], 3)).toBeNull();
  });

  it('writes the same figures as Markdown and as CSV', () => {
    const sel = fixedSelections(cube)[2];
    const sheet = buildSheet(sel, cube);
    const md = sheetMarkdown(sheet, meta);
    expect(md).toContain('# A list from the CEOL Universe');
    expect(md).toContain('By A team. Made October 26, 2026');
    expect(md).toContain(`${sheet.rows.toLocaleString('en-US')} rows`);
    expect(md).toContain(sheet.code.duckdb);
    expect(md).toContain(meta.link);
    expect(md).not.toMatch(/\bvalid word/i);
    const csv = sheetCsv(sheet).trimEnd().split('\n');
    expect(csv[0]).toBe('table,value,rows,share');
    expect(csv[1]).toBe(`list,rows of the universe,${sheet.rows},${(sheet.rows / sheet.universe).toFixed(6)}`);
    expect(csv).toHaveLength(2 + sheet.tables.reduce((n, t) => n + t.rows.length, 0));
  });

  it('names files from titles and writes US dates', () => {
    expect(fileStem('Naïve words, 3 to 8!')).toBe('naive-words-3-to-8');
    expect(fileStem('***')).toBe('ceol-universe-list');
    expect(usDate('2026-10-25')).toBe('October 25, 2026');
  });
});
