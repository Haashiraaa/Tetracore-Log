// frontend/src/api/superAdmin.ts  (backend: api/routes/super_admin.py)

import { request } from "./client";
import type { CreateAdminRequest, OfficerSummary, TempPinResponse } from "./schemas";

const BASE = "/super-admin/admins";

export function listAdmins(signal?: AbortSignal): Promise<OfficerSummary[]> {
  return request<OfficerSummary[]>(BASE, { signal });
}

export function createAdmin(body: CreateAdminRequest): Promise<TempPinResponse> {
  return request<TempPinResponse>(BASE, { method: "POST", body });
}

export function grantAdmin(officerId: string): Promise<OfficerSummary> {
  return request<OfficerSummary>(`${BASE}/${officerId}/grant`, { method: "POST" });
}

export function revokeAdmin(officerId: string): Promise<OfficerSummary> {
  return request<OfficerSummary>(`${BASE}/${officerId}/revoke`, { method: "POST" });
}

export function disableAdmin(officerId: string): Promise<OfficerSummary> {
  return request<OfficerSummary>(`${BASE}/${officerId}/disable`, { method: "POST" });
}

export function enableAdmin(officerId: string): Promise<OfficerSummary> {
  return request<OfficerSummary>(`${BASE}/${officerId}/enable`, { method: "POST" });
}

export function resetAdminPin(officerId: string): Promise<TempPinResponse> {
  return request<TempPinResponse>(`${BASE}/${officerId}/reset-pin`, { method: "POST" });
}
