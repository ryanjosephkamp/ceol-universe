/**
 * The list download, off the page's thread: the worker runs runDownload
 * (list-download.ts) on the page's request and posts its messages back.
 */

import { runDownload, type DownloadMessage, type DownloadRequest } from './list-download';

export type { DownloadMessage, DownloadRequest, ListFilter } from './list-download';

const post = (m: DownloadMessage) => (self as unknown as Worker).postMessage(m);

self.onmessage = (e: MessageEvent<DownloadRequest>) => {
  void runDownload(e.data, post);
};
