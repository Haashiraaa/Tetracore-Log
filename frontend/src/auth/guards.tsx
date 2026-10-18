// frontend/src/auth/guards.tsx
// Route guards. Counterpart of get_current_officer / require_* in backend/src/api/deps.py.

import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { OfficerProfile } from "@/api/schemas";
import { BootScreen } from "@/components/ui/BootScreen";
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
