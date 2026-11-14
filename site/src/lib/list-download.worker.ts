/**
 * The list download, off the page's thread: it reads the composed list from
 * the universe file (list-read.ts), zips it with its datasheet and notices
 * (list-zip.ts), and hands the page the zip, or a reason it made none. A list
 * whose rows differ from the page's count is never handed over.
 */

import type { Selection } from './cube';
import { rangeFetcher, readList, type Layout } from './list-read';
import { listZip, type TextFile } from './list-zip';

export interface DownloadRequest {
  readonly url: string;
  readonly layout: Layout;
  readonly sel: Selection;
  readonly lengthCap: number;
  /** the page's count for the list */
  readonly expected: number;
  readonly listName: string;
  readonly files: readonly TextFile[];
}

export type DownloadMessage =
  | { readonly kind: 'progress'; readonly group: number; readonly groups: number; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'done'; readonly blob: Blob; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'failed'; readonly reason: string };

const post = (m: DownloadMessage) => (self as unknown as Worker).postMessage(m);

self.onmessage = async (e: MessageEvent<DownloadRequest>) => {
  const { url, layout, sel, lengthCap, expected, listName, files } = e.data;
  try {
    const zip = listZip(listName, files);
    let rows = 0;
    let bytes = 0;
    for await (const step of readList(rangeFetcher(url), layout, sel, lengthCap)) {
      zip.push(step.words);
      rows += step.words.length;
      bytes = step.bytes;
      post({ kind: 'progress', group: step.group + 1, groups: step.groups, rows, bytes });
    }
    if (rows !== expected) {
      post({ kind: 'failed', reason: `The file held ${rows.toLocaleString('en-US')} rows, not the ${expected.toLocaleString('en-US')} this page counts, so it was not saved.` });
      return;
    }
    post({ kind: 'done', blob: new Blob(zip.finish() as BlobPart[], { type: 'application/zip' }), rows, bytes });
  } catch (err) {
    post({ kind: 'failed', reason: err instanceof Error ? err.message : String(err) });
  }
};
