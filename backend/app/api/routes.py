"""HTTP routes; calculations and persistence live in their services."""
import asyncio
from math import ceil
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.api.dependencies import (
    limit_analysis_concurrency, limit_analysis_requests, limit_location_requests,
)
from app.core.usage import UsageLimitError
from app.models import AnalysisRequest, AnalysisResult, LocationMatch
from app.services.analysis_service import get_analysis
from app.services.geocoding import fetch_locations

router = APIRouter()


@router.get("/api/health")
def health():
    return {"status":"ok"}


@router.get(
    "/api/locations",
    response_model=list[LocationMatch],
    dependencies=[Depends(limit_location_requests)],
)
async def search_locations(
    request: Request,
    query: Annotated[str,Query(min_length=2,max_length=100)],
):
    search_term=query.strip()
    
    if len(search_term) < 2:
        raise HTTPException(
            status_code=422,
            detail="Enter at least two non whitespace characters"
        )

    try:
        async with asyncio.timeout(15):
            response = await fetch_locations(
                request.app.state.http_client,
                request.app.state.location_slots,
                search_term,
            )
    except UsageLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="Location request budget exhausted. Try again later.",
            headers={"Retry-After": str(max(1, ceil(exc.retry_after)))},
        ) from exc
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=504,detail="Location search timed out"
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=503 if exc.response.status_code == 429 else 502,
            detail="Location search provider is temporarily unavailable.",
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



@router.post(
    "/api/analysis",
    response_model=AnalysisResult,
    dependencies=[
        Depends(limit_analysis_requests),
        Depends(limit_analysis_concurrency),
    ],
)
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
