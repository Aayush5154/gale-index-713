import { useContext } from "react";

import { AppDataContext, type AppDataState } from "../app/app-data-context";

export function useAppData(): AppDataState {
  const context = useContext(AppDataContext);
  if (!context) throw new Error("useAppData must be used inside AppDataProvider");
  return context;
}
