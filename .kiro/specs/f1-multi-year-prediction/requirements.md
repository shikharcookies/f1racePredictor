# Requirements Document

## Introduction

This feature upgrades the existing F1 Prediction Dashboard from a single-season (2022), per-race ML model to a multi-year, cross-race predictive system covering the 2022–2025 seasons and the current year. The upgrade replaces the misleading per-race Random Forest classifier with a properly trained and validated binary classifier that predicts podium finishes (top 3) across all historical races. The model is trained on 2022–2023 data and evaluated on 2024+ held-out races, producing real accuracy metrics. The dashboard gains a year selector, confidence intervals, per-circuit accuracy history, and automatic handling of driver/team roster changes across seasons via FastF1.

## Glossary

- **Dashboard**: The web application that hosts and displays F1 predictions and visualizations.
- **ML_Pipeline**: The Python code that loads multi-year data, engineers features, trains the cross-race classifier, and produces predictions.
- **Podium_Prediction**: A binary classification output indicating whether a given Driver is predicted to finish in the top 3 for a given race.
- **Cross_Race_Model**: A single ML model trained across all historical races (not per-race), enabling generalization to unseen events.
- **Training_Set**: Races from the 2022 and 2023 seasons used to fit the Cross_Race_Model.
- **Test_Set**: Races from the 2024 season onward used exclusively to evaluate Cross_Race_Model accuracy.
- **Feature_Vector**: The set of numerical inputs derived per driver per race used to train and run the Cross_Race_Model.
- **Confidence_Interval**: A range around a predicted probability indicating the model's uncertainty, computed via bootstrap or predict_proba variance across estimators.
- **Circuit_Accuracy**: The historical precision and recall of the Cross_Race_Model on the Test_Set, grouped by circuit.
- **Session**: A specific F1 event session — Free Practice 2, Qualifying, or Race.
- **Grand_Prix**: A single Formula 1 race weekend identified by year and event name (e.g., 2024 Monaco Grand Prix).
- **Driver**: A Formula 1 competitor identified by a three-letter code and full name.
- **Constructor**: A Formula 1 team (e.g., Red Bull, Ferrari).
- **FastF1**: The Python package used to retrieve and cache F1 telemetry and session data for seasons 2022–2025 and the current year.
- **Cache**: Local `.ff1pkl` files storing pre-fetched FastF1 session data.
- **Backend**: The Python web server that executes the ML_Pipeline and serves data to the Dashboard.
- **Frontend**: The browser-based UI layer of the Dashboard.
- **API**: The HTTP interface between the Frontend and the Backend.
- **FP2_Long_Run**: A sequence of consecutive laps on the same tyre compound during Free Practice 2, used to estimate race pace.
- **Tyre_Degradation_Rate**: The rate of lap time increase per lap on a given compound, derived from FP2 long-run data via linear regression.
- **Championship_Standing**: A Driver's or Constructor's cumulative points position in the World Championship at the time of a given race.
- **Home_Race**: A race held in the country of a Driver's nationality.

---

## Requirements

### Requirement 1: Multi-Year Data Loading

**User Story:** As a data engineer, I want the system to load race data from the 2022, 2023, 2024, 2025, and current seasons, so that the ML model has sufficient historical data to learn cross-race patterns.

#### Acceptance Criteria

1. THE ML_Pipeline SHALL load qualifying, FP2, and race result session data for all completed Grand Prix events across the 2022, 2023, 2024, and 2025 seasons using FastF1.
2. WHEN the current calendar year is beyond 2025, THE ML_Pipeline SHALL also load data for the current year's completed races.
3. THE ML_Pipeline SHALL store all loaded session data in the local Cache using FastF1's cache mechanism to avoid redundant network calls.
4. WHEN FastF1 cannot retrieve session data for a specific Grand Prix due to a network error, THE ML_Pipeline SHALL log a warning and continue loading remaining sessions without raising an unhandled exception.
5. THE ML_Pipeline SHALL automatically discover driver and team roster entries from FastF1 session data for each season, without requiring manual updates to a hardcoded driver list.
6. WHEN a Driver appears in one season but not another, THE ML_Pipeline SHALL include that Driver only in Feature_Vectors for races in which FastF1 reports them as a participant.

---

### Requirement 2: Feature Engineering

**User Story:** As a data scientist, I want the model to use a richer set of race-relevant features, so that predictions are based on factors with genuine predictive power.

#### Acceptance Criteria

