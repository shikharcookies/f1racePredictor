"""FastAPI route handlers for the F1 Prediction Dashboard API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models import DriverStats, DriverStatsResult, GPResult

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level reference to the PipelineCache instance.
# Set by app/main.py after startup before requests are served.
pipeline_cache = None  # type: Any  # PipelineCache

# Multi-year pipeline references — injected by app/main.py at startup.
multi_year_cache = None  # type: Any  # MultiYearCache
cross_race_model_ref = None  # type: Any  # CrossRaceModel
feature_engineer_ref = None  # type: Any  # FeatureEngineer


def _get_gp_or_404(gp_slug: str) -> GPResult:
    """Retrieve a GPResult from the cache or raise 404."""
    result = pipeline_cache.get(gp_slug)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No cached data found for grand prix: {gp_slug}",
            },
        )
    return result


@router.get("/grand-prix")
def list_grand_prix() -> list[dict]:
    """Return all available Grand Prix slugs and display names."""
    slugs = pipeline_cache.list_slugs()
    result = []
    for slug in slugs:
        gp = pipeline_cache.get(slug)
        display_name = gp.display_name if gp else slug
        result.append({"slug": slug, "display_name": display_name})
    return result


@router.get("/grand-prix/{gp_slug}")
def get_grand_prix(gp_slug: str) -> dict:
    """Return the full GPResult JSON for a given GP slug."""
    gp = _get_gp_or_404(gp_slug)
    return gp.model_dump()


@router.get("/grand-prix/{gp_slug}/prediction")
def get_prediction(gp_slug: str) -> dict:
    """Return the PredictionResult for a given GP slug."""
    gp = _get_gp_or_404(gp_slug)
    if gp.prediction is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No cached data found for grand prix: {gp_slug}",
            },
        )
    return gp.prediction.model_dump()


@router.get("/grand-prix/{gp_slug}/practice")
def get_practice(gp_slug: str) -> dict:
    """Return the PracticeResult for a given GP slug."""
    gp = _get_gp_or_404(gp_slug)
    if gp.practice is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No cached data found for grand prix: {gp_slug}",
            },
        )
    return gp.practice.model_dump()


@router.get("/grand-prix/{gp_slug}/qualifying")
def get_qualifying(gp_slug: str) -> dict:
    """Return the QualifyingResult for a given GP slug."""
    gp = _get_gp_or_404(gp_slug)
    if gp.qualifying is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No cached data found for grand prix: {gp_slug}",
            },
        )
    return gp.qualifying.model_dump()


@router.get("/grand-prix/{gp_slug}/simulation")
def get_simulation(gp_slug: str) -> dict:
    """Return the SimulationResult for a given GP slug."""
    gp = _get_gp_or_404(gp_slug)
    if gp.simulation is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No cached data found for grand prix: {gp_slug}",
            },
        )
    return gp.simulation.model_dump()


@router.get("/drivers")
def get_drivers() -> dict:
    """Return aggregated DriverStatsResult across all cached GPs."""
    slugs = pipeline_cache.list_slugs()

    # driver_code -> {compound -> [avg_times], total_laps, appearances}
    driver_data: dict[str, dict] = {}

    for slug in slugs:
        gp = pipeline_cache.get(slug)
        if gp is None:
            continue

        # Collect driver codes from qualifying
        if gp.qualifying and gp.qualifying.grid:
            for entry in gp.qualifying.grid:
                code = entry.driver_code
                if code not in driver_data:
                    driver_data[code] = {
                        "soft": [], "medium": [], "hard": [],
                        "total_laps": 0, "appearances": 0,
                    }
                driver_data[code]["appearances"] += 1

        # Collect lap time averages from FP2 raw data
        if gp.practice and gp.practice.raw_fp2_df:
            for row in gp.practice.raw_fp2_df:
                code = row.get("Driver")
                if not code or code not in driver_data:
                    continue
                compound = str(row.get("Compound", "")).upper()
                lap_time = row.get("LapTime")
                lap_numbers = row.get("LapNumbers", [])
                if lap_time and isinstance(lap_time, (int, float)):
                    if compound == "SOFT":
                        driver_data[code]["soft"].append(float(lap_time))
                    elif compound == "MEDIUM":
                        driver_data[code]["medium"].append(float(lap_time))
                    elif compound == "HARD":
                        driver_data[code]["hard"].append(float(lap_time))
                if isinstance(lap_numbers, list):
                    driver_data[code]["total_laps"] += len(lap_numbers)

    # Home race advantage: drivers racing in their home country
    # Based on 2022 calendar nationality mapping
    home_drivers = {"VER": "Dutch", "HAM": "British", "RUS": "British",
                    "LEC": "Monaco", "SAI": "Spanish", "ALO": "Spanish",
                    "GAS": "French", "OCO": "French", "MSC": "German",
                    "VET": "German", "BOT": "Finnish", "ZHO": "Chinese",
                    "TSU": "Japanese", "NOR": "British", "RIC": "Australian",
                    "STR": "Canadian", "LAT": "Canadian", "ALB": "Thai",
                    "MAG": "Danish", "PER": "Mexican"}

    drivers_list = []
    for code, data in sorted(driver_data.items()):
        soft_times = data["soft"]
        medium_times = data["medium"]
        hard_times = data["hard"]
        all_times = soft_times + medium_times + hard_times

        drivers_list.append(DriverStats(
            driver_code=code,
            soft_avg_time_rep=round(sum(soft_times) / len(soft_times), 3) if soft_times else None,
            medium_avg_time_rep=round(sum(medium_times) / len(medium_times), 3) if medium_times else None,
            hard_avg_time_rep=round(sum(hard_times) / len(hard_times), 3) if hard_times else None,
            total_avg_time_rep=round(sum(all_times) / len(all_times), 3) if all_times else None,
            total_laps_rep=data["total_laps"],
            dnf_index=0.0,
            home_race_advantage=code in home_drivers,
        ))

    return DriverStatsResult(drivers=drivers_list).model_dump()


# ---------------------------------------------------------------------------
# Multi-year prediction endpoints
# ---------------------------------------------------------------------------

def _build_historical_fallback_vectors(year: int, gp_slug: str, circuit_name: str) -> list[dict]:
    """Build prediction vectors using only historical features when qualifying isn't available yet."""
    from app.pipeline.feature_engineer import FEATURE_COLUMNS

    # Current 2026 driver lineup with approximate championship positions
    # Based on 2025 season results as prior
    drivers = [
        {"code": "NOR", "champ_pos": 1, "constructor": "McLaren", "constructor_pos": 1},
        {"code": "PIA", "champ_pos": 2, "constructor": "McLaren", "constructor_pos": 1},
        {"code": "LEC", "champ_pos": 3, "constructor": "Ferrari", "constructor_pos": 2},
        {"code": "ANT", "champ_pos": 4, "constructor": "Mercedes", "constructor_pos": 3},
        {"code": "RUS", "champ_pos": 5, "constructor": "Mercedes", "constructor_pos": 3},
        {"code": "VER", "champ_pos": 6, "constructor": "Red Bull", "constructor_pos": 4},
        {"code": "HAM", "champ_pos": 7, "constructor": "Ferrari", "constructor_pos": 2},
        {"code": "ALO", "champ_pos": 8, "constructor": "Aston Martin", "constructor_pos": 5},
        {"code": "STR", "champ_pos": 9, "constructor": "Aston Martin", "constructor_pos": 5},
        {"code": "GAS", "champ_pos": 10, "constructor": "Alpine", "constructor_pos": 6},
        {"code": "OCO", "champ_pos": 11, "constructor": "Haas", "constructor_pos": 7},
        {"code": "HUL", "champ_pos": 12, "constructor": "Sauber", "constructor_pos": 8},
        {"code": "BOT", "champ_pos": 13, "constructor": "Sauber", "constructor_pos": 8},
        {"code": "TSU", "champ_pos": 14, "constructor": "Red Bull", "constructor_pos": 4},
        {"code": "LAW", "champ_pos": 15, "constructor": "Racing Bulls", "constructor_pos": 9},
        {"code": "ALB", "champ_pos": 16, "constructor": "Williams", "constructor_pos": 10},
        {"code": "SAI", "champ_pos": 17, "constructor": "Williams", "constructor_pos": 10},
        {"code": "BOR", "champ_pos": 18, "constructor": "Alpine", "constructor_pos": 6},
        {"code": "COL", "champ_pos": 19, "constructor": "Haas", "constructor_pos": 7},
        {"code": "DOO", "champ_pos": 20, "constructor": "Racing Bulls", "constructor_pos": 9},
    ]

    rows = []
    n = len(drivers)
    for i, d in enumerate(drivers):
        rows.append({
            "driver_code": d["code"],
            "year": year,
            "gp_slug": gp_slug,
            "circuit_name": circuit_name,
            "grid_position": d["champ_pos"],          # use champ pos as proxy
            "gap_to_pole_s": (d["champ_pos"] - 1) * 0.1,
            "q2_flag": 1 if d["champ_pos"] <= 15 else 0,
            "q3_flag": 1 if d["champ_pos"] <= 10 else 0,
            "fp2_median_laptime": 90.0,               # neutral imputed value
            "tyre_deg_rate": 0.0,
            "driver_championship_pos": d["champ_pos"],
            "constructor_championship_pos": d["constructor_pos"],
            "circuit_win_rate": 0.0,                  # no prior data for this circuit yet
            "wet_flag": 0,
            "home_race_flag": 0,
            "constructor_rolling_podium_rate": max(0.0, (10 - d["constructor_pos"]) / 10),
            "fp2_pace_rank": (i + 1) / n,
            "actual_podium": None,
        })
    return rows


