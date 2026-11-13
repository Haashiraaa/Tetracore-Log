// frontend/src/pages/admin/OfficersPanel.tsx
// Every account that is not an admin. Admins can't see or touch other admins here: they are
// set and dropped from the admin CLI only (scripts/admin_manager.py), never from the UI.
import { useState, type FormEvent } from "react";
import * as adminApi from "@/api/admin";
import type { Facility, OfficerSummary } from "@/api/schemas";
import { TempPinDialog } from "@/components/admin/TempPinDialog";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { SelectField, TextField } from "@/components/ui/TextField";
import { Spinner } from "@/components/ui/Spinner";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { roleLabel } from "@/lib/format";
import { DEFAULT_ROLE, ROLE_MAX_LENGTH } from "@/models";
import * as adminService from "@/services/adminService";

type PendingKind = "reset" | "disable" | "revoke" | "endDuty";
interface Pending {
  kind: PendingKind;
  officer: OfficerSummary;
}

const CONFIRM_COPY: Record<PendingKind, { title: string; label: string; danger: boolean; body: (o: OfficerSummary) => string }> = {
  reset: {
    title: "Reset PIN",
    label: "Reset PIN",
    danger: false,
    body: (o) =>
      `${o.full_name} gets a new temporary PIN, is signed out on every phone, and must choose a new PIN at the next login.`,
  },
  disable: {
    title: "Disable account",
    label: "Disable",
    danger: true,
    body: (o) => `${o.full_name} will be signed out everywhere and won't be able to log in until you enable the account.`,
  },
  endDuty: {
    title: "End duty",
    label: "End duty",
    danger: false,
    body: (o) =>
      `${o.full_name} is taken off duty now, wherever they are. Use this when they forgot to go off duty. Nothing they logged changes.`,
  },
  revoke: {
    title: "Sign out everywhere",
    label: "Sign out everywhere",
    danger: true,
    body: (o) => `Every phone ${o.full_name} is logged in on is signed out. The account stays enabled.`,
  },
};