1. THE ML_Pipeline SHALL compute the following features for each Driver in each race and include them in the Feature_Vector: qualifying grid position, gap to pole position in seconds, Q2 participation flag, Q3 participation flag, FP2 median long-run lap time, Tyre_Degradation_Rate from FP2, Driver Championship_Standing at race time, Constructor Championship_Standing at race time, Driver historical win rate at the current circuit, weather condition flag (1 for wet session, 0 for dry), and Home_Race flag.
2. WHEN FP2 long-run data is unavailable for a Driver in a given race, THE ML_Pipeline SHALL substitute the median FP2 long-run lap time of all Drivers in that race for the missing value.
3. WHEN Tyre_Degradation_Rate cannot be computed for a Driver due to insufficient FP2 laps, THE ML_Pipeline SHALL substitute the median Tyre_Degradation_Rate of all Drivers in that race.
4. WHEN Championship_Standing data is unavailable for a race, THE ML_Pipeline SHALL substitute a value of 20 for Driver standing and 10 for Constructor standing as neutral defaults.
5. THE ML_Pipeline SHALL derive weather condition from the FastF1 weather data for the qualifying session of each race, classifying the session as wet if any lap is recorded on INTERMEDIATE or WET tyres.
6. THE ML_Pipeline SHALL compute historical circuit win rate as the number of times a Driver has finished in the top 3 at the same circuit in prior seasons divided by the total number of starts at that circuit in prior seasons.
7. WHEN a Driver has zero prior starts at a circuit, THE ML_Pipeline SHALL set the historical circuit win rate to 0.0.

---

### Requirement 3: Cross-Race Model Training and Validation

**User Story:** As a data scientist, I want the model trained across all historical races with a proper temporal train/test split, so that accuracy metrics reflect genuine out-of-sample predictive performance.

#### Acceptance Criteria

1. THE ML_Pipeline SHALL train the Cross_Race_Model on all Feature_Vectors from races in the Training_Set (2022 and 2023 seasons).
2. THE ML_Pipeline SHALL evaluate the Cross_Race_Model exclusively on Feature_Vectors from the Test_Set (2024 season and later completed races).
3. THE ML_Pipeline SHALL use a Random Forest classifier as the Cross_Race_Model with class weighting set to "balanced" to account for the 3-in-20 positive class ratio.
4. THE ML_Pipeline SHALL compute and store the following metrics on the Test_Set: accuracy, precision, recall, F1-score, and ROC-AUC.
5. THE ML_Pipeline SHALL compute Circuit_Accuracy by grouping Test_Set predictions by circuit and computing precision and recall per circuit.
6. THE ML_Pipeline SHALL compute a Confidence_Interval for each Driver's podium probability by collecting the individual tree predictions from the Random Forest and reporting the 10th and 90th percentile of the distribution.
7. WHEN the Training_Set contains fewer than 200 Feature_Vectors, THE ML_Pipeline SHALL log a warning indicating insufficient training data and SHALL still produce a model using all available data.
8. THE ML_Pipeline SHALL NOT use any Test_Set data during model training or hyperparameter selection.

---

### Requirement 4: Podium Prediction Output

**User Story:** As a user, I want to see which drivers are predicted to finish on the podium, so that I can assess the model's top-3 forecast for an upcoming or recent race.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display the Cross_Race_Model's predicted podium probability for each Driver in that race, sorted in descending order of probability.
2. THE Dashboard SHALL display the Confidence_Interval (10th–90th percentile range) alongside each Driver's predicted podium probability.
3. THE Dashboard SHALL visually distinguish Drivers with a predicted podium probability above 0.5 from those below 0.5.
4. WHEN the selected Grand Prix is in the Test_Set and actual race results are available, THE Dashboard SHALL display the actual podium finishers alongside the predictions to enable direct comparison.
5. IF the Cross_Race_Model has not been trained when a prediction is requested, THEN THE Backend SHALL return an HTTP 503 response with a descriptive error message.

---

### Requirement 5: Real Accuracy Metrics Display

**User Story:** As an analyst, I want to see real model accuracy computed on held-out test races, so that I can assess whether the predictions are trustworthy.

#### Acceptance Criteria

1. THE Dashboard SHALL display the Cross_Race_Model's Test_Set accuracy, precision, recall, F1-score, and ROC-AUC in a dedicated metrics panel.
2. THE Dashboard SHALL display the number of races in the Training_Set and the number of races in the Test_Set alongside the metrics.
3. THE Dashboard SHALL display a Circuit_Accuracy table showing precision and recall per circuit for all circuits present in the Test_Set.
4. WHEN a circuit has fewer than 3 races in the Test_Set, THE Dashboard SHALL display a low-sample warning indicator next to that circuit's Circuit_Accuracy values.
5. THE Dashboard SHALL NOT display per-race cross-validation accuracy computed on training data as a substitute for Test_Set accuracy.

---

### Requirement 6: Year and Race Selector

**User Story:** As a user, I want to filter races by season year, so that I can browse predictions and analysis for a specific year's calendar.

#### Acceptance Criteria

1. THE Dashboard SHALL display a year selector control populated with all seasons for which at least one completed Grand Prix exists in the Cache (2022, 2023, 2024, 2025, and current year as applicable).
2. WHEN a user selects a year, THE Dashboard SHALL update the Grand Prix list to show only races from that season.
3. THE Dashboard SHALL default to the current season on initial load, or the most recent season with data if the current season has no cached races.
4. WHEN a user selects a Grand Prix from a past season that is in the Test_Set, THE Dashboard SHALL display both the prediction and the actual race result for comparison.
5. WHEN a user selects a Grand Prix from a past season that is in the Training_Set, THE Dashboard SHALL display a label indicating the race was used for model training.

