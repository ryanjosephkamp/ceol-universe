/**
 * The CEOL grammar in TypeScript: the port of pipeline/ceol/grammar.py, which
 * is the specification. `normalize` and `classes` return what the Python
 * returns for every input; src/lib/grammar.test.ts holds them to it by
 * running the Python on the same inputs. `trace` adds the steps, so a page
 * can show why a string passes or fails.
 */

export const BASE = 'abcdefghijklmnopqrstuvwxyz';
/** The declared accent inventory: a closed set. */
export const ACCENTED = 'áàâäéèêëíîïñóôöúûüç';
export const LIGATURES = 'æœ';
export const DIAERESIS = 'äëïöü';
export const NON_DIAERESIS_ACCENTS = [...ACCENTED].filter((c) => !DIAERESIS.includes(c)).join('');

export const HYPHEN = '-';
export const APOSTROPHE = "'";
export const SPACE = ' ';

const LETTERS = new Set([...BASE, ...ACCENTED, ...LIGATURES]);
const CHARSET = new Set([...LETTERS, HYPHEN, APOSTROPHE, SPACE]);

/** The 2 declared canonicalizations; every other look-alike is rejected. */
export const CANONICALIZE: Readonly<Record<string, string>> = {
  '\u2019': APOSTROPHE,
  '\u00a0': SPACE,
};

const isLetter = (c: string) => LETTERS.has(c);

/** Why a token or string fails the structural rules, or null. */
function tokenFault(t: string): string | null {
  const chars = [...t];
  if (!chars.some(isLetter)) return 'a token has no letter';
  if (chars[0] === HYPHEN) return 'a hyphen begins a token';
  if (chars[chars.length - 1] === HYPHEN) return 'a hyphen ends a token';
  for (const segment of t.split(HYPHEN)) {
    if (!segment) return 'two hyphens touch';
    if (![...segment].some(isLetter)) return 'a part between hyphens has no letter';
  }
  if (chars[chars.length - 1] === APOSTROPHE) return 'an apostrophe ends a token';
  if (t.includes(APOSTROPHE + APOSTROPHE)) return 'two apostrophes touch';
  return null;
}

function structuralFault(s: string): string | null {
  if (!s) return 'the string is empty';
  const undeclared = [...s].find((c) => !CHARSET.has(c));
  if (undeclared !== undefined) return `${codePoint(undeclared)} is not in the declared characters`;
  const tokens = s.split(SPACE);
  if (tokens[0] === '') return 'a space begins the string';
  if (tokens[tokens.length - 1] === '') return 'a space ends the string';
  if (tokens.some((t) => !t)) return 'two spaces touch';
  for (const t of tokens) {
    const fault = tokenFault(t);
    if (fault) return fault;
  }
  return null;
}

/** NFC, the 2 canonicalizations, lower(), NFC again; the key, or null when
 *  the string fails the grammar. */
export function normalize(raw: string): string | null {
  let s = raw.normalize('NFC');
  s = s.replaceAll('\u2019', APOSTROPHE).replaceAll('\u00a0', SPACE);
  s = s.toLowerCase().normalize('NFC');
  return structuralFault(s) === null ? s : null;
}

/** The enclitic endings the census counts as contractions: an apostrophe and
 *  then ll, ve, re, d, or m. They are built from their letters so that this
 *  file holds none of them as a string; the Python's copy of them is exempt
 *  from the scan by hash (pipeline/safeguards/exemptions.csv). */
export const CONTRACTION_ENCLITICS = ["ll", "ve", "re", "d", "m"].map((e) => APOSTROPHE + e);

export function isContraction(word: string): boolean {
  if (word.endsWith("n't")) return true;
  if (CONTRACTION_ENCLITICS.some((e) => word.endsWith(e))) return true;
  return word.startsWith(APOSTROPHE);
}

/** The census classes of a string that passes the grammar; empty for a
 *  plain [a-z]+ string. In the order the dataset's `classes` column uses. */
export function classes(word: string): string[] {
  const out = new Set<string>();
  const chars = [...word];
  if (word.includes(HYPHEN)) out.add('hyphenated');
  if (chars.some((c) => NON_DIAERESIS_ACCENTS.includes(c))) out.add('accented');
  if (chars.some((c) => DIAERESIS.includes(c))) out.add('diaeresis');
  if (chars.some((c) => LIGATURES.includes(c))) out.add('ligature');
  if (word.includes(SPACE)) out.add('spaced');
  if (word.includes(APOSTROPHE)) {
    out.add('apostrophe-form');
    const tokens = word.split(SPACE);
    if (tokens.some(isContraction)) out.add('contraction');
    if (tokens.some((t) => t.endsWith("'s"))) out.add('s-final');
  }
  return [...out].sort();
}

export const codePoint = (c: string) =>
  `U+${(c.codePointAt(0) ?? 0).toString(16).toUpperCase().padStart(4, '0')}`;

export type CharKind =
  | 'letter'
  | 'accented'
  | 'ligature'
  | 'hyphen'
  | 'apostrophe'
  | 'space'
  | 'canonicalized'
  | 'combining'
  | 'undeclared';

/** What the grammar makes of 1 character as typed: an upper-case letter
 *  counts as the letter it lowers to, and a combining mark joins the letter
 *  before it when the string is composed. */
export function charKind(c: string): CharKind {
  if (c === HYPHEN) return 'hyphen';
  if (c === APOSTROPHE) return 'apostrophe';
  if (c === SPACE) return 'space';
  if (c in CANONICALIZE) return 'canonicalized';
  if (/^\p{M}$/u.test(c)) return 'combining';
  const lowered = c.toLowerCase().normalize('NFC');
  if ([...lowered].length === 1) {
    if (BASE.includes(lowered)) return 'letter';
    if (ACCENTED.includes(lowered)) return 'accented';
    if (LIGATURES.includes(lowered)) return 'ligature';
  }
  return 'undeclared';
}

export interface Step {
  readonly name: string;
  readonly detail: string;
  readonly before: string;
  readonly after: string;
}

export interface Trace {
  readonly input: string;
  readonly steps: readonly Step[];
  /** the normalized string, before the structural rules */
  readonly normalized: string;
  /** the key, or null when the string fails */
  readonly key: string | null;
  readonly fault: string | null;
  readonly classes: readonly string[];
  readonly tokens: number;
}

/** Every step of the normalization, and the structural verdict. */
export function trace(input: string): Trace {
  const steps: Step[] = [];
  let s = input;
  const push = (name: string, detail: string, next: string) => {
    steps.push({ name, detail, before: s, after: next });
    s = next;
  };
  push('Compose', 'Unicode NFC: a letter and its combining accent become 1 character', s.normalize('NFC'));
  push(
    'Canonicalize',
    'U+2019 becomes U+0027 and U+00A0 becomes U+0020; nothing else is folded',
    s.replaceAll('\u2019', APOSTROPHE).replaceAll('\u00a0', SPACE),
  );
  push('Lower', 'lower case, never a case fold, so \u00df stays \u00df and fails', s.toLowerCase());
  push('Compose again', 'NFC again, because lowering can split a letter', s.normalize('NFC'));
  const fault = structuralFault(s);
  const key = fault === null ? s : null;
  return {
    input,
    steps,
    normalized: s,
    key,
    fault,
    classes: key === null ? [] : classes(key),
    tokens: key === null ? 0 : key.split(SPACE).length,
  };
}
