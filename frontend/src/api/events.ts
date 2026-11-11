// frontend/src/api/events.ts  (backend: api/routes/events.py)

import { request } from "./client";
import type { EventItem, EventsQuery, EventsSummary, PushSubscriptionJson } from "./schemas";

export function listEvents(query: EventsQuery, signal?: AbortSignal): Promise<EventItem[]> {
  return request<EventItem[]>("/admin/events", { signal, query: { ...query } });
}

export function summary(signal?: AbortSignal): Promise<EventsSummary> {
  return request<EventsSummary>("/admin/events/summary", { signal });
}

/** Everything up to `upToId` (or everything so far) counts as read. */
export function markRead(upToId?: number): Promise<EventsSummary> {
  return request<EventsSummary>("/admin/events/read", {
    method: "POST",
    body: upToId === undefined ? {} : { up_to_id: upToId },
  });
}

/** public_key is null when the server has no push keys. */
export function pushConfig(signal?: AbortSignal): Promise<{ public_key: string | null }> {
  return request<{ public_key: string | null }>("/admin/push/config", { signal });
}

export function pushSubscribe(sub: PushSubscriptionJson): Promise<void> {
  return request<void>("/admin/push/subscribe", { method: "POST", body: sub });
}

export function pushUnsubscribe(endpoint: string): Promise<void> {
  return request<void>("/admin/push/unsubscribe", { method: "POST", body: { endpoint } });
}
