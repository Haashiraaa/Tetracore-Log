// frontend/src/services/entryService.ts
// Rules every log (trucks, visitors, staff) shares. Mirrors backend/src/api/entry_service.py.
// A log's own service (truckService, visitorService, staffService) adds what is specific to it.

import * as entriesApi from "@/api/entries";
import type { AnyEntry, EntryFilters, StaffEntry, TruckEntry, VisitorEntry } from "@/api/schemas";
import { EXPORT_ROW_CAP, PAGE_SIZE, TODAY_MAX_ROWS } from "@/config/env";
import { toCsv } from "@/lib/csv";
import { formatDateTime, lagosHour, startOfDayIso, todayDate } from "@/lib/dates";
import type { LogKind } from "@/models";
import { STATUS_LABEL } from "./truckService";
import { itemsLabel } from "./visitorService";

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

// ---- telling entries apart ----

export function isTruck(e: AnyEntry): e is TruckEntry {
  return "plate_number" in e;
}

export function isVisitor(e: AnyEntry): e is VisitorEntry {
  return "purpose" in e;
}

export function isStaff(e: AnyEntry): e is StaffEntry {
  return "capacity" in e;
}

/** How any entry is shown in a list: a plate (trucks only), a name, and one line under it. */
export interface EntryFace {
  plate: string | null;
  name: string;
  sub: string | null;
  phone: string | null;
}

export function faceOf(e: AnyEntry): EntryFace {
  if (isTruck(e)) {
    return { plate: e.plate_number, name: e.driver_name, sub: e.company, phone: e.driver_phone };
  }
  if (isVisitor(e)) {
    const sub = [e.company, e.purpose].filter(Boolean).join(", ");
    return { plate: null, name: e.full_name, sub: sub || null, phone: e.phone };
  }
  return { plate: null, name: e.full_name, sub: e.capacity, phone: e.phone };
}

