import type { DriverStats } from '../types';

interface Props {
  drivers: DriverStats[];
}

function fmt(val: number | null): string {
  return val != null ? val.toFixed(3) : 'N/A';
}

export default function DriverStatsPanel({ drivers }: Props) {
  return (
    <div className="panel">
      <h2>Driver Statistics</h2>
      <table>
        <thead>
          <tr>
            <th>Driver</th>
            <th>Soft Avg</th>
            <th>Medium Avg</th>
            <th>Hard Avg</th>
            <th>Total Avg</th>
            <th>Total Laps</th>
            <th>DNF Index</th>
            <th>Home Advantage</th>
          </tr>
        </thead>
        <tbody>
          {drivers.map(d => (
            <tr key={d.driver_code}>
              <td>{d.driver_code}</td>
              <td>{fmt(d.soft_avg_time_rep)}</td>
              <td>{fmt(d.medium_avg_time_rep)}</td>
              <td>{fmt(d.hard_avg_time_rep)}</td>
              <td>{fmt(d.total_avg_time_rep)}</td>
              <td>{d.total_laps_rep}</td>
              <td>{d.dnf_index.toFixed(3)}</td>
              <td>{d.home_race_advantage ? '✓' : '✗'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
