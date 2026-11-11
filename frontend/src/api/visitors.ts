// frontend/src/api/visitors.ts  (backend: api/routes/visitors.py)
// Visitor-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import * as entriesApi from "./entries";
import type { VisitorEntry, VisitorLookup, VisitorSignInRequest } from "./schemas";

export function signIn(body: VisitorSignInRequest): Promise<VisitorEntry> {
  return entriesApi.signIn<VisitorEntry>("visitors", body);
}

export function search(typed: string): Promise<VisitorLookup[]> {
  return entriesApi.searchByPhone<VisitorLookup>("visitors", typed);
}

export function lookup(phone: string): Promise<VisitorLookup | null> {
  return entriesApi.lookupByPhone<VisitorLookup>("visitors", phone);
}
