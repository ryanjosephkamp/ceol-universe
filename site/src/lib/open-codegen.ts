/**
 * The code that reproduces a selection of the open subset from its public
 * file, in 3 forms: DuckDB SQL and Polars, which read the `open-lists`
 * Parquet file from the Hugging Face hub at the commit the site reads, and
 * pandas through the datasets library at the same commit.
 * src/lib/open-download.test.ts runs all 3 on the subset's own file for a
 * battery of selections and holds each count to the cube's.
 */

import layoutFile from '../../../pipeline/research/release/layout_open_v1.0.json';
import { OPEN_FLAGS, type OpenFlag, type OpenSelection } from './open-cube';

export const OPEN_DATASET = layoutFile.dataset;
export const OPEN_COMMIT = layoutFile.commit;
export const OPEN_CONFIG = 'open-lists';
export const OPEN_PATH = layoutFile.hub_path;
export const OPEN_PARQUET = `hf://datasets/${OPEN_DATASET}@${OPEN_COMMIT}/${OPEN_PATH}`;

interface Term {
  readonly sql: string;
  readonly polars: string;
  readonly pandas: string;
  /** the column the term reads */
  readonly column: string;
}

const q = (s: string) => `'${s}'`;
const dq = (s: string) => `"${s}"`;

function termsOf(sel: OpenSelection, lengthCap: number): Term[] {
  const out: Term[] = [];
  if (sel.minLists && sel.minLists > 1) {
    const n = sel.minLists;
    out.push({ column: 'list_count', sql: `list_count >= ${n}`, polars: `pl.col("list_count") >= ${n}`, pandas: `(df.list_count >= ${n})` });
  }
  for (const s of sel.listedBy ?? []) {
    out.push({
      column: 'listed_by',
      sql: `list_contains(string_split(listed_by, ';'), ${q(s)})`,
      polars: `pl.col("listed_by").str.split(";").list.contains(${dq(s)})`,
      pandas: `df.listed_by.str.contains(r"(?:^|;)${s}(?:;|$)")`,
    });
  }
  if (sel.scowl != null) {
    const n = sel.scowl;
    out.push({
      column: 'scowl_size',
      sql: `scowl_size BETWEEN 10 AND ${n}`,
      polars: `pl.col("scowl_size").is_between(10, ${n})`,
      pandas: `df.scowl_size.between(10, ${n})`,
    });
  }
  if (sel.tokens?.length) {
    const exact = sel.tokens.filter((v) => !v.endsWith('+')).map(Number);
    const open = sel.tokens.find((v) => v.endsWith('+'));
    const parts: Term[] = [];
    if (exact.length === 1) {
      parts.push({ column: 'token_count', sql: `token_count = ${exact[0]}`, polars: `pl.col("token_count") == ${exact[0]}`, pandas: `(df.token_count == ${exact[0]})` });
    } else if (exact.length > 1) {
      parts.push({
        column: 'token_count',
        sql: `token_count IN (${exact.join(', ')})`,
        polars: `pl.col("token_count").is_in([${exact.join(', ')}])`,
        pandas: `df.token_count.isin([${exact.join(', ')}])`,
      });
    }
    if (open) {
      const n = Number.parseInt(open, 10);
      parts.push({ column: 'token_count', sql: `token_count >= ${n}`, polars: `pl.col("token_count") >= ${n}`, pandas: `(df.token_count >= ${n})` });
    }
    if (parts.length) out.push(join(parts));
  }
  if (sel.gbType === 'with' || sel.gbType === 'without') {
    const v = sel.gbType === 'with';
    out.push({
      column: 'gb_type',
      sql: `gb_type IS ${v ? 'TRUE' : 'FALSE'}`,
      polars: `pl.col("gb_type").eq(${v ? 'True' : 'False'})`,
      pandas: `df.gb_type.eq(${v ? 'True' : 'False'})`,
    });
  }
  const flags = sel.flags ?? {};
  if (flags.plain === 'with') {
    out.push({ column: 'classes', sql: `classes = ''`, polars: `pl.col("classes") == ""`, pandas: `(df.classes == "")` });
  } else if (flags.plain === 'without') {
    out.push({ column: 'classes', sql: `classes <> ''`, polars: `pl.col("classes") != ""`, pandas: `(df.classes != "")` });
  }
  for (const f of OPEN_FLAGS) {
    const rule = flags[f as OpenFlag];
    if (!rule || rule === 'any') continue;
    const not = rule === 'without';
    out.push({
      column: 'classes',
      sql: `${not ? 'NOT ' : ''}list_contains(string_split(classes, ';'), ${q(f)})`,
      polars: `${not ? '~' : ''}pl.col("classes").str.split(";").list.contains(${dq(f)})`,
      pandas: `${not ? '~' : ''}df.classes.str.contains(r"(?:^|;)${f}(?:;|$)")`,
    });
  }
  // a null is not true: these keep every row the column leaves null
  if (sel.noInstances) {
    out.push({ column: 'wn_instance', sql: 'wn_instance IS NOT TRUE', polars: '~pl.col("wn_instance").fill_null(False)', pandas: 'df.wn_instance.ne(True)' });
  }
  if (sel.noProperNouns) {
    out.push({ column: 'wk_proper_noun', sql: 'wk_proper_noun IS NOT TRUE', polars: '~pl.col("wk_proper_noun").fill_null(False)', pandas: 'df.wk_proper_noun.ne(True)' });
  }
  const lo = sel.minLength != null && sel.minLength > 1 ? sel.minLength : null;
  const hi = sel.maxLength != null && sel.maxLength < lengthCap ? sel.maxLength : null;
  if (lo !== null && hi !== null) {
    out.push({
      column: 'word',
      sql: `length(word) BETWEEN ${lo} AND ${hi}`,
      polars: `pl.col("word").str.len_chars().is_between(${lo}, ${hi})`,
      pandas: `df.word.str.len().between(${lo}, ${hi})`,
    });
  } else if (lo !== null) {
    out.push({ column: 'word', sql: `length(word) >= ${lo}`, polars: `pl.col("word").str.len_chars() >= ${lo}`, pandas: `(df.word.str.len() >= ${lo})` });
  } else if (hi !== null) {
    out.push({ column: 'word', sql: `length(word) <= ${hi}`, polars: `pl.col("word").str.len_chars() <= ${hi}`, pandas: `(df.word.str.len() <= ${hi})` });
  }
  return out;
}

