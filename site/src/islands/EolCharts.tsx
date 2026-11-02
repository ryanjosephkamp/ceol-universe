import { useEffect, useMemo, useState } from 'react';
import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import LineCompare from '../charts/LineCompare';
import { full } from '../charts/format';
import { Cube, type CubeFile } from '../lib/cube';
import { MODEL_OR_ENGINE, MOE_ORDER, MOE_SHORT, PROVENANCE, PROVENANCE_ORDER } from './labels';
import '../charts/charts.css';

const EOL = { values: { eol: ['true'] } };

/** The English OpenList's rows against the universe's, from the cube. */
export default function EolCharts({ cubeUrl }: { cubeUrl: string }) {
  const [cube, setCube] = useState<Cube | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch(cubeUrl)
      .then((r) => (r.ok ? (r.json() as Promise<CubeFile>) : Promise.reject(new Error(String(r.status)))))
      .then((f) => setCube(new Cube(f)), () => setFailed(true));
  }, [cubeUrl]);

  const v = useMemo(() => {
    if (!cube) return null;
    return {
      rows: cube.rows(EOL),
      lenEol: cube.byLength(EOL, true),
      lenAll: cube.byLength({}),
      lists: cube.byListCount(EOL, true),
      prov: cube.by('provenance_class', EOL, true),
      moe: cube.by('model_or_engine', EOL, true),
    };
  }, [cube]);

  if (failed) return <p className="compose-error">The data for these charts did not load. Reload the page to try again.</p>;
  if (!cube || !v) return <div className="eol-charts is-loading" aria-busy="true" style={{ minHeight: '40rem' }} />;
  const cap = cube.lengthCap;
  const L = (n: number) => (n >= cap ? `${cap}+` : String(n));

  return (
    <div className="eol-charts">
      <div className="eol-pair">
        <ChartFrame
          title="Length: the English OpenList against the universe"
          note="Each line is its own rows' shares, so the shapes compare whatever the sizes."
          table={v.lenEol.map((n, i) => ({ label: `${L(i + 1)} characters, English OpenList`, value: n }))}
          total={v.rows}
        >
          <LineCompare
            label="The share of rows at each length, for the English OpenList and for the universe"
            xLabel="Length in characters"
            bins={v.lenEol.map((_, i) => L(i + 1))}
            labelEvery={4}
            series={[
              { key: 'eol', label: 'The English OpenList', tone: 'eol', counts: v.lenEol },
              { key: 'all', label: 'The universe', tone: 'accent', counts: v.lenAll },
            ]}
          />
        </ChartFrame>

        <ChartFrame
          title="What decided its rows"
          note={`Of its ${full(v.rows)} rows in version 1.0. A record of how the English OpenList decided, never a verdict of this dataset's.`}
          table={MOE_ORDER.map((m) => ({ label: m === 'none' ? 'No model or engine' : sentence(MODEL_OR_ENGINE[m]), value: v.moe.get(m) ?? 0 }))}
          total={v.rows}
        >
          <BarList
            label="The English OpenList's rows by model or engine"
            bars={MOE_ORDER.map((m) => ({
              key: m,
              label: MOE_SHORT[m],
              value: v.moe.get(m) ?? 0,
              title: m === 'none' ? undefined : sentence(MODEL_OR_ENGINE[m]),
              tone: 'eol' as const,
            }))}
            total={v.rows}
          />
        </ChartFrame>
      </div>

      <div className="eol-pair">
        <ChartFrame
          title="What its rows rest on"
          table={PROVENANCE_ORDER.map((p) => ({ label: PROVENANCE[p].label, value: v.prov.get(p) ?? 0 }))}
          total={v.rows}
        >
          <BarList
            label="The English OpenList's rows by provenance class"
            bars={PROVENANCE_ORDER.map((p) => ({ key: p, label: PROVENANCE[p].label, value: v.prov.get(p) ?? 0, tone: 'eol' }))}
            total={v.rows}
          />
        </ChartFrame>

        <ChartFrame
          title="How many published lists list its rows"
          table={v.lists.map((n, k) => ({ label: `${k} of 8`, value: n }))}
          total={v.rows}
        >
          <Columns
            label="The English OpenList's rows by the number of published lists that list them"
            columns={v.lists.map((n, k) => ({ key: String(k), label: String(k), name: `${k} of 8 lists`, value: n }))}
            total={v.rows}
            tone="eol"
            height={150}
          />
        </ChartFrame>
      </div>
    </div>
  );
}

function sentence(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
