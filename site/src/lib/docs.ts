/**
 * The dataset's own documents, rendered at build time: the public card
 * (pipeline/research/release/CARD_v1.0.md, held to its calculator by the
 * figure check) and the data dictionary (docs/DATA_DICTIONARY.md, generated
 * from the columns module). The site shows their text as written, so the
 * site and the dataset cannot say different things.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Marked } from 'marked';

const REPO = resolve(process.cwd(), '..');
const read = (rel: string) => readFileSync(resolve(REPO, rel), 'utf-8');

export const CARD_PATH = 'pipeline/research/release/CARD_v1.0.md';
export const DICTIONARY_PATH = 'docs/DATA_DICTIONARY.md';

/** The card without its YAML header, split at its `## ` sections. */
function sections(md: string): Map<string, string> {
  const body = md.replace(/^---\n[\s\S]*?\n---\n/, '');
  const out = new Map<string, string>();
  const parts = body.split(/^## /m);
  out.set('', parts[0]);
  for (const part of parts.slice(1)) {
    const nl = part.indexOf('\n');
    out.set(part.slice(0, nl).trim(), part.slice(nl + 1));
  }
  return out;
}

const card = sections(read(CARD_PATH));

/** A card section by its number, e.g. 1 for "1. Limitations". A number the
 *  card does not hold stops the build. */
export function cardSection(n: number, level = 3): { title: string; html: string } {
  const key = [...card.keys()].find((k) => k.startsWith(`${n}. `));
  if (!key) throw new Error(`${CARD_PATH} has no section ${n}`);
  return { title: key.replace(/^\d+\.\s*/, ''), html: render(card.get(key)!, level) };
}

/** A card section's text as plain prose, its Markdown marks removed: for
 *  the datasheet's "How to cite it". */
export function cardSectionText(n: number): string {
  const key = [...card.keys()].find((k) => k.startsWith(`${n}. `));
  if (!key) throw new Error(`${CARD_PATH} has no section ${n}`);
  return card
    .get(key)!
    .trim()
    .replace(/[`*_]/g, '')
    .replace(/\s+/g, ' ');
}

/** A repository document below its title, its top sections at `level`. */
export function renderFile(rel: string, level = 2): string {
  return render(read(rel).replace(/^# .*\n/, ''), level);
}

/** A repository file's text, read at build time. */
export function readRepo(rel: string): string {
  return read(rel);
}

/** Markdown text to HTML, its top level at `level`. */
export function renderMarkdown(md: string, level = 2): string {
  return render(md, level);
}

/** The data dictionary below its title, its sections a level down. */
export function dictionary(): string {
  const md = read(DICTIONARY_PATH).replace(/^# .*\n/, '');
  return render(md, 2);
}

/**
 * Markdown to HTML: GitHub's dialect, every table in its own scrolling box,
 * and headings moved so that a document's top level sits at `level`.
 */
function render(md: string, level: number): string {
  const marked = new Marked({ gfm: true });
  marked.use({
    renderer: {
      heading({ tokens, depth }) {
        const text = this.parser.parseInline(tokens);
        const d = Math.min(6, depth - 2 + level);
        const id = text
          .replace(/<[^>]+>/g, '')
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)/g, '');
        return `<h${d} id="${id}">${text}</h${d}>\n`;
      },
      table(token) {
        const head = token.header.map((c) => `<th scope="col"${c.align ? ` style="text-align:${c.align}"` : ''}>${this.parser.parseInline(c.tokens)}</th>`).join('');
        const rows = token.rows
          .map((r) => `<tr>${r.map((c, i) => (i === 0 ? `<th scope="row">${this.parser.parseInline(c.tokens)}</th>` : `<td${c.align ? ` style="text-align:${c.align}"` : ''}>${this.parser.parseInline(c.tokens)}</td>`)).join('')}</tr>`)
          .join('\n');
        return `<div class="doc-table"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>\n`;
      },
    },
  });
  return marked.parse(md, { async: false }) as string;
}
