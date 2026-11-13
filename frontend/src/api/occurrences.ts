// frontend/src/api/occurrences.ts  (backend: api/routes/occurrences.py)
// The Events log: an officer's own notes. Not one of the sign-in logs (no sign-out).

import { request, requestAuthedBlob } from "./client";
import type { OccurrenceCreateRequest, OccurrenceEntry } from "./schemas";

/** 201 = created, 200 = replay of the same id. Both return the stored note. */
export function create(body: OccurrenceCreateRequest): Promise<OccurrenceEntry> {
  return request<OccurrenceEntry>("/occurrences", { method: "POST", body });
}

export function list(
  query: { facility_code?: string; limit?: number; offset?: number },
  signal?: AbortSignal,
): Promise<OccurrenceEntry[]> {
  return request<OccurrenceEntry[]>("/occurrences", { signal, query });
}

/** Does this officer have a signature from going on duty that a note can use? */
export function signatureOnFile(): Promise<{ has_signature: boolean }> {
  return request<{ has_signature: boolean }>("/occurrences/signature-on-file");
}

export function getSignature(noteId: string): Promise<Blob> {
  return requestAuthedBlob(`/occurrences/${noteId}/signature`);
}
