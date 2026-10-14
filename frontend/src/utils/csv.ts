import type { AnalysisResult } from '../types'


export type CsvCell = string | number | boolean | null

export function encodeCsvCell(value: CsvCell): string {
  if (value === null) return ''

  let text = String(value)

  // Protect text fields without changing legitimate negative numbers.
  if (
    typeof value === 'string' &&
    /^[\t\r\n]|^\s*[=+\-@＝＋－＠]/u.test(text)
  ) {
    text = `'${text}`
  }

  return `"${text.replace(/"/g, '""')}"`
}



export function buildAnalysisCsv(result: AnalysisResult): string {
    const { request, baseline } = result

    const headers = [
      'location_name',
      'latitude',
      'longitude',
      'timezone',
      'selected_start_year',
      'selected_end_year',
      'baseline_start_year',
      'baseline_end_year',
      'baseline_percentile',
      'baseline_percentile_method',
      'baseline_threshold_c',
      'source',
      'dataset',
      'grid_latitude',
      'grid_longitude',
      'year',
      'heatwaves_starting_in_year',
      'heatwave_days_in_year',
      'longest_event_portion_in_year_days',
      'peak_heatwave_temperature_c',
      'peak_above_threshold_c',
      'expected_days',
      'valid_days',
      'metrics_complete',
      'peak_interpretation',
      'blank_metric_meaning',
    ]

    const rows: CsvCell[][] = result.annual.map((year) => [
      request.location.name,
      request.location.latitude,
      request.location.longitude,
      request.location.timezone,
      request.start_year,
      request.end_year,
      baseline.baseline_start_year,
      baseline.baseline_end_year,
      baseline.percentile,
      baseline.percentile_method,
      baseline.threshold_c,
      baseline.source,
      baseline.dataset,
      baseline.grid_latitude,
      baseline.grid_longitude,
      year.year,
      year.events_starting_in_selection,
      year.heatwave_days,
      year.longest_duration_in_selection_days,
      year.peak_temperature_c,
      year.peak_above_threshold_c,
      year.expected_days,
      year.valid_days,
      year.metrics_complete,
      year.peak_temperature_c === null
        ? 'no_detected_heatwave_peak'
        : year.metrics_complete
          ? 'maximum_during_heatwaves_in_year'
          : 'observed_peak_not_guaranteed_whole_year_maximum',
      'unavailable_not_zero',
    ])

    return [headers, ...rows]
      .map((row) => row.map(encodeCsvCell).join(','))
      .join('\r\n') + '\r\n'
  }



  export function downloadAnalysisCsv(result: AnalysisResult): void {
    const csv = buildAnalysisCsv(result)
    const blob = new Blob(['\uFEFF', csv], {
      type: 'text/csv;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    const city = result.request.location.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'location'

    link.href = url
    link.download =
      `heatwaves-${city}-${result.request.start_year}-${result.request.end_year}.csv`

    document.body.appendChild(link)

    try {
      link.click()
    } finally {
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
  }
