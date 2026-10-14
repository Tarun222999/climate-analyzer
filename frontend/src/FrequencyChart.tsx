import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'
import type { AnalysisResult } from './types'

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
          aria-label="Annual heatwave starts and trailing five-year average"
        />
      </div>

      <p className="note">
        Missing values are unavailable, not zero. Rolling averages require
        five complete consecutive years.
      </p>
    </section>
  )
}
