import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import MiniSquare from '../charts/MiniSquare';
import ScaleSquares from '../charts/ScaleSquares';
import { full, pct } from '../charts/format';
import { codeFor } from '../lib/codegen';
import { Cube, FLAGS, PUBLISHED_SETS, type CubeFile, type Dim, type Flag, type FlagRule, type Selection } from '../lib/cube';
import type { SheetMeta } from '../lib/datasheet';
import { DATASET_PUBLIC } from '../lib/release-state';
import { normalizeSelection, readSelection, selectionQuery, writeSelection } from '../lib/selection-url';
import CopyButton from './CopyButton';
import ListDownload from './ListDownload';
import { CLASS_NAMES, INTAKE_KIND, INTAKE_LAYER, MOE_ORDER, MOE_SHORT, PROVENANCE, PROVENANCE_ORDER, SET_NAMES } from './labels';
import '../charts/charts.css';
import './compose.css';

const PRESETS: readonly { label: string; what: string; sel: Selection }[] = [
  { label: 'Everything', what: 'every row of the universe', sel: {} },
  { label: 'On a published list', what: 'at least 1 of the 8 published lists lists it', sel: { minLists: 1 } },
  { label: 'Broadly listed', what: 'at least 4 of the 8 published lists list it', sel: { minLists: 4 } },
  {
    label: 'Plain single tokens',
    what: 'a to z only, 1 token, on at least 1 published list',
    sel: { minLists: 1, flags: { plain: 'with' }, values: { token_count: ['1'] } },
  },
  { label: 'The English OpenList', what: 'its valid list at revision 08ae92b8', sel: { values: { eol: ['true'] } } },
  {
    label: 'Not made by the engine',
    what: 'no row the synthetic engine made',
    sel: { values: { model_or_engine: ['none'] } },
  },
];

const TRI: readonly [FlagRule, string][] = [
  ['any', 'Any'],
  ['with', 'With'],
  ['without', 'Without'],
];

const BOOL3 = [
  ['true', 'Yes'],
  ['false', 'No'],
  ['null', 'Not measured'],
] as const;

type Tab = 'duckdb' | 'polars' | 'pandas';

/** The last list composed on this device, so the menu's link brings it back. */
const STORE = 'ceol-compose';

function stored(): string {
  try {
    return localStorage.getItem(STORE) ?? '';
  } catch {
    return '';
  }
}

function store(query: string) {
  try {
    if (query) localStorage.setItem(STORE, query);
    else localStorage.removeItem(STORE);
  } catch {
    // storage refused (a private window): the address still holds the list
  }
}

function toggle(list: readonly string[] | undefined, v: string): string[] {
  const xs = list ?? [];
  return xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v];
}

function sameSelection(a: Selection, b: Selection): boolean {
  return JSON.stringify(normalize(a)) === JSON.stringify(normalize(b));
}

/** A selection with its empty parts dropped and its lists sorted. */
function normalize(s: Selection): Selection {
  const values: Partial<Record<Dim, string[]>> = {};
  for (const [d, v] of Object.entries(s.values ?? {})) if (v && v.length) values[d as Dim] = [...v].sort();
  const flags: Record<string, FlagRule> = {};
  for (const [f, r] of Object.entries(s.flags ?? {})) if (r && r !== 'any') flags[f] = r;
  return {
    values,
    listedBy: [...(s.listedBy ?? [])].sort(),
    minLists: s.minLists ?? 0,
    flags,
    minLength: s.minLength ?? null,
    maxLength: s.maxLength ?? null,
  };
}

