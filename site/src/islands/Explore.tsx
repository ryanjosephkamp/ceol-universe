import { useDeferredValue, useEffect, useId, useMemo, useState, type ReactNode } from 'react';
import { MODES, charLength, matcher, normalizeQuery, type Mode } from '../lib/lookup';
import { rowsOf, type Row, type SampleFile } from '../lib/sample';
import {
  CLASS_FLAGS,
  CLASS_NAMES,
  EOL_RECORD,
  INTAKE_KIND,
  INTAKE_LAYER,
  MODEL_OR_ENGINE,
  PLAIN,
  PROVENANCE,
  PROVENANCE_ORDER,
  SET_NAMES,
} from './labels';
import './explore.css';

/** Rows shown at a time; "Show more" adds as many again. */
const PAGE = 50;

type EolFilter = 'any' | 'in' | 'out';

interface Filters {
  readonly prov: readonly string[];
  readonly sets: readonly string[];
  readonly cls: readonly string[];
  readonly min: number | null;
  readonly max: number | null;
  readonly eol: EolFilter;
}

const NO_FILTERS: Filters = { prov: [], sets: [], cls: [], min: null, max: null, eol: 'any' };

const count = (n: number) => n.toLocaleString('en-US');
const list = (v: string | null) => (v ? v.split(';').filter(Boolean) : []);
const collator = new Intl.Collator('en', { sensitivity: 'variant' });

// ---------------------------------------------------------------------------
// The address: the search and its filters, so a view can be shared
// ---------------------------------------------------------------------------

function readUrl(): { q: string; mode: Mode; filters: Filters } {
  const p = new URLSearchParams(window.location.search);
  const mode = p.get('mode');
  const num = (k: string) => {
    const v = Number(p.get(k));
    return p.has(k) && Number.isFinite(v) && v > 0 ? Math.floor(v) : null;
  };
  const eol = p.get('eol');
  return {
    q: p.get('q') ?? '',
    mode: MODES.some(([m]) => m === mode) ? (mode as Mode) : 'prefix',
    filters: {
      prov: list(p.get('prov')).filter((x) => x in PROVENANCE),
      sets: list(p.get('sets')).filter((x) => x in SET_NAMES),
      cls: list(p.get('cls')).filter((x) => x in CLASS_NAMES),
      min: num('min'),
      max: num('max'),
      eol: eol === 'in' || eol === 'out' ? eol : 'any',
    },
  };
}

function writeUrl(q: string, mode: Mode, f: Filters): void {
  const p = new URLSearchParams();
  if (q) p.set('q', q);
  if (mode !== 'prefix') p.set('mode', mode);
  if (f.prov.length) p.set('prov', f.prov.join(';'));
  if (f.sets.length) p.set('sets', f.sets.join(';'));
  if (f.cls.length) p.set('cls', f.cls.join(';'));
  if (f.min !== null) p.set('min', String(f.min));
  if (f.max !== null) p.set('max', String(f.max));
  if (f.eol !== 'any') p.set('eol', f.eol);
  const search = p.toString();
  window.history.replaceState(null, '', search ? `?${search}` : window.location.pathname);
}

// ---------------------------------------------------------------------------
// The filters, each a test of a row; a facet's counts apply every other one
// ---------------------------------------------------------------------------

type Facet = 'text' | 'prov' | 'sets' | 'cls' | 'len' | 'eol';

interface Prepared {
  readonly row: Row;
  readonly sets: ReadonlySet<string>;
  readonly flags: ReadonlySet<string>;
  readonly length: number;
}

