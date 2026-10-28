import { useEffect, useMemo } from "react";
import type { ReactNode } from "react";

import { AppDataContext, type AppDataState } from "./app-data-context";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { HealthResponse, MetadataResponse } from "../types/api";

export function AppDataProvider({ children }: { children: ReactNode }) {
  const metadata = useResource<MetadataResponse>(
    "metadata",
    (signal) => api.getMetadata(signal),
    { keepPrevious: true },
  );
  const health = useResource<HealthResponse>(
    "health",
    (signal) => api.getHealth(signal),
    { keepPrevious: true },
  );

  useEffect(() => {
    const timer = window.setInterval(health.retry, 60_000);
    return () => window.clearInterval(timer);
  }, [health.retry]);

  const value: AppDataState = useMemo(
    () => ({
      metadata: metadata.data,
      metadataLoading: metadata.loading,
      metadataError: metadata.error,
      reloadMetadata: metadata.retry,
      health: health.data,
      healthLoading: health.loading,
      healthError: health.error,
      refreshHealth: health.retry,
    }),
    [metadata, health],
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}
