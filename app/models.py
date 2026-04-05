"""Shared Pydantic v2 data models for the F1 Prediction Dashboard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DriverPrediction(BaseModel):
    driver_code: str
    win_probability: float  # rounded to 2 decimal places


class ModelMetrics(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float


class FeatureScore(BaseModel):
    feature_name: str  # human-readable label
    importance: float


class PredictionResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    winner: DriverPrediction
    podium: list[DriverPrediction]          # top 3
    model_used: str                         # e.g. "Random Forest"
    model_comparison: list[ModelMetrics]
    feature_importance: list[FeatureScore]  # top 10, sorted desc


class PracticeResult(BaseModel):
    lap_time_chart: dict        # Plotly JSON
    stint_analysis_chart: dict  # Plotly JSON
    raw_fp2_df: list[dict]      # serialized fp2_race_sim rows


class GridEntry(BaseModel):
    position: int
    driver_code: str
    best_lap_seconds: float
    q1: float | None = None
    q2: float | None = None
    q3: float | None = None


class QualifyingResult(BaseModel):
    grid: list[GridEntry]
    gap_to_pole_chart: dict          # Plotly JSON
    teammate_comparison_chart: dict  # Plotly JSON


class SimFinisher(BaseModel):
    position: int
    driver_code: str
    gap_to_leader_seconds: float


class PitStrategy(BaseModel):
    driver_code: str
    pit_laps: list[int]
    compound_sequence: list[str]


class SimulationResult(BaseModel):
    lap_by_lap_chart: dict               # Plotly JSON
    final_classification: list[SimFinisher]
    pit_strategies: list[PitStrategy]


class DriverStats(BaseModel):
    driver_code: str
    soft_avg_time_rep: float | None = None
    medium_avg_time_rep: float | None = None
    hard_avg_time_rep: float | None = None
    total_avg_time_rep: float | None = None
    total_laps_rep: int
    dnf_index: float
    home_race_advantage: bool


class DriverStatsResult(BaseModel):
    drivers: list[DriverStats]


class GPResult(BaseModel):
    gp_slug: str
    display_name: str                       # e.g. "2022 Bahrain Grand Prix"
    prediction: PredictionResult | None = None
    practice: PracticeResult | None = None
    qualifying: QualifyingResult | None = None
    simulation: SimulationResult | None = None


# ---------------------------------------------------------------------------
# Multi-year prediction models
# ---------------------------------------------------------------------------

class FeatureVector(BaseModel):
    driver_code: str
    year: int
    gp_slug: str
    circuit_name: str
    grid_position: int
    gap_to_pole_s: float
    q2_flag: int
    q3_flag: int
    fp2_median_laptime: float
    tyre_deg_rate: float
    driver_championship_pos: int
    constructor_championship_pos: int
    circuit_win_rate: float
    wet_flag: int
    home_race_flag: int
    podium: int | None = None  # None for future races


class PodiumPredictionResult(BaseModel):
    driver_code: str
    podium_probability: float       # predict_proba output, rounded to 3dp
    ci_low: float                   # 10th percentile of tree predictions
    ci_high: float                  # 90th percentile of tree predictions
    above_threshold: bool           # podium_probability > 0.5
    actual_podium: bool | None = None  # None if race not yet completed


class CrossRaceMetrics(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    training_race_count: int
    test_race_count: int


class CircuitAccuracy(BaseModel):
    circuit_name: str
    precision: float
    recall: float
    race_count: int
    low_sample_warning: bool        # True if race_count < 3


class SeasonEvent(BaseModel):
    gp_slug: str
    display_name: str
    year: int
    is_training_set: bool           # year in {2022, 2023}
    is_test_set: bool               # year >= 2024
    has_actual_result: bool


class RaceSessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    year: int
    gp_slug: str
    event_name: str
    circuit_name: str
    qualifying_session: object | None = None
    fp2_session: object | None = None
    race_session: object | None = None
    actual_top3: list[str] = []     # driver codes of actual top-3 finishers
