// frontend/src/services/visitorService.ts
// Visitor rules. Mirrors backend/src/api/visitor_service.py.

import type { VisitorEntry, VisitorItem, VisitorLookup, VisitorSignInRequest } from "@/api/schemas";
import * as visitorsApi from "@/api/visitors";
import { cleanFullName, fullNameError } from "@/lib/people";
import { deviceId } from "@/lib/ids";
import type { FieldErrors } from "./entryService";

/** Quick picks for "purpose of visit". The field stays free text: these only fill it in. */
export const PURPOSE_PICKS = ["Delivery", "Meeting", "Maintenance"] as const;

/** A row on the form while it is being typed. `key` only keeps React's list stable. */
export interface ItemRow {
  key: string;
  name: string;
  /** Typed text; checked to be a whole number before it is sent. */
  quantity: string;
  unit: string;
}

export const MAX_ITEM_QUANTITY = 100_000;

/** "2 boxes", "10": how one item's amount reads. */
export function quantityLabel(i: Pick<VisitorItem, "quantity" | "unit">): string {
  return i.unit ? `${i.quantity} ${i.unit}` : String(i.quantity);
}

export interface VisitorForm {
  fullName: string;
  company: string;
  purpose: string;
  items: ItemRow[];
}

export const BLANK_VISITOR: VisitorForm = { fullName: "", company: "", purpose: "", items: [] };

/** What a visit's items read like in a table cell or a CSV: "Oil filters (2 boxes); Gloves (10)".
 *  Lines from before items were a list keep their old free text. */
export function itemsLabel(e: Pick<VisitorEntry, "items" | "items_received">): string {
  if (e.items.length > 0) return e.items.map((i) => `${i.name} (${quantityLabel(i)})`).join("; ");
  return e.items_received ?? "";
}

/** The rows that carry something. A row left completely empty is dropped; a half-filled one is an error. */
function cleanItems(rows: ItemRow[]): { items: VisitorItem[] } | { error: string } {
  const items: VisitorItem[] = [];
  for (const row of rows) {
    const name = row.name.trim();
    const quantity = row.quantity.trim();
    const unit = row.unit.trim();
    if (!name && !quantity && !unit) continue;
    if (!name || !quantity) return { error: "Give each item a name and a quantity, or remove it." };
    const n = /^\d+$/.test(quantity) ? Number(quantity) : 0;
    if (n < 1 || n > MAX_ITEM_QUANTITY) {
      return { error: "Quantity must be a whole number, 1 or more. Put words like boxes in Unit." };
    }
    items.push({ name, quantity: n, unit: unit || null });
  }
  return { items };
}

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

type Field = "fullName" | "items" | "signature";

/** `phone` is already canonical (it came from the lookup step). `signatureOnFile`: the server
 *  already has this person's signature, so none is needed (null `signaturePng` reuses it). */
export function buildSignInRequest(
  entryId: string,
  phone: string,
  form: VisitorForm,
  signaturePng: string | null,
  signatureOnFile = false,
): { ok: true; value: VisitorSignInRequest } | { ok: false; errors: FieldErrors<Field> } {
  const errors: FieldErrors<Field> = {};
  const nameProblem = fullNameError(form.fullName, "the visitor's");
  if (nameProblem) errors.fullName = nameProblem;
  const cleaned = cleanItems(form.items);
  if ("error" in cleaned) errors.items = cleaned.error;
  if (!signaturePng && !signatureOnFile) errors.signature = "Ask the visitor to sign.";
  if (Object.keys(errors).length > 0 || "error" in cleaned) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      full_name: cleanFullName(form.fullName),
      company: form.company.trim() || null,
      purpose: form.purpose.trim() || null,
      items: cleaned.items,
      phone,
      signature: signaturePng,
      device_id: deviceId(),
    },
  };
}

export function signIn(request: VisitorSignInRequest): Promise<VisitorEntry> {
  return visitorsApi.signIn(request);
}
