import type { AnalysisResult } from './types'

export default function ResultSummary({
  result,
}: {
  result: AnalysisResult
}) {
  const { summary, request } = result

  function format(value: number | null, unit = '') {
    return value === null ? 'Unavailable' : `${value}${unit}`
  }

  const cards = [
    {
      label: 'Heatwaves starting in selection',
      value: format(summary.events_starting_in_selection),
      note: 'Events counted by their starting date',
    },
    {
      label: 'Heatwave days',
      value: format(summary.heatwave_days),
      note: 'Qualifying days within selected years',
    },
    {
      label: 'Longest duration in selection',
      value: format(summary.longest_duration_in_selection_days, ' days'),
      note: 'Event portion within selected years',
    },
    {
      label: summary.metrics_complete
        ? 'Peak heatwave temperature'
        : 'Observed peak heatwave temperature',
      value: summary.peak_temperature_c === null
        ? 'Unavailable'
        : `${summary.peak_temperature_c.toFixed(1)}°C`,
      note: 'During heatwaves within selected years',
    },
  ]

  return (
    <>
      <div className="results-title">
        <div>
          <h2>{request.location.name}</h2>
          <p>
            {request.start_year}–{request.end_year} · Heatwave analysis
          </p>
        </div>
        <span className="badge">
          {summary.metrics_complete ? 'Complete metrics' : 'Incomplete metrics'}
        </span>
      </div>

      <section className="cards" aria-label="Heatwave summary">
        {cards.map((card) => (
          <div className="panel stat" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <small>{card.note}</small>
          </div>
        ))}
      </section>

      <p className="note">
        Valid daily readings: {summary.valid_days.toLocaleString()}
        {' / '}{summary.expected_days.toLocaleString()}.
      </p>

      {!summary.metrics_complete && (
        <p className="note">
          Missing readings or unresolved event boundaries make some metrics
          unavailable. The observed peak may not be the whole-period maximum.
        </p>
      )}

      {summary.metrics_complete && summary.heatwave_days === 0 && (
        <p className="note">
          No qualifying heatwave days were detected in the selected years.
        </p>
      )}
    </>
  )
}