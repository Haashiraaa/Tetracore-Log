// frontend/src/components/notifications/PushSwitch.tsx
// Turn browser push on or off for THIS browser. Hidden when the server has no push keys.
import { useCallback, useEffect, useState } from "react";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { errorMessage } from "@/exceptions/errors";
import { disablePush, enablePush, loadPushState, sendTestPush, type PushState } from "@/services/notificationService";

export function PushSwitch() {
  const [state, setState] = useState<PushState | null>(null);
  const [publicKey, setPublicKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<{ ok: boolean; message: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const loaded = await loadPushState();
      setState(loaded.state);
      setPublicKey(loaded.publicKey);
    } catch {
      setState(null); // could not ask the server: show nothing rather than a wrong switch
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      if (state === "on") await disablePush();
      else if (publicKey) await enablePush(publicKey);
      await load();
    } catch (e) {
      setError(e instanceof Error && !("code" in e) ? e.message : errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      setNote(await sendTestPush());
    } catch (e) {
      setError(e instanceof Error && !("code" in e) ? e.message : errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (state === null || state === "unconfigured") return null;

  return (
    <section className="card push" aria-label="Browser notifications">
      <div className="push__text">
        <strong>Notifications on this device</strong>
        {state === "unsupported" && (
          <p className="muted">
            This browser cannot show them here. They need a secure (https) address and a browser that supports push.
          </p>
        )}
        {state === "denied" && (
          <p className="muted">Blocked for this site. Allow notifications in the browser settings to turn them on.</p>
        )}
        {state === "off" && <p className="muted">Get every event as a notification, even when the app is closed.</p>}
        {state === "on" && <p className="muted">On. Every event reaches this device.</p>}
      </div>
      {state === "on" && (
        <Button variant="secondary" loading={busy} onClick={() => void test()}>
          Send test notification
        </Button>
      )}
      {(state === "off" || state === "on") && (
        <Button variant={state === "on" ? "secondary" : "primary"} loading={busy} onClick={() => void toggle()}>
          {state === "on" ? "Turn off" : "Turn on"}
        </Button>
      )}
      {note && <Banner tone={note.ok ? "success" : "error"}>{note.message}</Banner>}
      {error && <Banner tone="error">{error}</Banner>}
    </section>
  );
}
