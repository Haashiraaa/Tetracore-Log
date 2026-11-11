// frontend/src/pages/ChangePinPage.tsx
// Used twice: forced after a temporary PIN (first login or admin reset), and
// voluntarily from the account menu. A wrong current PIN is an ordinary error
// here: it must not log the person out.
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, useOfficer } from "@/auth/AuthContext";
import { homePathFor } from "@/auth/permissions";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { errorMessage } from "@/exceptions/errors";
import * as authService from "@/services/authService";

export default function ChangePinPage() {
  const profile = useOfficer();
  const { reloadProfile, logout } = useAuth();
  const navigate = useNavigate();
  const forced = profile.must_change_pin;

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<ReturnType<typeof authService.validateNewPin>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errors = authService.validateNewPin(current, next, confirm);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setBusy(true);
    setError(null);
    try {
      await authService.changePin(current, next);
      const updated = await reloadProfile();
      navigate(homePathFor(updated), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <form className="auth__card stack" onSubmit={submit} noValidate>
        <div className="brand brand--static">
          <span className="brand__mark" aria-hidden="true" />
          <span className="brand__name">Tetracore Log</span>
        </div>

        <h1>{forced ? "Set your new PIN" : "Change PIN"}</h1>

        {forced && (
          <Banner tone="info" title={`You're signed in as ${profile.full_name}`}>
            {profile.facility_name ? `${profile.facility_name}, ` : ""}
            {profile.officer_code}. If that isn't you,{" "}
            <button type="button" className="linklike" onClick={() => void logout()}>
              log out
            </button>
            .
          </Banner>
        )}
        {forced ? (
          <p className="muted">
            You logged in with a temporary PIN. Choose one you'll remember: 6 to 10 digits, not a run like 123456.
          </p>
        ) : (
          <p className="muted">Changing your PIN signs you out on your other devices.</p>
        )}

        {error && <Banner tone="error">{error}</Banner>}

        <TextField
          label={forced ? "Temporary PIN" : "Current PIN"}
          type="password"
          inputMode="numeric"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          error={fieldErrors.current}
          autoComplete="current-password"
        />
        <TextField
          label="New PIN"
          type="password"
          inputMode="numeric"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          error={fieldErrors.next}
          autoComplete="new-password"
        />
        <TextField
          label="Repeat new PIN"
          type="password"
          inputMode="numeric"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={fieldErrors.confirm}
          autoComplete="new-password"
        />

        <div className="row">
          <Button type="submit" loading={busy}>
            Save new PIN
          </Button>
          {!forced && (
            <Link to={homePathFor(profile)} className="btn btn--ghost">
              Cancel
            </Link>
          )}
        </div>
      </form>
    </main>
  );
}
