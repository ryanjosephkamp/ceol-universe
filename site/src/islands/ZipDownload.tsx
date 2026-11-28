import { useEffect, useRef, useState, type ReactNode } from 'react';
import { full } from '../charts/format';
import { DownloadSession, type DownloadState, type WorkerLike } from '../lib/download-session';
import type { ListFilter } from '../lib/list-download';
import type { Layout } from '../lib/list-read';
import type { TextFile } from '../lib/list-zip';

/** Hands the reader a file made in the page. */
function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export const mb = (bytes: number) => (bytes < 100_000 ? 'less than 0.1 MB' : `${(bytes / 1e6).toFixed(bytes < 10e6 ? 1 : 0)} MB`);

export interface ZipDownloadProps {
  /** where the file is read, or null while it cannot be */
  readonly source: string | null;
  /** what the button says while `source` is null */
  readonly closedNote: ReactNode;
  readonly layout: Layout;
  readonly filter: ListFilter;
  /** the page's count for the list */
  readonly rows: number;
  /** changes whenever the list does; a change ends a download in progress */
  readonly listKey: string;
  readonly zipName: string;
  /** the list's text in bytes, estimated */
  readonly textBytes: number;
  /** the bytes of the file the download reads */
  readonly readBytes: number;
  /** the file the download reads, as the note names it */
  readonly fileLabel: string;
  /** the files beside the list in the zip, made when the download starts;
   *  the signal aborts when the attempt ends, and a rejection's message is
   *  shown as the reason */
  readonly files: (signal: AbortSignal) => Promise<readonly TextFile[]>;
}

/**
 * "Download the list": reads the list from the dataset's file in the
 * reader's browser, in a worker, and saves it as a zip with the files that
 * travel with it. A list whose rows differ from the page's count is refused.
 */
export default function ZipDownload(props: ZipDownloadProps) {
  const { source, layout, filter, rows, listKey } = props;
  const [state, setState] = useState<DownloadState>({ kind: 'idle' });
  const session = useRef<DownloadSession | null>(null);
  session.current ??= new DownloadSession({
    onState: setState,
    makeWorker: () => new Worker(new URL('../lib/list-download.worker.ts', import.meta.url), { type: 'module' }) as unknown as WorkerLike,
    save: saveBlob,
  });

  // a changed list ends a download of the one before it, and so does leaving
  // the page
  useEffect(() => {
    session.current?.stop();
    setState({ kind: 'idle' });
  }, [listKey]);
  useEffect(() => () => session.current?.stop(), []);

  if (!source) {
    return (
      <div className="take-item">
        <button type="button" className="take-btn primary" disabled>
          Download the list
        </button>
        <p className="take-note">{props.closedNote}</p>
      </div>
    );
  }
  if (rows === 0) {
    return (
      <div className="take-item">
        <button type="button" className="take-btn primary" disabled>
          Download the list
        </button>
        <p className="take-note">No row meets every criterion, so there is nothing to download.</p>
      </div>
    );
  }

  const start = () =>
    session.current?.start({
      request: { url: source, layout, filter, expected: rows, listName: 'list.txt' },
      files: props.files,
      zipName: props.zipName,
    });

  if (state.kind === 'running') {
    return (
      <div className="take-item" aria-live="polite">
        <progress className="take-progress" value={state.read} max={state.total} aria-label="Reading the list" />
        <p className="take-note">
          {full(state.read)} of {full(state.total)} rows read: {full(state.rows)} kept, {mb(state.bytes)} of the file requested.
        </p>
        <button type="button" className="take-btn quiet" onClick={() => session.current?.cancel()}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="take-item">
      <button type="button" className="take-btn primary" onClick={start}>
        {state.kind === 'done' ? 'Download it again' : state.kind === 'failed' ? 'Try again' : 'Download the list'}
      </button>
      <p className="take-note" aria-live="polite">
        {state.kind === 'done'
          ? `Saved ${state.name}: ${full(state.rows)} rows, with its datasheet and the license notices. ${mb(state.bytes)} read.`
          : state.kind === 'failed'
            ? `The download stopped: ${state.reason}`
            : `A .zip: the list (about ${mb(props.textBytes)} of text), its datasheet, and the license notices. It reads about ${mb(props.readBytes)} of ${props.fileLabel} in your browser.`}
      </p>
    </div>
  );
}
