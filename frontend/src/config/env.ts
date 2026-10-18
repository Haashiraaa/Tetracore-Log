// frontend/src/config/env.ts
// Counterpart of backend/src/config/settings.py: every tunable lives here.

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "") || "/api";

/** The database stores UTC. Everything shown to people is Lagos time. */
export const DISPLAY_TZ = "Africa/Lagos";
/** Nigeria has no daylight saving, so a fixed offset is safe for day boundaries. */
export const DISPLAY_UTC_OFFSET = "+01:00";

/** A security log without a signature defeats the point; flip to false to make it optional. */
export const REQUIRE_SIGNATURE = true;
/** Backend rejects signatures over 200 KB; stay comfortably under. */
export const SIGNATURE_MAX_BYTES = 180 * 1024;

export const PAGE_SIZE = 50;
export const INSIDE_REFRESH_MS = 30_000;
export const EXPORT_ROW_CAP = 5_000;

/** Mirrors validate_pin_policy in backend/src/security/passwords.py. */
export const PIN_MIN_LENGTH = 6;
export const PIN_MAX_LENGTH = 10;
