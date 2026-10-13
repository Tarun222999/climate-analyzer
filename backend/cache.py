


from models import Location, WeatherYear


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