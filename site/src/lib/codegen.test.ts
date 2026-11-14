/**
 * Every snippet has been run: the code the site generates for a selection is
 * executed on version 1.0's own universe file, in DuckDB, Polars, and pandas, and
 * the rows each returns must be the cube's count for that selection. The
 * selections are a fixed set that touches every kind of criterion, and a
 * seeded random set beside it. The test needs the release files (data/) and
 * uv, which builds the 3 libraries' environment; without either it is
 * skipped and says so.
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { codeFor } from './codegen';
import { Cube, type CubeFile } from './cube';
import { fixedSelections, randomSelections } from './test-selections';

const REPO = resolve(__dirname, '../../..');
const cube = new Cube(
  JSON.parse(readFileSync(resolve(REPO, 'pipeline/research/release/figures/v1.0/cube.json'), 'utf-8')) as CubeFile,
);
const LOCAL = resolve(REPO, 'data/release/ceol-universe-v1.0/universe.parquet');
const hasUv = spawnSync('uv', ['--version']).status === 0;
const runnable = existsSync(LOCAL) && hasUv;

const FIXED = fixedSelections(cube);

const PY = String.raw`
import contextlib, io, json, re, sys
import duckdb, polars as pl, pandas as pd, pyarrow as pa, pyarrow.parquet as pq

cases = json.load(open(sys.argv[1]))
local = sys.argv[2]
out = []
for c in cases:
    got = {}
    sql = c["duckdb"].rsplit("ORDER BY", 1)[0]
    got["duckdb"] = duckdb.sql(f"SELECT count(*) FROM ({sql})").fetchone()[0]
    ns = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(c["polars"], ns)
    got["polars"] = ns["rows"].height
    if c.get("pandas"):
        cols = json.loads(re.search(r"select_columns\((\[.*?\])\)", c["pandas"]).group(1))
        lines = c["pandas"].splitlines()
        # the code after the load: the hub read is replaced by the local file
        start = next(k for k, l in enumerate(lines) if l.startswith("df = ds.")) + 1
        body = "\n".join(lines[start:])
        df = pq.read_table(local, columns=cols).to_pandas(
            types_mapper={pa.string(): pd.StringDtype("pyarrow"),
                          pa.large_string(): pd.StringDtype("pyarrow")}.get)
        ns = {"df": df}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(body, ns)
        got["pandas"] = len(ns["rows"])
        del df, ns
    out.append(got)
json.dump(out, open(sys.argv[3], "w"))
`;

describe.skipIf(!runnable)('the generated code', () => {
  it('returns the cube count in DuckDB, Polars, and pandas', () => {
    const selections = [...FIXED, ...randomSelections(cube, 24)];
    const cases = selections.map((sel, i) => {
      const code = codeFor(sel, cube.rows(sel), cube.lengthCap, LOCAL);
      // pandas loads whole columns, so it runs on the fixed set only
      return { duckdb: code.duckdb, polars: code.polars, pandas: i < FIXED.length ? code.pandas : null };
    });
    const dir = mkdtempSync(join(tmpdir(), 'ceol-codegen-'));
    writeFileSync(join(dir, 'cases.json'), JSON.stringify(cases));
    writeFileSync(join(dir, 'run.py'), PY);
    execFileSync(
      'uv',
      [
        'run', '--no-project', '--isolated', '--quiet',
        '--with', 'duckdb==1.5.6', '--with', 'polars==2.0.0', '--with', 'pandas==3.0.6', '--with', 'pyarrow==26.0.0',
        '--with', 'numpy==2.4.6',
        'python', join(dir, 'run.py'), join(dir, 'cases.json'), LOCAL, join(dir, 'out.json'),
      ],
      { stdio: ['ignore', 'ignore', 'inherit'], timeout: 900_000 },
    );
    const got = JSON.parse(readFileSync(join(dir, 'out.json'), 'utf-8')) as Record<string, number>[];
    const wrong: string[] = [];
    selections.forEach((sel, i) => {
      const want = cube.rows(sel);
      for (const [lib, n] of Object.entries(got[i])) {
        if (n !== want) wrong.push(`selection ${i} (${JSON.stringify(sel)}): ${lib} ${n}, cube ${want}`);
      }
    });
    expect(wrong).toEqual([]);
    expect(got.filter((g) => 'pandas' in g).length).toBe(FIXED.length);
  }, 900_000);
});

describe.skipIf(runnable)('the generated code, without the release files or uv', () => {
  it('is skipped: run it where data/ and uv exist', () => {
    expect(runnable).toBe(false);
  });
});
