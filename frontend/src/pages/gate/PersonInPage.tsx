// frontend/src/pages/gate/PersonInPage.tsx
// Sign a visitor or a staff member in. Same steps as a truck, with the phone number
// where the plate is:
//   type the phone  -> never seen here: blank form
//                   -> seen before: name (and company / capacity) filled in, to CONFIRM
//                   -> inside right now: offer sign-out instead
// `entryId` is made once per form open and reused on retry, so a retry after a lost reply
// returns the stored entry instead of creating a duplicate.
import { useCallback, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { AnyEntry, StaffLookup, VisitorLookup } from "@/api/schemas";
import { SignOutSheet, type SignOutTarget } from "@/components/entries/SignOutSheet";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { TextField } from "@/components/ui/TextField";
import { SIGNATURE_MAX_BYTES } from "@/config/env";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import { formatTime } from "@/lib/dates";
import { uuid } from "@/lib/ids";
import { PHONE_ERROR, cleanPhone } from "@/lib/people";
import * as staffService from "@/services/staffService";
import * as visitorService from "@/services/visitorService";
import { PURPOSE_PICKS } from "@/services/visitorService";

type PersonKind = "visitors" | "staff";

interface Fields {
  fullName: string;
  company: string;
  purpose: string;
  itemsReceived: string;
  capacity: string;
}

const BLANK: Fields = { fullName: "", company: "", purpose: "", itemsReceived: "", capacity: "" };

type Stage =
  | { kind: "idle" }
  | { kind: "looking" }
  | { kind: "form"; returning: boolean; phone: string; entryId: string }
  | { kind: "inside"; phone: string; name: string; entryId: string };

const COPY = {
  visitors: { title: "Visitor in", who: "visitor", button: "Sign visitor in", signs: "Visitor signs in" },
  staff: { title: "Staff in", who: "staff member", button: "Sign staff in", signs: "Staff member signs in" },
} as const;

async function lookUp(kind: PersonKind, phone: string): Promise<VisitorLookup | StaffLookup | null> {
  return kind === "visitors" ? visitorService.lookup(phone) : staffService.lookup(phone);
}

export default function PersonInPage({ kind }: { kind: PersonKind }) {
  const copy = COPY[kind];
  const [phoneInput, setPhoneInput] = useState("");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>({ kind: "idle" });
  const [fields, setFields] = useState<Fields>(BLANK);
  const [errors, setErrors] = useState<{ fullName?: string; capacity?: string; signature?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [signOutTarget, setSignOutTarget] = useState<SignOutTarget | null>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const pad = useRef<SignaturePadHandle>(null);

  const set = (patch: Partial<Fields>) => setFields((f) => ({ ...f, ...patch }));

  const runLookup = useCallback(
    async (raw: string) => {
      const phone = cleanPhone(raw);
      if (!phone) {
        setPhoneError(PHONE_ERROR);
        return;
      }
      setPhoneError(null);
      setLookupError(null);
      setError(null);
      setErrors({});
      setStage({ kind: "looking" });
      try {
        const found = await lookUp(kind, phone);
        if (found?.open_entry_id) {
          setStage({ kind: "inside", phone, name: found.full_name, entryId: found.open_entry_id });
          return;
        }
        setFields(
          found
            ? {
                ...BLANK,
                fullName: found.full_name,
                company: "company" in found ? (found.company ?? "") : "",
                capacity: "capacity" in found ? (found.capacity ?? "") : "",
              }
            : BLANK,
        );
        setStage({ kind: "form", returning: found !== null, phone, entryId: uuid() });
      } catch (e) {
        setStage({ kind: "idle" });
        setLookupError(errorMessage(e));
      }
    },
    [kind],
  );

  function reset(message: string | null) {
    setStage({ kind: "idle" });
    setPhoneInput("");
    setPhoneError(null);
    setLookupError(null);
    setError(null);
    setErrors({});
    setFields(BLANK);
    setOutcome(message);
    phoneRef.current?.focus();
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (stage.kind !== "form") return;
    const read = readPad(pad.current, SIGNATURE_MAX_BYTES);
    if ("error" in read) {
      setErrors({ signature: read.error });
      return;
    }
    const built =
      kind === "visitors"
        ? visitorService.buildSignInRequest(stage.entryId, stage.phone, fields, read.png)
        : staffService.buildSignInRequest(stage.entryId, stage.phone, fields, read.png);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }

    setErrors({});
    setError(null);
    setBusy(true);
    try {
      const entry =
        kind === "visitors"
          ? await visitorService.signIn(built.value as Parameters<typeof visitorService.signIn>[0])
          : await staffService.signIn(built.value as Parameters<typeof staffService.signIn>[0]);
      reset(`${entry.full_name} signed in at ${formatTime(entry.signed_in_at)}.`);
    } catch (err) {
      if (hasCode(err, ErrorCode.AlreadyInside)) {
        void runLookup(stage.phone); // someone else just signed them in: show sign-out instead
        return;
      }
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function onSignedOut(entry: AnyEntry) {
    const name = signOutTarget?.name ?? "Signed out";
    setSignOutTarget(null);
    const at = entry.signed_out_at ? ` at ${formatTime(entry.signed_out_at)}` : "";
    reset(`${name} signed out${at}.`);
  }

  return (
    <div className="page page--form stack stack--lg">
      <PageHeader title={copy.title} back={{ to: "/gate", label: "Back to gate" }} />

      {outcome && (
        <Banner tone="success">
          {outcome} <Link to="/inside">See who is inside</Link>
        </Banner>
      )}

      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          setOutcome(null);
          void runLookup(phoneInput);
        }}
        noValidate
      >
        <div className="lookup">
          <TextField
            label="Phone number"
            ref={phoneRef}
            inputMode="tel"
            value={phoneInput}
            onChange={(e) => setPhoneInput(e.target.value)}
            error={phoneError}
            autoComplete="off"
            className="input--lead"
            disabled={stage.kind === "looking"}
          />
          <Button type="submit" variant="dark" loading={stage.kind === "looking"}>
            Look up {copy.who}
          </Button>
        </div>
        <p className="muted">We use the phone number to find a {copy.who} who has been here before.</p>
        {lookupError && <Banner tone="error">{lookupError}</Banner>}
      </form>

      {stage.kind === "form" && (
        <form key={stage.entryId} className="card stack" onSubmit={submit} noValidate>
          <div className="row row--between">
            <span className="mono cell-main">{stage.phone}</span>
            <Badge tone={stage.returning ? "grey" : "amber"}>{stage.returning ? "Been here before" : "New here"}</Badge>
          </div>
          <p className="note-dark" role="status">
            {stage.returning ? (
              <>
                <strong>Details filled in.</strong> Check them with the {copy.who}.
              </>
            ) : (
              <>
                <strong>New {copy.who}.</strong> Enter their details. They are remembered for next time.
              </>
            )}
          </p>
          {error && <Banner tone="error">{error}</Banner>}

          <div className="form-grid">
            <TextField
              label="Full name"
              value={fields.fullName}
              onChange={(e) => set({ fullName: e.target.value })}
              error={errors.fullName}
              autoComplete="off"
              disabled={busy}
            />
            {kind === "staff" ? (
              <TextField
                label="Capacity"
                hint="What they work as, for example Cashier or Attendant."
                value={fields.capacity}
                onChange={(e) => set({ capacity: e.target.value })}
                error={errors.capacity}
                autoComplete="off"
                disabled={busy}
              />
            ) : (
              <TextField
                label="Company name"
                value={fields.company}
                onChange={(e) => set({ company: e.target.value })}
                autoComplete="off"
                disabled={busy}
              />
            )}
          </div>

          {kind === "visitors" && (
            <div className="form-grid">
              <div className="stack stack--sm">
                <TextField
                  label="Purpose of visit"
                  value={fields.purpose}
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
                      aria-pressed={fields.purpose === pick}
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
                value={fields.itemsReceived}
                onChange={(e) => set({ itemsReceived: e.target.value })}
                autoComplete="off"
                disabled={busy}
              />
            </div>
          )}

          <div className="field">
            <span className="field__label">{copy.signs}</span>
            <SignaturePad ref={pad} disabled={busy} invalid={Boolean(errors.signature)} hint="Sign here" />
            {errors.signature && (
              <p className="field__error" role="alert">
                {errors.signature}
              </p>
            )}
          </div>

          <div className="row">
            <Button type="submit" className="btn--lead" loading={busy}>
              {copy.button}
            </Button>
            <Button type="button" variant="ghost" onClick={() => reset(null)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {stage.kind === "inside" && (
        <section className="card stack">
          <div className="row row--between">
            <span className="cell-main">{stage.name}</span>
            <Badge tone="amber">Inside</Badge>
          </div>
          <Banner tone="warn">This {copy.who} is already inside. Sign them out before signing them in again.</Banner>
          <div className="row">
            <Button
              onClick={() =>
                setSignOutTarget({ kind, entryId: stage.entryId, plate: null, name: stage.name, signedInAt: null })
              }
            >
              Sign out {copy.who}
            </Button>
            <Button variant="ghost" onClick={() => reset(null)}>
              Cancel
            </Button>
          </div>
        </section>
      )}

      <SignOutSheet target={signOutTarget} onClose={() => setSignOutTarget(null)} onDone={onSignedOut} />
    </div>
  );
}
