# Backend

FastAPI + Postgres (SQLAlchemy, Alembic). Code lives in `backend/src/`; migrations in `alembic/`;
tests in `tests/`, mirroring the same folders.

## Layers

A request goes down these layers and never skips one. Each layer only calls the one below it.

| Layer | Folder | Job |
|---|---|---|
| Routes | `api/routes/` | HTTP only: parse the request, call a service, shape the response |
| Schemas | `api/schemas/` | What goes in and out. Types are checked here (see [Input rules](#input-rules)) |
| Services | `api/*_service.py` | The rules: who may do what, retries, "first sign-out wins". `entry_service.py` holds what every log shares |
| Queries | `db/queries/` | SQL only. No commits, no rules |
| Tables | `db/orm/` | The Postgres tables (`tables.py`) and shared columns (`_mixins.py`) |

Also: `config/` (every tunable, read from `.env`), `security/` (PINs, tokens, sessions),
`exceptions/errors.py` (every error code the API can return), `models.py` (the small pure rules
for names and phone numbers), `facility_codes.py`.

## Guides

| Guide | About |
|---|---|
| [people-logs.md](people-logs.md) | Visitors and staff: full names, phone numbers, items, signatures, one sign-in at a time |
| [trucks-and-duty.md](trucks-and-duty.md) | A truck's visit, a facility's gates, the officers' duty log, and its warnings |
| [notifications.md](notifications.md) | The global admin's live feed of every event, the warnings, and browser push |
| [facility-codes.md](facility-codes.md) | How facility codes (`CNG-LAG-01`) are issued and why they never repeat |

## Input rules

Request bodies are checked for **type**, not just shape. A field that wants a number must be sent a
JSON number, a flag must be `true` or `false`, and text must be text: `"3"` for a gate number, `1`
for a flag, or `["x"]` for a name are all refused with `422`, never quietly converted. Timestamps and
ids are the exception only in that JSON has no type for them: they travel as strings and are parsed
and validated (a timestamp must carry a timezone offset; an id must be a UUID). Gas bought
(`scm_purchased`) is sent as a decimal string such as `"12.50"` so no precision is lost.
Item quantities are integers (with a separate optional unit). Phone numbers are validated for their country and stored as E.164 (see
[people-logs.md](people-logs.md#phone-numbers)). The shared definitions are in
`api/schemas/common.py`.
