// frontend/src/services/adminService.ts
// Admin rules. Mirrors backend/src/api/admin_service.py and super_admin_service.py.
// Temp PINs are returned once by the server; nothing here stores them.

import * as adminApi from "@/api/admin";
import * as superAdminApi from "@/api/superAdmin";
import type {
  CreateAdminRequest,
  CreateFacilityRequest,
  CreateOfficerRequest,
  Facility,
} from "@/api/schemas";
import { isFacilityRole, type Role } from "@/models";

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

/** What the "show the temp PIN once" dialog needs. */
export interface PinReveal {
  title: string;
  officerCode: string;
  fullName: string;
  facilityCode: string | null;
  tempPin: string;
}

const CODE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9-]*$/;

// ---- facilities ----

export function validateFacility(
  code: string,
  name: string,
): { ok: true; value: CreateFacilityRequest } | { ok: false; errors: FieldErrors<"code" | "name"> } {
  const errors: FieldErrors<"code" | "name"> = {};
  const c = code.trim();
  const n = name.trim();
  if (c.length < 2 || c.length > 32 || !CODE_PATTERN.test(c)) {
    errors.code = "Use 2-32 letters, digits or dashes, such as CNG-BEN-01.";
  }
  if (n.length < 2) errors.name = "Enter the facility name.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, value: { code: c, name: n } };
}

export function createFacility(body: CreateFacilityRequest): Promise<Facility> {
  return adminApi.createFacility(body);
}

// ---- officers ----

export function validateNewAccount(
  fullName: string,
  role: Role,
  facilityCode: string,
): FieldErrors<"fullName" | "facility"> {
  const errors: FieldErrors<"fullName" | "facility"> = {};
  if (fullName.trim().length < 2) errors.fullName = "Enter the person's full name.";
  if (isFacilityRole(role) && !facilityCode.trim()) errors.facility = "Choose a facility.";
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

// ---- admins (super admin only) ----

export async function createAdmin(body: CreateAdminRequest): Promise<PinReveal> {
  const res = await superAdminApi.createAdmin(body);
  return {
    title: "Admin account created",
    officerCode: res.officer.officer_code,
    fullName: res.officer.full_name,
    facilityCode: res.officer.facility_code,
    tempPin: res.temp_pin,
  };
}

export async function resetAdminPin(officerId: string): Promise<PinReveal> {
  const res = await superAdminApi.resetAdminPin(officerId);
  return {
    title: "PIN reset",
    officerCode: res.officer.officer_code,
    fullName: res.officer.full_name,
    facilityCode: res.officer.facility_code,
    tempPin: res.temp_pin,
  };
}
