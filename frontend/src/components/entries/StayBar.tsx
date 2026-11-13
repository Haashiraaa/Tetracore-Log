// frontend/src/components/entries/StayBar.tsx
// Time made visible on an Inside line: a clock that ticks, and a bar that fills towards
// the point where the server warns that someone has been left inside.
import { Badge } from "@/components/ui/Badge";
import { useNow } from "@/hooks/useNow";
import { cx } from "@/lib/cx";
import { formatClock } from "@/lib/dates";

/** How long since `since`, ticking every second. Orange once the stay is a long one. */
export function StayClock({ since, longAfterMs, calm = "grey" }: { since: string; longAfterMs: number; calm?: "grey" | "blue" }) {
  const now = useNow();
  const long = now - new Date(since).getTime() >= longAfterMs;
  return <Badge tone={long ? "amber" : calm}>{formatClock(since, now)}</Badge>;
}

/** Fills over `limitHours`. Grey for the first half, warming to orange, hazard tape past the limit. */
export function StayBar({ since, limitHours, what }: { since: string; limitHours: number; what: string }) {
  const now = useNow();
  const part = Math.max(0, (now - new Date(since).getTime()) / (limitHours * 3_600_000));
  const late = part >= 1;
  const warmth = Math.min(1, Math.max(0, (part - 0.5) * 2));
  return (
    <div
      className={cx("stay", late && "stay--late")}
      role="img"
      aria-label={late ? `${what} for over ${limitHours} hours` : `${Math.round(part * 100)}% of ${limitHours} hours ${what}`}
    >
      <div
        className="stay__fill"
        style={{ width: `${Math.min(100, Math.max(2, part * 100))}%`, ["--warmth" as string]: `${Math.round(warmth * 100)}%` }}
      />
    </div>
  );
}
