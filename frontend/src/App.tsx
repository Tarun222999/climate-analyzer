import { useState } from 'react'
import CitySearch from './CitySearch'
import type { LocationMatch } from './types'
import './App.css'

export default function App() {
  const [location, setLocation] = useState<LocationMatch | null>(null)
  const [startYear, setStartYear] = useState('2015')
  const [endYear, setEndYear] = useState('2024')
  const [formError, setFormError] = useState('')
  const [status, setStatus] = useState('')

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
            onSubmit={(event) => {
              event.preventDefault()
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

              setStatus('Selection is valid. Analysis connection comes next.')
            }}
          >
            <CitySearch onSelect={setLocation} />

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

            <button type="submit">Analyze →</button>
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
      </main>
    </>
  )
}
