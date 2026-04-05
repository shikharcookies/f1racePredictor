import Plot from './PlotChart';
import type { Data, Layout } from 'plotly.js';
import type { SimulationResult } from '../types';

interface Props {
  simulation: SimulationResult | null;
}

type PlotlyFig = { data?: Data[]; layout?: Partial<Layout> };

function SafePlot({ fig }: { fig: PlotlyFig }) {
  if (!fig || !fig.data || fig.data.length === 0) return null;
  return <Plot data={fig.data} layout={fig.layout ?? {}} style={{ width: '100%' }} />;
}

export default function SimulationPanel({ simulation }: Props) {
  if (!simulation) return <div className="panel">Simulation data unavailable</div>;

  const lapChart = simulation.lap_by_lap_chart as PlotlyFig;
  const sorted = [...simulation.final_classification].sort((a, b) => a.position - b.position);

  return (
    <div className="panel">
      <h2>Race Simulation</h2>
      <SafePlot fig={lapChart} />
      <h3>Final Classification</h3>
      <table>
        <thead>
          <tr><th>Position</th><th>Driver</th><th>Gap to Leader (s)</th></tr>
        </thead>
        <tbody>
          {sorted.map(f => (
            <tr key={f.position}>
              <td>{f.position}</td>
              <td>{f.driver_code}</td>
              <td>{f.gap_to_leader_seconds.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Pit Strategies</h3>
      <table>
        <thead>
          <tr><th>Driver</th><th>Pit Laps</th><th>Compound Sequence</th></tr>
        </thead>
        <tbody>
          {simulation.pit_strategies.map(s => (
            <tr key={s.driver_code}>
              <td>{s.driver_code}</td>
              <td>{s.pit_laps.join(', ')}</td>
              <td>{s.compound_sequence.join(' → ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
