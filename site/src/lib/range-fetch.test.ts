/**
 * A byte range is taken only as asked: a 206 whose visible Content-Range or
 * Content-Length names other bytes or another file size is refused, and so
 * is a body of another length, a longer one before the rest of it is read.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { rangeFetcher } from './list-read';

const FILE = Uint8Array.from({ length: 100 }, (_, i) => i);

/** A stream of `bytes` in pieces of `piece`, counting the pieces pulled. */
function stream(bytes: Uint8Array, piece: number, pulled: { n: number }) {
  let at = 0;
  return new ReadableStream<Uint8Array>({
    pull(c) {
      if (at >= bytes.length) return c.close();
      pulled.n++;
      c.enqueue(bytes.slice(at, at + piece));
      at += piece;
    },
  });
}

function answer(status: number, body: Uint8Array | ReadableStream<Uint8Array>, headers: Record<string, string>) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(body, { status, headers })));
}

afterEach(() => vi.unstubAllGlobals());

describe('a range request', () => {
  const get = rangeFetcher('https://example.test/f.parquet', 100);

  it('returns the bytes asked for', async () => {
    answer(206, FILE.slice(10, 14), { 'content-range': 'bytes 10-13/100', 'content-length': '4' });
    expect([...new Uint8Array(await get(10, 14))]).toEqual([10, 11, 12, 13]);
  });

  it('takes an answer whose Content-Range is not visible, at the right length', async () => {
    answer(206, FILE.slice(10, 14), {});
    expect(new Uint8Array(await get(10, 14))).toHaveLength(4);
  });

  it('takes the unit in any case and the total in any spelling of the same number', async () => {
    answer(206, FILE.slice(10, 14), { 'content-range': 'Bytes 10-13/100', 'content-length': '4' });
    expect([...new Uint8Array(await get(10, 14))]).toEqual([10, 11, 12, 13]);
    answer(206, FILE.slice(10, 14), { 'content-range': 'BYTES 10-13/0100' });
    expect(new Uint8Array(await get(10, 14))).toHaveLength(4);
  });

  it('refuses other bytes of the same length', async () => {
    answer(206, FILE.slice(90, 94), { 'content-range': 'bytes 90-93/100' });
    await expect(get(10, 14)).rejects.toThrow('"bytes 90-93/100" to a request for bytes 10-13 of 100');
  });

  it('refuses another file size, an unknown size, and a malformed range', async () => {
    answer(206, FILE.slice(10, 14), { 'content-range': 'bytes 10-13/99' });
    await expect(get(10, 14)).rejects.toThrow('bytes 10-13/99');
    answer(206, FILE.slice(10, 14), { 'content-range': 'bytes 10-13/*' });
    await expect(get(10, 14)).rejects.toThrow('bytes 10-13/*');
    answer(206, FILE.slice(10, 14), { 'content-range': 'items 10-13/100' });
    await expect(get(10, 14)).rejects.toThrow('items 10-13/100');
  });

  it('refuses a whole file, a short body, and an announced length that differs', async () => {
    answer(200, FILE, {});
    await expect(get(10, 14)).rejects.toThrow('answered 200');
    answer(206, FILE.slice(10, 12), { 'content-range': 'bytes 10-13/100' });
    await expect(get(10, 14)).rejects.toThrow('returned 2 bytes, not 4');
    answer(206, FILE.slice(10, 14), { 'content-range': 'bytes 10-13/100', 'content-length': '5' });
    await expect(get(10, 14)).rejects.toThrow('announced 5 bytes');
  });

  it('stops reading a longer body at its first extra byte', async () => {
    const pulled = { n: 0 };
    answer(206, stream(FILE, 4, pulled), {});
    await expect(get(10, 14)).rejects.toThrow('more than 4 bytes');
    // the 1st piece fills the range, the 2nd overflows it, and the rest of
    // the 100 bytes (25 pieces) is never pulled
    expect(pulled.n).toBeLessThanOrEqual(3);
  });
});
