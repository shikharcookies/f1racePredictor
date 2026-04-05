# Formula One Race Prediction Dashboard

A comprehensive machine learning-powered web application for Formula 1 race predictions, analysis, and simulation. Built with multi-year historical data (2022-2025+) and powered by an XGBoost ensemble model for accurate podium predictions.

## Demo

https://github.com/user-attachments/assets/demo.mp4

> Watch the dashboard in action: multi-year predictions, confidence intervals, circuit accuracy, and interactive session analysis.

## Overview

This project transforms F1 race weekend data into actionable insights through advanced machine learning and interactive visualizations. Originally inspired by [F1Metric's Race Simulator (2014)](https://f1metrics.wordpress.com/2014/10/03/building-a-race-simulator/), it has evolved into a modern, production-ready web dashboard featuring:

- **Multi-year cross-race ML model** trained on 2022-2024 data with proper temporal validation
- **XGBoost + Random Forest + Logistic Regression ensemble** for robust podium predictions
- **Real accuracy metrics** computed on held-out test data (2024+ races)
- **Interactive web dashboard** with React frontend and FastAPI backend
- **Comprehensive race analysis** including practice, qualifying, and race simulation

## Key Features

### 🎯 Machine Learning Predictions

- **Podium Prediction Model**: XGBoost-based ensemble predicting top-3 finishers with confidence intervals
- **Cross-Race Training**: Single model trained across all historical races (not per-race overfitting)
- **13 Engineered Features**: Including grid position, FP2 pace, tyre degradation, championship standings, circuit history, weather conditions, and more
- **Temporal Validation**: 2022-2024 training set, 2025+ test set for genuine out-of-sample accuracy
- **Model Performance**:
  - Test Set Accuracy: ~74%
  - ROC-AUC: ~0.83
  - Precision/Recall: ~0.68/0.71
  - Per-circuit accuracy tracking

### 📊 Interactive Dashboard

- **Year Selector**: Browse predictions across multiple F1 seasons (2022-2025+)
- **Race Selection**: Choose any Grand Prix from the available seasons
- **Prediction Panel**: View podium probabilities with confidence intervals (10th-90th percentile)
- **Model Metrics**: Real-time display of test set accuracy, precision, recall, F1-score, and ROC-AUC
- **Circuit Accuracy**: Historical model performance breakdown by circuit
- **Training/Test Labels**: Clear indication of which races were used for training vs. evaluation

### 🏎️ Session Analysis

#### Free Practice Analysis
- Long-run pace analysis from FP2 sessions
- Tyre degradation rate computation per driver per compound
- Lap time distributions with interactive charts
- Stint-level performance breakdown
- FP2 pace ranking within the field

#### Qualifying Analysis
- Grid position and best lap times
- Gap-to-pole visualization for all drivers
- Teammate head-to-head comparisons
- Q1/Q2/Q3 progression tracking

#### Race Simulation
- Lap-by-lap position predictions
- Pit stop strategy optimization (2-stop SOFT → MEDIUM → HARD)
- Tyre degradation modeling
- Final classification with gap to leader
- Fuel effect and pit stop time loss calculations

### 🔬 Advanced Features

- **Feature Importance**: Top 10 features driving predictions with visual charts
- **Constructor Rolling Podium Rate**: Team form over last 5 races
- **Circuit Win Rate**: Driver historical performance at each circuit
- **Weather Detection**: Automatic wet/dry session classification
- **Home Race Advantage**: Nationality-based home circuit detection
- **Championship Context**: Driver and constructor standings at race time
- **Automatic Roster Management**: Dynamic driver/team changes across seasons

## Architecture

### Backend (Python)
- **FastAPI**: High-performance async web framework
- **FastF1**: Official F1 telemetry and session data
- **XGBoost**: Gradient boosting for podium classification
- **scikit-learn**: Random Forest, Logistic Regression, preprocessing
- **pandas/numpy**: Data manipulation and feature engineering
- **Plotly**: Interactive chart generation

### Frontend (React + TypeScript)
- **React 18**: Modern component-based UI
- **Vite**: Fast build tooling
- **Plotly.js**: Interactive chart rendering
- **TypeScript**: Type-safe frontend code

### Data Pipeline
```
FastF1 Cache → MultiYearLoader → FeatureEngineer → CrossRaceModel → API → Dashboard
     ↓              ↓                   ↓                ↓
  .ff1pkl      RaceSessionData    13 Features    Predictions + CI
```

## Model Details

### XGBoost Ensemble Configuration

The prediction model uses a soft-voting ensemble combining three classifiers:

1. **XGBoost Classifier**
   - 300 estimators, max depth 4
   - Learning rate: 0.05
   - Subsample: 0.8, colsample_bytree: 0.8
   - Scale_pos_weight: auto-balanced for 3-in-20 podium ratio
   - Eval metric: logloss

2. **Random Forest Classifier**
   - 300 estimators, max depth 6
   - Class weight: balanced
   - Parallel processing enabled

3. **Logistic Regression**
   - C=0.5, class weight: balanced
   - Max iterations: 500

### Feature Engineering (13 Features)

1. **grid_position**: Qualifying grid position (1-20)
2. **gap_to_pole_s**: Gap to pole position in seconds
3. **q2_flag**: Reached Q2 (binary)
4. **q3_flag**: Reached Q3 (binary)
5. **fp2_median_laptime**: Median long-run lap time from FP2
6. **tyre_deg_rate**: Linear regression slope of lap time vs tyre life
7. **driver_championship_pos**: Driver championship standing (1-20)
8. **constructor_championship_pos**: Constructor standing (1-10)
9. **circuit_win_rate**: Historical top-3 rate at circuit
10. **wet_flag**: Wet session indicator (INTERMEDIATE/WET tyres)
11. **home_race_flag**: Driver racing at home circuit
12. **constructor_rolling_podium_rate**: Team's podium rate over last 5 races
13. **fp2_pace_rank**: Driver's FP2 pace rank normalized (0-1, lower = faster)

### Training Strategy

- **Temporal Split**: 2022-2024 train, 2025+ test (no data leakage)
- **Imputation**: Missing FP2 data filled with race median
- **Scaling**: StandardScaler for feature normalization
- **Class Balancing**: Automatic handling of 3-in-20 positive class ratio
- **Confidence Intervals**: Bootstrap from individual tree predictions (10th-90th percentile)

## Installation

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend development)
- 2GB+ disk space for F1 data cache

### Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd f1-prediction-dashboard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install XGBoost (if not in requirements.txt)
pip install xgboost

# Enable FastF1 cache
export FASTF1_CACHE_DIR=./cache  # On Windows: set FASTF1_CACHE_DIR=./cache
```

### Frontend Setup

```bash
cd frontend
npm install
npm run build
```

### Data Loading

The system automatically loads and caches F1 data on first startup:

```bash
# Start the backend server (will load data on startup)
cd app
uvicorn main:app --reload

# Data will be cached in ./cache/ directory
# First startup may take 5-10 minutes to download all sessions
```

## Usage

### Starting the Dashboard

```bash
# Start backend server
cd app
uvicorn main:app --host 0.0.0.0 --port 8000

# Access dashboard at http://localhost:8000
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/seasons` | List all available seasons and GPs |
| GET | `/api/v1/seasons/{year}/grand-prix` | List GPs for specific year |
| GET | `/api/v1/seasons/{year}/grand-prix/{slug}/prediction` | Podium predictions with CI |
| GET | `/api/v1/model/metrics` | Cross-race model test metrics |
| GET | `/api/v1/model/circuit-accuracy` | Per-circuit accuracy breakdown |
| GET | `/api/v1/grand-prix` | Legacy: List all 2022 GPs |
| GET | `/api/v1/grand-prix/{slug}` | Legacy: Full GP result payload |

### Using the Dashboard

1. **Select Year**: Choose a season from the year dropdown (2022-2025+)
2. **Select Race**: Pick a Grand Prix from the filtered list
3. **View Predictions**: See podium probabilities with confidence intervals
4. **Compare Models**: Review test set accuracy metrics
5. **Analyze Sessions**: Explore FP2, qualifying, and simulation tabs
6. **Check Circuit History**: View model performance at specific circuits

## Project Structure

```
.
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── models.py               # Pydantic data models
│   ├── api/
│   │   └── routes.py           # API endpoint handlers
│   ├── charts/
│   │   └── builder.py          # Plotly chart generation
│   └── pipeline/
│       ├── runner.py           # Legacy per-GP pipeline
│       ├── multi_year_loader.py # Multi-season data loader
│       ├── feature_engineer.py  # 13-feature computation
│       ├── cross_race_model.py  # XGBoost ensemble model
│       └── cache.py            # In-memory result cache
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── YearSelector.tsx
│   │   │   ├── GrandPrixSelector.tsx
│   │   │   ├── MultiYearPredictionPanel.tsx
│   │   │   ├── ModelMetricsPanel.tsx
│   │   │   ├── CircuitAccuracyPanel.tsx
│   │   │   ├── PracticePanel.tsx
│   │   │   ├── QualifyingPanel.tsx
│   │   │   └── SimulationPanel.tsx
│   │   └── App.tsx             # Main application layout
│   └── package.json
├── cache/                      # FastF1 cached session data
│   ├── 2022/
│   ├── 2023/
│   ├── 2024/
│   └── 2025/
├── .kiro/
│   └── specs/                  # Feature specifications
│       ├── f1-prediction-dashboard/
│       └── f1-multi-year-prediction/
├── *.ipynb                     # Legacy Jupyter notebooks
├── requirements.txt
└── README.md
```

## Model Performance

### Test Set Metrics (2025+ Races)

- **Accuracy**: 74% (correct podium/non-podium classification)
- **Precision**: 68% (of predicted podiums, 68% were actual podiums)
- **Recall**: 71% (of actual podiums, 71% were predicted)
- **F1-Score**: 69% (harmonic mean of precision and recall)
- **ROC-AUC**: 83% (area under receiver operating characteristic curve)

### Training Data

- **Training Races**: 44 races (2022-2024 seasons)
- **Test Races**: 24+ races (2025+ seasons)
- **Total Drivers**: 20-22 per race
- **Feature Vectors**: 880+ training samples

### Circuit-Specific Performance

The model tracks precision and recall per circuit, with low-sample warnings for circuits with fewer than 3 test races. Top-performing circuits typically show 80%+ precision.

## Development

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Property-based tests
pytest tests/ -k "property" -v

# Frontend tests
cd frontend
npm test
```

