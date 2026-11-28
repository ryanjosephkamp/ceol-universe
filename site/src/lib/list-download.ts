/**
 * The list download's work, as the worker runs it (list-download.worker.ts):
 * it reads the composed list from the dataset's file (list-read.ts), zips
 * it with its datasheet and notices (list-zip.ts), and hands back the zip,
 * or a reason it made none. A list whose rows differ from the page's count
 * is never handed back. The file is the universe's, for Compose a list, or
 * the open subset's `open-lists`, for Compose from the open subset;
 * `filter` says which test the rows meet.
 */

import type { Selection } from './cube';
import { rowTest } from './list-filter';
import { rangeFetcher, readRows, type FetchRange, type Layout } from './list-read';
import { listZip, type TextFile } from './list-zip';
import type { OpenSelection } from './open-cube';
import { openRowTest } from './open-filter';

export type ListFilter =
  | { readonly of: 'universe'; readonly sel: Selection; readonly lengthCap: number }
  | { readonly of: 'open'; readonly sel: OpenSelection; readonly lengthCap: number };

export interface DownloadRequest {
  readonly url: string;
  readonly layout: Layout;
  readonly filter: ListFilter;
  /** the page's count for the list */
  readonly expected: number;
  readonly listName: string;
  readonly files: readonly TextFile[];
}

export type DownloadMessage =
  | { readonly kind: 'progress'; readonly read: number; readonly total: number; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'done'; readonly blob: Blob; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'failed'; readonly reason: string };

/** The row test a filter names. */
export const testOf = (f: ListFilter) => (f.of === 'open' ? openRowTest(f.sel, f.lengthCap) : rowTest(f.sel, f.lengthCap));

export interface RunOptions {
  /** how the file's bytes are fetched: by default, range requests to the URL */
  readonly fetchRange?: FetchRange;
  /** rows in a window (list-read.ts, WINDOW_ROWS); the tests use smaller windows */
  readonly windowRows?: number;
}

/** Reads, zips, and checks 1 list, posting its progress and then either the
 *  zip or the reason there is none. */
export async function runDownload(req: DownloadRequest, post: (m: DownloadMessage) => void, options: RunOptions = {}): Promise<void> {
  const { url, layout, filter, expected, listName, files } = req;
  try {
    const zip = listZip(listName, files);
    let rows = 0;
    let bytes = 0;
    const fetchRange = options.fetchRange ?? rangeFetcher(url, layout.bytes);
    for await (const step of readRows(fetchRange, layout, testOf(filter), { windowRows: options.windowRows })) {
      zip.push(step.words);
      rows += step.words.length;
      bytes = step.bytes;
      post({ kind: 'progress', read: step.rowsRead, total: step.rows, rows, bytes });
    }
    if (rows !== expected) {
      post({ kind: 'failed', reason: `The file held ${rows.toLocaleString('en-US')} rows, not the ${expected.toLocaleString('en-US')} this page counts, so it was not saved.` });
      return;
    }
    post({ kind: 'done', blob: new Blob(zip.finish() as BlobPart[], { type: 'application/zip' }), rows, bytes });
  } catch (err) {
    post({ kind: 'failed', reason: err instanceof Error ? err.message : String(err) });
  }
}
