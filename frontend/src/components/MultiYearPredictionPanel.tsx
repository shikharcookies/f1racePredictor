import { useEffect, useState } from 'react';
import type { Data } from 'plotly.js';
import PlotChart from './PlotChart';
import type { MultiYearPredictionResponse, PodiumPrediction } from '../types';

interface Props {
  year: number | null;
  gpSlug: string | null;
  displayName: string;
  isTestSet: boolean;
  hasActualResult: boolean;
}

function buildPodiumChart(predictions: PodiumPrediction[]): { data: Data[]; layout: object } {
  const sorted = [...predictions].sort((a, b) => b.podium_probability - a.podium_probability);

  const drivers = sorted.map(p => p.driver_code);
  const probs = sorted.map(p => p.podium_probability);
  const ciLows = sorted.map(p => p.ci_low);
  const ciHighs = sorted.map(p => p.ci_high);
  const colors = sorted.map(p => (p.above_threshold ? '#2ecc71' : '#888'));
  const errorMinus = sorted.map((_p, i) => Math.max(0, probs[i] - ciLows[i]));
  const errorPlus = sorted.map((_p, i) => Math.max(0, ciHighs[i] - probs[i]));

  const data: Data[] = [
    {
      type: 'bar',
      orientation: 'h',
      x: probs,
      y: drivers,
      marker: { color: colors },
      error_x: {
        type: 'data',
        symmetric: false,
        array: errorPlus,
        arrayminus: errorMinus,
      },
      customdata: sorted.map(p => [p.ci_low, p.ci_high]),
      hovertemplate:
        '<b>%{y}</b><br>Probability: %{x:.1%}<br>CI: [%{customdata[0]:.1%}, %{customdata[1]:.1%}]<extra></extra>',
    } as Data,
  ];

  const layout = {
    title: 'Podium Probability Prediction',
    xaxis: { title: 'Probability' },
    yaxis: { title: 'Driver' },
  };

  return { data, layout };
}

export default function MultiYearPredictionPanel({ year, gpSlug, displayName, hasActualResult }: Props) {
  const [response, setResponse] = useState<MultiYearPredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!year || !gpSlug) return;
    setLoading(true);
    setError(null);
    setResponse(null);

    fetch(`/api/v1/seasons/${year}/grand-prix/${gpSlug}/prediction`)
      .then(async r => {
        if (r.status === 503) {
          setError('503');
          return null;
        }
        if (r.status === 404) {
          setError('404');
          return null;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<MultiYearPredictionResponse>;
      })
      .then(data => { if (data) setResponse(data); })
      .catch(() => setError('network'))
      .finally(() => setLoading(false));
  }, [year, gpSlug]);

  if (!year || !gpSlug) return null;

  if (loading) return <p className="loading">Loading...</p>;

  if (error === '503') return <p className="error-message">Model training in progress, please wait...</p>;
  if (error === '404') return <p className="error-message">Race data not available</p>;
  if (error) return <p className="error-message">Failed to load prediction data</p>;
  if (!response) return null;

  const { data, layout } = buildPodiumChart(response.predictions);
  const badge = response.is_test_set
    ? <span className="badge badge-blue">Test Race</span>
    : <span className="badge badge-yellow">Training Data</span>;

  const isUpcoming = !response.has_actual_result && response.actual_top3.length === 0;

  return (
    <section className="panel multi-year-prediction-panel">
      <h2>Cross-Race Prediction — {displayName} {badge}</h2>
      <PlotChart data={data} layout={layout} />
      {response.is_test_set && hasActualResult && response.actual_top3.length > 0 && (
        <p className="actual-podium">
          Actual Podium: {response.actual_top3.join(', ')}
        </p>
      )}
      {isUpcoming && (
        <p className="upcoming-note">Upcoming race — no results yet. Prediction based on qualifying data.</p>
      )}
    </section>
  );
}
