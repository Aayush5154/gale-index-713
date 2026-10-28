import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled application error", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
          <div className="panel panel-pad max-w-md" role="alert">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-danger">
              Application error
            </p>
            <h1 className="mt-2 text-lg font-semibold text-ink">This view could not be displayed</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              An unexpected client-side error occurred. The API was not modified. Reload the page to
              start a new analysis session.
            </p>
            <button
              type="button"
              className="btn btn-primary mt-4"
              onClick={() => window.location.reload()}
            >
              Reload application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
