/**
 * The lookup's text rules, carried over from the earlier build
 * (site/legacy/src/lookup/text.ts): the typed text is normalized by the
 * grammar's pipeline, then matched in 1 of 5 modes, on the EOL site's
 * semantics. A pattern's `_` is 1 character and `*` is any run.
 */

export type Mode = 'prefix' | 'contains' | 'suffix' | 'pattern' | 'regex';

export const MODES: readonly (readonly [Mode, string])[] = [
  ['prefix', 'Starts with'],
  ['contains', 'Contains'],
  ['suffix', 'Ends with'],
  ['pattern', 'Pattern'],
  ['regex', 'Regex'],
];

/** NFC; U+2019 to U+0027 and U+00A0 to U+0020; lower case, never a case
 *  fold; NFC again; leading whitespace removed. A regex keeps its case,
 *  since lowering it would change its escapes. */
export function normalizeQuery(raw: string, mode: Mode): string {
  let s = raw.normalize('NFC').replaceAll('\u2019', "'").replaceAll('\u00a0', ' ');
  if (mode !== 'regex') s = s.toLowerCase().normalize('NFC');
  return s.replace(/^\s+/, '');
}

/** Escapes a regex syntax character. The hyphen is not one outside a class,
 *  and a Unicode regex refuses an escape it does not need. */
function escapeRegex(ch: string): string {
  return ch.replace(/[\\^$.*+?()[\]{}|/]/g, '\\$&');
}

export type Matcher = { readonly test: (s: string) => boolean } | { readonly error: string };

/** The mode's test for a string. An empty text matches every string. */
export function matcher(mode: Mode, text: string): Matcher {
  if (!text) return { test: () => true };
  switch (mode) {
    case 'prefix':
      return { test: (s) => s.startsWith(text) };
    case 'contains':
      return { test: (s) => s.includes(text) };
    case 'suffix':
      return { test: (s) => s.endsWith(text) };
    case 'pattern': {
      const body = Array.from(text)
        .map((ch) => (ch === '_' ? '.' : ch === '*' ? '.*' : escapeRegex(ch)))
        .join('');
      const re = new RegExp(`^${body}$`, 'u');
      return { test: (s) => re.test(s) };
    }
    case 'regex':
      try {
        const re = new RegExp(text, 'u');
        return { test: (s) => re.test(s) };
      } catch (cause) {
        return { error: cause instanceof Error ? cause.message : 'not a valid regular expression' };
      }
  }
}

/** The length of a string in characters (code points), as the dataset counts. */
export const charLength = (s: string) => Array.from(s).length;
