// frontend/src/pages/gate/TruckInPage.tsx
// Look up a plate, then sign the truck in (or out).
//   new plate        -> blank form
//   known plate      -> form prefilled to CONFIRM
//   already queued   -> offer "let in" or "left the queue" instead
//   already inside   -> offer sign-out instead (the server would refuse a second sign-in)
import { useCallback, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { AnyEntry, TruckEntry, TruckLookup } from "@/api/schemas";
import { SignOutSheet, type SignOutTarget } from "@/components/entries/SignOutSheet";
import { Badge } from "@/components/ui/Badge";
import {
  EnterTruckSheet,
  LeaveQueueSheet,
  type QueuedTruck,
} from "@/components/entries/TruckQueueSheets";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PlateChip } from "@/components/ui/PlateChip";
import { errorMessage } from "@/exceptions/errors";
import { formatTime } from "@/lib/dates";
import { uuid } from "@/lib/ids";
import * as truckService from "@/services/truckService";
import { TruckSignInForm, type SignInInitial } from "./TruckSignInForm";

type Stage =
  | { kind: "idle" }
  | { kind: "looking" }
  | {
      kind: "form";
      mode: "new" | "returning";
      plate: string;
      entryId: string;
      initial: SignInInitial;
      hasSignature: boolean;
    }
  | { kind: "queued"; truck: TruckLookup }
  | { kind: "inside"; truck: TruckLookup };

const BLANK: SignInInitial = { driverName: "", driverPhone: "", company: "" };

function stageFor(result: truckService.LookupResult): Stage {
  switch (result.kind) {
    case "new":
      return { kind: "form", mode: "new", plate: result.plate, entryId: uuid(), initial: BLANK, hasSignature: false };
    case "returning":
      return {
        kind: "form",
        mode: "returning",
        plate: result.truck.plate_number,
        entryId: uuid(), // one id per form open, reused on retry
        hasSignature: result.truck.has_signature,
        initial: {
          driverName: result.truck.driver_name,
          driverPhone: result.truck.driver_phone ?? "",
          company: result.truck.company ?? "",
        },
      };
    case "queued":
      return { kind: "queued", truck: result.truck };
    case "inside":
      return { kind: "inside", truck: result.truck };
  }
}

