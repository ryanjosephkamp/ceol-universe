/**
 * The proposed study's pages (site/content/study/), with their figures read
 * from site/content/study/figures.json, which tools/study_figures.py prints
 * from the study's own calculator. A `{{s:id}}` token the file does not
 * hold stops the build, as an unknown figure does elsewhere.
 */

import { readRepo, renderMarkdown } from './docs';

interface StudyFigure {
  readonly id: string;
  readonly value: number;
  readonly text: string;
  readonly row: string;
}

const file = JSON.parse(readRepo('site/content/study/figures.json')) as { figures: StudyFigure[]; commit: string };
const byId = new Map(file.figures.map((f) => [f.id, f]));

export const studyCommit = file.commit;

/** A content file with its tokens filled, as Markdown. */
export function studyMarkdown(name: string): string {
  const md = readRepo(`site/content/study/${name}.md`);
  return md.replace(/\{\{s:([a-z0-9_]+)\}\}/g, (_m, id: string) => {
    const f = byId.get(id);
    if (!f) throw new Error(`site/content/study/${name}.md quotes '${id}', which figures.json does not hold`);
    return f.text;
  });
}

/** A content file rendered to HTML, its top level at `level`. */
export function studyHtml(name: string, level = 2): string {
  const md = studyMarkdown(name);
  if (/\{\{|\}\}/.test(md)) throw new Error(`site/content/study/${name}.md has a malformed token`);
  return renderMarkdown(md, level);
}
