"""FeatureEngineer: computes 11-feature vectors per driver per race."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.models import RaceSessionData

logger = logging.getLogger(__name__)

# The 13 feature columns in training order (added 2 new features)
FEATURE_COLUMNS = [
    "grid_position",
    "gap_to_pole_s",
    "q2_flag",
    "q3_flag",
    "fp2_median_laptime",
    "tyre_deg_rate",
    "driver_championship_pos",
    "constructor_championship_pos",
    "circuit_win_rate",
    "wet_flag",
    "home_race_flag",
    "constructor_rolling_podium_rate",  # NEW: constructor's podium rate over last 5 races
    "fp2_pace_rank",                    # NEW: driver's FP2 pace rank within the field (1=fastest)
]


class FeatureEngineer:
    def build_dataset(self, races: list[RaceSessionData]) -> pd.DataFrame:
        """Build a DataFrame with all 13 features per driver per race."""
        sorted_races = sorted(races, key=lambda r: (r.year, r.gp_slug))

        # history: {driver: {circuit: {'starts': int, 'top3': int}}}
        history: dict[str, dict[str, dict[str, int]]] = {}
        # constructor_history: {constructor: deque of last 5 race podium counts (0 or 1 per driver)}
        constructor_recent: dict[str, list[int]] = {}  # {constructor: [podium_count_per_race, ...]}

        all_rows: list[dict] = []

        for race in sorted_races:
            race_rows = self._build_race_rows(race, history, constructor_recent)
            all_rows.extend(race_rows)
            self._update_history(race, history)
            self._update_constructor_history(race, constructor_recent)

        if not all_rows:
            return pd.DataFrame(columns=FEATURE_COLUMNS + ["podium", "year", "gp_slug", "circuit_name", "driver_code"])

        return pd.DataFrame(all_rows)

    def _build_race_rows(self, race: RaceSessionData, history: dict, constructor_recent: dict | None = None) -> list[dict]:
        """Build feature vectors for all drivers in a race."""
        if race.qualifying_session is None:
            return []

        try:
            q_session = race.qualifying_session
            results = q_session.results
            if results is None or results.empty:
                return []
        except Exception as exc:
            logger.warning("Could not access qualifying results for %s: %s", race.gp_slug, exc)
            return []

        # Build a driver number → abbreviation map from laps if results have numbers not codes
        num_to_abbrev: dict[str, str] = {}
        try:
            laps = q_session.laps
            if laps is not None and not laps.empty and "Driver" in laps.columns and "DriverNumber" in laps.columns:
                for _, row in laps[["Driver", "DriverNumber"]].drop_duplicates().iterrows():
                    num_to_abbrev[str(row["DriverNumber"])] = str(row["Driver"])
        except Exception:
            pass

        # Normalise Abbreviation column — replace driver numbers with codes if needed
        if "Abbreviation" in results.columns:
            results = results.copy()
            results["Abbreviation"] = results["Abbreviation"].apply(
                lambda x: num_to_abbrev.get(str(x), str(x))
            )

        wet_flag = self._is_wet_session(q_session)

        # Get pole lap time
        try:
            laps = q_session.laps
            if laps is not None and not laps.empty:
                valid_laps = laps.pick_accurate()
                if not valid_laps.empty:
                    pole_lap_time = valid_laps["LapTime"].min().total_seconds()
                else:
                    pole_lap_time = None
            else:
                pole_lap_time = None
        except Exception:
            pole_lap_time = None

        # Fallback: use Q3/Q2/Q1 best from results
        if pole_lap_time is None:
            try:
                for col in ["Q3", "Q2", "Q1"]:
                    if col in results.columns:
                        valid = results[col].dropna()
                        if not valid.empty:
                            pole_lap_time = valid.min().total_seconds()
                            break
            except Exception:
                pass

        # Build per-driver FP2 data
        fp2_data: dict[str, tuple[float, float]] = {}
        if race.fp2_session is not None:
            for driver in results["Abbreviation"].tolist():
                try:
                    median_lt, deg_rate = self._compute_fp2_long_run(str(driver), race.fp2_session)
                    if median_lt is not None:
                        fp2_data[str(driver)] = (median_lt, deg_rate)
                except Exception:
                    pass

        # Impute missing FP2 values with race median
        fp2_medians = [v[0] for v in fp2_data.values() if v[0] is not None]
        fp2_deg_medians = [v[1] for v in fp2_data.values() if v[1] is not None]
        fp2_median_impute = float(np.median(fp2_medians)) if fp2_medians else 90.0
        fp2_deg_impute = float(np.median(fp2_deg_medians)) if fp2_deg_medians else 0.0

        # FP2 pace rank: rank drivers by median lap time (1 = fastest)
        fp2_pace_ranks: dict[str, int] = {}
        if fp2_data:
            sorted_by_pace = sorted(fp2_data.items(), key=lambda x: x[1][0])
            for rank, (driver, _) in enumerate(sorted_by_pace, start=1):
                fp2_pace_ranks[driver] = rank
        n_drivers = len(results)

        rows: list[dict] = []
        for _, driver_row in results.iterrows():
            try:
                driver = str(driver_row["Abbreviation"])
                # Constructor rolling podium rate
                constructor_rolling = 0.0
                if constructor_recent is not None:
                    try:
                        team = str(driver_row.get("TeamName", ""))
                        if team and team in constructor_recent:
                            recent = constructor_recent[team][-5:]  # last 5 races
                            constructor_rolling = sum(recent) / len(recent) if recent else 0.0
                    except Exception:
                        pass

                # FP2 pace rank (normalised 0-1, lower = better)
                fp2_rank = fp2_pace_ranks.get(driver, n_drivers)
                fp2_pace_rank_norm = fp2_rank / max(n_drivers, 1)

                vec = self._build_feature_vector(
                    driver=driver,
                    race=race,
                    history=history,
                    driver_row=driver_row,
                    pole_lap_time=pole_lap_time,
                    fp2_data=fp2_data,
                    fp2_median_impute=fp2_median_impute,
                    fp2_deg_impute=fp2_deg_impute,
                    wet_flag=wet_flag,
                    constructor_rolling_podium_rate=constructor_rolling,
                    fp2_pace_rank=fp2_pace_rank_norm,
                )
                if vec is not None:
                    rows.append(vec)
            except Exception as exc:
                logger.warning("Could not build feature vector for driver %s in %s: %s",
                               driver_row.get("Abbreviation"), race.gp_slug, exc)

        return rows

    def _build_feature_vector(
        self,
        driver: str,
        race: RaceSessionData,
        history: dict,
        driver_row: Any,
        pole_lap_time: float | None,
        fp2_data: dict,
        fp2_median_impute: float,
        fp2_deg_impute: float,
        wet_flag: int,
        constructor_rolling_podium_rate: float = 0.0,
        fp2_pace_rank: float = 1.0,
    ) -> dict | None:
        """Build a single feature vector dict for one driver in one race."""
        try:
            # 1. grid_position
            try:
                gp_val = driver_row.get("GridPosition")
                import math
                if gp_val is None or (isinstance(gp_val, float) and math.isnan(gp_val)):
                    grid_pos = 20
                else:
                    grid_pos = int(float(gp_val))
                    if grid_pos <= 0:
                        grid_pos = 20
            except Exception:
                grid_pos = 20

            # 2. gap_to_pole_s — best lap minus pole lap
            gap_to_pole = 0.0
            try:
                best_lap = None
                for col in ["Q3", "Q2", "Q1"]:
                    val = driver_row.get(col)
                    if val is not None and str(val) not in ("nan", "NaT", "None"):
                        try:
                            best_lap = pd.Timedelta(val).total_seconds()
                            break
                        except Exception:
                            pass
                if best_lap is not None and pole_lap_time is not None:
                    gap_to_pole = max(0.0, best_lap - pole_lap_time)
            except Exception:
                pass

            # 3. q2_flag
            q2_flag = 0
            try:
                q2_val = driver_row.get("Q2")
                if q2_val is not None and str(q2_val) not in ("nan", "NaT", "None"):
                    q2_flag = 1
            except Exception:
                pass

            # 4. q3_flag
            q3_flag = 0
            try:
                q3_val = driver_row.get("Q3")
                if q3_val is not None and str(q3_val) not in ("nan", "NaT", "None"):
                    q3_flag = 1
            except Exception:
                pass

            # 5 & 6. fp2_median_laptime and tyre_deg_rate
            if driver in fp2_data:
                fp2_median_laptime, tyre_deg_rate = fp2_data[driver]
            else:
                fp2_median_laptime = fp2_median_impute
                tyre_deg_rate = fp2_deg_impute

            # 7. driver_championship_pos
            driver_champ_pos = 20
            try:
                pos = driver_row.get("Position")
                if pos is not None and str(pos) not in ("nan", "None", "NaT"):
                    pos_f = float(pos)
                    import math
                    if not math.isnan(pos_f):
                        driver_champ_pos = int(pos_f)
            except Exception:
                pass

            # 8. constructor_championship_pos
            constructor_champ_pos = 10
            try:
                team_order = self._get_constructor_order(race)
                team = str(driver_row.get("TeamName", ""))
                if team and team in team_order:
                    constructor_champ_pos = team_order[team]
            except Exception:
                pass

            # 9. circuit_win_rate
            circuit_win_rate = self._compute_circuit_win_rate(
                driver, race.circuit_name, race.year, history
            )

            # 10. wet_flag (already computed for the whole session)

            # 11. home_race_flag
            home_race_flag = self._compute_home_race_flag(driver, driver_row, race)

            # Target: podium
            podium: int | None = None
            if race.actual_top3:
                podium = 1 if driver in race.actual_top3 else 0

            return {
                "driver_code": driver,
                "year": race.year,
                "gp_slug": race.gp_slug,
                "circuit_name": race.circuit_name,
                "grid_position": grid_pos,
                "gap_to_pole_s": round(gap_to_pole, 4),
                "q2_flag": q2_flag,
                "q3_flag": q3_flag,
                "fp2_median_laptime": round(fp2_median_laptime, 4),
                "tyre_deg_rate": round(tyre_deg_rate, 6),
                "driver_championship_pos": driver_champ_pos,
                "constructor_championship_pos": constructor_champ_pos,
                "circuit_win_rate": round(circuit_win_rate, 4),
                "wet_flag": wet_flag,
                "home_race_flag": home_race_flag,
                "constructor_rolling_podium_rate": round(constructor_rolling_podium_rate, 4),
                "fp2_pace_rank": round(fp2_pace_rank, 4),
                "podium": podium,
            }
        except Exception as exc:
            logger.warning("Feature vector build error for %s: %s", driver, exc)
            return None

    def _compute_fp2_long_run(self, driver: str, fp2_session: Any) -> tuple[float, float]:
        """Compute median lap time and tyre degradation rate from FP2 long runs.

        Returns (median_laptime_seconds, deg_rate_seconds_per_lap).
        """
        try:
            laps = fp2_session.laps
            if laps is None or laps.empty:
                return (90.0, 0.0)

            driver_laps = laps.pick_drivers(driver).pick_accurate().pick_wo_box()
            if driver_laps.empty:
                return (90.0, 0.0)

            # Convert lap times to seconds
            lap_times = driver_laps["LapTime"].dropna()
            if lap_times.empty:
                return (90.0, 0.0)

            lap_times_s = lap_times.apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") else float(t))
            median_lt = float(lap_times_s.median())

            # Tyre deg rate: linear regression of lap time vs tyre life
            tyre_life = driver_laps["TyreLife"].dropna()
            if len(tyre_life) >= 2 and len(lap_times_s) == len(tyre_life):
                coeffs = np.polyfit(tyre_life.values.astype(float), lap_times_s.values, 1)
                deg_rate = float(coeffs[0])
            else:
                deg_rate = 0.0

            return (median_lt, deg_rate)
        except Exception as exc:
            logger.warning("FP2 long run computation failed for %s: %s", driver, exc)
            return (90.0, 0.0)

    def _compute_circuit_win_rate(
        self, driver: str, circuit: str, year: int, history: dict
    ) -> float:
        """Compute driver's top-3 rate at this circuit in prior seasons."""
        driver_history = history.get(driver, {})
        circuit_history = driver_history.get(circuit, {})
        starts = circuit_history.get("starts", 0)
        top3 = circuit_history.get("top3", 0)
        if starts == 0:
            return 0.0
        return top3 / starts

    def _is_wet_session(self, qualifying_session: Any) -> int:
        """Return 1 if any INTERMEDIATE or WET compound was used in qualifying."""
        try:
            laps = qualifying_session.laps
            if laps is None or laps.empty:
                return 0
            compounds = laps["Compound"].dropna().str.upper()
            if compounds.isin(["INTERMEDIATE", "WET"]).any():
                return 1
        except Exception:
            pass
        return 0

    def _compute_home_race_flag(self, driver: str, driver_row: Any, race: RaceSessionData) -> int:
        """Return 1 if driver nationality matches circuit country."""
        try:
            driver_nationality = str(driver_row.get("CountryCode", "") or "")
            circuit_country = str(race.circuit_name or "")

            # Try to get country from qualifying session driver info
            if hasattr(race.qualifying_session, "get_driver"):
                try:
                    driver_info = race.qualifying_session.get_driver(driver)
                    if driver_info is not None:
                        driver_nationality = str(driver_info.get("CountryCode", driver_nationality) or driver_nationality)
                except Exception:
                    pass

            # Simple nationality-to-country mapping
            nationality_country_map = {
                "NED": ["Netherlands", "Dutch", "Zandvoort"],
                "GBR": ["Great Britain", "British", "Silverstone", "United Kingdom"],
                "GER": ["Germany", "German", "Nürburgring", "Hockenheim"],
                "FRA": ["France", "French", "Paul Ricard"],
                "ESP": ["Spain", "Spanish", "Barcelona", "Catalunya"],
                "MON": ["Monaco", "Monte Carlo"],
                "FIN": ["Finland", "Finnish"],
                "AUS": ["Australia", "Australian", "Melbourne"],
                "CAN": ["Canada", "Canadian", "Montreal"],
                "MEX": ["Mexico", "Mexican", "Mexico City"],
                "BRA": ["Brazil", "Brazilian", "São Paulo", "Sao Paulo", "Interlagos"],
                "JPN": ["Japan", "Japanese", "Suzuka"],
                "CHN": ["China", "Chinese", "Shanghai"],
                "ITA": ["Italy", "Italian", "Monza", "Imola"],
                "BEL": ["Belgium", "Belgian", "Spa"],
                "AUT": ["Austria", "Austrian", "Spielberg", "Red Bull Ring"],
                "HUN": ["Hungary", "Hungarian", "Budapest"],
                "USA": ["United States", "American", "Austin", "Miami", "Las Vegas"],
                "THA": ["Thailand", "Thai"],
                "DNK": ["Denmark", "Danish"],
            }

            for nat_code, countries in nationality_country_map.items():
                if driver_nationality.upper() == nat_code:
                    for country in countries:
                        if country.lower() in circuit_country.lower():
                            return 1
        except Exception:
            pass
        return 0

    def _get_constructor_order(self, race: RaceSessionData) -> dict[str, int]:
        """Build a team → championship position mapping from race results."""
        try:
            results = race.race_session.results if race.race_session else None
            if results is None or results.empty:
                return {}

            # Group by team and sum points to get rough constructor order
            team_points: dict[str, float] = {}
            for _, row in results.iterrows():
                team = str(row.get("TeamName", ""))
                points = float(row.get("Points", 0) or 0)
                if team:
                    team_points[team] = team_points.get(team, 0) + points

            sorted_teams = sorted(team_points.items(), key=lambda x: x[1], reverse=True)
            return {team: pos + 1 for pos, (team, _) in enumerate(sorted_teams)}
        except Exception:
            return {}

    def _update_history(self, race: RaceSessionData, history: dict) -> None:
        """Update history dict with results from this race."""
        if not race.qualifying_session:
            return

        try:
            results = race.qualifying_session.results
            if results is None or results.empty:
                return

            for _, row in results.iterrows():
                driver = str(row["Abbreviation"])
                circuit = race.circuit_name

                if driver not in history:
                    history[driver] = {}
                if circuit not in history[driver]:
                    history[driver][circuit] = {"starts": 0, "top3": 0}

                history[driver][circuit]["starts"] += 1
                if driver in race.actual_top3:
                    history[driver][circuit]["top3"] += 1
        except Exception as exc:
            logger.warning("Could not update history for %s: %s", race.gp_slug, exc)

    def _update_constructor_history(self, race: RaceSessionData, constructor_recent: dict) -> None:
        """Update constructor rolling podium history after each race."""
        if not race.actual_top3:
            return
        try:
            results = race.qualifying_session.results if race.qualifying_session else None
            if results is None or results.empty:
                return

            # Count podiums per constructor in this race
            constructor_podiums: dict[str, int] = {}
            for _, row in results.iterrows():
                driver = str(row["Abbreviation"])
                team = str(row.get("TeamName", ""))
                if not team or team in ("nan", "None"):
                    continue
                if team not in constructor_podiums:
                    constructor_podiums[team] = 0
                if driver in race.actual_top3:
                    constructor_podiums[team] += 1

            # Append to rolling history (keep last 10 races)
            for team, podium_count in constructor_podiums.items():
                if team not in constructor_recent:
                    constructor_recent[team] = []
                # Store fraction of drivers on podium (0, 0.5, or 1.0 for 2-driver teams)
                constructor_recent[team].append(min(podium_count / 2.0, 1.0))
                if len(constructor_recent[team]) > 10:
                    constructor_recent[team] = constructor_recent[team][-10:]
        except Exception as exc:
            logger.warning("Could not update constructor history for %s: %s", race.gp_slug, exc)
