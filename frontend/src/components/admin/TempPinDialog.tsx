// frontend/src/components/admin/TempPinDialog.tsx
// The server shows a temporary PIN exactly once. This dialog is the only place it
// is held, in component state, and it is gone when the dialog closes.
import { useState } from "react";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { PinReveal } from "@/services/adminService";

export function TempPinDialog({ reveal, onClose }: { reveal: PinReveal | null; onClose: () => void }) {
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);

  async function copy() {
    if (!reveal) return;
    try {
      await navigator.clipboard.writeText(reveal.tempPin);
      setCopied("yes");
    } catch {
      setCopied("no"); // clipboard needs https or localhost
    }
  }

  function close() {
    setCopied(null);
    onClose();
  }

  return (
    <Modal
      open={reveal !== null}
      title={reveal?.title ?? ""}
      onClose={close}
      dismissible={false}
      footer={<Button onClick={close}>I've given it to them</Button>}
    >
      {reveal && (
        <div className="stack">
          <dl className="facts">
            <dt>Name</dt>
            <dd>{reveal.fullName}</dd>
            <dt>Officer code</dt>
            <dd>{reveal.officerCode}</dd>
            <dt>Facility</dt>
            <dd>{reveal.facilityCode ?? "None (global account)"}</dd>
          </dl>

          <div className="pin-reveal" aria-label="Temporary PIN">
            {reveal.tempPin}
          </div>

          <div className="row">
            <Button variant="secondary" size="sm" onClick={() => void copy()}>
              Copy PIN
            </Button>
            {copied === "yes" && <span className="muted">Copied.</span>}
            {copied === "no" && <span className="muted">Couldn't copy. Write it down.</span>}
          </div>

          <Banner tone="warn" title="This is the only time the PIN is shown">
            Give it to {reveal.fullName} in person. They will set their own PIN the first time they log in.
          </Banner>
        </div>
      )}
    </Modal>
  );
}
