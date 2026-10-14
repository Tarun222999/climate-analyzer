import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'
import type { AnalysisResult } from '../../types'

export default function TemperatureChart({
  result,
}: {
  result: AnalysisResult
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current) return

    const chart = new Chart<'line', (number | null)[], string>(
      canvasRef.current,
      {
        type: 'line',
        data: {
          labels: result.annual.map((row) => String(row.year)),
          datasets: [{
            label: 'Annual heatwave peak',
            data: result.annual.map((row) => row.peak_temperature_c),
            borderColor: '#3a9273',
            backgroundColor: '#3a9273',
            pointBackgroundColor: result.annual.map((row) =>
              row.metrics_complete ? '#3a9273' : '#d28a35',
            ),
            pointRadius: 4,
            pointHoverRadius: 6,
            spanGaps: false,
            tension: 0,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: { title: { display: true, text: 'Year' } },
            y: { title: { display: true, text: 'Temperature (°C)' } },
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  const row = result.annual[context.dataIndex]
                  const label = row.metrics_complete
                    ? 'Peak heatwave temperature'
                    : 'Observed peak (incomplete year)'
                  return `${label}: ${row.peak_temperature_c?.toFixed(1)}°C`
                },
              },
            },
          },
        },
      },
    )

    return () => chart.destroy()
  }, [result])

  return (
    <section className="panel">
      <h2>Peak heatwave temperature each year</h2>
      <p>Highest daily maximum temperature during detected heatwaves.</p>

      <div className="chart-container">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="Annual peak heatwave temperatures in Celsius; amber points indicate incomplete years"
        />
      </div>

      {result.annual.every((row) => row.peak_temperature_c === null) && (
        <p className="note">No detected heatwave peaks are available to plot.</p>
      )}
      <p className="note">
        Gaps mean no detected heatwave peak is available. Amber points mark
        incomplete years: their observed peaks may not be the whole-year
        maxima during heatwaves. No rolling temperature average is provided.
      </p>
    </section>
  )
}
