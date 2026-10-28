import type { ComparisonInterval, DailyMetric, HalfHourActual, HistogramBin } from "../../types/api";

export interface ForecastChartPoint {
  ts: number;
  actual: number | null;
  forecast: number | null;
  interval: ComparisonInterval | null;
}

export interface DailyChartPoint {
  date: string;
  mae: number | null;
  mbe: number | null;
  coverage: number;
  pairs: number;
  missingForecast: number;
  missingActual: number;
}

export interface HistogramChartPoint {
  mid: number;
  label: string;
  lower: number;
  upper: number;
  count: number;
  side: HistogramBin["signed_side"];
  total: number;
}

export function buildForecastChartPoints(
  intervals: ComparisonInterval[],
  actuals: HalfHourActual[],
): ForecastChartPoint[] {
  const points = new Map<number, ForecastChartPoint>();

  for (const interval of intervals) {
    const ts = Date.parse(interval.delivery_start_utc);
    if (Number.isNaN(ts)) continue;
    points.set(ts, {
      ts,
      actual: null,
      forecast: interval.forecast_mw,
      interval,
    });
  }

  for (const actual of actuals) {
    const ts = Date.parse(actual.start_utc);
    if (Number.isNaN(ts)) continue;
    const existing = points.get(ts);
    if (existing) {
      existing.actual = actual.generation_mw;
    } else {
      points.set(ts, {
        ts,
        actual: actual.generation_mw,
        forecast: null,
        interval: null,
      });
    }
  }

  return [...points.values()].sort((a, b) => a.ts - b.ts);
}

export function buildDailyChartPoints(daily: DailyMetric[]): DailyChartPoint[] {
  return daily.map((day) => ({
    date: day.date,
    mae: day.mae_mw,
    mbe: day.mbe_mw,
    coverage: day.coverage_percent,
    pairs: day.valid_pairs,
    missingForecast: day.missing_forecast,
    missingActual: day.missing_actual,
  }));
}

export function buildHistogramChartPoints(
  bins: HistogramBin[],
  total: number,
): HistogramChartPoint[] {
  return bins.map((bin) => ({
    mid: Math.round((bin.lower_mw + bin.upper_mw) / 2),
    label: String(Math.round((bin.lower_mw + bin.upper_mw) / 2)),
    lower: bin.lower_mw,
    upper: bin.upper_mw,
    count: bin.count,
    side: bin.signed_side,
    total,
  }));
}
