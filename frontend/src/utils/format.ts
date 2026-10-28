const TIME_ZONE = "Europe/London";
const EMPTY = "—";

function asDate(value: string | number | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const shortDateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const dayFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  day: "2-digit",
  month: "short",
});

const monthFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  month: "short",
  year: "numeric",
});

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value.length === 10 ? `${value}T12:00:00Z` : value);
  return date ? dateFormatter.format(date) : EMPTY;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value);
  return date ? dateTimeFormatter.format(date) : EMPTY;
}

export function formatShortDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value);
  return date ? shortDateTimeFormatter.format(date) : EMPTY;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value);
  return date ? timeFormatter.format(date) : EMPTY;
}

export function formatDay(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value.length === 10 ? `${value}T12:00:00Z` : value);
  return date ? dayFormatter.format(date) : EMPTY;
}

export function formatMonth(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const date = asDate(value.length === 10 ? `${value}T12:00:00Z` : value);
  return date ? monthFormatter.format(date) : EMPTY;
}

export function formatAxisTimestamp(timestamp: number, multiDay: boolean): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return multiDay ? dayFormatter.format(date) : timeFormatter.format(date);
}

export function formatNumber(
  value: number | null | undefined,
  fractionDigits = 0,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatInteger(value: number | null | undefined): string {
  return formatNumber(value, 0);
}

export function formatMw(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  return formatNumber(value, Math.abs(value) < 10 && value !== 0 ? 1 : 0);
}

export function formatSignedMw(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  if (value === 0) return "0";
  return `${value > 0 ? "+" : "−"}${formatMw(Math.abs(value))}`;
}

export function formatPercent(
  value: number | null | undefined,
  fractionDigits = 1,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  return `${formatNumber(value, fractionDigits)}%`;
}

export function formatHours(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  return `${formatNumber(value, 1)} h`;
}

export function formatDateRange(from: string, to: string): string {
  if (!from || !to) return EMPTY;
  return `${formatDate(from)} – ${formatDate(to)}`;
}

export function formatDays(count: number): string {
  return `${formatInteger(count)} ${count === 1 ? "day" : "days"}`;
}

export function formatCount(count: number, singular: string, plural?: string): string {
  return `${formatInteger(count)} ${count === 1 ? singular : (plural ?? `${singular}s`)}`;
}

export function formatSignedPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  if (value === 0) return "0.0%";
  return `${value > 0 ? "+" : "−"}${formatNumber(Math.abs(value), 1)}%`;
}

export { TIME_ZONE };
