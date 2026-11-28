/**
 * The page's side of a list download: 1 attempt at a time. Starting,
 * cancelling, a changed list, and leaving the page each end the attempt in
 * progress: its notices fetch is aborted, its worker is stopped, and nothing
 * it does afterward reaches the page, whatever it was awaiting when it
 * ended. ZipDownload.tsx draws the states; this module holds the attempts,
 * so they can be tested without a page.
 */

import type { DownloadMessage, DownloadRequest } from './list-download';
import type { TextFile } from './list-zip';

export type DownloadState =
  | { readonly kind: 'idle' }
  | { readonly kind: 'running'; readonly read: number; readonly total: number; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'done'; readonly name: string; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'failed'; readonly reason: string };

/** The part of a Worker a session uses. */
export interface WorkerLike {
  onmessage: ((e: { data: DownloadMessage }) => void) | null;
  onerror: ((e: unknown) => void) | null;
  postMessage(m: DownloadRequest): void;
  terminate(): void;
}

export interface SessionHooks {
  readonly onState: (s: DownloadState) => void;
  readonly makeWorker: () => WorkerLike;
  /** hands the reader the zip */
  readonly save: (blob: Blob, name: string) => void;
}

export interface Attempt {
  /** the worker's request, without the files made when it starts */
  readonly request: Omit<DownloadRequest, 'files'>;
  /** the files beside the list, fetched or made when the attempt starts;
   *  the signal aborts when the attempt ends */
  readonly files: (signal: AbortSignal) => Promise<readonly TextFile[]>;
  readonly zipName: string;
}

export class DownloadSession {
  private attempt = 0;
  private worker: WorkerLike | null = null;
  private abort: AbortController | null = null;

  constructor(private readonly hooks: SessionHooks) {}

  /** Ends the attempt in progress, if any, without a word to the page. */
  stop(): void {
    this.attempt++;
    this.abort?.abort();
    this.abort = null;
    this.worker?.terminate();
    this.worker = null;
  }

  /** Ends the attempt in progress and shows the button again. */
  cancel(): void {
    this.stop();
    this.hooks.onState({ kind: 'idle' });
  }

  async start(a: Attempt): Promise<void> {
    this.stop();
    const id = this.attempt;
    const live = () => this.attempt === id;
    const abort = new AbortController();
    this.abort = abort;
    let worker: WorkerLike | null = null;
    /** Ends the attempt with its last state. The attempt is ended first and
     *  its worker's callbacks detached, so no later event of it, a callback
     *  kept from before included, can replace that state. */
    const settle = (state: DownloadState, before?: () => void) => {
      if (!live()) return;
      this.attempt++;
      this.abort = null;
      if (worker) {
        worker.onmessage = null;
        worker.onerror = null;
        worker.terminate();
      }
      this.worker = null;
      try {
        before?.();
      } catch {
        this.hooks.onState({ kind: 'failed', reason: 'The browser did not save the file.' });
        return;
      }
      this.hooks.onState(state);
    };
    this.hooks.onState({ kind: 'running', read: 0, total: a.request.layout.rows, rows: 0, bytes: 0 });
    let files: readonly TextFile[];
    try {
      files = await a.files(abort.signal);
    } catch (err) {
      settle({ kind: 'failed', reason: err instanceof Error ? err.message : 'The files that travel with the list did not load.' });
      return;
    }
    if (!live()) return;
    this.abort = null;
    // a browser can refuse a worker outright (a SecurityError where workers
    // are blocked) or refuse its message: either ends the attempt as a
    // worker's error does
    try {
      const w = this.hooks.makeWorker();
      worker = w;
      this.worker = w;
      w.onmessage = (e) => {
        if (!live()) return;
        const m = e.data;
        if (m.kind === 'progress') {
          this.hooks.onState({ kind: 'running', read: m.read, total: m.total, rows: m.rows, bytes: m.bytes });
        } else if (m.kind === 'failed') {
          settle({ kind: 'failed', reason: m.reason });
        } else {
          settle({ kind: 'done', name: a.zipName, rows: m.rows, bytes: m.bytes }, () => this.hooks.save(m.blob, a.zipName));
        }
      };
      w.onerror = () => settle({ kind: 'failed', reason: 'The download stopped in the browser.' });
      w.postMessage({ ...a.request, files });
    } catch {
      settle({ kind: 'failed', reason: 'The download could not start in this browser.' });
    }
  }
}
