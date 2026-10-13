# Backend phase handoff

Completed and verified on October 14, 2026. The next implementation phase is
the React results flow; frontend integration and deployment are not complete.

- Entry point: `app.main:app`, run with `--app-dir backend --workers 1`.
- API: health, location search, and analysis. One analysis request returns the
  entire result page's data. The root README contains the request/response rules.
- Package layout: `app/api` holds routes and admission dependencies; `app/core`
  settings and limits; `app/services` provider/analysis coordination;
  `app/calculations` baseline and event logic; `app/storage` persistence and
  maintenance. Shared schemas remain in `app/models.py`. Use `app.*` imports.
- Persistence: `weather_years`, `baseline_thresholds`, and `analyses`, with
  unique indexes verified during startup. `app/storage/cache_io.py` tracks MongoDB thread
  operations for safe shutdown.
- Settings: existing local `.env`; `.env.example` documents public placeholders
  and defaults. Credentials were not inspected or committed.
- Maintenance: `scripts/manage_cache.py storage`; `invalidate` previews unless passed
  `--apply`. Stop the API before applying invalidation.
- Verification: 27 offline regression tests passed after the package refactor.
  API request/response and persisted cache paths remain unchanged. A real temporary server
  built Delhi's uncached 2018 analysis from cached weather, reused it, verified
  2020's six heatwave days/43.9 C peak, returned live Delhi geocoding, and closed
  its shared client. After the refactor the same check built an uncached 2017
  analysis and passed again. No real cache deletion was performed.
- Storage snapshot: 888,454 logical bytes including indexes in the configured
  database (about 0.18% of its 500,000,000-byte budget). This is a snapshot, not
  the whole cluster quota or a permanent guarantee.

Keep the one-worker assumption, incomplete-data/null semantics, source/grid
attribution, annual start-count rule, and observed/full/selected duration
distinctions when building the frontend. Rolling duration is the average of
annual longest durations, not average event duration. Insights compare two
five-year periods and do not claim statistical significance.

The five completion steps were committed separately: geocoding; shutdown;
storage/maintenance; regression/live verification; setup/methodology documentation.
