// The notices of version 1.0, written at build time from the pipeline's committed
// file (pipeline/research/release/NOTICES_v1.0.md): the list download puts them in
// its zip beside the list, as the license requires.
import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const GET: APIRoute = () =>
  new Response(readFileSync(resolve(process.cwd(), '../pipeline/research/release/NOTICES_v1.0.md'), 'utf-8'), {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
