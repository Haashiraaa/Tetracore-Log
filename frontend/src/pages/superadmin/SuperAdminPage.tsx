// frontend/src/pages/superadmin/SuperAdminPage.tsx  (backend: api/routes/super_admin.py)
// Creating and managing ADMIN accounts. Super admins themselves are CLI-only: the API
// never exposes them for changes, so their rows carry no actions here.
import { useState, type FormEvent } from "react";
import * as adminApi from "@/api/admin";
import type { OfficerSummary } from "@/api/schemas";
import * as superAdminApi from "@/api/superAdmin";
import { TempPinDialog } from "@/components/admin/TempPinDialog";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { SelectField, TextField } from "@/components/ui/TextField";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { isFacilityRole, ROLE_LABEL, type Role } from "@/models";
import * as adminService from "@/services/adminService";

const ROLES: Role[] = ["cso", "facility_manager", "officer"];

type PendingKind = "reset" | "disable" | "remove";
interface Pending {
  kind: PendingKind;
  admin: OfficerSummary;
}

const COPY: Record<PendingKind, { title: string; label: string; danger: boolean; body: (a: OfficerSummary) => string }> = {
  reset: {
    title: "Reset PIN",
    label: "Reset PIN",
    danger: false,
    body: (a) => `${a.full_name} gets a new temporary PIN and is signed out on every phone.`,
  },
  disable: {
    title: "Disable admin",
    label: "Disable",
    danger: true,
    body: (a) => `${a.full_name} is signed out everywhere and can't log in until you enable the account.`,
  },
  remove: {
    title: "Remove admin powers",
    label: "Remove admin powers",
    danger: true,
    body: (a) =>
      `${a.full_name} keeps the account, role and facility but loses admin powers from their next request.`,
  },
};

export default function SuperAdminPage() {
  const admins = useAsync((signal) => superAdminApi.listAdmins(signal), []);
  const facilities = useAsync((signal) => adminApi.listFacilities(signal), []);

  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("cso");
  const [facility, setFacility] = useState("");
  const [errors, setErrors] = useState<{ fullName?: string; facility?: string }>({});
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [reveal, setReveal] = useState<adminService.PinReveal | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const needsFacility = isFacilityRole(role);

  async function create(e: FormEvent) {
    e.preventDefault();
    const found = adminService.validateNewAccount(fullName, role, facility);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setCreating(true);
    setCreateError(null);
    try {
      setReveal(
        await adminService.createAdmin({
          full_name: fullName.trim(),
          role,
          facility_code: needsFacility ? facility : null,
        }),
      );
      setFullName("");
      admins.reload();
    } catch (err) {
      setCreateError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function runPending() {
    if (!pending) return;
    const { kind, admin } = pending;
    if (kind === "reset") setReveal(await adminService.resetAdminPin(admin.id));
    else if (kind === "disable") await superAdminApi.disableAdmin(admin.id);
    else await superAdminApi.revokeAdmin(admin.id);
    setPending(null);
    admins.reload();
  }

  async function enable(admin: OfficerSummary) {
    setActionError(null);
    try {
      await superAdminApi.enableAdmin(admin.id);
      admins.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  const rows = admins.data ?? [];
  const copy = pending ? COPY[pending.kind] : null;

  return (
    <div className="page stack stack--lg">
      <PageHeader title="Admins" subtitle="People who can create accounts and see every facility." />

      <form className="card stack" onSubmit={create} noValidate>
        <h2>Add an admin</h2>
        {createError && <Banner tone="error">{createError}</Banner>}
        <div className="form-grid">
          <TextField
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            error={errors.fullName}
            autoComplete="off"
          />
          <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </SelectField>
          {needsFacility && (
            <SelectField
              label="Facility"
              value={facility}
              onChange={(e) => setFacility(e.target.value)}
              error={errors.facility}
            >
              <option value="">Choose a facility</option>
              {(facilities.data ?? [])
                .filter((f) => f.is_active)
                .map((f) => (
                  <option key={f.id} value={f.code}>
                    {f.code}, {f.name}
                  </option>
                ))}
            </SelectField>
          )}
        </div>
        <p className="muted">
          To promote someone who already has an account, use Make admin on the Admin page.
        </p>
        <div>
          <Button type="submit" loading={creating}>
            Create admin
          </Button>
        </div>
      </form>

      {actionError && <Banner tone="error">{actionError}</Banner>}
      {admins.error !== null && <Banner tone="error">{errorMessage(admins.error)}</Banner>}
      {admins.loading && admins.data === null && <Spinner />}
      {admins.data !== null && rows.length === 0 && <EmptyState title="No admins yet" />}

      {rows.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Role</th>
                <th scope="col">Facility</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td data-label="Code">
                    <span className="cell-main">{a.officer_code}</span>
                  </td>
                  <td data-label="Name">{a.full_name}</td>
                  <td data-label="Role">{ROLE_LABEL[a.role]}</td>
                  <td data-label="Facility">{a.facility_code ?? "None"}</td>
                  <td data-label="Status">
                    <div className="row">
                      {a.is_super_admin && <Badge tone="blue">Super admin</Badge>}
                      <Badge tone={a.is_active ? "green" : "red"}>{a.is_active ? "Active" : "Disabled"}</Badge>
                      {a.must_change_pin && <Badge tone="amber">Temp PIN</Badge>}
                    </div>
                  </td>
                  <td className="table__action">
                    {a.is_super_admin ? (
                      <span className="muted">Managed from the command line</span>
                    ) : (
                      <div className="row row--end">
                        <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "reset", admin: a })}>
                          Reset PIN
                        </Button>
                        {a.is_active ? (
                          <Button variant="danger" size="sm" onClick={() => setPending({ kind: "disable", admin: a })}>
                            Disable
                          </Button>
                        ) : (
                          <Button variant="secondary" size="sm" onClick={() => void enable(a)}>
                            Enable
                          </Button>
                        )}
                        <Button variant="secondary" size="sm" onClick={() => setPending({ kind: "remove", admin: a })}>
                          Remove admin powers
                        </Button>
                      </div>
                    )}
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
        {pending && copy && <p>{copy.body(pending.admin)}</p>}
      </ConfirmDialog>

      <TempPinDialog reveal={reveal} onClose={() => setReveal(null)} />
    </div>
  );
}