export function OfficersPanel({ facilities }: { facilities: Facility[] }) {
  const activeFacilities = facilities.filter((f) => f.is_active);

  const [filter, setFilter] = useState("");
  const officers = useAsync((signal) => adminApi.listOfficers(filter || undefined, signal), [filter]);

  // create form
  const [facility, setFacility] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [errors, setErrors] = useState<{ fullName?: string; role?: string; facility?: string }>({});
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [reveal, setReveal] = useState<adminService.PinReveal | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    const found = adminService.validateNewAccount(fullName, role, facility);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setCreating(true);
    setCreateError(null);
    try {
      setReveal(await adminService.createOfficer({ facility_code: facility, full_name: fullName.trim(), role: role.trim() }));
      setFullName("");
      officers.reload();
    } catch (err) {
      setCreateError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function runPending() {
    if (!pending) return;
    const { kind, officer } = pending;
    if (kind === "reset") setReveal(await adminService.resetOfficerPin(officer.id, officer.facility_code));
    else if (kind === "disable") await adminApi.disableOfficer(officer.id);
    else if (kind === "endDuty") await adminService.endDuty(officer.id);
    else await adminApi.revokeSessions(officer.id);
    setPending(null);
    officers.reload();
  }

  async function enable(officer: OfficerSummary) {
    setActionError(null);
    try {
      await adminApi.enableOfficer(officer.id);
      officers.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  const rows = officers.data ?? [];
  const knownRoles = [...new Set([DEFAULT_ROLE, ...rows.map((o) => o.role)])];
  const copy = pending ? CONFIRM_COPY[pending.kind] : null;

  return (
    <div className="stack stack--lg">
      <form className="card stack" onSubmit={create} noValidate>
        <h2>Add an account</h2>
        {activeFacilities.length === 0 && (
          <Banner tone="warn">Add a facility first. Every officer belongs to one.</Banner>
        )}
        {createError && <Banner tone="error">{createError}</Banner>}
        <div className="form-grid">
          <SelectField
            label="Facility"
            value={facility}
            onChange={(e) => setFacility(e.target.value)}
            error={errors.facility}
          >
            <option value="">Choose a facility</option>
            {activeFacilities.map((f) => (
              <option key={f.id} value={f.code}>
                {f.code}, {f.name}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            error={errors.fullName}
            autoComplete="off"
          />
          <TextField
            label="Role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            error={errors.role}
            hint="A label only, it doesn't change what the person can do."
            maxLength={ROLE_MAX_LENGTH}
            list="known-roles"
            autoComplete="off"
          />
          <datalist id="known-roles">
            {knownRoles.map((r) => (
              <option key={r} value={r} />
            ))}
          </datalist>
        </div>
        <p className="muted">The system issues the officer code and a temporary PIN. You'll see the PIN once.</p>
        <div>
          <Button type="submit" loading={creating} disabled={activeFacilities.length === 0}>
            Create account
          </Button>
        </div>
      </form>

      <div className="row row--between">
        <h2>Accounts</h2>
        <SelectField label="Show" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All facilities</option>
          {facilities.map((f) => (
            <option key={f.id} value={f.code}>
              {f.code}
            </option>
          ))}
        </SelectField>
      </div>

      {actionError && <Banner tone="error">{actionError}</Banner>}
      {officers.error !== null && <Banner tone="error">{errorMessage(officers.error)}</Banner>}
      {officers.loading && officers.data === null && <Spinner />}
      {officers.data !== null && rows.length === 0 && (
        <EmptyState title="No accounts here yet">Create the first officer with the form above.</EmptyState>
      )}

      {rows.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Facility</th>
                <th scope="col">Role label</th>
                <th scope="col">Can do</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.id}>
                  <td data-label="Code">
                    <span className="cell-main mono">{o.officer_code}</span>
                  </td>
                  <td data-label="Name">{o.full_name}</td>
                  <td data-label="Facility" className="mono">
                    {o.facility_code ?? "ALL"}
                  </td>
                  <td data-label="Role label">{roleLabel(o.role)}</td>
                  <td data-label="Can do">
                    <Badge tone={o.can_write_entries ? "green" : "ink"}>
                      {o.can_write_entries ? "Signs in and out" : "Reads everything"}
                    </Badge>
                  </td>
                  <td data-label="Status">
                    <div className="row">
                      <Badge tone={o.is_active ? "green" : "red"}>{o.is_active ? "Active" : "Disabled"}</Badge>
                      {o.must_change_pin && <Badge tone="amber">Temp PIN</Badge>}
                    </div>
                  </td>
                  <td className="table__action">
                    <div className="row row--end">
                      <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "reset", officer: o })}>
                        Reset PIN
                      </Button>
                      {o.can_write_entries && (
                        <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "endDuty", officer: o })}>
                          End duty
                        </Button>
                      )}
                      <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "revoke", officer: o })}>
                        Sign out everywhere
                      </Button>
                      {o.is_active ? (
                        <Button variant="danger" size="sm" onClick={() => setPending({ kind: "disable", officer: o })}>
                          Disable
                        </Button>
                      ) : (
                        <Button variant="secondary" size="sm" onClick={() => void enable(o)}>
                          Enable
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="note-dark">

        <span className="mono" aria-hidden="true">$</span> Admins are not on this page. They are added and removed only

        from the server, with <span className="mono">log-book-admin</span>. Nobody can make themselves an admin from the app.

      </p>


      <ConfirmDialog
        open={pending !== null}
        title={copy?.title ?? ""}
        confirmLabel={copy?.label ?? "Confirm"}
        danger={copy?.danger}
        onConfirm={runPending}
        onClose={() => setPending(null)}
      >
        {pending && copy && <p>{copy.body(pending.officer)}</p>}
      </ConfirmDialog>

      <TempPinDialog reveal={reveal} onClose={() => setReveal(null)} />
    </div>
  );
}
