// frontend/src/pages/gate/GatePage.tsx
// The gate officer's screen: look up a plate, then sign the truck in (or out).
//   new plate        -> blank form
//   known plate      -> form prefilled to CONFIRM
//   already inside   -> offer sign-out instead (the server would refuse a second sign-in)
import { useCallback, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { TruckEntry, TruckLookup } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { SignOutDialog, type SignOutTarget } from "@/components/trucks/SignOutDialog";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { PlateChip } from "@/components/ui/PlateChip";
import { errorMessage } from "@/exceptions/errors";
import { formatTime } from "@/lib/dates";
import { uuid } from "@/lib/ids";
import * as truckService from "@/services/truckService";
import { SignInForm, type SignInInitial } from "./SignInForm";

type Stage =
  | { kind: "idle" }
  | { kind: "looking" }
  | { kind: "form"; mode: "new" | "returning"; plate: string; entryId: string; initial: SignInInitial }
  | { kind: "inside"; truck: TruckLookup };

const BLANK: SignInInitial = { driverName: "", driverPhone: "", company: "" };

function stageFor(result: truckService.LookupResult): Stage {
  switch (result.kind) {
    case "new":
      return { kind: "form", mode: "new", plate: result.plate, entryId: uuid(), initial: BLANK };
    case "returning":
      return {
        kind: "form",
        mode: "returning",
        plate: result.truck.plate_number,
        entryId: uuid(), // one id per form open, reused on retry
        initial: {
          driverName: result.truck.driver_name,
          driverPhone: result.truck.driver_phone ?? "",
          company: result.truck.company ?? "",
        },
      };
    case "inside":
      return { kind: "inside", truck: result.truck };
  }
}

export default function GatePage() {
  const profile = useOfficer();
  const [plateInput, setPlateInput] = useState("");
  const [plateError, setPlateError] = useState<string | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>({ kind: "idle" });
  const [outcome, setOutcome] = useState<string | null>(null);
  const [signOutTarget, setSignOutTarget] = useState<SignOutTarget | null>(null);
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
    reset(`${entry.plate_number} signed in at ${formatTime(entry.signed_in_at)}.`);
  }

  function onSignedOut(entry: TruckEntry) {
    setSignOutTarget(null);
    const at = entry.signed_out_at ? ` at ${formatTime(entry.signed_out_at)}` : "";
    reset(`${entry.plate_number} signed out${at}.`);
  }

  function submitLookup(e: FormEvent) {
    e.preventDefault();
    setOutcome(null);
    void runLookup(plateInput);
  }

  return (
    <div className="page page--narrow stack stack--lg">
      <PageHeader title="Gate" subtitle={profile.facility_name ?? profile.facility_code} />

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
        <Button type="submit" block loading={stage.kind === "looking"}>
          Look up truck
        </Button>
      </form>

      {stage.kind === "form" && (
        <SignInForm
          key={stage.entryId}
          plate={stage.plate}
          mode={stage.mode}
          entryId={stage.entryId}
          initial={stage.initial}
          onDone={onSignedIn}
          onCancel={() => reset(null)}
          onAlreadyInside={() => void runLookup(stage.plate)}
        />
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
                setSignOutTarget({ entryId: stage.truck.open_entry_id as string, plate: stage.truck.plate_number })
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

      <SignOutDialog target={signOutTarget} onClose={() => setSignOutTarget(null)} onDone={onSignedOut} />
    </div>
  );
}
