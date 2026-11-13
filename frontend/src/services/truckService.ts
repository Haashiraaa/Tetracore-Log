// frontend/src/services/truckService.ts
// Truck rules. Mirrors backend/src/api/truck_service.py (and its layering):
// api/trucks.ts only talks HTTP; decisions and validation live here. What every log
// shares (lists, sign-out, export) is in entryService.ts.

import type { TruckEntry, TruckLookup, TruckSignInRequest } from "@/api/schemas";
import * as trucksApi from "@/api/trucks";
import { PHONE_ERROR, cleanFullName, cleanPhone, fullNameError } from "@/lib/people";
import { deviceId } from "@/lib/ids";
import { isValidPlate, normalizePlate } from "@/lib/plate";
import type { FieldErrors } from "./entryService";

// ---- lookup ----

export type LookupResult =
  | { kind: "new"; plate: string }
  | { kind: "returning"; truck: TruckLookup }
  | { kind: "queued"; truck: TruckLookup }
  | { kind: "inside"; truck: TruckLookup };

export function validatePlate(raw: string): { plate: string } | { error: string } {
  const plate = normalizePlate(raw);
  if (!isValidPlate(plate)) return { error: "Enter a plate of 2 to 20 letters or digits." };
  return { plate };
}

export async function lookup(plate: string): Promise<LookupResult> {
  const truck = await trucksApi.lookupTruck(plate);
  if (truck === null) return { kind: "new", plate };
  if (truck.open_entry_status === "queued") return { kind: "queued", truck };
  if (truck.open_entry_id) return { kind: "inside", truck };
  return { kind: "returning", truck };
}

// ---- registering a truck ----

export interface SignInForm {
  plate: string;
  driverName: string;
  driverPhone: string;
  company: string;
  /** Only some trucks have a cab number. Blank is fine. */
  cabNumber: string;
}

type SignInField = "driverName" | "driverPhone" | "signature";

/** Register a truck. By default it joins the queue (no signature yet); with `enterNow` it
 *  is let in on the spot, which needs the driver's signature. */
export function buildSignInRequest(
  entryId: string,
  form: SignInForm,
  opts: { enterNow: boolean; signaturePng: string | null; signatureOnFile?: boolean },
): { ok: true; value: TruckSignInRequest } | { ok: false; errors: FieldErrors<SignInField> } {
  const errors: FieldErrors<SignInField> = {};
  const driverName = form.driverName.trim();
  const nameProblem = fullNameError(driverName, "the driver's");
  if (nameProblem) errors.driverName = nameProblem;
  // A phone is optional, but a number that is given must be a real one for its country.
  const driverPhone = form.driverPhone.trim() ? cleanPhone(form.driverPhone) : null;
  if (form.driverPhone.trim() && !driverPhone) errors.driverPhone = PHONE_ERROR;
  if (opts.enterNow && !opts.signaturePng && !opts.signatureOnFile) errors.signature = "Ask the driver to sign.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      plate_number: normalizePlate(form.plate),
      driver_name: cleanFullName(driverName),
      driver_phone: driverPhone,
      company: form.company.trim() || null,
      cab_number: form.cabNumber.trim() || null,
      // no signature + enter_now = the server uses the one on file for this plate
      ...(opts.enterNow ? { enter_now: true, ...(opts.signaturePng ? { signature: opts.signaturePng } : {}) } : {}),
      device_id: deviceId(),
      // signed_in_at is left out on purpose: the server clock is the truth while online.
    },
  };
}

export function signIn(request: TruckSignInRequest): Promise<TruckEntry> {
  return trucksApi.signIn(request);
}

// ---- moving a queued truck on ----

export const LEAVE_REASON_MAX = 300;

export function leaveReasonError(raw: string): string | null {
  const reason = raw.trim();
  if (reason.length < 2) return "Say why the truck left the queue.";
  if (reason.length > LEAVE_REASON_MAX) return `Keep it under ${LEAVE_REASON_MAX} characters.`;
  return null;
}

/** Let a queued truck in; the driver signs, or null to use the signature on file. */
export function enter(entryId: string, signaturePng: string | null): Promise<TruckEntry> {
  return trucksApi.enter(entryId, signaturePng ? { signature: signaturePng } : {});
}

/** A queued truck gave up before entering. */
export function leaveQueue(entryId: string, reason: string): Promise<TruckEntry> {
  return trucksApi.leaveQueue(entryId, { reason: reason.trim() });
}

/** The words for a status, for badges and CSV. */
export const STATUS_LABEL: Record<TruckEntry["status"], string> = {
  queued: "Queued",
  on_site: "On site",
  departed: "Departed",
  left_queue: "Left queue",
};
