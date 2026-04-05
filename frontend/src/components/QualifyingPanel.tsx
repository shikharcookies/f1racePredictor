import Plot from './PlotChart';
import type { Data, Layout } from 'plotly.js';
import type { QualifyingResult } from '../types';

interface Props {
  qualifying: QualifyingResult | null;
}

type PlotlyFig = { data?: Data[]; layout?: Partial<Layout> };

function SafePlot({ fig }: { fig: PlotlyFig }) {
  if (!fig || !fig.data || fig.data.length === 0) return null;
  return <Plot data={fig.data} layout={fig.layout ?? {}} style={{ width: '100%' }} />;
}

function fmt(val: number | null | undefined): string {
  if (val == null || isNaN(val)) return '—';
  return val.toFixed(3);
}

export default function QualifyingPanel({ qualifying }: Props) {
  if (!qualifying) return <div className="panel">Qualifying data unavailable</div>;

  const gapChart = qualifying.gap_to_pole_chart as PlotlyFig;
  const teammateChart = qualifying.teammate_comparison_chart as PlotlyFig;

  return (
    <div className="panel">
      <h2>Qualifying</h2>
      <table>
        <thead>
          <tr><th>Position</th><th>Driver</th><th>Best Lap (s)</th><th>Q1</th><th>Q2</th><th>Q3</th></tr>
        </thead>
        <tbody>
          {qualifying.grid.map(entry => (
            <tr key={entry.position}>
              <td>{entry.position}</td>
              <td>{entry.driver_code}</td>
              <td>{fmt(entry.best_lap_seconds)}</td>
              <td>{fmt(entry.q1)}</td>
              <td>{fmt(entry.q2)}</td>
              <td>{fmt(entry.q3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <SafePlot fig={gapChart} />
      <SafePlot fig={teammateChart} />
    </div>
  );
}
