import Plot from './PlotChart';
import type { Data, Layout } from 'plotly.js';
import type { PracticeResult } from '../types';

interface Props {
  practice: PracticeResult | null;
}

type PlotlyFig = { data: Data[]; layout: Partial<Layout> };

export default function PracticePanel({ practice }: Props) {
  if (!practice) return <div className="panel">FP2 data unavailable</div>;

  const lapChart = practice.lap_time_chart as PlotlyFig;
  const stintChart = practice.stint_analysis_chart as PlotlyFig;

  return (
    <div className="panel">
      <h2>Practice (FP2)</h2>
      <Plot data={lapChart.data} layout={lapChart.layout} style={{ width: '100%' }} />
      <Plot data={stintChart.data} layout={stintChart.layout} style={{ width: '100%' }} />
    </div>
  );
}
