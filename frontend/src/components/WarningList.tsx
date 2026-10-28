import { CheckCircle2 } from "lucide-react";

import { Notice } from "./ui/Notice";

export function WarningList({
  warnings,
  emptyMessage,
}: {
  warnings: string[];
  emptyMessage?: string;
}) {
  const unique = [...new Set(warnings)];
  if (unique.length === 0) {
    if (!emptyMessage) return null;
    return (
      <p className="flex items-start gap-2 text-xs leading-5 text-faint">
        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{emptyMessage}</span>
      </p>
    );
  }

  return (
    <Notice tone="warn" title={`${unique.length} data-quality ${unique.length === 1 ? "warning" : "warnings"}`}>
      <ul className="list-disc space-y-1 pl-4">
        {unique.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </Notice>
  );
}
