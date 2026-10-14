import { useEffect, useState } from 'react'
import { searchLocations } from './api'
import type { LocationMatch } from './types'

interface Props {
  onSelect: (location: LocationMatch | null) => void
}

export default function CitySearch({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<LocationMatch | null>(null)
  const [matches, setMatches] = useState<LocationMatch[]>([])
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [retryAttempt, setRetryAttempt] = useState(0)

  useEffect(() => {
    const term = query.trim()
    if (term.length < 2 || selected) return

    const controller = new AbortController()

    const timer = window.setTimeout(async () => {
      setStatus('Searching…')
      setError('')

      try {
        const results = await searchLocations(term, controller.signal)
        if (controller.signal.aborted) return

        setMatches(results)
        setStatus(results.length ? 'Choose a city below.' : 'No cities found.')
      } catch (err) {
        if (controller.signal.aborted) return

        setStatus('')
        setError(
          err instanceof TypeError
            ? 'Cannot reach city search. Check that the backend is running.'
            : err instanceof Error
              ? err.message
              : 'City search failed.',
        )
      }
    }, 500)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, selected, retryAttempt])

  function chooseCity(city: LocationMatch) {
    setSelected(city)
    setQuery(city.name)
    setMatches([])
    setStatus('City selected.')
    setError('')
    onSelect(city)
  }

  return (
    <div className="city">
      <label htmlFor="city">City</label>
      <input
        id="city"
        value={query}
        placeholder="Search for a city"
        maxLength={100}
        autoComplete="off"
        aria-describedby="city-status"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setMatches([])
            setStatus('')
          }
        }}
        onChange={(event) => {
          setQuery(event.target.value)
          setSelected(null)
          setMatches([])
          setStatus('')
          setError('')
          onSelect(null)
        }}
      />

      <p id="city-status" role="status">{status}</p>
      {error && (
        <>
          <p role="alert">{error}</p>
          <button
            className="search-retry"
            type="button"
            onClick={() => setRetryAttempt((attempt) => attempt + 1)}
          >
            Retry city search
          </button>
        </>
      )}

      {matches.length > 0 && (
        <ul aria-label="Matching cities">
          {matches.map((city) => (
            <li key={city.id}>
              <button type="button" onClick={() => chooseCity(city)}>
                {[city.name, city.admin1, city.country]
                  .filter(Boolean)
                  .join(', ')}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
