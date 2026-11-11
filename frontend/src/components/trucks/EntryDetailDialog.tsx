// frontend/src/components/trucks/EntryDetailDialog.tsx
// The signature endpoint needs the bearer header, so a plain <img src> can't load it:
// fetch it as a blob and point the image at an object URL.
import { useEffect, useState } from "react";
import { getSignature } from "@/api/trucks";
import type { TruckEntry } from "@/api/schemas";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import { formatDateTime, formatDuration } from "@/lib/dates";
import { formatScm } from "@/lib/format";
import { EntryStatus } from "./EntryStatus";

type SigState =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "error"; message: string };

function useSignature(entry: TruckEntry | null): SigState {
  const [state, setState] = useState<SigState>({ kind: "none" });

  useEffect(() => {
    if (!entry || !entry.has_signature) {
      setState({ kind: "none" });
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setState({ kind: "loading" });
    getSignature(entry.id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ kind: "ready", url: objectUrl });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setState(
          hasCode(e, ErrorCode.NotFound)
            ? { kind: "none" }
            : { kind: "error", message: errorMessage(e) },
        );
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [entry]);

  return state;
}

export function EntryDetailDialog({ entry, onClose }: { entry: TruckEntry | null; onClose: () => void }) {
  const sig = useSignature(entry);

  return (
    <Modal
      open={entry !== null}
      title="Truck entry"
      onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose}>Close</Button>}
    >
      {entry && (
        <div className="stack">
          <div className="row row--between">
            <PlateChip plate={entry.plate_number} large />
            <EntryStatus entry={entry} />
          </div>

          <dl className="facts">
            <dt>Driver</dt>
            <dd>{entry.driver_name}</dd>
            <dt>Phone</dt>
            <dd>{entry.driver_phone ?? "—"}</dd>
            <dt>Company</dt>
            <dd>{entry.company ?? "—"}</dd>
            <dt>Facility</dt>
            <dd>{entry.facility_code}</dd>
            <dt>Signed in</dt>
            <dd>
              {formatDateTime(entry.signed_in_at, true)} by {entry.signed_in_by_name}
            </dd>
            <dt>Signed out</dt>
            <dd>
              {entry.signed_out_at
                ? `${formatDateTime(entry.signed_out_at, true)} by ${entry.signed_out_by_name ?? "unknown"}`
                : `Still inside (${formatDuration(entry.signed_in_at)})`}
            </dd>
            <dt>SCM purchased</dt>
            <dd>{formatScm(entry.scm_purchased)}</dd>
          </dl>

          <div>
            <p className="field__label">Signature</p>
            {sig.kind === "loading" && <Spinner label="Loading signature" />}
            {sig.kind === "ready" && <img className="sig-view" src={sig.url} alt="Driver's signature" />}
            {sig.kind === "none" && <p className="muted">No signature was captured.</p>}
            {sig.kind === "error" && <Banner tone="error">{sig.message}</Banner>}
          </div>
        </div>
      )}
    </Modal>
  );
}
