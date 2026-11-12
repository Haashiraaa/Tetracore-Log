// frontend/src/api/admin.ts  (backend: api/routes/admin.py)

import { request } from "./client";
import type {
  CreateFacilityRequest,
  CreateOfficerRequest,
  CreateOfficerResponse,
  Facility,
  OfficerSummary,
  ResetPinResponse,
  StateOption,
} from "./schemas";

export function listFacilities(signal?: AbortSignal): Promise<Facility[]> {
  return request<Facility[]>("/admin/facilities", { signal });
}

export function listStates(signal?: AbortSignal): Promise<StateOption[]> {
  return request<StateOption[]>("/admin/states", { signal });
}

export function createFacility(body: CreateFacilityRequest): Promise<Facility> {
  return request<Facility>("/admin/facilities", { method: "POST", body });
}

export function listOfficers(facilityCode?: string, signal?: AbortSignal): Promise<OfficerSummary[]> {
  return request<OfficerSummary[]>("/admin/officers", {
    signal,
    query: { facility_code: facilityCode },
  });
}

export function createOfficer(body: CreateOfficerRequest): Promise<CreateOfficerResponse> {
  return request<CreateOfficerResponse>("/admin/officers", { method: "POST", body });
}

export function resetPin(officerId: string): Promise<ResetPinResponse> {
  return request<ResetPinResponse>(`/admin/officers/${officerId}/reset-pin`, { method: "POST" });
}

export function disableOfficer(officerId: string): Promise<void> {
  return request<void>(`/admin/officers/${officerId}/disable`, { method: "POST" });
}

export function enableOfficer(officerId: string): Promise<void> {
  return request<void>(`/admin/officers/${officerId}/enable`, { method: "POST" });
}

export function revokeSessions(officerId: string): Promise<void> {
  return request<void>(`/admin/officers/${officerId}/revoke-sessions`, { method: "POST" });
}

/** How many gates a facility has. Refused while someone is on duty at a gate that would go. */
export function setGates(facilityCode: string, gateCount: number): Promise<Facility> {
  return request<Facility>(`/admin/facilities/${encodeURIComponent(facilityCode)}/gates`, {
    method: "PUT",
    body: { gate_count: gateCount },
  });
}

/** Take an officer off duty (they forgot to). */
export function endDuty(officerId: string): Promise<void> {
  return request<void>(`/admin/officers/${officerId}/end-duty`, { method: "POST" });
}