export default function Compose({ cubeUrl, citation, file }: { cubeUrl: string; citation: string; file: SheetMeta['file'] }) {
  const [cube, setCube] = useState<Cube | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<Selection>({});
  const [tab, setTab] = useState<Tab>('duckdb');
  const codeRef = useRef<HTMLPreElement>(null);
  const [ready, setReady] = useState(false);
  // the "listed by at least" step a pointer or focus is on, for its readout
  const [lookK, setLookK] = useState<number | null>(null);
  const id = useId();

  useEffect(() => {
    // a shared address names its list; a bare one brings back the last list
    setSel(readSelection(window.location.search || stored()));
    setReady(true);
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<CubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then(
        (f) => {
          // a shared address may name values the cube does not hold; both the
          // count and the generated code then read the same normalized selection
          const c = new Cube(f);
          setSel((s) => normalizeSelection(s, c));
          setCube(c);
        },
        () => setFailed(true),
      );
  }, [cubeUrl]);

  useEffect(() => {
    if (!ready) return;
    writeSelection(sel);
    store(selectionQuery(sel));
  }, [sel, ready]);

  const view = useMemo(() => {
    if (!cube) return null;
    const rows = cube.rows(sel);
    const eolVals = sel.values?.eol;
    const eolRows = eolVals && eolVals.length && !eolVals.includes('true') ? 0 : cube.rows({ ...sel, values: { ...sel.values, eol: ['true'] } });
    return {
      rows,
      eolRows,
      lists: cube.byListCount(sel),
      listsOwn: cube.byListCount(sel, true),
      sets: cube.byList(sel),
      prov: cube.by('provenance_class', sel),
      provOwn: cube.by('provenance_class', sel, true),
      flags: cube.byFlag(sel),
      tokens: cube.by('token_count', sel),
      length: cube.byLength(sel),
      lengthOwn: cube.byLength(sel, true),
      gb: cube.by('gb_type', sel),
      wf: cube.by('wordfreq_scored', sel),
      wk: cube.by('wikt_title_any', sel),
      layer: cube.by('intake_layer', sel),
      kind: cube.by('intake_kind', sel),
      moe: cube.by('model_or_engine', sel),
      eol: cube.by('eol', sel),
    };
  }, [cube, sel]);

  const code = useMemo(() => (cube && view ? codeFor(sel, view.rows, cube.lengthCap) : null), [cube, view, sel]);

  if (failed) return <p className="compose-error">The data for this page did not load. Reload the page to try again.</p>;
  if (!cube || !view || !code) return <ComposeSkeleton />;

  const set = (patch: Partial<Selection>) => setSel((s) => ({ ...s, ...patch }));
  const setValues = (dim: Dim, vals: string[]) => setSel((s) => ({ ...s, values: { ...s.values, [dim]: vals } }));
  const setFlag = (f: Flag | 'plain', rule: FlagRule) => setSel((s) => ({ ...s, flags: { ...s.flags, [f]: rule } }));
  const total = cube.total;
  const cap = cube.lengthCap;
  const lengthLabel = (n: number) => (n >= cap ? `${cap}+` : String(n));
  const minL = sel.minLength ?? 1;
  const maxL = sel.maxLength ?? cap;
  const active = !sameSelection(sel, {});

  return (
    <div className="compose">
      <section className="compose-criteria" aria-label="Criteria">
        <div className="mobile-count">
          <MiniSquare universe={total} selected={view.rows} eol={view.eolRows} />
          <p aria-hidden="true">
            <strong>{full(view.rows)}</strong> rows, {pct(view.rows, total)}
          </p>
          <a href="#compose-take">Get your list</a>
        </div>
        <div className="presets">
          <span className="presets-label">Start from</span>
          <ul>
            {PRESETS.map((p) => (
              <li key={p.label}>
                <button
                  type="button"
                  title={p.what}
                  aria-pressed={sameSelection(sel, p.sel)}
                  onClick={() => setSel(p.sel)}
                >
                  {p.label}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <Group title="Published lists" hint="the 8 lists a public version names">
          <div className="crit">
            <p className="crit-label">Listed by at least</p>
            <div
              className="lists-step"
              role="radiogroup"
              aria-label="Listed by at least this many published lists"
              onPointerLeave={() => setLookK(null)}
            >
              {view.lists.map((n, k) => {
                const atLeast = view.lists.slice(k).reduce((a, b) => a + b, 0);
                const on = (sel.minLists ?? 0) === k;
                const inRange = k >= (sel.minLists ?? 0);
                // the scale is the listed rows' (k of 1 or more); the unlisted
                // column is far taller, so it is cut at the top and marked
                const top = Math.max(1, ...view.lists.slice(1));
                const clipped = n > top;
                const h = clipped ? 100 : Math.max(n ? 6 : 0, (100 * n) / top);
                return (
                  <button
                    key={k}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    aria-label={`${k} or more: ${full(atLeast)} rows`}
                    className={inRange ? 'in' : undefined}
                    onClick={() => set({ minLists: k })}
                    onPointerEnter={() => setLookK(k)}
                    onFocus={() => setLookK(k)}
                    onBlur={() => setLookK(null)}
                  >
                    <span className={clipped ? 'ls-bar clipped' : 'ls-bar'} style={{ height: `${h}%` }} aria-hidden="true">
                      {clipped && <span className="ls-break" />}
                    </span>
                    <span className="ls-k" aria-hidden="true">
                      {k}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="crit-note ls-readout" aria-hidden="true">
              {(() => {
                const k = lookK ?? sel.minLists ?? 0;
                const atLeast = view.lists.slice(k).reduce((a, b) => a + b, 0);
                const exactly = view.lists[k] ?? 0;
                if (k === 0) return `Any number, none included: ${full(atLeast)} rows, ${full(exactly)} of them listed by none.`;
                return `${k} or more of 8: ${full(atLeast)} rows. Exactly ${k}: ${full(exactly)}.`;
              })()}
            </p>
            <p className="crit-note">The column at 0 is cut: it stands for the rows no published list lists.</p>
          </div>
          <div className="crit">
            <p className="crit-label">And by every list checked</p>
            <div className="checks">
              {PUBLISHED_SETS.map((s) => (
                <Check
                  key={s}
                  label={SET_NAMES[s]}
                  n={view.sets.get(s) ?? 0}
                  checked={sel.listedBy?.includes(s) ?? false}
                  onChange={() => set({ listedBy: toggle(sel.listedBy, s) })}
                />
              ))}
            </div>
          </div>
        </Group>

        <Group title="What a row rests on" hint="its provenance class">
          <div className="checks">
            {PROVENANCE_ORDER.map((p) => (
              <Check
                key={p}
                label={PROVENANCE[p].label}
                title={PROVENANCE[p].what}
                n={view.prov.get(p) ?? 0}
                checked={sel.values?.provenance_class?.includes(p) ?? false}
                onChange={() => setValues('provenance_class', toggle(sel.values?.provenance_class, p))}
              />
            ))}
          </div>
        </Group>

        <Group title="Spelling" hint="classes, tokens, and length">
          <div className="flags" role="group" aria-label="Spelling classes">
            {(['plain', ...FLAGS] as const).map((f) => {
              const rule = sel.flags?.[f] ?? 'any';
              return (
                <div key={f} className="flag">
                  <span className="flag-label">{CLASS_NAMES[f]}</span>
                  <span className="flag-n">{full(view.flags.get(f) ?? 0)}</span>
                  <span className="tri" role="radiogroup" aria-label={CLASS_NAMES[f]}>
                    {TRI.map(([r, label]) => (
                      <button
                        key={r}
                        type="button"
                        role="radio"
                        aria-checked={rule === r}
                        onClick={() => setFlag(f, r)}
                      >
                        {label}
                      </button>
                    ))}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="crit">
            <p className="crit-label">Tokens</p>
            <div className="checks checks-row">
              {cube.values.token_count.map((t) => (
                <Check
                  key={t}
                  label={t === '1' ? '1 token' : `${t} tokens`}
                  n={view.tokens.get(t) ?? 0}
                  checked={sel.values?.token_count?.includes(t) ?? false}
                  onChange={() => setValues('token_count', toggle(sel.values?.token_count, t))}
                />
              ))}
            </div>
          </div>
          <div className="crit">
            <p className="crit-label">Length, in characters</p>
            <Columns
              label="Rows by length; pick a length, or Shift to extend the range"
              columns={view.length.map((n, i) => ({
                key: String(i + 1),
                label: lengthLabel(i + 1),
                name: `${lengthLabel(i + 1)} characters`,
                value: n,
              }))}
              total={view.length.reduce((a, b) => a + b, 0)}
              labelEvery={4}
              height={96}
              selected={(i) => i + 1 >= minL && i + 1 <= maxL && (minL > 1 || maxL < cap)}
              onPick={(i, extend) => {
                const L = i + 1;
                const ranged = sel.minLength != null || sel.maxLength != null;
                if (extend && ranged) {
                  const lo = Math.min(minL, L);
                  const hi = Math.max(maxL, L);
                  set({ minLength: lo === 1 ? null : lo, maxLength: hi >= cap ? null : hi });
                } else if (minL === L && maxL === L) {
                  set({ minLength: null, maxLength: null });
                } else {
                  set({ minLength: L === 1 ? null : L, maxLength: L >= cap ? null : L });
                }
              }}
            />
            <div className="range">
              <label>
                <span>From</span>
                <select value={minL} onChange={(e) => set({ minLength: Number(e.target.value) === 1 ? null : Number(e.target.value) })}>
                  {Array.from({ length: cap }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n} disabled={n > maxL}>
                      {lengthLabel(n)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>to</span>
                <select value={maxL} onChange={(e) => set({ maxLength: Number(e.target.value) >= cap ? null : Number(e.target.value) })}>
                  {Array.from({ length: cap }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n} disabled={n < minL}>
                      {n >= cap ? `${cap} or more` : n}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </Group>

        <Group title="Corpora" hint="multiword rows are not measured">
          {(
            [
              ['gb_type', 'A Google Books 1-gram type', view.gb],
              ['wordfreq_scored', 'Scored by wordfreq', view.wf],
              ['wikt_title_any', 'A Wiktionary page title', view.wk],
            ] as const
          ).map(([dim, label, counts]) => (
            <div key={dim} className="crit">
              <p className="crit-label">{label}</p>
              <div className="checks checks-row">
                {BOOL3.map(([v, l]) => (
                  <Check
                    key={v}
                    label={l}
                    n={counts.get(v) ?? 0}
                    checked={sel.values?.[dim]?.includes(v) ?? false}
                    onChange={() => setValues(dim, toggle(sel.values?.[dim], v))}
                  />
                ))}
              </div>
            </div>
          ))}
        </Group>

        <Group title="How a row came in" hint="its layer, its kind, and any model or engine">
          <div className="crit">
            <p className="crit-label">Layer</p>
            <div className="checks">
              {cube.values.intake_layer.map((v) => (
                <Check
                  key={v}
                  label={sentence(INTAKE_LAYER[v] ?? v)}
                  n={view.layer.get(v) ?? 0}
                  checked={sel.values?.intake_layer?.includes(v) ?? false}
                  onChange={() => setValues('intake_layer', toggle(sel.values?.intake_layer, v))}
                />
              ))}
            </div>
          </div>
          <div className="crit">
            <p className="crit-label">Kind</p>
            <div className="checks">
              {cube.values.intake_kind.map((v) => (
                <Check
                  key={v}
                  label={sentence(INTAKE_KIND[v] ?? v)}
                  n={view.kind.get(v) ?? 0}
                  checked={sel.values?.intake_kind?.includes(v) ?? false}
                  onChange={() => setValues('intake_kind', toggle(sel.values?.intake_kind, v))}
                />
              ))}
            </div>
          </div>
          <div className="crit">
            <p className="crit-label">Model or engine</p>
            <div className="checks">
              {MOE_ORDER.map((v) => (
                <Check
                  key={v}
                  label={MOE_SHORT[v]}
                  n={view.moe.get(v) ?? 0}
                  checked={sel.values?.model_or_engine?.includes(v) ?? false}
                  onChange={() => setValues('model_or_engine', toggle(sel.values?.model_or_engine, v))}
                />
              ))}
            </div>
          </div>
        </Group>

        <Group title="English OpenList" hint="its valid list at revision 08ae92b8">
          <div className="checks checks-row">
            {(
              [
                ['true', 'On its list'],
                ['false', 'Not on it'],
              ] as const
            ).map(([v, l]) => (
              <Check
                key={v}
                label={l}
                eol={v === 'true'}
                n={view.eol.get(v) ?? 0}
                checked={sel.values?.eol?.includes(v) ?? false}
                onChange={() => setValues('eol', toggle(sel.values?.eol, v))}
              />
            ))}
          </div>
        </Group>
      </section>

      <section className="compose-result" id="compose-result" aria-label="Your list">
        <div className="result-head">
          <p className="result-count" aria-live="polite">
            <span className="hero">{full(view.rows)}</span>
            <span className="hero-unit">rows</span>
          </p>
          <p className="result-share">
            {view.rows === total ? 'All' : pct(view.rows, total)} of the universe&rsquo;s {full(total)}.{' '}
            {view.rows > 0 && (
              <>
                {full(view.eolRows)} of them are on the English OpenList&rsquo;s list.
              </>
            )}
          </p>
          {active && (
            <button type="button" className="reset" onClick={() => setSel({})}>
              Clear every criterion
            </button>
          )}
        </div>

        <ScaleSquares universe={total} selected={view.rows} eol={view.eolRows} />

        {view.rows === 0 ? (
          <p className="result-empty">
            No row meets every criterion. Each count beside a criterion says how many rows it would leave with the others
            kept, so a 0 there names the criterion to loosen.
          </p>
        ) : (
          <div className="result-charts">
            <ChartFrame
              title="Your list by length"
              table={view.lengthOwn.map((n, i) => ({ label: `${lengthLabel(i + 1)} characters`, value: n }))}
              total={view.rows}
            >
              <Columns
                label="Your list by length"
                columns={view.lengthOwn.map((n, i) => ({
                  key: String(i + 1),
                  label: lengthLabel(i + 1),
                  name: `${lengthLabel(i + 1)} characters`,
                  value: n,
                }))}
                total={view.rows}
                labelEvery={4}
                height={120}
              />
            </ChartFrame>
            <ChartFrame
              title="What your list rests on"
              table={PROVENANCE_ORDER.map((p) => ({ label: PROVENANCE[p].label, value: view.provOwn.get(p) ?? 0 }))}
              total={view.rows}
            >
              <BarList
                label="Your list by provenance class"
                bars={PROVENANCE_ORDER.map((p) => ({ key: p, label: PROVENANCE[p].label, value: view.provOwn.get(p) ?? 0 }))}
                total={view.rows}
              />
            </ChartFrame>
            <ChartFrame
              title="How many published lists list it"
              table={view.listsOwn.map((n, k) => ({ label: `${k} of 8`, value: n }))}
              total={view.rows}
            >
              <Columns
                label="Your list by the number of published lists listing each row"
                columns={view.listsOwn.map((n, k) => ({ key: String(k), label: String(k), name: `${k} of 8 lists`, value: n }))}
                total={view.rows}
                height={120}
              />
            </ChartFrame>
          </div>
        )}

        <section className="take" id="compose-take" aria-labelledby={`${id}-take`}>
          <h2 className="take-title" id={`${id}-take`}>
            Take your list with you
          </h2>
          <p className="take-count">
            Your list: <strong>{full(view.rows)}</strong> rows.
          </p>
          <ListDownload cube={cube} sel={sel} rows={view.rows} query={selectionQuery(sel)} citation={citation} file={file} />
          <div className="take-item">
            <a className="take-btn" href={`/compose/datasheet/${selectionQuery(sel)}`} target="_blank" rel="noopener">
              Open the datasheet
            </a>
            <p className="take-note">
              Its counts, distributions, and code, with your own title: save it as a PDF, Markdown, or CSV. It opens in a new tab.
            </p>
          </div>
          <div className="take-item">
            <CopyButton className="take-btn quiet" label="Copy the link" text={typeof window === 'undefined' ? '' : `${window.location.origin}/compose/${selectionQuery(sel)}`} />
            <p className="take-note">The link reopens this list, on any device.</p>
          </div>
        </section>

        <div className="code">
          <h2 className="code-title">Or run the code yourself</h2>
          <div className="code-bar">
            <div className="code-tabs" role="tablist" aria-label="Language">
              {(
                [
                  ['duckdb', 'DuckDB'],
                  ['polars', 'Polars'],
                  ['pandas', 'pandas'],
                ] as const
              ).map(([t, label]) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  id={`${id}-tab-${t}`}
                  aria-selected={tab === t}
                  aria-controls={`${id}-code`}
                  onClick={() => setTab(t)}
                >
                  {label}
                </button>
              ))}
            </div>
            <CopyButton className="copy" label="Copy the code" text={code[tab]} select={codeRef} />
          </div>
          <div className="code-body" role="tabpanel" id={`${id}-code`} aria-labelledby={`${id}-tab-${tab}`}>
            <pre ref={codeRef}>
              <code>{code[tab]}</code>
            </pre>
          </div>
          <p className="code-note">
            Paste it into DuckDB, a Python script, or a notebook, on a computer. It reads version 1.0 from the Hugging Face hub at
            its tag and returns {full(view.rows)} rows. The site&rsquo;s tests run all 3 forms on version 1.0&rsquo;s own file for a
            battery of lists and hold every count to this page&rsquo;s.
            {!DATASET_PUBLIC && ' The dataset stays private until the release, so the code needs access until then.'}
          </p>
        </div>
      </section>
    </div>
  );
}

function sentence(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function Group({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <fieldset className="cgroup">
      <legend>
        <span className="cgroup-title">{title}</span>
        <span className="cgroup-hint">{hint}</span>
      </legend>
      {children}
    </fieldset>
  );
}

function Check(props: { label: string; title?: string; n: number; checked: boolean; eol?: boolean; onChange: () => void }) {
  return (
    <label className={`ccheck${props.n === 0 && !props.checked ? ' is-none' : ''}`} title={props.title}>
      <input type="checkbox" checked={props.checked} onChange={props.onChange} />
      <span className="ccheck-label">
        {props.eol && <span className="eol-key" aria-hidden="true" />}
        {props.label}
      </span>
      <span className="ccheck-n">{full(props.n)}</span>
    </label>
  );
}

function ComposeSkeleton() {
  return (
    <div className="compose is-loading" aria-busy="true">
      <p className="visually-hidden">Loading the counts.</p>
      <div className="compose-criteria">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="sk sk-group" />
        ))}
      </div>
      <div className="compose-result">
        <div className="sk sk-hero" />
        <div className="sk sk-square" />
      </div>
    </div>
  );
}
