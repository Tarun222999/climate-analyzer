# Climate Hazard Trend Analyzer

## Purpose

Build a web application that helps users explore how heatwaves have changed over time for a selected location. The user searches for a city and chooses a year range. The app retrieves historical daily maximum temperatures, detects heatwave events, and presents annual metrics, interactive charts, and evidence-based insights.

This project implements the full-stack developer case study. Complete the core requirements before attempting optional bonuses.

## Agreed technology stack

| Area | Technology | Purpose |
| --- | --- | --- |
| Frontend | React + TypeScript | Location search, date selection, analysis views, and loading/error states |
| Charts | Chart.js | Interactive frequency, duration, and temperature charts |
| Backend | Python + FastAPI | Validated API endpoints, weather ingestion, analysis, and cache coordination |
| Calculations | NumPy | Percentile thresholds and numerical calculations |
| Database | MongoDB Atlas free cluster | Persistent weather cache, baseline thresholds, and analysis results |
| Database access | PyMongo | Direct database queries, writes, and indexes |
| Validation | Pydantic | Request, response, and explicitly validated stored-record schemas |
| Weather source | Open-Meteo Historical Weather API, using ERA5-Land | Consistent historical daily maximum temperatures across decades |
| Location search | Open-Meteo Geocoding API | Resolve city searches into coordinates |

An ORM/ODM and Redis are not planned for the core implementation. MongoDB is the persistent cache; an in-memory cache is optional if a demonstrated need arises.

## Hosting

- **Frontend:** Vercel.
- **Backend:** Railway.
- **Database:** MongoDB Atlas free cluster.

Configure the frontend's backend API URL, keep MongoDB credentials in Railway environment variables, and allow the deployed frontend origin through backend CORS. Database access stays exclusively in the backend.

## Core user flow

1. Search for and select a city.
2. Choose full start and end years within **1950-2025**, with a maximum of **30 years** per search. Heatwave is the default hazard. Month/day selection is outside the initial scope.
3. Submit an analysis request to FastAPI.
4. The backend checks MongoDB for the required weather data and saved analysis.
5. Fetch only missing weather periods from Open-Meteo, validate them, and store them.
6. Calculate or reuse the baseline threshold, detect events, and calculate annual metrics and trends.
7. Store the analysis and return JSON results to the frontend.
8. Display charts, summary metrics, methodology, data quality information, and supported insights.

Repeated and overlapping searches reuse stored weather data. Concurrent requests for the same missing data should share a fetch rather than duplicate external calls.

## Heatwave methodology

The agreed core definition is **at least three consecutive days with daily maximum temperature strictly above the location's 95th-percentile baseline threshold**. A day exactly equal to the threshold does not qualify.

The fixed baseline is **1991-2020**, independent of the user's selected range. Calculate one 95th-percentile threshold per location from valid baseline daily maximum temperatures and save it in MongoDB. The baseline period and percentile are constant; the resulting temperature threshold varies by location. Require at least **95% valid baseline days**, otherwise return an insufficient-baseline-data message.

On a location's first request, fetch and store the baseline, calculate its threshold, and fetch any missing requested weather periods. Reuse overlapping baseline and requested periods. Subsequent requests reuse the saved threshold and weather data.

Use one threshold per location for the initial implementation and document its limitations. A seasonal threshold is a possible later refinement. Missing or invalid days must not be treated as valid hot days or silently bridge consecutive-day sequences.

### Event boundaries and reporting

- Detect continuously across December 31; a year boundary does not split an event.
- Count each event in its starting year. Label annual frequency as **Heatwaves starting each year**.
- Assign heatwave days to the calendar year in which each day occurs.
- Read at least two neighboring days before and after the selected range to establish whether boundary days belong to a qualifying event. If a hot run reaches the fetched boundary, extend the lookup until its actual start/end is known, or explicitly mark the boundary as unresolved rather than inventing a date.
- Show events overlapping the selected range, flagging those that start earlier or end later. Annual event counts and the total event-count card count starts within the selected range; the overlapping-event table may therefore contain additional events.
- Summary heatwave days, longest duration within the selection, and peak temperatures cover only selected dates. Distinguish full event duration from days within the selection in event details.
- Show data coverage and exclude incomplete years from trend calculations. Do not present missing days as zero heatwave activity.