function tests(f: Filters, textTest: (s: string) => boolean): Record<Facet, (r: Prepared) => boolean> {
  return {
    text: (r) => textTest(r.row.word),
    prov: (r) => f.prov.length === 0 || f.prov.includes(r.row.provenance_class),
    sets: (r) => f.sets.every((s) => r.sets.has(s)),
    cls: (r) =>
      f.cls.every((c) => (c === PLAIN ? r.flags.size === 0 : r.flags.has(c))),
    len: (r) => (f.min === null || r.length >= f.min) && (f.max === null || r.length <= f.max),
    eol: (r) => f.eol === 'any' || (f.eol === 'in') === r.row.eol,
  };
}

const FACETS: readonly Facet[] = ['text', 'prov', 'sets', 'cls', 'len', 'eol'];

function passesExcept(r: Prepared, t: Record<Facet, (r: Prepared) => boolean>, skip: Facet | null): boolean {
  for (const k of FACETS) if (k !== skip && !t[k](r)) return false;
  return true;
}

const modePhrase: Record<Mode, string> = {
  prefix: 'starts with',
  contains: 'contains',
  suffix: 'ends with',
  pattern: 'matches the pattern',
  regex: 'matches the regex',
};

// ---------------------------------------------------------------------------

interface Props {
  readonly sampleUrl: string;
  readonly suggestions: readonly string[];
  readonly grammarHref: string;
}

