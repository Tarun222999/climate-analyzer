from dataclasses import field
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query
from pydantic import ValidationError

from backend.models import LocationMatch

import httpx

app = FastAPI(title="Climate Hazard Trend Analyzer")


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



