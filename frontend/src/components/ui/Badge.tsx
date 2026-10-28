import type { ReactNode } from "react";

export type BadgeTone = "accent" | "neutral" | "warn" | "danger" | "muted";

const TONE_CLASSES: Record<BadgeTone, string> = {
  accent: "border-accent/30 bg-accent/10 text-accent",
  neutral: "border-line-strong bg-raised text-muted",
  warn: "border-warn/30 bg-warn/10 text-warn",
  danger: "border-danger/30 bg-danger/10 text-danger",
  muted: "border-line bg-transparent text-faint",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.09em] ${TONE_CLASSES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
