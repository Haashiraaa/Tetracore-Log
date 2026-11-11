# Tetracore Log: frontend

React + TypeScript + Vite. The browser talks only to its own origin (`/api/...`); in
development Vite forwards that to FastAPI, so there is no CORS to configure.

## Run it

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (backend must be on 127.0.0.1:8000)
```

Open it from a phone on the same Wi-Fi with `npm run dev -- --host`, then browse to
`http://<laptop-ip>:5173`. If the backend runs elsewhere, copy `.env.example` to `.env`
and set `API_PROXY_TARGET`.

Other scripts: `npm run typecheck`, `npm run build` (typechecks, then writes `dist/`).

## First run, end to end

1. Create a super admin: `python -m scripts.super_admin_manager create --code SA-01 --name "Your Name"`.
2. Log in with the facility field **blank**, officer code `SA-01` and your PIN.
3. **Admin > Facilities**: add a station (e.g. `CNG-BEN-01`).
4. **Admin > Officers**: add an officer. The temporary PIN is shown once; hand it over in person.
5. The officer logs in (facility, officer code, temp PIN), sets a new PIN, and lands on **Gate**.

## Where things live

The layout mirrors `backend/src/`, so each backend layer has a frontend twin:

| Frontend (`src/`)    | Backend twin                      | What goes there                                            |
| -------------------- | --------------------------------- | ---------------------------------------------------------- |
| `config/env.ts`      | `config/settings.py`              | Every tunable (timezone, page size, signature rules)       |
| `models.ts`          | `models.py`                       | Shared enums and labels (`Role`)                           |
| `exceptions/`        | `exceptions/errors.py`            | `ApiError`, error codes, text safe to show a guard         |
| `security/`          | `security/`                       | Token storage                                              |
| `api/`               | `api/routes/` + `api/schemas.py`  | HTTP only: one file per route group, `schemas.ts` = shapes |
| `services/`          | `api/*_service.py`                | Rules and validation. No JSX                               |
| `auth/`              | `api/deps.py`                     | Login state, route guards, role checks                     |
| `pages/`             | `api/routes/`                     | One folder per screen; thin, they call services            |
| `components/`        | n/a                               | Reusable UI (`ui/`, `trucks/`, `admin/`, `signature/`)     |
| `lib/`, `hooks/`     | `db/orm/_helpers.py`              | Small pure helpers, React hooks                            |
| `styles/`            | n/a                               | `tokens.css`, `base.css`, `components.css`, `layout.css`   |

Rule of thumb: `api/*` never contains a decision, `services/*` never touches the DOM.

## Behaviour worth knowing

- **Who sees what.** Gate officers get Gate, Inside, Log. Facility managers and the CSO get Inside and Log (read-only). Admins add Admin. Super admins add Admins. The backend re-checks every request; the UI only hides what you can't use.
- **Sessions.** Access token in memory, refresh token in `localStorage`. An expired token is refreshed once and the request retried. Only `session_revoked` logs you out; a wrong current PIN on Change PIN does not.
- **Retries are safe.** The sign-in entry id is generated once when the form opens and reused on retry, so a lost response can't create a duplicate.
- **Times.** The server stamps sign-in and sign-out times while the app is online. Everything is displayed in Lagos time (`config/env.ts`).
- **Signatures.** Drawn on a canvas, exported as a small PNG (well under the 200 KB limit), fetched back with the bearer header as a blob.
- **SCM** is typed at sign-out and sent as a decimal string (`"12.50"`).

## Putting it on the VPS later

`npm run build` produces `dist/`. Serve it from the same origin as the API (nginx, or a
`StaticFiles` mount in FastAPI) so `/api` needs no CORS. The app uses client-side routes,
so unknown paths must fall back to `index.html`.