ERA5-Land is reanalysis data: observations combined with models. A selected city is represented by its selected weather grid location, not a measured average over the city's entire area. Explain these assumptions and provide data attribution in the app and README.

## Core outputs

- Annual heatwave event counts by starting year and total events starting within the selected range.
- Annual number of heatwave days.
- Event dates and durations, including the longest duration within the selected range.
- Peak heatwave temperature in Celsius and its difference from the baseline threshold. Return unavailable temperature metrics as null when there are no qualifying days.
- Annual charts and a trailing **5-year rolling average**, available only for windows containing five complete consecutive years.
- Honest summary insights that handle missing data, short ranges, and zero starting counts.
- Methodology details, baseline threshold, source, units, and data coverage.

## Backend and storage requirements

- Cache weather by location, year, and dataset/model so overlapping searches can reuse it.
- Store source metadata, temperature units, coverage, and fetch timestamps.
- Version analysis logic and include the baseline and method settings in analysis cache keys.
- Recalculate analysis when its method changes while preserving reusable weather data.
- Validate location inputs and date ranges before fetching external data.
- Apply incoming request limits and control outgoing API concurrency and usage.
- Set external request timeouts and use bounded retries. Handle HTTP 429 and respect Retry-After when supplied.
- Keep MongoDB credentials in backend environment variables and restrict CORS to the frontend.
- Monitor storage use on the Atlas free cluster rather than assuming unlimited cache capacity.
- Use location/year weather documents and separate saved thresholds and analysis results. Historical cache has no automatic expiry for this submission; explicit invalidation remains available when source or method settings change.
- Start with a normal analysis request, a visible loading state, and bounded timeouts. Background jobs are deferred unless measured request latency demonstrates a need.
- Keep the architecture small and deliver the complete core flow before extras. Authentication is outside the initial scope.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| GET /api/locations?query=delhi | Return matching cities with names, coordinates, and timezones |
| POST /api/analysis | Accept a selected location and year range; return summary metrics, annual chart data, events, methodology, and coverage |
| GET /api/health | Confirm the backend is running |

One analysis request supplies the entire results page. Weather ingestion and caching are internal backend operations, not separate frontend endpoints.

## Implementation details to resolve during development

The major product and technology decisions are settled. Resolve the following within the agreed scope without adding unnecessary infrastructure:

- Exact request/response schemas, document fields, indexes, and duplicate-fetch coordination.
- Conservative validation rules for implausible weather values; document assumptions without silently removing legitimate extremes.
- Cache storage monitoring and any eviction needed to stay within the free cluster's capacity.
- Insight comparison rules, including zero denominators and insufficient data.
- UI styling and responsive layout. `preview.html` is a basic layout reference using fictional data, not a functioning analysis application.

## Verification

Test the climate logic with meaningful examples: isolated hot days, exactly three hot days, longer events, threshold equality, missing days, and events crossing boundaries. Verify cache reuse, validation, external API failures, and consistency between returned metrics and charts.

## Optional bonuses

Only begin these after the core application is complete. Current priority:

1. **Linear regression:** quantify changes in annual metrics if time permits. Do not imply statistical significance without supporting analysis.
2. **CSV export:** download the already calculated annual metrics with clear columns and units, without an additional weather request.
3. **Map selection:** add geographic selection if time remains.

PDF export and Mann-Kendall testing are optional alternatives or extensions, not committed scope.

## Submission deliverables

- Public GitHub repository containing the implementation. Do not publish the confidential case-study brief.
- Deployed application URL.
- README covering setup, architecture, data sources, hazard logic, assumptions, limitations, and improvements with more time.
- Disclosure of AI tools used and how they were used.
- Optional 3-5 minute demo video.

## Current status

Planning complete for the core scope, climate methodology, endpoints, and hosting. Implementation has not started. A standalone HTML layout preview exists. Next, implement and verify the backend weather/cache/analysis flow, then connect the React frontend and deploy.
