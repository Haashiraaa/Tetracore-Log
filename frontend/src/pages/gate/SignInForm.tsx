// frontend/src/pages/gate/SignInForm.tsx
// Confirm (returning truck) or enter (new truck) the driver's details, capture a signature, sign in.
//
// `entryId` is generated ONCE when the form opens (by GatePage) and reused on every
// retry. If the first request reached the server but the reply was lost, the retry
// returns the stored entry instead of creating a duplicate.
import { useRef, useState, type FormEvent } from "react";
import type { TruckEntry } from "@/api/schemas";
import { SignaturePad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
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
  onDone: (entry: TruckEntry) => void;
  onCancel: () => void;
  onAlreadyInside: () => void;
}

export function SignInForm({ plate, mode, entryId, initial, onDone, onCancel, onAlreadyInside }: SignInFormProps) {
  const [driverName, setDriverName] = useState(initial.driverName);
  const [driverPhone, setDriverPhone] = useState(initial.driverPhone);
  const [company, setCompany] = useState(initial.company);
  const [errors, setErrors] = useState<{ driverName?: string; signature?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pad = useRef<SignaturePadHandle>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();

    let png: string | null = null;
    if (pad.current && !pad.current.isEmpty()) {
      png = pad.current.toPng(SIGNATURE_MAX_BYTES);
      if (!png) {
        setErrors({ signature: "That signature is too detailed to save. Clear it and sign again." });
        return;
      }
    }

    const built = truckService.buildSignInRequest(
      entryId,
      { plate, driverName, driverPhone, company },
      png,
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

      <p className="muted">
        {mode === "returning"
          ? "Confirm the driver's details with them. Correct anything that changed."
          : "Enter the driver's details. They are saved for the next visit."}
      </p>

      {error && <Banner tone="error">{error}</Banner>}

      <TextField
        label="Driver's full name"
        value={driverName}
        onChange={(e) => setDriverName(e.target.value)}
        error={errors.driverName}
        autoComplete="off"
        disabled={busy}
      />
      <TextField
        label="Driver's phone"
        inputMode="tel"
        value={driverPhone}
        onChange={(e) => setDriverPhone(e.target.value)}
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

      <div className="field">
        <span className="field__label">Driver's signature</span>
        <SignaturePad ref={pad} disabled={busy} invalid={Boolean(errors.signature)} />
        {errors.signature && (
          <p className="field__error" role="alert">
            {errors.signature}
          </p>
        )}
      </div>

      <p className="muted">Gas bought is recorded when the truck signs out.</p>

      <div className="row">
        <Button type="submit" loading={busy}>
          Sign in truck
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
