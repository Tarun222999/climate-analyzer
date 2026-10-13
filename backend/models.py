
from datetime import date,timedelta
from typing import Self,Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator,AwareDatetime


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


class DailyTemperature(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    date:date
    max_temperature_c:float | None = Field(
        strict=True,
        ge=-100,
        le=70
    )



class WeatherYear(BaseModel):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False)

    location:Location
    year: int = Field(strict=True,ge=1950,le=9998)
    source: Literal["open-meteo"] = "open-meteo"
    dataset: Literal["era5_land"] = "era5_land"
    temperature_unit: Literal["celsius"] = "celsius"

    grid_latitude: float = Field(ge=-90, le=90)
    grid_longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=100)
    fetched_at: AwareDatetime

    days: list[DailyTemperature]
    invalid_dates: list[date]
    expected_days: int = Field(strict=True, ge=365, le=366)
    valid_days: int = Field(strict=True, ge=0, le=366)

    @model_validator(mode="after")
    def validate_records(self) -> Self:
        first = date(self.year, 1, 1)
        count = (date(self.year + 1, 1, 1) - first).days
        expected = [first + timedelta(days=i) for i in range(count)]

        if self.expected_days != count:
            raise ValueError("Incorrect expected day count")
        if [day.date for day in self.days] != expected:
            raise ValueError("Daily records must cover the year in order")

        valid = sum(day.max_temperature_c is not None for day in self.days)

        if self.valid_days != valid:
            raise ValueError("Valid day count does not match records")

        missing_dates = {
            day.date for day in self.days
            if day.max_temperature_c is None
        }

        if(len(set(self.invalid_dates)) != len(self.invalid_dates)):
            raise ValueError("Duplicate invalid dates")
        if not set(self.invalid_dates).issubset(missing_dates):
            raise ValueError("Invalid dates must correspond to missing readings")

        return self
