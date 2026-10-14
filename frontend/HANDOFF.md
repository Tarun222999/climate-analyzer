# Frontend phase handoff

Completed local core frontend and state verification on October 14, 2026.
Deployment remains a separate phase.

## Implemented

- React/TypeScript city search with a 500 ms debounce, cancellation, a 20-second
  search deadline, no-match/error states, retry, and Escape to dismiss results.
- Full-year selection (1950–2025, inclusive maximum 30 years), explicit city
  selection, and a single analysis POST containing only permitted location fields.
- Informative analysis loading state, a 200-second frontend deadline, disabled
  controls during analysis, and synchronous protection against duplicate submits.
- Errors for validation, rate limits, provider/capacity failures, timeout,
  network failure, and malformed JSON; controls recover for manual retry.
- Initial results guidance, zero-event results, null/unavailable metrics, and
  incomplete-data/boundary explanations. Editing the selection clears old results
  and stale validation messages.
- Four summary cards, coverage, peak difference above the baseline threshold,
  and Chart.js frequency, days, duration, and peak-temperature charts.
- Backend rolling averages are used without recalculation. Temperature has no
  rolling average; incomplete-year observed peaks are flagged in points/tooltips.
- Event details preserve observed, selected, and full-duration distinctions and
  nullable overlap flags. The table scrolls independently on narrow screens.
- Backend insights, baseline/coverage/methodology, grid/timezone information,
  source attribution, and interpretation limitations.
- Layout follows preview.html. Mobile cards/forms stack; desktop charts form a
  two-column layout. Single-year bars are capped at 48 pixels.

## Verification evidence

- Final frontend lint and production build passed.
- Real localhost browser/API integration: Delhi, India, 2020 returned 1 event
  start, 6 heatwave days, longest selected duration 6 days, peak 43.9 C, and
  baseline 41.1 C. Four charts, events, methodology, and insights rendered.
- User additionally checked single/multiple-year charts and results views during
  development, including the five-year rolling-average line.
- An isolated browser tab passed 20 scripted checks using a real Delhi response
  as the base fixture: initial guidance, required city, no search matches,
  search error/retry recovery, loading/disabled controls, duplicate submission,
  result rendering, mobile overflow, HTTP 422/429/502/503/504, numeric Retry-After,
  connection failure, invalid JSON, zero-event results, incomplete/null metrics,
  and unresolved event boundaries.
- Two additional browser checks passed for search and analysis timeout handling.
  Test deadlines were shortened in the isolated tab; production deadlines were
  not changed. Failure/empty/incomplete responses were simulated, not induced
  in the real database or weather provider.
- Real populated results had no page-wide horizontal overflow at 320, 375,
  768, and 1440 px. A 320 px screenshot was inspected; desktop search dropdown
  layout was also inspected. Event-table horizontal scrolling is intentional.
- No backend changes, dependency installation, server launches, commits, pushes,
  or deployment were performed during this final verification pass. Existing
  local servers were reused. Browser mocks were confined to an isolated tab;
  a real API flow was rechecked afterward.

## Deployment handoff / remaining issues

- Frontend: Vercel; backend: Railway with one worker/instance; database: Atlas.
  Configure VITE_API_BASE_URL and the actual frontend origin in backend CORS.
- Backend currently does not expose Retry-After through CORS. Generic retry
  guidance works, but an exact retry delay is readable by the cross-origin
  frontend only if deployment/backend CORS exposes that header. The numeric
  delay branch was verified with simulated browser responses.
- Browser QA used Chromium device emulation, not physical mobile devices or
  Safari. Real incomplete weather data/provider failures were not induced.
- API TypeScript types describe the contract; they are not full runtime schema
  validation. Malformed JSON and non-array location responses are handled.
- Deployed browser integration and hosting/build settings remain unverified.
- Regression, CSV export, and map selection remain optional bonuses.
