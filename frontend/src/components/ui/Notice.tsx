import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

export type NoticeTone = "info" | "warn" | "danger" | "success";

const TONE_STYLES: Record<NoticeTone, string> = {
  info: "border-line-strong bg-raised/60 text-muted",
  warn: "border-warn/30 bg-warn/[0.06] text-warn",
  danger: "border-danger/30 bg-danger/[0.06] text-danger",
  success: "border-line bg-panel text-muted",
};

const ICONS = {
  info: Info,
  warn: AlertTriangle,
  danger: XCircle,
  success: CheckCircle2,
};

export function Notice({
  tone = "info",
  title,
  children,
}: {
  tone?: NoticeTone;
  title?: string;
  children: ReactNode;
}) {
  const Icon = ICONS[tone];
  return (
    <div className={`flex gap-3 rounded-sm border px-3.5 py-3 ${TONE_STYLES[tone]}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 text-xs leading-5">
        {title ? <p className="mb-0.5 font-semibold text-ink">{title}</p> : null}
        <div className="text-muted">{children}</div>
      </div>
    </div>
  );
}
