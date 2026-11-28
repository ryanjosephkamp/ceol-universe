// The open subset's cube, written at build time from the pipeline's committed
// file (pipeline/research/release/open_cube_v1.0.json, which
// research/release/open_compose.py counts from the subset's open-lists file);
// Compose from the open subset computes every count from it.
import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const GET: APIRoute = () => {
  const file = JSON.parse(readFileSync(resolve(process.cwd(), '../pipeline/research/release/open_cube_v1.0.json'), 'utf-8'));
  // the cells and what the engine needs, without the prose fields
  const { version, dataset, commit, source, caps, dimensions, cells } = file;
  return new Response(JSON.stringify({ version, dataset, commit, source, caps, dimensions, cells }), {
    headers: { 'Content-Type': 'application/json' },
  });
};
