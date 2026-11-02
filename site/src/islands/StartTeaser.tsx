import { useEffect, useMemo, useState } from 'react';
import ScaleSquares from '../charts/ScaleSquares';
import { full, pct } from '../charts/format';
import { Cube, type CubeFile, type Selection } from '../lib/cube';
import { selectionQuery } from '../lib/selection-url';
import '../charts/charts.css';
import './teaser.css';

/** The criteria the teaser offers, each a part of a selection. */
const CRITERIA: readonly { key: string; label: string; part: Selection }[] = [
  { key: 'listed', label: 'On a published list', part: { minLists: 1 } },
  { key: 'broad', label: 'On 4 or more', part: { minLists: 4 } },
  { key: 'plain', label: 'Plain a to z', part: { flags: { plain: 'with' } } },
  { key: 'single', label: 'A single token', part: { values: { token_count: ['1'] } } },
  { key: 'nomodel', label: 'No model or engine', part: { values: { model_or_engine: ['none'] } } },
  { key: 'corpus', label: 'In Google Books', part: { values: { gb_type: ['true'] } } },
];

function combine(keys: ReadonlySet<string>): Selection {
  let sel: Selection = {};
  for (const c of CRITERIA) {
    if (!keys.has(c.key)) continue;
    sel = {
      ...sel,
      ...c.part,
      minLists: Math.max(sel.minLists ?? 0, c.part.minLists ?? 0),
      values: { ...sel.values, ...c.part.values },
      flags: { ...sel.flags, ...c.part.flags },
    };
  }
  return sel;
}

export default function StartTeaser({ cubeUrl }: { cubeUrl: string }) {
  const [cube, setCube] = useState<Cube | null>(null);
  const [on, setOn] = useState<ReadonlySet<string>>(new Set(['listed', 'plain']));
  // on load the list shrinks out of the whole universe, once
  const [intro, setIntro] = useState(true);
  useEffect(() => {
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<CubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then((f) => setCube(new Cube(f)), () => setCube(null));
  }, [cubeUrl]);
  useEffect(() => {
    if (!cube) return;
    const t = window.setTimeout(() => setIntro(false), 1400);
    return () => clearTimeout(t);
  }, [cube]);

  const sel = useMemo(() => combine(on), [on]);
  const v = useMemo(() => {
    if (!cube) return null;
    return { rows: cube.rows(sel), eol: cube.rows({ ...sel, values: { ...sel.values, eol: ['true'] } }) };
  }, [cube, sel]);

  const flip = (k: string) =>
    setOn((s) => {
      const next = new Set(s);
      if (next.has(k)) next.delete(k);
      else {
        next.add(k);
        // the 2 thresholds on published lists exclude each other
        if (k === 'broad') next.delete('listed');
        if (k === 'listed') next.delete('broad');
      }
      return next;
    });

  const total = cube?.total ?? 0;
  const introFrom = useMemo(
    () => (cube && intro ? { selected: cube.total, eol: cube.rows({ values: { eol: ['true'] } }) } : undefined),
    [cube, intro],
  );

  return (
    <div className="teaser">
      <p className="teaser-ask">Keep the rows that are</p>
      <ul className="teaser-chips">
        {CRITERIA.map((c) => (
          <li key={c.key}>
            <button type="button" aria-pressed={on.has(c.key)} onClick={() => flip(c.key)}>
              <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
                {on.has(c.key) ? (
                  <path d="M2.5 6.2l2.3 2.3 4.7-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                ) : (
                  <path d="M6 2.5v7M2.5 6h7" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                )}
              </svg>
              {c.label}
            </button>
          </li>
        ))}
      </ul>
      <div className="teaser-result">
        <div className="teaser-drawing">
          {v ? (
            <ScaleSquares universe={total} selected={v.rows} eol={v.eol} introFrom={introFrom} />
          ) : (
            <div className="sk sk-square" />
          )}
        </div>
        <div className="teaser-figures">
          <p className="teaser-count" aria-live="polite">
            {v ? (
              <>
                <strong>{full(v.rows)}</strong>
                <span>rows, {pct(v.rows, total)} of the universe</span>
              </>
            ) : (
              'Counting.'
            )}
          </p>
          <a className="teaser-go" href={`/compose/${selectionQuery(sel)}`}>
            Compose it, with its code
          </a>
        </div>
      </div>
      <p className="teaser-note">Each choice is a criterion over every row. The squares are to scale by area.</p>
    </div>
  );
}
