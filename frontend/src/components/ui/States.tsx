import { AlertCircle, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";

import { ApiError } from "../../services/api";

export function ErrorState({
  error,
  onRetry,
  title = "This view could not be loaded",
  children,
}: {
  error: Error;
  onRetry?: () => void;
  title?: string;
  children?: ReactNode;
}) {
  const apiError = error instanceof ApiError ? error : null;
  return (
    <div className="panel panel-pad" role="alert">
      <div className="flex gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden="true" />
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted">{error.message}</p>
          {children}
          {apiError ? (
            <p className="mt-2 text-xs leading-5 text-faint">
              Code: <span className="font-mono">{apiError.code}</span>
              {apiError.status ? ` · HTTP ${apiError.status}` : ""}
              {apiError.requestId ? ` · Request ${apiError.requestId}` : ""}
            </p>
          ) : null}
          {onRetry ? (
            <button type="button" onClick={onRetry} className="btn btn-secondary mt-4">
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Retry request
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-sm border border-dashed border-line-strong bg-panel/50 px-6 py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-md text-xs leading-5 text-muted">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
