/**
 * The open list download returns the code's rows, and the code returns the
 * page's count. On the open subset's own `open-lists` file (the copy the
 * subset's build wrote, held to the sha256 of the file at the hub commit),
 * for a battery of selections:
 *
 * - the strings the download's row test keeps are the strings DuckDB returns
 *   for the generated SQL, line for line (the same count and the same SHA-256
 *   of the lines, in the same order), and both counts are the cube's;
 * - the generated Polars and pandas code return DuckDB's strings too, the
 *   same count and the same SHA-256 of the lines in the same order, and
 *   only the strings;
 * - the layout's byte ranges are the file's own column chunks, and a read by
 *   range a row group at a time zips the same lines beside the datasheet and
 *   the subset's NOTICES.
 *
 * No string is printed; a failure names the selection and the counts. The
 * tests need the subset's file (made by open_subset.py beside data/) and uv;
 * without either they are skipped and say so.
 */

import { createHash } from 'node:crypto';
import { execFileSync, spawnSync } from 'node:child_process';
import { closeSync, existsSync, mkdtempSync, openSync, readFileSync, readSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { unzipSync } from 'fflate';
import { parquetMetadataAsync, parquetRead } from 'hyparquet';
import { compressors } from 'hyparquet-compressors';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Row } from './list-filter';
import { bytesFor, rangesFor, readRows, MERGE_GAP, type FetchRange, type Layout } from './list-read';
import { listZip } from './list-zip';
import { openCodeFor } from './open-codegen';
import { OpenCube, type OpenCubeFile, type OpenSelection } from './open-cube';
import { openSheetMarkdown } from './open-datasheet';
import { openRowTest } from './open-filter';
import { fixedOpenSelections, randomOpenSelections } from './test-open-selections';

const REPO = resolve(__dirname, '../../..');
const RELEASE = resolve(REPO, 'pipeline/research/release');
const cube = new OpenCube(JSON.parse(readFileSync(resolve(RELEASE, 'open_cube_v1.0.json'), 'utf-8')) as OpenCubeFile);
const layout = JSON.parse(readFileSync(resolve(RELEASE, 'layout_open_v1.0.json'), 'utf-8')) as Layout;
const NOTICES = readFileSync(resolve(RELEASE, 'NOTICES_open_v1.0.md'), 'utf-8');
const cap = cube.lengthCap;

/** The subset's file as its build writes it: beside the data folder, never
 *  in it (open_subset.default_out). */
function localFile(): string | null {
  const data = process.env.CEOL_DATA ?? resolve(REPO, 'data');
  if (!existsSync(data)) return null;
  const path = join(dirname(realpathSync(data)), 'data-open', 'ceol-universe-open-v1.0', layout.hub_path);
  return existsSync(path) ? path : null;
}

const LOCAL = localFile();
const hasUv = spawnSync('uv', ['--version']).status === 0;
const runnable = LOCAL !== null && hasUv;

function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}

describe('the open row test', () => {
  const t = (sel: OpenSelection, row: Row) => openRowTest(sel, cap).test({ word: 'x', ...row });

  it('leaves out a row whose column is missing, as SQL does', () => {
    expect(t({ minLists: 2 }, { list_count: null })).toBe(false);
    expect(t({ listedBy: ['wordnet'] }, { listed_by: null })).toBe(false);
    expect(t({ scowl: 70 }, { scowl_size: null })).toBe(false);
    expect(t({ gbType: 'with' }, { gb_type: null })).toBe(false);
    expect(t({ gbType: 'without' }, { gb_type: null })).toBe(false);
    expect(t({ flags: { plain: 'without' } }, { classes: null })).toBe(false);
  });

  it('keeps a missing properness signal, as IS NOT TRUE does', () => {
    expect(t({ noInstances: true }, { wn_instance: null })).toBe(true);
    expect(t({ noInstances: true }, { wn_instance: false })).toBe(true);
    expect(t({ noInstances: true }, { wn_instance: true })).toBe(false);
    expect(t({ noProperNouns: true }, { wk_proper_noun: undefined })).toBe(true);
    expect(t({ noProperNouns: true }, { wk_proper_noun: true })).toBe(false);
  });

  it('reads SCOWL by size and the joined columns by their parts', () => {
    expect(t({ scowl: 35 }, { scowl_size: 35 })).toBe(true);
    expect(t({ scowl: 35 }, { scowl_size: 40 })).toBe(false);
    expect(t({ scowl: 35 }, { scowl_size: 0 })).toBe(false);
    expect(t({ scowl: 35 }, { scowl_size: -1 })).toBe(false);
    expect(t({ listedBy: ['hunspell_en_CA'] }, { listed_by: 'wordnet;hunspell_en_CA' })).toBe(true);
    expect(t({ listedBy: ['wordnet'] }, { listed_by: 'wiktionary_english' })).toBe(false);
    expect(t({ flags: { plain: 'with' } }, { classes: '' })).toBe(true);
    expect(t({ flags: { plain: 'with' } }, { classes: 'spaced' })).toBe(false);
    expect(t({ flags: { hyphenated: 'without' } }, { classes: '' })).toBe(true);
    expect(t({ flags: { 's-final': 'with' } }, { classes: 'apostrophe-form;s-final' })).toBe(true);
  });
});