/** The words a search box matches against. */
export function searchText(e: AnyEntry): string {
  const face = faceOf(e);
  return [face.plate, face.name, face.sub, face.phone].filter(Boolean).join(" ").toUpperCase();
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

export function signatureError(png: string | null): string | null {
  return png ? null : "Ask them to sign before they leave.";
}

export function signOut(
  kind: LogKind,
  entryId: string,
  opts: { signature: string | null; scm?: string | null },
): Promise<AnyEntry> {
  // signature null (visitors and staff only): the server reuses the one from sign-in
  return entriesApi.signOut<AnyEntry>(kind, entryId, {
    ...(opts.signature ? { signature: opts.signature } : {}),
    ...(kind === "trucks" && opts.scm ? { scm_purchased: opts.scm } : {}),
  });
}

// ---- reading ----

export async function fetchPage(
  kind: LogKind,
  filters: EntryFilters,
  page: number,
  signal?: AbortSignal,
): Promise<{ rows: AnyEntry[]; hasMore: boolean }> {
  // Ask for one extra row to learn whether a next page exists without a count query.
  const rows = await entriesApi.listEntries<AnyEntry>(
    kind,
    { ...filters, limit: PAGE_SIZE + 1, offset: page * PAGE_SIZE },
    signal,
  );
  return { rows: rows.slice(0, PAGE_SIZE), hasMore: rows.length > PAGE_SIZE };
}

export const INSIDE_MAX_ROWS = 200;

export function fetchInside(kind: LogKind, signal?: AbortSignal): Promise<AnyEntry[]> {
  return entriesApi.listEntries<AnyEntry>(kind, { open: true, limit: INSIDE_MAX_ROWS }, signal);
}

export function fetchRecent(kind: LogKind, count: number, signal?: AbortSignal): Promise<AnyEntry[]> {
  return entriesApi.listEntries<AnyEntry>(kind, { limit: count }, signal);
}

/** Everything signed in since midnight in Lagos, newest first, up to TODAY_MAX_ROWS. */
export function fetchToday(kind: LogKind, signal?: AbortSignal): Promise<AnyEntry[]> {
  return entriesApi.listEntries<AnyEntry>(
    kind,
    { date_from: startOfDayIso(todayDate()), limit: TODAY_MAX_ROWS },
    signal,
  );
}

/** 24 counts: how many of these entries signed in during each Lagos hour. */
export function signInsByHour(entries: AnyEntry[]): number[] {
  const hours = new Array<number>(24).fill(0);
  for (const e of entries) hours[lagosHour(e.signed_in_at)] += 1;
  return hours;
}

/** How many of these trucks signed out and went today, whichever day they arrived. */
export function departedToday(entries: AnyEntry[]): number {
  const midnight = startOfDayIso(todayDate());
  return entries.filter(
    (e) => isTruck(e) && e.status === "departed" && e.signed_out_at !== null && e.signed_out_at >= midnight,
  ).length;
}

export async function fetchAll(
  kind: LogKind,
  filters: EntryFilters,
): Promise<{ rows: AnyEntry[]; capped: boolean }> {
  const rows: AnyEntry[] = [];
  const step = 200;
  for (let offset = 0; offset < EXPORT_ROW_CAP; offset += step) {
    const batch = await entriesApi.listEntries<AnyEntry>(kind, { ...filters, limit: step, offset });
    rows.push(...batch);
    if (batch.length < step) return { rows, capped: false };
  }
  return { rows: rows.slice(0, EXPORT_ROW_CAP), capped: true };
}

// ---- export ----

type Column = [header: string, cell: (e: AnyEntry) => string];

const OWN_COLUMNS: Record<LogKind, Column[]> = {
  trucks: [
    ["Plate", (e) => (isTruck(e) ? e.plate_number : "")],
    ["Full name", (e) => (isTruck(e) ? e.driver_name : "")],
    ["Phone", (e) => (isTruck(e) ? (e.driver_phone ?? "") : "")],
    ["Company", (e) => (isTruck(e) ? (e.company ?? "") : "")],
    ["SCM purchased", (e) => (isTruck(e) ? (e.scm_purchased ?? "") : "")],
    ["Status", (e) => (isTruck(e) ? STATUS_LABEL[e.status] : "")],
    ["Let in at", (e) => (isTruck(e) && e.entered_at ? formatDateTime(e.entered_at, true) : "")],
    ["Why it left the queue", (e) => (isTruck(e) ? (e.left_queue_reason ?? "") : "")],
  ],
  visitors: [
    ["Full name", (e) => (isVisitor(e) ? e.full_name : "")],
    ["Company name", (e) => (isVisitor(e) ? (e.company ?? "") : "")],
    ["Purpose of visit", (e) => (isVisitor(e) ? (e.purpose ?? "") : "")],
    ["Items brought", (e) => (isVisitor(e) ? itemsLabel(e) : "")],
    ["Phone number", (e) => (isVisitor(e) ? (e.phone ?? "") : "")],
  ],
  staff: [
    ["Full name", (e) => (isStaff(e) ? e.full_name : "")],
    ["Capacity", (e) => (isStaff(e) ? (e.capacity ?? "") : "")],
    ["Phone number", (e) => (isStaff(e) ? (e.phone ?? "") : "")],
  ],
};

/** "yes", "no", or "yes (reused)" when nobody drew it this time. */
function signatureCell(has: boolean, reused: boolean): string {
  if (!has) return "no";
  return reused ? "yes (reused)" : "yes";
}

const SHARED_COLUMNS: Column[] = [
  ["Time in", (e) => formatDateTime(e.signed_in_at, true)],
  ["Signed in", (e) => signatureCell(e.has_signature, e.signature_in_reused)],
  ["Time out", (e) => (e.signed_out_at ? formatDateTime(e.signed_out_at, true) : "")],
  ["Signed out", (e) => signatureCell(e.has_signature_out, e.signature_out_reused)],
  ["Signed in by", (e) => e.signed_in_by_name],
  ["Signed out by", (e) => e.signed_out_by_name ?? ""],
  ["Gate in", (e) => (e.gate_in ? String(e.gate_in) : "")],
  ["Gate out", (e) => (e.gate_out ? String(e.gate_out) : "")],
];

export function entriesToCsv(kind: LogKind, entries: AnyEntry[], includeFacility: boolean): string {
  const facility: Column[] = includeFacility ? [["Facility", (e) => e.facility_code]] : [];
  const columns = [...facility, ...OWN_COLUMNS[kind], ...SHARED_COLUMNS];
  return toCsv([columns.map(([header]) => header), ...entries.map((e) => columns.map(([, cell]) => cell(e)))]);
}
