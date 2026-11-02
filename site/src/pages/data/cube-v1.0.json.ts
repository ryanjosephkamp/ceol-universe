// The cube of version 1.0, written at build time from the pipeline's committed file
// (pipeline/research/release/figures/v1.0/cube.json); the interactive pages
// compute every count from it.
import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const GET: APIRoute = () => {
  const file = JSON.parse(
    readFileSync(resolve(process.cwd(), '../pipeline/research/release/figures/v1.0/cube.json'), 'utf-8'),
  );
  // the cells and what the engine needs, without the long prose fields
  const { version, dataset, built_on, caps, dimensions, cells } = file;
  return new Response(JSON.stringify({ version, dataset, built_on, caps, dimensions, cells }), {
    headers: { 'Content-Type': 'application/json' },
  });
};
