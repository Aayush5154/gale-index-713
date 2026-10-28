import { ArrowRight, RotateCcw, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import type { FilterState } from "../utils/filters";
import {
  DEFAULT_FILTERS,
  DEFAULT_MAX_RANGE_DAYS,
  daysInclusive,
  fixedModeDefaults,
  todayInLondon,
  validateFilters,
} from "../utils/filters";
import { Notice } from "./ui/Notice";

export function FilterBar({
  filters,
  onApply,
  onReset,
  maxRangeDays = DEFAULT_MAX_RANGE_DAYS,
}: {
  filters: FilterState;
  onApply: (filters: FilterState) => void;
  onReset: () => void;
  maxRangeDays?: number;
}) {
  const [draft, setDraft] = useState<FilterState>(filters);
  const [attempted, setAttempted] = useState(false);
  const today = todayInLondon();

  useEffect(() => {
    setDraft(filters);
    setAttempted(false);
  }, [filters]);

  const errors = attempted ? validateFilters(draft, maxRangeDays) : [];
  const days = daysInclusive(draft.from, draft.to);

  function update<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function selectMode(mode: FilterState["mode"]) {
    setDraft((current) =>
      mode === "fixed" ? fixedModeDefaults(current) : { ...current, mode },
    );
  }

  function apply() {
    setAttempted(true);
    const nextErrors = validateFilters(draft, maxRangeDays);
    if (nextErrors.length > 0) return;
    onApply(draft);
    setAttempted(false);
  }

  function reset() {
    setDraft(DEFAULT_FILTERS);
    setAttempted(false);
    onReset();
  }

  function presetJanuary() {
    setDraft((current) => ({
      ...current,
      from: "2026-01-01",
      to: "2026-01-31",
      at: "2025-12-31T09:20",
    }));
    setAttempted(false);
  }

  return (
    <section className="panel panel-pad" aria-labelledby="analysis-window-heading">
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-accent" aria-hidden="true" />
          <h2 id="analysis-window-heading" className="text-sm font-semibold text-ink">
            Analysis window
          </h2>
        </div>
        <button type="button" onClick={presetJanuary} className="btn btn-ghost self-start px-2 py-1 text-xs sm:self-auto">
          Load January 2026
        </button>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div>
          <label htmlFor="filter-from" className="label">
            Delivery from
          </label>
          <input
            id="filter-from"
            type="date"
            className="input mt-1.5"
            value={draft.from}
            max={today}
            onChange={(event) => update("from", event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="filter-to" className="label">
            Delivery to
          </label>
          <input
            id="filter-to"
            type="date"
            className="input mt-1.5"
            value={draft.to}
            max={today}
            onChange={(event) => update("to", event.target.value)}
          />
        </div>
        <div>
          <span className="label" id="cutoff-mode-label">
            Cut-off mode
          </span>
          <div
            role="group"
            aria-labelledby="cutoff-mode-label"
            className="mt-1.5 inline-flex w-full rounded-sm border border-line-strong bg-canvas p-0.5"
          >
            <button
              type="button"
              aria-pressed={draft.mode === "daily"}
              onClick={() => selectMode("daily")}
              className={`flex-1 rounded px-2 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                draft.mode === "daily" ? "bg-raised text-ink" : "text-muted hover:text-ink"
              }`}
            >
              Daily D-1
            </button>
            <button
              type="button"
              aria-pressed={draft.mode === "fixed"}
              onClick={() => selectMode("fixed")}
              className={`flex-1 rounded px-2 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                draft.mode === "fixed" ? "bg-raised text-ink" : "text-muted hover:text-ink"
              }`}
            >
              Fixed cut-off
            </button>
          </div>
        </div>
        {draft.mode === "daily" ? (
          <div>
            <label htmlFor="filter-cutoff" className="label">
              Cut-off time · London
            </label>
            <input
              id="filter-cutoff"
              type="time"
              className="input mt-1.5"
              value={draft.cutoff}
              step={60}
              onChange={(event) => update("cutoff", event.target.value)}
            />
          </div>
        ) : (
          <div>
            <label htmlFor="filter-at" className="label">
              Fixed cut-off · London
            </label>
            <input
              id="filter-at"
              type="datetime-local"
              className="input mt-1.5"
              value={draft.at}
              onChange={(event) => update("at", event.target.value)}
            />
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-xs leading-5 text-muted">
          <span className="tnum">{days}</span> delivery {days === 1 ? "day" : "days"} selected ·{" "}
          {draft.mode === "daily"
            ? `each day uses ${draft.cutoff} Europe/London on D-1`
            : "one cut-off applies to every interval and must precede the first delivery"}
          .
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={reset} className="btn btn-ghost">
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Reset
          </button>
          <button type="button" onClick={apply} className="btn btn-primary">
            Apply
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {errors.length > 0 ? (
        <div className="mt-3" role="alert">
          <Notice tone="danger" title="Check the analysis window">
            <ul className="list-disc space-y-1 pl-4">
              {errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          </Notice>
        </div>
      ) : null}
    </section>
  );
}
