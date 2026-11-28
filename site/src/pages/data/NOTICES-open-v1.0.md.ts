// The notices of the open subset, version 1.0, written at build time from the
// pipeline's committed copy (pipeline/research/release/NOTICES_open_v1.0.md),
// which must be byte for byte the NOTICES.md the subset's upload put on the
// hub: its sha256 is checked against the upload's record, and a copy that
// differs stops the build. The open list download puts it in its zip beside
// the list, as the license requires.
import type { APIRoute } from 'astro';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const RELEASE = resolve(process.cwd(), '../pipeline/research/release');

export const GET: APIRoute = () => {
  const bytes = readFileSync(resolve(RELEASE, 'NOTICES_open_v1.0.md'));
  const upload = JSON.parse(readFileSync(resolve(RELEASE, 'hf_upload_open_v1.0.json'), 'utf-8')) as {
    files: { path: string; sha256: string }[];
  };
  const want = upload.files.find((f) => f.path === 'NOTICES.md')?.sha256;
  const got = createHash('sha256').update(bytes).digest('hex');
  if (!want || got !== want) {
    throw new Error(`NOTICES_open_v1.0.md has sha256 ${got}, not the ${want ?? '(none)'} of the subset's NOTICES.md on the hub`);
  }
  return new Response(bytes, { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
};
