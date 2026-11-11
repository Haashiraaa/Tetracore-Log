// frontend/src/pages/inside/InsidePage.tsx
// Who is inside right now, across the three logs. Everyone can read it (scoped by
// the server); only accounts that belong to a facility get the sign-out button.
import { useState } from "react";
import { Link } from "react-router-dom";
import type { AnyEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, seesAllFacilities } from "@/auth/permissions";
import { EntryDetailDialog } from "@/components/entries/EntryDetailDialog";
import { KindTabs } from "@/components/entries/KindTabs";
import { SignOutSheet, signOutTargetOf, type SignOutTarget } from "@/components/entries/SignOutSheet";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { INSIDE_REFRESH_MS } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { useInterval } from "@/hooks/useInterval";
import { formatDuration, formatTime } from "@/lib/dates";
import { LOG_KINDS, LOG_LABEL, type LogKind } from "@/models";
import * as entryService from "@/services/entryService";

const SIGN_IN_PATH: Record<LogKind, string> = {
  trucks: "/gate/truck",
  visitors: "/gate/visitor",
  staff: "/gate/staff",
};

/** Inside this long and the duration turns orange, so a forgotten sign-out stands out. */
const LONG_STAY_MS = 6 * 60 * 60 * 1000;

function isLongStay(e: AnyEntry): boolean {
  return Date.now() - new Date(e.signed_in_at).getTime() >= LONG_STAY_MS;
}

export default function InsidePage() {
  const profile = useOfficer();
  const canWrite = canWriteEntries(profile);
  const showFacility = seesAllFacilities(profile);

  const [kind, setKind] = useState<LogKind>("trucks");
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<AnyEntry | null>(null);
  const [outTarget, setOutTarget] = useState<SignOutTarget | null>(null);

  const { data, error, loading, reload } = useAsync(
    (signal) => Promise.all(LOG_KINDS.map((k) => entryService.fetchInside(k, signal))),
    [],
  );
  useInterval(reload, INSIDE_REFRESH_MS);

  const all = data ? data[LOG_KINDS.indexOf(kind)] : [];
  const counts = data ? Object.fromEntries(LOG_KINDS.map((k, i) => [k, data[i].length])) : undefined;
  const needle = query.trim().toUpperCase();
  const rows = all.filter((e) => !needle || entryService.searchText(e).includes(needle));
  const many = LOG_LABEL[kind].many.toLowerCase();

  function pick(next: LogKind) {
    setKind(next);
    setQuery("");
  }

  return (
    <div className="page stack stack--lg">
      <PageHeader
        title="Inside now"
        actions={
          <Button variant="secondary" size="sm" onClick={reload} loading={loading && data !== null}>
            Refresh
          </Button>
        }
      />

      <KindTabs value={kind} onChange={pick} counts={counts} />

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
        <EmptyState title={`No ${many} inside`}>They show up here after they sign in at the gate.</EmptyState>
      )}
      {all.length > 0 && rows.length === 0 && (
        <EmptyState title="No match">Nothing inside matches "{query}".</EmptyState>
      )}

      <ul className="cards">
        {rows.map((e) => {
          const face = entryService.faceOf(e);
          return (
            <li key={e.id} className="card entry-card">
              <div className="entry-card__main">
                <div className="row row--between">
                  {face.plate ? <PlateChip plate={face.plate} /> : <span className="entry-name">{face.name}</span>}
                  {showFacility && <Badge tone="ink">{e.facility_code}</Badge>}
                </div>
                {face.plate && <span className="cell-main">{face.name}</span>}
                {face.sub && <span className="cell-sub">{face.sub}</span>}
                {face.phone && (
                  <a className="cell-sub" href={`tel:${face.phone}`}>
                    {face.phone}
                  </a>
                )}
                <p className="entry-card__time">
                  <span className="mono">in {formatTime(e.signed_in_at)}</span>
                  <Badge tone={isLongStay(e) ? "amber" : "grey"}>{formatDuration(e.signed_in_at)}</Badge>
                </p>
              </div>
              <div className="row">
                {canWrite && (
                  <Button variant="secondary" size="sm" onClick={() => setOutTarget(signOutTargetOf(kind, e))}>
                    Sign out
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => setDetail(e)}>
                  Details
                </Button>
              </div>
            </li>
          );
        })}
      </ul>

      <SignOutSheet
        target={outTarget}
        onClose={() => setOutTarget(null)}
        onDone={() => {
          setOutTarget(null);
          reload();
        }}
      />
      <EntryDetailDialog kind={kind} entry={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
