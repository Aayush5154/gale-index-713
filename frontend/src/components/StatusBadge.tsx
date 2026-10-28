import { Badge } from "./ui/Badge";

const LABELS: Record<string, { label: string; tone: "accent" | "neutral" | "warn" | "danger" | "muted" }> = {
  matched: { label: "Matched", tone: "accent" },
  available: { label: "Available", tone: "accent" },
  missing_forecast: { label: "No forecast", tone: "warn" },
  missing_actual: { label: "No outturn", tone: "neutral" },
  missing_both: { label: "No data", tone: "danger" },
};

export function StatusBadge({ status }: { status: string }) {
  const item = LABELS[status] ?? { label: status, tone: "muted" as const };
  return <Badge tone={item.tone}>{item.label}</Badge>;
}
