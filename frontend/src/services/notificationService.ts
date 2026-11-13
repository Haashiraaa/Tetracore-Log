// frontend/src/services/notificationService.ts
// What an event looks like, and the browser-push switch.
// Mirrors backend/src/api/event_service.py and backend/src/api/push.py.

import * as eventsApi from "@/api/events";
import type { EventGroup, EventItem } from "@/api/schemas";

// ---- how an event reads ----

export type BadgeTone = "grey" | "blue" | "amber" | "green" | "red" | "ink";

const KINDS: Record<string, { label: string; tone: BadgeTone }> = {
  truck_queued: { label: "Truck queued", tone: "blue" },
  truck_in: { label: "Truck in", tone: "green" },
  truck_out: { label: "Truck out", tone: "grey" },
  truck_left_queue: { label: "Left queue", tone: "amber" },
  visitor_in: { label: "Visitor in", tone: "green" },
  visitor_out: { label: "Visitor out", tone: "grey" },
  staff_in: { label: "Staff in", tone: "green" },
  staff_out: { label: "Staff out", tone: "grey" },
  waybill_in: { label: "Courier in", tone: "green" },
  waybill_out: { label: "Courier out", tone: "grey" },
  event_logged: { label: "Event", tone: "blue" },
  officer_on_duty: { label: "On duty", tone: "green" },
  officer_off_duty: { label: "Off duty", tone: "grey" },
  officer_gate_changed: { label: "Gate changed", tone: "grey" },
  facility_added: { label: "Facility", tone: "blue" },
  gates_changed: { label: "Gates", tone: "blue" },
  officer_added: { label: "Officer added", tone: "blue" },
  officer_pin_reset: { label: "PIN reset", tone: "blue" },
  officer_disabled: { label: "Disabled", tone: "blue" },
  officer_enabled: { label: "Enabled", tone: "blue" },
  sessions_revoked: { label: "Signed out", tone: "blue" },
  admin_granted: { label: "Admin added", tone: "blue" },
  admin_revoked: { label: "Admin removed", tone: "blue" },
  already_inside: { label: "Already inside", tone: "amber" },
  left_inside: { label: "Left inside", tone: "red" },
  queued_too_long: { label: "Queued too long", tone: "amber" },
  on_duty_too_long: { label: "On duty too long", tone: "amber" },
  gate_unmanned: { label: "Gate unmanned", tone: "red" },
};

export function eventLabel(e: EventItem): { label: string; tone: BadgeTone } {
  return KINDS[e.kind] ?? { label: e.kind, tone: "grey" };
}

export const GROUPS: { value: EventGroup | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "gate", label: "Gate" },
  { value: "admin", label: "Admin" },
  { value: "warnings", label: "Warnings" },
];

// ---- browser push ----

/** unsupported: this browser cannot. unconfigured: the server has no keys. denied: the person
 * blocked notifications for this site. off / on: what this browser is set to. */
export type PushState = "unsupported" | "unconfigured" | "denied" | "off" | "on";

export function pushSupported(): boolean {
  return (
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window &&
    window.isSecureContext
  );
}

function keyBytes(base64Url: string): Uint8Array {
  const padded = base64Url.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(base64Url.length / 4) * 4, "=");
  const raw = atob(padded);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

/** True when the browser's subscription was made with a different server key than the current one
 * (the keys were regenerated). The push service would reject every message sent to it. */
function keyMismatch(sub: PushSubscription, publicKey: string): boolean {
  const have = sub.options?.applicationServerKey;
  if (!have) return false;
  const a = new Uint8Array(have);
  const b = keyBytes(publicKey);
  return a.length !== b.length || a.some((v, i) => v !== b[i]);
}

async function currentSubscription(): Promise<PushSubscription | null> {
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function loadPushState(): Promise<{ state: PushState; publicKey: string | null }> {
  if (!pushSupported()) return { state: "unsupported", publicKey: null };
  const { public_key: publicKey } = await eventsApi.pushConfig();
  if (!publicKey) return { state: "unconfigured", publicKey: null };
  if (Notification.permission === "denied") return { state: "denied", publicKey };
  const sub = await currentSubscription();
  if (!sub) return { state: "off", publicKey };
  if (keyMismatch(sub, publicKey)) {
    // Made under an older server key: useless now. Drop it so the person turns it on afresh.
    await sub.unsubscribe().catch(() => undefined);
    await eventsApi.pushUnsubscribe(sub.endpoint).catch(() => undefined);
    return { state: "off", publicKey };
  }
  // Tell the server again: it may have dropped this browser (or this is another admin's login).
  await eventsApi.pushSubscribe(sub.toJSON() as never).catch(() => undefined);
  return { state: "on", publicKey };
}

/** Throws a plain Error with text fit to show when the person says no. */
export async function enablePush(publicKey: string): Promise<void> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Notifications are blocked for this site. Allow them in the browser settings, then try again.");
  }
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  let sub: PushSubscription;
  try {
    let existing = await reg.pushManager.getSubscription();
    if (existing && keyMismatch(existing, publicKey)) {
      await existing.unsubscribe();
      existing = null;
    }
    sub =
      existing ??
      (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(publicKey) }));
  } catch {
    throw new Error("Could not reach the browser's push service. Check the internet connection and try again.");
  }
  await eventsApi.pushSubscribe(sub.toJSON() as never);
}

export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  await eventsApi.pushUnsubscribe(sub.endpoint);
  await sub.unsubscribe();
}

/** Asks the server to send this admin a test notification. Returns text to show. */
export async function sendTestPush(): Promise<{ ok: boolean; message: string }> {
  const r = await eventsApi.pushTest();
  if (r.subscriptions === 0) {
    return { ok: false, message: "The server has no browser of yours on file. Turn notifications off and on again." };
  }
  if (r.failed.length > 0) return { ok: false, message: r.failed[0] };
  return { ok: true, message: "Test sent. It should appear on this device in a few seconds." };
}
