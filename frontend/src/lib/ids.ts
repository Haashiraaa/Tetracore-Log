// frontend/src/lib/ids.ts

/**
 * RFC 4122 v4 UUID. crypto.randomUUID() only exists in secure contexts (https
 * or localhost), so opening the app from a phone over http://192.168.x.x would
 * crash without this fallback. getRandomValues works everywhere.
 */
export function uuid(): string {
  const c = globalThis.crypto;
  if (typeof c.randomUUID === "function") return c.randomUUID();
  const b = new Uint8Array(16);
  c.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0"));
  return [h.slice(0, 4), h.slice(4, 6), h.slice(6, 8), h.slice(8, 10), h.slice(10)]
    .map((p) => p.join(""))
    .join("-");
}

const DEVICE_KEY = "log-book.device_id";
const OLD_DEVICE_KEY = "tetracore-log.device_id"; // the app's name before the rename

/** Stable per-browser id, stored on each entry so odd rows can be traced to a device. */
export function deviceId(): string {
  try {
    let id = window.localStorage.getItem(DEVICE_KEY);
    if (!id) {
      // Keep the id this browser already had under the old name, so its past entries still match.
      id = window.localStorage.getItem(OLD_DEVICE_KEY) ?? uuid();
      window.localStorage.removeItem(OLD_DEVICE_KEY);
      window.localStorage.setItem(DEVICE_KEY, id);
    }
    return id;
  } catch {
    return "unknown";
  }
}