describe('the open layout', () => {
  it('merges chunks closer than the gap and reads far less than the file', () => {
    const word = layout.row_groups[0].columns.word;
    expect(rangesFor(layout, 0, ['word'])).toEqual([[word[0], word[0] + word[1]]]);
    const all = rangesFor(layout, 0, Object.keys(layout.row_groups[0].columns));
    for (let i = 1; i < all.length; i++) expect(all[i][0] - all[i - 1][1]).toBeGreaterThan(MERGE_GAP);
    const strings = bytesFor(layout, ['word']);
    const typical = bytesFor(layout, openRowTest({ tokens: ['1'], flags: { plain: 'with' }, listedBy: ['hunspell_en_US'] }, cap).columns);
    const every = bytesFor(layout, Object.keys(layout.row_groups[0].columns));
    expect(strings).toBeLessThan(typical);
    expect(typical).toBeLessThan(every);
    // every column the page reads is under half the file: the ids are most of it
    expect(every).toBeLessThan(layout.bytes / 2);
  });
});

describe('the zip', () => {
  it('holds the list, its datasheet, and the notices', () => {
    const z = listZip('list.txt', [
      { name: 'DATASHEET.md', text: '# A list\n' },
      { name: 'NOTICES.md', text: NOTICES },
    ]);
    z.push(['alpha', 'beta']);
    z.push([]);
    const files = unzipSync(concat(z.finish()));
    expect(Object.keys(files)).toEqual(['DATASHEET.md', 'NOTICES.md', 'list.txt']);
    expect(new TextDecoder().decode(files['list.txt'])).toBe('alpha\nbeta\n');
    expect(new TextDecoder().decode(files['NOTICES.md'])).toBe(NOTICES);
  });
});

const PY = String.raw`
import contextlib, hashlib, io, json, re, sys
import duckdb, polars as pl, pandas as pd, pyarrow as pa, pyarrow.parquet as pq

cases = json.load(open(sys.argv[1]))
local = sys.argv[2]
out = []
con = duckdb.connect()


def lines(words):
    # the count and the SHA-256 of the strings, 1 per line, in their order
    h, n = hashlib.sha256(), 0
    for w in words:
        h.update((w + "\n").encode("utf-8"))
        n += 1
    return {"rows": n, "sha256": h.hexdigest()}


for c in cases:
    got = {}
    got["duckdb"] = lines(w for (w,) in con.execute(c["duckdb"]).fetchall())
    ns = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(c["polars"], ns)
    got["polars"] = lines(ns["rows"]["word"].to_list()) | {"columns": ns["rows"].columns}
    if c.get("pandas"):
        cols = json.loads(re.search(r"select_columns\((\[.*?\])\)", c["pandas"]).group(1))
        code = c["pandas"].splitlines()
        # the code after the load: the hub read is replaced by the local
        # file, in pandas' default types, as the datasets library gives them
        start = next(k for k, l in enumerate(code) if l.startswith("df = ds.")) + 1
        ns = {"df": pq.read_table(local, columns=cols).to_pandas()}
        with contextlib.redirect_stdout(io.StringIO()):
            exec("\n".join(code[start:]), ns)
        got["pandas"] = lines(ns["rows"]["word"].to_list()) | {"columns": list(ns["rows"].columns)}
    out.append(got)
json.dump(out, open(sys.argv[3], "w"))
`;

interface Lines {
  rows: number;
  sha256: string;
  columns?: string[];
}

interface Got {
  duckdb: Lines;
  polars: Lines;
  pandas?: Lines | null;
}

