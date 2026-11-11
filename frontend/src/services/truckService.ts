// frontend/src/services/truckService.ts
// Truck rules. Mirrors backend/src/api/truck_service.py (and its layering):
// api/trucks.ts only talks HTTP; decisions and validation live here.

import * as trucksApi from "@/api/trucks";
import type {
  TruckEntry,
  TruckEntryFilters,
  TruckLookup,
  TruckSignInRequest,
} from "@/api/schemas";
import { EXPORT_ROW_CAP, PAGE_SIZE, REQUIRE_SIGNATURE } from "@/config/env";
import { toCsv } from "@/lib/csv";
import { formatDateTime } from "@/lib/dates";
import { deviceId } from "@/lib/ids";
import { isValidPlate, normalizePlate } from "@/lib/plate";

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

// ---- lookup ----

export type LookupResult =
  | { kind: "new"; plate: string }
  | { kind: "returning"; truck: TruckLookup }
  | { kind: "inside"; truck: TruckLookup };

export function validatePlate(raw: string): { plate: string } | { error: string } {
  const plate = normalizePlate(raw);
  if (!isValidPlate(plate)) return { error: "Enter a plate of 2 to 20 letters or digits." };
  return { plate };
}

export async function lookup(plate: string): Promise<LookupResult> {
  const truck = await trucksApi.lookupTruck(plate);
  if (truck === null) return { kind: "new", plate };
  return truck.open_entry_id ? { kind: "inside", truck } : { kind: "returning", truck };
}

// ---- sign-in ----

export interface SignInForm {
  plate: string;
  driverName: string;
  driverPhone: string;
  company: string;
}

type SignInField = "driverName" | "signature";

export function buildSignInRequest(
  entryId: string,
  form: SignInForm,
  signaturePng: string | null,
): { ok: true; value: TruckSignInRequest } | { ok: false; errors: FieldErrors<SignInField> } {
  const errors: FieldErrors<SignInField> = {};
  const driverName = form.driverName.trim();
  if (driverName.length < 2) errors.driverName = "Enter the driver's full name.";
  if (REQUIRE_SIGNATURE && !signaturePng) errors.signature = "Ask the driver to sign.";
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: {
      id: entryId,
      plate_number: normalizePlate(form.plate),
      driver_name: driverName,
      driver_phone: form.driverPhone.trim() || null,
      company: form.company.trim() || null,
      signature: signaturePng,
      device_id: deviceId(),
      // signed_in_at is left out on purpose: the server clock is the truth while online.
    },
  };
}

export function signIn(request: TruckSignInRequest): Promise<TruckEntry> {
  return trucksApi.signIn(request);
}

// ---- sign-out ----

/** SCM of gas bought, as the decimal STRING the API expects ("12.50"). Blank = unknown. */
export function parseScm(text: string): { value: string | null } | { error: string } {
  const cleaned = text.trim().replace(",", ".");
  if (cleaned === "") return { value: null };
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(cleaned)) {
    return { error: "Enter a number such as 12 or 12.50." };
  }
  return { value: cleaned };
}

export function signOut(entryId: string, scm: string | null): Promise<TruckEntry> {
  return trucksApi.signOut(entryId, scm === null ? {} : { scm_purchased: scm });
}

// ---- reading ----

export async function fetchPage(
  filters: TruckEntryFilters,
  page: number,
  signal?: AbortSignal,
): Promise<{ rows: TruckEntry[]; hasMore: boolean }> {
  // Ask for one extra row to learn whether a next page exists without a count query.
  const rows = await trucksApi.listEntries(
    { ...filters, limit: PAGE_SIZE + 1, offset: page * PAGE_SIZE },
    signal,
  );
  return { rows: rows.slice(0, PAGE_SIZE), hasMore: rows.length > PAGE_SIZE };
}

export async function fetchInside(signal?: AbortSignal): Promise<TruckEntry[]> {
  return trucksApi.listEntries({ open: true, limit: 200 }, signal);
}

export async function fetchAll(
  filters: TruckEntryFilters,
): Promise<{ rows: TruckEntry[]; capped: boolean }> {
  const rows: TruckEntry[] = [];
  const step = 200;
  for (let offset = 0; offset < EXPORT_ROW_CAP; offset += step) {
    const batch = await trucksApi.listEntries({ ...filters, limit: step, offset });
    rows.push(...batch);
    if (batch.length < step) return { rows, capped: false };
  }
  return { rows: rows.slice(0, EXPORT_ROW_CAP), capped: true };
}

export function entriesToCsv(entries: TruckEntry[], includeFacility: boolean): string {
  const header = [
    ...(includeFacility ? ["Facility"] : []),
    "Plate",
    "Driver",
    "Phone",
    "Company",
    "Signed in",
    "Signed out",
    "SCM purchased",
    "Signed in by",
    "Signed out by",
  ];
  const body = entries.map((e) => [
    ...(includeFacility ? [e.facility_code] : []),
    e.plate_number,
    e.driver_name,
    e.driver_phone ?? "",
    e.company ?? "",
    formatDateTime(e.signed_in_at, true),
    e.signed_out_at ? formatDateTime(e.signed_out_at, true) : "",
    e.scm_purchased ?? "",
    e.signed_in_by_name,
    e.signed_out_by_name ?? "",
  ]);
  return toCsv([header, ...body]);
}
