// frontend/src/hooks/useAsync.ts
import { useCallback, useEffect, useState, type DependencyList } from "react";

interface AsyncState<T> {
  data: T | null;
  error: unknown;
  loading: boolean;
}

/**
 * Runs `fn` on mount and whenever `deps` change or reload() is called.
 * Keeps the previous data while reloading, so auto-refreshing lists don't flash.
 */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    fn(ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setState({ data, error: null, loading: false });
      })
      .catch((error: unknown) => {
        if (ctrl.signal.aborted) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState((s) => ({ ...s, error, loading: false }));
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
