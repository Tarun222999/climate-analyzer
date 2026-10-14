# Frontend regression integration handoff

Implemented October 15, 2026. Ready for user browser/API testing.

## Changes

- API types require `analysis_version: "analysis-v2"` and a discriminated
  `HeatwaveRegression` union. The request and CSV export are unchanged.
- Available regression adds a purple dashed **Historical linear trend** to the
  existing frequency chart, alongside annual bars and the five-year average.
- Fitted values map by actual year to the annual labels. Excluded years remain
  null gaps; zero, fractional, and negative fitted values are preserved.
  There is no extrapolation outside included historical years.
- Direction-aware text uses events per decade, actual included-year count, and
  selected-period context. Small nonzero changes say "less than 0.1" instead
  of falsely reporting zero. Constant fits report no fitted change.
- Unavailable regression omits the dataset and explains the project's
  ten-complete-year minimum. A disclosure lists eligible/included years.
- Explanation distinguishes historical OLS from a prediction, causal result,
  or significance claim, and distinguishes regression gaps from consecutive
  five-year rolling windows.
- Incompatible old API responses produce a recoverable message asking the user
  to restart the backend rather than crashing the chart.

## Verification

- Frontend lint and production build passed.
- Six Node tests cover year-based mapping, excluded/outside-year nulls,
  unrounded negative/fractional/zero values, unavailable results, increasing and
  decreasing descriptions, constant and near-zero fits, and included-year count
  with gaps. Run from the project root:

  ```powershell
  node --experimental-strip-types --test frontend/tests/regression.test.mjs
  ```

- Local frontend port 5173 was stopped during implementation. Browser/API
  integration of the new regression overlay has not been verified here. No
  servers were launched, weather/provider calls made, or deployment performed.
- Backend reported 35 offline tests; those were not rerun by the frontend chat.
- Existing root/backend documentation changes belong to the backend handoff and
  are excluded from the frontend commit.

## User test steps

1. Start/restart the latest backend in one PowerShell terminal from project root:

   ```powershell
   .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
   ```

2. Start frontend in another terminal:

   ```powershell
   npm --prefix frontend run dev -- --port 5173 --strictPort
   ```

3. Open http://localhost:5173. Select Delhi, India and analyze 2011–2020.
   If at least ten years are complete, confirm the purple dashed historical
   trend, bars, and rolling average coexist. Hover to inspect fitted values.
   Check the explanation against `regression.change_per_decade` in the Network
   panel's analysis response; its direction should agree and magnitude is rounded
   only in text. Expand the complete-years disclosure.
4. Analyze 2020–2020. Confirm the minimum-year explanation and no historical
   regression dataset/legend entry; the existing bar should remain 1.
5. Switch between those selections to check chart teardown/recreation. Check
   mobile layout and that CSV download still works with the same annual columns.

Constant/decreasing/gapped fits were verified with targeted tests; finding those
patterns in real weather is not required to force additional provider requests.
