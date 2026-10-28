import { ArrowUpRight, Clock3, Database, ShieldCheck } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

import { FilterBar } from "../components/FilterBar";
import { WarningList } from "../components/WarningList";
import { KpiCard } from "../components/ui/KpiCard";
import { KpiGridSkeleton, ChartSkeleton } from "../components/ui/LoadingSkeleton";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { ErrorState } from "../components/ui/States";
import { useAnalysisFilters } from "../hooks/useAnalysisFilters";
import { useAppData } from "../hooks/useAppData";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { DataSource, HealthResponse, MetadataResponse, MetricsResponse } from "../types/api";
import {
  formatCount,
  formatDateRange,
  formatDateTime,
  formatHours,
  formatInteger,
  formatMw,
  formatPercent,
  formatSignedMw,
} from "../utils/format";

function countFrom(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  return typeof value === "number" ? value : null;
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.09em] text-faint">{label}</dt>
      <dd className="mt-1 text-sm leading-5 text-ink">{value}</dd>
    </div>
  );
}

function DataSourcePanel({
  source,
  health,
  metadata,
}: {
  source: DataSource;
  health: HealthResponse | undefined;
  metadata: MetadataResponse | undefined;
}) {
  const dependency = health?.dependencies.find((item) => item.configured) ?? health?.dependencies[0];
  const cacheMinutes = Math.round(source.cache_ttl_seconds / 60);

  return (
    <section className="panel panel-pad">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-accent" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Data source &amp; freshness</h2>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${
            source.is_synthetic ? "text-warn" : "text-accent"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${source.is_synthetic ? "bg-warn" : "bg-accent"}`}
            aria-hidden="true"
          />
          {source.is_synthetic ? "Synthetic" : "Live"}
        </span>
      </div>

      <dl className="mt-4 space-y-3">
        <Fact label="Source" value={source.source_name} />
        <Fact label="Generated" value={`${formatDateTime(source.generated_at_utc)} Europe/London`} />
        <Fact
          label="Raw query"
          value={`${formatInteger(countFrom(source.fetch, "actual_chunks"))} FUELHH + ${formatInteger(
            countFrom(source.fetch, "forecast_chunks"),
          )} WINDFOR chunks`}
        />
        <Fact
          label="Records inspected"
          value={`${formatInteger(countFrom(source.fetch, "actual_records"))} FUELHH · ${formatInteger(
            countFrom(source.fetch, "forecast_records"),
          )} WINDFOR`}
        />
        <Fact label="Cache" value={`${cacheMinutes}-minute TTL, bounded in memory`} />
      </dl>

      <div className="mt-4 border-t border-line pt-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-faint">
          Upstream status
        </p>
        <p className="mt-1.5 flex items-center gap-2 text-xs text-muted">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health?.status === "ok" ? "bg-accent" : health ? "bg-warn" : "bg-faint"
            }`}
            aria-hidden="true"
          />
          {dependency
            ? `${dependency.name}: ${dependency.status.replaceAll("_", " ")}`
            : health?.status === "degraded"
              ? "Dependency degraded"
              : "No dependency detail"}
        </p>
        {metadata?.is_synthetic ? (
          <p className="mt-3 rounded border border-warn/25 bg-warn/[0.05] px-2.5 py-2 text-xs leading-4 text-warn">
            Fixture data is synthetic and must not be used for procurement decisions.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function OverviewContent({
  metrics,
  health,
  metadata,
}: {
  metrics: MetricsResponse;
  health: HealthResponse | undefined;
  metadata: MetadataResponse | undefined;
}) {
  const { query, coverage, metrics: accuracy, decision_context: decision } = metrics;
  const mbeBadge =
    accuracy.mbe_mw === null ? null : accuracy.mbe_mw > 0 ? (
      <span className="rounded border border-warn/30 bg-warn/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-warn">
        Overforecast
      </span>
    ) : accuracy.mbe_mw < 0 ? (
      <span className="rounded border border-actual/30 bg-actual/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-actual">
        Underforecast
      </span>
    ) : null;

  const coverageTone =
    coverage.coverage_percent >= 99.5
      ? "accent"
      : coverage.coverage_percent >= 95
        ? "neutral"
        : "warn";

  const incompleteHours = countFrom(metrics.data_quality, "incomplete_actual_hours");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        <span>{formatDateRange(query.from_date, query.to_date)}</span>
        <span className="text-faint" aria-hidden="true">
          ·
        </span>
        <span>
          {query.cutoff_mode === "daily"
            ? `daily cut-off ${query.cutoff_time_local} Europe/London on D-1`
            : `fixed cut-off ${formatDateTime(query.cutoff_datetime_local)}`}
        </span>
        <span className="text-faint" aria-hidden="true">
          ·
        </span>
        <span>{query.expected_intervals} hourly intervals</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Forecast coverage"
          value={formatPercent(coverage.coverage_percent)}
          hint={`${formatInteger(coverage.forecast_available)} of ${formatInteger(
            coverage.expected_intervals,
          )} expected delivery hours have a forecast published at or before the cut-off.`}
          footnote={`${formatCount(coverage.valid_pairs, "valid pair")} with outturn. Coverage is availability, not accuracy.`}
          badge={
            <span
              className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em] ${
                coverageTone === "accent"
                  ? "border-accent/30 bg-accent/10 text-accent"
                  : coverageTone === "warn"
                    ? "border-warn/30 bg-warn/10 text-warn"
                    : "border-line-strong bg-raised text-muted"
              }`}
            >
              {coverage.missing_forecast > 0 ? `${coverage.missing_forecast} gap` : "No gaps"}
            </span>
          }
        />
        <KpiCard
          label="Mean absolute error"
          value={formatMw(accuracy.mae_mw)}
          unit={accuracy.mae_mw === null ? undefined : "MW"}
          hint="Average absolute difference between the selected hourly forecast and the hourly outturn."
          footnote={`n = ${formatCount(coverage.valid_pairs, "valid pair")} · no adjustment applied`}
        />
        <KpiCard
          label="Root mean squared error"
          value={formatMw(accuracy.rmse_mw)}
          unit={accuracy.rmse_mw === null ? undefined : "MW"}
          hint="Square root of mean squared error; larger misses carry more weight than MAE."
          footnote={`n = ${formatCount(coverage.valid_pairs, "valid pair")} · MW`}
        />
        <KpiCard
          label="Mean bias error"
          value={formatSignedMw(accuracy.mbe_mw)}
          unit={accuracy.mbe_mw === null ? undefined : "MW"}
          hint="Signed mean of forecast minus outturn. Positive means the forecast was above outturn on average."
          footnote="Not an absolute error measure; offsetting errors can cancel."
          badge={mbeBadge}
        />
      </div>

      <WarningList
        warnings={metrics.warnings}
        emptyMessage="The API reported no missing values, duplicate publications or incomplete outturn hours for this window."
      />

      <div className="grid gap-6 xl:grid-cols-[1.65fr_1fr]">
        <section className="panel panel-pad">
          <div className="flex items-center gap-2">
            <Clock3 className="h-4 w-4 text-accent" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-ink">Decision-time context</h2>
          </div>
          <p className="mt-3 border-l-2 border-accent/50 pl-3 text-xs leading-5 text-muted">
            {decision.rule}
          </p>
          <dl className="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2">
            <Fact label="First cut-off" value={`${formatDateTime(decision.first_cutoff_local)} London`} />
            <Fact label="Last cut-off" value={`${formatDateTime(decision.last_cutoff_local)} London`} />
            <Fact
              label="Selected publication range"
              value={
                decision.earliest_publication_utc && decision.latest_publication_utc
                  ? `${formatDateTime(decision.earliest_publication_utc)} – ${formatDateTime(
                      decision.latest_publication_utc,
                    )}`
                  : "No selected publications"
              }
            />
            <Fact
              label="Distinct publications used"
              value={formatCount(decision.distinct_publications, "publication")}
            />
            <Fact
              label="Lead time at selection"
              value={
                decision.lead_time_min_hours === null
                  ? "—"
                  : `${formatHours(decision.lead_time_min_hours)} – ${formatHours(
                      decision.lead_time_max_hours,
                    )}`
              }
            />
            <Fact
              label="Forecast resolution"
              value={`${query.resolution} WINDFOR matched to ${formatInteger(
                query.expected_intervals,
              )} delivery hours`}
            />
          </dl>
          <p className="mt-5 border-t border-line pt-4 text-xs leading-5 text-faint">
            Forecasts are selected independently for each delivery hour. No publication later than the
            applicable cut-off can influence the result.
          </p>
        </section>

        <DataSourcePanel source={metrics.data_source} health={health} metadata={metadata} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
        <section className="panel panel-pad">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-accent" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-ink">Window integrity</h2>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-2xl font-semibold tnum text-ink">{formatInteger(coverage.missing_forecast)}</p>
              <p className="mt-1 text-xs leading-4 text-muted">Hours without an eligible forecast</p>
            </div>
            <div>
              <p className="text-2xl font-semibold tnum text-ink">{formatInteger(coverage.missing_actual)}</p>
              <p className="mt-1 text-xs leading-4 text-muted">Hours without complete outturn</p>
            </div>
            <div>
              <p className="text-2xl font-semibold tnum text-ink">
                {incompleteHours === null ? "—" : formatInteger(incompleteHours)}
              </p>
              <p className="mt-1 text-xs leading-4 text-muted">Hours with an incomplete half-hour pair</p>
            </div>
            <div>
              <p className="text-2xl font-semibold tnum text-ink">
                {formatInteger(accuracy.mape_excluded_count)}
              </p>
              <p className="mt-1 text-xs leading-4 text-muted">MAPE pairs excluded by the 1 MW floor</p>
            </div>
            <div>
              <p className="text-2xl font-semibold tnum text-ink">{formatInteger(coverage.missing_both)}</p>
              <p className="mt-1 text-xs leading-4 text-muted">Hours missing both forecast and outturn</p>
            </div>
            <div>
              <p className="text-2xl font-semibold tnum text-ink">
                {formatInteger(metrics.decision_context.distinct_publications)}
              </p>
              <p className="mt-1 text-xs leading-4 text-muted">Distinct forecast publications selected</p>
            </div>
          </div>
          <p className="mt-4 border-t border-line pt-3 text-xs leading-5 text-faint">
            Missing values remain missing. The tool does not interpolate, substitute or scale Elexon
            data.
          </p>
        </section>

        <section className="panel panel-pad">
          <h2 className="text-sm font-semibold text-ink">Reading these numbers</h2>
          <ul className="mt-3 space-y-2.5 text-xs leading-5 text-muted">
            <li className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              Coverage describes whether a forecast was available at the decision time. It is not an
              accuracy score.
            </li>
            <li className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              WINDFOR is hourly. Each forecast is matched to the arithmetic mean of the two FUELHH WIND
              half-hours for the same delivery hour.
            </li>
            <li className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              Positive MBE indicates overforecasting. In this January sample, errors are predominantly
              positive; the tool does not shift or calibrate the data.
            </li>
            <li className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
              No weather, demand, price or procurement volume data is used. All values are MW as supplied.
            </li>
          </ul>
        </section>
      </div>

      <Notice tone="info" title="Source and scope">
        This prototype evaluates national wind forecast accuracy using Elexon FUELHH WIND outturn and
        WINDFOR publications. It does not estimate financial impact or procurement savings. Read the{" "}
        <NavLink to="/methodology" className="link">
          methodology and data-quality notes
        </NavLink>{" "}
        before interpreting the results.
      </Notice>
    </div>
  );
}

export function OverviewPage() {
  const { filters, params, key, apply, reset } = useAnalysisFilters();
  const { metadata, health } = useAppData();
  const location = useLocation();
  const metrics = useResource<MetricsResponse>(`metrics:${key}`, (signal) =>
    api.getMetrics(params, signal),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Wind Forecast Analytics"
        description="How accurate were the wind forecasts available at the day-ahead decision point? Select a delivery window and cut-off, then review coverage and retrospective error against Elexon outturn."
        actions={
          <>
            <NavLink
              to={{ pathname: "/explorer", search: location.search }}
              className="btn btn-secondary"
            >
              Forecast explorer
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </NavLink>
            <NavLink
              to={{ pathname: "/accuracy", search: location.search }}
              className="btn btn-secondary"
            >
              Accuracy analysis
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </NavLink>
          </>
        }
      />

      <FilterBar
        filters={filters}
        onApply={apply}
        onReset={reset}
        maxRangeDays={metadata?.max_range_days}
      />

      {metrics.loading ? (
        <div className="space-y-6" role="status" aria-label="Loading forecast metrics">
          <KpiGridSkeleton />
          <ChartSkeleton height="h-[260px]" />
          <span className="sr-only">Loading forecast metrics…</span>
        </div>
      ) : metrics.error ? (
        <ErrorState
          error={metrics.error}
          onRetry={metrics.retry}
          title="Forecast metrics could not be loaded"
        >
          <p className="mt-2 text-xs text-faint">
            The frontend calls only the analytics API. If the backend is starting, retry in a moment.
          </p>
        </ErrorState>
      ) : metrics.data ? (
        <OverviewContent metrics={metrics.data} health={health} metadata={metadata} />
      ) : null}
    </div>
  );
}
