"""Application configuration, startup, shutdown, and route registration."""
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings
from app.core.request_limits import RequestConcurrencyLimiter, RequestRateLimiter
from app.services.weather_service import start_weather_fetches, shutdown_weather_fetches
from app.storage.cache_io import drain_cache_operations
from app.storage.database import (
    create_mongo_client, ensure_analysis_index, ensure_baseline_index, ensure_weather_index,
)
from app.storage.maintenance import monitor_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    mongo = create_mongo_client(settings)

    try:
        await asyncio.to_thread(mongo.admin.command, "ping")

        db = mongo[settings.mongodb_db_name]
        weather = db["weather_years"]
        baselines = db["baseline_thresholds"]
        analyses = db["analyses"]

        await asyncio.to_thread(ensure_weather_index, weather)
        await asyncio.to_thread(ensure_baseline_index, baselines)
        await asyncio.to_thread(ensure_analysis_index, analyses)

        async with httpx.AsyncClient(timeout=30.0) as client:
            start_weather_fetches(mongo)
            app.state.weather_collection = weather
            app.state.baseline_collection = baselines
            app.state.analysis_collection = analyses
            app.state.http_client = client
            app.state.analysis_limiter = RequestRateLimiter(6, 60.0)
            app.state.location_limiter = RequestRateLimiter(30, 60.0)
            app.state.analysis_concurrency = RequestConcurrencyLimiter(2)
            app.state.location_slots = asyncio.Semaphore(2)

            storage_stop = asyncio.Event()
            storage_task = asyncio.create_task(
                monitor_storage(db, settings.storage_budget_bytes, storage_stop)
            )
            try:
                yield
            finally:
                storage_stop.set()
                await storage_task
                await shutdown_weather_fetches(mongo)
                await drain_cache_operations()
    finally:
        await asyncio.to_thread(mongo.close)


app = FastAPI(
    title="Climate Hazard Trend Analyzer",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["Retry-After"],
)


app.include_router(router)
