// frontend/src/lib/dates.ts
// The API speaks UTC. People see Lagos time.

import { DISPLAY_TZ, DISPLAY_UTC_OFFSET } from "@/config/env";

const dayFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: DISPLAY_TZ,
  day: "numeric",
  month: "short",
});
const dayYearFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: DISPLAY_TZ,
  day: "numeric",
  month: "short",
  year: "numeric",
});
const timeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: DISPLAY_TZ,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const hourFmt = new Intl.DateTimeFormat("en-GB", { timeZone: DISPLAY_TZ, hour: "2-digit", hourCycle: "h23" });
const isoDayFmt = new Intl.DateTimeFormat("en-CA", { timeZone: DISPLAY_TZ, year: "numeric", month: "2-digit", day: "2-digit" });

/** The hour of the day in Lagos, 0 to 23. */
export function lagosHour(at: Date | string | number = new Date()): number {
  return Number(hourFmt.format(new Date(at)));
}

/** Today's date in Lagos as 'YYYY-MM-DD'. */
export function todayDate(at: Date = new Date()): string {
  return isoDayFmt.format(at);
}

export function formatTime(iso: string): string {
  return timeFmt.format(new Date(iso));
}

/** "17 Oct, 14:32" (or "17 Oct 2026, 14:32" with year). */
export function formatDateTime(iso: string, withYear = false): string {
  const d = new Date(iso);
  return `${(withYear ? dayYearFmt : dayFmt).format(d)}, ${timeFmt.format(d)}`;
}

/** "35 min", "2 h 15 min", "1 d 3 h". */
export function formatDuration(fromIso: string, to: Date = new Date()): string {
  const minutes = Math.max(0, Math.floor((to.getTime() - new Date(fromIso).getTime()) / 60_000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ${minutes % 60} min`;
  return `${Math.floor(hours / 24)} d ${hours % 24} h`;
}

/** A running clock, "0:52:07", for the first day; after that "1 d 3 h". */
export function formatClock(fromIso: string, nowMs: number = Date.now()): string {
  const seconds = Math.max(0, Math.floor((nowMs - new Date(fromIso).getTime()) / 1000));
  if (seconds >= 24 * 3600) return formatDuration(fromIso, new Date(nowMs));
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${Math.floor(seconds / 3600)}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`;
}

/** 'YYYY-MM-DD' (from <input type="date">) -> ISO instant at 00:00 Lagos time. */
export function startOfDayIso(date: string): string {
  return new Date(`${date}T00:00:00${DISPLAY_UTC_OFFSET}`).toISOString();
}

/** Exclusive upper bound for "up to and including this date". */
export function startOfNextDayIso(date: string): string {
  const start = new Date(`${date}T00:00:00${DISPLAY_UTC_OFFSET}`);
  return new Date(start.getTime() + 24 * 60 * 60 * 1000).toISOString();
}
