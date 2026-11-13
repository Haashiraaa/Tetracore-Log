// frontend/src/lib/haptics.ts

/** A short buzz on phones that support it, to confirm that something was written. */
export function buzz(ms = 30): void {
  try {
    navigator.vibrate?.(ms);
  } catch {
    /* not supported or not allowed: the stamp on screen is enough */
  }
}
