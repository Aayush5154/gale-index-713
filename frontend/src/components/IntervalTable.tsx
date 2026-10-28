import { ChevronDown, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { ComparisonInterval, HalfHourActual } from "../types/api";
import { downloadComparisonCsv } from "../utils/csv";
import {
  formatDate,
  formatDateTime,
  formatHours,
  formatInteger,
  formatMw,
  formatPercent,
  formatShortDateTime,
  formatSignedMw,
  formatTime,
} from "../utils/format";
import { StatusBadge } from "./StatusBadge";
import { EmptyState } from "./ui/States";

const PAGE_SIZE = 50;

type StatusFilter = "all" | "matched" | "missing_forecast" | "missing_actual" | "missing_both";

const FILTERS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "All intervals" },
  { value: "matched", label: "Matched" },
  { value: "missing_forecast", label: "No forecast" },
  { value: "missing_actual", label: "No outturn" },
  { value: "missing_both", label: "No data" },
];

function shortId(value: string): string {
  return value.replace(/[^a-zA-Z0-9]/g, "-");
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">{label}</dt>
      <dd className="mt-1 text-xs leading-5 text-ink">{value}</dd>
    </div>
  );
}

function IntervalDetail({
  interval,
  halfHourlyActuals,
}: {
  interval: ComparisonInterval;
  halfHourlyActuals: HalfHourActual[];
}) {
  const hourStart = Date.parse(interval.delivery_start_utc);
  const halves = halfHourlyActuals.filter((actual) => {
    const ts = Date.parse(actual.start_utc);
    return ts >= hourStart && ts < hourStart + 3_600_000;
  });

  const errors = [
    interval.signed_error_mw === null ? "Signed error unavailable" : `Signed: ${formatSignedMw(interval.signed_error_mw)} MW`,
    interval.absolute_error_mw === null ? null : `Absolute: ${formatMw(interval.absolute_error_mw)} MW`,
    interval.squared_error_mw2 === null ? null : `Squared: ${formatMw(interval.squared_error_mw2)} MW²`,
    interval.absolute_percentage_error === null
      ? null
      : `APE: ${formatPercent(interval.absolute_percentage_error, 2)}`,
  ].filter(Boolean);

  return (
    <div className="grid gap-5 border-t border-line bg-raised/40 px-4 py-4 lg:grid-cols-[1.1fr_1fr_1fr]">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        <DetailField label="Delivery start" value={`${formatDateTime(interval.delivery_start_local)} London`} />
        <DetailField label="Decision cut-off" value={`${formatDateTime(interval.cutoff_local)} London`} />
        <DetailField
          label="Selected publication"
          value={
            interval.forecast_publication_local
              ? `${formatDateTime(interval.forecast_publication_local)} London`
              : "No eligible publication"
          }
        />
        <DetailField label="Lead time" value={formatHours(interval.lead_time_hours)} />
        <DetailField
          label="Eligible versions"
          value={`${formatInteger(interval.eligible_forecast_count)} publication${
            interval.eligible_forecast_count === 1 ? "" : "s"
          } at or before cut-off`}
        />
        <DetailField
          label="Previous eligible"
          value={
            interval.previous_publication_utc
              ? `${formatDateTime(interval.previous_publication_utc)} · ${
                  interval.previous_forecast_mw === null ? "—" : `${formatMw(interval.previous_forecast_mw)} MW`
                }`
              : "None"
          }
        />
      </dl>

      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
          FUELHH half-hours in this hour
        </p>
        {halves.length === 0 ? (
          <p className="mt-1.5 text-xs text-muted">No outturn records were returned for this hour.</p>
        ) : (
          <ul className="mt-1.5 space-y-1 text-xs text-muted">
            {halves.map((half) => (
              <li key={half.start_utc} className="flex justify-between gap-3">
                <span>{formatTime(half.start_local)}</span>
                <span className="tnum text-ink">{formatMw(half.generation_mw)} MW</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-[10px] leading-4 text-faint">
          The hourly outturn is the arithmetic mean of the available half-hours; it is not a forecast
          value.
        </p>
      </div>

      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
          Error diagnostics
        </p>
        {errors.length === 0 ? (
          <p className="mt-1.5 text-xs text-muted">
            Error metrics are unavailable because a valid forecast/outturn pair does not exist.
          </p>
        ) : (
          <ul className="mt-1.5 space-y-1 text-xs text-muted">
            {errors.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {interval.duplicate_publication ? (
            <span className="rounded border border-warn/30 bg-warn/10 px-1.5 py-0.5 text-[10px] text-warn">
              Latest publication time tied; highest generation selected
            </span>
          ) : null}
          {interval.stale_forecast ? (
            <span className="rounded border border-warn/30 bg-warn/10 px-1.5 py-0.5 text-[10px] text-warn">
              Lead time exceeds 48 h
            </span>
          ) : null}
          {interval.eligible_forecast_count === 0 ? (
            <span className="rounded border border-line-strong bg-raised px-1.5 py-0.5 text-[10px] text-muted">
              No forecast was published at or before this cut-off
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function IntervalTable({
  intervals,
  halfHourlyActuals,
  filename,
}: {
  intervals: ComparisonInterval[];
  halfHourlyActuals: HalfHourActual[];
  filename: string;
}) {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [selectedStart, setSelectedStart] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [filter, intervals]);

  const counts = useMemo(() => {
    const result: Record<StatusFilter, number> = {
      all: intervals.length,
      matched: 0,
      missing_forecast: 0,
      missing_actual: 0,
      missing_both: 0,
    };
    for (const interval of intervals) {
      if (interval.status in result) result[interval.status as StatusFilter] += 1;
    }
    return result;
  }, [intervals]);

  const filtered = useMemo(
    () => (filter === "all" ? intervals : intervals.filter((item) => item.status === filter)),
    [filter, intervals],
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const startIndex = (safePage - 1) * PAGE_SIZE;
  const rows = filtered.slice(startIndex, startIndex + PAGE_SIZE);

  return (
    <section className="panel" aria-labelledby="interval-table-heading">
      <div className="flex flex-col gap-4 border-b border-line p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 id="interval-table-heading" className="text-sm font-semibold text-ink">
              Delivery intervals
            </h2>
            <p className="mt-1 text-xs text-muted">
              One row per delivery hour. Expand a row for the selected publication and error
              diagnostics.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => downloadComparisonCsv(filtered, filename)}
            disabled={filtered.length === 0}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Export filtered CSV
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by status">
          {FILTERS.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={filter === item.value}
              onClick={() => setFilter(item.value)}
              className={`rounded border px-2.5 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                filter === item.value
                  ? "border-accent/40 bg-accent/10 text-accent"
                  : "border-line bg-panel text-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              {item.label}
              <span className="ml-1.5 tnum text-faint">{formatInteger(counts[item.value])}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="relative overflow-x-auto">
        <table className="w-full min-w-[1080px] border-collapse">
          <caption className="sr-only">
            Hourly comparison of selected wind forecasts and half-hourly outturn
          </caption>
          <thead>
            <tr className="border-b border-line bg-raised/30 text-left">
              <th scope="col" className="table-cell text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Delivery · London
              </th>
              <th scope="col" className="table-cell text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Status
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Forecast MW
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Outturn MW
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Error MW
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Abs. MW
              </th>
              <th scope="col" className="table-cell text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Publication / cut-off
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                Lead
              </th>
              <th scope="col" className="table-cell text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-4">
                  <EmptyState
                    title="No intervals match this filter"
                    description="Choose another status filter or adjust the delivery window."
                  />
                </td>
              </tr>
            ) : (
              rows.map((interval) => {
                const detailId = `interval-detail-${shortId(interval.delivery_start_utc)}`;
                const selected = selectedStart === interval.delivery_start_utc;
                const errorTone =
                  interval.signed_error_mw === null
                    ? "text-faint"
                    : interval.signed_error_mw > 0
                      ? "text-warn"
                      : interval.signed_error_mw < 0
                        ? "text-actual"
                        : "text-muted";
                return (
                  <FragmentRow
                    key={interval.delivery_start_utc}
                    interval={interval}
                    detailId={detailId}
                    selected={selected}
                    errorTone={errorTone}
                    onToggle={() =>
                      setSelectedStart(selected ? null : interval.delivery_start_utc)
                    }
                    halfHourlyActuals={halfHourlyActuals}
                  />
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-faint">
          {filtered.length === 0
            ? "No rows"
            : `Showing ${formatInteger(startIndex + 1)}–${formatInteger(
                Math.min(startIndex + PAGE_SIZE, filtered.length),
              )} of ${formatInteger(filtered.length)}`}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-secondary px-2 py-1.5"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={safePage <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          <span className="text-xs tnum text-muted">
            Page {safePage} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-secondary px-2 py-1.5"
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={safePage >= totalPages}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}

function FragmentRow({
  interval,
  detailId,
  selected,
  errorTone,
  onToggle,
  halfHourlyActuals,
}: {
  interval: ComparisonInterval;
  detailId: string;
  selected: boolean;
  errorTone: string;
  onToggle: () => void;
  halfHourlyActuals: HalfHourActual[];
}) {
  return (
    <>
      <tr
        className={`border-b border-line/70 transition-colors ${
          selected ? "bg-raised/60" : "hover:bg-raised/25"
        }`}
      >
        <th scope="row" className="table-cell text-left font-normal">
          <span className="block text-ink">{formatDate(interval.delivery_date_local)}</span>
          <span className="block text-xs tnum text-faint">
            {formatTime(interval.delivery_start_local)} London
          </span>
        </th>
        <td className="table-cell">
          <StatusBadge status={interval.status} />
        </td>
        <td className="table-cell text-right tnum text-ink">
          {interval.forecast_mw === null ? "—" : formatMw(interval.forecast_mw)}
        </td>
        <td className="table-cell text-right tnum text-ink">
          {interval.actual_mw === null ? "—" : formatMw(interval.actual_mw)}
        </td>
        <td className={`table-cell text-right tnum ${errorTone}`}>
          {formatSignedMw(interval.signed_error_mw)}
        </td>
        <td className="table-cell text-right tnum text-muted">
          {formatMw(interval.absolute_error_mw)}
        </td>
        <td className="table-cell">
          <span className="block text-xs text-ink">
            {formatShortDateTime(interval.forecast_publication_local)}
          </span>
          <span className="block text-[10px] text-faint">
            cut-off {formatShortDateTime(interval.cutoff_local)}
          </span>
        </td>
        <td className="table-cell text-right tnum text-muted">
          {interval.lead_time_hours === null ? "—" : formatHours(interval.lead_time_hours)}
        </td>
        <td className="table-cell text-right">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={selected}
            aria-controls={detailId}
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted transition-colors hover:bg-raised hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Details
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform ${selected ? "rotate-180" : ""}`}
              aria-hidden="true"
            />
          </button>
        </td>
      </tr>
      {selected ? (
        <tr id={detailId}>
          <td colSpan={9} className="p-0">
            <IntervalDetail interval={interval} halfHourlyActuals={halfHourlyActuals} />
          </td>
        </tr>
      ) : null}
    </>
  );
}
