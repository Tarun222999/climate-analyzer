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
- Follow-up code inspection confirms backend CORS now includes
  `expose_headers=["Retry-After"]`. Actual cross-origin error-header exposure
  has not been independently browser-verified; the numeric delay branch was
  verified with simulated browser responses during core QA.
- Browser QA used Chromium device emulation, not physical mobile devices or
  Safari. Real incomplete weather data/provider failures were not induced.
- API TypeScript types describe the contract; they are not full runtime schema
  validation. Malformed JSON and non-array location responses are handled.
- Deployed browser integration and hosting/build settings remain unverified.
- Historical regression is now implemented; see REGRESSION_HANDOFF.md for
  verification limits and user test steps. Map selection remains optional.

## CSV export and source organization follow-up

- CSV export is implemented in `src/utils/csv.ts`. The results header provides
  Download CSV only for a successful result. It uses that response, not unsent
  form fields, and makes no API requests.
- One row per annual metric, with 26 consistent columns. Location, selected
  years, baseline percentile/method/threshold, source/dataset/grid context,
  coverage, completeness, peak interpretation, and blank-value meaning are
  included. Real zeroes are preserved; null metrics are empty fields.
- Cells escape quotes/commas/newlines. Formula-leading text is prefixed with
  an apostrophe; numeric negative values are preserved. The file has a UTF-8
  BOM, a descriptive filename, and temporary object URLs are revoked.
- The user verified a real Delhi 2020 browser download and expected filename,
  annual metrics, completeness, and baseline threshold; lint/build passed.
- After reorganizing, direct Node checks passed for 26-column CSV round-trip,
  expected values, zero/null/incomplete rows, text escaping/formula prefixes,
  numeric negatives, filename, UTF-8 BOM, and object URL/anchor cleanup. Download
  mechanics used a DOM stub; that check was not a new browser download.
- Source now uses `components/` for UI, `components/charts/` for charts,
  `services/api.ts` for HTTP, and `utils/csv.ts` for export. `App.tsx`, `main.tsx`,
  `types.ts`, and the single `index.css` remain at the source root. Empty
  App.css and unreferenced starter assets were removed. App coordination/form
  behavior was not refactored in this organizational pass.
- Final lint and build passed after file moves. Local frontend port 5173 was
  stopped during the follow-up, so a browser recheck after moving files remains
  pending. No server was launched and no deployment/push was performed.
