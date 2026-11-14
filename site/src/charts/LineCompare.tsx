import { useEffect, useId, useRef, useState } from 'react';
import { full, pct, ticks } from './format';

export interface Series {
  readonly key: string;
  readonly label: string;
  readonly tone: 'accent' | 'eol';
  /** a count per bin; the chart draws each bin's share of the series */
  readonly counts: readonly number[];
}

interface Props {
  readonly bins: readonly string[];
  readonly series: readonly Series[];
  readonly label: string;
  readonly xLabel: string;
  readonly labelEvery?: number;
}

const H = 240;
const M = { top: 12, right: 18, bottom: 34, left: 40 };

/**
 * The shares of 2 or more series across the same ordered bins, as 2px lines
 * on 1 axis, so their shapes compare whatever their sizes. A crosshair snaps
 * to the nearest bin and lists every series there. The drawing is as wide as
 * its box, so its labels keep their size on a phone.
 */
export default function LineCompare({ bins, series, label, xLabel, labelEvery = 1 }: Props) {
  const [at, setAt] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  // a narrow drawing labels half as many bins
  const every = W < 440 ? labelEvery * 2 : labelEvery;
  const id = useId();
  const totals = series.map((s) => s.counts.reduce((a, b) => a + b, 0));
  const shares = series.map((s, k) => s.counts.map((c) => (totals[k] ? (100 * c) / totals[k] : 0)));
  const maxShare = Math.max(1, ...shares.flat());
  const yt = ticks(maxShare, 4);
  const top = yt[yt.length - 1];
  const pw = W - M.left - M.right;
  const ph = H - M.top - M.bottom;
  const x = (i: number) => M.left + (bins.length === 1 ? pw / 2 : (pw * i) / (bins.length - 1));
  const y = (v: number) => M.top + ph - (ph * v) / top;

  const pick = (clientX: number) => {
    const svg = ref.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const px = ((clientX - r.left) / r.width) * W;
    const i = Math.round(((px - M.left) / pw) * (bins.length - 1));
    setAt(Math.max(0, Math.min(bins.length - 1, i)));
  };

  return (
    <div className="linec">
      <ul className="legend">
        {series.map((s, k) => (
          <li key={s.key}>
            <span className={`key-line t-${s.tone}`} aria-hidden="true" />
            {s.label} <span className="legend-n">{full(totals[k])} rows</span>
          </li>
        ))}
      </ul>
      <div className="linec-plot" ref={box}>
        <svg
          ref={ref}
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-labelledby={`${id}-d`}
          tabIndex={0}
          onPointerMove={(e) => pick(e.clientX)}
          onPointerLeave={() => setAt(null)}
          onFocus={() => setAt((a) => a ?? 0)}
          onBlur={() => setAt(null)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowRight') setAt((a) => Math.min(bins.length - 1, (a ?? -1) + 1));
            if (e.key === 'ArrowLeft') setAt((a) => Math.max(0, (a ?? 1) - 1));
          }}
        >
          <desc id={`${id}-d`}>{label}</desc>
          {yt.map((t) => (
            <g key={t}>
              <line className="grid" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
              <text className="axis" x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end">
                {t}%
              </text>
            </g>
          ))}
          {bins.map((b, i) =>
            i % every === 0 || i === bins.length - 1 ? (
              <text key={b} className="axis" x={x(i)} y={H - M.bottom + 18} textAnchor="middle">
                {b}
              </text>
            ) : null,
          )}
          <text className="axis axis-title" x={M.left + pw / 2} y={H - 2} textAnchor="middle">
            {xLabel}
          </text>
          {at !== null && <line className="crosshair" x1={x(at)} x2={x(at)} y1={M.top} y2={M.top + ph} />}
          {series.map((s, k) => (
            <path
              key={s.key}
              className={`line t-${s.tone}`}
              d={shares[k].map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')}
            />
          ))}
          {at !== null &&
            series.map((s, k) => (
              <circle key={s.key} className={`dot t-${s.tone}`} cx={x(at)} cy={y(shares[k][at])} r={4.5} />
            ))}
        </svg>
        {at !== null && (
          <div
            className="tip tip-multi"
            role="presentation"
            style={{ left: `clamp(5.5rem, ${(x(at) / W) * 100}%, calc(100% - 5.5rem))` }}
          >
            <span className="tip-head">
              {xLabel}: {bins[at]}
            </span>
            {series.map((s, k) => (
              <span key={s.key} className="tip-row">
                <span className={`key-line t-${s.tone}`} aria-hidden="true" />
                <strong>{pct(s.counts[at], totals[k])}</strong>
                <span>
                  {s.label}, {full(s.counts[at])}
                </span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
