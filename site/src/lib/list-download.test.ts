/**
 * The list download returns the code's rows. On version 1.0's own universe
 * file, the strings the download keeps for a selection are held to the strings
 * DuckDB returns for the generated code, line for line: the same count and the
 * same SHA-256 of the lines, in the same order. No string is printed; a
 * failure names the selection and the 2 counts. The parity test needs the
 * release files (data/) and uv; without either it is skipped and says so.
 */

import { createHash } from 'node:crypto';
import { execFileSync, spawnSync } from 'node:child_process';
import { closeSync, existsSync, mkdtempSync, openSync, readFileSync, readSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { unzipSync } from 'fflate';
import { parquetMetadataAsync, parquetRead } from 'hyparquet';
import { compressors } from 'hyparquet-compressors';
import { afterAll, describe, expect, it } from 'vitest';
import { codeFor } from './codegen';
import { Cube, type CubeFile, type Selection } from './cube';
import { charLength, rowTest, type Row } from './list-filter';
import { plannedBytes, rangesFor, readList, MERGE_GAP, type FetchRange, type Layout } from './list-read';
import { listZip } from './list-zip';
import { fixedSelections, randomSelections } from './test-selections';

const REPO = resolve(__dirname, '../../..');
const cube = new Cube(
  JSON.parse(readFileSync(resolve(REPO, 'pipeline/research/release/figures/v1.0/cube.json'), 'utf-8')) as CubeFile,
);
const layout = JSON.parse(readFileSync(resolve(REPO, 'pipeline/research/release/layout_v1.0.json'), 'utf-8')) as Layout;
const LOCAL = resolve(REPO, 'data/release/ceol-universe-v1.0/universe.parquet');
const hasUv = spawnSync('uv', ['--version']).status === 0;
const runnable = existsSync(LOCAL) && hasUv;
const cap = cube.lengthCap;

describe('the row test', () => {
  const t = (sel: Selection, row: Row) => rowTest(sel, cap).test({ word: 'x', ...row });

  it('leaves out a row whose column is missing, as SQL does', () => {
    expect(t({ minLists: 2 }, { panel_count: null })).toBe(false);
    expect(t({ flags: { plain: 'without' } }, { class_explicit: null })).toBe(false);
    expect(t({ flags: { hyphenated: 'without' } }, { class_explicit: null })).toBe(false);
    expect(t({ values: { eol: ['false'] } }, { eol: null })).toBe(false);
    expect(t({ values: { intake_kind: ['derived'] } }, { intake_kind: null })).toBe(false);
    expect(t({ listedBy: ['wordnet'] }, { panel_sets: null })).toBe(false);
  });

  it('keeps a missing measure only where "Not measured" is chosen', () => {
    expect(t({ values: { gb_type: ['null'] } }, { gb_type: null })).toBe(true);
    expect(t({ values: { gb_type: ['true', 'false'] } }, { gb_type: null })).toBe(false);
    expect(t({ values: { gb_type: ['false'] } }, { gb_type: false })).toBe(true);
  });

  it('reads the joined columns by their parts', () => {
    expect(t({ listedBy: ['enable1'] }, { panel_sets: 'wordnet;enable1' })).toBe(true);
    expect(t({ listedBy: ['enable'] }, { panel_sets: 'enable1' })).toBe(false);
    expect(t({ flags: { 's-final': 'with' } }, { class_explicit: 'hyphenated;s-final' })).toBe(true);
    expect(t({ flags: { hyphenated: 'without' } }, { class_explicit: 'plain' })).toBe(true);
    expect(t({ flags: { plain: 'with' } }, { class_explicit: 'plain' })).toBe(true);
  });

  it('takes an open token count as "or more", and lengths in characters', () => {
    expect(t({ values: { token_count: ['4+'] } }, { token_count: 7 })).toBe(true);
    expect(t({ values: { token_count: ['1', '2'] } }, { token_count: 3 })).toBe(false);
    expect(charLength('naïve')).toBe(5);
    expect(charLength('a\u{1F600}b')).toBe(3);
    expect(t({ minLength: 3, maxLength: 3 }, { word: 'a\u{1F600}b' })).toBe(true);
    // the cube's top length holds every longer row, so it bounds nothing
    expect(t({ maxLength: cap }, { word: 'x'.repeat(cap + 20) })).toBe(true);
  });

  it('reads only the columns the layout holds', () => {
    for (const sel of [...fixedSelections(cube), ...randomSelections(cube, 24)]) {
      for (const c of rowTest(sel, cap).columns) expect(layout.row_groups[0].columns[c], c).toBeDefined();
    }
  });
});

describe('the byte ranges', () => {
  it('merge chunks closer than the gap and keep the strings whole', () => {
    const word = layout.row_groups[0].columns.word;
    const only = rangesFor(layout, 0, ['word']);
    expect(only).toEqual([[word[0], word[0] + word[1]]]);
    const all = rangesFor(layout, 0, Object.keys(layout.row_groups[0].columns));
    for (let i = 1; i < all.length; i++) expect(all[i][0] - all[i - 1][1]).toBeGreaterThan(MERGE_GAP);
  });

  it('read the strings and the chosen columns, far less than the file', () => {
    const words = plannedBytes(layout, {}, cap);
    const some = plannedBytes(layout, fixedSelections(cube)[2], cap);
    expect(words).toBeLessThan(some);
    // every criterion at once: the strings and 12 columns, 56 MB of 159
    const every: Selection = {
      minLists: 1,
      listedBy: ['wordnet'],
      flags: { hyphenated: 'without' },
      minLength: 2,
      values: {
        provenance_class: ['containment_only'], token_count: ['1'], gb_type: ['true'], wordfreq_scored: ['true'],
        wikt_title_any: ['true'], intake_layer: ['eol_valid'], intake_kind: ['obtained'], model_or_engine: ['none'], eol: ['true'],
      },
    };
    expect(rowTest(every, cap).columns).toHaveLength(13);
    expect(plannedBytes(layout, every, cap)).toBeLessThan(57e6);
  });
});

describe('the zip', () => {
  it('holds the list, 1 string per line, and the files beside it', () => {
    const z = listZip('list.txt', [
      { name: 'DATASHEET.md', text: '# A list\n' },
      { name: 'NOTICES.md', text: 'notices\n' },
    ]);
    z.push(['alpha', 'beta']);
    z.push([]);
    z.push(['gamma']);
    const files = unzipSync(concat(z.finish()));
    expect(Object.keys(files)).toEqual(['DATASHEET.md', 'NOTICES.md', 'list.txt']);
    expect(new TextDecoder().decode(files['list.txt'])).toBe('alpha\nbeta\ngamma\n');
  });
});

function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}

