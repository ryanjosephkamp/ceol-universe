/**
 * Reading a composed list from the universe file, by byte range, for the list
 * download. The layout record (pipeline/research/release/layout_v1.0.json)
 * says where the strings and each criterion's column lie in every row group;
 * the reader requests only those, a row group at a time, so a phone never
 * holds the whole file, and it keeps the rows the list's test passes. The
 * file is sorted by `word`, so the strings come out in the order the code's
 * `ORDER BY word` gives.
 */

import { parquetMetadataAsync, parquetRead, type AsyncBuffer, type FileMetaData } from 'hyparquet';
import { compressors } from 'hyparquet-compressors';
import type { Selection } from './cube';
import { rowTest, type Row } from './list-filter';

export interface Layout {
  readonly version: string;
  readonly dataset: string;
  readonly hub_path: string;
  readonly bytes: number;
  readonly sha256: string;
  readonly rows: number;
  readonly row_groups: readonly {
    readonly rows: number;
    readonly columns: Readonly<Record<string, readonly [number, number] | readonly number[]>>;
  }[];
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

/** The bytes a download of `sel` reads: its ranges in every row group, and
 *  the footer. */
export function plannedBytes(layout: Layout, sel: Selection, lengthCap: number): number {
  const { columns } = rowTest(sel, lengthCap);
  let n = Math.min(FOOTER_READ, layout.bytes);
  for (let g = 0; g < layout.row_groups.length; g++) {
    for (const [s, e] of rangesFor(layout, g, columns)) n += e - s;
  }
  return n;
}

export type FetchRange = (start: number, end: number, signal?: AbortSignal) => Promise<ArrayBuffer>;

/** A fetch of 1 byte range of `url`. Only a partial answer (206) is taken:
 *  a server that ignores the range would send the whole file. */
export function rangeFetcher(url: string): FetchRange {
  return async (start, end, signal) => {
    const res = await fetch(url, { headers: { Range: `bytes=${start}-${end - 1}` }, signal });
    if (res.status !== 206) throw new Error(`the file's server answered ${res.status} to a range request`);
    const buf = await res.arrayBuffer();
    if (buf.byteLength !== end - start) throw new Error(`a range request returned ${buf.byteLength} bytes, not ${end - start}`);
    return buf;
  };
}

/** The file as hyparquet reads it, with each row group's ranges fetched in
 *  advance and every read inside them served from memory. */
class RangedFile implements AsyncBuffer {
  readonly byteLength: number;
  private cache: { range: Range; data: Promise<ArrayBuffer> }[] = [];
  read = 0;

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
  }

  async slice(start: number, end?: number): Promise<ArrayBuffer> {
    const stop = end ?? this.byteLength;
    const hit = this.cache.find((c) => c.range[0] <= start && stop <= c.range[1]);
    if (!hit) return this.get(start, stop);
    const data = await hit.data;
    return data.slice(start - hit.range[0], stop - hit.range[0]);
  }
}

export interface ReadStep {
  /** the row group just read, from 0 */
  readonly group: number;
  readonly groups: number;
  /** the strings of that row group the list keeps, in the file's order */
  readonly words: string[];
  /** the bytes requested so far */
  readonly bytes: number;
}

/** The list `sel` selects, a row group at a time. The file must be the one
 *  the layout describes: its length and row groups are checked first. */
export async function* readList(
  fetchRange: FetchRange,
  layout: Layout,
  sel: Selection,
  lengthCap: number,
  signal?: AbortSignal,
): AsyncGenerator<ReadStep> {
  const file = new RangedFile(fetchRange, layout.bytes, signal);
  const metadata: FileMetaData = await parquetMetadataAsync(file, { initialFetchSize: FOOTER_READ });
  const groups = metadata.row_groups.map((g) => Number(g.num_rows));
  if (Number(metadata.num_rows) !== layout.rows || groups.join() !== layout.row_groups.map((g) => g.rows).join()) {
    throw new Error('the file is not the one the layout describes');
  }
  const { columns, test } = rowTest(sel, lengthCap);
  const ranges = groups.map((_, g) => rangesFor(layout, g, columns));
  let start = 0;
  let next = file.hold(ranges[0]);
  for (let g = 0; g < groups.length; g++) {
    await next;
    // the next row group's bytes arrive while this one is decoded
    if (g + 1 < groups.length) next = file.hold(ranges[g + 1]);
    const rows = await new Promise<Row[]>((resolve, reject) => {
      parquetRead({
        file,
        metadata,
        columns: [...columns],
        rowStart: start,
        rowEnd: start + groups[g],
        compressors,
        rowFormat: 'object',
        onComplete: resolve,
      }).catch(reject);
    });
    file.release(ranges[g]);
    const words: string[] = [];
    for (const r of rows) if (test(r)) words.push(r.word as string);
    start += groups[g];
    yield { group: g, groups: groups.length, words, bytes: file.read };
  }
}
