/**
 * The TypeScript grammar against its specification, pipeline/ceol/grammar.py:
 * the same inputs go to both, and every key and every class set must agree.
 * The inputs are the vetted example list, the site's sample rows, those
 * strings altered in every way the grammar has a rule for, and characters
 * that look like declared ones.
 */

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { classes, normalize, trace } from './grammar';

const REPO = resolve(__dirname, '../../..');

const vetted = readFileSync(resolve(REPO, 'examples/vetted_examples.txt'), 'utf-8')
  .split('\n')
  .filter((l) => l && !l.startsWith('#'));
const sample = readFileSync(resolve(REPO, 'site/fixtures/rows.jsonl'), 'utf-8')
  .split('\n')
  .filter(Boolean)
  .map((l) => (JSON.parse(l) as { word: string }).word);

/** Every rule's violation, built from a real string. */
function altered(s: string): string[] {
  return [
    s.toUpperCase(),
    s[0].toUpperCase() + s.slice(1),
    s.normalize('NFD'),
    s.replaceAll("'", '\u2019'),
    s.replaceAll("'", '\u2018'),
    s.replaceAll("'", '\u02bc'),
    s.replaceAll(' ', '\u00a0'),
    s.replaceAll(' ', '  '),
    s.replaceAll(' ', '\t'),
    s.replaceAll('-', '\u2013'),
    s.replaceAll('-', '--'),
    `-${s}`,
    `${s}-`,
    ` ${s}`,
    `${s} `,
    `${s}'`,
    `'${s}`,
    `${s}''s`,
    `${s}\u00df`,
    `${s}\u00df`.toUpperCase(),
    `${s}\ufb03`,
    `${s}\u0130`,
    `${s}\u03c3`,
    `${s}_x`,
    `${s}1`,
  ];
}

const inputs = [
  ...new Set([
    ...vetted,
    ...sample,
    ...vetted.slice(0, 400).flatMap(altered),
    '',
    ' ',
    '-',
    "'",
    "''",
    'a',
    "'a",
    'a-b-c',
    'a--b',
    'a - b',
    "o'",
    "'tis",
    "n't",
    '\u00e6',
    'e\u0301',
    'E\u0301',
    '\u2019tis',
  ]),
];

function python(strings: string[]): [string | null, string[]][] {
  const script = [
    'import json, sys',
    "sys.path.insert(0, 'pipeline')",
    'from ceol import grammar',
    'out = []',
    'for s in json.load(sys.stdin):',
    '    k = grammar.normalize(s)',
    '    out.append([k, sorted(grammar.classes(k)) if k is not None else []])',
    'json.dump(out, sys.stdout)',
  ].join('\n');
  const stdout = execFileSync('python3', ['-c', script], {
    cwd: REPO,
    input: JSON.stringify(strings),
    maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(stdout.toString('utf-8'));
}

describe('the grammar port', () => {
  const expected = python(inputs);

  it(`agrees with grammar.py on ${inputs.length} inputs`, () => {
    const disagreements: string[] = [];
    inputs.forEach((s, i) => {
      const [key, cls] = expected[i];
      const mine = normalize(s);
      const mineClasses = mine === null ? [] : classes(mine);
      if (mine !== key || JSON.stringify(mineClasses) !== JSON.stringify(cls)) {
        disagreements.push(`input ${i}: python ${JSON.stringify([key, cls])}, typescript ${JSON.stringify([mine, mineClasses])}`);
      }
    });
    expect(disagreements.slice(0, 5)).toEqual([]);
  });

  it('passes every vetted example and every sample row unchanged', () => {
    for (const s of [...vetted, ...sample]) expect(normalize(s)).toBe(s);
  });

  it('traces to the same key it normalizes to', () => {
    for (const s of inputs.slice(0, 2000)) {
      const t = trace(s);
      expect(t.key).toBe(normalize(s));
      expect(t.fault === null).toBe(t.key !== null);
    }
  });
});
