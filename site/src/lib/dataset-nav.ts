/** The pages of the dataset section, in reading order. */
export const DATASET_PAGES = [
  { slug: '', label: 'Overview', blurb: 'What the dataset is, its configs, and how to load it.' },
  { slug: 'profile', label: 'Profile', blurb: 'Every dimension of every row, charted; click to filter them all.' },
  { slug: 'limitations', label: 'Limitations', blurb: 'What to know before using it, stated first.' },
  { slug: 'columns', label: 'Columns', blurb: 'The data dictionary: every column, its type, and its nulls.' },
  { slug: 'withheld', label: 'What is withheld', blurb: 'The lists, labels, rows, and feature columns this version leaves out, and why.' },
  { slug: 'sources', label: 'Sources and licenses', blurb: 'Where the strings come from, the licenses, and the credits.' },
  { slug: 'versions', label: 'Versions', blurb: 'The version, the pin it rests on, and the change log.' },
  { slug: 'cite', label: 'Cite and contact', blurb: 'How to cite it, how to ask for a change, and the canary.' },
] as const;
