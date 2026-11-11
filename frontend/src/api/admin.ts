// frontend/src/api/admin.ts  (backend: api/routes/admin.py)

import { request } from "./client";
import type {
  CreateFacilityRequest,
  CreateOfficerRequest,
  CreateOfficerResponse,
  Facility,
  OfficerSummary,
  ResetPinResponse,
} from "./schemas";

export function listFacilities(signal?: AbortSignal): Promise<Facility[]> {
  return request<Facility[]>("/admin/facilities", { signal });
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
