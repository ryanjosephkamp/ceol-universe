import type React from 'react';
import { full, pct } from './format';

interface Props {
  readonly universe: number;
  readonly selected: number;
  /** the part of the selection on the English OpenList's list */
  readonly eol: number;
  /** the counts the squares grow down from, once, when they first draw */
  readonly introFrom?: { readonly selected: number; readonly eol: number };
}

const SIDE = 240;

/**
 * The family's mark, live: the universe as an outlined square, the
 * selection as a square inside its corner, and the selection's English
 * OpenList rows as the red square inside that. Every square's area is to
 * scale. A selection too small to see is shown again, magnified, with the
 * factor stated.
 */
export default function ScaleSquares({ universe, selected, eol, introFrom }: Props) {
  const side = (n: number) => (universe ? SIDE * Math.sqrt(n / universe) : 0);
  const s = side(selected);
  const e = side(eol);
  // a square under 6px is hard to see: draw it again, magnified by a power of 10
  const zoom = s > 0 && s < 6 ? 10 ** Math.ceil(Math.log10(12 / s)) : 1;
  const zs = s * zoom;
  const ze = e * zoom;
  const P = 2;
  // the intro scales each square down from its starting size, about its
  // lower left corner; the drawn geometry is always the true one
  const from = (n: number, to: number) =>
    introFrom && zoom === 1 && to > 0 ? ({ '--from': side(n) / to } as React.CSSProperties) : undefined;
  const intro = introFrom && zoom === 1 ? ' sq-intro' : '';
  return (
    <figure className="squares">
      <svg
        viewBox={`0 0 ${SIDE + 2 * P} ${SIDE + 2 * P}`}
        role="img"
        aria-label={`The selection, ${full(selected)} rows, ${pct(selected, universe)} of the universe, drawn to scale by area inside the universe; ${full(eol)} of them are on the English OpenList's list.`}
      >
        <rect className="sq-u" x={P} y={P} width={SIDE} height={SIDE} />
        {s > 0 && (
          <rect className={'sq-s' + intro} style={from(introFrom?.selected ?? 0, s)} x={P} y={P + SIDE - s} width={s} height={s} />
        )}
        {e > 0 && (
          <rect className={'sq-e' + intro} style={from(introFrom?.eol ?? 0, e)} x={P} y={P + SIDE - e} width={e} height={e} />
        )}
        {/* the selection's edge, drawn over the red so its extent stays visible */}
        {s > 0 && (
          <rect className={'sq-frame' + intro} style={from(introFrom?.selected ?? 0, s)} x={P} y={P + SIDE - s} width={s} height={s} />
        )}
        {zoom > 1 && (
          <g transform={`translate(${P + SIDE - Math.max(zs, 28) - 14} ${P + 14})`}>
            <rect className="sq-zoom" x={-6} y={-6} width={Math.max(zs, 28) + 12} height={Math.max(zs, 28) + 12} />
            <rect className="sq-s" x={0} y={Math.max(zs, 28) - zs} width={zs} height={zs} />
            {ze > 0 && <rect className="sq-e" x={0} y={Math.max(zs, 28) - ze} width={ze} height={ze} />}
            <rect className="sq-frame" x={0} y={Math.max(zs, 28) - zs} width={zs} height={zs} />
          </g>
        )}
      </svg>
      <figcaption className="squares-key">
        <span>
          <span className="key-sq k-u" aria-hidden="true" /> The universe, {full(universe)}
        </span>
        <span>
          <span className="key-sq k-s" aria-hidden="true" /> Your list, {pct(selected, universe)}
        </span>
        <span>
          <span className="key-sq k-e" aria-hidden="true" /> On the English OpenList, {full(eol)}
        </span>
        {zoom > 1 && (
          <span className="squares-zoom">
            Top right: your list again, each side {zoom.toLocaleString('en-US')} times longer.
          </span>
        )}
      </figcaption>
    </figure>
  );
}