export default function Explore({ sampleUrl, suggestions, grammarHref }: Props) {
  const [file, setFile] = useState<SampleFile | null>(null);
  const [failed, setFailed] = useState(false);
  const [raw, setRaw] = useState('');
  const [mode, setMode] = useState<Mode>('prefix');
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [shown, setShown] = useState(PAGE);
  const [open, setOpen] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const ids = useId();

  useEffect(() => {
    const u = readUrl();
    setRaw(u.q);
    setMode(u.mode);
    setFilters(u.filters);
    setReady(true);
    fetch(sampleUrl)
      .then((r) => (r.ok ? (r.json() as Promise<SampleFile>) : Promise.reject(new Error(String(r.status)))))
      .then(setFile, () => setFailed(true));
  }, [sampleUrl]);

  useEffect(() => {
    if (ready) writeUrl(raw, mode, filters);
  }, [raw, mode, filters, ready]);

  const deferredRaw = useDeferredValue(raw);
  const text = normalizeQuery(deferredRaw, mode);
  const m = useMemo(() => matcher(mode, text), [mode, text]);

  const prepared = useMemo<Prepared[]>(() => {
    if (!file) return [];
    return rowsOf(file)
      .sort((a, b) => collator.compare(a.word, b.word))
      .map((row) => ({
        row,
        sets: new Set(list(row.panel_sets)),
        flags: new Set(list(row.classes)),
        length: charLength(row.word),
      }));
  }, [file]);

  const maxLength = useMemo(() => prepared.reduce((n, r) => Math.max(n, r.length), 0), [prepared]);
  const textTest = 'error' in m ? () => false : m.test;
  const t = useMemo(() => tests(filters, textTest), [filters, textTest]);

  const matches = useMemo(() => prepared.filter((r) => passesExcept(r, t, null)), [prepared, t]);

  /** For a facet, the count of each value under every other filter. */
  const facetCounts = useMemo(() => {
    const out = {
      prov: new Map<string, number>(),
      sets: new Map<string, number>(),
      cls: new Map<string, number>(),
      eol: new Map<string, number>(),
    };
    for (const r of prepared) {
      if (passesExcept(r, t, 'prov')) out.prov.set(r.row.provenance_class, (out.prov.get(r.row.provenance_class) ?? 0) + 1);
      if (passesExcept(r, t, 'sets')) for (const s of r.sets) out.sets.set(s, (out.sets.get(s) ?? 0) + 1);
      if (passesExcept(r, t, 'cls')) {
        if (r.flags.size === 0) out.cls.set(PLAIN, (out.cls.get(PLAIN) ?? 0) + 1);
        for (const c of r.flags) out.cls.set(c, (out.cls.get(c) ?? 0) + 1);
      }
      if (passesExcept(r, t, 'eol')) {
        const k = r.row.eol ? 'in' : 'out';
        out.eol.set(k, (out.eol.get(k) ?? 0) + 1);
      }
    }
    return out;
  }, [prepared, t]);

  useEffect(() => {
    setShown(PAGE);
    setOpen(null);
  }, [text, mode, filters]);

  const activeFilters =
    filters.prov.length + filters.sets.length + filters.cls.length + (filters.min !== null ? 1 : 0) +
    (filters.max !== null ? 1 : 0) + (filters.eol !== 'any' ? 1 : 0);
  const idle = text === '' && activeFilters === 0;
  const total = prepared.length;

  const toggle = (key: 'prov' | 'sets' | 'cls', value: string) =>
    setFilters((f) => ({
      ...f,
      [key]: f[key].includes(value) ? f[key].filter((v) => v !== value) : [...f[key], value],
    }));

  const publishedSets = file?.published_sets ?? [];

  return (
    <div className="explore">
      <form className="search" role="search" onSubmit={(e) => e.preventDefault()}>
        <label htmlFor={`${ids}-q`} className="search-label">
          Search the sample
        </label>
        <div className="search-row">
          <input
            id={`${ids}-q`}
            type="search"
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            placeholder={mode === 'pattern' ? '_ is 1 character, * is any run' : 'Type a string'}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            aria-describedby={`${ids}-norm`}
          />
        </div>
        <fieldset className="modes">
          <legend className="visually-hidden">How to match</legend>
          {MODES.map(([value, label]) => (
            <label key={value} className={mode === value ? 'on' : undefined}>
              <input
                type="radio"
                name={`${ids}-mode`}
                value={value}
                checked={mode === value}
                onChange={() => setMode(value)}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <p id={`${ids}-norm`} className="norm-note">
          What you type is normalized as the <a href={grammarHref}>spelling grammar</a> normalizes a string:
          composed, the typographic apostrophe made plain, and lower-cased. A regex is matched as typed.
        </p>
      </form>

      <div className="explore-body">
        <div className="facets-wrap">
          <button
            type="button"
            className="facets-toggle"
            aria-expanded={filtersOpen}
            aria-controls={`${ids}-facets`}
            onClick={() => setFiltersOpen((o) => !o)}
          >
            Filters{activeFilters ? ` (${activeFilters} on)` : ''}
          </button>
          <div id={`${ids}-facets`} className={`facets${filtersOpen ? ' is-open' : ''}`}>
            <Group title="Provenance" hint="what the row rests on">
              {PROVENANCE_ORDER.map((p) => (
                <Check
                  key={p}
                  label={PROVENANCE[p].label}
                  title={PROVENANCE[p].what}
                  checked={filters.prov.includes(p)}
                  n={facetCounts.prov.get(p) ?? 0}
                  onChange={() => toggle('prov', p)}
                />
              ))}
            </Group>
            <Group title="Listed by" hint="every list checked lists the row">
              {publishedSets.map((s) => (
                <Check
                  key={s}
                  label={SET_NAMES[s] ?? s}
                  checked={filters.sets.includes(s)}
                  n={facetCounts.sets.get(s) ?? 0}
                  onChange={() => toggle('sets', s)}
                />
              ))}
            </Group>
            <Group title="Spelling class" hint="every class checked applies">
              {[PLAIN, ...CLASS_FLAGS].map((c) => (
                <Check
                  key={c}
                  label={CLASS_NAMES[c]}
                  checked={filters.cls.includes(c)}
                  n={facetCounts.cls.get(c) ?? 0}
                  onChange={() => toggle('cls', c)}
                />
              ))}
            </Group>
            <Group title="Length" hint="in characters">
              <div className="range">
                <label>
                  <span>From</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={maxLength || undefined}
                    value={filters.min ?? ''}
                    onChange={(e) =>
                      setFilters((f) => ({ ...f, min: e.target.value ? Math.max(1, Math.floor(Number(e.target.value))) : null }))
                    }
                  />
                </label>
                <label>
                  <span>to</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={maxLength || undefined}
                    value={filters.max ?? ''}
                    onChange={(e) =>
                      setFilters((f) => ({ ...f, max: e.target.value ? Math.max(1, Math.floor(Number(e.target.value))) : null }))
                    }
                  />
                </label>
              </div>
            </Group>
            <Group title="English OpenList" hint="its valid list at revision c1139698">
              {(
                [
                  ['any', 'Either'],
                  ['in', 'On its list'],
                  ['out', 'Not on it'],
                ] as const
              ).map(([value, label]) => (
                <label key={value} className="opt">
                  <input
                    type="radio"
                    name={`${ids}-eol`}
                    checked={filters.eol === value}
                    onChange={() => setFilters((f) => ({ ...f, eol: value }))}
                  />
                  <span className="opt-label">
                    {value === 'in' && <span className="eol-key" aria-hidden="true" />}
                    {label}
                  </span>
                  {value !== 'any' && <span className="opt-n">{count(facetCounts.eol.get(value) ?? 0)}</span>}
                </label>
              ))}
            </Group>
            {activeFilters > 0 && (
              <button type="button" className="clear" onClick={() => setFilters(NO_FILTERS)}>
                Clear the filters
              </button>
            )}
          </div>
        </div>

        <section className="results" aria-label="Results">
          <p className="count" aria-live="polite">
            {failed ? (
              'The sample did not load. Reload the page to try again.'
            ) : !file ? (
              'Loading the sample.'
            ) : 'error' in m ? (
              <>Not a regular expression: {m.error}</>
            ) : (
              idle ? (
                <>
                  <strong>{count(total)}</strong> sample rows
                </>
              ) : (
                <>
                  <strong>{count(matches.length)}</strong> of {count(total)} sample rows match
                </>
              )
            )}
          </p>

          {file && idle && (
            <div className="start-from">
              <p>
                Type a string, choose a filter, or start from one of these. They are from the project's vetted
                example list, the only strings this site shows unasked.
              </p>
              <ul>
                {suggestions.map((s) => (
                  <li key={s}>
                    <button type="button" className="cand" onClick={() => setRaw(s)}>
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {file && !idle && !('error' in m) && matches.length === 0 && (
            <div className="empty">
              <p>
                {text
                  ? <>Nothing in the sample {modePhrase[mode]} <span className="cand">“{text}”</span>{activeFilters ? ' with these filters' : ''}.</>
                  : 'No sample row passes all of these filters.'}
              </p>
              <p>
                The sample holds {count(total)} of the version's rows, so most strings are not in it. The full lookup
                ships with the release.
              </p>
            </div>
          )}

          {file && !idle && matches.length > 0 && (
            <>
              <ol className="rows">
                {matches.slice(0, shown).map((r) => (
                  <RowItem
                    key={r.row.id}
                    r={r}
                    sets={publishedSets}
                    open={open === r.row.id}
                    onToggle={() => setOpen((o) => (o === r.row.id ? null : r.row.id))}
                  />
                ))}
              </ol>
              {matches.length > shown && (
                <button type="button" className="more" onClick={() => setShown((n) => n + PAGE)}>
                  Show {count(Math.min(PAGE, matches.length - shown))} more of {count(matches.length - shown)}
                </button>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Group({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <fieldset className="group">
      <legend>
        {title} <span className="hint">{hint}</span>
      </legend>
      {children}
    </fieldset>
  );
}

function Check(props: { label: string; title?: string; checked: boolean; n: number; onChange: () => void }) {
  return (
    <label className={`opt${props.n === 0 && !props.checked ? ' none' : ''}`} title={props.title}>
      <input type="checkbox" checked={props.checked} onChange={props.onChange} />
      <span className="opt-label">{props.label}</span>
      <span className="opt-n">{count(props.n)}</span>
    </label>
  );
}

function PanelDots({ sets, listed }: { sets: readonly string[]; listed: ReadonlySet<string> }) {
  const n = sets.filter((s) => listed.has(s)).length;
  return (
    <span className="dots" title={sets.filter((s) => listed.has(s)).map((s) => SET_NAMES[s]).join(', ') || 'no published list'}>
      <span className="visually-hidden">listed by {n} of {sets.length} published lists</span>
      {sets.map((s) => (
        <span key={s} className={listed.has(s) ? 'dot on' : 'dot'} aria-hidden="true" />
      ))}
    </span>
  );
}

function RowItem({ r, sets, open, onToggle }: { r: Prepared; sets: readonly string[]; open: boolean; onToggle: () => void }) {
  const row = r.row;
  const detailId = `row-${row.id}`;
  return (
    <li className={open ? 'row is-open' : 'row'}>
      <button type="button" className="row-head" aria-expanded={open} aria-controls={detailId} onClick={onToggle}>
        <span className="row-word cand">{row.word}</span>
        <span className="row-meta">
          {row.eol && (
            <span className="eol-tag" title="on the English OpenList's valid list at revision c1139698">
              <span className="eol-key" aria-hidden="true" />
              EOL
            </span>
          )}
          <PanelDots sets={sets} listed={r.sets} />
          <span className="row-prov">{PROVENANCE[row.provenance_class]?.label ?? row.provenance_class}</span>
        </span>
      </button>
      {open && (
        <dl id={detailId} className="record">
          <Field name="Listed by">
            {r.sets.size
              ? sets.filter((s) => r.sets.has(s)).map((s) => SET_NAMES[s]).join(', ')
              : 'none of the published lists'}
          </Field>
          <Field name="Provenance">
            {PROVENANCE[row.provenance_class]?.label}: {PROVENANCE[row.provenance_class]?.what}
          </Field>
          <Field name="Came in by">
            {INTAKE_LAYER[row.intake_layer] ?? row.intake_layer}; {INTAKE_KIND[row.intake_kind] ?? row.intake_kind}
          </Field>
          <Field name="Channels">
            {list(row.intake_channels).length ? (
              <span className="chips">
                {list(row.intake_channels).map((c) => (
                  <code key={c}>{c}</code>
                ))}
              </span>
            ) : (
              'none recorded'
            )}
          </Field>
          <Field name="Entered">{row.intake_date ?? 'not recorded'}</Field>
          <Field name="Sources">{row.sources ? <code className="wrap">{row.sources}</code> : 'none published'}</Field>
          <Field name="English OpenList">
            {row.eol ? 'on its valid list at revision c1139698' : 'not on its valid list at revision c1139698'};{' '}
            {EOL_RECORD[row.eol_record] ?? row.eol_record}
          </Field>
          <Field name="Model or engine">{MODEL_OR_ENGINE[row.model_or_engine] ?? row.model_or_engine}</Field>
          <Field name="Google Books">
            {row.gb_type === null ? 'not measured for multiword rows' : row.gb_type ? 'a 1-gram type' : 'not a 1-gram type'}
          </Field>
          <Field name="wordfreq">
            {row.wordfreq_scored === null ? 'not measured for multiword rows' : row.wordfreq_scored ? 'scored' : 'not scored'}
          </Field>
          <Field name="Form">
            {r.length} characters, {row.token_count} {row.token_count === 1 ? 'token' : 'tokens'};{' '}
            {r.flags.size ? [...r.flags].map((c) => CLASS_NAMES[c] ?? c).join(', ') : 'plain a to z'}
          </Field>
          <Field name="Row id">
            <code>{row.id}</code>
          </Field>
        </dl>
      )}
    </li>
  );
}

function Field({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div className="field">
      <dt>{name}</dt>
      <dd>{children}</dd>
    </div>
  );
}
