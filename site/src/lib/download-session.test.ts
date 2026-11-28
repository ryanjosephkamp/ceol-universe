/**
 * A download attempt ends for good when it is cancelled, replaced, or left:
 * whatever it was awaiting at the time, it starts no worker afterward, its
 * notices fetch is aborted, and no message of its worker reaches the page.
 */

import { describe, expect, it } from 'vitest';
import { DownloadSession, type Attempt, type DownloadState, type WorkerLike } from './download-session';
import type { DownloadMessage, DownloadRequest } from './list-download';
import type { Layout } from './list-read';
import type { TextFile } from './list-zip';

class FakeWorker implements WorkerLike {
  onmessage: ((e: { data: DownloadMessage }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  sent: DownloadRequest[] = [];
  terminated = false;
  postMessage(m: DownloadRequest) {
    this.sent.push(m);
  }
  terminate() {
    this.terminated = true;
  }
  say(m: DownloadMessage) {
    this.onmessage?.({ data: m });
  }
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
}

const layout = { rows: 10 } as Layout;
const NOTICES: readonly TextFile[] = [{ name: 'NOTICES.md', text: 'notices\n' }];

function harness() {
  const states: DownloadState[] = [];
  const workers: FakeWorker[] = [];
  const saved: string[] = [];
  const session = new DownloadSession({
    onState: (s) => states.push(s),
    makeWorker: () => {
      const w = new FakeWorker();
      workers.push(w);
      return w;
    },
    save: (_blob, name) => saved.push(name),
  });
  const signals: AbortSignal[] = [];
  const pending: ReturnType<typeof deferred<readonly TextFile[]>>[] = [];
  const attempt = (name: string): Attempt => ({
    request: { url: 'https://example.test/f.parquet', layout, filter: { of: 'open', sel: {}, lengthCap: 25 }, expected: 3, listName: 'list.txt' },
    files: (signal) => {
      signals.push(signal);
      const d = deferred<readonly TextFile[]>();
      pending.push(d);
      return d.promise;
    },
    zipName: name,
  });
  const last = () => states[states.length - 1];
  return { session, states, workers, saved, signals, pending, attempt, last };
}

const settle = () => new Promise((r) => setTimeout(r, 0));

describe('a download attempt', () => {
  it('runs to the end: the worker gets the files, and the zip is saved under its name', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].resolve(NOTICES);
    await run;
    expect(h.workers).toHaveLength(1);
    expect(h.workers[0].sent[0].files).toEqual(NOTICES);
    h.workers[0].say({ kind: 'progress', read: 5, total: 10, rows: 2, bytes: 100 });
    expect(h.last()).toEqual({ kind: 'running', read: 5, total: 10, rows: 2, bytes: 100 });
    h.workers[0].say({ kind: 'done', blob: new Blob(['x']), rows: 3, bytes: 200 });
    expect(h.saved).toEqual(['a.zip']);
    expect(h.last()).toEqual({ kind: 'done', name: 'a.zip', rows: 3, bytes: 200 });
    expect(h.workers[0].terminated).toBe(true);
  });

  it('cancelled while its notices load, starts no worker when they arrive', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.session.cancel();
    expect(h.signals[0].aborted).toBe(true);
    h.pending[0].resolve(NOTICES);
    await run;
    await settle();
    expect(h.workers).toHaveLength(0);
    expect(h.last()).toEqual({ kind: 'idle' });
  });

  it('replaced while its notices load, leaves the new attempt alone', async () => {
    const h = harness();
    const first = h.session.start(h.attempt('first.zip'));
    const second = h.session.start(h.attempt('second.zip'));
    expect(h.signals[0].aborted).toBe(true);
    h.pending[0].resolve(NOTICES);
    await first;
    expect(h.workers).toHaveLength(0);
    h.pending[1].resolve(NOTICES);
    await second;
    expect(h.workers).toHaveLength(1);
    h.workers[0].say({ kind: 'done', blob: new Blob(['x']), rows: 3, bytes: 1 });
    expect(h.saved).toEqual(['second.zip']);
  });

