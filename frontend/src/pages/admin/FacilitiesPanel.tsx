// frontend/src/pages/admin/FacilitiesPanel.tsx
import { useState, type FormEvent } from "react";
import type { Facility } from "@/api/schemas";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { SelectField, TextField } from "@/components/ui/TextField";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import * as adminService from "@/services/adminService";

/** The number of gates, with an inline edit. The server refuses to remove a gate someone is
 *  on duty at, and says so. */
function GatesCell({ facility, onChanged }: { facility: Facility; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(facility.gate_count));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await adminService.setGates(facility.code, value);
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    return (
      <span className="row">
        <span className="mono">{facility.gate_count}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setValue(String(facility.gate_count));
            setEditing(true);
          }}
        >
          Change
        </Button>
      </span>
    );
  }
  return (
    <span className="stack">
      <span className="row">
        <input
          className="input input--code"
          aria-label={`Number of gates at ${facility.code}`}
          inputMode="numeric"
          maxLength={2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={busy}
          size={3}
        />
        <Button size="sm" loading={busy} onClick={() => void save()}>
          Save
        </Button>
        <Button variant="ghost" size="sm" disabled={busy} onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </span>
      {error && <span className="field__error">{error}</span>}
    </span>
  );
}

export function FacilitiesPanel({ facilities, onChanged }: { facilities: Facility[]; onChanged: () => void }) {
  const states = useAsync((signal) => adminService.listStates(signal), []);
  const [state, setState] = useState("");
  const [name, setName] = useState("");
  const [gates, setGates] = useState("1");
  const [errors, setErrors] = useState<{ state?: string; name?: string; gates?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const checked = adminService.validateFacility(state, name, gates);
    if (!checked.ok) {
      setErrors(checked.errors);
      return;
    }
    setErrors({});
    setError(null);
    setCreated(null);
    setBusy(true);
    try {
      const facility = await adminService.createFacility(checked.value);
      setCreated(`${facility.code} created.`);
      setState("");
      setName("");
      setGates("1");
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack stack--lg">
      <form className="card stack" onSubmit={submit} noValidate>
        <h2>Add a facility</h2>
        {created && <Banner tone="success">{created}</Banner>}
        {error && <Banner tone="error">{error}</Banner>}
        <div className="form-grid">
          <SelectField
            label="State"
            hint={
              state
                ? "The code is issued for you, in the form CNG-" +
                  (states.data?.find((o) => o.name === state)?.abbrev ?? "XXX") +
                  "-01, -02 and so on."
                : "Choose the state. The code is issued for you, e.g. CNG-LAG-01."
            }
            value={state}
            onChange={(e) => setState(e.target.value)}
            error={errors.state ?? (states.error ? "Could not load the states." : undefined)}
          >
            <option value="">Choose a state</option>
            {(states.data ?? []).map((o) => (
              <option key={o.name} value={o.name}>
                {o.name}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={errors.name}
            autoComplete="off"
          />
          <TextField
            label="Number of gates"
            hint="Officers pick one of these when they go on duty. You can change it later."
            inputMode="numeric"
            value={gates}
            onChange={(e) => setGates(e.target.value)}
            error={errors.gates}
            autoComplete="off"
            maxLength={2}
          />
        </div>
        <div>
          <Button type="submit" loading={busy}>
            Add facility
          </Button>
        </div>
      </form>

      {facilities.length === 0 ? (
        <EmptyState title="No facilities yet">Add the first station above, then create its officers.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">State</th>
                <th scope="col">Name</th>
                <th scope="col">Gates</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {facilities.map((f) => (
                <tr key={f.id}>
                  <td data-label="Code">
                    <span className="cell-main">{f.code}</span>
                  </td>
                  <td data-label="State">{f.state ?? "-"}</td>
                  <td data-label="Name">{f.name}</td>
                  <td data-label="Gates">
                    <GatesCell facility={f} onChanged={onChanged} />
                  </td>
                  <td data-label="Status">
                    <Badge tone={f.is_active ? "green" : "red"}>{f.is_active ? "Active" : "Disabled"}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
