// frontend/src/api/waybill.ts  (backend: api/routes/waybill.py)
// Waybill-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import * as entriesApi from "./entries";
import type { WaybillEntry, WaybillLookup, WaybillSignInRequest } from "./schemas";

export function signIn(body: WaybillSignInRequest): Promise<WaybillEntry> {
  return entriesApi.signIn<WaybillEntry>("waybill", body);
}

export function search(typed: string): Promise<WaybillLookup[]> {
  return entriesApi.searchByPhone<WaybillLookup>("waybill", typed);
}

export function lookup(phone: string): Promise<WaybillLookup | null> {
  return entriesApi.lookupByPhone<WaybillLookup>("waybill", phone);
}
