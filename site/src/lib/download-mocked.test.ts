/**
 * The list download end to end on a small made-up file
 * (site/test-files/open-test/, tools/build_open_test_file.py), through mocked
 * HTTP answers and the worker's own code, with no data folder and no Python:
 * the range requests, the footer's checks, the decoding in windows across
 * pages (the strings column has 2 data pages in the first row group) and row
 * groups, the row test, the count's check, and the zip. The
 * download on the real files is held to DuckDB by open-download.test.ts and
 * list-download.test.ts.
 */

import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { unzipSync } from 'fflate';
import { parquetMetadata, parquetReadObjects } from 'hyparquet';
// hyparquet's own Thrift reader, for the page headers: the package does not
// export its page-header parser
import { deserializeTCompactProtocol } from '../../node_modules/hyparquet/src/thrift.js';
import { compressors } from 'hyparquet-compressors';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { runDownload, type DownloadMessage, type DownloadRequest, type ListFilter } from './list-download';
import type { Row } from './list-filter';
import type { Layout } from './list-read';
import type { OpenSelection } from './open-cube';
import { openRowTest } from './open-filter';

const DIR = resolve(__dirname, '../../test-files/open-test');
const FILE = new Uint8Array(readFileSync(join(DIR, 'open-lists.parquet')));
const layout = JSON.parse(readFileSync(join(DIR, 'layout.json'), 'utf-8')) as Layout;
const URL_ = layout.url!;
const NOTICES = { name: 'NOTICES.md', text: 'The notices.\n' };
const SHEET = { name: 'DATASHEET.md', text: '# A list\n' };

/** A hub that answers range requests for the file, as the real one does,
 *  and records each range asked for. `tamper` changes an answer. */
function hub(tamper?: (a: number, b: number) => { start: number; body: Uint8Array } | null) {
  const asked: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url !== URL_) return new Response(null, { status: 404 });
      const range = new Headers(init?.headers).get('range') ?? '';
      asked.push(range);
      const m = /^bytes=(\d+)-(\d+)$/.exec(range);
      if (!m) return new Response(FILE, { status: 200 });
      const [a, b] = [Number(m[1]), Number(m[2])];
      const t = tamper?.(a, b) ?? { start: a, body: FILE.slice(a, b + 1) };
      const last = t.start + t.body.length - 1;
      return new Response(t.body, {
        status: 206,
        headers: { 'content-range': `bytes ${t.start}-${last}/${FILE.length}`, 'content-length': String(t.body.length) },
      });
    }),
  );
  return asked;
}

afterEach(() => vi.unstubAllGlobals());

let allRows: Row[] = [];
beforeAll(async () => {
  const buf = FILE.buffer.slice(FILE.byteOffset, FILE.byteOffset + FILE.byteLength) as ArrayBuffer;
  allRows = (await parquetReadObjects({ file: buf, metadata: parquetMetadata(buf), compressors })) as Row[];
});

/** The rows of each data page of a column chunk, read from its page
 *  headers: hyparquet hands a column's pages back joined, so its callbacks
 *  cannot show where 1 page ends. */
function dataPageRows(group: number, column: string): number[] {
  const [start, size] = layout.row_groups[group].columns[column];
  const reader = { view: new DataView(FILE.buffer, FILE.byteOffset + start, size), offset: 0 };
  const rows: number[] = [];
  while (reader.offset < size) {
    const h = deserializeTCompactProtocol(reader) as {
      field_1: number;
      field_3: number;
      field_5?: { field_1: number };
      field_8?: { field_3: number };
    };
    // page type 0 is a data page (its values are its rows in a flat
    // column), 3 a version 2 data page; 2, a dictionary page, holds no rows
    if (h.field_1 === 0) rows.push(h.field_5!.field_1);
    if (h.field_1 === 3) rows.push(h.field_8!.field_3);
    reader.offset += h.field_3;
  }
  return rows;
}

const WINDOW = 7;

/** The strings a selection keeps, read whole and tested row by row. */
const expected = (sel: OpenSelection) => allRows.filter(openRowTest(sel, 25).test).map((r) => r.word as string);

const request = (filter: ListFilter, rows: number, l: Layout = layout): DownloadRequest => ({
  url: URL_,
  layout: l,
  filter,
  expected: rows,
  listName: 'list.txt',
  files: [SHEET, NOTICES],
});

async function run(req: DownloadRequest, windowRows?: number) {
  const messages: DownloadMessage[] = [];
  await runDownload(req, (m) => messages.push(m), { windowRows });
  return messages;
}

async function unzip(m: DownloadMessage | undefined) {
  if (m?.kind !== 'done') throw new Error(`no zip: ${JSON.stringify(m)}`);
  return unzipSync(new Uint8Array(await m.blob.arrayBuffer()));
}

const SELECTIONS: OpenSelection[] = [
  {},
  { tokens: ['1'], flags: { plain: 'with' } },
  { listedBy: ['wordnet'], noInstances: true },
  { scowl: 35, gbType: 'with' },
  { gbType: 'without' },
  { minLists: 2, noProperNouns: true, minLength: 5, maxLength: 6 },
  { flags: { hyphenated: 'with' } },
  { flags: { 'apostrophe-form': 'without', plain: 'without' } },
  { tokens: ['2'], noProperNouns: true },
];

