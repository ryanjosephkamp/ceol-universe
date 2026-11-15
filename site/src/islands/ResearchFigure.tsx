import { useEffect, useRef, useState, type ReactNode } from 'react';
import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import { compact, full, pct, ticks } from '../charts/format';
import '../charts/charts.css';
import './research.css';

/* The figures of the technical report and the Research section, each drawn
   from its entry of the descriptive analysis (analysis.json), with a table
   view and a readout that states the figure under the pointer or focus. */

type Entry = { id: string; question: string; note?: string; population: string; data: any };

const SHORT: Record<string, string> = {
  WordNet: 'WordNet',
  'Wiktionary (English)': 'Wiktionary',
  'hunspell en_US': 'en_US',
  'hunspell en_GB': 'en_GB',
  'hunspell en_CA': 'en_CA',
  'hunspell en_AU': 'en_AU',
  ENABLE: 'ENABLE',
  SCOWL: 'SCOWL',
};
/** column labels short enough for a narrow grid; the rows carry the names */
const ABBR: Record<string, string> = {
  WordNet: 'WN',
  'Wiktionary (English)': 'Wikt',
  'hunspell en_US': 'US',
  'hunspell en_GB': 'GB',
  'hunspell en_CA': 'CA',
  'hunspell en_AU': 'AU',
  ENABLE: 'EN',
  SCOWL: 'SC',
};
const share = (x: number | null | undefined, digits = 1) => (x == null ? 'n/a' : `${(100 * x).toFixed(digits)}%`);

/** The width of an element, so a drawing keeps its labels' size. */
function useWidth(fallback = 640): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/** Whether the screen is phone-narrow, so a figure can show less at once. */
function useNarrow(query = '(max-width: 34rem)'): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setNarrow(m.matches);
    on();
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, [query]);
  return narrow;
}

/** The view a figure shows, stated for print, where its controls are hidden. */
function Shown({ children }: { children: ReactNode }) {
  return <p className="rf-shown">Shown: {children}</p>;
}

function Readout({ children }: { children: ReactNode }) {
  return (
    <p className="rf-readout" aria-live="polite">
      {children}
    </p>
  );
}

