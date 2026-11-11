// frontend/src/services/staffService.ts
// Staff rules. Mirrors backend/src/api/staff_service.py.

import type { StaffEntry, StaffLookup, StaffSignInRequest } from "@/api/schemas";
import * as staffApi from "@/api/staff";
import { deviceId } from "@/lib/ids";
import { cleanFullName, fullNameError } from "@/lib/people";
import type { FieldErrors } from "./entryService";

export interface StaffForm {
  fullName: string;
  capacity: string;
}

export const BLANK_STAFF: StaffForm = { fullName: "", capacity: "" };

/** A returning staff member: what was written last time, to confirm. */
export function formFromLookup(found: StaffLookup): StaffForm {
  return { fullName: found.full_name, capacity: found.capacity ?? "" };
}

export function search(typed: string): Promise<StaffLookup[]> {
  return staffApi.search(typed);
}

export function lookup(phone: string): Promise<StaffLookup | null> {
  return staffApi.lookup(phone);
}

type Field = "fullName" | "capacity" | "signature";

/** `phone` is already canonical (it came from the lookup step). */
export function buildSignInRequest(
  entryId: string,
  phone: string,
  form: StaffForm,
  signaturePng: string | null,
): { ok: true; value: StaffSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const nameProblem = fullNameError(form.fullName, "the staff member's");
  if (nameProblem) errors.fullName = nameProblem;
  if (form.capacity.trim().length < 2) errors.capacity = "Enter the capacity they work in, such as Cashier.";
  if (!signaturePng) errors.signature = "Ask them to sign.";
  if (Object.keys(errors).length > 0 || !signaturePng) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      full_name: cleanFullName(form.fullName),
      capacity: form.capacity.trim(),
      phone,
      signature: signaturePng,
      device_id: deviceId(),
    },
  };
}

export function signIn(request: StaffSignInRequest): Promise<StaffEntry> {
  return staffApi.signIn(request);
}