  it('cancelled while its worker runs, stops the worker and ignores what it says later', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].resolve(NOTICES);
    await run;
    const w = h.workers[0];
    h.session.cancel();
    expect(w.terminated).toBe(true);
    const seen = h.states.length;
    w.say({ kind: 'progress', read: 9, total: 10, rows: 3, bytes: 1 });
    w.say({ kind: 'done', blob: new Blob(['x']), rows: 3, bytes: 1 });
    w.onerror?.(new Error('late'));
    expect(h.states.length).toBe(seen);
    expect(h.last()).toEqual({ kind: 'idle' });
    expect(h.saved).toEqual([]);
  });

  it('left (the page unmounted, or the list changed), reports nothing, not even a failure', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.session.stop();
    const seen = h.states.length;
    h.pending[0].reject(new Error('aborted'));
    await run;
    expect(h.states.length).toBe(seen);
    expect(h.workers).toHaveLength(0);
  });

  it('whose worker the browser refuses, fails and leaves nothing running', async () => {
    const states: DownloadState[] = [];
    const session = new DownloadSession({
      onState: (st) => states.push(st),
      makeWorker: () => {
        throw new DOMException('Workers are blocked here.', 'SecurityError');
      },
      save: () => {
        throw new Error('nothing to save');
      },
    });
    const h = harness();
    const attempt = h.attempt('a.zip');
    const run = session.start(attempt);
    h.pending[0].resolve(NOTICES);
    await expect(run).resolves.toBeUndefined();
    expect(states.map((st) => st.kind)).toEqual(['running', 'failed']);
    expect(states.at(-1)).toEqual({ kind: 'failed', reason: 'The download could not start in this browser.' });
  });

  it('whose message the worker refuses, fails and stops the worker', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].resolve(NOTICES);
    const refusing = FakeWorker.prototype.postMessage;
    FakeWorker.prototype.postMessage = () => {
      throw new DOMException('could not be cloned', 'DataCloneError');
    };
    try {
      await expect(run).resolves.toBeUndefined();
    } finally {
      FakeWorker.prototype.postMessage = refusing;
    }
    expect(h.last()).toEqual({ kind: 'failed', reason: 'The download could not start in this browser.' });
    expect(h.workers[0].terminated).toBe(true);
    expect(h.workers[0].onmessage).toBeNull();
  });

  it('done, ignores a callback of its worker that arrives later, even 1 kept from before', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].resolve(NOTICES);
    await run;
    const w = h.workers[0];
    const keptError = w.onerror!;
    const keptMessage = w.onmessage!;
    w.say({ kind: 'done', blob: new Blob(['x']), rows: 3, bytes: 1 });
    expect(h.last()).toEqual({ kind: 'done', name: 'a.zip', rows: 3, bytes: 1 });
    expect(w.onmessage).toBeNull();
    expect(w.onerror).toBeNull();
    const seen = h.states.length;
    keptError(new Error('late'));
    keptMessage({ data: { kind: 'failed', reason: 'late' } });
    keptMessage({ data: { kind: 'done', blob: new Blob(['y']), rows: 9, bytes: 9 } });
    expect(h.states.length).toBe(seen);
    expect(h.last()).toEqual({ kind: 'done', name: 'a.zip', rows: 3, bytes: 1 });
    expect(h.saved).toEqual(['a.zip']);
  });

  it('failed, ignores a later done from a callback kept from before', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].resolve(NOTICES);
    await run;
    const kept = h.workers[0].onmessage!;
    h.workers[0].say({ kind: 'failed', reason: 'the count differs' });
    kept({ data: { kind: 'done', blob: new Blob(['x']), rows: 3, bytes: 1 } });
    expect(h.last()).toEqual({ kind: 'failed', reason: 'the count differs' });
    expect(h.saved).toEqual([]);
  });

  it('whose notices fail, says so', async () => {
    const h = harness();
    const run = h.session.start(h.attempt('a.zip'));
    h.pending[0].reject(new Error('The notices that travel with the list did not load.'));
    await run;
    expect(h.last()).toEqual({ kind: 'failed', reason: 'The notices that travel with the list did not load.' });
    expect(h.workers).toHaveLength(0);
  });
});
