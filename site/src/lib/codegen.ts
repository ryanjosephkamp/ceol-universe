/**
 * The code that reproduces a selection from the dataset itself, in 3 forms:
 * DuckDB SQL and Polars, which read the universe config's Parquet file from
 * the Hugging Face hub at the version's tag, and pandas through the datasets
 * library. src/lib/codegen.test.ts runs all 3 on version 1.0's files for a battery
 * of selections and holds each count to the cube's.
 */

import { FLAGS, type Dim, type Flag, type Selection } from './cube';

export const DATASET = 'ryanjosephkamp/ceol-universe';
export const VERSION = 'v1.0';
export const PARQUET = `hf://datasets/${DATASET}@${VERSION}/data/universe.parquet`;

/** The columns a selection reads, besides `word`. */
function columnsOf(sel: Selection, lengthCap: number): string[] {
  const cols = new Set<string>();
  for (const [d, v] of Object.entries(sel.values ?? {})) if (v && v.length) cols.add(columnOf(d as Dim));
  if (sel.listedBy?.length) cols.add('panel_sets');
  if (sel.minLists) cols.add('panel_count');
  if (Object.values(sel.flags ?? {}).some((r) => r && r !== 'any')) cols.add('class_explicit');
  if (sel.minLength != null && sel.minLength > 1) cols.add('word');
  if (sel.maxLength != null && sel.maxLength < lengthCap) cols.add('word');
  cols.delete('word');
  return [...cols];
}

/** The column a cube dimension reads. The cube's `length` is the string's
 *  length in characters; every other dimension is a column of its name. */
const columnOf = (d: Dim) => (d === 'length' ? 'word' : d);

const BOOLEANS: readonly Dim[] = ['eol'];
const NULLABLE: readonly Dim[] = ['gb_type', 'wordfreq_scored', 'wikt_title_any'];
const NUMBERED: readonly Dim[] = ['token_count'];

interface Term {
  readonly sql: string;
  readonly polars: string;
  readonly pandas: string;
}

const q = (s: string) => `'${s}'`;
const dq = (s: string) => `"${s}"`;