def _require_multi_year_cache():
    """Raise 503 if multi_year_cache is not available."""
    if multi_year_cache is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "MODEL_NOT_READY",
                "message": "Multi-year pipeline has not completed startup yet.",
            },
        )


def _require_trained_model():
    """Raise 503 if the cross-race model is not trained."""
    _require_multi_year_cache()
    if cross_race_model_ref is None or not cross_race_model_ref.is_trained():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "MODEL_NOT_READY",
                "message": "Cross-race model is not yet trained.",
            },
        )


@router.get("/seasons")
def list_seasons() -> dict:
    """Return all available seasons and their GP events."""
    _require_multi_year_cache()
    seasons_raw = multi_year_cache.get_seasons()
    # Convert to JSON-serialisable dict keyed by year (as string for JSON)
    return {
        "seasons": {
            str(year): [event.model_dump() for event in events]
            for year, events in seasons_raw.items()
        }
    }


@router.get("/seasons/{year}/grand-prix")
def list_season_grand_prix(year: int) -> list[dict]:
    """Return GP list for a specific year; 404 if year unknown."""
    _require_multi_year_cache()
    events = multi_year_cache.get_season(year)
    if events is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No data found for season year: {year}",
            },
        )
    return [event.model_dump() for event in events]


@router.get("/seasons/{year}/grand-prix/{gp_slug}/prediction")
def get_multi_year_prediction(year: int, gp_slug: str) -> dict:
    """Return cross-race podium predictions for a specific GP."""
    _require_trained_model()

    # Look up the SeasonEvent
    season_event = multi_year_cache.get_event(year, gp_slug)
    if season_event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No data found for {year} / {gp_slug}",
            },
        )

    # Get raw race session data
    race = multi_year_cache.get_race_data(year, gp_slug)
    if race is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": f"No race session data found for {year} / {gp_slug}",
            },
        )

    try:
        # Build feature vectors for all drivers in this race
        history: dict = {}
        race_rows = feature_engineer_ref._build_race_rows(race, history)

        if not race_rows:
            # No qualifying data yet — build historical-only prediction using known 2026 driver lineup
            logger.info("No qualifying data for %s/%s — using historical fallback prediction", year, gp_slug)
            race_rows = _build_historical_fallback_vectors(year, gp_slug, race.circuit_name)

        if not race_rows:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"No data available for {year} / {gp_slug}.",
                },
            )

        # Attach actual_podium flag to each vector
        for vec in race_rows:
            driver = vec.get("driver_code", "")
            vec["actual_podium"] = (driver in race.actual_top3) if race.actual_top3 else None

        predictions = cross_race_model_ref.predict_race(race_rows)

        return {
            "gp_slug": gp_slug,
            "display_name": season_event.display_name,
            "is_test_set": season_event.is_test_set,
            "has_actual_result": season_event.has_actual_result,
            "predictions": [p.model_dump() for p in predictions],
            "actual_top3": race.actual_top3,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Prediction endpoint error for %s/%s: %s", year, gp_slug, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PIPELINE_ERROR",
                "message": "An error occurred while generating predictions.",
                "detail": str(exc),
            },
        )


