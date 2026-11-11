// frontend/src/hooks/useInterval.ts
import { useEffect, useRef } from "react";

/** Calls `callback` every `ms`; pass null to pause. Skips ticks while the tab is hidden. */
export function useInterval(callback: () => void, ms: number | null): void {
  const saved = useRef(callback);
  useEffect(() => {
    saved.current = callback;
  });
  useEffect(() => {
    if (ms === null) return;
    const id = window.setInterval(() => {
      if (!document.hidden) saved.current();
    }, ms);
    return () => window.clearInterval(id);
  }, [ms]);
}
