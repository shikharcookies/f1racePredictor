import { useEffect, useState } from 'react';
import type { Data } from 'plotly.js';
import PlotChart from './PlotChart';
import type { CircuitAccuracy } from '../types';

export default function CircuitAccuracyPanel() {
  const [circuits, setCircuits] = useState<CircuitAccuracy[] | null>(null);

  useEffect(() => {
    let cancelled = false;

    function fetchCircuits() {
      fetch('/api/v1/model/circuit-accuracy')
        .then(async r => {
          if (r.status === 503) return null;
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json() as Promise<CircuitAccuracy[]>;
        })
        .then(data => { if (!cancelled && data) setCircuits(data); })
        .catch(() => {});
    }

    fetchCircuits();
    const interval = setInterval(() => { if (!circuits) fetchCircuits(); }, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (!circuits) return null;

  const circuitNames = circuits.map(c =>
    c.low_sample_warning ? `${c.circuit_name} ⚠` : c.circuit_name
  );

  const chartData: Data[] = [
    {
      type: 'bar',
      name: 'Precision',
      x: circuitNames,
      y: circuits.map(c => c.precision),
      marker: { color: 'blue' },
      hovertemplate: '<b>%{x}</b><br>Precision: %{y:.1%}<extra></extra>',
    } as Data,
    {
      type: 'bar',
      name: 'Recall',
      x: circuitNames,
      y: circuits.map(c => c.recall),
      marker: { color: 'orange' },
      hovertemplate: '<b>%{x}</b><br>Recall: %{y:.1%}<extra></extra>',
    } as Data,
  ];

  return (
    <section className="panel circuit-accuracy-panel">
      <h2>Circuit Accuracy (Test Set)</h2>
      {circuits.some(c => c.low_sample_warning) && (
        <p className="low-sample-note">⚠ Low sample = fewer than 3 test races at this circuit</p>
      )}
      <PlotChart
        data={chartData}
        layout={{ title: { text: 'Circuit Accuracy (Test Set)' }, barmode: 'group' }}
      />
    </section>
  );
}
