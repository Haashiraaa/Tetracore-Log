// frontend/src/api/entries.ts  (backend: api/routes/_entries.py and db/queries/_entries.py)
// The calls every log shares. `kind` is the API path segment: /api/<kind>/entries.

import type { LogKind } from "@/models";
import { request, requestAuthedBlob } from "./client";
import type { AnyEntry, EntryQuery, EntrySignOutRequest, SignatureSide } from "./schemas";

/** 201 = created, 200 = replay of the same id. Both return the stored entry. */
export function signIn<T extends AnyEntry>(kind: LogKind, body: object): Promise<T> {
  return request<T>(`/${kind}/entries`, { method: "POST", body });
}

export function signOut<T extends AnyEntry>(
  kind: LogKind,
  entryId: string,
  body: EntrySignOutRequest & { scm_purchased?: string | null } = {},
): Promise<T> {
  return request<T>(`/${kind}/entries/${entryId}/sign-out`, { method: "POST", body });
}

export function listEntries<T extends AnyEntry>(
  kind: LogKind,
  query: EntryQuery,
  signal?: AbortSignal,
): Promise<T[]> {
  return request<T[]>(`/${kind}/entries`, {
    signal,
    query: {
      open: query.open ? "true" : undefined,
      plate: kind === "trucks" ? query.plate : undefined,
      facility_code: query.facility_code,
      date_from: query.date_from,
      date_to: query.date_to,
      limit: query.limit,
      offset: query.offset,
    },
  });
}

export function getSignature(kind: LogKind, entryId: string, side: SignatureSide = "in"): Promise<Blob> {
  return requestAuthedBlob(`/${kind}/entries/${entryId}/signature`, { query: { side } });
}
