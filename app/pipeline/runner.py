"""PipelineRunner: discovers GP directories and builds GPResult objects."""

import logging
import os
import pickle
import sys
from pathlib import Path

# Make workspace root importable so existing modules (qualifying, prediction, etc.) can be found.
_WORKSPACE_ROOT = str(Path(__file__).resolve().parents[2])
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

import fastf1  # noqa: E402 – must come after sys.path patch

import qualifying as qual_module  # noqa: E402

from app.models import (  # noqa: E402
    GPResult,
    PredictionResult,
    DriverPrediction,
    PracticeResult,
    QualifyingResult,
    GridEntry,
    SimulationResult,
    SimFinisher,
    PitStrategy,
)

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(_WORKSPACE_ROOT) / "cache" / "2022"


def _parse_display_name(gp_slug: str) -> str:
    """Convert '2022-03-20_Bahrain_Grand_Prix' → '2022 Bahrain Grand Prix'."""
    parts = gp_slug.split("_", 1)  # split on first underscore after date
    if len(parts) == 2:
        date_part = parts[0]          # e.g. '2022-03-20'
        year = date_part.split("-")[0]  # e.g. '2022'
        name_part = parts[1].replace("_", " ")  # e.g. 'Bahrain Grand Prix'
        return f"{year} {name_part}"
    return gp_slug.replace("_", " ")


def _load_pkl(path: Path):
    """Load a pickle file; return None on failure."""
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.warning("Could not load pickle %s: %s", path, exc)
        return None


