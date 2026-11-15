import { useEffect, useMemo, useRef, useState } from 'react';
import BarList from '../charts/BarList';
import Columns from '../charts/Columns';
import { full, pct } from '../charts/format';
import { Cube, type CubeFile, type Selection } from '../lib/cube';
import { usDate } from '../lib/dates';
import {
  CANDIDATE_TEXT,
  DEFAULT_TITLE,
  LICENSE_TEXT,
  buildSheet,
  fileStem,
  sheetCsv,
  sheetMarkdown,
  type SheetMeta,
  type SheetTable,
} from '../lib/datasheet';
import { DATASET, VERSION } from '../lib/codegen';
import { normalizeSelection, readSelection, selectionQuery } from '../lib/selection-url';
import CopyButton from './CopyButton';
import '../charts/charts.css';
import './datasheet.css';

interface Props {
  readonly cubeUrl: string;
  readonly citation: string;
  readonly file: SheetMeta['file'];
}

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

export default function Datasheet({ cubeUrl, citation, file }: Props) {
  const [cube, setCube] = useState<Cube | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<Selection>({});
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [note, setNote] = useState('');
  const [made] = useState(() => new Date());
  const [origin, setOrigin] = useState('');

  useEffect(() => {
    setOrigin(window.location.origin);
    const asked = readSelection(window.location.search);
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<CubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then(
        (f) => {
          const c = new Cube(f);
          setSel(normalizeSelection(asked, c));
          setCube(c);
        },
        () => setFailed(true),
      );
  }, [cubeUrl]);

  const sheet = useMemo(() => (cube ? buildSheet(sel, cube) : null), [cube, sel]);
  const query = selectionQuery(sel);
  const meta: SheetMeta = { title, author, note, made, link: `${origin}/compose/${query}`, citation, file };
  const shownTitle = title.trim() || DEFAULT_TITLE;

  if (failed) return <p className="sheet-error">The data for this page did not load. Reload the page to try again.</p>;
  if (!cube || !sheet) return <div className="sheet-loading" aria-busy="true">Loading the counts.</div>;

  const stem = fileStem(shownTitle);
  return (
    <div className="datasheet">
      <aside className="sheet-tools" aria-label="Your datasheet">
        <p className="tools-back">
          <a href={`/compose/${query}`}>Back to the composer</a>
        </p>
        <div className="tools-fields">
          <label>
            <span>Title</span>
            <input type="text" value={title} placeholder={DEFAULT_TITLE} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            <span>Author or team</span>
            <input type="text" value={author} placeholder="Optional" onChange={(e) => setAuthor(e.target.value)} />
          </label>
          <label className="tools-note">
            <span>Note</span>
            <textarea value={note} rows={3} placeholder="Optional: what the list is for" onChange={(e) => setNote(e.target.value)} />
          </label>
        </div>
        <p className="tools-private">What you type here stays on this page; nothing is sent anywhere.</p>
        <div className="tools-actions">
          <button type="button" className="tool-btn primary" onClick={() => window.print()}>
            Save as PDF
          </button>
          <button type="button" className="tool-btn" onClick={() => save(`${stem}.md`, sheetMarkdown(sheet, meta), 'text/markdown;charset=utf-8')}>
            Download Markdown
          </button>
          <button type="button" className="tool-btn" onClick={() => save(`${stem}.csv`, sheetCsv(sheet), 'text/csv;charset=utf-8')}>
            Download CSV
          </button>
        </div>
        <p className="tools-hint">
          Save as PDF opens your browser&rsquo;s print dialog: choose Save as PDF there. On a phone, Print is under Share.
          The CSV holds every table, the count of each length included.
        </p>
      </aside>

      <article className="sheet" aria-label="The datasheet">
        <header className="sheet-head">
          <p className="sheet-eyebrow">Datasheet · The CEOL Universe, version {VERSION.slice(1)}</p>
          <h1>{shownTitle}</h1>
          <p className="sheet-byline">
            {author.trim() ? `By ${author.trim()} · ` : ''}Made {usDate(made)}
          </p>
          {note.trim() && <p className="sheet-note">{note.trim()}</p>}
        </header>

        <section className="sheet-count" aria-label="The list">
          <p className="sheet-hero">
            <span className="hero-n">{full(sheet.rows)}</span> <span className="hero-unit">rows</span>
          </p>
          <p>
            {sheet.rows === sheet.universe ? 'All' : pct(sheet.rows, sheet.universe)} of the universe&rsquo;s {full(sheet.universe)}.{' '}
            {full(sheet.eolRows)} of them are on the English OpenList&rsquo;s valid list.
          </p>
        </section>

        <section className="sheet-section" aria-labelledby="def">
          <h2 id="def">Its definition</h2>
          <ul className="sheet-def">
            {sheet.definition.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>

        {sheet.length && (
          <section className="sheet-section" aria-labelledby="len">
            <h2 id="len">Length, in characters</h2>
            <dl className="sheet-stats">
              <div>
                <dt>Median</dt>
                <dd>{sheet.length.median}</dd>
              </div>
              <div>
                <dt>Middle half</dt>
                <dd>
                  {sheet.length.lower} to {sheet.length.upper}
                </dd>
              </div>
              <div>
                <dt>Shortest</dt>
                <dd>{sheet.length.shortest}</dd>
              </div>
              <div>
                <dt>Longest</dt>
                <dd>{sheet.length.longest}</dd>
              </div>
            </dl>
          </section>
        )}

        {sheet.rows > 0 && (
          <section className="sheet-section" aria-labelledby="dist">
            <h2 id="dist">Distributions</h2>
            <div className="sheet-figures">
              {sheet.tables.map((t) => (
                <SheetFigure key={t.id} table={t} />
              ))}
            </div>
          </section>
        )}

        <section className="sheet-section" aria-labelledby="code">
          <h2 id="code">Reproduce it</h2>
          <p>
            Each form below reads version {VERSION.slice(1)} from the Hugging Face hub at its tag and returns {full(sheet.rows)} rows.
            Run it on a computer: in DuckDB, a Python script, or a notebook.
          </p>
          <CodeBlock title="DuckDB" text={sheet.code.duckdb} />
          <CodeBlock title="Polars" text={sheet.code.polars} />
          <CodeBlock title="pandas" text={sheet.code.pandas} />
          <p className="sheet-link">
            Reopen it on the site: <a href={`/compose/${query}`}>{meta.link}</a>
          </p>
        </section>

        <section className="sheet-section" aria-labelledby="from">
          <h2 id="from">Where it comes from</h2>
          <ul className="sheet-from">
            <li>
              The dataset: <code>{DATASET}</code> on the Hugging Face hub, at the tag <code>{VERSION}</code>.
            </li>
            <li>
              The file the code reads: <code>{file.path}</code>, SHA-256 <code className="sha">{file.sha256}</code>.
            </li>
            <li>The counts: the cube of version {VERSION.slice(1)}, which counts every row of the universe, not a sample.</li>
          </ul>
        </section>

        <section className="sheet-section" aria-labelledby="cite">
          <h2 id="cite">How to cite it</h2>
          <p>{citation}</p>
          <h2 id="license">License</h2>
          <p>{LICENSE_TEXT}</p>
          <p className="sheet-candidate">{CANDIDATE_TEXT}</p>
        </section>
      </article>
    </div>
  );
}

function SheetFigure({ table }: { table: SheetTable }) {
  return (
    <figure className={`sheet-figure${table.kind === 'columns' ? ' is-wide' : ''}`}>
      <figcaption>{table.title}</figcaption>
      {table.note && <p className="sheet-fig-note">{table.note}</p>}
      {table.kind === 'columns' ? (
        <Columns
          label={table.title}
          columns={table.rows.map((r, i) => ({ key: String(i), label: r.label.replace(/ or more$/, '+'), name: `${r.label} characters`, value: r.value }))}
          total={table.total}
          labelEvery={4}
          height={120}
        />
      ) : (
        <BarList
          label={table.title}
          bars={table.rows.map((r, i) => ({ key: String(i), label: r.label, value: r.value, tone: table.id === 'eol' && i === 0 ? 'eol' : undefined }))}
          total={table.total}
        />
      )}
    </figure>
  );
}

function CodeBlock({ title, text }: { title: string; text: string }) {
  const pre = useRef<HTMLPreElement>(null);
  return (
    <div className="sheet-code">
      <div className="sheet-code-head">
        <h3>{title}</h3>
        <CopyButton text={text} label="Copy" className="tool-btn small" select={pre} />
      </div>
      <pre ref={pre}>
        <code>{text}</code>
      </pre>
    </div>
  );
}
