// frontend/src/pages/inside/InsidePage.tsx
// Who is inside right now, across the three logs. Everyone can read it (scoped by
// the server); only accounts that belong to a facility get the sign-out button.
// Time moves here: every line has a running clock and a bar that fills towards the point
// where the server warns, and a line is stamped the moment it is let in or signed out.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { AnyEntry, TruckEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, seesAllFacilities } from "@/auth/permissions";
import { EntryDetailDialog } from "@/components/entries/EntryDetailDialog";
import { FlowStrip } from "@/components/entries/FlowStrip";
import { KindTabs } from "@/components/entries/KindTabs";
import { SignOutSheet, signOutTargetOf, type SignOutTarget } from "@/components/entries/SignOutSheet";
import { Stamp } from "@/components/entries/Stamp";
import { StayBar, StayClock } from "@/components/entries/StayBar";
import {
  EnterTruckSheet,
  LeaveQueueSheet,
  queuedTruckOf,
  type QueuedTruck,
} from "@/components/entries/TruckQueueSheets";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { LiveDot } from "@/components/ui/LiveDot";
import { PageHeader } from "@/components/ui/PageHeader";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { INSIDE_REFRESH_MS, QUEUE_LIMIT_HOURS, STAMP_MS, STAY_LIMIT_HOURS, TODAY_MAX_ROWS, TODAY_REFRESH_MS } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { useFreshKeys } from "@/hooks/useFreshKeys";
import { useInterval } from "@/hooks/useInterval";
import { cx } from "@/lib/cx";
import { formatTime } from "@/lib/dates";
import { buzz } from "@/lib/haptics";
import { LOG_KINDS, LOG_LABEL, type LogKind } from "@/models";
import * as entryService from "@/services/entryService";

const SIGN_IN_PATH: Record<LogKind, string> = {
  trucks: "/gate/truck",
  visitors: "/gate/visitor",
  staff: "/gate/staff",
};

/** Inside this long and the duration turns orange, so a forgotten sign-out stands out. */
const LONG_STAY_MS = 6 * 60 * 60 * 1000;

/** A queued truck is waiting outside: it counts from joining the queue. Everyone else, and a
 *  truck on site, counts from when they came in. */
function isQueued(e: AnyEntry): e is TruckEntry {
  return entryService.isTruck(e) && e.status === "queued";
}

function cameInAt(e: AnyEntry): string {
  return entryService.isTruck(e) && e.entered_at ? e.entered_at : e.signed_in_at;
}

/** The server warns about visitors and trucks left inside, not staff, so staff get no bar. */
const HAS_STAY_BAR: Record<LogKind, boolean> = { trucks: true, visitors: true, staff: false };

