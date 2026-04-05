import { useEffect, useState } from 'react';
import './App.css';
import GrandPrixSelector from './components/GrandPrixSelector';
import YearSelector from './components/YearSelector';
import PredictionPanel from './components/PredictionPanel';
import MultiYearPredictionPanel from './components/MultiYearPredictionPanel';
import FeatureImportancePanel from './components/FeatureImportancePanel';
import QualifyingPanel from './components/QualifyingPanel';
import PracticePanel from './components/PracticePanel';
import SimulationPanel from './components/SimulationPanel';
import ModelMetricsPanel from './components/ModelMetricsPanel';
import CircuitAccuracyPanel from './components/CircuitAccuracyPanel';
import DriverStatsPanel from './components/DriverStatsPanel';
import ErrorBanner from './components/ErrorBanner';
import type { GPResult, DriverStats, SeasonEvent } from './types';

export default function App() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedSeasonEvent, setSelectedSeasonEvent] = useState<SeasonEvent | null>(null);
  const [gpData, setGpData] = useState<GPResult | null>(null);
  const [sessionData, setSessionData] = useState<{ qualifying: GPResult['qualifying']; practice: GPResult['practice'] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<DriverStats[]>([]);

  useEffect(() => {
    fetch('/api/v1/drivers')
      .then(r => r.json())
      .then(data => setDrivers(data.drivers ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedSlug) return;
    setLoading(true);
    setError(null);
    setSessionData(null);

    // Try the per-GP endpoint (works for 2022 data)
    fetch(`/api/v1/grand-prix/${selectedSlug}`)
      .then(async r => { if (!r.ok) return null; return r.json(); })
      .then((data) => { if (data) setGpData(data as GPResult); else setGpData(null); })
      .catch(() => setGpData(null))
      .finally(() => setLoading(false));

    // Also fetch multi-year session data for qualifying/practice charts
    if (selectedYear != null) {
      fetch(`/api/v1/seasons/${selectedYear}/grand-prix/${selectedSlug}/session-data`)
        .then(async r => { if (!r.ok) return null; return r.json(); })
        .then((data) => { if (data) setSessionData(data); })
        .catch(() => {});
    }
  }, [selectedSlug, selectedYear]);

  function handleYearChange(year: number) {
    setSelectedYear(year);
    setSelectedSlug(null);
    setGpData(null);
    setSessionData(null);
    setSelectedSeasonEvent(null);
  }

  function handleGpSelect(slug: string, seasonEvent?: SeasonEvent) {
    setSelectedSlug(slug);
    setSelectedSeasonEvent(seasonEvent ?? null);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>F1 Prediction Dashboard</h1>
      </header>
      <main className="app-main">
        <div className="selectors-row">
          <YearSelector onSelect={handleYearChange} selectedYear={selectedYear} />
          {selectedYear != null && (
            <GrandPrixSelector onSelect={handleGpSelect} selectedSlug={selectedSlug} year={selectedYear} />
          )}
        </div>
        {loading && <p className="loading">Loading...</p>}
        {error && <ErrorBanner message={error} />}
        {selectedYear && selectedSlug && (
          <MultiYearPredictionPanel
            year={selectedYear}
            gpSlug={selectedSlug}
            displayName={selectedSeasonEvent?.display_name ?? selectedSlug}
            isTestSet={selectedSeasonEvent?.is_test_set ?? false}
            hasActualResult={selectedSeasonEvent?.has_actual_result ?? false}
          />
        )}
        {!loading && (gpData || sessionData) && (
          <>
            {!selectedYear && gpData && <PredictionPanel prediction={gpData.prediction} />}
            {!selectedYear && gpData && <FeatureImportancePanel featureImportance={gpData.prediction?.feature_importance ?? []} />}
            <QualifyingPanel qualifying={sessionData?.qualifying ?? gpData?.qualifying ?? null} />
            <PracticePanel practice={sessionData?.practice ?? gpData?.practice ?? null} />
            {gpData && <SimulationPanel simulation={gpData.simulation} />}
          </>
        )}
        <ModelMetricsPanel />
        <CircuitAccuracyPanel />
        {drivers.length > 0 && <DriverStatsPanel drivers={drivers} />}
      </main>
    </div>
  );
}