export default function TruckInPage() {
  const [plateInput, setPlateInput] = useState("");
  const [plateError, setPlateError] = useState<string | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>({ kind: "idle" });
  const [outcome, setOutcome] = useState<string | null>(null);
  const [signOutTarget, setSignOutTarget] = useState<SignOutTarget | null>(null);
  const [enterTarget, setEnterTarget] = useState<QueuedTruck | null>(null);
  const [leaveTarget, setLeaveTarget] = useState<QueuedTruck | null>(null);
  const plateRef = useRef<HTMLInputElement>(null);

  const runLookup = useCallback(async (raw: string) => {
    const checked = truckService.validatePlate(raw);
    if ("error" in checked) {
      setPlateError(checked.error);
      return;
    }
    setPlateError(null);
    setLookupError(null);
    setStage({ kind: "looking" });
    try {
      setStage(stageFor(await truckService.lookup(checked.plate)));
    } catch (e) {
      setStage({ kind: "idle" });
      setLookupError(errorMessage(e));
    }
  }, []);

  function reset(message: string | null) {
    setStage({ kind: "idle" });
    setPlateInput("");
    setPlateError(null);
    setLookupError(null);
    setOutcome(message);
    plateRef.current?.focus();
  }

  function onSignedIn(entry: TruckEntry) {
    reset(
      entry.status === "queued"
        ? `${entry.plate_number} added to the queue at ${formatTime(entry.signed_in_at)}.`
        : `${entry.plate_number} signed in at ${formatTime(entry.signed_in_at)}.`,
    );
  }

  function onLetIn(entry: TruckEntry) {
    setEnterTarget(null);
    reset(`${entry.plate_number} let in at ${formatTime(entry.entered_at ?? entry.signed_in_at)}.`);
  }

  function onLeftQueue(entry: TruckEntry) {
    setLeaveTarget(null);
    reset(`${entry.plate_number} marked as left the queue.`);
  }

  function onSignedOut(entry: AnyEntry) {
    const plate = signOutTarget?.plate ?? "Truck";
    setSignOutTarget(null);
    const at = entry.signed_out_at ? ` at ${formatTime(entry.signed_out_at)}` : "";
    reset(`${plate} signed out${at}.`);
  }

  function submitLookup(e: FormEvent) {
    e.preventDefault();
    setOutcome(null);
    void runLookup(plateInput);
  }

  return (
    <div className="page page--form stack stack--lg">
      <PageHeader title="Truck in" back={{ to: "/gate", label: "Back to gate" }} />

      {outcome && (
        <Banner tone="success">
          {outcome} <Link to="/inside">See who is inside</Link>
        </Banner>
      )}

      <form className="stack" onSubmit={submitLookup} noValidate>
        <div className="field">
          <label className="field__label" htmlFor="plate">
            Number plate
          </label>
          <input
            id="plate"
            ref={plateRef}
            className="plate-input"
            value={plateInput}
            onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
            placeholder="ABC 123 XY"
            maxLength={24}
            autoCapitalize="characters"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            aria-invalid={plateError ? true : undefined}
            aria-describedby={plateError ? "plate-err" : undefined}
          />
          {plateError && (
            <p id="plate-err" className="field__error" role="alert">
              {plateError}
            </p>
          )}
        </div>
        {lookupError && <Banner tone="error">{lookupError}</Banner>}
        <Button type="submit" block variant="dark" loading={stage.kind === "looking"}>
          Look up truck
        </Button>
      </form>

      {stage.kind === "form" && (
        <TruckSignInForm
          key={stage.entryId}
          plate={stage.plate}
          mode={stage.mode}
          entryId={stage.entryId}
          initial={stage.initial}
          hasSignature={stage.hasSignature}
          onDone={onSignedIn}
          onCancel={() => reset(null)}
          onAlreadyInside={() => void runLookup(stage.plate)}
        />
      )}

      {stage.kind === "queued" && (
        <section className="card stack">
          <div className="row row--between">
            <PlateChip plate={stage.truck.plate_number} large />
            <Badge tone="blue">Queued</Badge>
          </div>
          <p>
            <span className="cell-main">{stage.truck.driver_name}</span>
            {stage.truck.company && <span className="cell-sub">{stage.truck.company}</span>}
          </p>
          <Banner tone="warn">This truck is already in the queue. Let it in, or mark it as left the queue.</Banner>
          <div className="row">
            <Button
              onClick={() =>
                setEnterTarget({
                  entryId: stage.truck.open_entry_id as string,
                  plate: stage.truck.plate_number,
                  driverName: stage.truck.driver_name,
                  queuedAt: null,
                })
              }
            >
              Let in
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                setLeaveTarget({
                  entryId: stage.truck.open_entry_id as string,
                  plate: stage.truck.plate_number,
                  driverName: stage.truck.driver_name,
                  queuedAt: null,
                })
              }
            >
              Left queue
            </Button>
            <Button variant="ghost" onClick={() => reset(null)}>
              Cancel
            </Button>
          </div>
        </section>
      )}

      {stage.kind === "inside" && (
        <section className="card stack">
          <div className="row row--between">
            <PlateChip plate={stage.truck.plate_number} large />
            <Badge tone="amber">Inside</Badge>
          </div>
          <p>
            <span className="cell-main">{stage.truck.driver_name}</span>
            {stage.truck.company && <span className="cell-sub">{stage.truck.company}</span>}
          </p>
          <Banner tone="warn">This truck is already inside. Sign it out before signing it in again.</Banner>
          <div className="row">
            <Button
              onClick={() =>
                setSignOutTarget({
                  kind: "trucks",
                  entryId: stage.truck.open_entry_id as string,
                  plate: stage.truck.plate_number,
                  name: stage.truck.driver_name,
                  signedInAt: null,
                })
              }
            >
              Sign out truck
            </Button>
            <Button variant="ghost" onClick={() => reset(null)}>
              Cancel
            </Button>
          </div>
        </section>
      )}

      <EnterTruckSheet truck={enterTarget} onClose={() => setEnterTarget(null)} onDone={onLetIn} />
      <LeaveQueueSheet truck={leaveTarget} onClose={() => setLeaveTarget(null)} onDone={onLeftQueue} />
      <SignOutSheet target={signOutTarget} onClose={() => setSignOutTarget(null)} onDone={onSignedOut} />
    </div>
  );
}
