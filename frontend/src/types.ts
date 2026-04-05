export interface DriverPrediction { driver_code: string; win_probability: number; }
export interface ModelMetrics { model_name: string; accuracy: number; precision: number; recall: number; f1_score: number; }
export interface FeatureScore { feature_name: string; importance: number; }
export interface PredictionResult { winner: DriverPrediction; podium: DriverPrediction[]; model_used: string; model_comparison: ModelMetrics[]; feature_importance: FeatureScore[]; }
export interface GridEntry { position: number; driver_code: string; best_lap_seconds: number; q1: number | null; q2: number | null; q3: number | null; }
export interface QualifyingResult { grid: GridEntry[]; gap_to_pole_chart: object; teammate_comparison_chart: object; }
export interface PracticeResult { lap_time_chart: object; stint_analysis_chart: object; raw_fp2_df: object[]; }
export interface SimFinisher { position: number; driver_code: string; gap_to_leader_seconds: number; }
export interface PitStrategy { driver_code: string; pit_laps: number[]; compound_sequence: string[]; }
export interface SimulationResult { lap_by_lap_chart: object; final_classification: SimFinisher[]; pit_strategies: PitStrategy[]; }
export interface DriverStats { driver_code: string; soft_avg_time_rep: number | null; medium_avg_time_rep: number | null; hard_avg_time_rep: number | null; total_avg_time_rep: number | null; total_laps_rep: number; dnf_index: number; home_race_advantage: boolean; }
export interface GPResult { gp_slug: string; display_name: string; prediction: PredictionResult | null; practice: PracticeResult | null; qualifying: QualifyingResult | null; simulation: SimulationResult | null; }
export interface GrandPrixItem { slug: string; display_name: string; }

export interface SeasonEvent {
  gp_slug: string;
  display_name: string;
  year: number;
  is_training_set: boolean;
  is_test_set: boolean;
  has_actual_result: boolean;
}

export interface PodiumPrediction {
  driver_code: string;
  podium_probability: number;
  ci_low: number;
  ci_high: number;
  above_threshold: boolean;
  actual_podium: boolean | null;
}

export interface MultiYearPredictionResponse {
  gp_slug: string;
  display_name: string;
  is_test_set: boolean;
  has_actual_result: boolean;
  predictions: PodiumPrediction[];
  actual_top3: string[];
}

export interface CrossRaceMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  training_race_count: number;
  test_race_count: number;
}

export interface CircuitAccuracy {
  circuit_name: string;
  precision: number;
  recall: number;
  race_count: number;
  low_sample_warning: boolean;
}
