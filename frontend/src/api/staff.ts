// frontend/src/api/staff.ts  (backend: api/routes/staff.py)
// Staff-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import * as entriesApi from "./entries";
import type { StaffEntry, StaffLookup, StaffSignInRequest } from "./schemas";

export function signIn(body: StaffSignInRequest): Promise<StaffEntry> {
  return entriesApi.signIn<StaffEntry>("staff", body);
}

export function search(typed: string): Promise<StaffLookup[]> {
  return entriesApi.searchByPhone<StaffLookup>("staff", typed);
}

export function lookup(phone: string): Promise<StaffLookup | null> {
  return entriesApi.lookupByPhone<StaffLookup>("staff", phone);
}
