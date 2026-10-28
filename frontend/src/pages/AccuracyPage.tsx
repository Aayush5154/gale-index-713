import { ArrowUpRight, BarChart3, Download } from "lucide-react";
import { useMemo } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { DailyMaeChart } from "../components/charts/DailyMaeChart";
import { ErrorHistogram } from "../components/charts/ErrorHistogram";
import {
  buildDailyChartPoints,
  buildHistogramChartPoints,
} from "../components/charts/chartData";
import { FilterBar } from "../components/FilterBar";
import { WarningList } from "../components/WarningList";
import { Badge } from "../components/ui/Badge";
import { KpiCard } from "../components/ui/KpiCard";
import { KpiGridSkeleton, ChartSkeleton } from "../components/ui/LoadingSkeleton";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState, ErrorState } from "../components/ui/States";
import { useAnalysisFilters } from "../hooks/useAnalysisFilters";
import { useAppData } from "../hooks/useAppData";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type {
  DailyMetricsResponse,
  MetricDefinition,
  MetricsResponse,
} from "../types/api";
import {
  formatCount,
  formatDate,
  formatDateTime,
  formatInteger,
  formatMw,
  formatPercent,
  formatSignedMw,
} from "../utils/format";

const FALLBACK_DEFINITIONS: MetricDefinition[] = [
  {
    key: "mae",
    label: "Mean absolute error (MAE)",
    formula: "mean(|forecast − outturn|)",
    unit: "MW",
    interpretation: "Average size of misses in MW; lower is better.",
  },
  {
    key: "rmse",
    label: "Root mean squared error (RMSE)",
    formula: "sqrt(mean((forecast − outturn)²))",
    unit: "MW",
    interpretation: "Penalises large misses more heavily than MAE.",
  },
  {
    key: "mbe",
    label: "Mean bias error (MBE)",
    formula: "mean(forecast − outturn)",
    unit: "MW",
    interpretation: "Positive means overforecasting; negative means underforecasting.",
  },
  {
    key: "mape",
    label: "Mean absolute percentage error (MAPE)",
    formula: "mean(|forecast − outturn| / |outturn|) × 100",
    unit: "%",
    interpretation: "Pairs with |outturn| below 1 MW are excluded and counted.",
  },
  {
    key: "coverage",
    label: "Forecast coverage",
    formula: "eligible forecast hours / expected delivery hours × 100",
    unit: "%",
    interpretation: "Availability at the decision cut-off; not an accuracy measure.",
  },
];

function CoverageBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="tnum text-muted">{formatPercent(value)}</span>
      <span className="h-1 w-12 overflow-hidden rounded bg-line" aria-hidden="true">
        <span
          className={`block h-full rounded ${clamped < 95 ? "bg-warn" : "bg-accent"}`}
          style={{ width: `${clamped}%` }}
        />
      </span>
    </div>
  );
}

