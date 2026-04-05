# Requirements Document

## Introduction

This feature transforms the existing Formula 1 race prediction and simulation Jupyter Notebook project into a publicly accessible web dashboard. The dashboard exposes the outputs of the existing ML pipeline (race winner predictions, podium probabilities, strategy simulations, driver/qualifying/practice analysis) through an interactive, hosted web interface. Users — fans, analysts, team managers, and bettors — can browse race predictions and visualizations without running notebooks locally.

The existing system uses FastF1 for data ingestion, cached `.ff1pkl` files for the 2022 season, and produces visualizations via Matplotlib/Seaborn. The dashboard wraps these outputs in a web-served UI.

## Glossary

- **Dashboard**: The web application that hosts and displays F1 predictions and visualizations.
- **ML_Pipeline**: The existing Python code (notebooks) that preprocesses data, trains classifiers, and produces predictions.
- **Prediction**: The output of the ML_Pipeline estimating the race winner and podium finishers for a given Grand Prix.
- **Simulation**: The race simulation output produced by the RaceSim notebook, modeling lap-by-lap race progression.
- **Session**: A specific F1 event session — Free Practice 1/2/3, Qualifying, or Race.
- **Grand_Prix**: A single Formula 1 race weekend identified by year and event name (e.g., 2022 Bahrain Grand Prix).
- **Driver**: A Formula 1 competitor identified by a three-letter code and full name.
- **Constructor**: A Formula 1 team (e.g., Red Bull, Ferrari).
- **FastF1**: The Python package used to retrieve and cache F1 telemetry and session data.
- **Cache**: Local `.ff1pkl` files storing pre-fetched FastF1 session data for the 2022 season.
- **Visualization**: A chart or plot generated from session or prediction data (lap times, stint analysis, qualifying gaps, position changes, etc.).
- **Backend**: The Python web server that executes the ML_Pipeline and serves data to the Dashboard.
- **Frontend**: The browser-based UI layer of the Dashboard.
- **API**: The HTTP interface between the Frontend and the Backend.

---

## Requirements

### Requirement 1: Race Selection

**User Story:** As a user, I want to select a Grand Prix from the 2022 season, so that I can view predictions and analysis specific to that race.

#### Acceptance Criteria

1. THE Dashboard SHALL display a list of all Grand Prix events available in the local Cache.
2. WHEN a user selects a Grand Prix, THE Dashboard SHALL load and display all available analysis sections for that event (Practice, Qualifying, Race prediction, Simulation).
3. IF no cached data exists for a selected Grand Prix, THEN THE Dashboard SHALL display a descriptive error message indicating the data is unavailable.
4. THE Dashboard SHALL default to displaying the most recently cached Grand Prix on initial load.

---

### Requirement 2: Race Winner and Podium Predictions

**User Story:** As a user, I want to see ML-generated race winner and podium predictions, so that I can understand which drivers are most likely to finish at the top.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display the predicted race winner and top-3 podium finishers produced by the ML_Pipeline.
2. THE Dashboard SHALL display the predicted win probability for each Driver in the top-3 as a percentage rounded to two decimal places.
3. THE Dashboard SHALL display which ML model (Logistic Regression, Random Forest, SVM, or Gaussian Naive Bayes) produced the displayed prediction.
4. WHEN multiple models are available, THE Dashboard SHALL display a model comparison table showing accuracy, precision, recall, and F1-score for each model.
5. IF the ML_Pipeline fails to produce a prediction for a selected Grand Prix, THEN THE Backend SHALL return a structured error response and THE Dashboard SHALL display a descriptive error message.

---

### Requirement 3: Practice Session Analysis

**User Story:** As a user, I want to view Free Practice 2 long-run and lap time analysis, so that I can understand driver race pace before the Grand Prix.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display lap time distributions per Driver for the FP2 session sourced from the Cache.
2. THE Dashboard SHALL display stint-level long-run analysis showing average lap time per tyre compound per Driver.
3. THE Dashboard SHALL render all Practice visualizations as interactive charts that support hover tooltips showing lap number, lap time, and tyre compound.
4. IF FP2 data is absent from the Cache for a selected Grand Prix, THEN THE Dashboard SHALL display a message indicating FP2 data is unavailable for that event.

---

### Requirement 4: Qualifying Analysis

