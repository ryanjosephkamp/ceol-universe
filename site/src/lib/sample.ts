/** The shape of the sample file the Explore page fetches: columns, then
 *  rows as arrays, so 5,000 rows cross the wire compactly. Written at build
 *  time by src/pages/data/sample-v1.0.json.ts from site/fixtures/rows.jsonl. */

export const SAMPLE_COLUMNS = [
  'id',
  'word',
  'classes',
  'token_count',
  'panel_sets',
  'panel_count',
  'provenance_class',
  'intake_layer',
  'intake_kind',
  'intake_channels',
  'intake_date',
  'sources',
  'eol',
  'eol_record',
  'model_or_engine',
  'gb_type',
  'wordfreq_scored',
] as const;

export type SampleColumn = (typeof SAMPLE_COLUMNS)[number];

export interface SampleFile {
  readonly version: string;
  readonly drawn_from: number;
  readonly published_sets: readonly string[];
  readonly columns: readonly SampleColumn[];
  readonly rows: readonly (readonly (string | number | boolean | null)[])[];
}

export interface Row {
  readonly id: string;
  readonly word: string;
  readonly classes: string;
  readonly token_count: number;
  readonly panel_sets: string;
  readonly panel_count: number;
  readonly provenance_class: string;
  readonly intake_layer: string;
  readonly intake_kind: string;
  readonly intake_channels: string;
  readonly intake_date: string | null;
  readonly sources: string;
  readonly eol: boolean;
  readonly eol_record: string;
  readonly model_or_engine: string;
  readonly gb_type: boolean | null;
  readonly wordfreq_scored: boolean | null;
}

export function rowsOf(file: SampleFile): Row[] {
  return file.rows.map((r) => Object.fromEntries(file.columns.map((c, i) => [c, r[i]])) as unknown as Row);
}
