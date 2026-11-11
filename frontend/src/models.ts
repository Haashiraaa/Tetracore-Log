// frontend/src/models.ts
// Shared constants. Mirrors backend/src/models.py.

/** A free-form label, such as "officer" or "Shift supervisor". Nothing in the app checks it:
 *  what an account can do comes from the profile (`can_write_entries`, `is_admin`, ...). */
export type Role = string;

export const DEFAULT_ROLE: Role = "officer";
export const ROLE_MAX_LENGTH = 32;

/** The three logs. The value is also the API path: /api/<kind>/entries. */
export type LogKind = "trucks" | "visitors" | "staff";

export const LOG_KINDS: readonly LogKind[] = ["trucks", "visitors", "staff"];

export const LOG_LABEL: Record<LogKind, { many: string; one: string }> = {
  trucks: { many: "Trucks", one: "truck" },
  visitors: { many: "Visitors", one: "visitor" },
  staff: { many: "Staff", one: "staff member" },
};