**User Story:** As a user, I want to view qualifying session analysis including teammate comparisons and one-lap pace, so that I can assess grid positions and driver form.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display each Driver's best qualifying lap time and grid position.
2. THE Dashboard SHALL display a teammate head-to-head qualifying comparison for each Constructor, showing the lap time delta in milliseconds.
3. THE Dashboard SHALL display a gap-to-pole visualization showing each Driver's qualifying time delta relative to the pole position lap time.
4. IF qualifying data is absent from the Cache for a selected Grand Prix, THEN THE Dashboard SHALL display a message indicating qualifying data is unavailable for that event.

---

### Requirement 5: Race Simulation Results

**User Story:** As a user, I want to view race simulation outputs, so that I can see projected lap-by-lap race progression and strategy outcomes.

#### Acceptance Criteria

1. WHEN a Grand Prix is selected, THE Dashboard SHALL display the race simulation results produced by the RaceSim notebook for that event.
2. THE Dashboard SHALL display a lap-by-lap position chart for all simulated Drivers across the full race distance.
3. THE Dashboard SHALL display each Driver's predicted pit stop laps and tyre compound sequence.
4. THE Dashboard SHALL display the simulated final race classification with finishing positions and gap to leader.
5. IF simulation data is absent for a selected Grand Prix, THEN THE Dashboard SHALL display a message indicating simulation results are unavailable for that event.

---

### Requirement 6: Driver Statistics View

**User Story:** As a user, I want to view historical driver performance statistics, so that I can understand each driver's career metrics and form.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Driver statistics panel sourced from the DriverStats notebook outputs, including wins, podiums, DNF count, and points per season.
2. WHEN a user selects a Driver, THE Dashboard SHALL display that Driver's performance metrics filtered to the 2022 season.
3. THE Dashboard SHALL display a DNF index and home race advantage indicator for each Driver as computed by the ML_Pipeline feature engineering step.

---

### Requirement 7: Backend Data API

**User Story:** As a developer, I want a structured API that serves prediction and session data, so that the Frontend can retrieve and display results without executing notebooks directly.

#### Acceptance Criteria

1. THE Backend SHALL expose an HTTP API endpoint that returns the list of available Grand Prix events from the Cache.
2. WHEN the API receives a valid Grand Prix identifier, THE Backend SHALL return prediction results, session analysis data, and simulation outputs in JSON format.
3. WHEN the API receives an invalid or unknown Grand Prix identifier, THE Backend SHALL return an HTTP 404 response with a descriptive error message.
4. THE Backend SHALL execute the ML_Pipeline using pre-cached data and SHALL NOT require a live FastF1 network connection to serve cached race data.
5. THE Backend SHALL respond to API requests within 10 seconds for any Grand Prix with data present in the Cache.
6. IF the ML_Pipeline raises an unhandled exception during execution, THEN THE Backend SHALL return an HTTP 500 response with a structured error body containing the exception type and message.

---

### Requirement 8: Hosted Deployment

**User Story:** As a user, I want to access the dashboard via a public URL, so that I can view predictions and analysis from any device without installing software.

#### Acceptance Criteria

1. THE Dashboard SHALL be accessible via a public HTTPS URL without requiring the user to install Python, Jupyter, or any local dependencies.
2. THE Backend SHALL serve the Frontend static assets and API from the same hosted origin.
3. THE Dashboard SHALL render correctly on screen widths between 768px and 1920px.
4. WHEN the Dashboard is loaded in a browser, THE Frontend SHALL complete initial render within 5 seconds on a 10 Mbps connection.
5. WHERE authentication is not configured, THE Dashboard SHALL be publicly accessible without login.

---

### Requirement 9: Feature Importance and Model Explainability

**User Story:** As an analyst, I want to see which features most influenced the ML model's prediction, so that I can understand the reasoning behind race outcome forecasts.

#### Acceptance Criteria

1. WHEN a prediction is displayed, THE Dashboard SHALL show a feature importance chart for the Random Forest model listing the top 10 features by importance score.
2. THE Dashboard SHALL label each feature using a human-readable name (e.g., "Home Race Advantage", "DNF Index", "Qualifying Position").
3. THE Dashboard SHALL display the feature importance values as a horizontal bar chart sorted in descending order of importance.
