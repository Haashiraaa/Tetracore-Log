// frontend/src/components/entries/TruckQueueSheets.tsx
// The two things that can happen to a truck waiting in the queue:
//   EnterTruckSheet      let it in: the driver signs on the way in
//   LeaveQueueSheet      it gave up and left: say why (free text)
import { useEffect, useRef, useState } from "react";
import type { TruckEntry } from "@/api/schemas";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
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
  const pad = useRef<SignaturePadHandle>(null);

  useEffect(() => {
    setSigError(null);
    setError(null);
    setBusy(false);
  }, [truck?.entryId]);

  async function submit() {
    if (!truck) return;
    const read = readPad(pad.current, SIGNATURE_MAX_BYTES);
    const problem = "error" in read ? read.error : read.png ? null : "Ask the driver to sign.";
    setSigError(problem);
    if ("error" in read || !read.png) return;
    setError(null);
    setBusy(true);
    try {
      onDone(await truckService.enter(truck.entryId, read.png));
    } catch (e) {
      setError(errorMessage(e));
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
          <div className="field">
            <span className="field__label">Driver signs to enter</span>
            <SignaturePad ref={pad} disabled={busy} invalid={Boolean(sigError)} hint="Sign here to enter" />
            {sigError && (
              <p className="field__error" role="alert">
                {sigError}
              </p>
            )}
          </div>
          {error && <Banner tone="error">{error}</Banner>}
          <div className="modal__footer">
            <Button variant="ghost" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" variant="dark" loading={busy}>
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
