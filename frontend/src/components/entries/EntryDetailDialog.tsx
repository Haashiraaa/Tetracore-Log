// frontend/src/components/entries/EntryDetailDialog.tsx
// One entry from any log, with the signature from the way in and the way out.
// The signature endpoint needs the bearer header, so a plain <img src> can't load it:
// fetch it as a blob and point the image at an object URL.
import { useEffect, useState } from "react";
import { getSignature } from "@/api/entries";
import type { AnyEntry, SignatureSide } from "@/api/schemas";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import { formatDateTime, formatDuration } from "@/lib/dates";
import { formatScm } from "@/lib/format";
import { LOG_LABEL, type LogKind } from "@/models";
import { faceOf, isTruck, isVisitor } from "@/services/entryService";
import { EntryStatus } from "./EntryStatus";

type SigState =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "error"; message: string };

function useSignature(kind: LogKind, entryId: string, has: boolean, side: SignatureSide): SigState {
  const [state, setState] = useState<SigState>({ kind: "none" });

  useEffect(() => {
    if (!has) {
      setState({ kind: "none" });
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setState({ kind: "loading" });
    getSignature(kind, entryId, side)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ kind: "ready", url: objectUrl });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setState(
          hasCode(e, ErrorCode.NotFound) ? { kind: "none" } : { kind: "error", message: errorMessage(e) },
        );
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [kind, entryId, has, side]);

  return state;
}

function SignatureView({ kind, entry, side }: { kind: LogKind; entry: AnyEntry; side: SignatureSide }) {
  const has = side === "in" ? entry.has_signature : entry.has_signature_out;
  const sig = useSignature(kind, entry.id, has, side);
  const label = side === "in" ? "Signed in" : "Signed out";
  return (
    <div className="sig-slot">
      <p className="field__label">{label}</p>
      {sig.kind === "loading" && <Spinner label="Loading signature" />}
      {sig.kind === "ready" && <img className="sig-view" src={sig.url} alt={`Signature: ${label.toLowerCase()}`} />}
      {sig.kind === "none" && <p className="sig-slot__none">No signature</p>}
      {sig.kind === "error" && <Banner tone="error">{sig.message}</Banner>}
    </div>
  );
}

function OwnFacts({ entry }: { entry: AnyEntry }) {
  if (isTruck(entry)) {
    return (
      <>
        <dt>Full name</dt>
        <dd>{entry.driver_name}</dd>
        <dt>Phone number</dt>
        <dd>{entry.driver_phone ?? "—"}</dd>
        <dt>Company</dt>
        <dd>{entry.company ?? "—"}</dd>
        <dt>Gas bought</dt>
        <dd>{entry.scm_purchased ? `${formatScm(entry.scm_purchased)} SCM` : "—"}</dd>
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
        <dt>Items received</dt>
        <dd>{entry.items_received ?? "—"}</dd>
        <dt>Phone number</dt>
        <dd>{entry.phone ?? "—"}</dd>
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
      <dd>{entry.phone ?? "—"}</dd>
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
            <dt>Time in</dt>
            <dd>
              {formatDateTime(entry.signed_in_at, true)} by {entry.signed_in_by_name}
            </dd>
            <dt>Time out</dt>
            <dd>
              {entry.signed_out_at
                ? `${formatDateTime(entry.signed_out_at, true)} by ${entry.signed_out_by_name ?? "unknown"}`
                : `Still inside (${formatDuration(entry.signed_in_at)})`}
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