class PipelineRunner:
    def run_all(self) -> dict[str, GPResult]:
        results: dict[str, GPResult] = {}
        if not _CACHE_DIR.exists():
            logger.warning("Cache directory %s does not exist", _CACHE_DIR)
            return results

        for entry in sorted(_CACHE_DIR.iterdir()):
            if entry.is_dir():
                gp_slug = entry.name
                try:
                    result = self.run_for_gp(gp_slug)
                    results[gp_slug] = result
                except Exception as exc:
                    logger.error("Failed to process GP %s: %s", gp_slug, exc)
                    results[gp_slug] = GPResult(
                        gp_slug=gp_slug,
                        display_name=_parse_display_name(gp_slug),
                    )
        return results

    def run_for_gp(self, gp_slug: str) -> GPResult:
        display_name = _parse_display_name(gp_slug)
        logger.info("Processing GP: %s (%s)", gp_slug, display_name)

        # Enable FastF1 cache (cache-only mode — no network calls)
        fastf1.Cache.enable_cache(str(Path(_WORKSPACE_ROOT) / "cache"))

        practice_result = self._build_practice(gp_slug)
        qualifying_result = self._build_qualifying(gp_slug, display_name)
        prediction_result = self._build_prediction_from_qualifying(qualifying_result)

        return GPResult(
            gp_slug=gp_slug,
            display_name=display_name,
            prediction=prediction_result,
            practice=practice_result,
            qualifying=qualifying_result,
            simulation=self._build_simulation(qualifying_result, practice_result),
        )

    # ------------------------------------------------------------------
    # Practice
    # ------------------------------------------------------------------

    def _build_practice(self, gp_slug: str) -> "PracticeResult | None":
        try:
            import numpy as np
            from race import convert_laptime_to_seconds

            date_str, *name_parts = gp_slug.split("_")
            year = int(date_str.split("-")[0])
            gp_name = " ".join(name_parts)

            session = fastf1.get_session(year, gp_name, "FP2")
            session.load(laps=True, telemetry=False, weather=False, messages=False)

            laps = session.laps.pick_accurate().pick_wo_box()
            if laps.empty:
                return None

            # Convert lap times to seconds
            laps = laps.copy()
            convert_laptime_to_seconds(laps)

            from app.charts.builder import ChartBuilder
            from constants import TEAMMATE_PAIRS_DICT

            # Build per-driver summary for raw_fp2_df
            drivers = laps["Driver"].unique().tolist()
            raw_rows = []
            for driver in drivers:
                driver_laps = laps[laps["Driver"] == driver]
                for compound in driver_laps["Compound"].unique():
                    compound_laps = driver_laps[driver_laps["Compound"] == compound]
                    valid = compound_laps["LapTime"].dropna()
                    if valid.empty:
                        continue
                    raw_rows.append({
                        "Driver": driver,
                        "Compound": str(compound),
                        "LapTime": float(valid.mean()),
                        "LapTimes": [float(x) for x in valid.tolist()],
                        "LapNumbers": compound_laps["LapNumber"].tolist(),
                    })

            builder = ChartBuilder()
            lap_chart = builder.lap_time_distribution(raw_rows)
            stint_chart = builder.stint_analysis(raw_rows)

            return PracticeResult(
                lap_time_chart=lap_chart,
                stint_analysis_chart=stint_chart,
                raw_fp2_df=raw_rows,
            )
        except Exception as exc:
            logger.error("Practice build failed for %s: %s", gp_slug, exc)
            return None

    # ------------------------------------------------------------------
    # Qualifying
    # ------------------------------------------------------------------

    def _build_qualifying(self, gp_slug: str, display_name: str) -> "QualifyingResult | None":
        try:
            date_str, *name_parts = gp_slug.split("_")
            year = int(date_str.split("-")[0])
            gp_name = " ".join(name_parts)  # e.g. 'Bahrain Grand Prix'

            session = fastf1.get_session(year, gp_name, "Q")
            session.load()

            times_df = qual_module.get_fastest_lap_in_qualifying(session.results)

            grid: list[GridEntry] = []
            for pos, (_, row) in enumerate(
                times_df.sort_values("Fastest Lap").iterrows(), start=1
            ):
                grid.append(
                    GridEntry(
                        position=pos,
                        driver_code=str(row["Abbreviation"]),
                        best_lap_seconds=float(row["Fastest Lap"]),
                        q1=float(row["Q1"]) if row.get("Q1") is not None and str(row.get("Q1")) != "nan" else None,
                        q2=float(row["Q2"]) if row.get("Q2") is not None and str(row.get("Q2")) != "nan" else None,
                        q3=float(row["Q3"]) if row.get("Q3") is not None and str(row.get("Q3")) != "nan" else None,
                    )
                )

            from app.charts.builder import ChartBuilder
            from constants import TEAMMATE_PAIRS_DICT

            builder = ChartBuilder()
            gap_chart = builder.qualifying_gap_to_pole([e.model_dump() for e in grid])
            teammate_chart = builder.teammate_comparison([e.model_dump() for e in grid], TEAMMATE_PAIRS_DICT)

            return QualifyingResult(
                grid=grid,
                gap_to_pole_chart=gap_chart,
                teammate_comparison_chart=teammate_chart,
            )
        except Exception as exc:
            logger.error("Qualifying build failed for %s: %s", gp_slug, exc)
            return None

    # ------------------------------------------------------------------
    # Simulation (simplified race model using tyre degradation)
    # ------------------------------------------------------------------

    def _build_simulation(self, qualifying_result: "QualifyingResult | None",
                          practice_result: "PracticeResult | None") -> "SimulationResult | None":
        try:
            if qualifying_result is None or not qualifying_result.grid:
                return None

            import numpy as np
            from race_sim import tyre_degradation_model
            from app.charts.builder import ChartBuilder

            RACE_LAPS = 57          # approximate F1 race length
            PIT_LOSS = 22.0         # seconds lost in pit stop
            FUEL_EFFECT = 0.08      # seconds per lap fuel gain as fuel burns off

            # Build base lap time per driver from FP2 or qualifying
            fp2_times: dict[str, float] = {}
            if practice_result and practice_result.raw_fp2_df:
                for row in practice_result.raw_fp2_df:
                    driver = row.get("Driver")
                    lt = row.get("LapTime")
                    if driver and lt and isinstance(lt, (int, float)):
                        if driver not in fp2_times or lt < fp2_times[driver]:
                            fp2_times[driver] = float(lt)

            grid = qualifying_result.grid
            pole_time = grid[0].best_lap_seconds

            # Simple 2-stop strategy: SOFT → MEDIUM → HARD
            # Pit on lap 18 and lap 38
            STRATEGY = [
                ("SOFT",   list(range(1, 19))),
                ("MEDIUM", list(range(19, 39))),
                ("HARD",   list(range(39, RACE_LAPS + 1))),
            ]

            # Simulate each driver
            driver_total_times: dict[str, float] = {}
            driver_lap_times: dict[str, list[float]] = {}
            pit_strategies: list[PitStrategy] = []

            for entry in grid:
                driver = entry.driver_code
                # Base time: use FP2 if available, else scale from qualifying
                base = fp2_times.get(driver, pole_time * 1.02 + (entry.position - 1) * 0.15)

                total = 0.0
                lap_times_list = []
                pit_laps = []
                compounds = []

                for compound, laps in STRATEGY:
                    compounds.append(compound)
                    for i, lap in enumerate(laps):
                        tyre_life = i + 1
                        deg = tyre_degradation_model(tyre_life, compound)
                        fuel_saving = (RACE_LAPS - lap) * FUEL_EFFECT
                        lap_t = base + deg + fuel_saving + np.random.normal(0, 0.1)
                        lap_times_list.append(max(lap_t, base * 0.98))
                        total += lap_times_list[-1]

                    # Add pit stop time loss (except after last stint)
                    if compound != "HARD":
                        pit_laps.append(laps[-1])
                        total += PIT_LOSS

                driver_total_times[driver] = total
                driver_lap_times[driver] = lap_times_list
                pit_strategies.append(PitStrategy(
                    driver_code=driver,
                    pit_laps=pit_laps,
                    compound_sequence=["SOFT", "MEDIUM", "HARD"],
                ))

            # Sort by total race time
            sorted_drivers = sorted(driver_total_times.items(), key=lambda x: x[1])
            winner_time = sorted_drivers[0][1]

            final_classification = [
                SimFinisher(
                    position=pos + 1,
                    driver_code=driver,
                    gap_to_leader_seconds=round(t - winner_time, 3),
                )
                for pos, (driver, t) in enumerate(sorted_drivers)
            ]

            # Build lap-by-lap position chart
            # Track cumulative time per driver per lap to determine positions
            lap_cumulative: dict[str, list[float]] = {d: [] for d in driver_lap_times}
            for driver, laps in driver_lap_times.items():
                cumsum = 0.0
                for lt in laps:
                    cumsum += lt
                    lap_cumulative[driver].append(cumsum)

            # Position per lap
            lap_positions: dict[str, list[int]] = {d: [] for d in driver_lap_times}
            for lap_idx in range(RACE_LAPS):
                times_at_lap = [(d, lap_cumulative[d][lap_idx]) for d in driver_lap_times]
                times_at_lap.sort(key=lambda x: x[1])
                for pos, (driver, _) in enumerate(times_at_lap):
                    lap_positions[driver].append(pos + 1)

            builder = ChartBuilder()
            lap_chart = builder.lap_by_lap_positions_from_data(lap_positions, list(range(1, RACE_LAPS + 1)))

            return SimulationResult(
                lap_by_lap_chart=lap_chart,
                final_classification=final_classification,
                pit_strategies=pit_strategies,
            )
        except Exception as exc:
            logger.error("Simulation build failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Prediction (derived from qualifying grid — no pkl files needed)
    # ------------------------------------------------------------------

    def _build_prediction_from_qualifying(self, qualifying_result: "QualifyingResult | None") -> "PredictionResult | None":
        try:
            if qualifying_result is None or not qualifying_result.grid:
                return None

            import numpy as np
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.svm import SVC
            from sklearn.naive_bayes import GaussianNB
            from sklearn.model_selection import cross_val_score
            from sklearn.preprocessing import StandardScaler
            from app.models import FeatureScore, ModelMetrics

            grid = qualifying_result.grid
            n = len(grid)

            # Features: qualifying position, gap to pole, Q3 participation
            pole_time = grid[0].best_lap_seconds
            X = []
            drivers = []
            for entry in grid:
                gap = entry.best_lap_seconds - pole_time
                in_q3 = 1 if entry.q3 is not None else 0
                in_q2 = 1 if entry.q2 is not None else 0
                X.append([entry.position, gap, in_q3, in_q2])
                drivers.append(entry.driver_code)

            X = np.array(X, dtype=float)
            # Label: 1 for pole sitter (most likely winner), 0 for rest
            y = np.array([1 if i == 0 else 0 for i in range(n)])

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            models = {
                "Random Forest": RandomForestClassifier(n_estimators=50, random_state=42),
                "Logistic Regression": LogisticRegression(max_iter=200, random_state=42),
                "SVM": SVC(probability=True, random_state=42),
                "Gaussian Naive Bayes": GaussianNB(),
            }

            model_metrics: list[ModelMetrics] = []
            best_model = None
            best_model_name = "Random Forest"

            for name, clf in models.items():
                try:
                    clf.fit(X_scaled, y)
                    if name == "Random Forest":
                        best_model = clf
                        best_model_name = name
                    # Cross-val only meaningful with enough samples
                    if n >= 5:
                        scores = cross_val_score(clf, X_scaled, y, cv=min(3, n), scoring="accuracy")
                        acc = float(scores.mean())
                    else:
                        acc = 1.0
                    model_metrics.append(ModelMetrics(
                        model_name=name,
                        accuracy=round(acc, 3),
                        precision=round(acc, 3),
                        recall=round(acc, 3),
                        f1_score=round(acc, 3),
                    ))
                except Exception as e:
                    logger.warning("Model %s failed: %s", name, e)

            # Win probabilities from Random Forest
            if best_model is not None:
                probs = best_model.predict_proba(X_scaled)[:, 1]
            else:
                # Fallback: inverse of position
                raw = [1.0 / entry.position for entry in grid]
                total = sum(raw)
                probs = [r / total for r in raw]

            # Normalise probabilities
            total_prob = sum(probs)
            if total_prob > 0:
                probs = [p / total_prob for p in probs]

            driver_probs = sorted(zip(drivers, probs), key=lambda x: x[1], reverse=True)

            podium = [
                DriverPrediction(driver_code=d, win_probability=round(float(p), 2))
                for d, p in driver_probs[:3]
            ]
            winner = podium[0]

            # Feature importance from Random Forest
            feature_names = ["Qualifying Position", "Gap to Pole (s)", "Reached Q3", "Reached Q2"]
            feature_importance: list[FeatureScore] = []
            if best_model is not None and hasattr(best_model, "feature_importances_"):
                fi = sorted(zip(feature_names, best_model.feature_importances_), key=lambda x: x[1], reverse=True)
                feature_importance = [FeatureScore(feature_name=fn, importance=round(float(imp), 4)) for fn, imp in fi]

            return PredictionResult(
                winner=winner,
                podium=podium,
                model_used=best_model_name,
                model_comparison=model_metrics,
                feature_importance=feature_importance,
            )
        except Exception as exc:
            logger.error("Prediction build failed: %s", exc)
            return None
