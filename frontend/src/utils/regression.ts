import type { AnalysisResult, HeatwaveRegression } from '../types'

export function historicalTrendValues(
  result: Pick<AnalysisResult, 'annual' | 'regression'>,
): (number | null)[] {
  const fittedByYear = new Map(
    result.regression.fitted_values.map((point) => [
      point.year,
      point.fitted_event_starts,
    ] as const),
  )
  return result.annual.map((row) => fittedByYear.get(row.year) ?? null)
}

export function describeRegression(
  regression: HeatwaveRegression,
  startYear: number,
  endYear: number,
): string {
  const count = regression.years_used.length
  const context = `Using ${count} complete ${count === 1 ? 'year' : 'years'} within the selected ${startYear}–${endYear} period.`

  if (regression.status === 'unavailable') {
    return `Historical linear trend unavailable: at least ${regression.minimum_complete_years} complete years with known heatwave counts are required. ${context}`
  }

  const change = regression.change_per_decade
  if (change === 0) {
    return `The fitted annual event count showed no change over the analyzed years (0.0 events per decade). ${context}`
  }

  const magnitude = Math.abs(change).toFixed(1)
  const amount = magnitude === '0.0' ? 'less than 0.1' : `an estimated ${magnitude}`
  const direction = change > 0 ? 'rose' : 'fell'
  return `The fitted annual event count ${direction} by ${amount} events per decade over the analyzed years. ${context}`
}
