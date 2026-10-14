import { useRef, useState } from 'react'
import { analyzeLocation } from './api'
import CitySearch from './CitySearch'
import type { AnalysisResult, LocationMatch } from './types'
import ResultSummary from './ResultSummary'
import FrequencyChart from './FrequencyChart'
import HeatwaveDaysChart from './HeatwaveDaysChart'
import DurationChart from './DurationChart'
import TemperatureChart from './TemperatureChart'
import './App.css'

export default function App() {
  const [location, setLocation] = useState<LocationMatch | null>(null)
  const [startYear, setStartYear] = useState('2015')
  const [endYear, setEndYear] = useState('2024')
  const [formError, setFormError] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const submitting = useRef(false)

  return (
    <>
      <header>
        <div className="brand">◒ Climate Analyzer</div>
        <span className="badge">Historical heatwaves</span>
      </header>

      <main>
        <div className="intro">
          <h1>Explore heatwaves over time.</h1>
          <p>
            Choose a city and compare historical heatwave frequency,
            duration, and intensity.
          </p>
        </div>

        <section className="panel" aria-label="Analysis settings">
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              if (submitting.current) return
              setFormError('')
              setStatus('')

              const start = Number(startYear)
              const end = Number(endYear)

              if (!location) {
                setFormError('Select a city from the search results.')
                return
              }

              if (
                !startYear || !endYear ||
                !Number.isInteger(start) || !Number.isInteger(end) ||
                start < 1950 || start > 2025 ||
                end < 1950 || end > 2025
              ) {
                setFormError('Enter whole years between 1950 and 2025.')
                return
              }

              if (end < start) {
                setFormError('End year must be at least the start year.')
                return
              }

              if (end - start + 1 > 30) {
                setFormError('Select at most 30 years.')
                return
              }

              submitting.current = true
              setLoading(true)
              setResult(null)
              setStatus(
                'Analyzing historical weather. A first analysis may take up to three minutes.',
              )

              try {
                const data = await analyzeLocation({
                  location,
                  start_year: start,
                  end_year: end,
                })

                setResult(data)
                setStatus('Analysis complete.')
              } catch (err) {
                setStatus('')
                setFormError(
                  err instanceof Error ? err.message : 'Analysis failed.',
                )
              } finally {
                submitting.current = false
                setLoading(false)
              }
            }}
          >
            <CitySearch
              onSelect={(city) => {
                setLocation(city)
                setFormError('')
                if (!submitting.current) setStatus('')
              }}
            />

            <div>
              <label htmlFor="hazard">Hazard</label>
              <select id="hazard">
                <option>Heatwave</option>
              </select>
            </div>

            <div>
              <label htmlFor="start-year">Start year</label>
              <input
                id="start-year"
                type="number"
                min={1950}
                max={2025}
                step={1}
                required
                value={startYear}
                onChange={(event) => setStartYear(event.target.value)}
              />
            </div>

            <div>
              <label htmlFor="end-year">End year</label>
              <input
                id="end-year"
                type="number"
                min={1950}
                max={2025}
                step={1}
                required
                value={endYear}
                onChange={(event) => setEndYear(event.target.value)}
              />
            </div>

            <button type="submit" disabled={loading}>
              {loading ? 'Analyzing…' : 'Analyze →'}
            </button>
          </form>

          {location && (
            <p className="note">
              Selected: {[location.name, location.admin1, location.country]
                .filter(Boolean)
                .join(', ')}
            </p>
          )}

          {formError && <p className="note" role="alert">{formError}</p>}
          <p className="note" role="status">{status}</p>
        </section>
        {result && (
          <>
            <ResultSummary result={result} />
            <div className="charts">
              <FrequencyChart result={result} />
              <HeatwaveDaysChart result={result} />
              <DurationChart result={result} />
              <TemperatureChart result={result} />
            </div>
          </>
        )}
      </main>
    </>
  )
}
