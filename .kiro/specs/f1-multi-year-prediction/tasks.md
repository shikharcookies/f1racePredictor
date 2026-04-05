# Implementation Plan: F1 Multi-Year Prediction

## Overview

Upgrade the F1 Prediction Dashboard from a single-season per-race model to a multi-year cross-race podium prediction system. Backend-first: data loading → feature engineering → model → API → frontend.

## Tasks

- [x] 1. Add new Pydantic models to `app/models.py`
  - Add `FeatureVector`, `PodiumPredictionResult`, `CrossRaceMetrics`, `CircuitAccuracy`, `SeasonEvent`, `RaceSessionData`
  - Keep all existing models unchanged
  - _Requirements: 3.4, 4.1, 4.2, 5.1, 5.3, 6.1, 10.2_

- [x] 2. Implement `MultiYearLoader` in `app/pipeline/multi_year_loader.py`
  - `SEASONS = [2022, 2023, 2024, 2025]` plus current year if beyond 2025
  - `load_all_seasons()` → `list[RaceSessionData]` using `fastf1.get_event_schedule(year)` to discover completed races
  - Load Q, FP2, and R sessions per race; populate `actual_top3` from race results
  - On any exception: log warning, skip that race, continue
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.1, 8.3, 9.1_

- [x] 3. Implement `FeatureEngineer` in `app/pipeline/feature_engineer.py`
  - [x] 3.1 `build_dataset(races)` → `pd.DataFrame` with all 11 features per driver per race
    - `grid_position`, `gap_to_pole_s`, `q2_flag`, `q3_flag` from qualifying
    - `fp2_median_laptime`, `tyre_deg_rate` via linear regression on FP2 long-run stints
    - `driver_championship_pos` (default 20), `constructor_championship_pos` (default 10)
    - `circuit_win_rate` = top-3 count / starts at circuit in prior seasons (0.0 if no prior starts)
    - `wet_flag` = 1 if any INTERMEDIATE or WET tyre in qualifying
    - `home_race_flag` = 1 if circuit country matches driver nationality
    - `podium` label = 1 if driver in `actual_top3`, else 0; `None` for future races
    - _Requirements: 2.1, 2.5, 2.6, 2.7, 9.1, 9.2, 9.3, 9.4_
  - [x] 3.2 FP2 imputation: substitute race median for missing `fp2_median_laptime` and `tyre_deg_rate`
    - _Requirements: 2.2, 2.3_

- [x] 4. Implement `CrossRaceModel` in `app/pipeline/cross_race_model.py`
  - [x] 4.1 `train(dataset)`: temporal split (2022-2023 train, 2024+ test), fit `RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)`, compute and store `CrossRaceMetrics` and `list[CircuitAccuracy]`
    - Log warning if training set < 200 rows
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.8_
  - [x] 4.2 `predict(feature_vector)` → `PodiumPredictionResult` with `podium_probability`, `ci_low`/`ci_high` (10th/90th percentile of tree predictions), `above_threshold = probability > 0.5`
    - _Requirements: 3.6, 4.2, 4.3_
  - [x] 4.3 `get_metrics()`, `get_circuit_accuracy()`, `is_trained()` (False until train() completes)
    - _Requirements: 3.4, 3.5, 4.5_

- [x] 5. Add `MultiYearCache` to `app/pipeline/cache.py`
  - `set_seasons()`, `get_seasons()`, `get_season(year)` storing `dict[int, list[SeasonEvent]]`
  - _Requirements: 6.1, 10.1_

- [x] 6. Wire multi-year startup into `app/main.py`
  - After existing `PipelineRunner.run_all()`: run `MultiYearLoader` → `FeatureEngineer` → `CrossRaceModel.train()` → populate `MultiYearCache`
  - On any exception: log error, leave `is_trained()` False, continue serving existing endpoints
  - _Requirements: 1.3, 3.8_

- [x] 7. Add new API endpoints to `app/api/routes.py`
  - [x] 7.1 `GET /api/v1/seasons` — all seasons and GP events from `MultiYearCache`
  - [x] 7.2 `GET /api/v1/seasons/{year}/grand-prix` — GP list for year; 404 if unknown
  - [x] 7.3 `GET /api/v1/seasons/{year}/grand-prix/{gp_slug}/prediction` — predictions sorted descending by probability; 503 if not trained; 404 if unknown; 500 on exception
  - [x] 7.4 `GET /api/v1/model/metrics` — `CrossRaceMetrics`; 503 if not trained
  - [x] 7.5 `GET /api/v1/model/circuit-accuracy` — `list[CircuitAccuracy]`; 503 if not trained
  - _Requirements: 4.1, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 10.1–10.7_

- [x] 8. Extend `ChartBuilder` in `app/charts/builder.py`
  - `podium_probability_chart(predictions)` — horizontal bar with CI error bars, color by `above_threshold`
  - `circuit_accuracy_chart(circuit_accuracy)` — grouped bar (precision + recall), `barmode="group"`, low-sample annotations
  - `model_metrics_chart(metrics)` — bar chart for all 5 metrics
  - _Requirements: 11.1, 11.2, 11.3, 11.6_

- [x] 9. Add `YearSelector.tsx` (`frontend/src/components/YearSelector.tsx`)
  - Fetch seasons from `GET /api/v1/seasons`; default to current year or most recent with data
  - Props: `onSelect: (year: number) => void`, `selectedYear: number | null`
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 10. Add `MultiYearPredictionPanel.tsx`
  - Fetch from `GET /api/v1/seasons/{year}/grand-prix/{gp_slug}/prediction`
  - Render `podium_probability_chart` with CI bars
  - Show training/test set label; side-by-side predicted vs actual when `has_actual_result` is true
  - Handle 503 ("Model training in progress") and 404 ("Event not found")
  - _Requirements: 4.1–4.4, 6.4, 6.5, 8.2, 8.4, 11.1, 11.4, 11.5_

- [x] 11. Add `ModelMetricsPanel.tsx` and `CircuitAccuracyPanel.tsx`
  - `ModelMetricsPanel`: fetch `/api/v1/model/metrics`; display all 5 metrics + race counts
  - `CircuitAccuracyPanel`: fetch `/api/v1/model/circuit-accuracy`; render grouped bar chart; show low-sample warnings
  - _Requirements: 5.1–5.4, 11.2, 11.3, 11.6_

- [x] 12. Update `App.tsx` and `GrandPrixSelector.tsx`
  - Add `selectedYear` state; pass to `GrandPrixSelector` (filter by year) and new panels
  - Mount `YearSelector`, `MultiYearPredictionPanel`, `ModelMetricsPanel`, `CircuitAccuracyPanel`
  - _Requirements: 6.1, 6.2_
