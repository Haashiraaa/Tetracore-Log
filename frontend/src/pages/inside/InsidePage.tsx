// frontend/src/pages/inside/InsidePage.tsx
// Trucks currently inside. Every role can read it (scoped by the server);
// only gate officers get the sign-out button.
import { useState } from "react";
import type { TruckEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, seesAllFacilities } from "@/auth/permissions";
import { EntryDetailDialog } from "@/components/trucks/EntryDetailDialog";
import { SignOutDialog, type SignOutTarget } from "@/components/trucks/SignOutDialog";
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
import { normalizePlate } from "@/lib/plate";
import * as truckService from "@/services/truckService";

const MAX_ROWS = 200;

export default function InsidePage() {
  const profile = useOfficer();
  const canWrite = canWriteEntries(profile);
  const showFacility = seesAllFacilities(profile);

  const { data, error, loading, reload } = useAsync((signal) => truckService.fetchInside(signal), []);
  useInterval(reload, INSIDE_REFRESH_MS);

  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<TruckEntry | null>(null);
  const [outTarget, setOutTarget] = useState<SignOutTarget | null>(null);

  const needle = normalizePlate(query);
  const rows = (data ?? []).filter((e) => !needle || e.plate_number.includes(needle));
  const total = data?.length ?? 0;

  return (
    <div className="page stack stack--lg">
      <PageHeader
        title="Inside"
        subtitle={data ? `${total} ${total === 1 ? "truck" : "trucks"} inside now` : undefined}
        actions={
          <Button variant="secondary" size="sm" onClick={reload} loading={loading && data !== null}>
            Refresh
          </Button>
        }
      />

      {total >= MAX_ROWS && (
        <Banner tone="warn">Showing the first {MAX_ROWS} trucks. Use the Log page to see the rest.</Banner>
      )}

      {total > 0 && (
        <TextField
          label="Find a plate"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
        />
      )}

      {error !== null && data === null && <Banner tone="error">{errorMessage(error)}</Banner>}
      {loading && data === null && error === null && <Spinner />}

      {data !== null && total === 0 && (
        <EmptyState title="No trucks inside">Trucks show up here after they sign in at the gate.</EmptyState>
      )}
      {data !== null && total > 0 && rows.length === 0 && (
        <EmptyState title="No match">No truck inside matches "{query}".</EmptyState>
      )}

      <ul className="cards">
        {rows.map((e) => (
          <li key={e.id} className="card entry-card">
            <div className="row row--between">
              <PlateChip plate={e.plate_number} large />
              {showFacility && <Badge tone="blue">{e.facility_code}</Badge>}
            </div>
            <div>
              <span className="cell-main">{e.driver_name}</span>
              {e.company && <span className="cell-sub">{e.company}</span>}
              {e.driver_phone && (
                <a className="cell-sub" href={`tel:${e.driver_phone}`}>
                  {e.driver_phone}
                </a>
              )}
            </div>
            <p className="muted">
              In since {formatTime(e.signed_in_at)}, inside for {formatDuration(e.signed_in_at)}. Signed in by{" "}
              {e.signed_in_by_name}.
            </p>
            <div className="row">
              {canWrite && (
                <Button size="sm" onClick={() => setOutTarget({ entryId: e.id, plate: e.plate_number })}>
                  Sign out
                </Button>
              )}
              <Button variant="secondary" size="sm" onClick={() => setDetail(e)}>
                Details
              </Button>
            </div>
          </li>
        ))}
      </ul>

      <SignOutDialog
        target={outTarget}
        onClose={() => setOutTarget(null)}
        onDone={() => {
          setOutTarget(null);
          reload();
        }}
      />
      <EntryDetailDialog entry={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
