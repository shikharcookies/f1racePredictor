# Implementation Plan: F1 Prediction Dashboard

## Overview

Wrap the existing Jupyter Notebook-based F1 analysis system into a FastAPI backend + React/Vite frontend. The backend pre-computes results from cached `.ff1pkl` data at startup and serves them via a JSON API. The frontend renders interactive Plotly charts and tables. All tasks build incrementally toward a fully wired, single-origin deployment.

## Tasks

- [x] 1. Set up project structure and shared data models
  - Create `app/` Python package with `__init__.py` files
  - Create `app/models.py` with all Pydantic models: `GPResult`, `PredictionResult`, `DriverPrediction`, `ModelMetrics`, `FeatureScore`, `PracticeResult`, `QualifyingResult`, `GridEntry`, `SimulationResult`, `SimFinisher`, `PitStrategy`, `DriverStatsResult`, `DriverStats`
  - Create `frontend/` Vite+React+TypeScript project scaffold (`npm create vite`)
  - Add `requirements.txt` with `fastapi`, `uvicorn`, `pandas`, `plotly`
  - _Requirements: 7.1, 7.2_

- [x] 2. Implement PipelineCache and PipelineRunner
  - [x] 2.1 Implement `app/pipeline/cache.py` — `PipelineCache` with `set`, `get`, `list_slugs` using a thread-safe `dict` + `threading.Lock`
    - _Requirements: 7.1, 7.4_

  - [x] 2.2 Implement `app/pipeline/runner.py` — `PipelineRunner.run_all()` and `run_for_gp(gp_slug)`
    - Discover GP directories under `cache/2022/` by listing subdirectories
    - For each GP, load session data via FastF1 in cache-only mode
    - Call existing analysis functions (import from existing notebook modules)
    - Populate and return `GPResult`; on exception, log error and set affected fields to `None`
    - _Requirements: 7.4, 7.5_

- [x] 3. Implement ChartBuilder
  - Implement `app/charts/builder.py` — `ChartBuilder` with all six methods converting DataFrames/model outputs to Plotly figure dicts
    - `lap_time_distribution(fp2_df)` — box/violin per driver, hover: lap number, lap time, compound
    - `stint_analysis(fp2_df)` — avg lap time per compound per driver
    - `qualifying_gap_to_pole(times_df)` — bar chart, gap = driver_time − min_time; pole gap = 0
    - `teammate_comparison(h2h_df)` — delta in milliseconds per constructor pair
    - `lap_by_lap_positions(sim_result)` — line chart, one trace per driver
    - `feature_importance(model, feature_names)` — horizontal bar, top 10, descending order
  - _Requirements: 3.1, 3.2, 3.3, 4.2, 4.3, 5.2, 9.1, 9.2, 9.3_

- [x] 4. Implement FastAPI routes and application entry point
  - [x] 4.1 Implement `app/api/routes.py` — all seven route handlers using `PipelineCache`
    - `GET /api/v1/grand-prix` → list of `{slug, display_name}`
    - `GET /api/v1/grand-prix/{gp_slug}` → full `GPResult` JSON
    - `GET /api/v1/grand-prix/{gp_slug}/prediction|practice|qualifying|simulation` → sub-result JSON
    - `GET /api/v1/drivers` → `DriverStatsResult` JSON
    - Return 404 `{"error": "NOT_FOUND", ...}` for unknown slugs
    - Return 500 `{"error": "PIPELINE_ERROR", ...}` for pipeline exceptions
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [x] 4.2 Implement `app/main.py` — FastAPI app with `lifespan` startup hook
    - Call `PipelineRunner.run_all()` on startup and populate `PipelineCache`
    - Mount React static build at `/` via `StaticFiles`
    - Register API router under `/api/v1`
    - _Requirements: 7.4, 8.2_

- [x] 5. Implement React frontend components
  - [x] 5.1 Implement `GrandPrixSelector.tsx`
    - Fetch `GET /api/v1/grand-prix` on mount; populate dropdown with display names
    - Default selection = last item in list (most recent GP); disable selector while loading
    - _Requirements: 1.1, 1.4_

  - [x] 5.2 Implement `PredictionPanel.tsx`
    - Display predicted winner, top-3 podium with win probabilities (2 decimal places)
    - Display model used and model comparison table (accuracy, precision, recall, F1)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.3 Implement `PracticePanel.tsx`
    - Render Plotly `lap_time_chart` and `stint_analysis_chart` from `PracticeResult`
    - Show "FP2 data unavailable" when section is `null`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 5.4 Implement `QualifyingPanel.tsx`
    - Render grid table (position, driver, best lap, Q1/Q2/Q3 times)
    - Render `gap_to_pole_chart` and `teammate_comparison_chart`
    - Show "Qualifying data unavailable" when section is `null`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.5 Implement `SimulationPanel.tsx`
    - Render `lap_by_lap_chart`, pit strategy table, final classification sorted by position
    - Show "Simulation data unavailable" when section is `null`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.6 Implement `DriverStatsPanel.tsx`
    - Render table with driver code, avg lap times per compound, DNF index, home race advantage
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.7 Implement `FeatureImportancePanel.tsx`
    - Render Plotly horizontal bar chart from `feature_importance` in `PredictionResult`
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 5.8 Implement `ErrorBanner.tsx`
    - Render structured error message from non-2xx API responses or network failures
    - _Requirements: 1.3, 2.5, 3.4, 4.4, 5.5_

  - [x] 5.9 Implement `App.tsx`
    - Layout with `GrandPrixSelector` at top; render all panels below based on selected GP data
    - Handle loading state (spinner) and error state (`ErrorBanner`)
    - Responsive layout for 768px–1920px screen widths
    - _Requirements: 1.2, 8.3_

- [x] 6. Wire frontend build into FastAPI static serving
  - Configure `app/main.py` `StaticFiles` mount to serve `frontend/dist` at `/`
  - Add a catch-all route returning `index.html` for client-side routing
  - Verify `uvicorn app.main:app` serves both API and frontend from the same origin
  - _Requirements: 8.1, 8.2_
