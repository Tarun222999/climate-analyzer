export interface Location {
    name: string
    latitude: number
    longitude: number
    timezone: string
  }
  
  export interface LocationMatch extends Location {
    id: number
    country: string | null
    admin1: string | null
  }
  
  export interface AnalysisRequest {
    location: Location
    start_year: number
    end_year: number
  }



  export interface HeatwaveSummary {
    events_starting_in_selection: number | null
    heatwave_days: number | null
    longest_duration_in_selection_days: number | null
    peak_temperature_c: number | null
    peak_above_threshold_c: number | null
    expected_days: number
    valid_days: number
    metrics_complete: boolean
  }
  
  export interface AnalysisResult {
    request: AnalysisRequest
    summary: HeatwaveSummary
    calculated_at: string
    annual: AnnualHeatwaveMetrics[]
    rolling_averages: RollingHeatwaveMetrics[]
    events: SelectedHeatwaveEvent[]
    baseline: BaselineThreshold
    minimum_consecutive_days: 3
    threshold_comparison: 'strictly_above'
    insights: string[]
  }



  export interface AnnualHeatwaveMetrics extends HeatwaveSummary {
    year: number
  }
  
  export interface RollingHeatwaveMetrics {
    year: number
    window_years: 5
    events_starting_average: number | null
    heatwave_days_average: number | null
    longest_duration_average_days: number | null
  }

export interface SelectedHeatwaveEvent {
  observed_start_date: string
  observed_end_date: string
  observed_duration_days: number
  peak_temperature_c: number
  start_boundary_resolved: boolean
  end_boundary_resolved: boolean
  selected_start_date: string
  selected_end_date: string
  days_in_selection: number
  peak_temperature_in_selection_c: number
  full_duration_days: number | null
  starts_before_selection: boolean | null
  ends_after_selection: boolean | null
}

export interface BaselineThreshold {
  location: Location
  grid_latitude: number
  grid_longitude: number
  timezone: string
  source: 'open-meteo'
  dataset: 'era5_land'
  temperature_unit: 'celsius'
  baseline_start_year: 1991
  baseline_end_year: 2020
  percentile: 95
  percentile_method: 'linear'
  baseline_version: 'baseline-v1'
  threshold_c: number
  expected_days: 10958
  valid_days: number
  calculated_at: string
}
