// frontend/src/services/adminService.ts
// Admin rules. Mirrors backend/src/api/admin_service.py.
// Temp PINs are returned once by the server; nothing here stores them.

import { fullNameError } from "@/lib/people";
import * as adminApi from "@/api/admin";
import type {
  CreateFacilityRequest,
  CreateOfficerRequest,
  Facility,
  StateOption,
} from "@/api/schemas";
import { ROLE_MAX_LENGTH } from "@/models";

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

/** What the "show the temp PIN once" dialog needs. */
export interface PinReveal {
  title: string;
  officerCode: string;
  fullName: string;
  facilityCode: string | null;
  tempPin: string;
}


// ---- facilities ----

export const MAX_GATES = 20;

/** "4" -> 4; null when it is not a whole number from 1 to 20. */
export function parseGateCount(raw: string): number | null {
  const text = raw.trim();
  if (!/^\d{1,2}$/.test(text)) return null;
  const n = Number(text);
  return n >= 1 && n <= MAX_GATES ? n : null;
}

export const GATE_COUNT_ERROR = `Enter a number of gates from 1 to ${MAX_GATES}.`;

export function validateFacility(
  state: string,
  name: string,
  gates: string,
): { ok: true; value: CreateFacilityRequest } | { ok: false; errors: FieldErrors<"state" | "name" | "gates"> } {
  const errors: FieldErrors<"state" | "name" | "gates"> = {};
  const n = name.trim();
  const gateCount = parseGateCount(gates);
  if (!state) errors.state = "Choose the state.";
  if (n.length < 2) errors.name = "Enter the facility name.";
  if (gateCount === null) errors.gates = GATE_COUNT_ERROR;
  if (Object.keys(errors).length > 0 || gateCount === null) return { ok: false, errors };
  return { ok: true, value: { state, name: n, gate_count: gateCount } };
}

export function setGates(facilityCode: string, gates: string): Promise<Facility> {
  const gateCount = parseGateCount(gates);
  if (gateCount === null) return Promise.reject(new Error(GATE_COUNT_ERROR));
  return adminApi.setGates(facilityCode, gateCount);
}

export function endDuty(officerId: string): Promise<void> {
  return adminApi.endDuty(officerId);
}

export function listStates(signal?: AbortSignal): Promise<StateOption[]> {
  return adminApi.listStates(signal);
}

export function createFacility(body: CreateFacilityRequest): Promise<Facility> {
  return adminApi.createFacility(body);
}

// ---- officers ----

export function validateNewAccount(
  fullName: string,
  role: string,
  facilityCode: string,
): FieldErrors<"fullName" | "role" | "facility"> {
  const errors: FieldErrors<"fullName" | "role" | "facility"> = {};
  const r = role.trim();
  const nameProblem = fullNameError(fullName, "the person's");
  if (nameProblem) errors.fullName = nameProblem;
  if (r.length === 0 || r.length > ROLE_MAX_LENGTH) errors.role = `Enter a role of 1-${ROLE_MAX_LENGTH} characters.`;
  if (!facilityCode.trim()) errors.facility = "Choose a facility.";
  return errors;
}

export async function createOfficer(body: CreateOfficerRequest): Promise<PinReveal> {
  const res = await adminApi.createOfficer(body);
  return {
    title: "Account created",
    officerCode: res.officer.officer_code,
    fullName: res.officer.full_name,
    facilityCode: res.officer.facility_code,
    tempPin: res.temp_pin,
  };
}

export async function resetOfficerPin(officerId: string, facilityCode: string | null): Promise<PinReveal> {
  const res = await adminApi.resetPin(officerId);
  return {
    title: "PIN reset",
    officerCode: res.officer_code,
    fullName: res.full_name,
    facilityCode,
    tempPin: res.temp_pin,
  };
}