const PY = String.raw`
import duckdb, hashlib, json, sys
out = []
con = duckdb.connect()
for sql in json.load(open(sys.argv[1])):
    h, n = hashlib.sha256(), 0
    res = con.execute(sql)
    while True:
        rows = res.fetchmany(200000)
        if not rows:
            break
        for (w,) in rows:
            h.update((w + "\n").encode("utf-8"))
        n += len(rows)
    out.append({"rows": n, "sha256": h.hexdigest()})
json.dump(out, open(sys.argv[2], "w"))
`;

interface Lines {
  rows: number;
  sha256: string;
}

/** What DuckDB returns for each selection's generated code. */
function duckdbLines(selections: readonly Selection[]): Lines[] {
  const dir = mkdtempSync(join(tmpdir(), 'ceol-download-'));
  const sqls = selections.map((sel) => codeFor(sel, cube.rows(sel), cap, LOCAL).duckdb);
  writeFileSync(join(dir, 'cases.json'), JSON.stringify(sqls));
  writeFileSync(join(dir, 'run.py'), PY);
  execFileSync(
    'uv',
    ['run', '--no-project', '--isolated', '--quiet', '--with', 'duckdb==1.5.6',
      'python', join(dir, 'run.py'), join(dir, 'cases.json'), join(dir, 'out.json')],
    { stdio: ['ignore', 'ignore', 'inherit'], timeout: 900_000 },
  );
  return JSON.parse(readFileSync(join(dir, 'out.json'), 'utf-8')) as Lines[];
}

describe.skipIf(!runnable)('the download on version 1.0', () => {
  const fd = runnable ? openSync(LOCAL, 'r') : -1;
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

  it("keeps DuckDB's rows for every selection, line for line", async () => {
    const selections = [...fixedSelections(cube), ...randomSelections(cube, 12, 20261026)];
    const want = duckdbLines(selections);
    // 1 pass over the file: each row group is decoded once, with the columns
    // every selection reads, and each selection's test is applied to it
    const tests = selections.map((sel) => rowTest(sel, cap));
    const columns = [...new Set(tests.flatMap((t) => t.columns))];
    const hashes = selections.map(() => createHash('sha256'));
    const counts = selections.map(() => 0);
    const file = { byteLength: layout.bytes, slice: (s: number, e?: number) => fromFile(s, e ?? layout.bytes) };
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
      const got = hashes[i].digest('hex');
      if (counts[i] !== want[i].rows || got !== want[i].sha256 || counts[i] !== cube.rows(sel)) {
        wrong.push(`selection ${i} (${JSON.stringify(sel)}): download ${counts[i]} rows, DuckDB ${want[i].rows}, cube ${cube.rows(sel)}, lines ${got === want[i].sha256 ? 'equal' : 'differ'}`);
      }
    });
    expect(wrong).toEqual([]);
  }, 900_000);

  it('reads by range a row group at a time and zips what DuckDB returns', async () => {
    const fixed = fixedSelections(cube);
    const selections = [fixed[2], fixed[9], fixed[16]];
    const want = duckdbLines(selections);
    for (const [i, sel] of selections.entries()) {
      requests = 0;
      const z = listZip('list.txt', [{ name: 'NOTICES.md', text: 'notices\n' }]);
      let last = 0;
      for await (const step of readList(fromFile, layout, sel, cap)) {
        z.push(step.words);
        last = step.bytes;
      }
      const list = unzipSync(concat(z.finish()))['list.txt'];
      const lines = new TextDecoder().decode(list);
      const rows = lines ? lines.split('\n').length - 1 : 0;
      expect({ rows, sha256: createHash('sha256').update(list).digest('hex') }).toEqual(want[i]);
      // the footer, then a few ranges per row group, as planned
      expect(last).toBe(plannedBytes(layout, sel, cap));
      expect(requests).toBeLessThanOrEqual(1 + 4 * layout.row_groups.length);
    }
  }, 900_000);

  it('refuses a file the layout does not describe', async () => {
    const other = { ...layout, row_groups: layout.row_groups.slice(1), rows: layout.rows - layout.row_groups[0].rows };
    const steps = readList(fromFile, other, {}, cap);
    await expect(steps.next()).rejects.toThrow('not the one the layout describes');
  });
});

describe.skipIf(runnable)('the download on version 1.0, without the release files or uv', () => {
  it('is skipped: run it where data/ and uv exist', () => {
    expect(runnable).toBe(false);
  });
});
