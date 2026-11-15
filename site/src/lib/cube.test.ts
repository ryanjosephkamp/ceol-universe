/**
 * The cube engine against the figures file, which the pipeline computes from
 * the release files by other code: every count the site derives from the cube
 * must equal the figure the pipeline states for it.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { Cube, FLAGS, PUBLISHED_SETS, type CubeFile } from './cube';

const REPO = resolve(__dirname, '../../..');
const DIR = resolve(REPO, 'pipeline/research/release/figures/v1.0');
const cube = new Cube(JSON.parse(readFileSync(resolve(DIR, 'cube.json'), 'utf-8')) as CubeFile);
const figures = new Map<string, number>(
  (JSON.parse(readFileSync(resolve(DIR, 'figures.json'), 'utf-8')).figures as { id: string; value: number }[]).map(
    (f) => [f.id, f.value],
  ),
);
const fig = (id: string) => {
  const v = figures.get(id);
  if (v === undefined) throw new Error(`no figure ${id}`);
  return v;
};

describe('the cube', () => {
  it('holds every row of the universe config', () => {
    expect(cube.total).toBe(fig('rows'));
    expect(cube.rows()).toBe(fig('config.universe.rows'));
  });

  it('counts each value of the plain dimensions as the figures do', () => {
    for (const dim of ['intake_layer', 'intake_kind', 'provenance_class', 'model_or_engine', 'token_count'] as const) {
      for (const [v, n] of cube.by(dim)) expect([dim, v, n]).toEqual([dim, v, fig(`rows.by_${dim}.${v}`)]);
    }
    for (const [v, n] of cube.by('class_explicit')) {
      if (n) expect([v, n]).toEqual([v, fig(`rows.by_class_explicit.${v}`)]);
    }
  });

  it('counts the boolean columns as the figures do', () => {
    expect(cube.rows({ values: { eol: ['true'] } })).toBe(fig('rows.eol'));
    expect(cube.rows({ values: { gb_type: ['true'] } })).toBe(fig('rows.gb_type'));
    expect(cube.rows({ values: { wordfreq_scored: ['true'] } })).toBe(fig('rows.wordfreq_scored'));
    expect(cube.rows({ values: { wikt_title_any: ['true'] } })).toBe(fig('rows.wikt_title_any'));
  });

  it('decodes the published lists: each list, and the panel-listed config', () => {
    for (const [s, n] of cube.byList()) expect([s, n]).toEqual([s, fig(`rows.listed_by.${s}`)]);
    expect(cube.rows({ minLists: 1 })).toBe(fig('config.panel-listed.rows'));
    expect(cube.byListCount().reduce((a, b) => a + b, 0)).toBe(cube.total);
    expect(cube.rows({ listedBy: [...PUBLISHED_SETS] })).toBe(cube.byListCount()[PUBLISHED_SETS.length]);
  });

  it('decodes the spelling classes: the exceptions and the spaced configs', () => {
    const exceptions = ['hyphenated', 'accented', 'contraction', 'apostrophe-form', 'ligature', 'diaeresis'] as const;
    const notExceptional = cube.rows({ flags: Object.fromEntries(exceptions.map((f) => [f, 'without'])) });
    expect(cube.total - notExceptional).toBe(fig('config.exceptions.rows'));
    expect(cube.rows({ values: { token_count: ['2', '3', '4+'] } })).toBe(fig('config.spaced.rows'));
    expect(cube.rows({ flags: { spaced: 'with' } })).toBe(fig('config.spaced.rows'));
    const flags = cube.byFlag();
    expect(flags.get('spaced')).toBe(fig('config.spaced.rows'));
    expect(cube.rows({ flags: { plain: 'with' } })).toBe(flags.get('plain'));
    expect(FLAGS.length).toBe(8);
  });

  it("reproduces the card's limitation counts", () => {
    const inherited = ['eol_valid', 'eol_invalid'];
    expect(
      cube.rows({ values: { intake_layer: inherited, gb_type: ['true'], panel_sets: [''] } }),
    ).toBe(fig('rows.inherited_google_books_no_published_set'));
    expect(
      cube.rows({ values: { token_count: ['1'], panel_sets: [''], gb_type: ['false'], wordfreq_scored: ['false'] } }),
    ).toBe(fig('rows.single_token_no_published_set_no_corpus'));
  });

  it('keeps the length buckets whole, the last one holding every longer row', () => {
    const lengths = cube.byLength();
    expect(lengths.length).toBe(cube.lengthCap);
    expect(lengths.reduce((a, b) => a + b, 0)).toBe(cube.total);
    expect(cube.rows({ minLength: cube.lengthCap })).toBe(lengths[cube.lengthCap - 1]);
    expect(cube.rows({ minLength: 3, maxLength: 5 })).toBe(lengths[2] + lengths[3] + lengths[4]);
  });

  it('leaves a facet out of its own breakdown, and keeps every other filter', () => {
    const sel = { values: { provenance_class: ['neither'], eol: ['true'] } };
    const byProv = cube.by('provenance_class', sel);
    expect([...byProv.values()].reduce((a, b) => a + b, 0)).toBe(cube.rows({ values: { eol: ['true'] } }));
    expect(cube.by('provenance_class', sel, true).get('channel_only')).toBe(0);
  });
});
