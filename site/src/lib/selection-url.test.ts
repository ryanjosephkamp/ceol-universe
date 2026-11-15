/**
 * A shared address gives the same rows in the composer's count and in its
 * generated code: the selection read from the address is normalized against
 * the cube first (the 3 addresses below once counted differently).
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { codeFor } from './codegen';
import { Cube, type CubeFile } from './cube';
import { normalizeSelection, readSelection } from './selection-url';

const REPO = resolve(__dirname, '../../..');
const cube = new Cube(
  JSON.parse(readFileSync(resolve(REPO, 'pipeline/research/release/figures/v1.0/cube.json'), 'utf-8')) as CubeFile,
);
const read = (q: string) => normalizeSelection(readSelection(q), cube);

describe('a shared address', () => {
  it('chooses lengths by the length range, never by the length dimension', () => {
    const sel = read('?d.length=1');
    expect(sel.values?.length).toBeUndefined();
    expect(cube.rows(sel)).toBe(cube.total);
  });

  it('holds a length past the cap in the last bucket, as the code selects it', () => {
    const sel = read('?len=26-');
    expect(sel.minLength).toBe(cube.lengthCap);
    expect(cube.rows(sel)).toBeGreaterThan(0);
    expect(codeFor(sel, cube.rows(sel), cube.lengthCap).duckdb).toContain(`length(word) >= ${cube.lengthCap}`);
  });

  it('drops a value the cube does not hold', () => {
    const sel = read('?d.eol=invalid');
    expect(sel.values?.eol).toBeUndefined();
    expect(cube.rows(sel)).toBe(cube.total);
    expect(read('?d.eol=true').values?.eol).toEqual(['true']);
  });

  it('keeps a well-formed selection as it was', () => {
    const sel = read('?d.token_count=1&lists=2&len=3-7');
    expect(sel.values?.token_count).toEqual(['1']);
    expect([sel.minLists, sel.minLength, sel.maxLength]).toEqual([2, 3, 7]);
  });
});
