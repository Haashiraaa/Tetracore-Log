// frontend/src/pages/gate/TruckSignInForm.tsx
// Confirm (returning truck) or enter (new truck) the driver's details, then either put the
// truck in the queue (no signature yet) or let it in now (the driver signs).
//
// `entryId` is generated ONCE when the form opens (by TruckInPage) and reused on every
// retry. If the first request reached the server but the reply was lost, the retry
// returns the stored entry instead of creating a duplicate.
import { useRef, useState, type FormEvent } from "react";
import type { TruckEntry } from "@/api/schemas";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { PlateChip } from "@/components/ui/PlateChip";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import * as truckService from "@/services/truckService";

export interface SignInInitial {
  driverName: string;
  driverPhone: string;
  company: string;
}

interface SignInFormProps {
  plate: string;
  mode: "new" | "returning";
  entryId: string;
  initial: SignInInitial;
  /** A driver's signature for this plate is on file, so letting it in needs no signing. */
  hasSignature?: boolean;
  onDone: (entry: TruckEntry) => void;
  onCancel: () => void;
  onAlreadyInside: () => void;
}

export function TruckSignInForm({
  plate,
  mode,
  entryId,
  initial,
  hasSignature = false,
  onDone,
  onCancel,
  onAlreadyInside,
}: SignInFormProps) {
  const [driverName, setDriverName] = useState(initial.driverName);
  const [driverPhone, setDriverPhone] = useState(initial.driverPhone);
  const [company, setCompany] = useState(initial.company);
  const [errors, setErrors] = useState<{ driverName?: string; driverPhone?: string; signature?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [letIn, setLetIn] = useState(false);
  const [resign, setResign] = useState(false); // sign again even though one is on file
  const pad = useRef<SignaturePadHandle>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();

    const onFile = hasSignature && !resign;
    const read = letIn && !onFile ? readPad(pad.current, SIGNATURE_MAX_BYTES) : { png: null };
    if ("error" in read) {
      setErrors({ signature: read.error });
      return;
    }

    const built = truckService.buildSignInRequest(
      entryId,
      { plate, driverName, driverPhone, company },
      { enterNow: letIn, signaturePng: read.png, signatureOnFile: onFile },
    );
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }

    setErrors({});
    setError(null);
    setBusy(true);
    try {
      onDone(await truckService.signIn(built.value));
    } catch (err) {
      if (hasCode(err, ErrorCode.TruckAlreadyInside)) {
        onAlreadyInside();
        return;
      }
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={submit} noValidate>
      <div className="row row--between">
        <PlateChip plate={plate} large />
        <span className="muted">{mode === "returning" ? "Returning truck" : "New truck"}</span>
      </div>

      <p className="note-dark" role="status">
        {mode === "returning" ? (
          <>
            <strong>Been here before.</strong> Details filled in. Check them with the driver.
          </>
        ) : (
          <>
            <strong>New truck.</strong> Enter the driver's details. They are saved for the next visit.
          </>
        )}
      </p>

      {error && <Banner tone="error">{error}</Banner>}

      <div className="form-grid">
        <TextField
          label="Full name"
          value={driverName}
          onChange={(e) => setDriverName(e.target.value)}
          error={errors.driverName}
          autoComplete="off"
          disabled={busy}
        />
        <TextField
          label="Phone number"
          hint="Optional. Nigerian: 0803 123 4567. Another country: + and the country code."
          inputMode="tel"
          value={driverPhone}
          onChange={(e) => setDriverPhone(e.target.value)}
          error={errors.driverPhone}
          autoComplete="off"
          disabled={busy}
        />
        <TextField
          label="Company"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          autoComplete="off"
          disabled={busy}
        />
      </div>

      <label className="check">
        <input type="checkbox" checked={letIn} onChange={(e) => setLetIn(e.target.checked)} disabled={busy} />
        Let it in now (the driver signs)
      </label>

      {letIn && hasSignature && !resign && (
        <div className="sig-onfile">
          <span className="field__label">Driver's signature</span>
          <p>
            <strong>Signature on file.</strong> The driver does not need to sign again; it is used for entering and
            for signing out.
          </p>
          <div>
            <Button variant="secondary" size="sm" onClick={() => setResign(true)} disabled={busy}>
              Sign again instead
            </Button>
          </div>
        </div>
      )}

      {letIn && !(hasSignature && !resign) && (
        <div className="field">
          <span className="field__label">Driver's signature</span>
          <SignaturePad ref={pad} disabled={busy} invalid={Boolean(errors.signature)} hint="Driver signs here" />
          {errors.signature && (
            <p className="field__error" role="alert">
              {errors.signature}
            </p>
          )}
          {hasSignature && (
            <div>
              <Button variant="ghost" size="sm" onClick={() => setResign(false)} disabled={busy}>
                Use the signature on file
              </Button>
            </div>
          )}
        </div>
      )}

      <p className="muted">
        {letIn
          ? "Gas bought is recorded when the truck signs out."
          : "It waits in the queue until you let it in. The driver signs then."}
      </p>

      <div className="row">
        <Button type="submit" className="btn--lead" loading={busy}>
          {letIn ? "Sign truck in" : "Add to queue"}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
