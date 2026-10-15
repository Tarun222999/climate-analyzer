# Climate Hazard Trend Analyzer

Explore historical heatwaves for a selected city: how often they occurred, how
long they lasted, and how intense they were. Select full years from **1950-2025**,
with at most **30 years per request**.

**Status:** core backend and frontend, CSV export, and historical linear
regression are complete locally. Deployment and public end-to-end verification
are pending. Planned hosting: **Vercel + Railway + MongoDB Atlas free cluster**.
Public app and repository links will be added after deployment.

## Features

- City search with region/country context, validated year selection, and clear
  loading, retry, and error states.
- Summary cards for heatwaves starting in the selection, heatwave days, longest
  event portion within the selection, and peak heatwave temperature.
- Four interactive Chart.js charts: annual frequency, heatwave days, longest
  duration, and peak temperature. Eligible metrics have five-year rolling averages.
- A historical regression overlay on the frequency chart, with fitted change per
  decade and disclosure of the complete years used.
- Event details, coverage, baseline methodology, source attribution, and insights.
- Annual CSV download with location, baseline, grid/source context, units, and
  completeness. Missing metrics stay blank; real zeroes stay zero.
- Persistent weather/analysis caching, input validation, bounded provider requests,
  request limits, and explicit handling of incomplete data.

## Stack and architecture

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Chart.js |
| Backend | Python, FastAPI, Pydantic, NumPy, httpx |
| Database | MongoDB Atlas, PyMongo |
| External data | Open-Meteo Geocoding and Historical Weather APIs, ERA5-Land |

```text
React frontend -> FastAPI -> MongoDB cache
                      -> Open-Meteo for missing weather / city search
```

The frontend receives one analysis response containing the results needed for
the page. FastAPI fetches only missing weather periods, calculates or reuses the
baseline, detects events, and returns annual metrics and trends. MongoDB stores
weather by location/year, baseline thresholds, and versioned analyses. CSV is
created in the browser from the current successful analysis; it needs no extra
request. There is no ORM/ODM, Redis, authentication, or background job service.

```text
backend/
  app/
    main.py                 # App lifespan, shared clients, CORS
    models.py               # Validated requests, responses, stored records
    api/                    # Routes and admission checks
    core/                   # Configuration, limits, provider budget
    services/               # Ingestion, baseline and analysis coordination
    calculations/           # Percentile, heatwaves, linear regression
    storage/                # MongoDB caches and maintenance
  scripts/                  # Mongo check, cache maintenance, live verification
  tests/                    # Offline tests
  .env.example
  requirements.txt
frontend/
  src/
    components/             # Search, summaries, charts, events, methodology
    services/api.ts         # Requests and error handling
    utils/                  # CSV and regression presentation
    types.ts                # API response types
    index.css               # Responsive styles
  tests/                    # Regression mapping and description tests
  .env.example
  package.json
```

## Local setup

