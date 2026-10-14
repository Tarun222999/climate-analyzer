import type { AnalysisResult, SelectedHeatwaveEvent } from '../types'

function boundaryNotes(event: SelectedHeatwaveEvent) {
  const notes: string[] = []
  if (!event.start_boundary_resolved) notes.push('Actual start unresolved')
  if (!event.end_boundary_resolved) notes.push('Actual end unresolved')
  if (event.starts_before_selection === true) notes.push('Starts before selection')
  if (event.ends_after_selection === true) notes.push('Ends after selection')
  if (event.starts_before_selection === null) {
    notes.push('Start relative to selection unknown')
  }
  if (event.ends_after_selection === null) {
    notes.push('End relative to selection unknown')
  }
  return notes.length ? notes.join('; ') : 'Fully within selection'
}

export default function EventDetails({ result }: { result: AnalysisResult }) {
  const events = [...result.events].sort((a, b) =>
    b.observed_end_date.localeCompare(a.observed_end_date),
  )

  return (
    <section className="panel">
      <h2>Heatwave events overlapping selected years</h2>
      <p>
        Latest events first. This table includes events starting before the
        selection; the summary counts only starts within selected years.
      </p>

      {events.length === 0 ? (
        <p className="note">
          {result.summary.metrics_complete
            ? 'No heatwave events overlap the selected years.'
            : 'No confirmed events were detected. Incomplete data prevents concluding there were no heatwaves.'}
        </p>
      ) : (
        <div
          className="event-table-scroll"
          role="region"
          aria-label="Heatwave event details; scroll horizontally on smaller screens"
          tabIndex={0}
        >
          <table className="event-table">
            <thead>
              <tr>
                <th scope="col">Observed dates</th>
                <th scope="col">Dates in selection</th>
                <th scope="col">Days in selection</th>
                <th scope="col">Full duration</th>
                <th scope="col">Peak in selection</th>
                <th scope="col">Boundaries</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={`${event.observed_start_date}/${event.observed_end_date}`}>
                  <td>
                    {event.observed_start_date} to {event.observed_end_date}
                    <small className="event-detail-note">
                      {event.observed_duration_days} observed days
                    </small>
                  </td>
                  <td>{event.selected_start_date} to {event.selected_end_date}</td>
                  <td>{event.days_in_selection} days</td>
                  <td>
                    {event.full_duration_days === null
                      ? 'Unknown'
                      : `${event.full_duration_days} days`}
                  </td>
                  <td>{event.peak_temperature_in_selection_c.toFixed(1)}°C</td>
                  <td>{boundaryNotes(event)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="note">
        Dates use the location’s calendar (YYYY-MM-DD). Observed dates show the
        detected hot run; its actual start or end may be unresolved. Full
        duration is available only when both boundaries are resolved. Days and
        peaks in selection cover only selected dates.
      </p>
    </section>
  )
}
