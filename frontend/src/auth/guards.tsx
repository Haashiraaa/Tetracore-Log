// frontend/src/auth/guards.tsx
// Route guards. Counterpart of get_current_officer / require_* in backend/src/api/deps.py.

import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import type { OfficerProfile } from "@/api/schemas";
import { useDuty } from "@/components/duty/DutyContext";
import { Banner } from "@/components/ui/Banner";
import { BootScreen } from "@/components/ui/BootScreen";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "./AuthContext";
import { homePathFor } from "./permissions";

/** Logged in, and not stuck on a temporary PIN. */
export function RequireAuth() {
  const { status, profile } = useAuth();
  const location = useLocation();

  if (status === "booting" || status === "unreachable") return <BootScreen />;
  if (status !== "authenticated" || !profile) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (profile.must_change_pin && location.pathname !== "/change-pin") {
    return <Navigate to="/change-pin" replace />;
  }
  return <Outlet />;
}

/** Only renders its routes when `allow(profile)` is true; otherwise goes home. */
export function RequireAccess({ allow }: { allow: (p: OfficerProfile) => boolean }) {
  const { profile } = useAuth();
  if (!profile || !allow(profile)) return <Navigate to={homePathFor(profile)} replace />;
  return <Outlet />;
}

/** Gate pages that write entries: an officer who is off duty is sent to the Duty page first.
 *  While the answer is still loading (or could not be fetched) the page opens and the
 *  server stays the judge. */
export function RequireDuty() {
  const duty = useDuty();
  if (duty && duty.status !== null && !duty.onDuty) {
    return (
      <div className="page page--form stack stack--lg">
        <PageHeader title="Go on duty first" back={{ to: "/gate", label: "Back to gate" }} />
        <Banner tone="warn">
          You are off duty. Pick your gate on the Duty page, then come back to sign trucks, visitors and staff in.
        </Banner>
        <Link to="/duty" className="btn btn--dark">
          Go to Duty
        </Link>
      </div>
    );
  }
  return <Outlet />;
}
