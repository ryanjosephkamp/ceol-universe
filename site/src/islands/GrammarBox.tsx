import { useId, useMemo, useState } from 'react';
import { charKind, codePoint, trace, type CharKind } from '../lib/grammar';
import { CLASS_NAMES } from './labels';
import './grammar.css';

export interface Demo {
  readonly label: string;
  readonly input: string;
}

const KIND: Record<CharKind, string> = {
  letter: 'letter',
  accented: 'accented letter',
  ligature: 'ligature',
  hyphen: 'hyphen',
  apostrophe: 'apostrophe',
  space: 'space',
  canonicalized: 'rewritten',
  combining: 'joins the letter before',
  undeclared: 'not declared',
};

const NAMES: Record<string, string> = {
  ' ': 'space',
  '\u00a0': 'no-break space',
  '\t': 'tab',
  '\u2019': 'right quotation mark',
  '\u2018': 'left quotation mark',
  '\u02bc': 'modifier apostrophe',
};

/** A string with its invisible characters made visible. */
function Visible({ s }: { s: string }) {
  if (!s) return <span className="vis-empty">empty</span>;
  return (
    <>
      {Array.from(s).map((c, i) => {
        if (c === ' ') return <span key={i} className="vis-ws" title="U+0020 space">·</span>;
        if (c === '\u00a0') return <span key={i} className="vis-ws odd" title="U+00A0 no-break space">⍽</span>;
        if (c === '\t') return <span key={i} className="vis-ws odd" title="U+0009 tab">→</span>;
        if (/\p{M}/u.test(c)) return <span key={i} title={codePoint(c)}>{`\u25cc${c}`}</span>;
        return <span key={i}>{c}</span>;
      })}
    </>
  );
}

interface Props {
  readonly demos: readonly Demo[];
  readonly initial: string;
}

export default function GrammarBox({ demos, initial }: Props) {
  const [raw, setRaw] = useState(initial);
  const id = useId();
  const t = useMemo(() => trace(raw), [raw]);
  const chars = Array.from(raw);

  return (
    <div className="gbox">
      <label htmlFor={`${id}-in`} className="gbox-label">
        Type or paste a string
      </label>
      <input
        id={`${id}-in`}
        className="gbox-input cand"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
      />
      <div className="demos" role="group" aria-label="Try an altered example">
        <span className="demos-label">Try</span>
        {demos.map((d) => (
          <button key={d.label} type="button" onClick={() => setRaw(d.input)} aria-pressed={raw === d.input}>
            {d.label}
          </button>
        ))}
      </div>

      <section className="gbox-part" aria-label="The characters as typed">
        <h3>The characters as typed</h3>
        {chars.length === 0 ? (
          <p className="muted">Nothing typed yet.</p>
        ) : (
          <ol className="cells">
            {chars.map((c, i) => {
              const k = charKind(c);
              return (
                <li key={i} className={`cell k-${k}`}>
                  <span className="glyph">{/\p{M}/u.test(c) ? `\u25cc${c}` : c === ' ' ? '·' : c === '\u00a0' ? '⍽' : c === '\t' ? '→' : c}</span>
                  <span className="cp">{codePoint(c)}</span>
                  <span className="kind">{NAMES[c] ?? KIND[k]}</span>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section className="gbox-part" aria-label="The normalization">
        <h3>The normalization, step by step</h3>
        <ol className="steps">
          {t.steps.map((s) => {
            const changed = s.before !== s.after;
            return (
              <li key={s.name} className={changed ? 'step changed' : 'step'}>
                <span className="step-name">{s.name}</span>
                <span className="step-detail">{s.detail}</span>
                <span className="step-out">
                  {changed ? (
                    <>
                      <span className="cand mono"><Visible s={s.after} /></span>
                    </>
                  ) : (
                    <span className="muted">no change</span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className={`verdict ${t.key === null ? 'fails' : 'passes'}`} aria-live="polite">
        {raw === '' ? (
          <p>Type a string to see how the grammar reads it.</p>
        ) : t.key !== null ? (
          <>
            <p className="verdict-line">
              <svg className="mark-ok" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path d="M3 8.5l3.2 3.2L13 4.8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>{' '}
              Passes the grammar. Its key:
            </p>
            <p className="key cand"><Visible s={t.key} /></p>
            <p className="verdict-meta">
              {t.tokens} {t.tokens === 1 ? 'token' : 'tokens'};{' '}
              {t.classes.length ? (
                <>
                  {t.classes.length === 1 ? 'class' : 'classes'}{' '}
                  {t.classes.map((c) => (
                    <span key={c} className="class-chip">
                      {CLASS_NAMES[c] ?? c}
                    </span>
                  ))}
                </>
              ) : (
                'plain a to z'
              )}
            </p>
            <p className="verdict-note">
              Passing fixes how a candidate is written. It says nothing about whether the string is a word.
            </p>
          </>
        ) : (
          <>
            <p className="verdict-line">
              <svg className="mark-no" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>{' '}
              Fails the grammar: {t.fault}.
            </p>
            <p className="verdict-note">A string that fails is not a candidate in any version.</p>
          </>
        )}
      </section>
    </div>
  );
}
