// frontend/src/api/schemas.ts
// Request/response shapes. Mirrors backend/src/api/schemas/.
// Decimals (scm_purchased) travel as STRINGS ("12.50"); never parse them for storage.

import type { Role } from "@/models";

// ---- auth ----

export interface OfficerProfile {
  id: string;
  officer_code: string;
  full_name: string;
  role: Role;
  is_admin: boolean;
  sees_all_facilities: boolean;
  can_write_entries: boolean;
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
  /** Empty only for a facility made before codes were issued from a state. */
  state: string | null;
  name: string;
  is_active: boolean;
  /** Gates are numbered 1..gate_count. */
  gate_count: number;
}

/** No code: the server issues it from the state, e.g. CNG-LAG-01. */
export interface CreateFacilityRequest {
  state: string;
  name: string;
  gate_count: number;
}

export interface StateOption {
  name: string;
  abbrev: string;
}

/** AdminOfficerOut: an account plus whether it is enabled. */
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

// ---- every log (trucks, visitors, staff) ----

/** What every entry says. Mirrors EntryOut in backend/src/api/schemas/common.py. */
export interface EntryBase {
  id: string;
  facility_id: string;
  facility_code: string;
  signed_in_at: string;
  signed_out_at: string | null;
  signed_in_by: string;
  signed_in_by_name: string;
  signed_out_by: string | null;
  signed_out_by_name: string | null;
  device_id: string | null;
  /** The gate it came in through / went out through (the gate its officer stood at). */
  gate_in: number | null;
  gate_out: number | null;
  /** Signed on the way in. */
  has_signature: boolean;
  has_signature_out: boolean;
  created_at: string;
  updated_at: string;
}

export interface EntrySignInBase {
  id: string; // generated here, once per form open; makes retries idempotent
  /** Omit while online: the server stamps its own clock, so phone drift cannot skew the log. */
  signed_in_at?: string | null;
  signature: string; // PNG data URL. Always required: nobody is signed in without it
  device_id?: string | null;
}

export interface EntrySignOutRequest {
  signed_out_at?: string | null;
  signature: string; // PNG data URL. Always required: nobody is signed out without it
}

export type SignatureSide = "in" | "out";

export interface EntryFilters {
  open?: boolean;
  facility_code?: string;
  date_from?: string; // ISO with offset
  date_to?: string; // exclusive
  /** Trucks only. */
  plate?: string;
}

export interface EntryQuery extends EntryFilters {
  limit?: number;
  offset?: number;
}

// ---- trucks ----

/** Queued (registered, still outside) -> On site (let in) -> Departed (signed out).
 *  Or Queued -> Left queue (gave up before entering). */
export type TruckStatus = "queued" | "on_site" | "departed" | "left_queue";

export interface TruckLookup {
  truck_id: string;
  plate_number: string;
  driver_name: string;
  driver_phone: string | null;
  company: string | null;
  /** Set when the truck is in the middle of a visit: queued or on site. */
  open_entry_id: string | null;
  open_entry_status: "queued" | "on_site" | null;
}

/** Register a truck. Without `enter_now` it joins the queue and needs no signature;
 *  with it the truck is let in on the spot and the driver signs. */
export interface TruckSignInRequest extends Omit<EntrySignInBase, "signature"> {
  plate_number: string;
  driver_name: string;
  driver_phone?: string | null;
  company?: string | null;
  scm_purchased?: string | null;
  signature?: string | null;
  enter_now?: boolean;
}

/** Let a queued truck in: the driver signs. */
export interface TruckEnterRequest {
  entered_at?: string | null;
  signature: string;
}

/** A queued truck gave up. A reason is required. */
export interface TruckLeaveQueueRequest {
  reason: string;
  left_at?: string | null;
}

export interface TruckSignOutRequest extends EntrySignOutRequest {
  scm_purchased?: string | null;
}

export interface TruckEntry extends EntryBase {
  truck_id: string;
  plate_number: string;
  driver_name: string;
  driver_phone: string | null;
  company: string | null;
  scm_purchased: string | null;
  status: TruckStatus;
  /** When it was let in. signed_in_at is when it joined the queue. */
  entered_at: string | null;
  entered_by: string | null;
  queued_gate: number | null;
  left_queue_reason: string | null;
}

// ---- visitors ----

/** What the gate sees when a returning person's phone is typed (visitors and staff). */
export interface PersonLookup {
  full_name: string;
  phone: string;
  /** Set when they are inside right now. */
  open_entry_id: string | null;
}

export interface VisitorLookup extends PersonLookup {
  company: string | null;
}

export interface VisitorSignInRequest extends EntrySignInBase {
  full_name: string;
  company?: string | null;
  purpose?: string | null;
  items_received?: string | null;
  phone: string; // identifies a returning visitor
}

export interface VisitorEntry extends EntryBase {
  full_name: string;
  company: string | null;
  purpose: string | null;
  items_received: string | null;
  phone: string | null;
}

// ---- staff ----

export interface StaffLookup extends PersonLookup {
  capacity: string | null;
}

export interface StaffSignInRequest extends EntrySignInBase {
  full_name: string;
  capacity: string; // the capacity they work in, free text
  phone: string; // identifies a returning staff member
}

export interface StaffEntry extends EntryBase {
  full_name: string;
  capacity: string | null;
  phone: string | null;
}

export type AnyEntry = TruckEntry | VisitorEntry | StaffEntry;

// ---- duty (security officers log themselves) ----

/** One stretch of duty at one gate. A change of gate closes it and opens another that
 *  shares the shift_id. */
export interface DutyEntry {
  id: string;
  facility_id: string;
  facility_code: string;
  officer_id: string;
  officer_name: string;
  officer_code: string;
  gate: number;
  shift_id: string;
  on_duty_at: string;
  off_duty_at: string | null;
  started_how: "on" | "moved";
  ended_how: "off" | "moved" | "admin" | null;
  device_id: string | null;
  has_signature: boolean;
  has_signature_out: boolean;
}

export interface DutyStatus {
  facility_code: string;
  gate_count: number;
  /** null = off duty. */
  current: DutyEntry | null;
}

export interface DutyOnRequest {
  id: string;
  gate: number;
  signature?: string | null;
  device_id?: string | null;
}

export interface DutyChangeGateRequest {
  id: string;
  gate: number;
}

export interface DutyOffRequest {
  signature?: string | null;
}

export interface DutyQuery {
  open?: boolean;
  facility_code?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

// ---- notifications (the admin's feed) ----

export interface EventItem {
  id: number;
  created_at: string;
  kind: string;
  severity: "info" | "warning";
  summary: string;
  facility_code: string | null;
  /** Who did it. null for things nobody did, such as "left inside". */
  actor_name: string | null;
  entry_id: string | null;
}

export interface EventsSummary {
  latest_id: number;
  last_read_id: number;
  unread: number;
}

export type EventGroup = "gate" | "admin" | "warnings";

export interface EventsQuery {
  limit?: number;
  before_id?: number;
  after_id?: number;
  facility_code?: string;
  group?: EventGroup;
}

/** What the browser's PushSubscription.toJSON() gives. */
export interface PushSubscriptionJson {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}
