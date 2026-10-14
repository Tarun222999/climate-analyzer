
import type {
    AnalysisRequest,
    AnalysisResult,
    LocationMatch,
  } from '../types'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')



export async function searchLocations(
  query: string,
  signal?: AbortSignal,
): Promise<LocationMatch[]> {
  const params = new URLSearchParams({ query })
  const timeout = AbortSignal.timeout(20_000)
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout

  try {
  const response = await fetch(
    `${API_BASE_URL}/api/locations?${params}`,
    { signal: requestSignal },
  )

  if (!response.ok) {
    if (response.status === 429) {
      throw new Error('Too many city searches. Please wait before trying again.')
    }

    if (response.status === 503 || response.status === 504) {
      throw new Error('City search is temporarily unavailable. Please try again later.')
    }

    throw new Error('Unable to search for cities. Please try again.')
  }

  const matches = await response.json() as LocationMatch[]
  if (!Array.isArray(matches)) throw new Error('City search returned an invalid response. Please retry.')
  return matches
  } catch (err) {
    if (signal?.aborted) throw err
    if (timeout.aborted) {
      throw new Error('City search timed out. Please retry.', { cause: err })
    }
    if (err instanceof SyntaxError) {
      throw new Error('City search returned an invalid response. Please retry.', { cause: err })
    }
    throw err
  }
}


export async function analyzeLocation(
    request: AnalysisRequest,
  ): Promise<AnalysisResult> {
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 200_000)
  
    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          location: {
            name: request.location.name,
            latitude: request.location.latitude,
            longitude: request.location.longitude,
            timezone: request.location.timezone,
          },
          start_year: request.start_year,
          end_year: request.end_year,
        }),
      })
  
      if (!response.ok) {
        const messages: Record<number, string> = {
          422: 'Invalid selection. Check the city and year range.',
          429: 'Too many analysis requests. Please try again later.',
          502: 'Weather data could not be retrieved or processed.',
          503: 'Analysis is temporarily unavailable. Please try again later.',
          504: 'Analysis timed out. Retrieved weather remains cached; try again later.',
        }
  
        const retryAfter = response.headers.get('Retry-After')
        const seconds = retryAfter === null ? NaN : Number(retryAfter)
        const retryHint = Number.isFinite(seconds) && seconds > 0
          ? ` Wait at least ${Math.ceil(seconds)} seconds before retrying.`
          : ''
  
        throw new Error(
          (messages[response.status] || 'Analysis failed. Please try again.')
            + retryHint,
        )
      }
  
      const result = await response.json() as AnalysisResult
      if (
        result.analysis_version !== 'analysis-v2' ||
        !result.regression ||
        !['available', 'unavailable'].includes(result.regression.status)
      ) {
        throw new Error('The API returned an incompatible analysis response. Restart the backend with the latest regression code and retry.')
      }
      return result
    } catch (err) {
        if (controller.signal.aborted) {
          throw new Error(
            'The request timed out. Please try again later.',
            { cause: err },
          )
        }
      
        if (err instanceof TypeError) {
          throw new Error(
            'Cannot reach the API. Check your connection and backend.',
            { cause: err },
          )
        }
        if (err instanceof SyntaxError) {
          throw new Error('The API returned an invalid response. Please try again.', { cause: err })
        }
      
        throw err
    } finally {
      window.clearTimeout(timer)
    }
  }
