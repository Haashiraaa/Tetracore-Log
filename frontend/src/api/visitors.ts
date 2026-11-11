// frontend/src/api/visitors.ts  (backend: api/routes/visitors.py)
// Visitor-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import * as entriesApi from "./entries";
import type { VisitorEntry, VisitorSignInRequest } from "./schemas";

export function signIn(body: VisitorSignInRequest): Promise<VisitorEntry> {
  return entriesApi.signIn<VisitorEntry>("visitors", body);
}
