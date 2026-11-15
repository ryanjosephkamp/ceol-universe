/**
 * The descriptive analysis of the version (pipeline/research/analysis/
 * descriptive.py), read at build time. An entry is a question of the
 * analysis plan, under its id; an id the file does not hold stops the
 * build, as an unknown figure does (src/lib/data.ts).
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { VERSION } from './data';

export const ANALYSIS_PATH = `pipeline/research/release/figures/${VERSION}/analysis.json`;

export interface AnalysisEntry<T = unknown> {
  readonly id: string;
  readonly question: string;
  readonly unit: string;
  readonly population: string;
  readonly exact: boolean;
  readonly note?: string;
  readonly data: T;
}

interface AnalysisFile {
  readonly version: string;
  readonly rows: { all: number; single_token: number; multiword: number; by_tier: Record<string, number> };
  readonly tiers: readonly string[];
  readonly list_set: { lists: readonly string[]; families: Record<string, readonly string[]> };
  readonly analyses: readonly AnalysisEntry[];
}

const file: AnalysisFile = JSON.parse(readFileSync(resolve(process.cwd(), '..', ANALYSIS_PATH), 'utf-8'));
if (file.version !== VERSION) throw new Error(`${ANALYSIS_PATH} is version ${file.version}, not ${VERSION}`);
const byId = new Map(file.analyses.map((e) => [e.id, e]));

export function analysis<T = unknown>(id: string): AnalysisEntry<T> {
  const e = byId.get(id);
  if (!e) throw new Error(`no analysis '${id}' in ${ANALYSIS_PATH}`);
  return e as AnalysisEntry<T>;
}

export const analysisRows = file.rows;
export const analysisTiers = file.tiers;
export const analysisLists = file.list_set;