function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: readonly { key: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="rf-seg" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.key} type="button" role="radio" aria-checked={value === o.key} onClick={() => onChange(o.key)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* S2: directed containment as an asymmetric heat map */
function Containment({ e }: { e: Entry }) {
  const d = e.data;
  const lists: string[] = d.lists;
  const [mode, setMode] = useState<'containment' | 'jaccard'>('containment');
  const [at, setAt] = useState<[number, number] | null>(null);
  const value = (a: number, b: number) => (mode === 'containment' ? d.containment[a][b] : d.jaccard[a][b]);
  const cell = (a: number, b: number) => {
    if (a === b) return <span className="hm-cell hm-diag" key={b} aria-hidden="true" />;
    const v = value(a, b) ?? 0;
    const dark = v > 0.55;
    return (
      <span
        key={b}
        className={`hm-cell${dark ? ' dark' : ''}${at && at[0] === a && at[1] === b ? ' on' : ''}`}
        style={{ ['--v' as string]: `${Math.round(v * 100)}%` }}
        tabIndex={0}
        role="gridcell"
        aria-label={`${SHORT[lists[a]]} in ${SHORT[lists[b]]}: ${share(value(a, b), 0)}`}
        onMouseEnter={() => setAt([a, b])}
        onFocus={() => setAt([a, b])}
      >
        {Math.round(v * 100)}
      </span>
    );
  };
  const readout = at ? (
    mode === 'containment' ? (
      <>
        <strong>{share(d.containment[at[0]][at[1]])}</strong> of {SHORT[lists[at[0]]]}&rsquo;s {full(d.eligible[at[0]][at[1]])} rows that {SHORT[lists[at[1]]]} can hold are listed by {SHORT[lists[at[1]]]}
        {d.blind[at[0]][at[1]] > 0 && <>; {full(d.blind[at[0]][at[1]])} of its rows ({share(d.blind_share[at[0]][at[1]])}) {SHORT[lists[at[1]]]} cannot hold</>}.
      </>
    ) : (
      <>
        Jaccard <strong>{(d.jaccard[at[0]][at[1]] ?? 0).toFixed(3)}</strong>: {full(d.both[at[0]][at[1]])} rows both list, of {full(d.either[at[0]][at[1]])} either lists, over the rows both can hold.
      </>
    )
  ) : (
    'Point at or focus a cell: the row is list A, the column list B.'
  );
  return (
    <ChartFrame
      title="How far each list contains the others"
      note="Of the rows list A lists that list B can hold, the share B lists. Read across a row; the map is not symmetric, so nesting shows as a bright cell beside a dim one. Columns: WN WordNet, Wikt Wiktionary, US, GB, CA, and AU the hunspell dictionaries, EN ENABLE, SC SCOWL."
      table={[]}
      tableView={
        <table className="chart-table">
          <thead>
            <tr>
              <th scope="col">A, listed by B</th>
              {lists.map((l) => (
                <th key={l} scope="col" className="num">
                  {SHORT[l]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lists.map((a, i) => (
              <tr key={a}>
                <th scope="row">{SHORT[a]}</th>
                {lists.map((b, j) => (
                  <td key={b} className="num">
                    {i === j ? '—' : share(value(i, j), 0)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      }
      actions={
        <Segmented
          label="Measure"
          value={mode}
          onChange={setMode}
          options={[
            { key: 'containment', label: 'Containment' },
            { key: 'jaccard', label: 'Jaccard' },
          ]}
        />
      }
    >
      <div className="hm-wrap" onMouseLeave={() => setAt(null)}>
        <div className="hm" role="grid" aria-label="Containment of each list in each other list" style={{ ['--n' as string]: lists.length }}>
          <span className="hm-corner" aria-hidden="true">
            A ↓ B →
          </span>
          {lists.map((l) => (
            <span key={l} className="hm-col" aria-hidden="true" title={SHORT[l]}>
              {ABBR[l]}
            </span>
          ))}
          {lists.map((a, i) => (
            <div className="hm-row" role="row" key={a}>
              <span className="hm-rowlabel" role="rowheader">
                <span className="hm-full">{SHORT[a]}</span>
                <span className="hm-abbr" aria-hidden="true">
                  {ABBR[a]}
                </span>
              </span>
              {lists.map((_b, j) => cell(i, j))}
            </div>
          ))}
        </div>
      </div>
      <Readout>{readout}</Readout>
      <Shown>{mode === 'containment' ? 'containment' : 'the Jaccard index'}</Shown>
    </ChartFrame>
  );
}

/* S3: the combinations of families, as an intersection plot */
function Intersections({ e }: { e: Entry }) {
  const d = e.data;
  const families: string[] = d.families;
  const [withNone, setWithNone] = useState(false);
  const [at, setAt] = useState<number | null>(null);
  const narrow = useNarrow();
  const shown = narrow ? 10 : 15;
  const combos: { families: string[]; rows: number }[] = d.combinations
    .filter((c: any) => withNone || c.families.length > 0)
    .slice(0, shown + (withNone ? 1 : 0));
  const max = Math.max(1, ...combos.map((c) => c.rows));
  const listed = d.combinations.filter((c: any) => c.families.length).reduce((a: number, c: any) => a + c.rows, 0);
  const sel = at === null ? null : combos[at];
  return (
    <ChartFrame
      title="Which families list the rows"
      note={`Over the ${full(d.rows)} rows all ${families.length} families can hold; the ${combos.length} largest combinations. A filled dot marks a family that lists the rows.`}
      table={combos.map((c) => ({ label: c.families.join(', ') || 'no family', value: c.rows }))}
      total={withNone ? d.rows : listed}
      actions={
        <button type="button" className="chart-switch" aria-pressed={withNone} onClick={() => setWithNone((x) => !x)}>
          {withNone ? 'Hide' : 'Show'} rows no family lists
        </button>
      }
    >
      <div className="ix-scroll">
        <div className="ix" style={{ ['--k' as string]: combos.length }} onMouseLeave={() => setAt(null)}>
          <div className="ix-bars" aria-hidden="true">
            <span className="ix-axis" />
            {combos.map((c, i) => (
              <span key={i} className={`ix-bar${at === i ? ' on' : ''}`} onMouseEnter={() => setAt(i)}>
                <span className="ix-n">{compact(c.rows)}</span>
                <span className="ix-fill" style={{ height: `${Math.max(1.5, (100 * c.rows) / max)}%` }} />
              </span>
            ))}
          </div>
          {families.map((f) => (
            <div className="ix-row" key={f}>
              <span className="ix-fam">{f}</span>
              {combos.map((c, i) => (
                <span
                  key={i}
                  className={`ix-dot${c.families.includes(f) ? ' in' : ''}${at === i ? ' on' : ''}`}
                  onMouseEnter={() => setAt(i)}
                  tabIndex={f === families[0] ? 0 : -1}
                  onFocus={() => setAt(i)}
                  aria-label={f === families[0] ? `${c.families.join(', ') || 'no family'}: ${full(c.rows)} rows` : undefined}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      <Readout>
        {sel ? (
          <>
            <strong>{full(sel.rows)}</strong> rows are listed by {sel.families.length ? sel.families.join(', ') : 'no family'}
            {sel.families.length > 0 && ` and by no other family`}: {pct(sel.rows, withNone ? d.rows : listed)} of the {withNone ? 'rows' : 'listed rows'}.
          </>
        ) : (
          'Point at a column, or focus the first row of dots, for its count.'
        )}
      </Readout>
    </ChartFrame>
  );
}

/* S6: coverage by frequency band, 1 small chart per list */
function Coverage({ e }: { e: Entry }) {
  const d = e.data;
  const [metric, setMetric] = useState<'share' | 'token_weighted_share'>('share');
  const [at, setAt] = useState<{ list: string; band: number } | null>(null);
  const bands: string[] = d.bands.filter((b: string, i: number) => i > 0 && d.rows_per_band[i] > 0);
  const W = 240;
  const H = 120;
  const M = { l: 30, r: 8, t: 8, b: 22 };
  const x = (i: number) => M.l + ((W - M.l - M.r) * i) / Math.max(1, bands.length - 1);
  const y = (v: number) => M.t + (H - M.t - M.b) * (1 - v);
  return (
    <ChartFrame
      title="Coverage by frequency"
      note="For each band of wordfreq's Zipf value, the share of the rows a list can hold that it lists. Most rows have no Zipf value; that band is stated under each chart."
      table={[]}
      tableView={
        <table className="chart-table">
          <thead>
            <tr>
              <th scope="col">List</th>
              {d.bands.map((b: string, i: number) => d.rows_per_band[i] > 0 && (
                <th key={b} scope="col" className="num">
                  {b}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.lists.map((l: any) => (
              <tr key={l.list}>
                <th scope="row">{l.list}</th>
                {l.bands.map((b: any, i: number) => d.rows_per_band[i] > 0 && (
                  <td key={b.band} className="num">
                    {share(b[metric] ?? (metric === 'token_weighted_share' && i === 0 ? null : b.share), 0)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      }
      actions={
        <Segmented
          label="Count"
          value={metric}
          onChange={setMetric}
          options={[
            { key: 'share', label: 'By strings' },
            { key: 'token_weighted_share', label: 'By tokens' },
          ]}
        />
      }
    >
      <div className="cov-grid" onMouseLeave={() => setAt(null)}>
        {d.lists.map((l: any) => {
          const pts = l.bands.filter((_b: any, i: number) => i > 0 && d.rows_per_band[i] > 0);
          const vals = pts.map((b: any) => b[metric] ?? 0);
          const lo = pts.map((b: any) => (b.interval ? b.interval[0] : b.share ?? 0));
          const hi = pts.map((b: any) => (b.interval ? b.interval[1] : b.share ?? 0));
          const path = vals.map((v: number, i: number) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
          const band =
            metric === 'share'
              ? hi.map((v: number, i: number) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('') +
                lo
                  .map((v: number, i: number) => [i, v] as const)
                  .reverse()
                  .map(([i, v]: readonly [number, number]) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`)
                  .join('') +
                'Z'
              : '';
          return (
            <div className="cov-card" key={l.list}>
              <p className="cov-name">{l.list}</p>
              <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${l.list}: ${pts.map((b: any, i: number) => `${bands[i]} ${share(b[metric], 0)}`).join(', ')}`}>
                {[0, 0.5, 1].map((t) => (
                  <g key={t}>
                    <line className="cov-grid-line" x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} />
                    <text className="cov-axis" x={M.l - 5} y={y(t)} dy="0.32em" textAnchor="end">
                      {t * 100}%
                    </text>
                  </g>
                ))}
                {bands.map((b, i) => (
                  <text key={b} className="cov-axis" x={x(i)} y={H - 6} textAnchor="middle">
                    {b.replace(' to ', '–').replace(' and over', '+')}
                  </text>
                ))}
                {band && <path className="cov-band" d={band} />}
                <path className="cov-line" d={path} />
                {vals.map((v: number, i: number) => (
                  <circle
                    key={i}
                    className={`cov-dot${at && at.list === l.list && at.band === i ? ' on' : ''}`}
                    cx={x(i)}
                    cy={y(v)}
                    r={at && at.list === l.list && at.band === i ? 4.5 : 3}
                    tabIndex={0}
                    aria-label={`${l.list}, band ${bands[i]}: ${share(v)}`}
                    onMouseEnter={() => setAt({ list: l.list, band: i })}
                    onFocus={() => setAt({ list: l.list, band: i })}
                  />
                ))}
              </svg>
              <p className="cov-none">No Zipf value: {share(l.bands[0].share)} listed</p>
            </div>
          );
        })}
      </div>
      <Readout>
        {at ? (
          (() => {
            const l = d.lists.find((x: any) => x.list === at.list);
            const b = l.bands.filter((_b: any, i: number) => i > 0 && d.rows_per_band[i] > 0)[at.band];
            return (
              <>
                <strong>{share(b[metric])}</strong> {metric === 'share' ? 'of the' : 'of the tokens of the'} {full(b.can_hold)} rows {at.list} can hold in the band {b.band} are listed by it
                {metric === 'share' && b.interval && <> (95% interval {share(b.interval[0])} to {share(b.interval[1])})</>}.
              </>
            );
          })()
        ) : (
          'Point at or focus a dot for its share, the rows behind it, and its 95% interval, which at these sizes is narrower than the line.'
        )}
      </Readout>
      <Shown>{metric === 'share' ? 'shares by strings' : 'shares weighted by tokens'}</Shown>
    </ChartFrame>
  );
}

/* S13: the union's growth as lists are added in every order */
function Accumulation({ e }: { e: Entry }) {
  const d = e.data;
  const pts: { lists: number; mean: number; min: number; max: number; subsets: number }[] = d.accumulation;
  const [ref, W] = useWidth();
  const H = 220;
  const M = { l: 56, r: 12, t: 22, b: 40 };
  const top = ticks(d.union_of_all, 4);
  const ymax = top[top.length - 1];
  const x = (k: number) => M.l + ((W - M.l - M.r) * k) / (pts.length - 1);
  const y = (v: number) => M.t + (H - M.t - M.b) * (1 - v / ymax);
  const [at, setAt] = useState<number | null>(null);
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.lists).toFixed(1)},${y(p.mean).toFixed(1)}`).join('');
  const band =
    pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.lists).toFixed(1)},${y(p.max).toFixed(1)}`).join('') +
    [...pts].reverse().map((p) => `L${x(p.lists).toFixed(1)},${y(p.min).toFixed(1)}`).join('') +
    'Z';
  const sel = at === null ? null : pts[at];
  return (
    <ChartFrame
      title="How the union grows as lists are added"
      note="For each number of lists, the mean union over every choice of that many lists, and its smallest and largest."
      table={pts.slice(1).map((p) => ({ label: `${p.lists} list${p.lists === 1 ? '' : 's'}, mean`, value: Math.round(p.mean) }))}
    >
      <div ref={ref} className="acc" onMouseLeave={() => setAt(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`The union grows from ${full(Math.round(pts[1].mean))} rows on average for 1 list to ${full(d.union_of_all)} for all ${pts.length - 1}.`}>
          {top.map((t) => (
            <g key={t}>
              <line className="cov-grid-line" x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} />
              <text className="cov-axis" x={M.l - 6} y={y(t)} dy="0.32em" textAnchor="end">
                {compact(t)}
              </text>
            </g>
          ))}
          {pts.map((p) => (
            <text key={p.lists} className="cov-axis" x={x(p.lists)} y={H - 22} textAnchor="middle">
              {p.lists}
            </text>
          ))}
          <text className="cov-axis acc-title" x={M.l + (W - M.l - M.r) / 2} y={H - 4} textAnchor="middle">
            Lists added
          </text>
          <text className="cov-axis acc-title" x={M.l - 6} y={10} textAnchor="end">
            Rows listed
          </text>
          <path className="cov-band" d={band} />
          <path className="cov-line" d={line} />
          {pts.map((p, i) => (
            <g key={p.lists}>
              <rect
                x={x(p.lists) - 14}
                y={M.t}
                width={28}
                height={H - M.t - M.b}
                fill="transparent"
                tabIndex={p.lists > 0 ? 0 : -1}
                aria-label={`${p.lists} lists: a mean union of ${full(Math.round(p.mean))} rows`}
                onMouseEnter={() => setAt(i)}
                onFocus={() => setAt(i)}
              />
              <circle className={`cov-dot${at === i ? ' on' : ''}`} cx={x(p.lists)} cy={y(p.mean)} r={at === i ? 4.5 : 3} />
            </g>
          ))}
        </svg>
      </div>
      <Readout>
        {sel && sel.lists > 0 ? (
          <>
            With <strong>{sel.lists}</strong> list{sel.lists === 1 ? '' : 's'}: a mean union of <strong>{full(Math.round(sel.mean))}</strong> rows, from {full(sel.min)} to {full(sel.max)} over {full(sel.subsets)} choices.
          </>
        ) : (
          `All ${pts.length - 1} lists list ${full(d.union_of_all)} rows. Point at a step for its range.`
        )}
      </Readout>
    </ChartFrame>
  );
}

/* S5: agreement among families, by frequency band */
function Agreement({ e }: { e: Entry }) {
  const d = e.data;
  const rows = d.by_frequency_band.filter((r: any) => r.m === 5 && r.k > 0);
  const bands: string[] = Array.from(new Set(rows.map((r: any) => r.key))) as string[];
  const [at, setAt] = useState<{ band: string; k: number } | null>(null);
  const totals = Object.fromEntries(bands.map((b) => [b, rows.filter((r: any) => r.key === b).reduce((a: number, r: any) => a + r.rows, 0)]));
  const cellOf = (b: string, k: number) => rows.find((r: any) => r.key === b && r.k === k)?.rows ?? 0;
  return (
    <ChartFrame
      title="How many families list a row, by frequency"
      note="The listed rows all 5 families can hold, by the number of families that list them, in each band of wordfreq's Zipf value."
      table={[]}
      tableView={
        <table className="chart-table">
          <thead>
            <tr>
              <th scope="col">Zipf band</th>
              {[1, 2, 3, 4, 5].map((k) => (
                <th key={k} scope="col" className="num">
                  {k} of 5
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bands.map((b) => (
              <tr key={b}>
                <th scope="row">{b}</th>
                {[1, 2, 3, 4, 5].map((k) => (
                  <td key={k} className="num">
                    {full(cellOf(b, k))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <ul className="ag-legend">
        {[1, 2, 3, 4, 5].map((k) => (
          <li key={k}>
            <span className={`ag-key rf-k${k}`} aria-hidden="true" />
            {k} of 5
          </li>
        ))}
      </ul>
      <div className="ag" onMouseLeave={() => setAt(null)}>
        {bands.map((b) => (
          <div className="ag-row" key={b}>
            <span className="ag-band">{b}</span>
            <span className="ag-bar">
              {[1, 2, 3, 4, 5].map((k) => {
                const n = cellOf(b, k);
                return n ? (
                  <span
                    key={k}
                    className={`ag-seg rf-k${k}${at && at.band === b && at.k === k ? ' on' : ''}`}
                    style={{ flexGrow: n }}
                    onMouseEnter={() => setAt({ band: b, k })}
                  />
                ) : null;
              })}
            </span>
            <span className="ag-n">{compact(totals[b])}</span>
          </div>
        ))}
      </div>
      <Readout>
        {at ? (
          <>
            <strong>{full(cellOf(at.band, at.k))}</strong> rows in the band {at.band} are listed by {at.k} of the 5 families: {pct(cellOf(at.band, at.k), totals[at.band])} of its listed rows.
          </>
        ) : (
          'The darker the segment, the more families agree. Point at a segment for its count.'
        )}
      </Readout>
    </ChartFrame>
  );
}

/* P1: how each intake layer reaches each tier */
const TIER_ORDER = ['2+ families', '1 family', 'corpus only', 'no evidence', 'multiword'];
const LAYER_NAMES: Record<string, string> = {
  eol_invalid: "The English OpenList's invalid list",
  eol_valid: "The English OpenList's valid list",
  c1_exceptions: 'The census',
  c4_additions: "The audit's additions",
  spaced_c015: 'The spaced admission',
};
function Flows({ e }: { e: Entry }) {
  const flows = e.data.flows as Record<string, Record<string, Record<string, number>>>;
  const layers = Object.keys(flows).sort((a, b) => sumLayer(flows[b]) - sumLayer(flows[a]));
  const [at, setAt] = useState<{ layer: string; tier: string } | null>(null);
  const by = (layer: string, tier: string) => Object.values(flows[layer]).reduce((a, g) => a + (g[tier] ?? 0), 0);
  return (
    <ChartFrame
      title="How each intake layer reaches each evidence tier"
      note="Each bar is 1 intake layer, its rows split by evidence tier; multiword rows are their own group."
      table={layers.flatMap((l) => TIER_ORDER.filter((t) => by(l, t)).map((t) => ({ label: `${LAYER_NAMES[l] ?? l}: ${t}`, value: by(l, t) })))}
    >
      <ul className="ag-legend">
        {TIER_ORDER.map((t, i) => (
          <li key={t}>
            <span className={`fl-key rf-t${i}`} aria-hidden="true" />
            {t}
          </li>
        ))}
      </ul>
      <div className="ag" onMouseLeave={() => setAt(null)}>
        {layers.map((l) => (
          <div className="ag-row fl-row" key={l}>
            <span className="ag-band">{LAYER_NAMES[l] ?? l}</span>
            <span className="ag-bar">
              {TIER_ORDER.map((t, i) =>
                by(l, t) ? (
                  <span key={t} className={`ag-seg fl rf-t${i}${at && at.layer === l && at.tier === t ? ' on' : ''}`} style={{ flexGrow: by(l, t) }} onMouseEnter={() => setAt({ layer: l, tier: t })} />
                ) : null,
              )}
            </span>
            <span className="ag-n">{compact(sumLayer(flows[l]))}</span>
          </div>
        ))}
      </div>
      <Readout>
        {at ? (
          <>
            <strong>{full(by(at.layer, at.tier))}</strong> rows of {LAYER_NAMES[at.layer] ?? at.layer} are in the tier &ldquo;{at.tier}&rdquo;: {pct(by(at.layer, at.tier), sumLayer(flows[at.layer]))} of the layer.
          </>
        ) : (
          'Point at a segment for its count.'
        )}
      </Readout>
    </ChartFrame>
  );
}
function sumLayer(kinds: Record<string, Record<string, number>>) {
  return Object.values(kinds).reduce((a, g) => a + Object.values(g).reduce((x, y) => x + y, 0), 0);
}

/* F1 and U1: a distribution by group, 1 group at a time */
function ByGroup({ title, note, groups, bins, counts, label, tableLabels, axis }: { title: string; note: string; groups: string[]; bins: string[]; counts: Record<string, number[]>; label: string; tableLabels?: string[]; axis: string }) {
  const [g, setG] = useState(groups.includes('corpus only') ? 'corpus only' : groups[0]);
  const values = counts[g] ?? [];
  const total = values.reduce((a, b) => a + b, 0);
  return (
    <ChartFrame
      title={title}
      note={note}
      table={values.map((v, i) => ({ label: (tableLabels ?? bins)[i], value: v }))}
      total={total}
      actions={<Segmented label="Group" value={g} onChange={setG} options={groups.map((x) => ({ key: x, label: x }))} />}
    >
      <Columns label={`${label}, ${g}`} columns={values.map((v, i) => ({ key: String(i), label: bins[i], name: (tableLabels ?? bins)[i], value: v }))} total={total} labelEvery={Math.ceil(values.length / 10)} height={160} />
      <p className="rf-axis">{axis}</p>
      <Shown>{g}</Shown>
    </ChartFrame>
  );
}

function Flags({ e }: { e: Entry }) {
  const d = e.data;
  const bars = (d.flags as string[]).map((f) => ({ key: f, label: f, value: (d.rows_by_flag[f] as number[]).reduce((a, b) => a + b, 0) }));
  const total = (d.combinations as any[]).reduce((a, c) => a + c.rows, 0);
  return (
    <ChartFrame title="Rows per spelling class" note="A row can carry several classes; a row with none is plain." table={bars} total={total}>
      <BarList label="Rows per spelling class" bars={bars} total={total} />
    </ChartFrame>
  );
}

export default function ResearchFigure({ id, entry }: { id: string; entry: Entry }) {
  switch (id) {
    case 'S2':
      return <Containment e={entry} />;
    case 'S3':
      return <Intersections e={entry} />;
    case 'S5':
      return <Agreement e={entry} />;
    case 'S6':
      return <Coverage e={entry} />;
    case 'S13':
      return <Accumulation e={entry} />;
    case 'P1':
      return <Flows e={entry} />;
    case 'F4':
      return <Flags e={entry} />;
    case 'F1': {
      const by = entry.data.by_group as Record<string, { counts: number[] }>;
      return (
        <ByGroup
          title="Length in characters, by evidence tier"
          note="The rows of each group by their length; the last column holds every longer row."
          groups={Object.keys(by)}
          bins={entry.data.length_bins}
          counts={Object.fromEntries(Object.entries(by).map(([k, v]) => [k, v.counts]))}
          label="Rows by length"
          axis="Length in characters"
        />
      );
    }
    case 'U1': {
      const z = entry.data.wordfreq_zipf;
      const edges: number[] = z.edges;
      // each column is labeled by its lower edge; the table names both edges
      const bins = edges.slice(0, -1).map((a: number) => String(a));
      const groups = Object.keys(z.by_tier).filter((t) => z.by_tier[t].with_value > 0);
      return (
        <ByGroup
          title="wordfreq's Zipf value, by evidence tier"
          note="The rows wordfreq scores, by their Zipf value. Most rows have none, and the tier with no evidence has none by definition."
          groups={groups}
          bins={bins}
          tableLabels={edges.slice(0, -1).map((a: number, i: number) => `${a} to ${edges[i + 1]}`)}
          counts={Object.fromEntries(groups.map((t) => [t, z.by_tier[t].counts]))}
          label="Rows by Zipf value"
          axis="wordfreq's Zipf value (the lower edge of each half-unit band)"
        />
      );
    }
    default:
      return null;
  }
}