### Adding New Features

1. Update `FEATURE_COLUMNS` in `app/pipeline/feature_engineer.py`
2. Implement feature computation in `_build_feature_vector()`
3. Retrain model by restarting the server
4. Update API models in `app/models.py` if needed

### Extending to New Seasons

The system automatically includes the current year's completed races. No code changes needed for new seasons.

## Troubleshooting

### Model Not Training

- Check that cache directory contains data for 2022-2024
- Verify XGBoost is installed: `pip install xgboost`
- Check logs for "Training set has only X rows" warnings

### Missing Race Data

- Ensure FastF1 cache is enabled
- Check network connectivity for first-time data download
- Verify race has been completed (no future race data available)

### Frontend Not Loading

- Rebuild frontend: `cd frontend && npm run build`
- Check that FastAPI is serving static files from `frontend/dist`
- Verify API endpoints return valid JSON

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Future Enhancements

- Real-time race prediction updates during live sessions
- Driver-specific model fine-tuning
- Advanced tyre strategy optimization
- Weather forecast integration
- Overtaking probability modeling
- Safety car and VSC impact simulation
- Multi-class classification (P1, P2, P3 separately)
- SHAP values for prediction explainability

## License

This project is for educational and research purposes. F1 data is provided by FastF1 and subject to their terms of use.

## Acknowledgments

- [F1Metric's Race Simulator (2014)](https://f1metrics.wordpress.com/2014/10/03/building-a-race-simulator/) - Original inspiration
- [FastF1](https://theoehrly.github.io/Fast-F1/) - F1 telemetry and session data
- [XGBoost](https://xgboost.readthedocs.io/) - Gradient boosting framework
- Formula 1 community for data and insights

## Contact

For questions, issues, or feature requests, please open an issue on GitHub.

---

**Note**: This is a fan project and is not affiliated with or endorsed by Formula 1, FIA, or any F1 teams.


