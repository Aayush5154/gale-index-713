export type CutoffMode = "daily" | "fixed";

export type ForecastStatus = "available" | "missing_forecast";
export type ComparisonStatus =
  | "matched"
  | "missing_forecast"
  | "missing_actual"
  | "missing_both";

export interface Period {
  from_date: string;
  to_date: string;
}

export interface QuerySummary {
  from_date: string;
  to_date: string;
  timezone: string;
  cutoff_mode: CutoffMode;
  cutoff_time_local: string;
  cutoff_datetime_utc: string | null;
  cutoff_datetime_local: string | null;
  delivery_start_utc: string;
  delivery_end_utc: string;
  delivery_start_local: string;
  delivery_end_local: string;
  expected_intervals: number;
  resolution: string;
}

export interface CoverageSummary {
  expected_intervals: number;
  forecast_available: number;
  missing_forecast: number;
  valid_pairs: number;
  missing_actual: number;
  missing_both: number;
  coverage_percent: number;
  valid_pair_percent: number;
  status_counts: Record<string, number>;
}

export interface DataSource {
  data_mode: "live" | "fixture";
  is_synthetic: boolean;
  source_name: string;
  generated_at_utc: string;
  cache_ttl_seconds: number;
  cache: Record<string, number>;
  fetch: Record<string, number>;
}

export interface IntervalBase {
  delivery_start_utc: string;
  delivery_start_local: string;
  delivery_date_local: string;
  cutoff_utc: string;
  cutoff_local: string;
  status: string;
  forecast_mw: number | null;
  forecast_publication_utc: string | null;
  forecast_publication_local: string | null;
  lead_time_hours: number | null;
  eligible_forecast_count: number;
  duplicate_publication: boolean;
  stale_forecast: boolean;
  previous_publication_utc: string | null;
  previous_forecast_mw: number | null;
}

export interface ForecastInterval extends IntervalBase {
  status: ForecastStatus;
}

export interface ComparisonInterval extends IntervalBase {
  status: ComparisonStatus;
  actual_mw: number | null;
  actual_half_hours: number;
  signed_error_mw: number | null;
  absolute_error_mw: number | null;
  squared_error_mw2: number | null;
  absolute_percentage_error: number | null;
}

export interface HalfHourActual {
  start_utc: string;
  start_local: string;
  generation_mw: number;
  settlement_date: string | null;
  settlement_period: number | null;
}

export interface ForecastSummary {
  expected_intervals: number;
  available: number;
  missing: number;
  coverage_percent: number;
  distinct_publications: number;
  publication_min_utc: string | null;
  publication_min_local: string | null;
  publication_max_utc: string | null;
  publication_max_local: string | null;
  lead_time_min_hours: number | null;
  lead_time_max_hours: number | null;
  duplicate_publication_intervals: number;
  stale_intervals: number;
}

export interface ForecastResponse {
  query: QuerySummary;
  summary: ForecastSummary;
  intervals: ForecastInterval[];
  data_source: DataSource;
  warnings: string[];
  data_quality: Record<string, unknown>;
}

export interface ComparisonResponse {
  query: QuerySummary;
  coverage: CoverageSummary;
  intervals: ComparisonInterval[];
  half_hourly_actuals: HalfHourActual[];
  data_source: DataSource;
  warnings: string[];
  data_quality: Record<string, unknown>;
}

export interface AccuracyMetrics {
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  mape_percent: number | null;
  mape_valid_count: number;
  mape_excluded_count: number;
  max_abs_error_mw: number | null;
  max_abs_error_at_utc: string | null;
  max_abs_error_at_local: string | null;
}

export interface DecisionContext {
  mode: CutoffMode;
  timezone: string;
  cutoff_time_local: string;
  first_cutoff_utc: string;
  first_cutoff_local: string;
  last_cutoff_utc: string;
  last_cutoff_local: string;
  fixed_cutoff_utc: string | null;
  fixed_cutoff_local: string | null;
  rule: string;
  distinct_publications: number;
  earliest_publication_utc: string | null;
  latest_publication_utc: string | null;
  lead_time_min_hours: number | null;
  lead_time_max_hours: number | null;
}

export interface HistogramBin {
  lower_mw: number;
  upper_mw: number;
  count: number;
  signed_side: "overforecast" | "underforecast" | "straddles_zero";
}

export interface ErrorHistogram {
  bin_width_mw: number;
  total_pairs: number;
  bins: HistogramBin[];
}

export interface MetricsResponse {
  query: QuerySummary;
  coverage: CoverageSummary;
  metrics: AccuracyMetrics;
  decision_context: DecisionContext;
  histogram: ErrorHistogram;
  data_source: DataSource;
  warnings: string[];
  data_quality: Record<string, unknown>;
}

export interface DailyMetric {
  date: string;
  expected_intervals: number;
  forecast_available: number;
  valid_pairs: number;
  missing_forecast: number;
  missing_actual: number;
  missing_both: number;
  coverage_percent: number;
  valid_pair_percent: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  mape_percent: number | null;
  mape_valid_count: number;
  mape_excluded_count: number;
  max_abs_error_mw: number | null;
}

export interface DailyMetricsResponse {
  query: QuerySummary;
  coverage: CoverageSummary;
  daily: DailyMetric[];
  warnings: string[];
}

export interface MetricDefinition {
  key: string;
  label: string;
  formula: string;
  unit: string;
  interpretation: string;
}

export interface DatasetField {
  name: string;
  description: string;
}

export interface DatasetInfo {
  key: string;
  name: string;
  description: string;
  endpoint: string;
  documentation_url: string;
  resolution: string;
  fields: DatasetField[];
}

export interface DataQualityRule {
  topic: string;
  handling: string;
}

export interface MetadataResponse {
  app_name: string;
  version: string;
  environment: string;
  data_mode: "live" | "fixture";
  is_synthetic: boolean;
  timezone: string;
  generated_at_utc: string;
  target_period: Period;
  supported_range: Period | null;
  supported_range_note: string;
  max_range_days: number;
  cutoff: {
    default_mode: CutoffMode;
    default_time_local: string;
    timezone: string;
    rule: string;
    reference: string;
    reference_url: string;
    alternatives: string[];
  };
  resolution: {
    forecast: string;
    actual: string;
    comparison: string;
    explanation: string;
  };
  units: {
    generation: string;
    energy: string;
    note: string;
  };
  datasets: DatasetInfo[];
  metric_definitions: MetricDefinition[];
  data_quality_rules: DataQualityRule[];
  limitations: string[];
}

export interface DependencyStatus {
  name: string;
  configured: boolean;
  status: "ok" | "fixture" | "not_yet_called" | "degraded" | "unavailable" | string;
  last_success_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  app_name: string;
  version: string;
  environment: string;
  data_mode: "live" | "fixture";
  is_synthetic: boolean;
  timezone: string;
  timestamp_utc: string;
  dependencies: DependencyStatus[];
  cache: Record<string, number>;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface AnalysisParams {
  from_date: string;
  to_date: string;
  cutoff_mode: CutoffMode;
  cutoff_time: string;
  cutoff_datetime?: string;
}
