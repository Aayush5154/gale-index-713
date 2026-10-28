import { Activity, ArrowUpRight, CalendarClock, Info } from "lucide-react";
import { useMemo } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { FilterBar } from "../components/FilterBar";
import { IntervalTable } from "../components/IntervalTable";
import { WarningList } from "../components/WarningList";
import { CHART } from "../utils/chartTheme";
import { buildForecastChartPoints } from "../components/charts/chartData";
import { ChartLegend } from "../components/charts/ChartLegend";
import { ForecastChart } from "../components/charts/ForecastChart";
import { ChartSkeleton, KpiGridSkeleton } from "../components/ui/LoadingSkeleton";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState, ErrorState } from "../components/ui/States";
import { useAnalysisFilters } from "../hooks/useAnalysisFilters";
import { useAppData } from "../hooks/useAppData";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { ComparisonResponse } from "../types/api";
import { daysInclusive } from "../utils/filters";
import {
  formatCount,
  formatDateTime,
  formatInteger,
  formatPercent,
} from "../utils/format";

function MiniStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-line/80 px-4 py-3 first:pl-0 last:pr-0 sm:border-l sm:first:border-l-0">
      <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-faint">{label}</p>
      <p className="mt-1 text-lg font-semibold tnum text-ink">{value}</p>
      {hint ? <p className="mt-0.5 text-[10px] leading-4 text-muted">{hint}</p> : null}
    </div>
  );
}

function ComparisonContent({ comparison }: { comparison: ComparisonResponse }) {
  const { query, coverage, intervals, half_hourly_actuals: actuals } = comparison;

  const points = useMemo(
    () => buildForecastChartPoints(intervals, actuals),
    [intervals, actuals],
  );

  const publicationRange = useMemo(() => {
    const publications = intervals
      .map((item) => item.forecast_publication_utc)
      .filter((value): value is string => Boolean(value))
      .sort();
    return publications.length > 0
      ? { earliest: publications[0], latest: publications[publications.length - 1], count: new Set(publications).size }
      : null;
  }, [intervals]);

  const rangeDays = daysInclusive(query.from_date, query.to_date);
  const filename = `wind-forecast-comparison_${query.from_date}_${query.to_date}.csv`;

  return (
    <div className="space-y-6">
      <section className="panel" aria-label="Comparison summary">
        <div className="grid grid-cols-2 gap-y-1 divide-line/70 sm:grid-cols-3 xl:grid-cols-5 xl:divide-x">
          <MiniStat
            label="Forecast coverage"
            value={formatPercent(coverage.coverage_percent)}
            hint={`${formatInteger(coverage.forecast_available)} of ${formatInteger(
              coverage.expected_intervals,
            )} hours`}
          />
          <MiniStat
            label="Valid pairs"
            value={formatInteger(coverage.valid_pairs)}
            hint="forecast and outturn present"
          />
          <MiniStat
            label="Missing forecast"
            value={formatInteger(coverage.missing_forecast)}
            hint="not available at cut-off"
          />
          <MiniStat
            label="Missing outturn"
            value={formatInteger(coverage.missing_actual + coverage.missing_both)}
            hint="incomplete FUELHH half-hours"
          />
          <MiniStat
            label="Distinct publications"
            value={formatInteger(publicationRange?.count ?? 0)}
            hint={
              publicationRange
                ? `${formatDateTime(publicationRange.earliest)} – ${formatDateTime(
                    publicationRange.latest,
                  )}`
                : "none selected"
            }
          />
        </div>
      </section>

      {coverage.missing_forecast > 0 ? (
        <Notice
          tone="warn"
          title={`${formatCount(coverage.missing_forecast, "delivery hour")} without an eligible forecast`}
        >
          No WINDFOR publication existed at or before that hour's cut-off. These rows remain
          unavailable and are excluded from error metrics. Use the{" "}
          <span className="text-ink">No forecast</span> filter in the table to inspect them.
        </Notice>
      ) : null}

      <WarningList warnings={comparison.warnings} />

      <section className="panel panel-pad" aria-labelledby="comparison-chart-heading">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <SectionHeading
            title="Forecast vs half-hourly outturn"
            description="The selected hourly WINDFOR forecast is shown against FUELHH WIND outturn at its native 30-minute resolution."
          />
          <ChartLegend
            items={[
              { label: "Selected WINDFOR (hourly)", color: CHART.accent },
              { label: "FUELHH WIND (30-min)", color: CHART.actual },
            ]}
          />
        </div>

        <div className="mt-4 border-t border-line pt-4">
          {points.length === 0 ? (
            <EmptyState
              title="No comparison data in this window"
              description="The API returned no forecast or outturn records for the selected delivery period. Adjust the analysis window or retry the request."
            />
          ) : (
            <ForecastChart points={points} rangeDays={rangeDays} />
          )}
        </div>

        <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3 text-xs leading-5 text-faint sm:flex-row sm:items-start sm:justify-between">
          <p className="flex gap-1.5">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            At :30 points only outturn is plotted. WINDFOR is hourly; no half-hourly forecast is
            interpolated.
          </p>
          <p className="shrink-0">
            {formatInteger(actuals.length)} half-hour outturn records · {formatInteger(intervals.length)} delivery
            hours
          </p>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
          {comparison.data_source.is_synthetic ? "Synthetic fixture source" : "Live Elexon source"}
        </span>
        <span className="text-faint" aria-hidden="true">
          ·
        </span>
        <span>Generated {formatDateTime(comparison.data_source.generated_at_utc)} London</span>
        <span className="text-faint" aria-hidden="true">
          ·
        </span>
        <span>{formatCount(intervals.length, "delivery hour")}</span>
      </div>

      <IntervalTable
        intervals={intervals}
        halfHourlyActuals={actuals}
        filename={filename}
      />
    </div>
  );
}

export function ExplorerPage() {
  const { filters, params, key, apply, reset } = useAnalysisFilters();
  const { metadata } = useAppData();
  const location = useLocation();
  const comparison = useResource<ComparisonResponse>(`comparison:${key}`, (signal) =>
    api.getComparison(params, signal),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Forecast, outturn and decision-time selection"
        description="Inspect the exact WINDFOR publication used for each delivery hour, compare it with FUELHH outturn, and audit missing forecasts without substituting values."
        actions={
          <NavLink
            to={{ pathname: "/accuracy", search: location.search }}
            className="btn btn-secondary"
          >
            Accuracy analysis
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

      {comparison.loading ? (
        <div className="space-y-6" role="status" aria-label="Loading forecast comparison">
          <KpiGridSkeleton />
          <ChartSkeleton height="h-[390px]" />
          <span className="sr-only">Loading forecast comparison…</span>
        </div>
      ) : comparison.error ? (
        <ErrorState
          error={comparison.error}
          onRetry={comparison.retry}
          title="Forecast comparison could not be loaded"
        />
      ) : comparison.data ? (
        <ComparisonContent comparison={comparison.data} />
      ) : null}

      <div className="flex items-start gap-2 rounded-sm border border-line bg-panel/50 px-3.5 py-3 text-xs leading-5 text-faint">
        <CalendarClock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <p>
          The cut-off shown for each row is the actual decision time used for that delivery hour.
          "Publication" is the latest eligible WINDFOR publication, never a later issue. All times are
          displayed in Europe/London.
        </p>
      </div>
    </div>
  );
}
