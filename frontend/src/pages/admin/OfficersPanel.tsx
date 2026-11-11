// frontend/src/pages/admin/OfficersPanel.tsx
// Facility accounts (officers and facility managers). Admins can't see or touch other
// admins or the CSO here; the server enforces that, the UI just never offers it.
import { useState, type FormEvent } from "react";
import * as adminApi from "@/api/admin";
import type { Facility, OfficerSummary } from "@/api/schemas";
import * as superAdminApi from "@/api/superAdmin";
import { useOfficer } from "@/auth/AuthContext";
import { isSuperAdmin } from "@/auth/permissions";
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
import { ROLE_LABEL, type Role } from "@/models";
import * as adminService from "@/services/adminService";

type PendingKind = "reset" | "disable" | "revoke" | "grant";
interface Pending {
  kind: PendingKind;
  officer: OfficerSummary;
}

const CREATABLE: Role[] = ["officer", "facility_manager"];

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
  revoke: {
    title: "Sign out everywhere",
    label: "Sign out everywhere",
    danger: true,
    body: (o) => `Every phone ${o.full_name} is logged in on is signed out. The account stays enabled.`,
  },
  grant: {
    title: "Make admin",
    label: "Make admin",
    danger: true,
    body: (o) =>
      `${o.full_name} gets admin powers: all facilities, plus creating accounts and resetting PINs. Only do this for someone you trust.`,
  },
};

export function OfficersPanel({ facilities }: { facilities: Facility[] }) {
  const me = useOfficer();
  const superAdmin = isSuperAdmin(me);
  const activeFacilities = facilities.filter((f) => f.is_active);

  const [filter, setFilter] = useState("");
  const officers = useAsync((signal) => adminApi.listOfficers(filter || undefined, signal), [filter]);

  // create form
  const [facility, setFacility] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("officer");
  const [errors, setErrors] = useState<{ fullName?: string; facility?: string }>({});
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
      setReveal(await adminService.createOfficer({ facility_code: facility, full_name: fullName.trim(), role }));
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
    else if (kind === "revoke") await adminApi.revokeSessions(officer.id);
    else await superAdminApi.grantAdmin(officer.id);
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
  const copy = pending ? CONFIRM_COPY[pending.kind] : null;

  return (
    <div className="stack stack--lg">
      <form className="card stack" onSubmit={create} noValidate>
        <h2>Add an officer or manager</h2>
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
          <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {CREATABLE.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </SelectField>
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
                <th scope="col">Role</th>
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
                    <span className="cell-main">{o.officer_code}</span>
                  </td>
                  <td data-label="Name">{o.full_name}</td>
                  <td data-label="Facility">{o.facility_code ?? "None"}</td>
                  <td data-label="Role">{ROLE_LABEL[o.role]}</td>
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
                      {superAdmin && o.is_active && (
                        <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "grant", officer: o })}>
                          Make admin
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
