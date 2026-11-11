// frontend/src/api/trucks.ts  (backend: api/routes/trucks.py)
// Truck-only calls. Listing, sign-out and signatures are shared: see api/entries.ts.

import { request } from "./client";
import * as entriesApi from "./entries";
import type {
  TruckEnterRequest,
  TruckEntry,
  TruckLeaveQueueRequest,
  TruckLookup,
  TruckSignInRequest,
} from "./schemas";

export function lookupTruck(plate: string): Promise<TruckLookup | null> {
  return request<TruckLookup | null>("/trucks/lookup", { query: { plate } });
}

export function signIn(body: TruckSignInRequest): Promise<TruckEntry> {
  return entriesApi.signIn<TruckEntry>("trucks", body);
}

/** Let a queued truck in; the driver signs. */
export function enter(entryId: string, body: TruckEnterRequest): Promise<TruckEntry> {
  return request<TruckEntry>(`/trucks/entries/${entryId}/enter`, { method: "POST", body });
}

/** A queued truck gave up and left. */
export function leaveQueue(entryId: string, body: TruckLeaveQueueRequest): Promise<TruckEntry> {
  return request<TruckEntry>(`/trucks/entries/${entryId}/leave-queue`, { method: "POST", body });
}
