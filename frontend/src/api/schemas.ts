// frontend/src/api/schemas.ts
// Request/response shapes. Mirrors backend/src/api/schemas.py.
// Decimals (scm_purchased) travel as STRINGS ("12.50"); never parse them for storage.

import type { Role } from "@/models";

// ---- auth ----

export interface OfficerProfile {
  id: string;
  officer_code: string;
  full_name: string;
  role: Role;
  is_admin: boolean;
  is_super_admin: boolean;
  sees_all_facilities: boolean;
  must_change_pin: boolean;
  facility_id: string | null;
  facility_code: string | null;
  facility_name: string | null;
}

export interface LoginRequest {
  facility_code: string | null;
  officer_code: string;
  pin: string;
  device_label?: string | null;
}

export interface LoginResponse {
  token_type: "bearer";
  access_token: string;
  access_expires_at: string;
  refresh_token: string;
  refresh_expires_at: string;
  officer: OfficerProfile;
}

export interface RefreshResponse {
  token_type: "bearer";
  access_token: string;
  access_expires_at: string;
  refresh_expires_at: string;
}

// ---- admin ----

export interface Facility {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface CreateFacilityRequest {
  code: string;
  name: string;
}

/** AdminOfficerOut and AdminSummary share this shape. */
export interface OfficerSummary extends OfficerProfile {
  is_active: boolean;
}

export interface CreateOfficerRequest {
  facility_code: string;
  full_name: string;
  role: Role;
}

export interface CreateOfficerResponse {
  officer: OfficerProfile;
  temp_pin: string;
}

export interface ResetPinResponse {
  officer_code: string;
  full_name: string;
  temp_pin: string;
}

// ---- super admin ----

export interface CreateAdminRequest {
  full_name: string;
  role: Role;
  facility_code?: string | null;
}

export interface TempPinResponse {
  officer: OfficerSummary;
  temp_pin: string;
}

// ---- trucks ----

export interface TruckLookup {
  truck_id: string;
  plate_number: string;
  driver_name: string;
  driver_phone: string | null;
  company: string | null;
  /** Set when the truck is currently inside. */
  open_entry_id: string | null;
}

export interface TruckSignInRequest {
  id: string; // generated here, once per form open; makes retries idempotent
  plate_number: string;
  driver_name: string;
  driver_phone?: string | null;
  company?: string | null;
  scm_purchased?: string | null;
  /** Omit in V1 (online): the server stamps its own clock, so phone drift cannot skew the log. */
  signed_in_at?: string | null;
  signature?: string | null; // PNG data URL
  device_id?: string | null;
}

export interface TruckSignOutRequest {
  signed_out_at?: string | null;
  scm_purchased?: string | null;
}

export interface TruckEntry {
  id: string;
  truck_id: string;
  facility_id: string;
  facility_code: string;
  plate_number: string;
  driver_name: string;
  driver_phone: string | null;
  company: string | null;
  scm_purchased: string | null;
  signed_in_at: string;
  signed_out_at: string | null;
  signed_in_by: string;
  signed_in_by_name: string;
  signed_out_by: string | null;
  signed_out_by_name: string | null;
  device_id: string | null;
  has_signature: boolean;
  created_at: string;
  updated_at: string;
}

export interface TruckEntryFilters {
  open?: boolean;
  plate?: string;
  facility_code?: string;
  date_from?: string; // ISO with offset
  date_to?: string; // exclusive
}

export interface TruckEntryQuery extends TruckEntryFilters {
  limit?: number;
  offset?: number;
}
