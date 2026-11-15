/**
 * The download's file: a zip holding the list, 1 string per line, beside the
 * small text files that travel with it (its datasheet and the notices the
 * license requires). The list is compressed as it is read, so only the
 * compressed bytes are held.
 */

import { Zip, ZipDeflate } from 'fflate';

export interface TextFile {
  readonly name: string;
  readonly text: string;
}

export interface ListZip {
  /** adds strings to the list, each on its own line */
  push(words: readonly string[]): void;
  /** ends the zip and returns its bytes, in order */
  finish(): Uint8Array[];
}

export function listZip(listName: string, files: readonly TextFile[]): ListZip {
  const enc = new TextEncoder();
  const parts: Uint8Array[] = [];
  let failed: Error | null = null;
  const zip = new Zip((err, data) => {
    if (err) failed = err;
    else parts.push(data);
  });
  for (const f of files) {
    const entry = new ZipDeflate(f.name, { level: 6 });
    zip.add(entry);
    entry.push(enc.encode(f.text), true);
  }
  const list = new ZipDeflate(listName, { level: 6 });
  zip.add(list);
  return {
    push(words) {
      if (words.length) list.push(enc.encode(words.join('\n') + '\n'));
      if (failed) throw failed;
    },
    finish() {
      list.push(new Uint8Array(0), true);
      zip.end();
      if (failed) throw failed;
      return parts;
    },
  };
}