/** Terms joined by OR, as 1 term. Each Polars part keeps its own
 *  parentheses: Python binds | before ==, so a bare comparison would chain. */
function join(parts: Term[]): Term {
  if (parts.length === 1) return parts[0];
  return {
    column: parts[0].column,
    sql: `(${parts.map((p) => p.sql).join(' OR ')})`,
    polars: `(${parts.map((p) => `(${p.polars})`).join(' | ')})`,
    pandas: `(${parts.map((p) => p.pandas).join(' | ')})`,
  };
}

export interface Code {
  readonly duckdb: string;
  readonly polars: string;
  readonly pandas: string;
}

/** The 3 forms of the code for `sel`, each stating the rows it returns. */
export function openCodeFor(sel: OpenSelection, rows: number, lengthCap: number, source = OPEN_PARQUET): Code {
  const terms = termsOf(sel, lengthCap);
  const n = rows.toLocaleString('en-US');
  const where = terms.length ? `\nWHERE ${terms.map((t) => t.sql).join('\n  AND ')}` : '';
  const duckdb = `-- The CEOL Universe, open subset, version 1.0: ${n} rows
SELECT word
FROM
  '${source}'${where}
ORDER BY word;`;

  const filter = terms.length ? `\n    .filter(\n${terms.map((t) => `        ${t.polars},`).join('\n')}\n    )` : '';
  const polars = `import polars as pl

rows = (
    pl.scan_parquet(
        "${source}"
    )${filter}
    .select("word")
    .sort("word")
    .collect()
)
print(rows.height)  # ${n}`;

  const cols = ['word', ...new Set(terms.map((t) => t.column).filter((c) => c !== 'word'))];
  // the rows that pass, in the file's order, as the strings alone, as DuckDB
  // and Polars return them
  const mask = terms.length ? `df[\n    ${terms.map((t) => t.pandas).join('\n    & ')}\n][["word"]]` : 'df[["word"]]';
  const pandas = `from datasets import load_dataset

ds = load_dataset(
    "${OPEN_DATASET}",
    "${OPEN_CONFIG}",
    revision="${OPEN_COMMIT}",
    split="candidates",
)
df = ds.select_columns([${cols.map(dq).join(', ')}]).to_pandas()
rows = ${mask}
print(len(rows))  # ${n}`;
  return { duckdb, polars, pandas };
}
