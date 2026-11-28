/**
 * The selections the tests run on the open subset's own file: a fixed set
 * that touches every kind of criterion, and a seeded random set beside it.
 * Shared by the open cube's test and the open download's test.
 */

import type { FlagRule } from './cube';
import { NAMED_LISTS, OPEN_FLAGS, SCOWL_SIZES, type OpenCube, type OpenSelection } from './open-cube';
import { normalizeOpenSelection, readOpenSelection } from './open-url';

export function fixedOpenSelections(cube: OpenCube): OpenSelection[] {
  return [
    {},
    { minLists: 2 },
    { minLists: 6 },
    { listedBy: ['wordnet'] },
    { listedBy: ['hunspell_en_US', 'hunspell_en_CA'] },
    { scowl: 10 },
    { scowl: 50, flags: { plain: 'with' } },
    { scowl: 70 },
    { tokens: ['1'] },
    { tokens: ['2', '4+'] },
    { gbType: 'with' },
    { gbType: 'without' },
    // no multiword row is measured: none is left
    { gbType: 'without', tokens: ['2'] },
    { flags: { plain: 'without' } },
    { flags: { hyphenated: 'with' }, listedBy: ['wiktionary_english'] },
    { flags: { 'apostrophe-form': 'without', 's-final': 'without' }, minLists: 3 },
    { flags: { accented: 'with' }, gbType: 'with' },
    { flags: { diaeresis: 'with', ligature: 'without' } },
    { noInstances: true },
    { noProperNouns: true, tokens: ['2', '3'] },
    { noInstances: true, noProperNouns: true, listedBy: ['wordnet'] },
    { minLength: 3, maxLength: 7 },
    { maxLength: 4, flags: { contraction: 'with' } },
    { minLength: 25 },
    { listedBy: ['hunspell_en_AU'], scowl: 35, gbType: 'with', flags: { plain: 'with' }, minLength: 4, maxLength: 9 },
    // shared addresses: a length past the cap, an unknown token count, a size
    // SCOWL does not name, and a least number every row meets
    ...['?len=30-', '?tok=1~9', '?scowl=45', '?lists=1'].map((q) => normalizeOpenSelection(readOpenSelection(q), cube)),
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

export function randomOpenSelections(cube: OpenCube, n: number, seed = 20261127): OpenSelection[] {
  const r = rng(seed);
  const pick = <T,>(xs: readonly T[]) => xs[Math.floor(r() * xs.length)];
  const out: OpenSelection[] = [];
  for (let i = 0; i < n; i++) {
    const flags: Record<string, FlagRule> = {};
    for (const f of ['plain', ...OPEN_FLAGS]) if (r() < 0.12) flags[f] = pick(['with', 'without'] as const);
    out.push({
      listedBy: NAMED_LISTS.filter(() => r() < 0.15),
      scowl: r() < 0.25 ? pick(SCOWL_SIZES) : null,
      minLists: r() < 0.3 ? 1 + Math.floor(r() * 6) : 0,
      tokens: r() < 0.3 ? cube.values.token_count.filter(() => r() < 0.5) : [],
      gbType: r() < 0.3 ? pick(['with', 'without'] as const) : 'any',
      flags,
      noInstances: r() < 0.2,
      noProperNouns: r() < 0.2,
      minLength: r() < 0.3 ? 1 + Math.floor(r() * 8) : null,
      maxLength: r() < 0.3 ? 6 + Math.floor(r() * 22) : null,
    });
  }
  return out;
}