export default function InsidePage() {
  const profile = useOfficer();
  const canWrite = canWriteEntries(profile);
  const showFacility = seesAllFacilities(profile);

  const [kind, setKind] = useState<LogKind>("trucks");
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<AnyEntry | null>(null);
  const [outTarget, setOutTarget] = useState<SignOutTarget | null>(null);
  const [enterTarget, setEnterTarget] = useState<QueuedTruck | null>(null);
  const [leaveTarget, setLeaveTarget] = useState<QueuedTruck | null>(null);

  const { data, error, loading, updatedAt, reload } = useAsync(
    (signal) => Promise.all(LOG_KINDS.map((k) => entryService.fetchInside(k, signal))),
    [],
  );
  useInterval(reload, INSIDE_REFRESH_MS);
  // The newest trucks, whatever day they came: one that arrived yesterday can leave today.
  const latestTrucks = useAsync((signal) => entryService.fetchRecent("trucks", TODAY_MAX_ROWS, signal), []);
  useInterval(latestTrucks.reload, TODAY_REFRESH_MS);

  // A stamp lands on a line the moment it is written. `then` runs once the stamp has been seen.
  const [stamps, setStamps] = useState<Record<string, string>>({});
  const timers = useRef<number[]>([]);
  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((id) => window.clearTimeout(id));
  }, []);
  function stamp(entryId: string, text: string, ms: number, then?: () => void) {
    setStamps((s) => ({ ...s, [entryId]: text }));
    buzz();
    timers.current.push(
      window.setTimeout(() => {
        then?.();
        setStamps((s) => {
          const rest = { ...s };
          delete rest[entryId];
          return rest;
        });
      }, ms),
    );
  }
  function reloadAll() {
    reload();
    latestTrucks.reload();
  }

  const all = data ? data[LOG_KINDS.indexOf(kind)] : [];
  const counts = data ? Object.fromEntries(LOG_KINDS.map((k, i) => [k, data[i].length])) : undefined;
  const needle = query.trim().toUpperCase();
  const rows = all.filter((e) => !needle || entryService.searchText(e).includes(needle));
  const many = LOG_LABEL[kind].many.toLowerCase();
  const queued = rows.filter(isQueued);
  const present = rows.filter((e) => !isQueued(e));
  const fresh = useFreshKeys(
    present.map((e) => e.id),
    data !== null,
  );
  const trucks = data ? data[LOG_KINDS.indexOf("trucks")] : [];
  const trucksQueued = trucks.filter(isQueued).length;

  function pick(next: LogKind) {
    setKind(next);
    setQuery("");
  }

  return (
    <div className="page stack stack--lg">
      <PageHeader
        title="Inside now"
        actions={
          <div className="row">
            <LiveDot updatedAt={updatedAt} failed={error !== null} />
            <Button variant="secondary" size="sm" onClick={reloadAll} loading={loading && data !== null}>
              Refresh
            </Button>
          </div>
        }
      />

      <KindTabs value={kind} onChange={pick} counts={counts} />

      {kind === "trucks" && data !== null && (
        <FlowStrip
          queued={trucksQueued}
          onSite={trucks.length - trucksQueued}
          leftToday={latestTrucks.data ? entryService.departedToday(latestTrucks.data) : null}
        />
      )}

      {canWrite && (
        <Link to={SIGN_IN_PATH[kind]} className="btn btn--primary btn--block btn--lead">
          Sign {kind === "staff" ? "staff" : `a ${LOG_LABEL[kind].one}`} in
        </Link>
      )}

      {all.length >= entryService.INSIDE_MAX_ROWS && (
        <Banner tone="warn">
          Showing the first {entryService.INSIDE_MAX_ROWS}. Use the Log page to see the rest.
        </Banner>
      )}

      {all.length > 5 && (
        <TextField
          label={kind === "trucks" ? "Find a plate or driver" : "Find a name"}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      )}

      {error !== null && data === null && <Banner tone="error">{errorMessage(error)}</Banner>}
      {loading && data === null && error === null && <Spinner />}

      {data !== null && all.length === 0 && (
        <EmptyState title={`No ${many} ${kind === "trucks" ? "queued or on site" : "inside"}`}>
          They show up here after they sign in at the gate.
        </EmptyState>
      )}
      {all.length > 0 && rows.length === 0 && (
        <EmptyState title="No match">Nothing inside matches "{query}".</EmptyState>
      )}

      {kind === "trucks" && queued.length > 0 && (
        <section className="stack" aria-labelledby="queued-heading">
          <h2 id="queued-heading" className="eyebrow">
            Queued outside ({queued.length})
          </h2>
          <ul className="lines">
            {queued.map((e) => {
              const face = entryService.faceOf(e);
              return (
                <li key={e.id} className="line">
                  <div className="line__who">
                    {face.plate && <PlateChip plate={face.plate} />}
                    <span className="cell-main">{face.name}</span>
                    {face.sub && <span className="cell-sub">{face.sub}</span>}
                  </div>
                  <div className="line__meta">
                    {face.phone && (
                      <a className="mono" href={`tel:${face.phone}`}>
                        {face.phone}
                      </a>
                    )}
                    {showFacility && <Badge tone="ink">{e.facility_code}</Badge>}
                  </div>
                  <div className="line__time">
                    <span className="mono">queued {formatTime(e.signed_in_at)}</span>
                    <StayClock since={e.signed_in_at} longAfterMs={LONG_STAY_MS} calm="blue" />
                  </div>
                  <div className="line__actions">
                    {canWrite && (
                      <>
                        <Button variant="secondary" size="sm" onClick={() => setEnterTarget(queuedTruckOf(e))}>
                          Let in
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setLeaveTarget(queuedTruckOf(e))}>
                          Left queue
                        </Button>
                      </>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => setDetail(e)}>
                      Details
                    </Button>
                  </div>
                  <StayBar since={e.signed_in_at} limitHours={QUEUE_LIMIT_HOURS} what="in the queue" />
                  {stamps[e.id] && <Stamp text={stamps[e.id]} />}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {kind === "trucks" && queued.length > 0 && present.length > 0 && (
        <h2 className="eyebrow">On site ({present.length})</h2>
      )}

      <ul className="lines">
        {present.map((e) => {
          const face = entryService.faceOf(e);
          return (
            <li key={e.id} className={cx("line", fresh.has(e.id) && "line--new")}>
              <div className="line__who">
                {face.plate && <PlateChip plate={face.plate} />}
                <span className="cell-main">{face.name}</span>
                {face.sub && <span className="cell-sub">{face.sub}</span>}
              </div>
              <div className="line__meta">
                {face.phone && (
                  <a className="mono" href={`tel:${face.phone}`}>
                    {face.phone}
                  </a>
                )}
                {showFacility && <Badge tone="ink">{e.facility_code}</Badge>}
                {e.gate_in && <Badge tone="grey">Gate {e.gate_in}</Badge>}
              </div>
              <div className="line__time">
                <span className="mono">in {formatTime(cameInAt(e))}</span>
                <StayClock since={cameInAt(e)} longAfterMs={LONG_STAY_MS} />
              </div>
              <div className="line__actions">
                {canWrite && (
                  <Button variant="secondary" size="sm" onClick={() => setOutTarget(signOutTargetOf(kind, e, cameInAt(e)))}>
                    Sign out
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => setDetail(e)}>
                  Details
                </Button>
              </div>
              {HAS_STAY_BAR[kind] && (
                <StayBar since={cameInAt(e)} limitHours={STAY_LIMIT_HOURS} what={kind === "trucks" ? "on site" : "inside"} />
              )}
              {stamps[e.id] && <Stamp text={stamps[e.id]} />}
            </li>
          );
        })}
      </ul>

      <EnterTruckSheet
        truck={enterTarget}
        onClose={() => setEnterTarget(null)}
        onDone={(entry) => {
          setEnterTarget(null);
          reloadAll();
          // The line moves to "On site" when the reload lands; the stamp waits for it there.
          stamp(entry.id, `In · ${formatTime(entry.entered_at ?? new Date().toISOString())}`, STAMP_MS * 2);
        }}
      />
      <LeaveQueueSheet
        truck={leaveTarget}
        onClose={() => setLeaveTarget(null)}
        onDone={(entry) => {
          setLeaveTarget(null);
          stamp(entry.id, `Left queue · ${formatTime(entry.signed_out_at ?? new Date().toISOString())}`, STAMP_MS, reloadAll);
        }}
      />

      <SignOutSheet
        target={outTarget}
        onClose={() => setOutTarget(null)}
        onDone={(entry) => {
          setOutTarget(null);
          stamp(entry.id, `Signed out · ${formatTime(entry.signed_out_at ?? new Date().toISOString())}`, STAMP_MS, reloadAll);
        }}
      />
      <EntryDetailDialog kind={kind} entry={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
