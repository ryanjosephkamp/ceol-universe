import { useEffect, useMemo, useState } from 'react';
import BarList from '../charts/BarList';
import MiniSquare from '../charts/MiniSquare';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import { full, pct } from '../charts/format';
import { Cube, FLAGS, PUBLISHED_SETS, type CubeFile, type Dim, type Flag, type Selection } from '../lib/cube';
import { readSelection, selectionQuery, writeSelection } from '../lib/selection-url';
import { CLASS_NAMES, INTAKE_KIND, INTAKE_LAYER, MODEL_OR_ENGINE, MOE_ORDER, MOE_SHORT, PROVENANCE, PROVENANCE_ORDER, SET_NAMES } from './labels';
import '../charts/charts.css';
import './profile.css';

const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const toggle = (xs: readonly string[] | undefined, v: string) =>
  (xs ?? []).includes(v) ? (xs ?? []).filter((x) => x !== v) : [...(xs ?? []), v];
const BOOL3: Record<string, string> = { true: 'Yes', false: 'No', null: 'Not measured' };

/** What a filter on a dimension's value reads as, in a chip. */
function valueLabel(dim: Dim, v: string): string {
  switch (dim) {
    case 'provenance_class':
      return PROVENANCE[v]?.label ?? v;
    case 'intake_layer':
      return sentence(INTAKE_LAYER[v] ?? v);
    case 'intake_kind':
      return sentence(INTAKE_KIND[v] ?? v).split(':')[0];
    case 'model_or_engine':
      return MOE_SHORT[v] ?? v;
    case 'eol':
      return v === 'true' ? 'On the English OpenList' : 'Not on the English OpenList';
    case 'token_count':
      return v === '1' ? '1 token' : `${v} tokens`;
    case 'gb_type':
      return `Google Books type: ${BOOL3[v]}`;
    case 'wordfreq_scored':
      return `wordfreq score: ${BOOL3[v]}`;
    case 'wikt_title_any':
      return `Wiktionary title: ${BOOL3[v]}`;
    default:
      return v;
  }
}

