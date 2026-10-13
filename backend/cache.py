
from models import Location, WeatherYear,BaselineThreshold


def weather_key(location:Location,year:int)->dict:
    return {
        "location.latitude":location.latitude,
        "location.longitude":location.longitude,
        "location.timezone":location.timezone,
        "year":year,
        "source":"open-meteo",
        "dataset":"era5_land",
        "temperature_unit":"celsius",
    }



def load_weather_year(
    collection,location:Location,year:int
) -> WeatherYear | None:
    document = collection.find_one(
        weather_key(location,year),
        {"_id":0}
    )  

    if document is None:
        return None
    return WeatherYear.model_validate(document)




def save_weather_year(collection,record:WeatherYear) -> None:
    document = record.model_dump(mode="json")
    WeatherYear.model_validate(document)

    collection.update_one(
        weather_key(record.location,record.year),
        {"$setOnInsert":document},
        upsert=True,
    )

def baseline_key(location: Location) -> dict:
    return {
        "location.latitude": location.latitude,
        "location.longitude": location.longitude,
        "location.timezone": location.timezone,
        "source": "open-meteo",
        "dataset": "era5_land",
        "temperature_unit": "celsius",
        "baseline_start_year": 1991,
        "baseline_end_year": 2020,
        "percentile": 95,
        "percentile_method": "linear",
        "baseline_version": "baseline-v1",
    }


def load_baseline_threshold(
    collection, location: Location
) -> BaselineThreshold | None:
    document = collection.find_one(
        baseline_key(location),
        {"_id": 0},
    )
    if document is None:
        return None

    return BaselineThreshold.model_validate(document)


def save_baseline_threshold(
    collection, record: BaselineThreshold
) -> None:
    document = record.model_dump(mode="json")
    BaselineThreshold.model_validate(document)

    collection.update_one(
        baseline_key(record.location),
        {"$setOnInsert": document},
        upsert=True,
    )