function AccuracyContent({
  metrics,
  daily,
  definitions,
}: {
  metrics: MetricsResponse;
  daily: DailyMetricsResponse;
  definitions: MetricDefinition[];
}) {
  const { coverage, metrics: accuracy, histogram } = metrics;
  const dailyPoints = useMemo(() => buildDailyChartPoints(daily.daily), [daily.daily]);
  const histogramPoints = useMemo(
    () => buildHistogramChartPoints(histogram.bins, histogram.total_pairs),
    [histogram],
  );
  const zeroBin = histogram.bins.find((bin) => bin.lower_mw <= 0 && bin.upper_mw >= 0);
  const zeroBinMid = zeroBin ? Math.round((zeroBin.lower_mw + zeroBin.upper_mw) / 2) : null;

  const mbeTone = accuracy.mbe_mw !== null && accuracy.mbe_mw > 0 ? "warn" : "default";
  const mbeBadge =
    accuracy.mbe_mw === null ? null : (
      <Badge tone={accuracy.mbe_mw > 0 ? "warn" : "neutral"}>
        {accuracy.mbe_mw > 0 ? "Overforecast" : accuracy.mbe_mw < 0 ? "Underforecast" : "Neutral"}
      </Badge>
    );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard
          label="MAE"
          value={formatMw(accuracy.mae_mw)}
          unit={accuracy.mae_mw === null ? undefined : "MW"}
          hint="Average absolute hourly forecast error."
          footnote={`n = ${formatCount(coverage.valid_pairs, "valid pair")}`}
        />
        <KpiCard
          label="RMSE"
          value={formatMw(accuracy.rmse_mw)}
          unit={accuracy.rmse_mw === null ? undefined : "MW"}
          hint="Root mean squared error; sensitive to large misses."
          footnote={`n = ${formatCount(coverage.valid_pairs, "valid pair")}`}
        />
        <KpiCard
          label="MBE"
          value={formatSignedMw(accuracy.mbe_mw)}
          unit={accuracy.mbe_mw === null ? undefined : "MW"}
          hint="Signed forecast minus outturn. Positive is overforecast."
          footnote="Offsetting errors can cancel in the mean."
          badge={mbeBadge}
          tone={mbeTone}
        />
        <KpiCard
          label="MAPE"
          value={formatPercent(accuracy.mape_percent)}
          hint="Mean absolute percentage error where outturn is at least 1 MW."
          footnote={`${formatInteger(accuracy.mape_valid_count)} included · ${formatInteger(
            accuracy.mape_excluded_count,
          )} excluded`}
        />
        <KpiCard
          label="Largest absolute miss"
          value={formatMw(accuracy.max_abs_error_mw)}
          unit={accuracy.max_abs_error_mw === null ? undefined : "MW"}
          hint={
            accuracy.max_abs_error_at_local
              ? `At ${formatDateTime(accuracy.max_abs_error_at_local)} London.`
              : "No valid forecast/outturn pairs."
          }
          footnote="Single worst interval in the selected window."
        />
      </div>

      {coverage.coverage_percent < 95 ? (
        <Notice
          tone="danger"
          title={`Low forecast coverage: ${formatPercent(coverage.coverage_percent)}`}
        >
          Error metrics are computed only on the {formatInteger(coverage.valid_pairs)} hours with
          both an eligible forecast and complete outturn. The remaining{" "}
          {formatInteger(coverage.expected_intervals - coverage.valid_pairs)} hours are unavailable.
          Do not treat these metrics as representative of the full window.
        </Notice>
      ) : null}

      <WarningList
        warnings={[...metrics.warnings, ...daily.warnings]}
        emptyMessage="The API reported no data-quality warnings for this window."
      />

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <section className="panel panel-pad" aria-labelledby="daily-chart-heading">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <SectionHeading
              title="Mean absolute error by delivery day"
              description="Bars are daily MAE in MW. The line is forecast coverage on the right axis; amber bars indicate coverage below 95%."
            />
            <span className="flex shrink-0 items-center gap-3 text-[10px] text-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-accent" aria-hidden="true" />
                MAE
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-0.5 w-4 bg-actual" aria-hidden="true" />
                Coverage
              </span>
            </span>
          </div>
          <div className="mt-4 border-t border-line pt-4">
            {dailyPoints.length === 0 ? (
              <EmptyState
                title="No daily metrics"
                description="The API returned no daily breakdown for this period."
              />
            ) : (
              <DailyMaeChart points={dailyPoints} />
            )}
          </div>
        </section>

        <section className="panel panel-pad" aria-labelledby="histogram-heading">
          <SectionHeading
            title="Signed forecast error"
            description="Counts of hourly pairs by signed error. Positive bins are overforecasts."
          />
          <div className="mt-4 border-t border-line pt-4">
            {histogramPoints.length === 0 || histogram.total_pairs === 0 ? (
              <EmptyState
                title="No error distribution"
                description="No valid forecast/outturn pairs exist for this window."
              />
            ) : (
              <ErrorHistogram points={histogramPoints} zeroBinMid={zeroBinMid} />
            )}
          </div>
          <p className="mt-2 border-t border-line pt-3 text-xs leading-5 text-faint">
            Bin width {formatInteger(histogram.bin_width_mw)} MW. {formatInteger(histogram.total_pairs)}{" "}
            valid pairs in total. The dashed line marks the zero-error bin.
          </p>
        </section>
      </div>

      <section className="panel" aria-labelledby="daily-table-heading">
        <div className="flex flex-col gap-2 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div>
            <h2 id="daily-table-heading" className="text-sm font-semibold text-ink">
              Daily breakdown
            </h2>
            <p className="mt-1 text-xs text-muted">
              Coverage and error by Europe/London delivery date. Missing pairs are not imputed.
            </p>
          </div>
          <BarChart3 className="hidden h-4 w-4 text-faint sm:block" aria-hidden="true" />
        </div>
        <div className="relative max-h-[520px] overflow-auto">
          <table className="w-full min-w-[820px] border-collapse">
            <caption className="sr-only">Daily forecast coverage and error metrics</caption>
            <thead className="sticky top-0 z-10 bg-panel">
              <tr className="border-b border-line">
                <th scope="col" className="table-cell text-left text-[10px] uppercase tracking-[0.08em] text-faint">
                  Delivery date
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  Valid / expected
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  Coverage
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  MAE
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  RMSE
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  MBE
                </th>
                <th scope="col" className="table-cell text-right text-[10px] uppercase tracking-[0.08em] text-faint">
                  MAPE
                </th>
              </tr>
            </thead>
            <tbody>
              {daily.daily.map((day) => (
                <tr key={day.date} className="border-b border-line/70 hover:bg-raised/25">
                  <th scope="row" className="table-cell text-left font-normal text-ink">
                    {formatDate(day.date)}
                  </th>
                  <td className="table-cell text-right tnum text-muted">
                    {formatInteger(day.valid_pairs)} / {formatInteger(day.expected_intervals)}
                  </td>
                  <td className="table-cell text-right">
                    <CoverageBar value={day.coverage_percent} />
                  </td>
                  <td className="table-cell text-right tnum text-ink">{formatMw(day.mae_mw)}</td>
                  <td className="table-cell text-right tnum text-muted">{formatMw(day.rmse_mw)}</td>
                  <td className="table-cell text-right tnum text-muted">{formatSignedMw(day.mbe_mw)}</td>
                  <td
                    className="table-cell text-right tnum text-muted"
                    title={
                      day.mape_excluded_count > 0
                        ? `${day.mape_excluded_count} pair(s) excluded below the 1 MW floor`
                        : undefined
                    }
                  >
                    {formatPercent(day.mape_percent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-line px-4 py-3 text-xs leading-5 text-faint sm:px-5">
          MAPE excludes pairs with |outturn| below 1 MW. Coverage measures forecast availability, not
          accuracy.
        </div>
      </section>

      <section className="panel panel-pad" aria-labelledby="definitions-heading">
        <SectionHeading
          title="How each metric is calculated"
          description="Calculations use the same valid hourly pairs. No weighting, scaling or bias correction is applied."
        />
        <dl className="mt-4 grid gap-4 border-t border-line pt-4 sm:grid-cols-2 xl:grid-cols-5">
          {definitions.map((definition) => (
            <div key={definition.key}>
              <dt className="text-xs font-medium text-ink">{definition.label}</dt>
              <dd className="mt-1 font-mono text-[10px] leading-4 text-accent">{definition.formula}</dd>
              <dd className="mt-1.5 text-xs leading-4 text-muted">{definition.interpretation}</dd>
              <dd className="mt-1 text-[10px] uppercase tracking-[0.08em] text-faint">
                Unit: {definition.unit}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="flex items-start gap-2 rounded-sm border border-line bg-panel/50 px-3.5 py-3 text-xs leading-5 text-faint">
        <Download className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <p>
          Download per-interval rows from the Forecast Explorer. Metrics here are aggregated by the
          API from the same comparison records, not recalculated in the browser.
        </p>
      </div>
    </div>
  );
}

export function AccuracyPage() {
  const { filters, params, key, apply, reset } = useAnalysisFilters();
  const { metadata } = useAppData();
  const location = useLocation();
  const metrics = useResource<MetricsResponse>(`metrics:${key}`, (signal) =>
    api.getMetrics(params, signal),
  );
  const daily = useResource<DailyMetricsResponse>(`daily:${key}`, (signal) =>
    api.getDaily(params, signal),
  );

  const error = metrics.error ?? daily.error;
  const loading = metrics.loading || daily.loading;

  function retryAll() {
    metrics.retry();
    daily.retry();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="How large were the misses?"
        description="Aggregate and daily error metrics for selected decision-time forecasts, with explicit coverage, missing-data counts and a signed error distribution."
        actions={
          <NavLink
            to={{ pathname: "/explorer", search: location.search }}
            className="btn btn-secondary"
          >
            Inspect intervals
            <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
          </NavLink>
        }
      />

      <FilterBar
        filters={filters}
        onApply={apply}
        onReset={reset}
        maxRangeDays={metadata?.max_range_days}
      />

      {loading ? (
        <div className="space-y-6" role="status" aria-label="Loading accuracy metrics">
          <KpiGridSkeleton />
          <div className="grid gap-6 xl:grid-cols-2">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
          <span className="sr-only">Loading accuracy metrics…</span>
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={retryAll} title="Accuracy metrics could not be loaded" />
      ) : metrics.data && daily.data ? (
        <AccuracyContent
          metrics={metrics.data}
          daily={daily.data}
          definitions={metadata?.metric_definitions ?? FALLBACK_DEFINITIONS}
        />
      ) : null}
    </div>
  );
}
