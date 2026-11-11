// frontend/src/pages/gate/StaffInPage.tsx
// Sign a staff member in: their name and their signature. The time is the server's.
import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { formatTime } from "@/lib/dates";
import { uuid } from "@/lib/ids";
import * as staffService from "@/services/staffService";

export default function StaffInPage() {
  const [entryId, setEntryId] = useState(uuid); // one id per blank form, reused on retry
  const [fullName, setFullName] = useState("");
  const [errors, setErrors] = useState<{ fullName?: string; signature?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pad = useRef<SignaturePadHandle>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const read = readPad(pad.current, SIGNATURE_MAX_BYTES);
    if ("error" in read) {
      setErrors({ signature: read.error });
      return;
    }
    const built = staffService.buildSignInRequest(entryId, fullName, read.png);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }

    setErrors({});
    setError(null);
    setOutcome(null);
    setBusy(true);
    try {
      const entry = await staffService.signIn(built.value);
      setOutcome(`${entry.full_name} signed in at ${formatTime(entry.signed_in_at)}.`);
      setFullName("");
      setEntryId(uuid());
      pad.current?.clear();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page--narrow stack stack--lg">
      <PageHeader title="Staff in" back={{ to: "/gate", label: "Back to gate" }} />

      {outcome && (
        <Banner tone="success">
          {outcome} <Link to="/inside">See who is inside</Link>
        </Banner>
      )}
      {error && <Banner tone="error">{error}</Banner>}

      <form className="stack" onSubmit={submit} noValidate>
        <TextField
          label="Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={errors.fullName}
          autoComplete="off"
          className="input--lead"
          disabled={busy}
        />
        <div className="field">
          <span className="field__label">Staff member signs in</span>
          <SignaturePad ref={pad} disabled={busy} invalid={Boolean(errors.signature)} hint="Sign here" />
          {errors.signature && (
            <p className="field__error" role="alert">
              {errors.signature}
            </p>
          )}
        </div>
        <Button type="submit" block className="btn--lead" loading={busy}>
          Sign staff in
        </Button>
      </form>
    </div>
  );
}
