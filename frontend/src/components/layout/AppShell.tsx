// frontend/src/components/layout/AppShell.tsx
// Header, navigation and account menu around every logged-in screen.
import { useRef } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useOfficer, useAuth } from "@/auth/AuthContext";
import { canWriteEntries, isAdmin, isSuperAdmin } from "@/auth/permissions";
import { initials } from "@/lib/format";
import { ROLE_LABEL } from "@/models";

export function AppShell() {
  const profile = useOfficer();
  const { logout } = useAuth();
  const menu = useRef<HTMLDetailsElement>(null);

  const links = [
    canWriteEntries(profile) && { to: "/gate", label: "Gate" },
    { to: "/inside", label: "Inside" },
    { to: "/log", label: "Log" },
    isAdmin(profile) && { to: "/admin", label: "Admin" },
    isSuperAdmin(profile) && { to: "/super-admin", label: "Admins" },
  ].filter((l): l is { to: string; label: string } => Boolean(l));

  const closeMenu = () => menu.current?.removeAttribute("open");

  return (
    <div className="shell">
      <header className="shell__bar">
        <Link to="/" className="brand" aria-label="Tetracore Log home">
          <span className="brand__mark" aria-hidden="true" />
          <span className="brand__name">Tetracore Log</span>
        </Link>

        <nav className="nav" aria-label="Main">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className="nav__link">
              {l.label}
            </NavLink>
          ))}
        </nav>

        <details className="account" ref={menu}>
          <summary className="account__summary" aria-label="Account menu">
            <span className="account__avatar" aria-hidden="true">
              {initials(profile.full_name)}
            </span>
            <span className="account__who">
              <span className="account__name">{profile.full_name}</span>
              <span className="account__meta">{profile.facility_code ?? "All facilities"}</span>
            </span>
          </summary>
          <div className="account__panel">
            <p className="account__line">
              <strong>{profile.full_name}</strong>
            </p>
            <p className="account__line">
              {ROLE_LABEL[profile.role]}, {profile.officer_code}
            </p>
            {profile.facility_name && <p className="account__line">{profile.facility_name}</p>}
            <Link to="/change-pin" className="account__action" onClick={closeMenu}>
              Change PIN
            </Link>
            <button type="button" className="account__action" onClick={() => void logout()}>
              Log out
            </button>
          </div>
        </details>
      </header>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
