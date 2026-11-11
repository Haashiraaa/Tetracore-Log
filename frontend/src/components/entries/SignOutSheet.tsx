// frontend/src/components/entries/SignOutSheet.tsx
// Sign anyone out: time in, how long they were inside, their signature, and for
// trucks the gas they bought. Slides up from the bottom on phones.
import { useEffect, useRef, useState } from "react";
import type { AnyEntry } from "@/api/schemas";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { formatDuration, formatTime } from "@/lib/dates";
import { LOG_LABEL, type LogKind } from "@/models";
import * as entryService from "@/services/entryService";

export interface SignOutTarget {
  kind: LogKind;
  entryId: string;
  plate: string | null;
  name: string;
  /** null when only a lookup result is in hand (the gate's "already inside" case). */
  signedInAt: string | null;
}

/** `cameInAt` overrides the time inside is counted from (a truck counts from entering). */
export function signOutTargetOf(kind: LogKind, entry: AnyEntry, cameInAt?: string): SignOutTarget {
  const face = entryService.faceOf(entry);
  return { kind, entryId: entry.id, plate: face.plate, name: face.name, signedInAt: cameInAt ?? entry.signed_in_at };
}

interface SignOutSheetProps {
  target: SignOutTarget | null;
  onClose: () => void;
  onDone: (entry: AnyEntry) => void;
}

const SIGNER: Record<LogKind, string> = { trucks: "Driver", visitors: "Visitor", staff: "Staff member" };

export function SignOutSheet({ target, onClose, onDone }: SignOutSheetProps) {
  const [scm, setScm] = useState("");
  const [scmError, setScmError] = useState<string | null>(null);
  const [sigError, setSigError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pad = useRef<SignaturePadHandle>(null);

  // fresh form every time the sheet opens for someone
  useEffect(() => {
    setScm("");
    setScmError(null);
    setSigError(null);
    setError(null);
    setBusy(false);
  }, [target?.entryId]);

  async function submit() {
    if (!target) return;
    const parsed = target.kind === "trucks" ? entryService.parseScm(scm) : { value: null };
    const read = readPad(pad.current, SIGNATURE_MAX_BYTES);
    const signatureProblem = "error" in read ? read.error : entryService.signatureError(read.png);
    setScmError("error" in parsed ? parsed.error : null);
    setSigError(signatureProblem);
    if ("error" in parsed || "error" in read || signatureProblem || !read.png) return;

    setError(null);
    setBusy(true);
    try {
      onDone(await entryService.signOut(target.kind, target.entryId, { signature: read.png, scm: parsed.value }));
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  const one = target ? LOG_LABEL[target.kind].one : "";

  return (
    <Modal open={target !== null} title={`Sign ${one} out`} onClose={onClose} dismissible={!busy} sheet>
      {target && (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div className="row row--between">
            {target.plate ? <PlateChip plate={target.plate} large /> : <span className="entry-name">{target.name}</span>}
            {target.plate && <span className="muted">{target.name}</span>}
          </div>

          {target.signedInAt && (
            <dl className="strip">
              <div className="strip__cell">
                <dt>In</dt>
                <dd>{formatTime(target.signedInAt)}</dd>
              </div>
              <div className="strip__cell">
                <dt>Out</dt>
                <dd>{formatTime(new Date().toISOString())}</dd>
              </div>
              <div className="strip__cell strip__cell--key">
                <dt>Inside for</dt>
                <dd>{formatDuration(target.signedInAt)}</dd>
              </div>
            </dl>
          )}

          {target.kind === "trucks" && (
            <TextField
              label="Gas bought (SCM)"
              hint="Leave blank if it isn't known."
              inputMode="decimal"
              autoComplete="off"
              className="input--code"
              value={scm}
              onChange={(e) => setScm(e.target.value)}
              error={scmError}
              disabled={busy}
            />
          )}

          <div className="field">
            <span className="field__label">{SIGNER[target.kind]} signs out</span>
            <SignaturePad ref={pad} disabled={busy} invalid={Boolean(sigError)} hint="Sign here to leave" />
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
              Sign {one} out
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
