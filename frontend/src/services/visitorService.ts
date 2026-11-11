// frontend/src/services/visitorService.ts
// Visitor rules. Mirrors backend/src/api/visitor_service.py.

import type { VisitorEntry, VisitorLookup, VisitorSignInRequest } from "@/api/schemas";
import * as visitorsApi from "@/api/visitors";
import { cleanFullName, fullNameError } from "@/lib/people";
import { deviceId } from "@/lib/ids";
import type { FieldErrors } from "./entryService";

/** Quick picks for "purpose of visit". The field stays free text: these only fill it in. */
export const PURPOSE_PICKS = ["Delivery", "Meeting", "Maintenance"] as const;

export interface VisitorForm {
  fullName: string;
  company: string;
  purpose: string;
  itemsReceived: string;
}

export const BLANK_VISITOR: VisitorForm = { fullName: "", company: "", purpose: "", itemsReceived: "" };

/** A returning visitor: what was written last time, to confirm. Purpose and items are new each visit. */
export function formFromLookup(found: VisitorLookup): VisitorForm {
  return { ...BLANK_VISITOR, fullName: found.full_name, company: found.company ?? "" };
}

export function search(typed: string): Promise<VisitorLookup[]> {
  return visitorsApi.search(typed);
}

export function lookup(phone: string): Promise<VisitorLookup | null> {
  return visitorsApi.lookup(phone);
}

type Field = "fullName" | "signature";

/** `phone` is already canonical (it came from the lookup step). */
export function buildSignInRequest(
  entryId: string,
  phone: string,
  form: VisitorForm,
  signaturePng: string | null,
): { ok: true; value: VisitorSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const nameProblem = fullNameError(form.fullName, "the visitor's");
  if (nameProblem) errors.fullName = nameProblem;
  if (!signaturePng) errors.signature = "Ask the visitor to sign.";
  if (Object.keys(errors).length > 0 || !signaturePng) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      full_name: cleanFullName(form.fullName),
      company: form.company.trim() || null,
      purpose: form.purpose.trim() || null,
      items_received: form.itemsReceived.trim() || null,
      phone,
      signature: signaturePng,
      device_id: deviceId(),
    },
  };
}

export function signIn(request: VisitorSignInRequest): Promise<VisitorEntry> {
  return visitorsApi.signIn(request);
}
