// frontend/src/models.ts
// Shared enums and labels. Mirrors backend/src/models.py.

export type Role = "officer" | "facility_manager" | "cso";

export const ROLE_LABEL: Record<Role, string> = {
  officer: "Gate officer",
  facility_manager: "Facility manager",
  cso: "Chief security officer",
};

/** Roles that belong to exactly one facility. */
export const FACILITY_ROLES: readonly Role[] = ["officer", "facility_manager"];
/** Roles with no facility (they see everything). */
export const GLOBAL_ROLES: readonly Role[] = ["cso"];

export function isFacilityRole(role: Role): boolean {
  return FACILITY_ROLES.includes(role);
}
