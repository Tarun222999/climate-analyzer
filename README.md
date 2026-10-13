# Climate Hazard Trend Analyzer

The backend analyzes historical heatwaves for a selected location and full years
from 1950 through 2025, with at most 30 years per request. It uses FastAPI,
Pydantic, NumPy, httpx, and MongoDB Atlas. The React/Vite frontend is currently a
starter; connecting its results page is the next phase. The application has not
been deployed yet.

## Backend setup

Use Python 3.13. From the repository root in PowerShell:

```powershell
py -3.13 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Skip the copy if your local `.env` already exists. Edit it locally to supply
`MONGODB_URI` and `MONGODB_DB_NAME`. Never commit credentials. If a password has
special characters, percent-encode them in the MongoDB URI. Configure Atlas
network access for the machine running the API and use a database user with the
permissions required for reads, writes, indexes, and database statistics.

Other configuration:

| Variable | Default / meaning |
| --- | --- |
| `CORS_ORIGINS` | JSON array containing `http://localhost:5173` and `http://127.0.0.1:5173` |
| `STORAGE_BUDGET_BYTES` | `500000000`; budget for the configured database's logical data plus indexes |

Run the backend from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

Use **one worker and one backend instance**: request limits, outgoing budgets,
and shared-fetch coordination are in process memory. Additional workers or
replicas would each have independent counters and could race on weather cache
updates. Restarts reset the in-memory counters. Forwarded client IP headers must
only be trusted from your hosting platform's actual proxy; arbitrary forwarded
headers should not determine client identity.

API documentation is at `http://127.0.0.1:8000/docs`. The root `/` has no route.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /api/health` | Returns `{"status":"ok"}`; a liveness check, not a per-request database readiness check |
| `GET /api/locations?query=Delhi` | Returns a JSON array of location matches; choose by country/region as well as name |
| `POST /api/analysis` | Returns baseline, summary, annual metrics, rolling averages, events, insights, and method settings |

Example analysis request:

```json
{
  "location": {
    "name": "Delhi",
    "latitude": 28.65195,
    "longitude": 77.23149,
    "timezone": "Asia/Kolkata"
  },
  "start_year": 2020,
  "end_year": 2020
}
```

Use only the location fields above. The geocoding response's `id`, `country`, and
`admin1` are useful for the selection UI but are not fields of `AnalysisRequest.location`.

Responses use 422 for invalid input, 429 for incoming rate limits, 503 for
capacity/budget/storage/provider rate-limit failures, 504 for timeouts, and 502
for other provider failures or incompatible/invalid stored or fetched data.
Capacity and budget responses include `Retry-After`. Never infer zero activity
from a null metric. An observed peak on an incomplete result is the peak among
detected events, not a guaranteed maximum for the whole period.

## Calculation and interpretation

- The baseline is always **1991–2020**, independent of the selected years. One
  location-specific threshold is NumPy's 95th percentile with `method="linear"`
  across valid baseline daily maximum temperatures. At least 95% of the 10,958
  baseline days must be valid. The percentile is a rank in the temperature
  distribution, not multiplication of a temperature by 95%.
- A heatwave is at least **three consecutive calendar days strictly above** the
  threshold. Equality is not hot. Missing and invalid readings break runs.
  Nonfinite values, strings, and temperatures outside -100 to 70 C are invalid;
  they become recorded gaps, not silently removed dates.
- Events continue across December 31. Frequency counts events in their starting
  year, while heatwave days belong to the years in which those days occur.
  The overlapping-event table can therefore contain more events than the
  selection's event-start count.
- Selection summaries clip event dates and peaks to the selected period. A
  four-day event crossing January 1 can contribute only two selected days;
  those two still belong to a qualifying event. Full duration is null unless
  both boundaries are resolved.
- The backend initially reads two neighboring days and extends connected hot
  runs in 30-day chunks, capped at 366 extra days per side. It does not fetch
  before 1950 or beyond the conservative five-day ERA5-Land availability lag.
  Missing neighbors, dataset edges, and lookup caps can leave boundaries
  unresolved. A short run beside unknown data is not reported as a confirmed
  non-event.
- Every selected date must have a valid reading and relevant boundary
  classification must be known for complete summary counts. Otherwise counts
  and duration metrics are null and `metrics_complete` is false. A year can be
  complete even when another selected year is incomplete.
- Trailing five-year averages require five complete consecutive selected years.
  The first four selected years have null averages. Duration averages refer to
  the mean of each year's longest event portion, not average full event length.
- Insights compare the first five and last five selected years only when there
  are at least ten selected years and both comparison periods are complete.
  Middle years are not part of that comparison. An earlier zero average makes
  percentage change unavailable. These comparisons do not establish causality
  or statistical significance.

Data comes from [Open-Meteo historical weather](https://open-meteo.com/en/docs/historical-weather-api)
using ERA5-Land daily `temperature_2m_max`; location search uses
[Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api).
ERA5-Land is reanalysis, combining observations and models. A selected city is
represented by one weather grid point, not an average over its city area or a
local station measurement. Grid coordinates can differ from the selected
coordinates; the backend checks consistency against the baseline. One annual
threshold mixes seasons and can miss changes relative to seasonal expectations.

## Architecture, limits, and caching

`main.py` owns shared HTTP and MongoDB clients during the app lifespan.
`weather.py` validates provider windows and implements weather retries;
`weather_service.py` fills only unfetched dates and shares in-flight work per
location/year. `baseline_service.py` builds/reuses the threshold.
`analysis_service.py` calculates results and checks the analysis cache first.

Collections have unique indexes:

- `weather_years`: coordinates, timezone, year, source, dataset, and unit. Each
  document contains the year's full calendar with gaps. `fetched_dates=None`
  means the whole year was fetched; an explicit date list tracks a partial
  year. A fetched missing reading is not repeatedly requested.
- `baseline_thresholds`: location, source/dataset/unit, baseline period,
  percentile, percentile method, and baseline version.
- `analyses`: location, selected years, and baseline/detection/context method
  settings. Display names are excluded from keys. Complete analyses with fully
  resolved event boundaries are persisted; uncertain results are returned but
  not permanently saved as settled analyses.

Stored JSON documents are validated on write and read. Historical records have
no automatic expiry. When calculation settings change, update the corresponding
model version/settings and matching service constants; reusable weather remains
available. Use explicit invalidation when source weather or a stored baseline
must be refreshed.

Incoming allowances are 6 analyses/minute and 30 location searches/minute per
client IP, with at most two active analyses. People sharing a public IP share
its allowance. Provider concurrency is two weather calls and two geocoding
calls. Analysis has a 180-second deadline; location search has a 15-second
deadline. Both providers use at most three attempts for retryable failures.
Geocoding never retries sooner than `Retry-After`; delays above two seconds are
returned to the caller rather than retried. Weather's corresponding retry-delay
cap is ten seconds.

The outgoing budget conservatively charges each HTTP attempt, including failed
attempts: geocoding costs one unit, weather costs `ceil(requested_days / 14)`.
Its limits are 540/minute, 4,500/hour, and 9,000/day. These are local protective
limits, not a complete provider-account quota ledger; monthly usage and other
applications on the same IP must also be monitored. See
[Open-Meteo pricing and usage terms](https://open-meteo.com/en/pricing).
A first location request can need 30 baseline years and hit the deadline or
budget. Retry later: successfully fetched periods remain cached.

Cancelling one caller does not cancel a shared weather fetch. On shutdown,
fetches get ten seconds to finish; remaining HTTP work is cancelled. Running
synchronous MongoDB operations are tracked and drained before the clients close.
MongoDB calls have connection, selection, and socket timeouts.

## Storage and maintenance

The API samples database storage every five minutes and logs a warning at 80%
of the configured budget. Read a report manually:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage_cache.py storage
```

