/**
 * Reading a composed list from a Parquet file, by byte range, for the list
 * download: the universe file, with the layout record
 * pipeline/research/release/layout_v1.0.json, or the open subset's
 * `open-lists` file, with layout_open_v1.0.json. The layout says where the
 * strings and each criterion's column lie in every row group; the reader
 * requests only those, a row group at a time, so a phone never holds the
 * whole file, and it keeps the rows the list's test passes. Both files are
 * sorted by `word`, so the strings come out in the order the code's
 * `ORDER BY word` gives.
 */

import { parquetMetadataAsync, parquetRead, type AsyncBuffer, type FileMetaData } from 'hyparquet';
import { compressors } from 'hyparquet-compressors';
import type { Selection } from './cube';
import { rowTest, type RowTest } from './list-filter';

export interface Layout {
  readonly version: string;
  readonly dataset: string;
  readonly hub_path: string;
  /** the hub commit the file is read at, and its address there, where the
   *  layout records them (the open subset's) */
  readonly commit?: string;
  readonly url?: string;
  readonly bytes: number;
  readonly sha256: string;
  readonly rows: number;
  readonly row_groups: readonly {
    readonly rows: number;
    readonly columns: Readonly<Record<string, readonly [number, number] | readonly number[]>>;
  }[];
  /** key-value metadata the file's footer must carry, where the layout
   *  records it (the open subset's license and attribution) */
  readonly metadata?: Readonly<Record<string, string>>;
}

/** Column chunks closer than this are requested together: a wider gap
 *  saves requests but reads the unrequested columns between them (with every
 *  criterion, 68 MB at 256 KB against 56 MB at 64 KB). A row group's ranges
 *  are requested at once, so their number costs little time. */
export const MERGE_GAP = 64 * 1024;
/** The end of the file read for its footer (hyparquet's first read). */
export const FOOTER_READ = 1 << 19;

export type Range = readonly [start: number, end: number];

/** The byte ranges a read of `columns` requests in row group `g`, merged. */
export function rangesFor(layout: Layout, g: number, columns: readonly string[]): Range[] {
  const spans = columns
    .map((c) => {
      const span = layout.row_groups[g].columns[c];
      if (!span) throw new Error(`the layout has no column ${c}`);
      return [span[0], span[0] + span[1]] as const;
    })
    .sort((a, b) => a[0] - b[0]);
  const out: [number, number][] = [];
  for (const [s, e] of spans) {
    const last = out[out.length - 1];
    if (last && s - last[1] <= MERGE_GAP) last[1] = Math.max(last[1], e);
    else out.push([s, e]);
  }
  return out;
}

/** The bytes a read of `columns` requests: their ranges in every row
 *  group, and the footer. */
export function bytesFor(layout: Layout, columns: readonly string[]): number {
  let n = Math.min(FOOTER_READ, layout.bytes);
  for (let g = 0; g < layout.row_groups.length; g++) {
    for (const [s, e] of rangesFor(layout, g, columns)) n += e - s;
  }
  return n;
}

/** The bytes a download of `sel` from the universe file reads. */
export function plannedBytes(layout: Layout, sel: Selection, lengthCap: number): number {
  return bytesFor(layout, rowTest(sel, lengthCap).columns);
}

export type FetchRange = (start: number, end: number, signal?: AbortSignal) => Promise<ArrayBuffer>;

/** A fetch of 1 byte range of `url`, a file of `size` bytes. Only a partial
 *  answer (206) is taken: a server that ignores the range would send the
 *  whole file. Where the answer's Content-Range is visible (the hub's is),
 *  it must name the bytes asked for and the file's size; where its
 *  Content-Length is, it must be the range's length. The body is read only
 *  up to the range's length: a longer one is refused at its first extra
 *  byte. */
