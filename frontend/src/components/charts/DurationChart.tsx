import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'
import type { AnalysisResult } from '../../types'

export default function DurationChart({
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
            label: 'Annual longest duration',
            data: result.annual.map(
              (row) => row.longest_duration_in_selection_days,
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
              (row) => row.longest_duration_average_days,
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
            title: { display: true, text: 'Days' },
          },
        },
      },
    })

    return () => chart.destroy()
  }, [result])

  return (
    <section className="panel">
      <h2>Longest heatwave duration each year</h2>
      <p>Longest event portion within each calendar year.</p>

      <div className="chart-container">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="Annual longest heatwave duration and trailing five-year average"
        />
      </div>

      <p className="note">
        Events crossing year boundaries contribute their days to each year.
        The rolling line averages five annual longest durations, not full event
        lengths. Unavailable values remain gaps.
      </p>
    </section>
  )
}


