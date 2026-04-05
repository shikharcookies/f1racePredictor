import Plot from './PlotChart';
import type { Data, Layout } from 'plotly.js';
import type { FeatureScore } from '../types';

interface Props {
  featureImportance: FeatureScore[];
}

export default function FeatureImportancePanel({ featureImportance }: Props) {
  if (!featureImportance || featureImportance.length === 0) {
    return <div className="panel">Feature importance data unavailable</div>;
  }

  const top10 = [...featureImportance]
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 10);

  const data: Data[] = [{
    type: 'bar',
    orientation: 'h',
    x: top10.map(f => f.importance),
    y: top10.map(f => f.feature_name),
  }];

  const layout: Partial<Layout> = {
    title: { text: 'Feature Importance' },
    margin: { l: 150 },
    yaxis: { autorange: 'reversed' },
  };

  return (
    <div className="panel">
      <h2>Feature Importance</h2>
      <Plot data={data} layout={layout} style={{ width: '100%' }} />
    </div>
  );
}