The report sums logical document bytes and index bytes for the **configured
database only**, not compressed disk size or the entire cluster. Other databases
also use quota. Check the Atlas **Logical Size** metric and configure alerts;
[Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
describe the cluster-wide quota and lack of automatic storage expansion.
If growth approaches capacity, inspect obsolete analysis versions and unused
locations, invalidate selected caches, or upgrade storage. There is no automatic
eviction or deletion of valuable historical weather.

Preview invalidation without changing data:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage_cache.py invalidate --kind weather --year 2020 --latitude 28.65195 --longitude 77.23149 --timezone Asia/Kolkata
```

**Stop the API first** if applying maintenance, then run the same command with
`--apply` to delete the displayed scope. This avoids races with ongoing fetches.
No public invalidation endpoint exists. Weather invalidation removes all analyses
at that location, and also its thresholds if the year is in 1991–2020. Baseline
invalidation removes its analyses and thresholds; `--kind analyses` preserves
the inputs. Invalidation covers all method versions at the supplied coordinates
and timezone. Deletion is not an atomic multi-collection transaction; rerun a
failed maintenance operation while the API remains stopped.

## Verification

Offline regression suite (no provider calls or database writes):

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Tests cover cold and concurrent analysis flows using an in-memory database and
mock HTTP provider, warm-cache reuse, baseline coverage, strict thresholds,
cross-year allocation, incomplete years, rolling averages, insights, CORS,
incoming limits, failure responses, provider retries/concurrency, cancellation,
safe shutdown, and maintenance previews.

Optional real-cache/server verification:

```powershell
.\backend\.venv\Scripts\python.exe backend/verify_live.py
```

This requires the previously populated Delhi baseline/weather cache. It starts a
temporary server on a free localhost port, creates one missing analysis from
real cached weather, verifies a repeat cache hit and the 2020 result, calls live
geocoding, then shuts down. It writes one analysis document and deletes nothing.
The 2020 regression expectation is six heatwave days with a 43.9 C peak and a
41.1 C baseline. The script fails if it needs external weather or no uncached
analysis year remains in its test range. Normal regression tests need no such
fixtures. Windows asyncio requires local socket access even for offline tests.

## Next phase and deployment

Connect React to the API using a configurable backend URL; display summary,
annual charts, events, coverage, methodology, insights, loading states, and null
metrics honestly. Set Railway's database environment variables and the actual
Vercel origin in `CORS_ORIGINS`; run the backend with one worker/instance.
Deployment, frontend integration, and browser end-to-end testing remain pending.

Codex assisted with implementation, debugging, regression tests, and documentation.