Prerequisites: **Python 3.13**, **Node.js 22.18+ or a compatible newer LTS version**,
npm, and a MongoDB Atlas database reachable from your machine. Open-Meteo's free
non-commercial endpoints do not require API keys; attribution and usage limits
still apply. See [Open-Meteo usage terms](https://open-meteo.com/en/terms).

### Backend

From the repository root in PowerShell:

```powershell
py -3.13 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Skip the copy if your local file already exists. Configure these values locally;
never commit credentials or put them in frontend variables:

| Backend variable | Value |
| --- | --- |
| `MONGODB_URI` | Atlas connection URI with database credentials |
| `MONGODB_DB_NAME` | Database name, for example `climate_analyzer` |
| `CORS_ORIGINS` | JSON array; defaults to `http://localhost:5173` and `http://127.0.0.1:5173` |
| `STORAGE_BUDGET_BYTES` | Defaults to `500000000` for configured-database logical data plus indexes |

Percent-encode special characters in the URI password. Configure Atlas network
access and a database user with permissions for reads, writes, indexes, and
storage statistics. Backend settings resolve `backend/.env` independently of the
working directory.

Check connectivity, then start the API:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/check_mongo.py
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

API documentation: `http://127.0.0.1:8000/docs`. Health: `/api/health`.
There is no route at `/`.

### Frontend

In another terminal at the repository root:

```powershell
npm --prefix frontend ci
Copy-Item frontend/.env.example frontend/.env
npm --prefix frontend run dev -- --port 5173 --strictPort
```

Skip the copy if the file already exists. Set
`VITE_API_BASE_URL=http://127.0.0.1:8000` for local development and open
`http://localhost:5173`. Restart Vite after environment changes. `VITE_` variables
are public browser configuration and must never contain secrets.

Try **Delhi, India / 2020-2020** for a small analysis, then a range with at least
ten complete years for regression. A new city needs 30 baseline years and may
load slowly or hit a timeout/provider limit. Successfully fetched periods stay
cached, so a later retry can reuse them.

## Heatwave methodology

- **Baseline:** fixed **1991-2020**, independent of the selected years. Calculate
  the location's 95th percentile of valid daily maximum temperatures with NumPy
  `method="linear"`. At least 95% of the 10,958 baseline days must be valid.
- **Event:** at least **three consecutive calendar days strictly above** the
  threshold. Equal temperatures do not qualify. Missing/invalid readings break
  sequences. Nonfinite/non-numeric readings and values outside -100 to 70 C are
  treated as gaps rather than removed dates.
- **Year boundaries:** detect continuously across December 31. Count an event in
  its starting year; allocate heatwave days to the year in which each day occurs.
- **Selected range:** summary duration and peak use only selected dates. Event
  details distinguish observed, selected, and full durations. The table can show
  overlapping events that started before the selection, so it can contain more
  events than the start-count card.
- **Boundary context:** read two neighboring days, extending connected hot runs
  in 30-day chunks up to 366 extra days per side. Dataset edges, missing values,
  and caps can leave boundaries unresolved; full duration is then unknown.
- **Completeness:** unknown counts/durations are `null`, never invented zeroes.
  Complete metrics require valid selected readings and known relevant boundary
  classifications. Peaks on incomplete results are observed values, not guaranteed
  whole-period maxima. Years are assessed independently.
- **Rolling averages:** trailing five complete consecutive selected years. The
  first four years are unavailable. Duration averages use annual longest portions,
  not all event durations. Peak temperature has no rolling-average line.
- **Insights:** compare the first and last five selected years when there are at
  least ten years and both comparison periods are complete. Earlier zero means
  percentage change is unavailable. No causal or significance claims are made.

### Historical linear regression

Ordinary least squares fits **annual heatwave start counts against actual calendar
years**. Only complete years with known valid counts are included, with at least
**ten usable years** required. Gaps retain actual year distances; constant counts
produce a valid flat line. The ten-year rule is a project choice, not proof of
statistical significance.

The dashed line describes the historical direction and rate. For example,
`change_per_decade = 2` means the fitted annual count rises by two events over a
ten-year interval. This is **not a forecast, causal conclusion, or significance
test**. Fitted values can be fractional or negative because OLS is unconstrained;
they are not observed counts. Plot values remain unrounded; text is rounded.

### Data source and assumptions

Weather comes from [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api),
using **ERA5-Land** daily `temperature_2m_max`; city lookup uses
[Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api).
ERA5-Land combines observations and models (reanalysis). A city represents one
weather grid point, not a city-wide average or local station measurement. Grid
coordinates may differ from the selected coordinates; consistency with the
baseline is checked. An annual threshold mixes seasons and has limitations
compared with a seasonal/day-of-year definition.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness: `{"status":"ok"}`; not a database readiness probe |
| `GET /api/locations?query=Delhi` | JSON array of matching cities |
| `POST /api/analysis` | Baseline, summary, annual metrics, rolling averages, regression, events, insights, and method settings |

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

Send only these location fields; geocoding `id`, `country`, and `admin1` are display
context, not analysis request fields. Exact schemas are available in `/docs` and
`backend/app/models.py`.

Responses include `analysis_version: "analysis-v2"` and `regression` containing
`status`, `reason`, `metric`, `minimum_complete_years`, `years_used`,
`slope_events_per_year`, `change_per_decade`, and `fitted_values`. Each fitted point
has `year`, `observed_event_starts`, and `fitted_event_starts`. Unavailable results
use `reason: "insufficient_complete_years"`, null slope/change, and empty fitted
values. The frontend explains the minimum rather than drawing a line.

Errors: **422** validation, **429** incoming rate limits, **503** capacity,
provider limits, storage or budget failures, **504** timeouts, and **502** other
provider/data failures. Relevant capacity/budget responses carry `Retry-After`,
which the backend CORS configuration exposes to browser code.

## Caching and operational limits

MongoDB collections have unique indexes and validated records:

- `weather_years`: location, timezone, year, source/dataset/unit, daily values,
  gaps, and fetched-date coverage. Fetch only missing periods, including when
  baseline and selected years overlap.
- `baseline_thresholds`: location and baseline/method settings.
- `analyses`: selected years plus baseline/detection/context/version settings.
  Persist settled analyses with complete metrics and resolved boundaries;
  uncertain results are returned without permanently caching them as settled.

Older `analysis-v1` results are skipped and rebuilt as v2 from reusable weather
and baseline caches, not automatically deleted. Changing regression rules requires
another analysis-version change. Historical records have no automatic expiry.

Use **one backend worker and one instance**. Incoming counters, outgoing budgets,
and shared-fetch coordination are in memory; restarts reset counters. Multiple
workers/replicas would need shared coordination. Trust forwarded client IP headers
only from the hosting platform's actual proxy.

Incoming limits are six analyses/minute and 30 city searches/minute per client
IP, with at most two active analyses. People on one public IP share limits.
Provider concurrency is two weather calls and two geocoding calls. Backend
deadlines are 180 seconds for analysis and 15 seconds for city search; the frontend
allows 200 and 20 seconds respectively. Provider retries are bounded to three
attempts and respect supported `Retry-After` handling.

The local outgoing budget charges every HTTP attempt, including failed attempts:
one unit per city lookup and `ceil(requested_days / 14)` per weather fetch, capped
at 540/minute, 4,500/hour, and 9,000/day. This is a protective estimate, not a
provider-wide ledger. Monitor monthly usage and other apps sharing the IP. See
[Open-Meteo pricing](https://open-meteo.com/en/pricing).

### Storage maintenance

Storage is sampled every five minutes with a warning at 80% of the configured
budget. The report covers logical data plus indexes in the configured database,
not all databases or compressed disk usage. Also monitor Atlas cluster metrics.

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/manage_cache.py storage
```

Invalidation previews by default. **Stop the API before using `--apply`.** Weather
invalidation also removes dependent analyses and, for baseline years, thresholds.
Baseline invalidation removes its analyses; analyses-only invalidation keeps
inputs. No automatic eviction or public invalidation endpoint exists. See
`backend/scripts/manage_cache.py --help` for scoped options.

## Verification

Run from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
npm --prefix frontend run lint
npm --prefix frontend run build
node --experimental-strip-types --test frontend/tests/regression.test.mjs
```

Recorded results from development (not a claim that each command was rerun during
this documentation update):

- **35 backend offline tests passed:** climate edge cases, completeness, actual
  year regression distances, cache migration/reuse, validation, limits, retries,
  cancellation, shutdown, and maintenance. Dependency checks passed.
- **Frontend lint/build and six regression tests passed:** year mapping, excluded
  years, precision, increasing/decreasing/constant/near-zero descriptions, and
  unavailable fits.
- **Real localhost integration:** Delhi 2020 produced one event start, six
  heatwave days, a six-day longest selected portion, 43.9 C peak, and 41.1 C baseline.
- **User browser checks:** available regression overlay/tooltip, decreasing
  wording, single-year unavailable state, and an actual CSV download. Direct CSV
  zero/null/escaping checks also passed.
- **Core browser checks:** loading, duplicate-submit protection, simulated HTTP,
  connection/timeout, malformed-response, empty/incomplete, and boundary states.
  Real populated layouts were checked at 320, 375, 768, and 1440 px.

Simulated responses do not verify actual provider failures. Physical mobile,
Safari, production end-to-end behavior, and production cross-origin `Retry-After`
access remain unverified.

An optional live verification script starts a temporary localhost server, uses
existing Delhi weather/baseline cache, creates a missing analysis, checks repeat
cache reuse, calls real geocoding, and shuts down:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/verify_live.py
```

It **writes an analysis document**, deletes nothing, and requires populated cache
fixtures and an uncached test year; it is not an offline test. All normal backend
tests use mock providers/database data and do not write real cache records.

## Deployment plan

Deployment has not yet been verified. Intended settings:

| Service | Configuration |
| --- | --- |
| Vercel | Root `frontend`; build `npm run build`; output `dist` |
| Vercel environment | `VITE_API_BASE_URL` = public Railway backend origin, set before building |
| Railway | Python 3.13; install `backend/requirements.txt`; repository-root start command below |
| Railway environment | `MONGODB_URI`, `MONGODB_DB_NAME`, JSON-array `CORS_ORIGINS` containing the actual allowed frontend origins |
| Atlas | Database user and network access for the running backend |

```sh
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --workers 1
```

Use one Railway instance and `/api/health` for its health check. The frontend calls
the backend directly. Configure trusted proxy handling for the actual platform.
Before submitting, verify production city search, analysis, cache reuse, CSV,
available/unavailable regression, responsive layout, and CORS through the public
frontend. Keep database credentials server-side.

## Limitations and improvements

- Heatwaves only, with city/point selection. Area aggregation, map selection,
  additional hazards, PDF export, and Mann-Kendall testing are not implemented.
- Improve seasonal thresholds after domain review; quantify trend uncertainty
  rather than interpreting descriptive OLS as significance or prediction.
- Background jobs with progress could improve slow first searches.
- Shared limits/coordination are needed for multiple backend instances.
- Monitor Atlas storage and deliberately refresh revised source data; there is
  no automatic historical-cache refresh or eviction.
- Add cross-browser/physical-device checks and deployment monitoring.

## AI tools used

**OpenAI Codex** assisted with planning and mentoring, architecture/methodology
explanations, code generation and review, debugging, tests, browser verification
assistance, refactoring, and documentation. Work combined user-written changes
with explicitly authorized direct implementation. The user ran setup and browser
checks and reviewed behavior during development. AI assistance does not constitute
independent scientific validation of the heatwave definition.
