// frontend/src/services/visitorService.ts
// Visitor rules. Mirrors backend/src/api/visitor_service.py.

import type { VisitorEntry, VisitorSignInRequest } from "@/api/schemas";
import * as visitorsApi from "@/api/visitors";
import { REQUIRE_SIGNATURE } from "@/config/env";
import { deviceId } from "@/lib/ids";
import type { FieldErrors } from "./entryService";

/** Quick picks for "purpose of visit". The field stays free text: these only fill it in. */
export const PURPOSE_PICKS = ["Delivery", "Meeting", "Maintenance"] as const;

export interface VisitorForm {
  fullName: string;
  company: string;
  purpose: string;
  itemsReceived: string;
  phone: string;
}

export const BLANK_VISITOR: VisitorForm = {
  fullName: "",
  company: "",
  purpose: "",
  itemsReceived: "",
  phone: "",
};

type Field = "fullName" | "signature";

export function buildSignInRequest(
  entryId: string,
  form: VisitorForm,
  signaturePng: string | null,
): { ok: true; value: VisitorSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const fullName = form.fullName.trim();
  if (fullName.length < 2) errors.fullName = "Enter the visitor's full name.";
  if (REQUIRE_SIGNATURE && !signaturePng) errors.signature = "Ask the visitor to sign.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      full_name: fullName,
      company: form.company.trim() || null,
      purpose: form.purpose.trim() || null,
      items_received: form.itemsReceived.trim() || null,
      phone: form.phone.trim() || null,
      signature: signaturePng,
      device_id: deviceId(),
    },
  };
}

export function signIn(request: VisitorSignInRequest): Promise<VisitorEntry> {
  return visitorsApi.signIn(request);
}
