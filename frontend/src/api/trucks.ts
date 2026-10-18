// frontend/src/api/trucks.ts  (backend: api/routes/trucks.py)

import { request, requestAuthedBlob } from "./client";
import type {
  TruckEntry,
  TruckEntryQuery,
  TruckLookup,
  TruckSignInRequest,
  TruckSignOutRequest,
} from "./schemas";

export function lookupTruck(plate: string): Promise<TruckLookup | null> {
  return request<TruckLookup | null>("/trucks/lookup", { query: { plate } });
}

/** 201 = created, 200 = replay of the same id. Both return the stored entry. */
export function signIn(body: TruckSignInRequest): Promise<TruckEntry> {
  return request<TruckEntry>("/trucks/entries", { method: "POST", body });
}

export function signOut(entryId: string, body: TruckSignOutRequest = {}): Promise<TruckEntry> {
  return request<TruckEntry>(`/trucks/entries/${entryId}/sign-out`, { method: "POST", body });
}

export function listEntries(query: TruckEntryQuery, signal?: AbortSignal): Promise<TruckEntry[]> {
  return request<TruckEntry[]>("/trucks/entries", {
    signal,
    query: {
      open: query.open ? "true" : undefined,
      plate: query.plate,
      facility_code: query.facility_code,
      date_from: query.date_from,
      date_to: query.date_to,
      limit: query.limit,
      offset: query.offset,
    },
  });
}

export function getSignature(entryId: string): Promise<Blob> {
  return requestAuthedBlob(`/trucks/entries/${entryId}/signature`);
}
