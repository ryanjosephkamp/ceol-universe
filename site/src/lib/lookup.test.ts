import { describe, expect, it } from 'vitest';
import { charLength, matcher, normalizeQuery } from './lookup';

const hits = (mode: Parameters<typeof matcher>[0], text: string, strings: string[]) => {
  const m = matcher(mode, normalizeQuery(text, mode));
  if ('error' in m) throw new Error(m.error);
  return strings.filter(m.test);
};

// made-up strings, so this file lists no candidate of the universe
const strings = ["q'zylk", 'zylk', 'zylkvo', 'mo-zylk', 'zyak', 'vrè zûl'];

describe('the lookup modes', () => {
  it('matches a prefix, a part, and an ending', () => {
    expect(hits('prefix', 'zylk', strings)).toEqual(['zylk', 'zylkvo']);
    expect(hits('contains', 'zylk', strings)).toEqual(["q'zylk", 'zylk', 'zylkvo', 'mo-zylk']);
    expect(hits('suffix', 'zylk', strings)).toEqual(["q'zylk", 'zylk', 'mo-zylk']);
  });

  it('reads _ as 1 character and * as any run in a pattern', () => {
    expect(hits('pattern', 'zy_k', strings)).toEqual(['zylk', 'zyak']);
    expect(hits('pattern', 'zy*', strings)).toEqual(['zylk', 'zylkvo', 'zyak']);
    expect(hits('pattern', '*-*', strings)).toEqual(['mo-zylk']);
  });

  it('normalizes the typed text as the grammar does', () => {
    expect(hits('prefix', 'Q\u2019ZY', strings)).toEqual(["q'zylk"]);
    expect(hits('prefix', 'VRE\u0300\u00a0Z', strings)).toEqual(['vrè zûl']);
    expect(hits('prefix', '   zylkv', strings)).toEqual(['zylkvo']);
  });

  it('keeps a regex as typed and reports a bad one', () => {
    expect(hits('regex', '^zy[la]k$', strings)).toEqual(['zylk', 'zyak']);
    expect('error' in matcher('regex', '(')).toBe(true);
  });

  it('matches everything when nothing is typed', () => {
    expect(hits('contains', '', strings)).toEqual(strings);
  });

  it('counts characters as code points', () => {
    expect(charLength('vrè zûl')).toBe(7);
  });
});