export function rangeFetcher(url: string, size?: number): FetchRange {
  return async (start, end, signal) => {
    const want = end - start;
    const asked = `bytes ${start}-${end - 1}${size === undefined ? '' : ` of ${size}`}`;
    const res = await fetch(url, { headers: { Range: `bytes=${start}-${end - 1}` }, signal });
    const refuse = async (why: string): Promise<never> => {
      await res.body?.cancel().catch(() => {});
      throw new Error(`the file's server ${why}`);
    };
    if (res.status !== 206) return refuse(`answered ${res.status} to a range request`);
    const range = res.headers.get('content-range');
    if (range !== null) {
      // the unit is case-insensitive; the total is compared as a number, and
      // an unknown total ('*') is refused where the size is known
      const m = /^bytes (\d+)-(\d+)\/(\d+|\*)$/i.exec(range.trim());
      const ok = m && Number(m[1]) === start && Number(m[2]) === end - 1 && (size === undefined || (m[3] !== '*' && Number(m[3]) === size));
      if (!ok) return refuse(`answered "${range}" to a request for ${asked}`);
    }
    const length = res.headers.get('content-length');
    if (length !== null && Number(length) !== want) return refuse(`announced ${length} bytes for ${asked}`);
    return readBody(res, want);
  };
}

/** The body of `res`, which must be `want` bytes. */
async function readBody(res: Response, want: number): Promise<ArrayBuffer> {
  if (!res.body) {
    const buf = await res.arrayBuffer();
    if (buf.byteLength !== want) throw new Error(`a range request returned ${buf.byteLength} bytes, not ${want}`);
    return buf;
  }
  const out = new Uint8Array(want);
  let at = 0;
  const reader = res.body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    if (at + value.length > want) {
      await reader.cancel().catch(() => {});
      throw new Error(`a range request returned more than ${want} bytes`);
    }
    out.set(value, at);
    at += value.length;
  }
  if (at !== want) throw new Error(`a range request returned ${at} bytes, not ${want}`);
  return out.buffer;
}

/** Rows in a window: the batch of rows tested and handed on at a time. A
 *  row group can hold over a million rows; its rows are tested a window at a
 *  time, through 1 reused object, never an object per row, and each window's
 *  kept strings are handed on before the next. A column's pages are decoded
 *  whole and kept while they still hold the next window's rows, so a small
 *  column that is 1 page for its whole row group stays decoded for the group
 *  (at a byte a row, where it has few distinct values). */
export const WINDOW_ROWS = 1 << 17;

/** The file as hyparquet reads it, with each row group's ranges fetched in
 *  advance and every read inside them served from memory. A read of a
 *  sub-range is copied once and kept, so the windows of a row group reuse
 *  it rather than copying it again. */
class RangedFile implements AsyncBuffer {
  readonly byteLength: number;
  private cache: { range: Range; data: Promise<ArrayBuffer> }[] = [];
  /** exact sub-ranges already copied out of a held range, by "start-end" */
  private copies = new Map<string, { parent: Range; data: Promise<ArrayBuffer> }>();
  read = 0;
  /** once the footer is read and checked, every read must lie in a held
   *  range: a read the layout did not plan is refused, never fetched */
  strict = false;

  constructor(
    private readonly fetchRange: FetchRange,
    byteLength: number,
    private readonly signal?: AbortSignal,
  ) {
    this.byteLength = byteLength;
  }

  private get(start: number, end: number): Promise<ArrayBuffer> {
    this.read += end - start;
    return this.fetchRange(start, end, this.signal);
  }

  hold(ranges: readonly Range[]): Promise<unknown> {
    const added = ranges.map((range) => ({ range, data: this.get(range[0], range[1]) }));
    this.cache.push(...added);
    return Promise.all(added.map((a) => a.data));
  }

  release(ranges: readonly Range[]): void {
    this.cache = this.cache.filter((c) => !ranges.includes(c.range));
    for (const [key, copy] of this.copies) if (ranges.includes(copy.parent)) this.copies.delete(key);
  }

