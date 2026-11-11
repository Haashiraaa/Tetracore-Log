// frontend/src/components/trucks/SignOutDialog.tsx
import { useEffect, useState } from "react";
import type { TruckEntry } from "@/api/schemas";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlateChip } from "@/components/ui/PlateChip";
import { TextField } from "@/components/ui/TextField";
import { errorMessage } from "@/exceptions/errors";
import * as truckService from "@/services/truckService";

export interface SignOutTarget {
  entryId: string;
  plate: string;
}

interface SignOutDialogProps {
  target: SignOutTarget | null;
  onClose: () => void;
  onDone: (entry: TruckEntry) => void;
}

export function SignOutDialog({ target, onClose, onDone }: SignOutDialogProps) {
  const [scm, setScm] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // fresh form every time the dialog opens for a truck
  useEffect(() => {
    setScm("");
    setFieldError(null);
    setError(null);
    setBusy(false);
  }, [target?.entryId]);

  async function submit() {
    if (!target) return;
    const parsed = truckService.parseScm(scm);
    if ("error" in parsed) {
      setFieldError(parsed.error);
      return;
    }
    setFieldError(null);
    setError(null);
    setBusy(true);
    try {
      onDone(await truckService.signOut(target.entryId, parsed.value));
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  return (
    <Modal
      open={target !== null}
      title="Sign out truck"
      onClose={onClose}
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Sign out truck
          </Button>
        </>
      }
    >
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {target && <PlateChip plate={target.plate} large />}
        <TextField
          label="Gas bought (SCM)"
          hint="Optional. Leave blank if it isn't known yet."
          inputMode="decimal"
          autoComplete="off"
          value={scm}
          onChange={(e) => setScm(e.target.value)}
          error={fieldError}
        />
        {error && <Banner tone="error">{error}</Banner>}
      </form>
    </Modal>
  );
}