function termsOf(sel: Selection, lengthCap: number): Term[] {
  const out: Term[] = [];
  if (sel.minLists) {
    const n = sel.minLists;
    out.push({ sql: `panel_count >= ${n}`, polars: `pl.col("panel_count") >= ${n}`, pandas: `(df.panel_count >= ${n})` });
  }
  for (const s of sel.listedBy ?? []) {
    out.push({
      sql: `list_contains(string_split(panel_sets, ';'), ${q(s)})`,
      polars: `pl.col("panel_sets").str.split(";").list.contains(${dq(s)})`,
      pandas: `df.panel_sets.str.contains(r"(?:^|;)${s}(?:;|$)")`,
    });
  }
  const flags = sel.flags ?? {};
  if (flags.plain === 'with') {
    out.push({ sql: `class_explicit = 'plain'`, polars: `pl.col("class_explicit") == "plain"`, pandas: `(df.class_explicit == "plain")` });
  } else if (flags.plain === 'without') {
    out.push({ sql: `class_explicit <> 'plain'`, polars: `pl.col("class_explicit") != "plain"`, pandas: `(df.class_explicit != "plain")` });
  }
  for (const f of FLAGS) {
    const rule = flags[f as Flag];
    if (!rule || rule === 'any') continue;
    const not = rule === 'without';
    out.push({
      sql: `${not ? 'NOT ' : ''}list_contains(string_split(class_explicit, ';'), ${q(f)})`,
      polars: `${not ? '~' : ''}pl.col("class_explicit").str.split(";").list.contains(${dq(f)})`,
      pandas: `${not ? '~' : ''}df.class_explicit.str.contains(r"(?:^|;)${f}(?:;|$)")`,
    });
  }
  const values = sel.values ?? {};
  for (const [dim, vals] of Object.entries(values) as [Dim, readonly string[]][]) {
    if (!vals || vals.length === 0) continue;
    if (dim === 'length') continue;
    if (BOOLEANS.includes(dim)) {
      if (vals.length === 2) continue;
      const yes = vals[0] === 'true';
      out.push({ sql: `${yes ? '' : 'NOT '}${dim}`, polars: `${yes ? '' : '~'}pl.col("${dim}")`, pandas: `${yes ? '' : '~'}df.${dim}` });
    } else if (NULLABLE.includes(dim)) {
      if (vals.length === 3) continue;
      const parts = vals.map((v) => ({
        sql: v === 'null' ? `${dim} IS NULL` : `${dim} IS ${v.toUpperCase()}`,
        polars: v === 'null' ? `pl.col("${dim}").is_null()` : `pl.col("${dim}").eq(${v === 'true' ? 'True' : 'False'})`,
        pandas: v === 'null' ? `df.${dim}.isna()` : `df.${dim}.eq(${v === 'true' ? 'True' : 'False'})`,
      }));
      out.push(join(parts));
    } else if (NUMBERED.includes(dim)) {
      const exact = vals.filter((v) => !v.endsWith('+')).map(Number);
      const open = vals.find((v) => v.endsWith('+'));
      const parts: Term[] = [];
      if (exact.length === 1) {
        parts.push({ sql: `${dim} = ${exact[0]}`, polars: `pl.col("${dim}") == ${exact[0]}`, pandas: `(df.${dim} == ${exact[0]})` });
      } else if (exact.length > 1) {
        parts.push({
          sql: `${dim} IN (${exact.join(', ')})`,
          polars: `pl.col("${dim}").is_in([${exact.join(', ')}])`,
          pandas: `df.${dim}.isin([${exact.join(', ')}])`,
        });
      }
      if (open) {
        const n = Number.parseInt(open, 10);
        parts.push({ sql: `${dim} >= ${n}`, polars: `pl.col("${dim}") >= ${n}`, pandas: `(df.${dim} >= ${n})` });
      }
      out.push(join(parts));
    } else {
      const list = vals.map(q).join(', ');
      out.push({
        sql: vals.length === 1 ? `${dim} = ${q(vals[0])}` : `${dim} IN (${list})`,
        polars: vals.length === 1 ? `pl.col("${dim}") == ${dq(vals[0])}` : `pl.col("${dim}").is_in([${vals.map(dq).join(', ')}])`,
        pandas: vals.length === 1 ? `(df.${dim} == ${dq(vals[0])})` : `df.${dim}.isin([${vals.map(dq).join(', ')}])`,
      });
    }
  }
  const lo = sel.minLength != null && sel.minLength > 1 ? sel.minLength : null;
  const hi = sel.maxLength != null && sel.maxLength < lengthCap ? sel.maxLength : null;
  if (lo !== null && hi !== null) {
    out.push({
      sql: `length(word) BETWEEN ${lo} AND ${hi}`,
      polars: `pl.col("word").str.len_chars().is_between(${lo}, ${hi})`,
      pandas: `df.word.str.len().between(${lo}, ${hi})`,
    });
  } else if (lo !== null) {
    out.push({ sql: `length(word) >= ${lo}`, polars: `pl.col("word").str.len_chars() >= ${lo}`, pandas: `(df.word.str.len() >= ${lo})` });
  } else if (hi !== null) {
    out.push({ sql: `length(word) <= ${hi}`, polars: `pl.col("word").str.len_chars() <= ${hi}`, pandas: `(df.word.str.len() <= ${hi})` });
  }
  return out;
}

/** Terms joined by OR, as 1 term. Each Polars part keeps its own
 *  parentheses: Python binds | before ==, so a bare comparison would chain. */
function join(parts: Term[]): Term {
  if (parts.length === 1) return parts[0];
  return {
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
export function codeFor(sel: Selection, rows: number, lengthCap: number, source = PARQUET): Code {
  const terms = termsOf(sel, lengthCap);
  const n = rows.toLocaleString('en-US');
  const where = terms.length ? `\nWHERE ${terms.map((t) => t.sql).join('\n  AND ')}` : '';
  const duckdb = `-- The CEOL Universe, version ${VERSION.slice(1)}: ${n} rows
SELECT word
FROM
  '${source}'${where}
ORDER BY word;`;

  const filter = terms.length
    ? `\n    .filter(\n${terms.map((t) => `        ${t.polars},`).join('\n')}\n    )`
    : '';
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

  const cols = ['word', ...columnsOf(sel, lengthCap)];
  const mask = terms.length ? `df[\n    ${terms.map((t) => t.pandas).join('\n    & ')}\n]` : 'df';
  const pandas = `from datasets import load_dataset

ds = load_dataset(
    "${DATASET}",
    "universe",
    revision="${VERSION}",
    split="candidates",
)
df = ds.select_columns([${cols.map(dq).join(', ')}]).to_pandas()
rows = ${mask}
print(len(rows))  # ${n}`;
  return { duckdb, polars, pandas };
}
