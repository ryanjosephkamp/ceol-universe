/** The pages of the Research section, in reading order. */
export const RESEARCH_PAGES = [
  { slug: '', label: 'Overview', blurb: 'What the research covers, and the sources compared at a glance.' },
  { slug: 'report', label: 'The technical report', blurb: 'The dataset described and measured, with every figure from code.' },
  { slug: 'literature', label: 'Literature', blurb: 'Comparable resources, documentation standards, and contamination, each claim checked at its source.' },
  { slug: 'study', label: 'The proposed study', blurb: 'A study design that has not been run: its question, design, instrument, and pilot.' },
] as const;
