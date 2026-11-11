// frontend/src/services/truckService.ts
// Truck rules. Mirrors backend/src/api/truck_service.py (and its layering):
// api/trucks.ts only talks HTTP; decisions and validation live here. What every log
// shares (lists, sign-out, export) is in entryService.ts.

import type { TruckEntry, TruckLookup, TruckSignInRequest } from "@/api/schemas";
import * as trucksApi from "@/api/trucks";
import { REQUIRE_SIGNATURE } from "@/config/env";
import { deviceId } from "@/lib/ids";
import { isValidPlate, normalizePlate } from "@/lib/plate";
import type { FieldErrors } from "./entryService";

// ---- lookup ----

export type LookupResult =
  | { kind: "new"; plate: string }
  | { kind: "returning"; truck: TruckLookup }
  | { kind: "inside"; truck: TruckLookup };

export function validatePlate(raw: string): { plate: string } | { error: string } {
  const plate = normalizePlate(raw);
  if (!isValidPlate(plate)) return { error: "Enter a plate of 2 to 20 letters or digits." };
  return { plate };
}

export async function lookup(plate: string): Promise<LookupResult> {
  const truck = await trucksApi.lookupTruck(plate);
  if (truck === null) return { kind: "new", plate };
  return truck.open_entry_id ? { kind: "inside", truck } : { kind: "returning", truck };
}

// ---- sign-in ----

export interface SignInForm {
  plate: string;
  driverName: string;
  driverPhone: string;
  company: string;
}

type SignInField = "driverName" | "signature";

export function buildSignInRequest(
  entryId: string,
  form: SignInForm,
  signaturePng: string | null,
): { ok: true; value: TruckSignInRequest } | { ok: false; errors: FieldErrors<SignInField> } {
  const errors: FieldErrors<SignInField> = {};
  const driverName = form.driverName.trim();
  if (driverName.length < 2) errors.driverName = "Enter the driver's full name.";
  if (REQUIRE_SIGNATURE && !signaturePng) errors.signature = "Ask the driver to sign.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      plate_number: normalizePlate(form.plate),
      driver_name: driverName,
      driver_phone: form.driverPhone.trim() || null,
      company: form.company.trim() || null,
      signature: signaturePng,
      device_id: deviceId(),
      // signed_in_at is left out on purpose: the server clock is the truth while online.
    },
  };
}

export function signIn(request: TruckSignInRequest): Promise<TruckEntry> {
  return trucksApi.signIn(request);
}
