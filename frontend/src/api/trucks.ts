// frontend/src/api/trucks.ts  (backend: api/routes/trucks.py)
// Truck-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import { request } from "./client";
import * as entriesApi from "./entries";
import type { TruckEntry, TruckLookup, TruckSignInRequest } from "./schemas";

export function lookupTruck(plate: string): Promise<TruckLookup | null> {
  return request<TruckLookup | null>("/trucks/lookup", { query: { plate } });
}

export function signIn(body: TruckSignInRequest): Promise<TruckEntry> {
  return entriesApi.signIn<TruckEntry>("trucks", body);
}
