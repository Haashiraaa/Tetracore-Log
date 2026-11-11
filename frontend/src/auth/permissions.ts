// frontend/src/auth/permissions.ts
// Role gates for the UI. Counterpart of the gates in backend/src/api/deps.py.
// These only decide what to SHOW. The backend re-checks every request.

import type { OfficerProfile } from "@/api/schemas";

/** Writes log entries: a facility officer (CSO is read-only, managers read-only). */
export function canWriteEntries(p: OfficerProfile): boolean {
  return p.role === "officer" && p.facility_id !== null;
}

export function isAdmin(p: OfficerProfile): boolean {
  return p.is_admin;
}

export function isSuperAdmin(p: OfficerProfile): boolean {
  return p.is_super_admin;
}

export function seesAllFacilities(p: OfficerProfile): boolean {
  return p.sees_all_facilities;
}

/** Where a person lands after logging in. */
export function homePathFor(p: OfficerProfile | null): string {
  if (!p) return "/login";
  return canWriteEntries(p) ? "/gate" : "/inside";
}
