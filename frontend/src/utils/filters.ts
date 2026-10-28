import type { AnalysisParams, CutoffMode } from "../types/api";

export const DEFAULT_FROM = "2026-01-01";
export const DEFAULT_TO = "2026-01-31";
export const DEFAULT_CUTOFF = "09:20";
export const DEFAULT_MAX_RANGE_DAYS = 92;

export interface FilterState {
  from: string;
  to: string;
  mode: CutoffMode;
  cutoff: string;
  at: string;
}

export const DEFAULT_FILTERS: FilterState = {
  from: DEFAULT_FROM,
  to: DEFAULT_TO,
  mode: "daily",
  cutoff: DEFAULT_CUTOFF,
  at: "2025-12-31T09:20",
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const TIME = /^([01]\d|2[0-3]):[0-5]\d$/;
const LOCAL_DATE_TIME = /^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d/;

export function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function isValidLocalDateTime(value: string): boolean {
  return LOCAL_DATE_TIME.test(value) && isValidIsoDate(value.slice(0, 10));
}

export function shiftIsoDate(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function daysInclusive(from: string, to: string): number {
  const start = new Date(`${from}T00:00:00Z`);
  const end = new Date(`${to}T00:00:00Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0;
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
}

export function todayInLondon(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function defaultFixedAt(from: string, cutoff: string): string {
  return `${shiftIsoDate(from, -1)}T${cutoff}`;
}

export function readFilters(searchParams: URLSearchParams): FilterState {
  const rawFrom = searchParams.get("from") ?? DEFAULT_FROM;
  const rawTo = searchParams.get("to") ?? DEFAULT_TO;
  const from = isValidIsoDate(rawFrom) ? rawFrom : DEFAULT_FROM;
  const to = isValidIsoDate(rawTo) ? rawTo : DEFAULT_TO;
  const mode: CutoffMode = searchParams.get("mode") === "fixed" ? "fixed" : "daily";
  const rawCutoff = searchParams.get("cutoff") ?? DEFAULT_CUTOFF;
  const cutoff = TIME.test(rawCutoff) ? rawCutoff : DEFAULT_CUTOFF;
  const rawAt = searchParams.get("at") ?? "";
  const at = isValidLocalDateTime(rawAt) ? rawAt : defaultFixedAt(from, cutoff);
  return { from, to, mode, cutoff, at };
}

export function toSearchParams(filters: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  params.set("from", filters.from);
  params.set("to", filters.to);
  params.set("mode", filters.mode);
  params.set("cutoff", filters.cutoff);
  if (filters.mode === "fixed") params.set("at", filters.at);
  return params;
}

export function toAnalysisParams(filters: FilterState): AnalysisParams {
  const base: AnalysisParams = {
    from_date: filters.from,
    to_date: filters.to,
    cutoff_mode: filters.mode,
    cutoff_time: filters.cutoff,
  };
  if (filters.mode === "fixed") base.cutoff_datetime = filters.at;
  return base;
}

export function validateFilters(
  filters: FilterState,
  maxRangeDays = DEFAULT_MAX_RANGE_DAYS,
): string[] {
  const errors: string[] = [];
  if (!isValidIsoDate(filters.from)) errors.push("Enter a valid start date (YYYY-MM-DD).");
  if (!isValidIsoDate(filters.to)) errors.push("Enter a valid end date (YYYY-MM-DD).");
  if (errors.length) return errors;

  if (filters.to < filters.from) {
    errors.push("The end date must be on or after the start date.");
    return errors;
  }

  const days = daysInclusive(filters.from, filters.to);
  if (days > maxRangeDays) {
    errors.push(`The selected period is ${days} days. The maximum is ${maxRangeDays} days.`);
  }

  if (!TIME.test(filters.cutoff)) {
    errors.push("Cut-off time must use the 24-hour HH:MM format.");
  }

  if (filters.mode === "fixed") {
    if (!isValidLocalDateTime(filters.at)) {
      errors.push("Enter a valid fixed cut-off date and time.");
    } else if (filters.at >= `${filters.from}T00:00`) {
      errors.push("The fixed cut-off must be before the first delivery interval.");
    }
  }

  return errors;
}

export function fixedModeDefaults(filters: FilterState): FilterState {
  return {
    ...filters,
    mode: "fixed",
    at: defaultFixedAt(filters.from, filters.cutoff),
  };
}
