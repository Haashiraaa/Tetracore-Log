// frontend/src/config/env.ts
// Counterpart of backend/src/config/settings.py: every tunable lives here.

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "") || "/api";

/** The database stores UTC. Everything shown to people is Lagos time. */
export const DISPLAY_TZ = "Africa/Lagos";
/** Nigeria has no daylight saving, so a fixed offset is safe for day boundaries. */
export const DISPLAY_UTC_OFFSET = "+01:00";

/** Backend rejects signatures over 200 KB; stay comfortably under. */
export const SIGNATURE_MAX_BYTES = 180 * 1024;

export const PAGE_SIZE = 50;
/** How often Gate and Inside ask the server who is inside. */
export const INSIDE_REFRESH_MS = 15_000;
/** How often today's totals (the hour strip, "left today") are fetched. */
export const TODAY_REFRESH_MS = 60_000;
/** The most rows fetched for today's totals, per log. The API allows 200 a request. */
export const TODAY_MAX_ROWS = 200;

/** The stay bar on Inside fills over these hours. They mirror the backend defaults
 *  LEFT_INSIDE_HOURS and QUEUED_WARN_HOURS (backend/src/config/settings.py), the points at
 *  which the server raises its "left inside" and "queued too long" warnings. */
export const STAY_LIMIT_HOURS = 12;
export const QUEUE_LIMIT_HOURS = 6;

/** How long the "Signed out" stamp stays on a line before the line goes. */
export const STAMP_MS = 1_300;

/** With the theme on Auto, the night theme runs between these Lagos hours. */
export const NIGHT_STARTS_HOUR = 19;
export const NIGHT_ENDS_HOUR = 6;
export const EXPORT_ROW_CAP = 5_000;
/** How often the bell asks the server whether anything new happened. */
export const NOTIFICATIONS_POLL_MS = 5_000;

/** Mirrors validate_pin_policy in backend/src/security/passwords.py. */
export const PIN_MIN_LENGTH = 6;
export const PIN_MAX_LENGTH = 10;
