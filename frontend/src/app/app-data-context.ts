import { createContext } from "react";

import type { HealthResponse, MetadataResponse } from "../types/api";

export interface AppDataState {
  metadata: MetadataResponse | undefined;
  metadataLoading: boolean;
  metadataError: Error | null;
  reloadMetadata: () => void;
  health: HealthResponse | undefined;
  healthLoading: boolean;
  healthError: Error | null;
  refreshHealth: () => void;
}

export const AppDataContext = createContext<AppDataState | null>(null);