export default function Profile({ cubeUrl, composeHref }: { cubeUrl: string; composeHref: string }) {
  const [cube, setCube] = useState<Cube | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<Selection>({});
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSel(readSelection(window.location.search));
    setReady(true);
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<CubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then((f) => setCube(new Cube(f)), () => setFailed(true));
  }, [cubeUrl]);

  useEffect(() => {
    if (ready) writeSelection(sel);
  }, [sel, ready]);

  const v = useMemo(() => {
    if (!cube) return null;
    const eolVals = sel.values?.eol;
    return {
      rows: cube.rows(sel),
      eolRows: eolVals && eolVals.length && !eolVals.includes('true') ? 0 : cube.rows({ ...sel, values: { ...sel.values, eol: ['true'] } }),
      rowsNoBy: cube.rows({ ...sel, listedBy: [] }),
      rowsNoFlags: cube.rows({ ...sel, flags: {} }),
      prov: cube.by('provenance_class', sel),
      layer: cube.by('intake_layer', sel),
      kind: cube.by('intake_kind', sel),
      sets: cube.byList(sel),
      lists: cube.byListCount(sel),
      length: cube.byLength(sel),
      tokens: cube.by('token_count', sel),
      flags: cube.byFlag(sel),
      gb: cube.by('gb_type', sel),
      wf: cube.by('wordfreq_scored', sel),
      wk: cube.by('wikt_title_any', sel),
      moe: cube.by('model_or_engine', sel),
      eol: cube.by('eol', sel),
    };
  }, [cube, sel]);

  if (failed) return <p className="compose-error">The data for this page did not load. Reload the page to try again.</p>;
  if (!cube || !v) return <div className="profile is-loading" aria-busy="true"><div className="sk sk-hero" /></div>;

  const total = cube.total;
  const cap = cube.lengthCap;
  const L = (n: number) => (n >= cap ? `${cap}+` : String(n));
  const setValues = (dim: Dim, vals: string[]) => setSel((s) => ({ ...s, values: { ...s.values, [dim]: vals } }));
  const held = (dim: Dim) => new Set(sel.values?.[dim] ?? []);
  const sumOf = (m: Map<string, number>) => [...m.values()].reduce((a, b) => a + b, 0);

  // the chips: every filter held, each removable
  const chips: { key: string; label: string; drop: () => void }[] = [];
  for (const [dim, vals] of Object.entries(sel.values ?? {}) as [Dim, string[]][]) {
    for (const val of vals ?? []) {
      chips.push({ key: `${dim}:${val}`, label: valueLabel(dim, val), drop: () => setValues(dim, toggle(sel.values?.[dim], val)) });
    }
  }
  for (const s of sel.listedBy ?? []) {
    chips.push({ key: `by:${s}`, label: `Listed by ${SET_NAMES[s]}`, drop: () => setSel((x) => ({ ...x, listedBy: toggle(x.listedBy, s) })) });
  }
  if (sel.minLists) chips.push({ key: 'lists', label: `On ${sel.minLists} or more lists`, drop: () => setSel((x) => ({ ...x, minLists: 0 })) });
  for (const [f, r] of Object.entries(sel.flags ?? {})) {
    if (r && r !== 'any') {
      chips.push({
        key: `f:${f}`,
        label: `${r === 'with' ? '' : 'Not '}${CLASS_NAMES[f]}`.trim(),
        drop: () => setSel((x) => ({ ...x, flags: { ...x.flags, [f]: 'any' } })),
      });
    }
  }
  if (sel.minLength != null || sel.maxLength != null) {
    const lo = sel.minLength ?? 1;
    const hi = sel.maxLength ?? cap;
    chips.push({
      key: 'len',
      label: lo === hi ? `${L(lo)} characters` : `${L(lo)} to ${L(hi)} characters`,
      drop: () => setSel((x) => ({ ...x, minLength: null, maxLength: null })),
    });
  }

  // with the English OpenList as the only filter, every chart is of its rows
  const tone = chips.length === 1 && chips[0].key === 'eol:true' ? ('eol' as const) : undefined;

  const minL = sel.minLength ?? 1;
  const maxL = sel.maxLength ?? cap;
  const ranged = sel.minLength != null || sel.maxLength != null;

  return (
    <div className="profile">
      <div className="pf-bar" role="region" aria-label="Filters">
        <MiniSquare universe={total} selected={v.rows} eol={v.eolRows} />
        <p className="pf-count" aria-live="polite">
          <strong>{full(v.rows)}</strong> rows{chips.length ? `, ${pct(v.rows, total)} of the universe` : ', the whole universe'}
        </p>
        {chips.length > 0 ? (
          <ul className="pf-chips">
            {chips.map((c) => (
              <li key={c.key}>
                <button type="button" onClick={c.drop} aria-label={`Remove the filter ${c.label}`}>
                  {c.label}
                  <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
                    <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                </button>
              </li>
            ))}
            <li>
              <button type="button" className="pf-clear" onClick={() => setSel({})}>
                Clear all
              </button>
            </li>
          </ul>
        ) : (
          <p className="pf-hint">Click any bar to filter every chart by it. Click it again to let it go.</p>
        )}
        {chips.length > 0 && (
          <a className="pf-compose" href={`${composeHref}${selectionQuery(sel)}`}>
            Compose a list from this view
          </a>
        )}
      </div>

      <div className="pf-grid">
        <ChartFrame
          title="What each row rests on"
          table={PROVENANCE_ORDER.map((p) => ({ label: PROVENANCE[p].label, value: v.prov.get(p) ?? 0 }))}
          total={sumOf(v.prov)}
          note="A channel is a recorded way the string came in; containment means a published list or a corpus holds it."
        >
          <BarList
            tone={tone}
            label="Rows by provenance class"
            bars={PROVENANCE_ORDER.map((p) => ({ key: p, label: PROVENANCE[p].label, value: v.prov.get(p) ?? 0, title: PROVENANCE[p].what }))}
            total={sumOf(v.prov)}
            selected={held('provenance_class')}
            onToggle={(k) => setValues('provenance_class', toggle(sel.values?.provenance_class, k))}
          />
        </ChartFrame>

        <ChartFrame
          title="On the English OpenList"
          table={[
            { label: 'On its list', value: v.eol.get('true') ?? 0 },
            { label: 'Not on it', value: v.eol.get('false') ?? 0 },
          ]}
          total={sumOf(v.eol)}
          note="Its valid list at revision c1139698, the revision the universe pins."
        >
          <BarList
            tone={tone}
            label="Rows by the English OpenList's list"
            bars={[
              { key: 'true', label: 'On its list', value: v.eol.get('true') ?? 0, tone: 'eol' },
              { key: 'false', label: 'Not on it', value: v.eol.get('false') ?? 0 },
            ]}
            total={sumOf(v.eol)}
            selected={held('eol')}
            onToggle={(k) => setValues('eol', toggle(sel.values?.eol, k))}
          />
        </ChartFrame>

        <ChartFrame
          title="Listed by each published list"
          table={PUBLISHED_SETS.map((s) => ({ label: SET_NAMES[s], value: v.sets.get(s) ?? 0 }))}
          total={v.rowsNoBy}
          note="A row can be on several lists, so these overlap. Checking several keeps the rows every one of them lists."
        >
          <BarList
            tone={tone}
            label="Rows listed by each published list"
            bars={PUBLISHED_SETS.map((s) => ({ key: s, label: SET_NAMES[s], value: v.sets.get(s) ?? 0 }))}
            total={v.rowsNoBy}
            selected={new Set(sel.listedBy ?? [])}
            onToggle={(k) => setSel((x) => ({ ...x, listedBy: toggle(x.listedBy, k) }))}
          />
        </ChartFrame>

        <ChartFrame
          title="How many published lists list it"
          table={v.lists.map((n, k) => ({ label: `${k} of 8`, value: n }))}
          total={v.lists.reduce((a, b) => a + b, 0)}
          note="Click a column to keep the rows that at least that many lists list."
        >
          <Columns
            tone={tone}
            label="Rows by the number of published lists that list them"
            columns={v.lists.map((n, k) => ({ key: String(k), label: String(k), name: `${k} of 8 lists`, value: n }))}
            total={v.lists.reduce((a, b) => a + b, 0)}
            selected={(k) => !!sel.minLists && k >= sel.minLists}
            onPick={(k) => setSel((x) => ({ ...x, minLists: x.minLists === k || k === 0 ? 0 : k }))}
          />
        </ChartFrame>

        <ChartFrame
          title="Length, in characters"
          table={v.length.map((n, i) => ({ label: `${L(i + 1)} characters`, value: n }))}
          total={v.length.reduce((a, b) => a + b, 0)}
          note="Click a length to keep it; hold Shift to extend the range."
        >
          <Columns
            tone={tone}
            label="Rows by length"
            columns={v.length.map((n, i) => ({ key: String(i + 1), label: L(i + 1), name: `${L(i + 1)} characters`, value: n }))}
            total={v.length.reduce((a, b) => a + b, 0)}
            labelEvery={4}
            selected={(i) => ranged && i + 1 >= minL && i + 1 <= maxL}
            onPick={(i, extend) => {
              const n = i + 1;
              if (extend && ranged) {
                const lo = Math.min(minL, n);
                const hi = Math.max(maxL, n);
                setSel((x) => ({ ...x, minLength: lo === 1 ? null : lo, maxLength: hi >= cap ? null : hi }));
              } else if (minL === n && maxL === n) {
                setSel((x) => ({ ...x, minLength: null, maxLength: null }));
              } else {
                setSel((x) => ({ ...x, minLength: n === 1 ? null : n, maxLength: n >= cap ? null : n }));
              }
            }}
          />
        </ChartFrame>

        <ChartFrame
          title="Spelling classes"
          table={(['plain', ...FLAGS] as const).map((f) => ({ label: CLASS_NAMES[f], value: v.flags.get(f) ?? 0 }))}
          total={v.rowsNoFlags}
          note="A row can carry several classes. Plain a to z is a row with none."
        >
          <BarList
            tone={tone}
            label="Rows carrying each spelling class"
            bars={(['plain', ...FLAGS] as const).map((f) => ({ key: f, label: CLASS_NAMES[f], value: v.flags.get(f) ?? 0 }))}
            total={v.rowsNoFlags}
            selected={new Set(Object.entries(sel.flags ?? {}).filter(([, r]) => r === 'with').map(([f]) => f))}
            onToggle={(k) =>
              setSel((x) => ({
                ...x,
                flags: { ...x.flags, [k]: x.flags?.[k as Flag | 'plain'] === 'with' ? 'any' : 'with' },
              }))
            }
          />
        </ChartFrame>

        <ChartFrame
          title="Tokens"
          table={cube.values.token_count.map((t) => ({ label: valueLabel('token_count', t), value: v.tokens.get(t) ?? 0 }))}
          total={sumOf(v.tokens)}
        >
          <BarList
            tone={tone}
            label="Rows by tokens"
            bars={cube.values.token_count.map((t) => ({ key: t, label: valueLabel('token_count', t), value: v.tokens.get(t) ?? 0 }))}
            total={sumOf(v.tokens)}
            selected={held('token_count')}
            onToggle={(k) => setValues('token_count', toggle(sel.values?.token_count, k))}
          />
        </ChartFrame>

        <ChartFrame
          title="How each row came in"
          table={cube.values.intake_layer.map((l) => ({ label: sentence(INTAKE_LAYER[l] ?? l), value: v.layer.get(l) ?? 0 }))}
          total={sumOf(v.layer)}
        >
          <div className="pf-sub">
            <p className="pf-sub-title">Layer</p>
            <BarList
              tone={tone}
              label="Rows by intake layer"
              bars={cube.values.intake_layer.map((l) => ({ key: l, label: sentence(INTAKE_LAYER[l] ?? l), value: v.layer.get(l) ?? 0 }))}
              total={sumOf(v.layer)}
              selected={held('intake_layer')}
              onToggle={(k) => setValues('intake_layer', toggle(sel.values?.intake_layer, k))}
            />
          </div>
          <div className="pf-sub">
            <p className="pf-sub-title">Kind</p>
            <BarList
              tone={tone}
              label="Rows by intake kind"
              bars={cube.values.intake_kind.map((k) => ({ key: k, label: valueLabel('intake_kind', k), value: v.kind.get(k) ?? 0 }))}
              total={sumOf(v.kind)}
              selected={held('intake_kind')}
              onToggle={(k) => setValues('intake_kind', toggle(sel.values?.intake_kind, k))}
            />
          </div>
        </ChartFrame>

        <ChartFrame
          title="Model or engine"
          table={MOE_ORDER.map((m) => ({ label: m === 'none' ? 'No model or engine' : sentence(MODEL_OR_ENGINE[m]), value: v.moe.get(m) ?? 0 }))}
          total={sumOf(v.moe)}
          note="A record of how the English OpenList decided a row, never a verdict of this dataset's."
        >
          <BarList
            tone={tone}
            label="Rows by model or engine"
            bars={MOE_ORDER.map((m) => ({
              key: m,
              label: MOE_SHORT[m],
              value: v.moe.get(m) ?? 0,
              title: m === 'none' ? undefined : sentence(MODEL_OR_ENGINE[m]),
            }))}
            total={sumOf(v.moe)}
            selected={held('model_or_engine')}
            onToggle={(k) => setValues('model_or_engine', toggle(sel.values?.model_or_engine, k))}
          />
        </ChartFrame>

        <ChartFrame
          title="In the corpora"
          table={[
            ...['true', 'false', 'null'].map((x) => ({ label: `Google Books type: ${BOOL3[x]}`, value: v.gb.get(x) ?? 0 })),
            ...['true', 'false', 'null'].map((x) => ({ label: `wordfreq score: ${BOOL3[x]}`, value: v.wf.get(x) ?? 0 })),
            ...['true', 'false', 'null'].map((x) => ({ label: `Wiktionary title: ${BOOL3[x]}`, value: v.wk.get(x) ?? 0 })),
          ]}
          note="Multiword rows are not measured against the corpora."
        >
          {(
            [
              ['gb_type', 'A Google Books 1-gram type', v.gb],
              ['wordfreq_scored', 'Scored by wordfreq', v.wf],
              ['wikt_title_any', 'A Wiktionary page title', v.wk],
            ] as const
          ).map(([dim, title, m]) => (
            <div key={dim} className="pf-sub">
              <p className="pf-sub-title">{title}</p>
              <BarList
                tone={tone}
                label={title}
                bars={['true', 'false', 'null'].map((x) => ({ key: x, label: BOOL3[x], value: m.get(x) ?? 0 }))}
                total={sumOf(m)}
                selected={held(dim)}
                onToggle={(k) => setValues(dim, toggle(sel.values?.[dim], k))}
              />
            </div>
          ))}
        </ChartFrame>
      </div>
    </div>
  );
}
