/**
 * The study kit's documents (kit/*.md), rendered at build time for the
 * "Run a study" section, so the site and the kit say the same thing. A link
 * to another kit document becomes its page; a link to a repository path
 * becomes the path as code, since the site does not serve the repository.
 */

import { readRepo, renderMarkdown } from './docs';

export const KIT_PAGES = [
  { slug: '', file: 'README', label: 'The kit', blurb: 'Load a pinned version, draw a reproducible stratified sample, and use the notebooks.' },
  { slug: 'codebook', file: 'CODEBOOK', label: 'Codebook', blurb: 'A labeling codebook for annotators who label sampled candidates against a definition you choose.' },
  { slug: 'preregistration', file: 'PREREGISTRATION_TEMPLATE', label: 'Preregistration template', blurb: 'A form for the question, the sample, the labels, and the analysis. It registers nothing.' },
  { slug: 'contamination', file: 'CONTAMINATION', label: 'Contamination', blurb: 'The canary, the model-decided rows, mentions on this site, and dating a release.' },
] as const;

const route = new Map<string, string>(KIT_PAGES.map((p) => [`${p.file}.md`, `/study/${p.slug ? `${p.slug}/` : ''}`]));
/** repository documents the site shows as pages of its own */
const SITE_PAGES: Record<string, string> = {
  'docs/DATA_DICTIONARY.md': '/dataset/columns/',
  'pipeline/research/release/CARD_v1.0.md': '/dataset/',
};

export function kitHtml(file: string): { title: string; html: string } {
  const md = readRepo(`kit/${file}.md`);
  const title = (md.match(/^# (.*)$/m) ?? ['', file])[1];
  const body = md
    .replace(/^# .*\n/, '')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (whole, text: string, href: string) => {
      if (/^(https?:|mailto:|#)/.test(href)) return whole;
      const [path, anchor] = href.split('#');
      const page = route.get(path.replace(/^\.\//, '')) ?? SITE_PAGES[path.replace(/^(\.\.\/)+/, '')];
      if (page) return `[${text}](${page}${anchor ? `#${anchor}` : ''})`;
      // a repository path the site does not serve: its name as code, or the prose as written
      if (text.startsWith('`')) return text;
      return /[/.]/.test(text) ? `\`${text}\`` : text;
    });
  return { title, html: renderMarkdown(body, 2) };
}