---

### Requirement 7: FP2 Long-Run and Tyre Degradation Analysis

**User Story:** As a user, I want to view FP2 long-run pace and tyre degradation rates, so that I can understand each driver's expected race pace and tyre management.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display the FP2 median long-run lap time per Driver per tyre compound sourced from the Cache.
2. THE Dashboard SHALL display the Tyre_Degradation_Rate per Driver per compound as a slope value in seconds per lap, derived from linear regression on FP2 long-run stints.
3. THE Dashboard SHALL render FP2 long-run analysis as an interactive chart with hover tooltips showing lap number, lap time, tyre compound, and stint number.
4. IF FP2 data is absent from the Cache for a selected Grand Prix, THEN THE Dashboard SHALL display a message indicating FP2 data is unavailable for that event.

---

### Requirement 8: Actual Race Result Integration

**User Story:** As a user, I want the system to fetch and display actual race results for completed races, so that I can compare predictions against what actually happened.

#### Acceptance Criteria

1. WHEN a completed Grand Prix is selected, THE Backend SHALL load the actual race finishing order from the FastF1 race session data for that event.
2. THE Dashboard SHALL display the actual top-3 finishers alongside the predicted podium for any completed race in the Test_Set.
3. THE Backend SHALL cache actual race results in the local Cache to avoid repeated network calls for the same completed race.
4. WHEN actual race result data is unavailable for a selected Grand Prix, THE Dashboard SHALL display a message indicating results are not yet available.

---

### Requirement 9: Driver and Team Roster Management

**User Story:** As a developer, I want the system to handle driver and team changes across seasons automatically, so that new drivers and mid-season team changes are reflected without manual code updates.

#### Acceptance Criteria

1. THE ML_Pipeline SHALL derive the active Driver roster for each race from FastF1 session participant data rather than a hardcoded list.
2. WHEN a Driver joins the grid mid-season (e.g., a substitute driver), THE ML_Pipeline SHALL include that Driver in Feature_Vectors for races in which FastF1 reports them as a participant.
3. THE ML_Pipeline SHALL derive Constructor-to-Driver mappings for each race from FastF1 session data, reflecting mid-season team changes.
4. WHEN a Driver's Constructor changes between races, THE ML_Pipeline SHALL use the Constructor Championship_Standing of the Constructor the Driver raced for in that specific race.

---

### Requirement 10: Backend API Extensions

**User Story:** As a developer, I want the API to expose multi-year data and model metrics, so that the Frontend can display year-filtered race lists, real accuracy metrics, and per-circuit accuracy.

#### Acceptance Criteria

1. THE Backend SHALL expose an API endpoint that returns the list of available seasons and their Grand Prix events.
2. WHEN the API receives a valid season year and Grand Prix identifier, THE Backend SHALL return the Feature_Vector, Podium_Prediction with Confidence_Interval, and actual race result (if available) in JSON format.
3. THE Backend SHALL expose an API endpoint that returns the Cross_Race_Model's Test_Set metrics: accuracy, precision, recall, F1-score, ROC-AUC, training race count, and test race count.
4. THE Backend SHALL expose an API endpoint that returns Circuit_Accuracy data for all circuits in the Test_Set.
5. WHEN the API receives a request for a Grand Prix that has no cached data, THE Backend SHALL return an HTTP 404 response with a descriptive error message.
6. WHEN the ML_Pipeline raises an unhandled exception during model training or prediction, THE Backend SHALL return an HTTP 500 response with a structured error body containing the exception type and message.
7. THE Backend SHALL respond to all API requests within 10 seconds for any Grand Prix with data present in the Cache.

---

### Requirement 11: Dashboard Visualization Updates

**User Story:** As a user, I want the dashboard to show prediction confidence, historical accuracy per circuit, and model metrics, so that I can interpret predictions with appropriate context.

#### Acceptance Criteria

1. THE Dashboard SHALL display a confidence interval bar for each Driver's podium probability in the prediction panel, showing the 10th–90th percentile range.
2. THE Dashboard SHALL display a Circuit_Accuracy chart showing precision and recall per circuit for all circuits in the Test_Set, rendered as a grouped bar chart.
3. THE Dashboard SHALL display the Cross_Race_Model's overall Test_Set metrics (accuracy, precision, recall, F1-score, ROC-AUC) in a summary metrics panel visible on every race view.
4. THE Dashboard SHALL display a label on each Grand Prix indicating whether it belongs to the Training_Set or the Test_Set.
5. WHEN a Grand Prix is in the Test_Set and actual results are available, THE Dashboard SHALL render a side-by-side comparison of predicted versus actual podium finishers.
6. THE Dashboard SHALL render all new visualizations as interactive Plotly charts with hover tooltips.
