// frontend/src/api/duty.ts  (backend: api/routes/duty.py)
// The officer's own duty log. Listing and signatures are readable by every account.

import { request, requestAuthedBlob } from "./client";
import type {
  DutyChangeGateRequest,
  DutyEntry,
  DutyOffRequest,
  DutyOnRequest,
  DutyQuery,
  DutyStatus,
  SignatureSide,
} from "./schemas";

/** My facility's gates and where I am on duty (current = null when off duty). */
export function myStatus(signal?: AbortSignal): Promise<DutyStatus> {
  return request<DutyStatus>("/duty", { signal });
}

/** 201 = created, 200 = replay of the same id. */
export function goOn(body: DutyOnRequest): Promise<DutyEntry> {
  return request<DutyEntry>("/duty/on", { method: "POST", body });
}

export function changeGate(body: DutyChangeGateRequest): Promise<DutyEntry> {
  return request<DutyEntry>("/duty/change-gate", { method: "POST", body });
}

export function goOff(body: DutyOffRequest): Promise<DutyStatus> {
  return request<DutyStatus>("/duty/off", { method: "POST", body });
}

/** Who is on duty right now, and at which gate. */
export function onDutyNow(signal?: AbortSignal): Promise<DutyEntry[]> {
  return request<DutyEntry[]>("/duty/now", { signal });
}

export function listEntries(query: DutyQuery, signal?: AbortSignal): Promise<DutyEntry[]> {
  return request<DutyEntry[]>("/duty/entries", {
    signal,
    query: {
      open: query.open ? "true" : undefined,
      facility_code: query.facility_code,
      date_from: query.date_from,
      date_to: query.date_to,
      limit: query.limit,
      offset: query.offset,
    },
  });
}

export function getSignature(entryId: string, side: SignatureSide = "in"): Promise<Blob> {
  return requestAuthedBlob(`/duty/entries/${entryId}/signature`, { query: { side } });
}
