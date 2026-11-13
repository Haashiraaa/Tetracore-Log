// frontend/src/components/entries/DayStrip.tsx
// Today's sign-ins, one bar per hour. Sits in the black hero on Gate.
import { RollingNumber } from "@/components/ui/RollingNumber";
import { cx } from "@/lib/cx";

/** Bars are scaled to the busiest hour, but a quiet day is not blown up to full height. */
const MIN_SCALE = 4;

export function DayStrip({
  hours,
  nowHour,
  total,
  capped,
}: {
  /** 24 counts, index = hour of the day in Lagos. */
  hours: number[];
  nowHour: number;
  total: number;
  /** The server gave as many rows as were asked for, so there may be more. */
  capped: boolean;
}) {
  const scale = Math.max(MIN_SCALE, ...hours);
  const busiest = hours.indexOf(Math.max(...hours));
  const label =
    total === 0
      ? "Nobody has signed in today"
      : `${total}${capped ? " or more" : ""} signed in today, most between ${busiest}:00 and ${busiest + 1}:00`;
  return (
    <div className="day">
      <div className="day__head">
        <span>Today, hour by hour</span>
        <span className="mono">
          <RollingNumber value={total} />
          {capped ? "+" : ""} signed in
        </span>
      </div>
      <div className="day__bars" role="img" aria-label={label}>
        {hours.map((count, hour) => (
          <span
            key={hour}
            className={cx("day__bar", hour === nowHour && "day__bar--now", hour > nowHour && "day__bar--later")}
            style={{ height: `${Math.max(6, Math.round((count / scale) * 100))}%` }}
          />
        ))}
      </div>
      <div className="day__axis mono" aria-hidden="true">
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>24</span>
      </div>
    </div>
  );
}
