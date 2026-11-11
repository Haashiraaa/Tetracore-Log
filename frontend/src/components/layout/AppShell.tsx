// frontend/src/components/layout/AppShell.tsx
// The frame around every logged-in screen. On a desktop it is a black sidebar;
// on a phone it is a slim top bar plus thumb-reach navigation at the bottom.
import { useRef, type ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth, useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, isAdmin } from "@/auth/permissions";
import { roleLabel } from "@/lib/format";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

const GATE: NavItem = { to: "/gate", label: "Gate", icon: <Icon><path d="M4 20V6M20 20V6M4 9h16M4 15h16" /></Icon> };
const INSIDE: NavItem = { to: "/inside", label: "Inside", icon: <Icon><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2.5" /></Icon> };
const LOG: NavItem = { to: "/log", label: "Log", icon: <Icon><path d="M6 4h12v16H6zM9 9h6M9 13h6M9 17h3" /></Icon> };
const ADMIN: NavItem = { to: "/admin", label: "Accounts", icon: <Icon><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.8-3.6 3.5-5.5 7-5.5s6.200 1.900 7 5.500" /></Icon> };

export function AppShell() {
  const profile = useOfficer();
  const { logout } = useAuth();
  const menu = useRef<HTMLDetailsElement>(null);

  const links = [canWriteEntries(profile) ? GATE : null, INSIDE, LOG, isAdmin(profile) ? ADMIN : null].filter(
    (l): l is NavItem => l !== null,
  );
  const where = profile.facility_code ?? "All facilities";
  const closeMenu = () => menu.current?.removeAttribute("open");

  return (
    <div className="shell">
      <aside className="side">
        <Link to="/" className="brand" aria-label="Tetracore Log home">
          <span className="brand__name">
            Tetracore <span className="brand__log">Log</span>
          </span>
          <span className="brand__tape" aria-hidden="true" />
        </Link>

        <nav className="nav" aria-label="Main">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className="nav__link">
              {l.icon}
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>

        <details className="account" ref={menu}>
          <summary className="account__summary" aria-label="Account menu">
            <span className="account__name">{profile.full_name}</span>
            <span className="account__meta">
              {profile.officer_code} / {where}
            </span>
          </summary>
          <div className="account__panel">
            <p className="account__line">
              <strong>{profile.full_name}</strong>
            </p>
            <p className="account__line">
              {roleLabel(profile.role)}, {profile.officer_code}
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
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
