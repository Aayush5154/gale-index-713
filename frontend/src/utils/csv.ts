import type { ComparisonInterval } from "../types/api";

function escapeCell(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (text.includes(",") || text.includes('"') || text.includes("\n")) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

const HEADERS = [
  "delivery_start_local",
  "delivery_date_local",
  "cutoff_local",
  "status",
  "forecast_mw",
  "actual_mw",
  "signed_error_mw",
  "absolute_error_mw",
  "absolute_percentage_error",
  "forecast_publication_local",
  "lead_time_hours",
  "eligible_forecast_count",
  "duplicate_publication",
  "stale_forecast",
];

export function downloadComparisonCsv(
  rows: ComparisonInterval[],
  filename: string,
): void {
  const lines = [HEADERS.join(",")];
  for (const row of rows) {
    lines.push(
      [
        row.delivery_start_local,
        row.delivery_date_local,
        row.cutoff_local,
        row.status,
        row.forecast_mw,
        row.actual_mw,
        row.signed_error_mw,
        row.absolute_error_mw,
        row.absolute_percentage_error,
        row.forecast_publication_local,
        row.lead_time_hours,
        row.eligible_forecast_count,
        row.duplicate_publication,
        row.stale_forecast,
      ]
        .map(escapeCell)
        .join(","),
    );
  }

  const blob = new Blob([`\uFEFF${lines.join("\r\n")}`], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
