from models import AnalysisRequest, AnalysisResult, BaselineThreshold


BASELINE_KEY_FIELDS = (
    "source",
    "dataset",
    "temperature_unit",
    "baseline_start_year",
    "baseline_end_year",
    "percentile",
    "percentile_method",
    "baseline_version",
)


METHOD_KEY_FIELDS = (
    "analysis_version",
    "minimum_consecutive_days",
    "threshold_comparison",
    "context_padding_days",
    "context_chunk_days",
    "maximum_context_days_per_side",
)


ANALYSIS_KEY_FIELDS = (
    "request.location.latitude",
    "request.location.longitude",
    "request.location.timezone",
    "request.start_year",
    "request.end_year",
    *(f"baseline.{field}" for field in BASELINE_KEY_FIELDS),
    *METHOD_KEY_FIELDS,
)





def analysis_key(request: AnalysisRequest) -> dict:
    key = {
        "request.location.latitude": request.location.latitude,
        "request.location.longitude": request.location.longitude,
        "request.location.timezone": request.location.timezone,
        "request.start_year": request.start_year,
        "request.end_year": request.end_year,
    }

    for field in BASELINE_KEY_FIELDS:
        key[f"baseline.{field}"] = BaselineThreshold.model_fields[field].default

    for field in METHOD_KEY_FIELDS:
        key[field] = AnalysisResult.model_fields[field].default

    return key



def load_analysis(
    collection,
    request: AnalysisRequest,
) -> AnalysisResult | None:
    document = collection.find_one(
        analysis_key(request),
        {"_id": 0},
    )

    if document is None:
        return None

    return AnalysisResult.model_validate(document)


def save_analysis(
    collection,
    result: AnalysisResult,
) -> bool:
    document = result.model_dump(mode="json")
    validated = AnalysisResult.model_validate(document)

    # Keep uncertain results available to the caller, but do not
    # permanently cache them as settled historical analyses.
    if not validated.summary.metrics_complete:
        return False

    if any(
        not event.start_boundary_resolved
        or not event.end_boundary_resolved
        for event in validated.events
    ):
        return False

    collection.update_one(
        analysis_key(validated.request),
        {"$setOnInsert": document},
        upsert=True,
    )
    return True

