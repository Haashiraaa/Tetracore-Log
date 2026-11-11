// frontend/src/components/ui/PageHeader.tsx
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function PageHeader({
  title,
  subtitle,
  actions,
  back,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Shows a back arrow before the title. */
  back?: { to: string; label: string };
}) {
  return (
    <header className="page-head">
      <div className="page-head__main">
        {back && (
          <Link to={back.to} className="page-head__back" aria-label={back.label}>
            <svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 5l-7 7 7 7" />
            </svg>
          </Link>
        )}
        <div>
          <h1>{title}</h1>
          {subtitle && <p className="page-head__sub">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="page-head__actions">{actions}</div>}
    </header>
  );
}
