/**
 * The selections the tests run on version 1.0's own file: a fixed set that
 * touches every kind of criterion, and a seeded random set beside it. Shared by
 * the generated code's test and the list download's test.
 */

import { DIMENSIONS, FLAGS, PUBLISHED_SETS, type Cube, type Dim, type Selection } from './cube';
import { normalizeSelection, readSelection } from './selection-url';

export function fixedSelections(cube: Cube): Selection[] {
  return [
    {},
    { minLists: 1 },
    { minLists: 4, flags: { plain: 'with' }, values: { token_count: ['1'] } },
    { listedBy: ['wordnet', 'scowl'] },
    { listedBy: ['enable1'], flags: { 'apostrophe-form': 'without', hyphenated: 'without' } },
    { values: { eol: ['true'] } },
    { values: { eol: ['false'], provenance_class: ['neither', 'channel_only'] } },
    { values: { gb_type: ['null'] } },
    { values: { gb_type: ['true', 'null'], wordfreq_scored: ['false'] } },
    { values: { wikt_title_any: ['true'] }, minLength: 3, maxLength: 7 },
    { values: { token_count: ['1', '4+'] } },
    { values: { token_count: ['2', '3'] }, flags: { 'apostrophe-form': 'with' } },
    { values: { intake_layer: ['c1_exceptions', 'c4_additions'], intake_kind: ['derived'] } },
    { values: { model_or_engine: ['none'] }, minLength: 25 },
    { values: { model_or_engine: ['engine_generated'] } },
    { flags: { plain: 'without', spaced: 'without' } },
    { flags: { contraction: 'with' }, maxLength: 6 },
    { flags: { diaeresis: 'with', accented: 'with' } },
    { flags: { 's-final': 'with' }, minLists: 2 },
    { flags: { ligature: 'with' } },
    // shared addresses that once counted differently from their code: a length
    // given as a dimension, a length past the cube's cap, an unknown Boolean
    ...['?d.length=1', '?len=26-', '?d.eol=invalid'].map((q) => normalizeSelection(readSelection(q), cube)),
  ];
}

/** A seeded generator, so the random selections are the same every run. */
function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 2 ** 32;
  };
}

export function randomSelections(cube: Cube, n: number, seed = 20261025): Selection[] {
  const r = rng(seed);
  const pick = <T,>(xs: readonly T[]) => xs[Math.floor(r() * xs.length)];
  const plainDims: Dim[] = DIMENSIONS.filter((d) => !['panel_sets', 'class_explicit', 'length'].includes(d));
  const out: Selection[] = [];
  for (let i = 0; i < n; i++) {
    const values: Partial<Record<Dim, string[]>> = {};
    for (const d of plainDims) {
      if (r() < 0.25) {
        const vals = cube.values[d].filter(() => r() < 0.5);
        if (vals.length) values[d] = vals;
      }
    }
    const flags: Record<string, 'any' | 'with' | 'without'> = {};
    for (const f of [...FLAGS, 'plain']) if (r() < 0.15) flags[f] = pick(['with', 'without'] as const);
    const sel: Selection = {
      values,
      flags,
      listedBy: PUBLISHED_SETS.filter(() => r() < 0.08),
      minLists: r() < 0.3 ? Math.floor(r() * 5) : 0,
      minLength: r() < 0.3 ? 1 + Math.floor(r() * 8) : null,
      maxLength: r() < 0.3 ? 6 + Math.floor(r() * 22) : null,
    };
    out.push(sel);
  }
  return out;
}