describe('the list download, on a made-up file over mocked HTTP', () => {
  it('is a file of 2 row groups whose strings column has 2 data pages in the first, and a window crosses the page boundary', () => {
    expect(layout.row_groups.map((g) => g.rows)).toEqual([60, 30]);
    expect(allRows).toHaveLength(90);
    const pages = layout.row_groups.map((_, g) => dataPageRows(g, 'word'));
    expect(pages.map((p) => p.reduce((a, b) => a + b, 0))).toEqual([60, 30]);
    expect(pages[0].length).toBeGreaterThan(1);
    // the rows where a page of the first row group ends, inside the group
    const ends = pages[0].slice(0, -1).map((_, i) => pages[0].slice(0, i + 1).reduce((a, b) => a + b, 0));
    // a window of WINDOW rows that starts before 1 of them and ends after it
    expect(ends.some((e) => e % WINDOW !== 0)).toBe(true);
  });

  it('zips the strings each selection keeps, line for line, in windows across pages and row groups', async () => {
    for (const sel of SELECTIONS) {
      const want = expected(sel);
      for (const windowRows of [WINDOW, 1 << 17]) {
        const asked = hub();
        const messages = await run(request({ of: 'open', sel, lengthCap: 25 }, want.length), windowRows);
        const files = await unzip(messages.at(-1));
        expect(Object.keys(files)).toEqual(['DATASHEET.md', 'NOTICES.md', 'list.txt']);
        const text = new TextDecoder().decode(files['list.txt']);
        expect([JSON.stringify(sel), windowRows, text]).toEqual([JSON.stringify(sel), windowRows, want.map((w) => `${w}\n`).join('')]);
        expect(new TextDecoder().decode(files['NOTICES.md'])).toBe(NOTICES.text);
        // the footer, then 1 merged range per row group
        expect(asked).toHaveLength(3);
        const progress = messages.filter((m) => m.kind === 'progress');
        expect(progress.at(-1)).toMatchObject({ read: 90, total: 90, rows: want.length });
        if (windowRows === WINDOW) expect(progress.length).toBe(Math.ceil(60 / WINDOW) + Math.ceil(30 / WINDOW));
      }
    }
  });

  it('runs the universe filter through the same path', async () => {
    hub();
    const messages = await run(request({ of: 'universe', sel: {}, lengthCap: 25 }, 90), 11);
    const text = new TextDecoder().decode((await unzip(messages.at(-1)))['list.txt']);
    expect(text.split('\n').length - 1).toBe(90);
  });

  it('refuses to save a list whose rows differ from the page count', async () => {
    hub();
    const sel: OpenSelection = { tokens: ['1'] };
    const messages = await run(request({ of: 'open', sel, lengthCap: 25 }, expected(sel).length + 1));
    expect(messages.at(-1)).toMatchObject({ kind: 'failed' });
    expect((messages.at(-1) as { reason: string }).reason).toContain('so it was not saved');
  });

  it('refuses a file whose column lies elsewhere than the layout says, before fetching any of its data', async () => {
    const asked = hub();
    const moved = structuredClone(layout) as { row_groups: { columns: Record<string, number[]> }[] };
    const [start, size] = moved.row_groups[0].columns.word;
    moved.row_groups[0].columns.word = [start + 1, size - 1];
    const messages = await run(request({ of: 'open', sel: {}, lengthCap: 25 }, 90, moved as unknown as Layout));
    expect(messages.at(-1)).toEqual({ kind: 'failed', reason: "the file's word column in row group 1 is not where the layout records it" });
    expect(asked).toHaveLength(1);
  });

  it('refuses a file whose metadata or row groups are not the layout’s', async () => {
    hub();
    const other = { ...layout, metadata: { ...layout.metadata, 'ceol.attribution': 'another file' } };
    expect((await run(request({ of: 'open', sel: {}, lengthCap: 25 }, 90, other))).at(-1)).toEqual({
      kind: 'failed',
      reason: "the file's ceol.attribution is not the one the layout records",
    });
    hub();
    const fewer = { ...layout, row_groups: layout.row_groups.slice(1), rows: 30 };
    expect((await run(request({ of: 'open', sel: {}, lengthCap: 25 }, 30, fewer))).at(-1)).toMatchObject({ kind: 'failed' });
  });

  it('refuses a range answered with other bytes of the same length', async () => {
    hub((a, b) => (a > 0 && a < layout.bytes - 1000 ? { start: a + 1, body: FILE.slice(a + 1, b + 2) } : null));
    const messages = await run(request({ of: 'open', sel: {}, lengthCap: 25 }, 90));
    expect(messages.at(-1)).toMatchObject({ kind: 'failed' });
    expect((messages.at(-1) as { reason: string }).reason).toMatch(
      new RegExp(`^the file's server answered "bytes \\d+-\\d+/${layout.bytes}" to a request for bytes`),
    );
  });
});

describe('the worker', () => {
  it('runs a request it is sent and posts the zip back', async () => {
    hub();
    const posted: DownloadMessage[] = [];
    const self = { postMessage: (m: DownloadMessage) => posted.push(m), onmessage: null as ((e: { data: DownloadRequest }) => void) | null };
    vi.stubGlobal('self', self);
    await import('./list-download.worker');
    const sel: OpenSelection = { tokens: ['1'], flags: { plain: 'with' } };
    self.onmessage!({ data: request({ of: 'open', sel, lengthCap: 25 }, expected(sel).length) });
    await vi.waitFor(() => expect(posted.at(-1)?.kind).toBe('done'));
    const text = new TextDecoder().decode((await unzip(posted.at(-1)))['list.txt']);
    expect(text).toBe(expected(sel).map((w) => `${w}\n`).join(''));
  });
});
