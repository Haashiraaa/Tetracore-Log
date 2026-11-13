// frontend/src/hooks/useFreshKeys.ts
import { useEffect, useRef, useState } from "react";

const NONE: ReadonlySet<string> = new Set();
/** Long enough for the arrival animation to finish. */
const FRESH_MS = 2_000;

/**
 * Which rows of a list have just appeared. The rows present on the first load are not
 * fresh: only what arrives afterwards is, and only for a moment.
 */
export function useFreshKeys(keys: readonly string[], ready: boolean): ReadonlySet<string> {
  const seen = useRef<Set<string> | null>(null);
  const [fresh, setFresh] = useState<ReadonlySet<string>>(NONE);
  const signature = keys.join("|");

  useEffect(() => {
    if (!ready) return;
    if (seen.current === null) {
      seen.current = new Set(keys);
      return;
    }
    const known = seen.current;
    const added = keys.filter((k) => !known.has(k));
    keys.forEach((k) => known.add(k));
    if (added.length === 0) return;
    setFresh(new Set(added));
    const id = window.setTimeout(() => setFresh(NONE), FRESH_MS);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, ready]);

  return fresh;
}
