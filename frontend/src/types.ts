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
  }