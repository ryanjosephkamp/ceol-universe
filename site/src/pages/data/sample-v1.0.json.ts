// The Explore page's data: the site's sample rows of version 1.0, written at build
// time. These are sample data for the lookup, not examples (site/README.md).
import type { APIRoute } from 'astro';
import { VERSION, publishedSets, sampleManifest, sampleRows } from '../../lib/data';
import { SAMPLE_COLUMNS, type SampleFile } from '../../lib/sample';

export const GET: APIRoute = () => {
  const file: SampleFile = {
    version: VERSION,
    drawn_from: sampleManifest.source.rows,
    published_sets: publishedSets,
    columns: SAMPLE_COLUMNS,
    rows: sampleRows.map((r) => SAMPLE_COLUMNS.map((c) => r[c] ?? null)),
  };
  return new Response(JSON.stringify(file), { headers: { 'Content-Type': 'application/json' } });
};
