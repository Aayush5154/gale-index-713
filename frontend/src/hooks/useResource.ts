import { useCallback, useEffect, useRef, useState } from "react";

export interface ResourceState<T> {
  data: T | undefined;
  error: Error | null;
  loading: boolean;
  retry: () => void;
}

export function useResource<T>(
  key: string,
  loader: (signal: AbortSignal) => Promise<T>,
  options: { keepPrevious?: boolean } = {},
): ResourceState<T> {
  const { keepPrevious = false } = options;
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    if (!keepPrevious) setData(undefined);

    loaderRef
      .current(controller.signal)
      .then((value) => {
        if (controller.signal.aborted) return;
        setData(value);
        setLoading(false);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(caught instanceof Error ? caught : new Error("Unknown request failure"));
        setLoading(false);
      });

    return () => controller.abort();
  }, [key, nonce, keepPrevious]);

  const retry = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, loading, retry };
}
