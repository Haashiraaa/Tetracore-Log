// frontend/src/pages/duty/DutyPage.tsx
// Security officers' duty. An officer logs THEMSELVES here: go on duty at a gate, change
// gate mid-shift, go off duty. Everyone can read who is on duty now and the duty log.
// Nobody can sign trucks, visitors or staff in or out until they are on duty.
import { useRef, useState, type RefObject } from "react";
import type { DutyEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, seesAllFacilities } from "@/auth/permissions";
import { useDuty } from "@/components/duty/DutyContext";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SelectField } from "@/components/ui/TextField";
import { Spinner } from "@/components/ui/Spinner";
import { INSIDE_REFRESH_MS, SIGNATURE_MAX_BYTES } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { useInterval } from "@/hooks/useInterval";
import { downloadCsv } from "@/lib/csv";
import { formatDateTime, formatDuration, formatTime } from "@/lib/dates";
import { uuid } from "@/lib/ids";
import * as dutyService from "@/services/dutyService";

/** "Sign" switch plus the pad that appears when it is on. The signature is the officer's choice. */
function OptionalSignature({
  label,
  padRef,
  on,
  onChange,
  error,
  disabled,
}: {
  label: string;
  padRef: RefObject<SignaturePadHandle>;
  on: boolean;
  onChange: (on: boolean) => void;
  error: string | null;
  disabled: boolean;
}) {
  return (
    <div className="stack">
      <label className="check">
        <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} disabled={disabled} />
        {label}
      </label>
      {on && (
        <div className="field">
          <SignaturePad ref={padRef} disabled={disabled} invalid={Boolean(error)} hint="Sign here" />
          {error && (
            <p className="field__error" role="alert">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function readSignature(
  on: boolean,
  pad: SignaturePadHandle | null,
): { png: string | null } | { error: string } {
  if (!on) return { png: null };
  const read = readPad(pad, SIGNATURE_MAX_BYTES);
  if ("error" in read) return read;
  return read.png ? read : { error: "Sign, or switch the signature off." };
}

function Controls() {
  const duty = useDuty();
  const [gate, setGate] = useState("1");
  const [newGate, setNewGate] = useState("");
  const [signOn, setSignOn] = useState(true);
  const [signOff, setSignOff] = useState(true);
  const [sigError, setSigError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dutyId, setDutyId] = useState(uuid); // one id per attempt, reused on retry
  const onPad = useRef<SignaturePadHandle>(null);
  const offPad = useRef<SignaturePadHandle>(null);

  if (!duty) return null;
  if (duty.status === null) return duty.unknown ? <Banner tone="error">Could not load your duty status.</Banner> : <Spinner />;
  const { status } = duty;
  const current = status.current;
  const gates = dutyService.gatesOf(status.gate_count);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function goOn() {
    const read = readSignature(signOn, onPad.current);
    setSigError("error" in read ? read.error : null);
    if ("error" in read) return;
    await run(async () => {
      await dutyService.goOn(dutyId, Number(gate), read.png);
      setDutyId(uuid());
      duty?.refresh();
    });
  }

  async function changeGate() {
    await run(async () => {
      await dutyService.changeGate(Number(newGate));
      setNewGate("");
      duty?.refresh();
    });
  }

  async function goOff() {
    const read = readSignature(signOff, offPad.current);
    setSigError("error" in read ? read.error : null);
    if ("error" in read) return;
    await run(async () => {
      duty?.set(await dutyService.goOff(read.png));
    });
  }

  if (!current) {
    return (
      <section className="card stack" aria-labelledby="go-on-heading">
        <div className="row row--between">
          <h2 id="go-on-heading" className="eyebrow">
            You are off duty
          </h2>
          <Badge tone="grey">Off duty</Badge>
        </div>
        <p className="muted">Go on duty at your gate to start signing trucks, visitors and staff in and out.</p>
        {error && <Banner tone="error">{error}</Banner>}
        <SelectField label="Your gate" value={gate} onChange={(e) => setGate(e.target.value)} disabled={busy}>
          {gates.map((g) => (
            <option key={g} value={g}>
              {dutyService.gateLabel(g)}
            </option>
          ))}
        </SelectField>
        <OptionalSignature label="Sign to go on duty" padRef={onPad} on={signOn} onChange={setSignOn} error={sigError} disabled={busy} />
        <Button variant="dark" block loading={busy} onClick={() => void goOn()}>
          Go on duty
        </Button>
      </section>
    );
  }

  const others = gates.filter((g) => g !== current.gate);
  return (
    <section className="card stack" aria-labelledby="on-duty-heading">
      <div className="row row--between">
        <h2 id="on-duty-heading" className="eyebrow">
          You are on duty
        </h2>
        <Badge tone="green">On duty</Badge>
      </div>
      <p>
        <span className="cell-main">{dutyService.gateLabel(current.gate)}</span>
        <span className="cell-sub">
          Since {formatTime(current.on_duty_at)}, {formatDuration(current.on_duty_at)}
        </span>
      </p>
      {error && <Banner tone="error">{error}</Banner>}

      {others.length > 0 && (
        <div className="stack">
          <SelectField label="Change gate" value={newGate} onChange={(e) => setNewGate(e.target.value)} disabled={busy}>
            <option value="">Choose a gate</option>
            {others.map((g) => (
              <option key={g} value={g}>
                {dutyService.gateLabel(g)}
              </option>
            ))}
          </SelectField>
          <Button variant="secondary" disabled={!newGate} loading={busy} onClick={() => void changeGate()}>
            Move to this gate
          </Button>
        </div>
      )}

      <hr />
      <OptionalSignature label="Sign to go off duty" padRef={offPad} on={signOff} onChange={setSignOff} error={sigError} disabled={busy} />
      <Button variant="dark" block loading={busy} onClick={() => void goOff()}>
        Go off duty
      </Button>
    </section>
  );
}

function OnDutyNow({ showFacility }: { showFacility: boolean }) {
  const { data, error, reload } = useAsync((signal) => dutyService.onDutyNow(signal), []);
  useInterval(reload, INSIDE_REFRESH_MS);
  return (
    <section className="stack" aria-labelledby="now-heading">
      <h2 id="now-heading" className="eyebrow">
        On duty now
      </h2>
      {error !== null && data === null && <Banner tone="error">{errorMessage(error)}</Banner>}
      {data && data.length === 0 && <EmptyState title="Nobody is on duty" />}
      {data && data.length > 0 && (
        <ul className="activity">
          {data.map((d) => (
            <li key={d.id} className="activity__row">
              <span className="activity__time mono">{formatTime(d.on_duty_at)}</span>
              <span className="activity__who">
                <strong>{d.officer_name}</strong>
                {showFacility ? `, ${d.facility_code}` : ""}
              </span>
              <Badge tone="green">{dutyService.gateLabel(d.gate)}</Badge>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DutyLog({ showFacility }: { showFacility: boolean }) {
  const [page, setPage] = useState(0);
  const [rows, setRows] = useState<DutyEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const { error, loading, reload } = useAsync(async (signal) => {
    const result = await dutyService.fetchPage({}, page, signal);
    setRows((prev) => (page === 0 ? result.rows : [...prev, ...result.rows]));
    setHasMore(result.hasMore);
    return null;
  }, [page]);

  return (
    <section className="stack" aria-labelledby="log-heading">
      <div className="row row--between">
        <h2 id="log-heading" className="eyebrow">
          Duty log
        </h2>
        <div className="row">
          <Button variant="ghost" size="sm" onClick={() => { setPage(0); reload(); }}>
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={rows.length === 0}
            onClick={() => downloadCsv("duty-log.csv", dutyService.dutyToCsv(rows, showFacility))}
          >
            Download CSV
          </Button>
        </div>
      </div>
      {error !== null && <Banner tone="error">{errorMessage(error)}</Banner>}
      {!loading && rows.length === 0 && <EmptyState title="No duty logged yet" />}
      {rows.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {showFacility && <th>Facility</th>}
                <th>Officer</th>
                <th>Gate</th>
                <th>On duty</th>
                <th>Off duty</th>
                <th>How</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  {showFacility && <td data-label="Facility">{d.facility_code}</td>}
                  <td data-label="Officer">
                    <span className="cell-main">{d.officer_name}</span>
                    <span className="cell-sub mono">{d.officer_code}</span>
                  </td>
                  <td data-label="Gate">{d.gate}</td>
                  <td data-label="On duty">{formatDateTime(d.on_duty_at)}</td>
                  <td data-label="Off duty">{d.off_duty_at ? formatDateTime(d.off_duty_at) : "Now"}</td>
                  <td data-label="How">
                    <Badge tone={d.ended_how === null ? "green" : d.ended_how === "admin" ? "red" : "grey"}>
                      {dutyService.endedLabel(d)}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {hasMore && (
        <Button variant="secondary" loading={loading} onClick={() => setPage((p) => p + 1)}>
          Load more
        </Button>
      )}
    </section>
  );
}

export default function DutyPage() {
  const profile = useOfficer();
  const showFacility = seesAllFacilities(profile);
  const duty = useDuty();
  // The lists start over whenever this officer's own duty changes, so they never lag behind it.
  const stamp = duty?.status?.current?.id ?? "off";
  return (
    <div className="page stack stack--lg">
      <PageHeader title="Duty" subtitle="Who is on duty, and at which gate." />
      {canWriteEntries(profile) && <Controls />}
      <OnDutyNow key={`now-${stamp}`} showFacility={showFacility} />
      <DutyLog key={`log-${stamp}`} showFacility={showFacility} />
    </div>
  );
}
