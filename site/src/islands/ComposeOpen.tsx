import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import layoutFile from '../../../pipeline/research/release/layout_open_v1.0.json';
import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import MiniSquare from '../charts/MiniSquare';
import { full, pct } from '../charts/format';
import type { FlagRule } from '../lib/cube';
import { bytesFor, type Layout } from '../lib/list-read';
import { OPEN_COMMIT, openCodeFor } from '../lib/open-codegen';
import {
  NAMED_LISTS,
  OPEN_FLAGS,
  OPEN_LISTS,
  OpenCube,
  SCOWL_SIZES,
  type OpenCubeFile,
  type OpenFlag,
  type OpenSelection,
} from '../lib/open-cube';
import { openSheetMarkdown, scowlPhrase, tokenLabel, type OpenSheetMeta } from '../lib/open-datasheet';
import { openRowTest } from '../lib/open-filter';
import { initialOpenSelection, normalizeOpenSelection, openLink, openSelectionQuery, openShareQuery, storeSelection } from '../lib/open-url';
import CopyButton from './CopyButton';
import ZipDownload from './ZipDownload';
import { CLASS_NAMES, SET_NAMES } from './labels';
import '../charts/charts.css';
import './compose.css';
import './compose-open.css';

const layout = layoutFile as Layout;

const PRESETS: readonly { label: string; what: string; sel: OpenSelection }[] = [
  { label: 'Everything', what: 'every row of the open subset', sel: {} },
  { label: 'Single words', what: '1 token', sel: { tokens: ['1'] } },
  { label: 'Plain a to z', what: 'single words of the letters a to z only', sel: { flags: { plain: 'with' } } },
  { label: 'On 2 or more lists', what: 'at least 2 of the 6 open lists list it', sel: { minLists: 2 } },
  { label: 'SCOWL up to size 50', what: 'SCOWL lists it at a size of 10 to 50', sel: { scowl: 50 } },
  { label: 'Multiword terms', what: '2 or more tokens', sel: { tokens: ['2', '3', '4+'] } },
];

const TRI: readonly [FlagRule, string][] = [
  ['any', 'Any'],
  ['with', 'With'],
  ['without', 'Without'],
];

type Tab = 'duckdb' | 'polars' | 'pandas';

/** This device's storage, which keeps the last list composed, or null where
 *  it is refused. */
function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function toggle(list: readonly string[] | undefined, v: string): string[] {
  const xs = list ?? [];
  return xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v];
}

const sameSelection = (a: OpenSelection, b: OpenSelection) => openSelectionQuery(a) === openSelectionQuery(b);

