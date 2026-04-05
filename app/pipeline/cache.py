"""Thread-safe in-memory cache for pipeline results."""

import threading
from app.models import GPResult


class PipelineCache:
    def __init__(self) -> None:
        self._store: dict[str, GPResult] = {}
        self._lock = threading.Lock()

    def set(self, gp_slug: str, result: GPResult) -> None:
        with self._lock:
            self._store[gp_slug] = result

    def get(self, gp_slug: str) -> GPResult | None:
        with self._lock:
            return self._store.get(gp_slug)

    def list_slugs(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())


class MultiYearCache:
    """Thread-safe cache for multi-year season data and raw race session data."""

    def __init__(self) -> None:
        self._seasons: dict[int, list] = {}  # dict[int, list[SeasonEvent]]
        self._race_data: dict[str, object] = {}  # key: "{year}:{gp_slug}" -> RaceSessionData
        self._lock = threading.Lock()

    def set_seasons(self, seasons: dict) -> None:
        with self._lock:
            self._seasons = dict(seasons)

    def get_seasons(self) -> dict:
        with self._lock:
            return dict(self._seasons)

    def get_season(self, year: int) -> list | None:
        with self._lock:
            return self._seasons.get(year)

    def get_event(self, year: int, gp_slug: str) -> object | None:
        with self._lock:
            events = self._seasons.get(year, [])
            for event in events:
                if event.gp_slug == gp_slug:
                    return event
            return None

    def set_race_data(self, races: list) -> None:
        with self._lock:
            self._race_data = {}
            for race in races:
                key = f"{race.year}:{race.gp_slug}"
                self._race_data[key] = race

    def get_race_data(self, year: int, gp_slug: str) -> object | None:
        with self._lock:
            return self._race_data.get(f"{year}:{gp_slug}")