  slice(start: number, end?: number): Promise<ArrayBuffer> {
    const stop = end ?? this.byteLength;
    const key = `${start}-${stop}`;
    const copied = this.copies.get(key);
    if (copied) return copied.data;
    const hit = this.cache.find((c) => c.range[0] <= start && stop <= c.range[1]);
    if (!hit && this.strict) return Promise.reject(new Error(`the reader asked for bytes ${start} to ${stop}, which the layout does not plan`));
    if (!hit) return this.get(start, stop);
    if (hit.range[0] === start && hit.range[1] === stop) return hit.data;
    const data = hit.data.then((d) => d.slice(start - hit.range[0], stop - hit.range[0]));
    this.copies.set(key, { parent: hit.range, data });
    return data;
  }
}

export interface ReadStep {
  /** the row group being read, from 0 */
  readonly group: number;
  readonly groups: number;
  /** the strings of the rows just read that the list keeps, in the file's
   *  order */
  readonly words: string[];
  /** the rows read so far, and the file's rows */
  readonly rowsRead: number;
  readonly rows: number;
  /** the bytes requested so far */
  readonly bytes: number;
}

export interface ReadOptions {
  readonly signal?: AbortSignal;
  /** rows in a window (WINDOW_ROWS); the tests use smaller windows */
  readonly windowRows?: number;
}

/** The list `sel` selects from the universe file. */
export function readList(
  fetchRange: FetchRange,
  layout: Layout,
  sel: Selection,
  lengthCap: number,
  signal?: AbortSignal,
): AsyncGenerator<ReadStep> {
  return readRows(fetchRange, layout, rowTest(sel, lengthCap), { signal });
}

/** A column's decoded values for the rows [start, start + length). */
interface Chunk {
  readonly start: number;
  readonly length: number;
  readonly at: (i: number) => unknown;
}

/** A decoded column of few distinct values (a list's names, the classes, a
 *  count, a flag, a null) as 1 byte per row and its distinct values, so a
 *  row group's worth costs about a byte a row; a column of more than 255
 *  distinct values (the strings) is kept as decoded. */
function packed(start: number, data: ArrayLike<unknown>): Chunk {
  // each closure is made in its own function: a closure made here would
  // hold `data`, the whole decoded array, for as long as the chunk lives
  const values: unknown[] = [];
  const index = new Map<unknown, number>();
  const codes = new Uint8Array(data.length);
  for (let i = 0; i < data.length; i++) {
    const v = data[i];
    let c = index.get(v);
    if (c === undefined) {
      if (values.length === 255) return plain(start, data);
      c = values.length;
      index.set(v, c);
      values.push(v);
    }
    codes[i] = c;
  }
  return coded(start, values, codes);
}

function plain(start: number, data: ArrayLike<unknown>): Chunk {
  return { start, length: data.length, at: (j) => data[j] };
}

function coded(start: number, values: readonly unknown[], codes: Uint8Array): Chunk {
  return { start, length: codes.length, at: (j) => values[codes[j]] };
}

/** A column's value at a row, from its decoded chunks, for rows asked in
 *  increasing order. */
function cursor(name: string, chunks: readonly Chunk[]): (row: number) => unknown {
  let k = 0;
  return (row) => {
    while (k < chunks.length && row >= chunks[k].start + chunks[k].length) k++;
    const c = chunks[k];
    if (!c || row < c.start) throw new Error(`the file's ${name} column holds no value for row ${row}`);
    return c.at(row - c.start);
  };
}

/** Whether decoded chunks, which are contiguous, hold rows [a, b). */
function covers(chunks: readonly Chunk[] | undefined, a: number, b: number): boolean {
  if (!chunks?.length) return false;
  const last = chunks[chunks.length - 1];
  return chunks[0].start <= a && last.start + last.length >= b;
}

/** The decoded chunks of 1 column for rows [rowStart, rowEnd). hyparquet
 *  skips the pages before the window and stops after it, so a chunk may
 *  begin before the window or run past it, and says where it begins. */
async function decodeColumn(
  file: AsyncBuffer,
  metadata: FileMetaData,
  column: string,
  rowStart: number,
  rowEnd: number,
): Promise<Chunk[]> {
  const chunks: Chunk[] = [];
  await parquetRead({
    file,
    metadata,
    columns: [column],
    rowStart,
    rowEnd,
    compressors,
    onChunk: (c) => {
      chunks.push(column === 'word' ? plain(c.rowStart, c.columnData) : packed(c.rowStart, c.columnData));
    },
  });
  return chunks;
}

