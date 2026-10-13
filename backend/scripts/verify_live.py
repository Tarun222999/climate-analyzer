"""Run a temporary local server and verify real caches without deleting data."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

import httpx
import uvicorn

from app.storage.analysis_cache import load_analysis
from app.core.config import Settings
from app.storage.database import create_mongo_client
from app.main import app
from app.models import AnalysisRequest, AnalysisResult, Location


async def main():
    settings = Settings()
    location = Location(name="Delhi", latitude=28.65195, longitude=77.23149, timezone="Asia/Kolkata")

    def choose_uncached_year():
        with create_mongo_client(settings) as mongo:
            collection = mongo[settings.mongodb_db_name]["analyses"]
            for year in range(2018, 1991, -1):
                request = AnalysisRequest(location=location, start_year=year, end_year=year)
                if load_analysis(collection, request) is None:
                    return request
        raise RuntimeError("No uncached analysis year found in the existing baseline weather")

    cold_request = await asyncio.to_thread(choose_uncached_year)
    config = uvicorn.Config(app, host="127.0.0.1", port=0, workers=1, log_level="warning")
    listener = config.bind_socket()
    port = listener.getsockname()[1]
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[listener]))

    try:
        async with asyncio.timeout(30):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Server stopped before startup")
                await asyncio.sleep(0.05)

        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=190, trust_env=False) as api:
            health = await api.get("/api/health")
            assert health.status_code == 200 and health.json() == {"status": "ok"}
            print("Running server: health passed")

            def reject_weather(request):
                raise AssertionError("Expected cached weather, but an external request was attempted")

            original = app.state.http_client
            async with httpx.AsyncClient(transport=httpx.MockTransport(reject_weather)) as blocked:
                app.state.http_client = blocked
                try:
                    cold = await api.post("/api/analysis", json=cold_request.model_dump(mode="json"))
                    assert cold.status_code == 200, f"Cold analysis returned HTTP {cold.status_code}"
                    result = AnalysisResult.model_validate(cold.json())
                    assert result.summary.metrics_complete
                    print(f"Uncached {cold_request.start_year} analysis built from real cached weather")
                    warm = await api.post("/api/analysis", json=cold_request.model_dump(mode="json"))
                    assert warm.status_code == 200 and warm.json() == cold.json()
                    print("Repeated request reused the stored analysis with zero weather HTTP requests")

                    known = AnalysisRequest(location=location, start_year=2020, end_year=2020)
                    response = await api.post("/api/analysis", json=known.model_dump(mode="json"))
                    assert response.status_code == 200
                    summary = response.json()["summary"]
                    assert summary["heatwave_days"] == 6 and summary["peak_temperature_c"] == 43.9
                    print("Delhi 2020 regression: six heatwave days, peak 43.9 C")
                    invalid = {**known.model_dump(mode="json"), "end_year": 2019}
                    assert (await api.post("/api/analysis", json=invalid)).status_code == 422
                    print("Invalid request rejected over real HTTP")
                finally:
                    app.state.http_client = original

            cities = await api.get("/api/locations", params={"query": "Delhi"})
            assert cities.status_code == 200, f"Live geocoding returned HTTP {cities.status_code}"
            assert any(city["country"] == "India" for city in cities.json())
            print("Live location provider returned Delhi, India")
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 30)
        listener.close()
    assert app.state.http_client.is_closed
    print("Running server shut down and shared HTTP client closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Live verification failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
