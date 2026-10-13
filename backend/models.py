

from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Location(BaseModel):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False)

    name:str = Field(min_length=1,max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone:str = Field(min_length=1,max_length=100)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location:Location
    start_year: int = Field(strict=True, ge=1950, le=2025)
    end_year: int = Field(strict=True, ge=1950, le=2025)

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        if self.end_year < self.start_year:
            raise ValueError("end_year must be at least start_year")
        if self.end_year - self.start_year + 1 >30:
            raise ValueError("Select at most 30 years")
        return self 


class LocationMatch(Location):
    id: int = Field(strict=True,gt=0)
    country:str | None = Field(default=None,max_length=200)
    admin1: str | None = Field(default=None, max_length=200)