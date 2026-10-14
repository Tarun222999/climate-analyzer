import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'
import type { AnalysisResult } from '../../types'

export default function HeatwaveDaysChart({
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
            label: 'Annual heatwave days',
            data: result.annual.map(
              (row) => row.heatwave_days,
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
              (row) => row.heatwave_days_average,
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
      <h2>Heatwave days each year</h2>
      <p>Qualifying days are assigned to the year they occur.</p>

      <div className="chart-container">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="Annual heatwave days and trailing five-year average"
        />
      </div>

      <p className="note">
        Missing values are unavailable, not zero. Rolling averages require
        five complete consecutive years.
      </p>
    </section>
  )
}

