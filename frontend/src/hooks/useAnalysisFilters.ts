import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { AnalysisParams } from "../types/api";
import {
  readFilters,
  toAnalysisParams,
  toSearchParams,
  type FilterState,
} from "../utils/filters";

export interface AnalysisFilterController {
  filters: FilterState;
  params: AnalysisParams;
  key: string;
  apply: (next: FilterState) => void;
  reset: () => void;
}

export function useAnalysisFilters(): AnalysisFilterController {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);
  const params = useMemo(() => toAnalysisParams(filters), [filters]);
  const key = useMemo(() => JSON.stringify(params), [params]);

  const apply = useCallback(
    (next: FilterState) => {
      setSearchParams(toSearchParams(next), { replace: false });
    },
    [setSearchParams],
  );

  const reset = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: false });
  }, [setSearchParams]);

  return { filters, params, key, apply, reset };
}
