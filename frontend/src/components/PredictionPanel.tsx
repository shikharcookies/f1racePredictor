import type { PredictionResult } from '../types';

interface Props {
  prediction: PredictionResult | null;
}

export default function PredictionPanel({ prediction }: Props) {
  if (!prediction) return <div className="panel">Prediction data unavailable</div>;

  return (
    <div className="panel">
      <h2>Race Prediction</h2>
      <p className="winner">Winner: <strong>{prediction.winner.driver_code}</strong></p>
      <p>Model: {prediction.model_used}</p>

      <h3>Podium</h3>
      <table>
        <thead>
          <tr><th>Position</th><th>Driver</th><th>Win Probability</th></tr>
        </thead>
        <tbody>
          {prediction.podium.slice(0, 3).map((d, i) => (
            <tr key={d.driver_code}>
              <td>{i + 1}</td>
              <td>{d.driver_code}</td>
              <td>{d.win_probability != null ? d.win_probability.toFixed(2) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {prediction.model_comparison.length > 0 && (
        <>
          <h3>Model Comparison</h3>
          <table>
            <thead>
              <tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th></tr>
            </thead>
            <tbody>
              {prediction.model_comparison.map(m => (
                <tr key={m.model_name}>
                  <td>{m.model_name}</td>
                  <td>{m.accuracy != null ? m.accuracy.toFixed(3) : '—'}</td>
                  <td>{m.precision != null ? m.precision.toFixed(3) : '—'}</td>
                  <td>{m.recall != null ? m.recall.toFixed(3) : '—'}</td>
                  <td>{m.f1_score != null ? m.f1_score.toFixed(3) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
