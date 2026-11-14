/** What the dataset's codes mean, in the site's words. Each matches the data
 *  dictionary (docs/DATA_DICTIONARY.md). */

export const SET_NAMES: Readonly<Record<string, string>> = {
  wordnet: 'WordNet',
  wiktionary_english: 'Wiktionary (English)',
  hunspell_en_US: 'hunspell en_US',
  hunspell_en_GB: 'hunspell en_GB',
  hunspell_en_CA: 'hunspell en_CA',
  hunspell_en_AU: 'hunspell en_AU',
  enable1: 'ENABLE',
  scowl: 'SCOWL',
};

export const PROVENANCE: Readonly<Record<string, { label: string; what: string }>> = {
  channel_and_containment: {
    label: 'Channel and containment',
    what: 'came in by a recorded channel, and a published list or a corpus holds it',
  },
  containment_only: {
    label: 'Containment only',
    what: 'a published list or a corpus holds it; no published channel is recorded',
  },
  channel_only: {
    label: 'Channel only',
    what: 'came in by a recorded channel; no published list or corpus holds it',
  },
  neither: { label: 'Neither', what: 'no published channel and no containment' },
};

export const PROVENANCE_ORDER = ['channel_and_containment', 'containment_only', 'channel_only', 'neither'];

export const INTAKE_LAYER: Readonly<Record<string, string>> = {
  eol_valid: "the English OpenList's valid list",
  eol_invalid: "the English OpenList's invalid list",
  c1_exceptions: 'the census of spelling classes',
  c4_additions: "the audit's additions",
  spaced_c015: 'the pass over multiword terms',
};

export const INTAKE_KIND: Readonly<Record<string, string>> = {
  obtained: 'obtained: taken in through a channel',
  derived: 'derived from pinned sources',
  generated: "made by the English OpenList's synthetic engine",
};

export const MODEL_OR_ENGINE: Readonly<Record<string, string>> = {
  none: 'none',
  engine_generated: "made by the English OpenList's synthetic engine",
};

/** The model-or-engine values a published row carries, in 1 order. */
export const MOE_ORDER = ['none', 'engine_generated'] as const;

/** Short labels for a chart's bars; MODEL_OR_ENGINE says each in full. */
export const MOE_SHORT: Readonly<Record<string, string>> = {
  none: 'Not made by the engine',
  engine_generated: 'The synthetic engine',
};

export const EOL_RECORD: Readonly<Record<string, string>> = {
  'valid-dict': "an entry in the English OpenList's valid dictionary",
  'invalid-dict': "an entry in the English OpenList's invalid dictionary",
  none: "no entry in either of the English OpenList's dictionaries",
};

export const CLASS_FLAGS = [
  'hyphenated',
  'accented',
  'diaeresis',
  'ligature',
  'apostrophe-form',
  'contraction',
  's-final',
  'spaced',
] as const;

export const PLAIN = 'plain';

export const CLASS_NAMES: Readonly<Record<string, string>> = {
  hyphenated: 'Hyphenated',
  accented: 'Accented',
  diaeresis: 'Diaeresis',
  ligature: 'Ligature',
  'apostrophe-form': 'Apostrophe',
  contraction: 'Contraction',
  's-final': "Ends in 's",
  spaced: 'Multiword',
  plain: 'Plain a to z',
};
