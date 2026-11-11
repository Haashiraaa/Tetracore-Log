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

export function FacilitiesPanel({ facilities, onChanged }: { facilities: Facility[]; onChanged: () => void }) {
  const states = useAsync((signal) => adminService.listStates(signal), []);
  const [state, setState] = useState("");
  const [name, setName] = useState("");
  const [errors, setErrors] = useState<{ state?: string; name?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const checked = adminService.validateFacility(state, name);
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
