import { useEffect, useRef, useState } from 'react';
import { full } from '../charts/format';
import layoutFile from '../../../pipeline/research/release/layout_v1.0.json';
import { VERSION } from '../lib/codegen';
import type { Cube, Selection } from '../lib/cube';
import { DEFAULT_TITLE, buildSheet, sheetMarkdown, type SheetMeta } from '../lib/datasheet';
import type { DownloadMessage, DownloadRequest } from '../lib/list-download.worker';
import { plannedBytes, type Layout } from '../lib/list-read';
import { LIST_SOURCE } from '../lib/release-state';

const layout = layoutFile as Layout;

type State =
  | { readonly kind: 'idle' }
  | { readonly kind: 'running'; readonly group: number; readonly groups: number; readonly rows: number; readonly bytes: number }
  | { readonly kind: 'done'; readonly name: string; readonly rows: number }
  | { readonly kind: 'failed'; readonly reason: string };

const mb = (bytes: number) => (bytes < 100_000 ? 'less than 0.1 MB' : `${(bytes / 1e6).toFixed(bytes < 10e6 ? 1 : 0)} MB`);

/** The list's text in bytes, 1 string and a line break per row, from the
 *  lengths in characters; the top bucket counts as its least length, and a
 *  character outside ASCII takes more than 1 byte, so it is an estimate. */
function textBytes(cube: Cube, sel: Selection): number {
  return cube.byLength(sel, true).reduce((n, rows, i) => n + rows * (i + 2), 0);
}

/**
 * "Download the list": reads the list from the dataset's universe file in the
 * reader's browser and saves it as a zip with its datasheet and notices. While
 * the dataset is private it says it opens with the release.
 */
export default function ListDownload(props: {
  cube: Cube;
  sel: Selection;
  rows: number;
  query: string;
  citation: string;
  file: SheetMeta['file'];
}) {
  const { cube, sel, rows, query } = props;
  const [state, setState] = useState<State>({ kind: 'idle' });
  const worker = useRef<Worker | null>(null);

  const stop = () => {
    worker.current?.terminate();
    worker.current = null;
  };
  // a changed list ends a download of the one before it
  useEffect(() => {
    stop();
    setState({ kind: 'idle' });
  }, [query]);
  useEffect(() => stop, []);

  if (!LIST_SOURCE) {
    return (
      <div className="take-item">
        <button type="button" className="take-btn primary" disabled>
          Download the list
        </button>
        <p className="take-note">
          Opens with the public release of version {VERSION.slice(1)}. Until then, the code below reproduces the list.
        </p>
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

  const source = LIST_SOURCE;
  const start = async () => {
    stop();
    setState({ kind: 'running', group: 0, groups: layout.row_groups.length, rows: 0, bytes: 0 });
    let notices: string;
    try {
      const res = await fetch(`/data/NOTICES-${VERSION}.md`);
      if (!res.ok) throw new Error(String(res.status));
      notices = await res.text();
    } catch {
      setState({ kind: 'failed', reason: 'The notices that travel with the list did not load.' });
      return;
    }
    const meta: SheetMeta = {
      title: DEFAULT_TITLE,
      author: '',
      note: '',
      made: new Date(),
      link: `${window.location.origin}/compose/${query}`,
      citation: props.citation,
      file: props.file,
    };
    const name = `ceol-universe-${VERSION}-${rows}-rows.zip`;
    const w = new Worker(new URL('../lib/list-download.worker.ts', import.meta.url), { type: 'module' });
    worker.current = w;
    w.onmessage = (e: MessageEvent<DownloadMessage>) => {
      const m = e.data;
      if (m.kind === 'progress') setState({ kind: 'running', group: m.group, groups: m.groups, rows: m.rows, bytes: m.bytes });
      else if (m.kind === 'failed') {
        setState({ kind: 'failed', reason: m.reason });
        stop();
      } else {
        const url = URL.createObjectURL(m.blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
        setState({ kind: 'done', name, rows: m.rows });
        stop();
      }
    };
    w.onerror = () => {
      setState({ kind: 'failed', reason: 'The download stopped in the browser.' });
      stop();
    };
    const request: DownloadRequest = {
      url: source,
      layout,
      sel,
      lengthCap: cube.lengthCap,
      expected: rows,
      listName: 'list.txt',
      files: [
        { name: 'DATASHEET.md', text: sheetMarkdown(buildSheet(sel, cube), meta) },
        { name: 'NOTICES.md', text: notices },
      ],
    };
    w.postMessage(request);
  };

  if (state.kind === 'running') {
    return (
      <div className="take-item" aria-live="polite">
        <progress className="take-progress" value={state.group} max={state.groups} aria-label="Reading the list" />
        <p className="take-note">
          Row group {state.group} of {state.groups}: {full(state.rows)} rows kept, {mb(state.bytes)} read.
        </p>
        <button
          type="button"
          className="take-btn quiet"
          onClick={() => {
            stop();
            setState({ kind: 'idle' });
          }}
        >
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
          ? `Saved ${state.name}: ${full(state.rows)} rows, with its datasheet and the license notices.`
          : state.kind === 'failed'
            ? `The download stopped: ${state.reason}`
            : `A .zip: the list (about ${mb(textBytes(cube, sel))} of text), its datasheet, and the license notices. It reads about ${mb(plannedBytes(layout, sel, cube.lengthCap))} of the dataset's file in your browser.`}
      </p>
    </div>
  );
}
