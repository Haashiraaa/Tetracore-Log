// frontend/src/hooks/useNow.ts
import { useSyncExternalStore } from "react";

// One clock for the whole app: every ticking number on a screen shares a single timer.
let now = Date.now();
let timer: number | undefined;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  if (listeners.size === 0) {
    now = Date.now();
    timer = window.setInterval(() => {
      if (document.hidden) return;
      now = Date.now();
      listeners.forEach((l) => l());
    }, 1000);
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.clearInterval(timer);
  };
}

/** The time now (ms since epoch), updated every second while the tab is visible. */
export function useNow(): number {
  return useSyncExternalStore(subscribe, () => now);
}
