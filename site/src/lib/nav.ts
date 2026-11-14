/** The site's sections, with the English OpenList's own
 *  section. `built` is false for a section this preview does not hold yet;
 *  the header names it without linking to it. */

export interface Section {
  readonly label: string;
  readonly href: string;
  readonly built: boolean;
  readonly blurb: string;
}

export const SECTIONS: readonly Section[] = [
  { label: 'Start', href: '/', built: true, blurb: 'What the universe is, and where to go next.' },
  { label: 'Explore', href: '/explore/', built: true, blurb: 'Look a string up and read its record.' },
  { label: 'Compose a list', href: '/compose/', built: true, blurb: 'Choose criteria, see the count, get the code.' },
  { label: 'The dataset', href: '/dataset/', built: true, blurb: 'The card, the data dictionary, versions, licenses, and how to cite.' },
  { label: 'How it was built', href: '/built/', built: true, blurb: 'The pipeline, step by step, with the count at each step.' },
  { label: 'Definitions', href: '/definitions/', built: true, blurb: 'What a candidate is, and the spelling grammar every candidate is written in.' },
  { label: 'Research', href: '/research/', built: true, blurb: 'The technical report, the literature, and the proposed study.' },
  { label: 'Run a study', href: '/study/', built: true, blurb: 'The study kit: sampling, labeling, and preregistration.' },
  { label: 'English OpenList', href: '/eol/', built: true, blurb: 'The EOL, a dated subset of the universe, and its downloads.' },
  { label: 'About', href: '/about/', built: true, blurb: 'The author, the sister projects, licenses, and the change log.' },
];

export const builtCount = SECTIONS.filter((s) => s.built).length;
