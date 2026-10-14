import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'
import type { AnalysisResult } from '../../types'
import { describeRegression, historicalTrendValues } from '../../utils/regression'

export default function FrequencyChart({
  result,
}: {
  result: AnalysisResult
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current) return

    const chart = new Chart<
      'bar' | 'line',
      (number | null)[],
      string
    >(canvasRef.current, {
      type: 'bar',
      data: {
        labels: result.annual.map((row) => String(row.year)),
        datasets: [
          {
            type: 'bar',
            label: 'Annual event starts',
            data: result.annual.map(
              (row) => row.events_starting_in_selection,
            ),
            backgroundColor: '#3a9273',
            borderRadius: 3,
            maxBarThickness: 48,
            order: 2,
          },
          {
            type: 'line',
            label: 'Trailing 5-year average',
            data: result.rolling_averages.map(
              (row) => row.events_starting_average,
            ),
            borderColor: '#d28a35',
            backgroundColor: '#d28a35',
            spanGaps: false,
            tension: 0,
            order: 1,
          },
          ...(result.regression.status === 'available' ? [{
            type: 'line' as const,
            label: 'Historical linear trend',
            data: historicalTrendValues(result),
            borderColor: '#7756a8',
            backgroundColor: '#7756a8',
            borderDash: [6, 4],
            pointRadius: 2,
            spanGaps: false,
            tension: 0,
            order: 0,
          }] : []),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { title: { display: true, text: 'Year' } },
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Event starts' },
          },
        },
      },
    })

    return () => chart.destroy()
  }, [result])

  return (
    <section className="panel">
      <h2>Heatwaves starting each year</h2>
      <p>Each event is counted in the year it begins.</p>

      <div className="chart-container">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={result.regression.status === 'available'
            ? 'Annual heatwave starts, trailing five-year average, and historical linear trend'
            : 'Annual heatwave starts and trailing five-year average; historical linear trend unavailable'}
        />
      </div>

      <p className="note">
        Missing values are unavailable, not zero. Rolling averages require
        five complete consecutive years.
      </p>
      <p className="note">
        {describeRegression(result.regression, result.request.start_year, result.request.end_year)}
      </p>
      <p className="note">
        Ordinary least squares uses actual calendar years and excludes incomplete
        or unknown counts; included years may have gaps. The ten-complete-year
        minimum is a project rule. This summarizes historical data, not a
        prediction, causal conclusion, or statistical-significance claim. Fitted
        counts can be fractional or negative; they are not observed counts.
      </p>
      {result.regression.years_used.length > 0 && (
        <details>
          <summary>
            {result.regression.status === 'available'
              ? 'Complete years used in the historical fit'
              : 'Complete years eligible for a historical fit'}
          </summary>
          <p>{result.regression.years_used.join(', ')}</p>
        </details>
      )}
    </section>
  )
}
