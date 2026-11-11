// frontend/src/pages/LoginPage.tsx
import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { homePathFor } from "@/auth/permissions";
import { Banner } from "@/components/ui/Banner";
import { BootScreen } from "@/components/ui/BootScreen";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { errorMessage } from "@/exceptions/errors";
import * as authService from "@/services/authService";

export default function LoginPage() {
  const { status, profile, login, notice, dismissNotice } = useAuth();
  const location = useLocation();

  const [facility, setFacility] = useState("");
  const [officer, setOfficer] = useState("");
  const [pin, setPin] = useState("");
  const [fieldErrors, setFieldErrors] = useState<ReturnType<typeof authService.validateLogin>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "booting" || status === "unreachable") return <BootScreen />;
  if (status === "authenticated" && profile) {
    const from = (location.state as { from?: string } | null)?.from;
    const target = profile.must_change_pin
      ? "/change-pin"
      : from && from !== "/login"
        ? from
        : homePathFor(profile);
    return <Navigate to={target} replace />;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const input = { facilityCode: facility, officerCode: officer, pin };
    const errors = authService.validateLogin(input);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setBusy(true);
    setError(null);
    dismissNotice();
    try {
      await login(input);
    } catch (err) {
      setError(errorMessage(err));
      setPin("");
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
        <h1>Log in</h1>

        {notice && <Banner tone="info">{notice}</Banner>}
        {error && <Banner tone="error">{error}</Banner>}

        <TextField
          label="Facility code"
          hint="Leave blank for CSO and admin accounts."
          value={facility}
          onChange={(e) => setFacility(e.target.value.toUpperCase())}
          autoCapitalize="characters"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          className="input--code"
        />
        <TextField
          label="Officer code"
          value={officer}
          onChange={(e) => setOfficer(e.target.value.toUpperCase())}
          error={fieldErrors.officerCode}
          autoCapitalize="characters"
          autoComplete="username"
          autoCorrect="off"
          spellCheck={false}
          className="input--code"
        />
        <TextField
          label="PIN"
          type="password"
          inputMode="numeric"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          error={fieldErrors.pin}
          autoComplete="current-password"
        />

        <Button type="submit" block loading={busy}>
          Log in
        </Button>
      </form>
    </main>
  );
}
