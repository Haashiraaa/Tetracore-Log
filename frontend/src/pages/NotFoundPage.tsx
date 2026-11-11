// frontend/src/pages/NotFoundPage.tsx
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="auth">
      <div className="auth__card stack">
        <h1>Page not found</h1>
        <p className="muted">That address doesn't lead anywhere in the gate log.</p>
        <Link to="/" className="btn btn--primary">
          Go to the start
        </Link>
      </div>
    </main>
  );
}
