# Log Book documentation

Start with the [project README](../README.md). This folder holds the detail.

## Layout

```
docs/
  README.md                     this index
  releasing.md                  releases, changelog, commit rules
  architecture/
    backend/                    how the API works, one guide per area
    frontend/                   how the app is laid out and behaves
    scripts/                    the operator scripts and a guide for each
```

Anything that is about running or shipping the project rather than how the code is built
(releasing, and later deployment) stays directly in `docs/`.

## Guides

| Doc | About |
|---|---|
| [releasing.md](releasing.md) | Automated changelog, versions and tags. Squash-merge only, and why |
| [architecture/backend/README.md](architecture/backend/README.md) | The backend's layers and its input rules |
| [architecture/backend/people-logs.md](architecture/backend/people-logs.md) | Visitors and staff: full names, phone numbers (any country), items, signatures, one sign-in at a time |
| [architecture/backend/trucks-and-duty.md](architecture/backend/trucks-and-duty.md) | A truck's visit (queued, on site, departed, left queue), a facility's gates, the officers' own duty log, and its warnings |
| [architecture/backend/notifications.md](architecture/backend/notifications.md) | The global admin's live feed of every event, the warnings, and browser push |
| [architecture/backend/facility-codes.md](architecture/backend/facility-codes.md) | How facility codes (`CNG-LAG-01`) are issued and why they never repeat |
| [architecture/frontend/README.md](architecture/frontend/README.md) | Running the app, where things live, behaviour worth knowing |
| [architecture/scripts/README.md](architecture/scripts/README.md) | The operator scripts and the rules they follow |
| [architecture/scripts/admin_manager.md](architecture/scripts/admin_manager.md) | The `log-book-admin` command: list accounts, create or drop admins, reset an admin's PIN |
| [architecture/scripts/vapid_keys.md](architecture/scripts/vapid_keys.md) | Make the key pair browser push needs |

## Keeping these docs true

When you change code, update its guide **in the same pull request**:

| You changed | Review |
|---|---|
| `scripts/<name>.py` | `architecture/scripts/<name>.md` and the table in `architecture/scripts/README.md` |
| Facility codes or the states list | `architecture/backend/facility-codes.md` and the hint on the Add a facility form |
| Who can do what (roles, facility scoping, admin) | `architecture/scripts/admin_manager.md`, "How access works", and the note on the Accounts page |
| Visitor or staff fields, phone rules, lookup, sign-in/out rules | `architecture/backend/people-logs.md` and `architecture/frontend/README.md` |
| Truck statuses, gates, duty, the on-duty rule, or their warnings | `architecture/backend/trucks-and-duty.md`, `architecture/backend/notifications.md` and `architecture/frontend/README.md` |
| Events, the feed, warnings, push, or anything that should be announced | `architecture/backend/notifications.md` and `architecture/frontend/README.md` |
| Request or response types, input validation, the backend's layers | `architecture/backend/README.md` |
| Releases, commit rules, CI | `releasing.md` |
| A new script or doc | The tables in this file and in `architecture/scripts/README.md` |

Where a new doc goes: how the **backend** works → `architecture/backend/`, the **frontend** →
`architecture/frontend/`, an operator **script** → `architecture/scripts/`. Process and
operations docs (releasing, deployment) stay in `docs/`.

Before opening a pull request, read the guides for the files you touched and check that every
command, option and example output still matches what the code does.
