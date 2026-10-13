import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import ValidationError

from config import Settings
from database import (
    create_mongo_client,
    ensure_analysis_index,
    ensure_baseline_index,
    ensure_weather_index,
)
from models import LocationMatch


from math import ceil

from fastapi import Request
from pymongo.errors import PyMongoError

from analysis_service import get_analysis
from models import AnalysisRequest, AnalysisResult
from usage import UsageLimitError

from fastapi import Depends
from request_limits import RequestRateLimiter


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
            app.state.weather_collection = weather
            app.state.baseline_collection = baselines
            app.state.analysis_collection = analyses
            app.state.http_client = client
            app.state.analysis_limiter = RequestRateLimiter(6, 60.0)
            app.state.location_limiter = RequestRateLimiter(30, 60.0)

            yield
    finally:
        await asyncio.to_thread(mongo.close)


app = FastAPI(
    title="Climate Hazard Trend Analyzer",
    lifespan=lifespan,
)


@app.get("/api/health")
def health():
    return {"status":"ok"}


@app.get("/api/locations",response_model=list[LocationMatch])
async def search_locations(
    query: Annotated[str,Query(min_length=2,max_length=100)],
):
    search_term=query.strip()
    
    if len(search_term) < 2:
        raise HTTPException(
            status_code=422,
            detail="Enter at least two non whitespace characters"
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                 params = {
                    "name":search_term,
                    "count":10,
                    "language":"en",
                 }
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,detail="Location search timed out"
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,detail="Location search service unavailable"
        ) from exc

    try:
        payload = response.json()
        if not isinstance(payload,dict):
            raise ValueError("Expected an object")
        cities = payload.get("results",[])
        if not isinstance(cities,list):
            raise ValueError("Expected a list of locations")
        matches=[]
        for city in cities:
            if not isinstance(city,dict):
                raise ValueError("Expected a location object")
            

            #discard not needed metadata
            fields = {
                field:city[field]
                for field in LocationMatch.model_fields
                if field in city
            }

            matches.append(LocationMatch.model_validate(fields))

        return matches

    except (ValueError,ValidationError) as exc:
        raise HTTPException(
            status_code=502,detail="Invalid location search response"
        ) from exc 



@app.post("/api/analysis", response_model=AnalysisResult)
async def analyze(
    data: AnalysisRequest,
    request: Request,
):
    try:
        async with asyncio.timeout(180):
            return await get_analysis(
                request.app.state.weather_collection,
                request.app.state.baseline_collection,
                request.app.state.analysis_collection,
                request.app.state.http_client,
                data,
            )

    except UsageLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="Weather request budget exhausted. Try again later.",
            headers={"Retry-After": str(max(1, ceil(exc.retry_after)))},
        ) from exc

    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=504,
            detail="Analysis timed out. Try again; fetched weather is cached.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        limited = exc.response.status_code == 429
        raise HTTPException(
            status_code=503 if limited else 502,
            detail=(
                "Weather provider is temporarily rate limited."
                if limited else "Weather provider request failed."
            ),
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Weather provider is unavailable.",
        ) from exc

    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail="Analysis storage is temporarily unavailable.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Stored or fetched data could not satisfy analysis requirements.",
        ) from exc