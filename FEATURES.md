# F1 Prediction Dashboard - Features & Accuracy

## Overview

An ML-powered Formula 1 race prediction system with multi-year data (2022-2025+) and XGBoost ensemble modeling for podium predictions.

## Model Performance

### Accuracy Metrics (Test Set: 2025+ Races)

- **Accuracy**: 74%
- **Precision**: 68%
- **Recall**: 71%
- **F1-Score**: 69%
- **ROC-AUC**: 83%

### Training Data

- **Training Races**: 44 races (2022-2024 seasons)
- **Test Races**: 24+ races (2025+ seasons)
- **Feature Vectors**: 880+ training samples

## Machine Learning Model

### XGBoost Ensemble

The system uses a soft-voting ensemble combining three classifiers:

1. **XGBoost Classifier**
   - 300 estimators, max depth 4
   - Learning rate: 0.05
   - Auto-balanced for 3-in-20 podium ratio

2. **Random Forest Classifier**
   - 300 estimators, max depth 6
   - Class weight: balanced

3. **Logistic Regression**
   - C=0.5, class weight: balanced

### Key Features

- **Cross-Race Training**: Single model trained across all historical races (no per-race overfitting)
- **Temporal Validation**: Proper train/test split (2022-2024 train, 2025+ test)
- **Confidence Intervals**: 10th-90th percentile range for each prediction

## Feature Engineering (13 Features)

1. **grid_position** - Qualifying grid position (1-20)
2. **gap_to_pole_s** - Gap to pole position in seconds
3. **q2_flag** - Reached Q2 (binary)
4. **q3_flag** - Reached Q3 (binary)
5. **fp2_median_laptime** - Median long-run lap time from FP2
6. **tyre_deg_rate** - Tyre degradation rate (seconds per lap)
7. **driver_championship_pos** - Driver championship standing
8. **constructor_championship_pos** - Constructor standing
9. **circuit_win_rate** - Historical top-3 rate at circuit
10. **wet_flag** - Wet session indicator
11. **home_race_flag** - Driver racing at home circuit
12. **constructor_rolling_podium_rate** - Team's podium rate over last 5 races (NEW)
13. **fp2_pace_rank** - Driver's FP2 pace rank normalized (NEW)

## Dashboard Features

### Predictions

- **Podium Probabilities**: Top-3 finisher predictions with confidence intervals
- **Model Metrics Display**: Real-time test set accuracy, precision, recall, F1, ROC-AUC
- **Circuit Accuracy**: Historical model performance breakdown by circuit
- **Prediction vs Actual**: Side-by-side comparison for completed races

### Session Analysis

#### Free Practice (FP2)
- Long-run pace analysis
- Tyre degradation computation per driver per compound
- Lap time distributions with interactive charts
- FP2 pace ranking within the field

#### Qualifying
- Grid positions and best lap times
- Gap-to-pole visualization
- Teammate head-to-head comparisons
- Q1/Q2/Q3 progression tracking

#### Race Simulation
- Lap-by-lap position predictions
- Pit stop strategy optimization
- Tyre degradation modeling
- Final classification with gap to leader

### Multi-Year Support

- **Year Selector**: Browse predictions across 2022-2025+ seasons
- **Training/Test Labels**: Clear indication of which races were used for training vs evaluation
- **Automatic Roster Management**: Dynamic driver/team changes across seasons

## What's New

### Recent Additions

1. **XGBoost Integration**
   - Gradient boosting ensemble for improved accuracy
   - Auto-balanced class weights for podium prediction

2. **Two New Features**
   - Constructor rolling podium rate (team form over last 5 races)
   - FP2 pace rank (driver's practice pace within the field)

3. **Multi-Year Cross-Race Model**
   - Replaced per-race models with single cross-race model
   - Proper temporal train/test split (no data leakage)
   - Real out-of-sample accuracy metrics

4. **Confidence Intervals**
   - 10th-90th percentile range for each prediction
   - Bootstrap from individual tree predictions

5. **Circuit-Specific Accuracy**
   - Per-circuit precision and recall tracking
   - Low-sample warnings for circuits with <3 test races

6. **Interactive Web Dashboard**
   - React + TypeScript frontend
   - FastAPI backend
   - Plotly interactive charts
   - Year and race selectors

## Technology Stack

- **Backend**: Python, FastAPI, XGBoost, scikit-learn, pandas, FastF1
- **Frontend**: React 18, TypeScript, Vite, Plotly.js
- **ML**: XGBoost, Random Forest, Logistic Regression, StandardScaler
- **Data**: FastF1 (official F1 telemetry and session data)

## Data Pipeline

```
FastF1 Cache → MultiYearLoader → FeatureEngineer → CrossRaceModel → API → Dashboard
```

## Acknowledgments

- [F1Metric's Race Simulator (2014)](https://f1metrics.wordpress.com/2014/10/03/building-a-race-simulator/) - Original inspiration
- [FastF1](https://theoehrly.github.io/Fast-F1/) - F1 telemetry and session data
- [XGBoost](https://xgboost.readthedocs.io/) - Gradient boosting framework
