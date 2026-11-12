// frontend/src/services/dutyService.ts
// Duty rules. Mirrors backend/src/api/duty_service.py: an officer logs THEMSELVES, from their
// own login. api/duty.ts only talks HTTP; decisions and validation live here.

import * as dutyApi from "@/api/duty";
import type { DutyEntry, DutyQuery, DutyStatus } from "@/api/schemas";
import { PAGE_SIZE } from "@/config/env";
import { toCsv } from "@/lib/csv";
import { formatDateTime } from "@/lib/dates";
import { deviceId, uuid } from "@/lib/ids";

export function status(signal?: AbortSignal): Promise<DutyStatus> {
  return dutyApi.myStatus(signal);
}

/** The gates to choose from: 1..gate_count. */
export function gatesOf(count: number): number[] {
  return Array.from({ length: count }, (_, i) => i + 1);
}

export function gateLabel(gate: number | null | undefined): string {
  return gate ? `Gate ${gate}` : "";
}

/** `signaturePng` is optional: the officer chooses whether to sign. `id` is generated once per
 *  form open and reused on retry, so a lost reply never puts them on duty twice. */
export function goOn(id: string, gate: number, signaturePng: string | null): Promise<DutyEntry> {
  return dutyApi.goOn({ id, gate, signature: signaturePng, device_id: deviceId() });
}

export function changeGate(gate: number): Promise<DutyEntry> {
  return dutyApi.changeGate({ id: uuid(), gate });
}

export function goOff(signaturePng: string | null): Promise<DutyStatus> {
  return dutyApi.goOff({ signature: signaturePng });
}

export function onDutyNow(signal?: AbortSignal): Promise<DutyEntry[]> {
  return dutyApi.onDutyNow(signal);
}

export async function fetchPage(
  filters: Omit<DutyQuery, "limit" | "offset">,
  page: number,
  signal?: AbortSignal,
): Promise<{ rows: DutyEntry[]; hasMore: boolean }> {
  const rows = await dutyApi.listEntries({ ...filters, limit: PAGE_SIZE + 1, offset: page * PAGE_SIZE }, signal);
  return { rows: rows.slice(0, PAGE_SIZE), hasMore: rows.length > PAGE_SIZE };
}

const ENDED: Record<NonNullable<DutyEntry["ended_how"]>, string> = {
  off: "Went off duty",
  moved: "Changed gate",
  admin: "Taken off by admin",
};

export function endedLabel(e: DutyEntry): string {
  return e.ended_how ? ENDED[e.ended_how] : "On duty";
}

export function dutyToCsv(entries: DutyEntry[], includeFacility: boolean): string {
  const header = [
    ...(includeFacility ? ["Facility"] : []),
    "Officer", "Officer code", "Gate", "On duty", "Off duty", "How it ended", "Signed on", "Signed off",
  ];
  const rows = entries.map((e) => [
    ...(includeFacility ? [e.facility_code] : []),
    e.officer_name,
    e.officer_code,
    String(e.gate),
    formatDateTime(e.on_duty_at, true),
    e.off_duty_at ? formatDateTime(e.off_duty_at, true) : "",
    e.ended_how ? ENDED[e.ended_how] : "",
    e.has_signature ? "yes" : "no",
    e.has_signature_out ? "yes" : "no",
  ]);
  return toCsv([header, ...rows]);
}
