"""MultiYearLoader: loads FastF1 session data across multiple seasons."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

# Make workspace root importable so existing modules are accessible.
_WORKSPACE_ROOT = str(Path(__file__).resolve().parents[2])
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

import fastf1  # noqa: E402

from app.models import RaceSessionData  # noqa: E402

logger = logging.getLogger(__name__)

# Enable FastF1 cache
fastf1.Cache.enable_cache(str(Path(_WORKSPACE_ROOT) / "cache"))


class MultiYearLoader:
    SEASONS: list[int] = [2022, 2023, 2024, 2025]

    def _get_seasons(self) -> list[int]:
        seasons = list(self.SEASONS)
        current_year = date.today().year
        if current_year > 2025 and current_year not in seasons:
            seasons.append(current_year)
        return seasons

    def load_all_seasons(self) -> list[RaceSessionData]:
        """Load all races across all configured seasons."""
        all_races: list[RaceSessionData] = []
        for year in self._get_seasons():
            try:
                races = self.load_season(year)
                all_races.extend(races)
                logger.info("Loaded %d races for season %d", len(races), year)
            except Exception as exc:
                logger.warning("Failed to load season %d: %s", year, exc)
        return all_races

    def load_season(self, year: int) -> list[RaceSessionData]:
        """Load all completed races + the next upcoming race for a given season year."""
        races: list[RaceSessionData] = []
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as exc:
            logger.warning("Could not get event schedule for %d: %s — trying cache discovery", year, exc)
            return self._load_season_from_cache(year)

        today = date.today()
        upcoming_added = False  # only add the very next upcoming race

        # Sort by event date so we process in order
        try:
            schedule = schedule.sort_values("EventDate")
        except Exception:
            pass

        for _, event in schedule.iterrows():
            try:
                event_date = event["EventDate"]
                if hasattr(event_date, "date"):
                    event_date = event_date.date()

                event_name = str(event["EventName"])
                circuit_name = str(event.get("Location", event_name))

                if event_date < today:
                    # Completed race — load normally
                    race = self._load_race(year, event_name, circuit_name)
                    if race is not None:
                        races.append(race)
                elif not upcoming_added:
                    # Next upcoming race — load qualifying only (no race results yet)
                    race = self._load_upcoming_race(year, event_name, circuit_name)
                    if race is not None:
                        races.append(race)
                        upcoming_added = True
            except Exception as exc:
                logger.warning("Failed to process event in %d: %s", year, exc)

        return races

    def _load_upcoming_race(self, year: int, event_name: str, circuit_name: str) -> "RaceSessionData | None":
        """Load an upcoming race — qualifying and FP2 only, no race results."""
        try:
            # Build a slug using the scheduled race date from the event schedule
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            event_row = schedule[schedule["EventName"] == event_name]
            if event_row.empty:
                return None

            event_date = event_row.iloc[0]["EventDate"]
            if hasattr(event_date, "date"):
                event_date = event_date.date()
            date_str = event_date.strftime("%Y-%m-%d")
            slug_name = event_name.replace(" ", "_")
            gp_slug = f"{date_str}_{slug_name}"

            # Load qualifying session (may not exist yet if race weekend hasn't started)
            qualifying_session = None
            try:
                qualifying_session = fastf1.get_session(year, event_name, "Q")
                qualifying_session.load(laps=True, telemetry=False, weather=False, messages=False)
                logger.info("Loaded qualifying for upcoming race: %s %d", event_name, year)
            except Exception as exc:
                logger.warning("Could not load qualifying for upcoming %s %d: %s", event_name, year, exc)

            # Load FP2 session
            fp2_session = None
            try:
                fp2_session = fastf1.get_session(year, event_name, "FP2")
                fp2_session.load(laps=True, telemetry=False, weather=False, messages=False)
            except Exception as exc:
                logger.warning("Could not load FP2 for upcoming %s %d: %s", event_name, year, exc)

            if qualifying_session is None and fp2_session is None:
                logger.info("No session data available yet for upcoming race %s %d — skipping", event_name, year)
                return None

            return RaceSessionData(
                year=year,
                gp_slug=gp_slug,
                event_name=event_name,
                circuit_name=circuit_name,
                qualifying_session=qualifying_session,
                fp2_session=fp2_session,
                race_session=None,
                actual_top3=[],  # No results yet
            )
        except Exception as exc:
            logger.warning("Could not load upcoming race %s %d: %s", event_name, year, exc)
            return None

    def _load_season_from_cache(self, year: int) -> list[RaceSessionData]:
        """Discover and load races from local cache directory when API is unavailable."""
        races: list[RaceSessionData] = []
        cache_year_dir = Path(_WORKSPACE_ROOT) / "cache" / str(year)
        if not cache_year_dir.exists():
            logger.warning("No cache directory found for year %d", year)
            return races

        for gp_dir in sorted(cache_year_dir.iterdir()):
            if not gp_dir.is_dir():
                continue
            try:
                # Parse event name from directory name e.g. "2024-03-02_Bahrain_Grand_Prix"
                dir_name = gp_dir.name
                parts = dir_name.split("_", 1)
                if len(parts) < 2:
                    continue
                event_name = parts[1].replace("_", " ")
                circuit_name = event_name

                race = self._load_race(year, event_name, circuit_name)
                if race is not None:
                    races.append(race)
            except Exception as exc:
                logger.warning("Failed to load cached race %s: %s", gp_dir.name, exc)

        return races

    def _load_race(self, year: int, event_name: str, circuit_name: str) -> RaceSessionData | None:
        """Load Q, FP2, and R sessions for a single race. Returns None on any failure."""
        try:
            # Build gp_slug from race session date
            race_session_obj = fastf1.get_session(year, event_name, "R")
            race_session_obj.load(laps=False, telemetry=False, weather=False, messages=False)

            race_date = race_session_obj.date
            if hasattr(race_date, "date"):
                race_date = race_date.date()
            date_str = race_date.strftime("%Y-%m-%d")
            slug_name = event_name.replace(" ", "_")
            gp_slug = f"{date_str}_{slug_name}"

            # Extract actual top 3 finishers from race results
            actual_top3: list[str] = []
            try:
                # Load race laps — use final lap position to determine finishing order
                race_session_laps = fastf1.get_session(year, event_name, "R")
                race_session_laps.load(laps=True, telemetry=False, weather=False, messages=False)

                rlaps = race_session_laps.laps
                if rlaps is not None and not rlaps.empty:
                    # Build number→abbreviation map
                    num_to_abbrev: dict[str, str] = {}
                    if "Driver" in rlaps.columns and "DriverNumber" in rlaps.columns:
                        for _, row in rlaps[["Driver", "DriverNumber"]].drop_duplicates().iterrows():
                            num_to_abbrev[str(row["DriverNumber"])] = str(row["Driver"])

                    # Get finishing order from the LAST lap each driver completed
                    # Position on the final lap = finishing position
                    if "Position" in rlaps.columns and "LapNumber" in rlaps.columns:
                        # Get each driver's last lap
                        last_lap_per_driver = (
                            rlaps.sort_values("LapNumber")
                            .groupby("Driver")
                            .last()
                            .reset_index()
                        )
                        last_lap_per_driver = last_lap_per_driver.dropna(subset=["Position"])
                        last_lap_per_driver["Position"] = last_lap_per_driver["Position"].astype(float)
                        top3_rows = last_lap_per_driver.sort_values("Position").head(3)
                        actual_top3 = [str(d) for d in top3_rows["Driver"].tolist()
                                       if str(d) not in ("nan", "None", "")]

                race_session_obj = race_session_laps
            except Exception as exc:
                logger.warning("Could not extract top3 for %s %d: %s", event_name, year, exc)

            # Load qualifying session
            qualifying_session = None
            try:
                qualifying_session = fastf1.get_session(year, event_name, "Q")
                qualifying_session.load(laps=True, telemetry=False, weather=False, messages=False)
            except Exception as exc:
                logger.warning("Could not load qualifying for %s %d: %s", event_name, year, exc)

            # Load FP2 session
            fp2_session = None
            try:
                fp2_session = fastf1.get_session(year, event_name, "FP2")
                fp2_session.load(laps=True, telemetry=False, weather=False, messages=False)
            except Exception as exc:
                logger.warning("Could not load FP2 for %s %d: %s", event_name, year, exc)

            return RaceSessionData(
                year=year,
                gp_slug=gp_slug,
                event_name=event_name,
                circuit_name=circuit_name,
                qualifying_session=qualifying_session,
                fp2_session=fp2_session,
                race_session=race_session_obj,
                actual_top3=actual_top3,
            )

        except Exception as exc:
            logger.warning("Skipping race %s %d: %s", event_name, year, exc)
            return None
