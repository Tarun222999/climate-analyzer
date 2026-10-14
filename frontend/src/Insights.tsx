import type { AnalysisResult } from './types'

export default function Insights({ result }: { result: AnalysisResult }) {
  const { start_year, end_year } = result.request
  const hasComparisonRange = end_year - start_year + 1 >= 10

  return (
    <section className="panel insight analysis-insights">
      <h2>What the results tell us</h2>

      {result.insights.length > 0 ? (
        <ul className="insight-list">
          {result.insights.map((insight) => (
            <li key={insight}>{insight}</li>
          ))}
        </ul>
      ) : (
        <p>No comparison insights are available for this result.</p>
      )}

      {hasComparisonRange && (
        <p className="note">
          Comparison periods: {start_year}–{start_year + 4} and{' '}
          {end_year - 4}–{end_year}. Years between these periods are not part
          of the comparison.
        </p>
      )}
      <p className="note">
        Comparisons require at least ten selected years and complete metrics in
        both five-year periods. Percentage change is unavailable when the earlier
        average is zero. These descriptive comparisons do not establish
        causality or statistical significance.
      </p>
    </section>
  )
}
