// frontend/src/pages/gate/GateHomePage.tsx
// Where a shift starts: how many are inside, three big sign-in buttons, and the
// last few things that happened at the gate.
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { AnyEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { PlateChip } from "@/components/ui/PlateChip";
import { INSIDE_REFRESH_MS } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { useInterval } from "@/hooks/useInterval";
import { formatTime } from "@/lib/dates";
import { LOG_KINDS, type LogKind } from "@/models";
import * as entryService from "@/services/entryService";

const RECENT_PER_LOG = 4;
const RECENT_SHOWN = 5;

interface GateEvent {
  key: string;
  at: string;
  went: "in" | "out";
  kind: LogKind;
  entry: AnyEntry;
}

/** Every sign-in and sign-out among the entries, newest first. */
function latestEvents(byKind: AnyEntry[][]): GateEvent[] {
  const events = byKind.flatMap((entries, i) =>
    entries.flatMap((entry): GateEvent[] => {
      const kind = LOG_KINDS[i];
      const cameIn: GateEvent = { key: `${entry.id}-in`, at: entry.signed_in_at, went: "in", kind, entry };
      return entry.signed_out_at
        ? [cameIn, { key: `${entry.id}-out`, at: entry.signed_out_at, went: "out", kind, entry }]
        : [cameIn];
    }),
  );
  return events.sort((a, b) => b.at.localeCompare(a.at)).slice(0, RECENT_SHOWN);
}

function Tile({ to, title, hint, count, primary, icon }: {
  to: string;
  title: string;
  hint?: string;
  count: number | null;
  primary?: boolean;
  icon: ReactNode;
}) {
  return (
    <Link to={to} className={primary ? "tile tile--primary" : "tile"}>
      <span className="tile__top">
        <span className="tile__title">{title}</span>
        <svg aria-hidden="true" className="tile__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </span>
      <span className="tile__bottom">
        {hint && <span>{hint}</span>}
        <span className="mono">{count === null ? "" : `${count} in`}</span>
      </span>
    </Link>
  );
}

export default function GateHomePage() {
  const profile = useOfficer();
  const inside = useAsync(
    (signal) => Promise.all(LOG_KINDS.map((k) => entryService.fetchInside(k, signal))),
    [],
  );
  const recent = useAsync(
    (signal) => Promise.all(LOG_KINDS.map((k) => entryService.fetchRecent(k, RECENT_PER_LOG, signal))),
    [],
  );
  useInterval(() => {
    inside.reload();
    recent.reload();
  }, INSIDE_REFRESH_MS);

  const counts = inside.data ? inside.data.map((rows) => rows.length) : null;
  const total = counts ? counts.reduce((a, b) => a + b, 0) : null;
  const events = recent.data ? latestEvents(recent.data) : [];
  const failure = inside.error ?? recent.error;

  return (
    <div className="page page--narrow stack stack--lg">
      <section className="hero" aria-label="Inside right now">
        <p className="hero__where mono">{profile.facility_code}</p>
        <div className="hero__row">
          <p className="hero__count">
            <span className="hero__number">{total ?? "–"}</span>
            <span className="hero__label">
              Inside
              <br />
              right now
            </span>
          </p>
          <Link to="/inside" className="btn btn--on-dark btn--sm">
            See all
          </Link>
        </div>
      </section>

      {failure !== null && inside.data === null && <Banner tone="error">{errorMessage(failure)}</Banner>}

      <section className="stack" aria-labelledby="sign-in-heading">
        <h2 id="sign-in-heading" className="eyebrow">
          Sign someone in
        </h2>
        <Tile
          to="/gate/truck"
          title="Truck"
          hint="Type the plate, confirm the driver"
          count={counts ? counts[0] : null}
          primary
          icon={<><path d="M2 6h11v10H2zM13 9h4l4 4v3h-8z" /><circle cx="6.5" cy="17.5" r="1.8" /><circle cx="17" cy="17.5" r="1.8" /></>}
        />
        <div className="tiles">
          <Tile
            to="/gate/visitor"
            title="Visitor"
            count={counts ? counts[1] : null}
            icon={<><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.8-3.6 3.5-5.5 7-5.5s6.200 1.900 7 5.500" /></>}
          />
          <Tile
            to="/gate/staff"
            title="Staff"
            count={counts ? counts[2] : null}
            icon={<><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M9 5V3h6v2M8 16.500c.6-1.800 2-2.600 4-2.600s3.400.800 4 2.600" /><circle cx="12" cy="10.500" r="1.800" /></>}
          />
        </div>
      </section>

      {events.length > 0 && (
        <section className="stack" aria-labelledby="recent-heading">
          <h2 id="recent-heading" className="eyebrow">
            Last at the gate
          </h2>
          <ul className="activity">
            {events.map((ev) => {
              const face = entryService.faceOf(ev.entry);
              return (
                <li key={ev.key} className="activity__row">
                  <span className="activity__time mono">{formatTime(ev.at)}</span>
                  {face.plate && <PlateChip plate={face.plate} />}
                  <span className="activity__who">
                    <strong>{face.name}</strong>
                    {ev.kind === "staff" ? ", staff" : face.sub && !face.plate ? `, ${face.sub}` : ""}
                  </span>
                  <Badge tone={ev.went === "in" ? "amber" : "grey"}>{ev.went === "in" ? "IN" : "OUT"}</Badge>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
