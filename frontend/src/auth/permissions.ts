// frontend/src/auth/permissions.ts
// Access gates for the UI. Counterpart of the gates in backend/src/api/deps.py.
// These only decide what to SHOW. The backend re-checks every request.
// The role is just a label: access comes from the facts the server puts on the profile.

import type { OfficerProfile } from "@/api/schemas";

/** Writes log entries: any account that belongs to a facility. */
export function canWriteEntries(p: OfficerProfile): boolean {
  return p.can_write_entries;
}

export function isAdmin(p: OfficerProfile): boolean {
  return p.is_admin;
}

export function seesAllFacilities(p: OfficerProfile): boolean {
  return p.sees_all_facilities;
}

/** Where a person lands after logging in. */
export function homePathFor(p: OfficerProfile | null): string {
  if (!p) return "/login";
  return canWriteEntries(p) ? "/gate" : "/inside";
}
