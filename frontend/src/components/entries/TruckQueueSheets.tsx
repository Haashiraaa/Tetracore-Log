// frontend/src/components/entries/TruckQueueSheets.tsx
// The two things that can happen to a truck waiting in the queue:
//   EnterTruckSheet      let it in: the driver signs on the way in (or the signature on file is used)
//   LeaveQueueSheet      it gave up and left: say why (free text)
import { useEffect, useRef, useState } from "react";
import type { TruckEntry } from "@/api/schemas";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import { formatDuration, formatTime } from "@/lib/dates";
import * as truckService from "@/services/truckService";

/** A queued truck, as much as the sheets need to know about it. */
export interface QueuedTruck {
  entryId: string;
  plate: string;
  driverName: string;
  /** When it joined the queue. null when only a lookup result is in hand. */
  queuedAt: string | null;
}

export function queuedTruckOf(e: TruckEntry): QueuedTruck {
  return { entryId: e.id, plate: e.plate_number, driverName: e.driver_name, queuedAt: e.signed_in_at };
}

function Who({ truck }: { truck: QueuedTruck }) {
  return (
    <>
      <div className="row row--between">
        <PlateChip plate={truck.plate} large />
        <span className="muted">{truck.driverName}</span>
      </div>
      {truck.queuedAt && (
        <p className="muted">
          Queued since {formatTime(truck.queuedAt)} ({formatDuration(truck.queuedAt)}).
        </p>
      )}
    </>
  );
}

interface SheetProps {
  truck: QueuedTruck | null;
  onClose: () => void;
  onDone: (entry: TruckEntry) => void;
}

export function EnterTruckSheet({ truck, onClose, onDone }: SheetProps) {
  const [sigError, setSigError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Is a signature for this plate already on file? null = still asking.
  const [onFile, setOnFile] = useState<boolean | null>(null);
  const [resign, setResign] = useState(false); // sign again instead of using the one on file
  const pad = useRef<SignaturePadHandle>(null);
  const plate = truck?.plate;

  useEffect(() => {
    setSigError(null);
    setError(null);
    setBusy(false);
    setResign(false);
    setOnFile(null);
    if (!plate) return;
    let current = true;
    truckService
      .lookup(plate)
      .then((found) => {
        if (!current) return;
        setOnFile("truck" in found ? found.truck.has_signature : false);
      })
      .catch(() => current && setOnFile(false)); // can't tell: show the pad, which always works
    return () => {
      current = false;
    };
  }, [truck?.entryId, plate]);

  const usePad = onFile === false || resign;

  async function submit() {
    if (!truck) return;
    const read = usePad ? readPad(pad.current, SIGNATURE_MAX_BYTES) : { png: null };
    const problem = "error" in read ? read.error : usePad && !read.png ? "Ask the driver to sign." : null;
    setSigError(problem);
    if ("error" in read || problem) return;
    setError(null);
    setBusy(true);
    try {
      onDone(await truckService.enter(truck.entryId, read.png));
    } catch (e) {
      if (hasCode(e, ErrorCode.InvalidSignature) && !usePad) {
        setOnFile(false); // nothing usable on file after all: the driver signs now
        setError("There is no signature on file. Ask the driver to sign.");
      } else {
        setError(errorMessage(e));
      }
      setBusy(false);
    }
  }

  return (
    <Modal open={truck !== null} title="Let truck in" onClose={onClose} dismissible={!busy} sheet>
      {truck && (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <Who truck={truck} />
          {onFile === null && <Spinner label="Checking for a signature on file" />}
          {onFile === true && !resign && (
            <div className="sig-onfile">
              <span className="field__label">Driver's signature</span>
              <p>
                <strong>Signature on file.</strong> The driver does not need to sign again.
              </p>
              <div>
                <Button variant="secondary" size="sm" onClick={() => setResign(true)} disabled={busy}>
                  Sign again instead
                </Button>
              </div>
            </div>
          )}
          {usePad && (
            <div className="field">
              <span className="field__label">Driver signs to enter</span>
              <SignaturePad ref={pad} disabled={busy} invalid={Boolean(sigError)} hint="Sign here to enter" />
              {sigError && (
                <p className="field__error" role="alert">
                  {sigError}
                </p>
              )}
              {onFile === true && (
                <div>
                  <Button variant="ghost" size="sm" onClick={() => setResign(false)} disabled={busy}>
                    Use the signature on file
                  </Button>
                </div>
              )}
            </div>
          )}
          {error && <Banner tone="error">{error}</Banner>}
          <div className="modal__footer">
            <Button variant="ghost" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" variant="dark" loading={busy} disabled={onFile === null}>
              Let truck in
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export function LeaveQueueSheet({ truck, onClose, onDone }: SheetProps) {
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setReason("");
    setReasonError(null);
    setError(null);
    setBusy(false);
  }, [truck?.entryId]);

  async function submit() {
    if (!truck) return;
    const problem = truckService.leaveReasonError(reason);
    setReasonError(problem);
    if (problem) return;
    setError(null);
    setBusy(true);
    try {
      onDone(await truckService.leaveQueue(truck.entryId, reason));
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  return (
    <Modal open={truck !== null} title="Truck left the queue" onClose={onClose} dismissible={!busy} sheet>
      {truck && (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <Who truck={truck} />
          <TextField
            label="Why did it leave?"
            hint="For example: no CNG left, driver got tired of waiting."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            error={reasonError}
            maxLength={truckService.LEAVE_REASON_MAX}
            autoComplete="off"
            disabled={busy}
          />
          {error && <Banner tone="error">{error}</Banner>}
          <div className="modal__footer">
            <Button variant="ghost" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" variant="dark" loading={busy}>
              Mark as left
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
