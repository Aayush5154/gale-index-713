import type {
  AnalysisParams,
  ApiErrorResponse,
  ApiErrorDetail,
  ComparisonResponse,
  DailyMetricsResponse,
  HealthResponse,
  MetadataResponse,
  MetricsResponse,
  ForecastResponse,
} from "../types/api";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(
    message: string,
    code = "request_failed",
    status: number | null = null,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!value || typeof value !== "object") return false;
  const error = (value as { error?: unknown }).error;
  return Boolean(error) && typeof error === "object" && typeof (error as ApiErrorDetail).message === "string";
}

function queryString(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, value);
  }
  const serialised = query.toString();
  return serialised ? `?${serialised}` : "";
}

function paramsFromAnalysis(params: AnalysisParams): Record<string, string | undefined> {
  return {
    from_date: params.from_date,
    to_date: params.to_date,
    cutoff_mode: params.cutoff_mode,
    cutoff_time: params.cutoff_time,
    cutoff_datetime: params.cutoff_datetime,
  };
}

async function fetchJson<T>(
  path: string,
  params: Record<string, string | undefined> = {},
  externalSignal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  const onAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort();
    else externalSignal.addEventListener("abort", onAbort, { once: true });
  }

  try {
    const response = await fetch(`${API_BASE}${path}${queryString(params)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
      credentials: "same-origin",
    });

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (isApiErrorResponse(payload)) {
        const detail = payload.error;
        throw new ApiError(
          detail.message,
          detail.code,
          response.status,
          detail.details ?? {},
          detail.request_id ?? response.headers.get("X-Request-ID"),
        );
      }
      throw new ApiError(
        `The API returned HTTP ${response.status}.`,
        "http_error",
        response.status,
        {},
        response.headers.get("X-Request-ID"),
      );
    }

    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError(
        "The API returned a response that could not be read.",
        "invalid_response",
        response.status,
      );
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (externalSignal?.aborted) throw error;
    if (timedOut) {
      throw new ApiError(
        "The request timed out. The Elexon data source may be slow; please retry.",
        "timeout",
      );
    }
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      "The analytics API could not be reached. Check that the backend is running.",
      "network_error",
    );
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", onAbort);
  }
}

export const api = {
  baseUrl: API_BASE,
  getHealth: (signal?: AbortSignal) => fetchJson<HealthResponse>("/health", {}, signal),
  getMetadata: (signal?: AbortSignal) => fetchJson<MetadataResponse>("/metadata", {}, signal),
  getMetrics: (params: AnalysisParams, signal?: AbortSignal) =>
    fetchJson<MetricsResponse>("/metrics", paramsFromAnalysis(params), signal),
  getComparison: (params: AnalysisParams, signal?: AbortSignal) =>
    fetchJson<ComparisonResponse>("/comparison", paramsFromAnalysis(params), signal),
  getForecasts: (params: AnalysisParams, signal?: AbortSignal) =>
    fetchJson<ForecastResponse>("/forecasts", paramsFromAnalysis(params), signal),
  getDaily: (params: AnalysisParams, signal?: AbortSignal) =>
    fetchJson<DailyMetricsResponse>("/accuracy/daily", paramsFromAnalysis(params), signal),
};
