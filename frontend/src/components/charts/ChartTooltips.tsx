import type { ReactNode } from "react";
import type { TooltipProps } from "recharts";

import type {
  DailyChartPoint,
  ForecastChartPoint,
  HistogramChartPoint,
} from "./chartData";
import { formatDate, formatDateTime, formatMw, formatNumber, formatPercent, formatSignedMw } from "../../utils/format";

function TooltipShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-w-[220px] max-w-[320px] rounded-sm border border-line-strong bg-panel px-3 py-2.5 text-xs shadow-lg">
      {children}
    </div>
  );
}

function Row({
  label,
  value,
  tone = "text-ink",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-faint">{label}</dt>
      <dd className={`text-right tnum ${tone}`}>{value}</dd>
    </div>
  );
}

export function ForecastTooltip({ active, payload }: TooltipProps<number, string>) {
  const point = payload?.[0]?.payload as ForecastChartPoint | undefined;
  if (!active || !point) return null;
  const date = new Date(point.ts);
  const isHour = date.getUTCMinutes() === 0;
  const status = point.interval?.status;

  return (
    <TooltipShell>
      <p className="font-medium text-ink">{formatDateTime(date.toISOString())}</p>
      <p className="mt-0.5 text-[10px] uppercase tracking-[0.08em] text-faint">Europe/London</p>
      <dl className="mt-2 space-y-1">
        <Row
          label="FUELHH outturn"
          value={point.actual === null ? "Not reported" : `${formatMw(point.actual)} MW`}
        />
        <Row
          label="Selected forecast"
          value={
            point.forecast !== null
              ? `${formatMw(point.forecast)} MW`
              : !isHour
                ? "Hourly only · see :00"
                : status === "missing_forecast"
                  ? "Not available at cut-off"
                  : "No data"
          }
          tone={point.forecast !== null ? "text-accent" : "text-muted"}
        />
        {point.interval?.forecast_publication_local ? (
          <Row label="Published" value={formatDateTime(point.interval.forecast_publication_local)} />
        ) : null}
        {point.interval?.cutoff_local ? (
          <Row label="Cut-off" value={formatDateTime(point.interval.cutoff_local)} />
        ) : null}
        {point.interval?.signed_error_mw !== null &&
        point.interval?.signed_error_mw !== undefined ? (
          <Row
            label="Forecast − actual"
            value={`${formatSignedMw(point.interval.signed_error_mw)} MW`}
            tone={point.interval.signed_error_mw > 0 ? "text-warn" : "text-actual"}
          />
        ) : null}
      </dl>
      {!isHour ? (
        <p className="mt-2 border-t border-line pt-1.5 text-[10px] leading-4 text-faint">
          Outturn is half-hourly; WINDFOR is hourly. No half-hourly forecast is fabricated.
        </p>
      ) : null}
    </TooltipShell>
  );
}

export function DailyTooltip({ active, payload }: TooltipProps<number, string>) {
  const point = payload?.[0]?.payload as DailyChartPoint | undefined;
  if (!active || !point) return null;

  return (
    <TooltipShell>
      <p className="font-medium text-ink">{formatDate(point.date)}</p>
      <dl className="mt-2 space-y-1">
        <Row label="MAE" value={point.mae === null ? "No valid pairs" : `${formatMw(point.mae)} MW`} tone="text-accent" />
        <Row label="MBE" value={point.mbe === null ? "—" : `${formatSignedMw(point.mbe)} MW`} />
        <Row label="Coverage" value={formatPercent(point.coverage)} />
        <Row label="Valid pairs" value={formatNumber(point.pairs, 0)} />
        <Row label="Missing forecast" value={formatNumber(point.missingForecast, 0)} />
        <Row label="Missing outturn" value={formatNumber(point.missingActual, 0)} />
      </dl>
      <p className="mt-2 border-t border-line pt-1.5 text-[10px] leading-4 text-faint">
        Coverage is forecast availability at the cut-off, not accuracy.
      </p>
    </TooltipShell>
  );
}

export function HistogramTooltip({ active, payload }: TooltipProps<number, string>) {
  const point = payload?.[0]?.payload as HistogramChartPoint | undefined;
  if (!active || !point) return null;
  const share = point.total > 0 ? (point.count / point.total) * 100 : 0;
  const sideLabel =
    point.side === "overforecast"
      ? "Forecast above outturn"
      : point.side === "underforecast"
        ? "Forecast below outturn"
        : "Bin spans zero";

  return (
    <TooltipShell>
      <p className="font-medium text-ink">
        {formatNumber(point.lower, 0)} to {formatNumber(point.upper, 0)} MW
      </p>
      <dl className="mt-2 space-y-1">
        <Row label="Intervals" value={formatNumber(point.count, 0)} />
        <Row label="Share of pairs" value={formatPercent(share)} />
        <Row label="Interpretation" value={sideLabel} />
      </dl>
      <p className="mt-2 border-t border-line pt-1.5 text-[10px] leading-4 text-faint">
        Bin label is the signed error midpoint, forecast − actual.
      </p>
    </TooltipShell>
  );
}
