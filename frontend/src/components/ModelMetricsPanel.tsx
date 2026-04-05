import { useEffect, useState } from 'react';
import type { Data } from 'plotly.js';
import PlotChart from './PlotChart';
import type { CrossRaceMetrics } from '../types';

export default function ModelMetricsPanel() {
  const [metrics, setMetrics] = useState<CrossRaceMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    function fetchMetrics() {
      fetch('/api/v1/model/metrics')
        .then(async r => {
          if (r.status === 503) return null;
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json() as Promise<CrossRaceMetrics>;
        })
        .then(data => {
          if (cancelled) return;
          if (data) {
            setMetrics(data);
          }
        })
        .catch(() => { if (!cancelled) setError('network'); });
    }

    fetchMetrics();
    // Poll every 10s until metrics arrive
    const interval = setInterval(() => {
      if (!metrics) fetchMetrics();
    }, 10000);

    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (error) return null;
  if (!metrics) return <p className="error-message">Model metrics loading... (background pipeline running)</p>;

  const fmt = (v: number) => `${(v * 100).toFixed(1)}%`;

  const chartData: Data[] = [
    {
      type: 'bar',
      x: ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC'],
      y: [metrics.accuracy, metrics.precision, metrics.recall, metrics.f1_score, metrics.roc_auc],
      hovertemplate: '<b>%{x}</b><br>Value: %{y:.1%}<extra></extra>',
    } as Data,
  ];

  return (
    <section className="panel model-metrics-panel">
      <h2>Model Performance Metrics</h2>
      <p className="race-counts">
        Trained on {metrics.training_race_count} races | Tested on {metrics.test_race_count} races
      </p>
      <div className="metrics-grid">
        <div><strong>Accuracy</strong> {fmt(metrics.accuracy)}</div>
        <div><strong>Precision</strong> {fmt(metrics.precision)}</div>
        <div><strong>Recall</strong> {fmt(metrics.recall)}</div>
        <div><strong>F1-Score</strong> {fmt(metrics.f1_score)}</div>
        <div><strong>ROC-AUC</strong> {fmt(metrics.roc_auc)}</div>
      </div>
      <PlotChart
        data={chartData}
        layout={{ title: { text: 'Model Performance Metrics (Test Set)' }, yaxis: { range: [0, 1] } }}
      />
    </section>
  );
}
