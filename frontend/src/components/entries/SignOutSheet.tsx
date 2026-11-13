// frontend/src/components/entries/SignOutSheet.tsx
// Sign anyone out: time in, how long they were inside, their signature, and for
// trucks the gas they bought. Slides up from the bottom on phones.
// Visitors and staff already signed on the way in, so by default that signature is used
// (shown here) and nobody has to be present; "Let them sign instead" opens the pad.
import { useEffect, useRef, useState } from "react";
import type { AnyEntry } from "@/api/schemas";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import { useSignature } from "@/hooks/useSignature";
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
  const [redraw, setRedraw] = useState(false); // visitors/staff: sign again instead of reusing
  const pad = useRef<SignaturePadHandle>(null);
  const reusable = target !== null && target.kind !== "trucks";
  const onFile = useSignature(target?.kind ?? "visitors", target?.entryId ?? "", reusable, "in");
  // No sign-in signature to reuse (an old line): they have to sign now.
  const mustSign = !reusable || redraw || onFile.kind === "none" || onFile.kind === "error";

  // fresh form every time the sheet opens for someone
  useEffect(() => {
    setScm("");
    setScmError(null);
    setSigError(null);
    setError(null);
    setBusy(false);
    setRedraw(false);
  }, [target?.entryId]);

  async function submit() {
    if (!target) return;
    const parsed = target.kind === "trucks" ? entryService.parseScm(scm) : { value: null };
    // Reusing the sign-in signature: send none, the server copies it.
    const read = mustSign ? readPad(pad.current, SIGNATURE_MAX_BYTES) : { png: null };
    const signatureProblem = "error" in read ? read.error : mustSign ? entryService.signatureError(read.png) : null;
    setScmError("error" in parsed ? parsed.error : null);
    setSigError(signatureProblem);
    if ("error" in parsed || "error" in read || signatureProblem) return;

    setError(null);
    setBusy(true);
    try {
      onDone(await entryService.signOut(target.kind, target.entryId, { signature: read.png, scm: parsed.value }));
    } catch (e) {
      if (hasCode(e, ErrorCode.InvalidSignature) && !mustSign) {
        setRedraw(true); // nothing usable on file after all: let them sign now
        setError("There is no signature on file to reuse. Ask them to sign.");
      } else {
        setError(errorMessage(e));
      }
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

          {mustSign ? (
            <div className="field">
              <span className="field__label">{SIGNER[target.kind]} signs out</span>
              <SignaturePad ref={pad} disabled={busy} invalid={Boolean(sigError)} hint="Sign here to leave" />
              {sigError && (
                <p className="field__error" role="alert">
                  {sigError}
                </p>
              )}
              {reusable && onFile.kind === "ready" && (
                <div>
                  <Button variant="ghost" size="sm" onClick={() => setRedraw(false)} disabled={busy}>
                    Use their sign-in signature
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="sig-onfile">
              <span className="field__label">{SIGNER[target.kind]} signature from sign-in</span>
              {onFile.kind === "loading" && <Spinner label="Loading signature" />}
              {onFile.kind === "ready" && <img className="sig-view" src={onFile.url} alt="Signature given at sign-in" />}
              <p className="muted">Used to sign them out, so they do not need to be here.</p>
              <div>
                <Button variant="secondary" size="sm" onClick={() => setRedraw(true)} disabled={busy}>
                  Let them sign instead
                </Button>
              </div>
            </div>
          )}

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
