
from pymongo import ASCENDING, MongoClient

from config import Settings



WEATHER_INDEX_NAME = "unique_weather_year"

WEATHER_INDEX_FIELDS = [
    ("location.latitude", ASCENDING),
    ("location.longitude", ASCENDING),
    ("location.timezone", ASCENDING),
    ("year", ASCENDING),
    ("source", ASCENDING),
    ("dataset", ASCENDING),
    ("temperature_unit", ASCENDING),
]




def create_mongo_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.mongodb_uri.get_secret_value(),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        tz_aware=True,
    )



def ensure_weather_index(collection) -> str:
    return collection.create_index(
        WEATHER_INDEX_FIELDS,
        name=WEATHER_INDEX_NAME,
        unique=True,
    )


BASELINE_INDEX_NAME = "unique_baseline_threshold"


BASELINE_INDEX_FIELDS = [
    (field, ASCENDING)
    for field in (
        "location.latitude",
        "location.longitude",
        "location.timezone",
        "source",
        "dataset",
        "temperature_unit",
        "baseline_start_year",
        "baseline_end_year",
        "percentile",
        "percentile_method",
        "baseline_version",
    )
]



def ensure_baseline_index(collection) -> str:
    return collection.create_index(
        BASELINE_INDEX_FIELDS,
        name=BASELINE_INDEX_NAME,
        unique=True,
    )

from analysis_cache import ANALYSIS_KEY_FIELDS


ANALYSIS_INDEX_NAME = "unique_analysis"

ANALYSIS_INDEX_FIELDS = [
    (field, ASCENDING)
    for field in ANALYSIS_KEY_FIELDS
]


def ensure_analysis_index(collection) -> str:
    return collection.create_index(
        ANALYSIS_INDEX_FIELDS,
        name=ANALYSIS_INDEX_NAME,
        unique=True,
    )