import type { AnalysisResult } from './types'

export default function Methodology({ result }: { result: AnalysisResult }) {
  const { baseline, summary, request } = result
  const baselineCoverage = 100 * baseline.valid_days / baseline.expected_days
  const selectionCoverage = 100 * summary.valid_days / summary.expected_days
  const incompleteYears = result.annual.filter((row) => !row.metrics_complete)

  return (
    <section className="panel methodology">
      <h2>Methodology and data quality</h2>
      <p>
        A heatwave requires at least {result.minimum_consecutive_days} consecutive
        calendar days with daily maximum temperature strictly above{' '}
        <strong>{baseline.threshold_c.toFixed(1)}°C</strong>. A day equal to
        the threshold does not qualify. Comparisons use the unrounded threshold.
      </p>

      <div className="methodology-grid">
        <div>
          <h3>Fixed baseline</h3>
          <p>
            {baseline.baseline_start_year}–{baseline.baseline_end_year}, independent
            of selected years. The threshold is the {baseline.percentile}th
            percentile of valid daily maximum temperatures, calculated with
            NumPy’s {baseline.percentile_method} method.
          </p>
          <p className="note">
            Baseline coverage: {baseline.valid_days.toLocaleString()} /{' '}
            {baseline.expected_days.toLocaleString()} valid days
            ({baselineCoverage.toFixed(2)}%). At least 95% is required.
          </p>
        </div>

        <div>
          <h3>Selected-period coverage</h3>
          <p>
            {summary.valid_days.toLocaleString()} /{' '}
            {summary.expected_days.toLocaleString()} valid days
            ({selectionCoverage.toFixed(2)}%).{' '}
            {result.annual.length - incompleteYears.length} /{' '}
            {result.annual.length} years have complete metrics.
          </p>
          {incompleteYears.length > 0 && (
            <p className="note">
              Years with incomplete metrics:{' '}
              {incompleteYears.map((row) => row.year).join(', ')}.
            </p>
          )}
          <p className="note">
            Missing or invalid readings break hot runs. Complete metrics also
            require resolved classification at relevant boundaries, so 100%
            daily coverage alone does not guarantee complete metrics.
          </p>
        </div>
      </div>

      <details>
        <summary>Event counts and rolling averages</summary>
        <p>
          Events can cross December 31. Each event is counted in its starting
          year; heatwave days belong to the year they occur. Summary durations
          and peaks cover selected dates only. Full event duration is unknown
          until both boundaries are resolved. Null means unavailable, not zero.
        </p>
        <p>
          Trailing five-year averages require five complete consecutive selected
          years. Duration averages use each year’s longest event portion.
          Observed peaks in incomplete years may not be the whole-year maxima
          during heatwaves.
        </p>
      </details>

      <details>
        <summary>Weather source and limitations</summary>
        <p>
          Source: <a
            href="https://open-meteo.com/en/docs/historical-weather-api"
            target="_blank"
            rel="noopener noreferrer"
          >Open-Meteo historical weather</a>, dataset {baseline.dataset}
          {' '}(ERA5-Land), daily temperature_2m_max in {baseline.temperature_unit}.
          Reanalysis combines observations and models; it is not a local station
          measurement or an average across the city.
        </p>
        <p>
          Selected coordinates: {request.location.latitude.toFixed(4)},{' '}
          {request.location.longitude.toFixed(4)}. Weather grid coordinates:{' '}
          {baseline.grid_latitude.toFixed(4)}, {baseline.grid_longitude.toFixed(4)}.
          Calendar timezone: {baseline.timezone}.
        </p>
        <p>
          One annual threshold mixes seasons and may miss changes relative to
          seasonal expectations. Missing neighboring data, dataset edges, or
          lookup limits may leave event boundaries unresolved.
        </p>
      </details>
    </section>
  )
}