/** What the generated code returns for each selection, run on the local file. */
function runCode(selections: readonly OpenSelection[], pandasFor: (i: number) => boolean): Got[] {
  const dir = mkdtempSync(join(tmpdir(), 'ceol-open-'));
  try {
    const cases = selections.map((sel, i) => {
      const code = openCodeFor(sel, cube.rows(sel), cap, LOCAL!);
      return { duckdb: code.duckdb, polars: code.polars, pandas: pandasFor(i) ? code.pandas : null };
    });
    writeFileSync(join(dir, 'cases.json'), JSON.stringify(cases));
    writeFileSync(join(dir, 'run.py'), PY);
    execFileSync(
      'uv',
      [
        'run', '--no-project', '--isolated', '--quiet',
        '--with', 'duckdb==1.5.6', '--with', 'polars==2.0.0', '--with', 'pandas==3.0.6', '--with', 'pyarrow==26.0.0',
        '--with', 'numpy==2.4.6',
        'python', join(dir, 'run.py'), join(dir, 'cases.json'), LOCAL!, join(dir, 'out.json'),
      ],
      { stdio: ['ignore', 'ignore', 'inherit'], timeout: 900_000 },
    );
    return JSON.parse(readFileSync(join(dir, 'out.json'), 'utf-8')) as Got[];
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

describe.skipIf(!runnable)("the open download on the subset's own file", () => {
  const fd = runnable ? openSync(LOCAL!, 'r') : -1;
  afterAll(() => {
    if (fd >= 0) closeSync(fd);
  });
  let requests = 0;
  const fromFile: FetchRange = async (start, end) => {
    requests++;
    const buf = Buffer.alloc(end - start);
    readSync(fd, buf, 0, end - start, start);
    return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length) as ArrayBuffer;
  };
  const file = { byteLength: layout.bytes, slice: (s: number, e?: number) => fromFile(s, e ?? layout.bytes) };
  const fixed = fixedOpenSelections(cube);
  const selections = [...fixed, ...randomOpenSelections(cube, 24)];
  let got: Got[] = [];
  beforeAll(() => {
    got = runCode(selections, () => true);
  }, 900_000);

  it('is the file at the hub commit', () => {
    expect(createHash('sha256').update(readFileSync(LOCAL!)).digest('hex')).toBe(layout.sha256);
  });

  it("keeps DuckDB's rows for every selection, line for line, and the cube counts them", async () => {
    // 1 pass over the file: each row group is decoded once, with the columns
    // every selection reads, and each selection's test is applied to it
    const tests = selections.map((sel) => openRowTest(sel, cap));
    const columns = [...new Set(tests.flatMap((t) => t.columns))];
    const hashes = selections.map(() => createHash('sha256'));
    const counts = selections.map(() => 0);
    const metadata = await parquetMetadataAsync(file);
    let start = 0;
    for (const g of metadata.row_groups) {
      const n = Number(g.num_rows);
      const rows = await new Promise<Row[]>((done, fail) => {
        parquetRead({ file, metadata, columns, rowStart: start, rowEnd: start + n, compressors, rowFormat: 'object', onComplete: done }).catch(fail);
      });
      tests.forEach((t, i) => {
        const kept = rows.filter(t.test).map((r) => r.word as string);
        if (kept.length) hashes[i].update(kept.join('\n') + '\n', 'utf8');
        counts[i] += kept.length;
      });
      start += n;
    }
    const wrong: string[] = [];
    selections.forEach((sel, i) => {
      const sha = hashes[i].digest('hex');
      const want = got[i].duckdb;
      if (counts[i] !== want.rows || sha !== want.sha256 || want.rows !== cube.rows(sel)) {
        wrong.push(`selection ${i} (${JSON.stringify(sel)}): download ${counts[i]} rows, DuckDB ${want.rows}, cube ${cube.rows(sel)}, lines ${sha === want.sha256 ? 'equal' : 'differ'}`);
      }
    });
    expect(wrong).toEqual([]);
    // the battery reaches both ends: an empty list and the whole subset
    expect(selections.some((s) => cube.rows(s) === 0)).toBe(true);
    expect(selections.some((s) => cube.rows(s) === cube.total)).toBe(true);
  }, 900_000);

  it("returns DuckDB's strings, in its order, in Polars and pandas, and only the strings", () => {
    const wrong: string[] = [];
    selections.forEach((sel, i) => {
      const want = got[i].duckdb;
      for (const [lib, lines] of [['Polars', got[i].polars], ['pandas', got[i].pandas]] as const) {
        if (!lines || lines.rows !== want.rows || lines.sha256 !== want.sha256) {
          wrong.push(`selection ${i} (${JSON.stringify(sel)}): ${lib} ${lines?.rows} rows, DuckDB ${want.rows}, lines ${lines?.sha256 === want.sha256 ? 'equal' : 'differ'}`);
        }
        if (lines?.columns?.join() !== 'word') wrong.push(`selection ${i}: ${lib} returns the columns ${lines?.columns?.join(', ')}`);
      }
    });
    expect(wrong).toEqual([]);
    expect(got.filter((g) => g.pandas).length).toBe(selections.length);
  });

  it("holds the layout's spans to the file's own column chunks", async () => {
    const metadata = await parquetMetadataAsync(file);
    expect(Number(metadata.num_rows)).toBe(layout.rows);
    const kv = new Map((metadata.key_value_metadata ?? []).map((e) => [e.key, e.value]));
    for (const [k, v] of Object.entries(layout.metadata ?? {})) expect([k, kv.get(k)]).toEqual([k, v]);
    metadata.row_groups.forEach((g, i) => {
      expect(Number(g.num_rows)).toBe(layout.row_groups[i].rows);
      for (const chunk of g.columns) {
        const m = chunk.meta_data!;
        const name = m.path_in_schema.join('.');
        const span = layout.row_groups[i].columns[name];
        if (!span) continue;
        const first = Number(m.dictionary_page_offset ?? m.data_page_offset);
        expect([name, span[0], span[1]]).toEqual([name, Math.min(first, Number(m.data_page_offset)), Number(m.total_compressed_size)]);
      }
    });
  });

  it('reads by range a row group at a time and zips what DuckDB returns, with the datasheet and the notices', async () => {
    const picks = [8, 6, 19];
    for (const at of picks) {
      const sel = fixed[at];
      requests = 0;
      const sheet = openSheetMarkdown(sel, cube, {
        made: new Date(2026, 10, 27),
        link: 'https://example.test/compose/open/',
        citation: 'The card says how to cite it.',
        file: { path: layout.hub_path, bytes: layout.bytes, sha256: layout.sha256, license: layout.metadata!['ceol.license'], attribution: layout.metadata!['ceol.attribution'] },
      });
      const z = listZip('list.txt', [
        { name: 'DATASHEET.md', text: sheet },
        { name: 'NOTICES.md', text: NOTICES },
      ]);
      const rowTest = openRowTest(sel, cap);
      let last = 0;
      for await (const step of readRows(fromFile, layout, rowTest)) {
        z.push(step.words);
        last = step.bytes;
      }
      const files = unzipSync(concat(z.finish()));
      expect(Object.keys(files)).toEqual(['DATASHEET.md', 'NOTICES.md', 'list.txt']);
      const list = files['list.txt'];
      const text = new TextDecoder().decode(list);
      const rows = text ? text.split('\n').length - 1 : 0;
      expect({ rows, sha256: createHash('sha256').update(list).digest('hex') }).toEqual(got[at].duckdb);
      expect(rows).toBe(cube.rows(sel));
      expect(new TextDecoder().decode(files['NOTICES.md'])).toBe(NOTICES);
      expect(new TextDecoder().decode(files['DATASHEET.md'])).toContain(`${rows.toLocaleString('en-US')} rows`);
      // the footer, then a few ranges per row group, as planned
      expect(last).toBe(bytesFor(layout, rowTest.columns));
      expect(requests).toBeLessThanOrEqual(1 + 4 * layout.row_groups.length);
    }
  }, 900_000);

  it('refuses a file the layout does not describe', async () => {
    const fewer = { ...layout, row_groups: layout.row_groups.slice(1), rows: layout.rows - layout.row_groups[0].rows };
    await expect(readRows(fromFile, fewer, openRowTest({}, cap)).next()).rejects.toThrow('not the one the layout describes');
    const other = { ...layout, metadata: { ...layout.metadata, 'ceol.attribution': 'another file' } };
    await expect(readRows(fromFile, other, openRowTest({}, cap)).next()).rejects.toThrow('ceol.attribution');
  });
});

describe.skipIf(runnable)("the open download, without the subset's file or uv", () => {
  it("is skipped: run it where the subset's file (open_subset.py) and uv exist", () => {
    expect(runnable).toBe(false);
  });
});
