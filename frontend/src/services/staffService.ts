// frontend/src/services/staffService.ts
// Staff rules. Mirrors backend/src/api/staff_service.py.

import type { StaffEntry, StaffSignInRequest } from "@/api/schemas";
import * as staffApi from "@/api/staff";
import { REQUIRE_SIGNATURE } from "@/config/env";
import { deviceId } from "@/lib/ids";
import type { FieldErrors } from "./entryService";

type Field = "fullName" | "signature";

export function buildSignInRequest(
  entryId: string,
  fullNameRaw: string,
  signaturePng: string | null,
): { ok: true; value: StaffSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const fullName = fullNameRaw.trim();
  if (fullName.length < 2) errors.fullName = "Enter the staff member's name.";
  if (REQUIRE_SIGNATURE && !signaturePng) errors.signature = "Ask them to sign.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: { id: entryId, full_name: fullName, signature: signaturePng, device_id: deviceId() },
  };
}

export function signIn(request: StaffSignInRequest): Promise<StaffEntry> {
  return staffApi.signIn(request);
}