@router.get("/seasons/{year}/grand-prix/{gp_slug}/session-data")
def get_session_data(year: int, gp_slug: str) -> dict:
    """Return qualifying grid and practice data for any year's GP from multi-year cache."""
    _require_multi_year_cache()

    race = multi_year_cache.get_race_data(year, gp_slug)
    if race is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"No session data for {year}/{gp_slug}"},
        )

    try:
        from app.pipeline.feature_engineer import FeatureEngineer
        from app.models import QualifyingResult, GridEntry, PracticeResult
        from app.charts.builder import ChartBuilder
        from constants import TEAMMATE_PAIRS_DICT
        import math

        qualifying_result = None
        practice_result = None

        # Build qualifying grid
        if race.qualifying_session is not None:
            try:
                q_session = race.qualifying_session
                laps = q_session.laps

                # Build number→abbreviation map from laps
                num_to_abbrev: dict[str, str] = {}
                if laps is not None and not laps.empty and "Driver" in laps.columns and "DriverNumber" in laps.columns:
                    for _, row in laps[["Driver", "DriverNumber"]].drop_duplicates().iterrows():
                        num_to_abbrev[str(row["DriverNumber"])] = str(row["Driver"])

                # Build best lap per driver from laps (Q1/Q2/Q3 compound filter)
                if laps is not None and not laps.empty:
                    import pandas as pd
                    best_laps: dict[str, float] = {}
                    q_times: dict[str, dict[str, float | None]] = {}

                    for driver_num in laps["DriverNumber"].unique():
                        driver_laps = laps[laps["DriverNumber"] == driver_num]
                        driver_code = num_to_abbrev.get(str(driver_num), str(driver_num))
                        q_times[driver_code] = {"Q1": None, "Q2": None, "Q3": None}

                        for q_session_name in ["Q1", "Q2", "Q3"]:
                            try:
                                q_laps = driver_laps[driver_laps.get("Session", pd.Series()) == q_session_name] if "Session" in driver_laps.columns else pd.DataFrame()
                                if q_laps.empty:
                                    # Fall back: use all laps and pick best
                                    q_laps = driver_laps
                                valid = q_laps["LapTime"].dropna()
                                if not valid.empty:
                                    best_t = valid.min()
                                    if hasattr(best_t, "total_seconds"):
                                        best_t = best_t.total_seconds()
                                    q_times[driver_code][q_session_name] = round(float(best_t), 3)
                            except Exception:
                                pass

                        # Overall best
                        all_valid = driver_laps["LapTime"].dropna()
                        if not all_valid.empty:
                            best = all_valid.min()
                            if hasattr(best, "total_seconds"):
                                best = best.total_seconds()
                            best_laps[driver_code] = round(float(best), 3)

                    if best_laps:
                        sorted_drivers = sorted(best_laps.items(), key=lambda x: x[1])
                        grid = []
                        for pos, (driver_code, best_t) in enumerate(sorted_drivers, start=1):
                            grid.append(GridEntry(
                                position=pos,
                                driver_code=driver_code,
                                best_lap_seconds=best_t,
                                q1=q_times.get(driver_code, {}).get("Q1"),
                                q2=q_times.get(driver_code, {}).get("Q2"),
                                q3=q_times.get(driver_code, {}).get("Q3"),
                            ))

                        if grid:
                            builder = ChartBuilder()
                            gap_chart = builder.qualifying_gap_to_pole([e.model_dump() for e in grid])
                            teammate_chart = builder.teammate_comparison([e.model_dump() for e in grid], TEAMMATE_PAIRS_DICT)
                            qualifying_result = QualifyingResult(
                                grid=grid,
                                gap_to_pole_chart=gap_chart,
                                teammate_comparison_chart=teammate_chart,
                            )
            except Exception as exc:
                logger.warning("Could not build qualifying for %s/%s: %s", year, gp_slug, exc)

        # Build practice data
        if race.fp2_session is not None:
            try:
                from race import convert_laptime_to_seconds
                import numpy as np
                laps = race.fp2_session.laps
                if laps is not None and not laps.empty:
                    laps = laps.pick_accurate().pick_wo_box().copy()
                    convert_laptime_to_seconds(laps)
                    drivers_list = laps["Driver"].unique().tolist()
                    raw_rows = []
                    for driver in drivers_list:
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
                    if raw_rows:
                        builder = ChartBuilder()
                        practice_result = PracticeResult(
                            lap_time_chart=builder.lap_time_distribution(raw_rows),
                            stint_analysis_chart=builder.stint_analysis(raw_rows),
                            raw_fp2_df=raw_rows,
                        )
            except Exception as exc:
                logger.warning("Could not build practice for %s/%s: %s", year, gp_slug, exc)

        return {
            "gp_slug": gp_slug,
            "year": year,
            "qualifying": qualifying_result.model_dump() if qualifying_result else None,
            "practice": practice_result.model_dump() if practice_result else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Session data endpoint error for %s/%s: %s", year, gp_slug, exc)
        raise HTTPException(status_code=500, detail={"error": "PIPELINE_ERROR", "message": str(exc)})


@router.get("/model/metrics")
def get_model_metrics() -> dict:
    """Return cross-race model test-set metrics; 503 if not trained."""
    _require_trained_model()
    metrics = cross_race_model_ref.get_metrics()
    if metrics is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "MODEL_NOT_READY",
                "message": "Model metrics are not available yet.",
            },
        )
    return metrics.model_dump()


@router.get("/model/circuit-accuracy")
def get_circuit_accuracy() -> list[dict]:
    """Return per-circuit precision/recall; 503 if not trained."""
    _require_trained_model()
    circuit_accuracy = cross_race_model_ref.get_circuit_accuracy()
    return [ca.model_dump() for ca in circuit_accuracy]
