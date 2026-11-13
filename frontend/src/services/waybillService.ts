// frontend/src/services/waybillService.ts
// Waybill rules. Mirrors backend/src/api/waybill_service.py.

import type { WaybillEntry, WaybillLookup, WaybillSignInRequest } from "@/api/schemas";
import * as waybillApi from "@/api/waybill";
import { deviceId } from "@/lib/ids";
import { cleanFullName, fullNameError } from "@/lib/people";
import { isValidPlate, normalizePlate } from "@/lib/plate";
import type { FieldErrors } from "./entryService";
import { cleanItems, type ItemRow } from "./visitorService";

export interface WaybillForm {
  fullName: string;
  items: ItemRow[];
  /** Did the courier drive here? On foot means no plate. */
  cameByVehicle: boolean;
  plate: string;
}

export const BLANK_WAYBILL: WaybillForm = { fullName: "", items: [], cameByVehicle: false, plate: "" };

/** A returning courier: their name and the vehicle they last came with, to confirm.
 *  What they bring is new each visit. */
export function formFromLookup(found: WaybillLookup): WaybillForm {
  return {
    ...BLANK_WAYBILL,
    fullName: found.full_name,
    cameByVehicle: found.came_by_vehicle,
    plate: found.plate_number ?? "",
  };
}

export function search(typed: string): Promise<WaybillLookup[]> {
  return waybillApi.search(typed);
}

export function lookup(phone: string): Promise<WaybillLookup | null> {
  return waybillApi.lookup(phone);
}

type Field = "fullName" | "items" | "plate" | "signature";

/** `phone` is already canonical. `signatureOnFile`: the server already has this courier's
 *  signature, so none is needed (null `signaturePng` reuses it). */
export function buildSignInRequest(
  entryId: string,
  phone: string,
  form: WaybillForm,
  signaturePng: string | null,
  signatureOnFile = false,
): { ok: true; value: WaybillSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const nameProblem = fullNameError(form.fullName, "the courier's");
  if (nameProblem) errors.fullName = nameProblem;
  const cleaned = cleanItems(form.items);
  if ("error" in cleaned) errors.items = cleaned.error;
  else if (cleaned.items.length === 0) errors.items = "Add what the courier brought.";
  const plate = normalizePlate(form.plate);
  if (form.cameByVehicle && !isValidPlate(plate)) errors.plate = "Enter a plate of 2 to 20 letters or digits.";
  if (!signaturePng && !signatureOnFile) errors.signature = "Ask the courier to sign.";
  if (Object.keys(errors).length > 0 || "error" in cleaned) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      full_name: cleanFullName(form.fullName),
      phone,
      items: cleaned.items,
      came_by_vehicle: form.cameByVehicle,
      plate_number: form.cameByVehicle ? plate : null,
      signature: signaturePng,
      device_id: deviceId(),
    },
  };
}

export function signIn(request: WaybillSignInRequest): Promise<WaybillEntry> {
  return waybillApi.signIn(request);
}