/** The strings of the rows `rows.test` keeps, reading only `rows.columns`:
 *  a row group's ranges at a time, the next group's arriving while this one
 *  is read, and each group's rows tested and handed on a window at a time
 *  (WINDOW_ROWS), with whole decoded pages kept as long as a window needs
 *  them. The test sees each row through 1 reused object. The file must be the one the layout
 *  describes: its rows, its row groups, and the metadata the layout records
 *  are checked first. */
export async function* readRows(
  fetchRange: FetchRange,
  layout: Layout,
  rows: RowTest,
  options: ReadOptions = {},
): AsyncGenerator<ReadStep> {
  const file = new RangedFile(fetchRange, layout.bytes, options.signal);
  const metadata: FileMetaData = await parquetMetadataAsync(file, { initialFetchSize: FOOTER_READ });
  const groups = metadata.row_groups.map((g) => Number(g.num_rows));
  if (Number(metadata.num_rows) !== layout.rows || groups.join() !== layout.row_groups.map((g) => g.rows).join()) {
    throw new Error('the file is not the one the layout describes');
  }
  const kv = new Map((metadata.key_value_metadata ?? []).map((e) => [e.key, e.value]));
  for (const [key, value] of Object.entries(layout.metadata ?? {})) {
    if (kv.get(key) !== value) throw new Error(`the file's ${key} is not the one the layout records`);
  }
  const { columns, test } = rows;
  // the columns read must lie where the layout says, or the planned ranges
  // would not hold them: checked before any of them is fetched
  metadata.row_groups.forEach((group, g) => {
    for (const c of columns) {
      const span = layout.row_groups[g].columns[c];
      const meta = group.columns.find((x) => x.meta_data?.path_in_schema.join('.') === c)?.meta_data;
      if (!span) throw new Error(`the layout has no column ${c}`);
      if (!meta) throw new Error(`the file has no column ${c}`);
      // where hyparquet begins reading the chunk, and its length
      const first = Number(meta.dictionary_page_offset || meta.data_page_offset);
      if (first !== span[0] || Number(meta.total_compressed_size) !== span[1]) {
        throw new Error(`the file's ${c} column in row group ${g + 1} is not where the layout records it`);
      }
    }
  });
  file.strict = true;
  const window = Math.max(1, options.windowRows ?? WINDOW_ROWS);
  const ranges = groups.map((_, g) => rangesFor(layout, g, columns));
  const view: Record<string, unknown> = {};
  let start = 0;
  let next = file.hold(ranges[0]);
  for (let g = 0; g < groups.length; g++) {
    await next;
    // the next row group's bytes arrive while this one is decoded
    if (g + 1 < groups.length) next = file.hold(ranges[g + 1]);
    const end = start + groups[g];
    // a page is decoded whole: a column whose decoded chunks still cover the
    // next window (a small column is often 1 page for the whole group) is
    // kept, not decoded again
    const decoded = new Map<string, Chunk[]>();
    for (let a = start; a < end; a += window) {
      const b = Math.min(end, a + window);
      // 1 column at a time, so only 1 column's decoding buffers exist at once
      for (const c of columns) {
        if (!covers(decoded.get(c), a, b)) {
          decoded.delete(c);
          decoded.set(c, await decodeColumn(file, metadata, c, a, b));
        }
      }
      const at = columns.map((c) => cursor(c, decoded.get(c)!));
      const words: string[] = [];
      for (let i = a; i < b; i++) {
        for (let k = 0; k < columns.length; k++) view[columns[k]] = at[k](i);
        if (test(view)) words.push(view.word as string);
      }
      yield { group: g, groups: groups.length, words, rowsRead: b, rows: layout.rows, bytes: file.read };
    }
    file.release(ranges[g]);
    start = end;
  }
}
