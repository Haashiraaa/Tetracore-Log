// frontend/src/pages/gate/VisitorInPage.tsx
// Sign a visitor in: full name, company name, purpose of visit, items received,
// phone number, and their signature. Only the name (and signature) is required.
//
// `entryId` is made once per blank form and reused on every retry, so a retry after
// a lost reply returns the stored entry instead of creating a duplicate.
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
import * as visitorService from "@/services/visitorService";
import { BLANK_VISITOR, PURPOSE_PICKS, type VisitorForm } from "@/services/visitorService";

export default function VisitorInPage() {
  const [entryId, setEntryId] = useState(uuid);
  const [form, setForm] = useState<VisitorForm>(BLANK_VISITOR);
  const [errors, setErrors] = useState<{ fullName?: string; signature?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pad = useRef<SignaturePadHandle>(null);

  const set = (patch: Partial<VisitorForm>) => setForm((f) => ({ ...f, ...patch }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const read = readPad(pad.current, SIGNATURE_MAX_BYTES);
    if ("error" in read) {
      setErrors({ signature: read.error });
      return;
    }
    const built = visitorService.buildSignInRequest(entryId, form, read.png);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }

    setErrors({});
    setError(null);
    setOutcome(null);
    setBusy(true);
    try {
      const entry = await visitorService.signIn(built.value);
      setOutcome(`${entry.full_name} signed in at ${formatTime(entry.signed_in_at)}.`);
      setForm(BLANK_VISITOR);
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
      <PageHeader title="Visitor in" back={{ to: "/gate", label: "Back to gate" }} />

      {outcome && (
        <Banner tone="success">
          {outcome} <Link to="/inside">See who is inside</Link>
        </Banner>
      )}
      {error && <Banner tone="error">{error}</Banner>}

      <form className="stack" onSubmit={submit} noValidate>
        <TextField
          label="Full name"
          value={form.fullName}
          onChange={(e) => set({ fullName: e.target.value })}
          error={errors.fullName}
          autoComplete="off"
          className="input--lead"
          disabled={busy}
        />
        <div className="form-grid">
          <TextField
            label="Company name"
            value={form.company}
            onChange={(e) => set({ company: e.target.value })}
            autoComplete="off"
            disabled={busy}
          />
          <TextField
            label="Phone number"
            inputMode="tel"
            value={form.phone}
            onChange={(e) => set({ phone: e.target.value })}
            autoComplete="off"
            disabled={busy}
          />
        </div>

        <div className="stack stack--sm">
          <TextField
            label="Purpose of visit"
            value={form.purpose}
            onChange={(e) => set({ purpose: e.target.value })}
            autoComplete="off"
            disabled={busy}
          />
          <div className="chips" role="group" aria-label="Common purposes">
            {PURPOSE_PICKS.map((pick) => (
              <button
                key={pick}
                type="button"
                className="chip"
                aria-pressed={form.purpose === pick}
                onClick={() => set({ purpose: pick })}
                disabled={busy}
              >
                {pick}
              </button>
            ))}
          </div>
        </div>

        <TextField
          label="Items received"
          value={form.itemsReceived}
          onChange={(e) => set({ itemsReceived: e.target.value })}
          autoComplete="off"
          disabled={busy}
        />

        <div className="field">
          <span className="field__label">Visitor signs in</span>
          <SignaturePad ref={pad} disabled={busy} invalid={Boolean(errors.signature)} hint="Visitor signs here" />
          {errors.signature && (
            <p className="field__error" role="alert">
              {errors.signature}
            </p>
          )}
        </div>

        <Button type="submit" block className="btn--lead" loading={busy}>
          Sign visitor in
        </Button>
      </form>
    </div>
  );
}
