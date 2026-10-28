import type { ReactNode } from "react";

export interface KpiCardProps {
  label: string;
  value: string;
  unit?: string;
  hint: string;
  badge?: ReactNode;
  footnote?: string;
  tone?: "default" | "accent" | "warn" | "danger";
}

const VALUE_TONES = {
  default: "text-ink",
  accent: "text-accent",
  warn: "text-warn",
  danger: "text-danger",
};

export function KpiCard({
  label,
  value,
  unit,
  hint,
  badge,
  footnote,
  tone = "default",
}: KpiCardProps) {
  return (
    <div className="panel flex min-h-[136px] flex-col p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="label">{label}</p>
        {badge}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className={`text-[28px] font-semibold leading-none tracking-tight tnum ${VALUE_TONES[tone]}`}>
          {value}
        </span>
        {unit ? <span className="text-sm text-muted">{unit}</span> : null}
      </div>
      <p className="mt-2 text-xs leading-4 text-muted">{hint}</p>
      {footnote ? <p className="mt-auto pt-2 text-[10px] leading-4 text-faint">{footnote}</p> : null}
    </div>
  );
}
