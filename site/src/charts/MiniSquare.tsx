/** The to-scale squares at the size of a glyph, for a count's line: the
 *  universe outlined, the selection filled, its English OpenList part red. */
export default function MiniSquare({
  universe,
  selected,
  eol,
  size = 28,
}: {
  universe: number;
  selected: number;
  eol: number;
  size?: number;
}) {
  const S = 24;
  const side = (n: number) => (universe ? Math.max(n > 0 ? 1.2 : 0, S * Math.sqrt(n / universe)) : 0);
  const s = side(selected);
  const e = Math.min(s, side(eol));
  return (
    <svg className="mini-sq" viewBox="0 0 26 26" width={size} height={size} aria-hidden="true">
      <rect className="sq-u" x="1" y="1" width={S} height={S} />
      {s > 0 && <rect className="sq-s" x="1" y={1 + S - s} width={s} height={s} />}
      {e > 0 && <rect className="sq-e" x="1" y={1 + S - e} width={e} height={e} />}
    </svg>
  );
}
