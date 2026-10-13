"""Admission checks for API requests."""
from math import ceil

from fastapi import HTTPException, Request

from app.core.request_limits import RequestRateLimiter


def check_request_limit(
    request: Request,
    limiter: RequestRateLimiter,
) -> None:
    client_key = request.client.host if request.client else "unknown"
    retry_after = limiter.reserve(client_key)

    if retry_after > 0:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(max(1, ceil(retry_after)))},
        )


async def limit_analysis_requests(request: Request) -> None:
    check_request_limit(request, request.app.state.analysis_limiter)


async def limit_location_requests(request: Request) -> None:
    check_request_limit(request, request.app.state.location_limiter)


async def limit_analysis_concurrency(request: Request):
    limiter = request.app.state.analysis_concurrency

    if not limiter.try_acquire():
        raise HTTPException(
            status_code=503,
            detail="Analysis capacity is busy. Try again shortly.",
            headers={"Retry-After": "1"},
        )

    try:
        yield
    finally:
        limiter.release()
