// frontend/src/components/entries/EntryDetailDialog.tsx
// One entry from any log, with the signature from the way in and the way out.
// The signature endpoint needs the bearer header, so a plain <img src> can't load it:
// fetch it as a blob and point the image at an object URL.
import type { AnyEntry, SignatureSide } from "@/api/schemas";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { useSignature } from "@/hooks/useSignature";
import { formatDateTime, formatDuration } from "@/lib/dates";
import { formatScm } from "@/lib/format";
import { formatPhone } from "@/lib/people";
import { LOG_LABEL, type LogKind } from "@/models";
import { faceOf, isTruck, isVisitor, isWaybill } from "@/services/entryService";
import { quantityLabel } from "@/services/visitorService";
import { EntryStatus } from "./EntryStatus";
import { STATUS_LABEL } from "@/services/truckService";

function SignatureView({ kind, entry, side }: { kind: LogKind; entry: AnyEntry; side: SignatureSide }) {
  const has = side === "in" ? entry.has_signature : entry.has_signature_out;
  const sig = useSignature(kind, entry.id, has, side);
  const label = side === "in" ? "Signed in" : "Signed out";
  const reused = side === "in" ? entry.signature_in_reused : entry.signature_out_reused;
  return (
    <div className="sig-slot">
      <p className="field__label">{label}</p>
      {sig.kind === "loading" && <Spinner label="Loading signature" />}
      {sig.kind === "ready" && <img className="sig-view" src={sig.url} alt={`Signature: ${label.toLowerCase()}`} />}
      {sig.kind === "ready" && reused && (
        <p className="muted">
          {side === "in" ? "Signature on file, not drawn this visit." : "Sign-in signature reused, not drawn at sign-out."}
        </p>
      )}
      {sig.kind === "none" && <p className="sig-slot__none">No signature</p>}
      {sig.kind === "error" && <Banner tone="error">{sig.message}</Banner>}
    </div>
  );
}

function OwnFacts({ entry }: { entry: AnyEntry }) {
  if (isTruck(entry)) {
    return (
      <>
        <dt>Status</dt>
        <dd>{STATUS_LABEL[entry.status]}</dd>
        <dt>Full name</dt>
        <dd>{entry.driver_name}</dd>
        <dt>Phone number</dt>
        <dd>{entry.driver_phone ? formatPhone(entry.driver_phone) : "—"}</dd>
        <dt>Company</dt>
        <dd>{entry.company ?? "—"}</dd>
        <dt>Cab number</dt>
        <dd>{entry.cab_number ?? "—"}</dd>
        <dt>Gas bought</dt>
        <dd>{entry.scm_purchased ? `${formatScm(entry.scm_purchased)} SCM` : "—"}</dd>
        {entry.status === "left_queue" && (
          <>
            <dt>Why it left</dt>
            <dd>{entry.left_queue_reason}</dd>
          </>
        )}
      </>
    );
  }
  if (isVisitor(entry)) {
    return (
      <>
        <dt>Full name</dt>
        <dd>{entry.full_name}</dd>
        <dt>Company name</dt>
        <dd>{entry.company ?? "—"}</dd>
        <dt>Purpose of visit</dt>
        <dd>{entry.purpose ?? "—"}</dd>
        <dt>Items brought</dt>
        <dd>
          {entry.items.length > 0 ? (
            <ul className="detail-items">
              {entry.items.map((item, i) => (
                <li key={i}>
                  {item.name} <span className="muted">× {quantityLabel(item)}</span>
                </li>
              ))}
            </ul>
          ) : (
            (entry.items_received ?? "—")
          )}
        </dd>
        <dt>Phone number</dt>
        <dd>{entry.phone ? formatPhone(entry.phone) : "—"}</dd>
      </>
    );
  }
  if (isWaybill(entry)) {
    return (
      <>
        <dt>Courier</dt>
        <dd>{entry.full_name}</dd>
        <dt>Items</dt>
        <dd>
          <ul className="detail-items">
            {entry.items.map((item, i) => (
              <li key={i}>
                {item.name} <span className="muted">× {quantityLabel(item)}</span>
              </li>
            ))}
          </ul>
        </dd>
        <dt>Vehicle</dt>
        <dd>{entry.came_by_vehicle ? (entry.plate_number ?? "Came by vehicle") : "On foot"}</dd>
        <dt>Phone number</dt>
        <dd>{entry.phone ? formatPhone(entry.phone) : "—"}</dd>
      </>
    );
  }
  return (
    <>
      <dt>Full name</dt>
      <dd>{entry.full_name}</dd>
      <dt>Capacity</dt>
      <dd>{entry.capacity ?? "—"}</dd>
      <dt>Phone number</dt>
      <dd>{entry.phone ? formatPhone(entry.phone) : "—"}</dd>
    </>
  );
}

interface EntryDetailDialogProps {
  kind: LogKind;
  entry: AnyEntry | null;
  onClose: () => void;
}

export function EntryDetailDialog({ kind, entry, onClose }: EntryDetailDialogProps) {
  const face = entry ? faceOf(entry) : null;
  return (
    <Modal
      open={entry !== null}
      title={`${LOG_LABEL[kind].many} log entry`}
      onClose={onClose}
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {entry && face && (
        <div className="stack">
          <div className="row row--between">
            {face.plate ? <PlateChip plate={face.plate} large /> : <span className="entry-name">{face.name}</span>}
            <EntryStatus entry={entry} />
          </div>

          <dl className="facts">
            <OwnFacts entry={entry} />
            <dt>Facility</dt>
            <dd>{entry.facility_code}</dd>
            {isTruck(entry) ? (
              <>
                <dt>Joined the queue</dt>
                <dd>
                  {formatDateTime(entry.signed_in_at, true)} by {entry.signed_in_by_name}
                  {entry.queued_gate ? `, gate ${entry.queued_gate}` : ""}
                </dd>
                <dt>Let in</dt>
                <dd>
                  {entry.entered_at
                    ? `${formatDateTime(entry.entered_at, true)}${entry.gate_in ? `, gate ${entry.gate_in}` : ""}`
                    : "Not yet"}
                </dd>
              </>
            ) : (
              <>
                <dt>Time in</dt>
                <dd>
                  {formatDateTime(entry.signed_in_at, true)} by {entry.signed_in_by_name}
                  {entry.gate_in ? `, gate ${entry.gate_in}` : ""}
                </dd>
              </>
            )}
            <dt>Time out</dt>
            <dd>
              {entry.signed_out_at
                ? `${formatDateTime(entry.signed_out_at, true)} by ${entry.signed_out_by_name ?? "unknown"}${
                    entry.gate_out ? `, gate ${entry.gate_out}` : ""
                  }`
                : isTruck(entry) && entry.status === "queued"
                  ? `Still in the queue (${formatDuration(entry.signed_in_at)})`
                  : `Still inside (${formatDuration(isTruck(entry) && entry.entered_at ? entry.entered_at : entry.signed_in_at)})`}
            </dd>
          </dl>

          <div className="sig-pair">
            <SignatureView kind={kind} entry={entry} side="in" />
            <SignatureView kind={kind} entry={entry} side="out" />
          </div>
        </div>
      )}
    </Modal>
  );
}
