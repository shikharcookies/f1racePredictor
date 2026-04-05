"""FastAPI application entry point for the F1 Prediction Dashboard."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes as routes_module
from app.api.routes import router
from app.pipeline.cache import PipelineCache
from app.pipeline.runner import PipelineRunner

logger = logging.getLogger(__name__)

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _run_multi_year_pipeline(routes_mod) -> None:
    """Run the multi-year ML pipeline in a background thread."""
    try:
        from app.pipeline.multi_year_loader import MultiYearLoader
        from app.pipeline.feature_engineer import FeatureEngineer
        from app.pipeline.cross_race_model import cross_race_model
        from app.pipeline.cache import MultiYearCache
        from app.models import SeasonEvent

        multi_year_cache = MultiYearCache()
        # Inject cache immediately so seasons endpoint returns partial data as it loads
        routes_mod.multi_year_cache = multi_year_cache
        routes_mod.cross_race_model_ref = cross_race_model
        routes_mod.feature_engineer_ref = FeatureEngineer()

        loader = MultiYearLoader()
        engineer = routes_mod.feature_engineer_ref

        logger.info("Multi-year pipeline starting in background...")
        races = loader.load_all_seasons()
        logger.info("Multi-year loader complete: %d races loaded.", len(races))

        # Build SeasonEvent index and populate cache incrementally
        seasons: dict[int, list[SeasonEvent]] = {}
        for race in races:
            year = race.year
            event = SeasonEvent(
                gp_slug=race.gp_slug,
                display_name=f"{year} {race.event_name}",
                year=year,
                is_training_set=year in (2022, 2023),
                is_test_set=year >= 2024,
                has_actual_result=len(race.actual_top3) > 0,
            )
            seasons.setdefault(year, []).append(event)

        multi_year_cache.set_seasons(seasons)
        multi_year_cache.set_race_data(races)
        logger.info("Season index built: %s", list(seasons.keys()))

        # Train model
        dataset = engineer.build_dataset(races)
        if not dataset.empty:
            cross_race_model.train(dataset)
            logger.info("Cross-race model trained. is_trained=%s", cross_race_model.is_trained())
        else:
            logger.warning("Empty dataset — model not trained.")

    except Exception as exc:
        logger.error("Multi-year pipeline failed: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run the per-GP pipeline synchronously, then start multi-year pipeline in background."""
    # Per-GP pipeline (fast — uses local cache only)
    cache = PipelineCache()
    runner = PipelineRunner()
    logger.info("Running per-GP pipeline...")
    results = runner.run_all()
    for gp_slug, gp_result in results.items():
        cache.set(gp_slug, gp_result)
    logger.info("Per-GP pipeline complete. %d GPs cached.", len(results))
    routes_module.pipeline_cache = cache

    # Multi-year pipeline runs in background — server starts immediately
    import app.api.routes as routes_mod
    t = threading.Thread(target=_run_multi_year_pipeline, args=(routes_mod,), daemon=True)
    t.start()

    yield


app = FastAPI(title="F1 Prediction Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", _FRONTEND_DIST)
else:
    logger.info("frontend/dist not found — skipping static file mount")