/** Hands the reader a file made in the page. */
function save(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** The list's text in bytes, 1 string and a line break per row, from the
 *  lengths in characters; the top bucket counts as its least length, and a
 *  character outside ASCII takes more than 1 byte, so it is an estimate. */
function textBytes(cube: OpenCube, sel: OpenSelection): number {
  return cube.byLength(sel, true).reduce((n, rows, i) => n + rows * (i + 2), 0);
}

export default function ComposeOpen({ cubeUrl, noticesUrl, citation }: { cubeUrl: string; noticesUrl: string; citation: string }) {
  const [cube, setCube] = useState<OpenCube | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<OpenSelection>({});
  const [tab, setTab] = useState<Tab>('duckdb');
  const codeRef = useRef<HTMLPreElement>(null);
  const [ready, setReady] = useState(false);
  // the "listed by at least" step a pointer or focus is on, for its readout
  const [lookK, setLookK] = useState<number | null>(null);
  const id = useId();

  useEffect(() => {
    // a shared address names its list; a bare one brings back the last list
    setSel(initialOpenSelection(window.location.search, storage()));
    setReady(true);
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<OpenCubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then(
        (f) => {
          const c = new OpenCube(f);
          setSel((s) => normalizeOpenSelection(s, c));
          setCube(c);
        },
        () => setFailed(true),
      );
  }, [cubeUrl]);

  useEffect(() => {
    if (!ready) return;
    // the address names every row explicitly, so a copy of it never reopens
    // the recipient's own stored list
    window.history.replaceState(null, '', openShareQuery(sel));
    storeSelection(storage(), sel);
  }, [sel, ready]);

  const view = useMemo(() => {
    if (!cube) return null;
    return {
      rows: cube.rows(sel),
      lists: cube.byListCount(sel),
      listsOwn: cube.byListCount(sel, true),
      sets: cube.byList(sel),
      setsOwn: cube.byList(sel, true),
      scowl: cube.byScowlSize(sel),
      flags: cube.byFlag(sel),
      tokens: cube.byTokens(sel),
      gb: cube.byGbType(sel),
      instances: cube.instances(sel),
      properNouns: cube.properNouns(sel),
      length: cube.byLength(sel),
      lengthOwn: cube.byLength(sel, true),
    };
  }, [cube, sel]);

  const code = useMemo(() => (cube && view ? openCodeFor(sel, view.rows, cube.lengthCap) : null), [cube, view, sel]);

  if (failed) return <p className="compose-error">The data for this page did not load. Reload the page to try again.</p>;
  if (!cube || !view || !code) return <ComposeSkeleton />;

  const set = (patch: Partial<OpenSelection>) => setSel((s) => ({ ...s, ...patch }));
  const setFlag = (f: OpenFlag | 'plain', rule: FlagRule) => setSel((s) => ({ ...s, flags: { ...s.flags, [f]: rule } }));
  const total = cube.total;
  const cap = cube.lengthCap;
  const lengthLabel = (n: number) => (n >= cap ? `${cap}+` : String(n));
  const minL = sel.minLength ?? 1;
  const maxL = sel.maxLength ?? cap;
  const minK = Math.max(1, sel.minLists ?? 1);
  const active = !sameSelection(sel, {});
  const query = openSelectionQuery(sel);
  const link = typeof window === 'undefined' ? '' : openLink(window.location.origin, sel);
  // the rows SCOWL lists up to each size, under the other criteria
  const scowlUpTo = (n: number) => SCOWL_SIZES.filter((s) => s <= n).reduce((a, s) => a + (view.scowl.get(s) ?? 0), 0);
  const sheetMeta = (): OpenSheetMeta => ({
    made: new Date(),
    link,
    citation,
    file: {
      path: layout.hub_path,
      bytes: layout.bytes,
      sha256: layout.sha256,
      license: layout.metadata?.['ceol.license'] ?? '',
      attribution: layout.metadata?.['ceol.attribution'] ?? '',
    },
  });
  const files = async (signal: AbortSignal) => {
    let notices: string;
    try {
      const res = await fetch(noticesUrl, { signal });
      if (!res.ok) throw new Error(String(res.status));
      notices = await res.text();
    } catch {
      throw new Error('The notices that travel with the list did not load.');
    }
    return [
      { name: 'DATASHEET.md', text: openSheetMarkdown(sel, cube, sheetMeta()) },
      { name: 'NOTICES.md', text: notices },
    ];
  };

  return (
    <div className="compose compose-open">
      <section className="compose-criteria" aria-label="Criteria">
        <div className="mobile-count">
          <MiniSquare universe={total} selected={view.rows} eol={0} />
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
                <button type="button" title={p.what} aria-pressed={sameSelection(sel, p.sel)} onClick={() => setSel(p.sel)}>
                  {p.label}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <Group title="Open lists" hint="the 6 lists the subset keeps">
          <div className="crit">
            <p className="crit-label">Listed by at least</p>
            <div
              className="lists-step"
              role="radiogroup"
              aria-label="Listed by at least this many open lists"
              onPointerLeave={() => setLookK(null)}
            >
              {view.lists.slice(1).map((n, i) => {
                const k = i + 1;
                const atLeast = view.lists.slice(k).reduce((a, b) => a + b, 0);
                const top = Math.max(1, ...view.lists.slice(1));
                const h = Math.max(n ? 6 : 0, (100 * n) / top);
                return (
                  <button
                    key={k}
                    type="button"
                    role="radio"
                    aria-checked={minK === k}
                    aria-label={`${k} or more: ${full(atLeast)} rows`}
                    className={k >= minK ? 'in' : undefined}
                    onClick={() => set({ minLists: k === 1 ? 0 : k })}
                    onPointerEnter={() => setLookK(k)}
                    onFocus={() => setLookK(k)}
                    onBlur={() => setLookK(null)}
                  >
                    <span className="ls-bar" style={{ height: `${h}%` }} aria-hidden="true" />
                    <span className="ls-k" aria-hidden="true">
                      {k}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="crit-note ls-readout" aria-hidden="true">
              {(() => {
                const k = lookK ?? minK;
                const atLeast = view.lists.slice(k).reduce((a, b) => a + b, 0);
                const exactly = view.lists[k] ?? 0;
                if (k === 1) return `Any number: every row is listed by at least 1. ${full(atLeast)} rows, ${full(exactly)} of them by exactly 1.`;
                return `${k} or more of 6: ${full(atLeast)} rows. Exactly ${k}: ${full(exactly)}.`;
              })()}
            </p>
            <p className="crit-note">The 3 hunspell dictionaries come from SCOWL, so the count counts lists, not independent sources.</p>
          </div>
          <div className="crit">
            <p className="crit-label">And by every list checked</p>
            <div className="checks">
              {NAMED_LISTS.map((s) => (
                <Check
                  key={s}
                  label={SET_NAMES[s]}
                  n={view.sets.get(s) ?? 0}
                  checked={sel.listedBy?.includes(s) ?? false}
                  onChange={() => set({ listedBy: toggle(sel.listedBy, s) })}
                />
              ))}
            </div>
            <p className="crit-note">
              Each count is the rows that list lists under your other criteria, with the lists checked here set aside, so the counts
              don&rsquo;t add up to what checking 2 of them would leave.
            </p>
          </div>
          <div className="crit">
            <label className="crit-label" htmlFor={`${id}-scowl`}>
              And by SCOWL
            </label>
            <div className="scowl-pick">
              <select
                id={`${id}-scowl`}
                value={sel.scowl ?? ''}
                onChange={(e) => set({ scowl: e.target.value ? Number(e.target.value) : null })}
              >
                <option value="">Not required</option>
                {SCOWL_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s === SCOWL_SIZES[0] ? `At size ${s}` : `At a size of 10 to ${s}`}: {full(scowlUpTo(s))}
                  </option>
                ))}
              </select>
              <span className="ccheck-n">{full(scowlUpTo(sel.scowl ?? SCOWL_SIZES[SCOWL_SIZES.length - 1]))}</span>
            </div>
            <p className="crit-note">
              Each size&rsquo;s count is the rows that choice leaves with your other criteria.{' '}
              {sel.scowl != null
                ? `Keeps the rows SCOWL lists ${scowlPhrase(sel.scowl)}.`
                : 'SCOWL holds its lists in sizes; a smaller size is a smaller list. The subset names sizes 10 to 70, and a row SCOWL lists only at 80 or 95 counts here as not listed.'}
            </p>
          </div>
        </Group>

        <Group title="Spelling" hint="classes, tokens, and length">
          <div className="flags" role="group" aria-label="Spelling classes">
            {(['plain', ...OPEN_FLAGS] as const).map((f) => {
              const rule = sel.flags?.[f] ?? 'any';
              return (
                <div key={f} className="flag">
                  <span className="flag-label">{CLASS_NAMES[f]}</span>
                  <span className="flag-n">{full(view.flags.get(f) ?? 0)}</span>
                  <span className="tri" role="radiogroup" aria-label={CLASS_NAMES[f]}>
                    {TRI.map(([r, label]) => (
                      <button key={r} type="button" role="radio" aria-checked={rule === r} onClick={() => setFlag(f, r)}>
                        {label}
                      </button>
                    ))}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="crit-note">
            Each count is the rows in that class under your other criteria, with every class rule set aside; for Plain a to z, the rows
            in no class. It is the same whether Any, With, or Without is chosen. A multiword row is in the class Multiword, so Plain a
            to z keeps single words only.
          </p>
          <div className="crit">
            <p className="crit-label">Tokens</p>
            <div className="checks checks-row">
              {cube.values.token_count.map((t) => (
                <Check
                  key={t}
                  label={tokenLabel(t)}
                  n={view.tokens.get(t) ?? 0}
                  checked={sel.tokens?.includes(t) ?? false}
                  onChange={() => set({ tokens: toggle(sel.tokens, t) })}
                />
              ))}
            </div>
            <p className="crit-note">
              Each count is the rows with that many tokens under your other criteria. 1 token is a single word; 2 or more make a
              multiword term.
            </p>
          </div>
          <div className="crit">
            <p className="crit-label">Length, in characters</p>
            <Columns
              label="Rows by length under the other criteria"
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

        <Group title="Google Books" hint="the 2020 English 1-grams">
          <div className="flags" role="group" aria-label="Google Books">
            <div className="flag">
              <span className="flag-label">A 1-gram type</span>
              <span className="flag-n">{full(view.gb.get('true') ?? 0)}</span>
              <span className="tri" role="radiogroup" aria-label="A Google Books 1-gram type">
                {TRI.map(([r, label]) => (
                  <button key={r} type="button" role="radio" aria-checked={(sel.gbType ?? 'any') === r} onClick={() => set({ gbType: r })}>
                    {label}
                  </button>
                ))}
              </span>
            </div>
          </div>
          <p className="crit-note">
            With keeps the {full(view.gb.get('true') ?? 0)} rows that are types; Without keeps the {full(view.gb.get('false') ?? 0)}{' '}
            single words that are not. Google Books was measured on single words only, so both leave out every multiword row (
            {full(view.gb.get('null') ?? 0)} under the other criteria).
          </p>
        </Group>

        <Group title="Properness signals" hint="recorded on multiword rows only">
          <div className="checks">
            <Check
              label="Leave out WordNet instances"
              n={view.instances}
              checked={sel.noInstances ?? false}
              onChange={() => set({ noInstances: !sel.noInstances })}
            />
            <Check
              label="Leave out Wiktionary proper nouns"
              n={view.properNouns}
              checked={sel.noProperNouns ?? false}
              onChange={() => set({ noProperNouns: !sel.noProperNouns })}
            />
          </div>
          <p className="crit-note">
            Each count is the rows the box leaves out under your other criteria: the multiword rows WordNet records as instances, and
            those under a Wiktionary proper-noun heading. Neither signal is recorded on a single word, so neither box leaves one out.
          </p>
        </Group>
      </section>

      <section className="compose-result" id="compose-result" aria-label="Your list">
        <div className="result-head">
          <p className="result-count" aria-live="polite">
            <span className="hero">{full(view.rows)}</span>
            <span className="hero-unit">rows</span>
          </p>
          <p className="result-share">
            {view.rows === total ? 'All' : pct(view.rows, total)} of the open subset&rsquo;s {full(total)}.
          </p>
          {active && (
            <button type="button" className="reset" onClick={() => setSel({})}>
              Clear every criterion
            </button>
          )}
        </div>

        {view.rows === 0 ? (
          <p className="result-empty">
            No row meets every criterion at once. Loosen or clear one of them, or clear every criterion to start again.
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
              title="Which open lists list it"
              note="A row that several lists list counts under each."
              table={OPEN_LISTS.map((s) => ({ label: SET_NAMES[s], value: view.setsOwn.get(s) ?? 0 }))}
              total={view.rows}
            >
              <BarList
                label="Your list by open list"
                bars={OPEN_LISTS.map((s) => ({ key: s, label: SET_NAMES[s], value: view.setsOwn.get(s) ?? 0 }))}
                total={view.rows}
              />
            </ChartFrame>
            <ChartFrame
              title="How many open lists list it"
              table={view.listsOwn.slice(1).map((n, i) => ({ label: `${i + 1} of 6`, value: n }))}
              total={view.rows}
            >
              <Columns
                label="Your list by the number of open lists listing each row"
                columns={view.listsOwn.slice(1).map((n, i) => ({ key: String(i + 1), label: String(i + 1), name: `${i + 1} of 6 lists`, value: n }))}
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
          <ZipDownload
            source={layout.url ?? null}
            closedNote="The download cannot reach the open subset's file."
            layout={layout}
            filter={{ of: 'open', sel, lengthCap: cap }}
            rows={view.rows}
            listKey={query}
            zipName={`ceol-universe-open-v1.0-${view.rows}-rows.zip`}
            textBytes={textBytes(cube, sel)}
            readBytes={bytesFor(layout, openRowTest(sel, cap).columns)}
            fileLabel="the open subset's file, from the Hugging Face hub,"
            files={files}
          />
          <div className="take-item">
            <button
              type="button"
              className="take-btn"
              onClick={() => save('DATASHEET.md', openSheetMarkdown(sel, cube, sheetMeta()), 'text/markdown;charset=utf-8')}
            >
              Download the datasheet
            </button>
            <p className="take-note">The datasheet alone, as Markdown: the definition, counts, distributions, code, source, and license. It is the one in the .zip.</p>
          </div>
          <div className="take-item">
            <CopyButton className="take-btn quiet" label="Copy the link" text={link} />
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
            Paste it into DuckDB, a Python script, or a notebook, on a computer. It reads the open subset from the Hugging Face hub at
            commit <code>{OPEN_COMMIT.slice(0, 7)}</code> and returns {full(view.rows)} rows. The site&rsquo;s tests run all 3 forms on
            the subset&rsquo;s own file for a battery of lists and hold every count to this page&rsquo;s.
          </p>
        </div>
      </section>
    </div>
  );
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

function Check(props: { label: string; n: number; checked: boolean; onChange: () => void }) {
  return (
    <label className={`ccheck${props.n === 0 && !props.checked ? ' is-none' : ''}`}>
      <input type="checkbox" checked={props.checked} onChange={props.onChange} />
      <span className="ccheck-label">{props.label}</span>
      <span className="ccheck-n">{full(props.n)}</span>
    </label>
  );
}

function ComposeSkeleton() {
  return (
    <div className="compose compose-open is-loading" aria-busy="true">
      <p className="visually-hidden">Loading the counts.</p>
      <div className="compose-criteria">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="sk sk-group" />
        ))}
      </div>
      <div className="compose-result">
        <div className="sk sk-hero" />
      </div>
    </div>
  );
}
