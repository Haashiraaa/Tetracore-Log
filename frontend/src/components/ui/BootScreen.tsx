// frontend/src/components/ui/BootScreen.tsx
// Shown while the saved session is being checked, or when the server can't be reached.
import { useAuth } from "@/auth/AuthContext";
import { Banner } from "./Banner";
import { Button } from "./Button";
import { Spinner } from "./Spinner";

export function BootScreen() {
  const { status, retryBoot, logout } = useAuth();

  if (status === "unreachable") {
    return (
      <main className="auth">
        <div className="auth__card stack">
          <h1>Can't reach the server</h1>
          <Banner tone="warn">
            Check that the backend is running and that this device is online. Your login is kept.
          </Banner>
          <div className="row">
            <Button onClick={retryBoot}>Try again</Button>
            <Button variant="ghost" onClick={() => void logout()}>
              Log out
            </Button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="auth auth--center">
      <Spinner label="Checking your login" />
    </main>
  );
}
