# `scripts/admin_manager.py`

**Purpose:** the only place admins are made or removed. No API route can do it, so a stolen
admin session cannot create more admins. Day-to-day account work (new officers, disabling,
resetting an officer's PIN) is done by admins on the **Accounts** page of the app.

**Touches:** your real database. Each command is one transaction (all or nothing), except `list`
which only reads.

```bash
log-book-admin list                  # admins only
log-book-admin list --all            # every account
log-book-admin create --code ADM-01 --name "Ada Obi"
log-book-admin grant --code OFF-003 --facility CNG-LAG-01
log-book-admin revoke --code ADM-01
log-book-admin reset-pin --code ADM-01
```

`log-book-admin` is a command registered in `pyproject.toml` (`[project.scripts]`, next to
`log-book`). It exists once the project is installed: run `pip install -e .` in the
virtualenv, once, and again after pulling a change that touches `pyproject.toml`. If the command is
not found, that is the reason (or the virtualenv is not active). `python -m scripts.admin_manager`
does exactly the same and needs no install.

## Commands

| Command | What it does | PIN prompt |
|---|---|---|
| `list` | Prints admins. With `--all`, every account, with an `admin` marker | no |
| `create` | Makes a **new** account that is an admin from the start | yes, twice |
| `grant` | Turns an existing account into an admin | no |
| `revoke` | Removes admin powers. The account, its role, facility and code stay | no |
| `reset-pin` | Sets a new PIN for an **admin** and signs them out everywhere | yes, twice |

## Options

| Option | Used by | Meaning |
|---|---|---|
| `--code CODE` | create, grant, revoke, reset-pin | The officer code (any case) |
| `--facility CODE` | create, grant, revoke, reset-pin | The facility code as issued, e.g. `CNG-LAG-01` (see [facility-codes.md](../facility-codes.md)). Leave it out for a global account. The same officer code can exist in two facilities, so a scoped account needs this to be found |
| `--name "Full Name"` | create | Required. First and last name (at least two words) |
| `--role LABEL` | create | Free-text label, up to 32 characters. Default `admin`. Nothing checks it, see [How access works](#how-access-works) |
| `--force` | revoke | Allow dropping the **last active** admin |
| `--all` | list | Include accounts that are not admins |

## What `list` prints

One line per account:

```
ADM-01     Ada Obi                      role=admin            facility=-            admin  active
OFF-001    Musa Bello                   role=Officer          facility=CNG-LAG-01    -      active
```

| Column | Meaning |
|---|---|
| code | The officer code used to log in |
| name | Full name |
| `role=` | The free-text label. It does not change what the person can do |
| `facility=` | The facility the account is scoped to, or `-` for a global account |
| `admin` / `-` | Whether the account has admin powers (only shown as `-` with `--all`) |
| `active` / `DISABLED` | A disabled account cannot log in |

With `--all` admins are listed first, then the rest by facility and code.

## Resetting a PIN

- **An admin:** `reset-pin` here. You type the new PIN twice (6 to 10 digits, the same policy as
  the app). The account stops being forced to change it, the lockout is cleared, and every
  logged-in phone is signed out.
- **Any other officer:** the CLI refuses. Use **Accounts, Reset PIN** in the app as an admin. It
  generates a temporary PIN, shows it once, and makes the officer choose their own at next
  login.
- **No admin can log in at all:** `create` a fresh admin here (with a new code), sign in with it,
  then clean up from the app.

## How access works

Three things decide what an account can do. The `role` label is not one of them.

| Field | Effect |
|---|---|
| Facility set | The account sees and writes entries for that one facility only |
| Facility empty (global) | Reads every facility, writes no entries |
| Admin | Can use the admin API and Accounts page. An admin that belongs to a facility can also write entries there |

So `role` is a label for people ("Supervisor", "Officer"). Use any text you like.

## Notifications

`create`, `grant` and `revoke` add an event to the admins' notification feed, marked "from the
server console" (see [../notifications.md](../notifications.md)). The event is written in the same
transaction as the change. The console does **not** send browser push: only the running server does,
so these appear in the feed the next time an admin looks.

## Safety

- `revoke` refuses to remove the **last active admin** unless you pass `--force`. Without an
  admin nobody can manage accounts from the app.
- `grant` refuses a disabled account (enable it from the app first) and one that is already an
  admin.
- `create` refuses a code that already exists in that facility, and refuses weak PINs.
- Errors print `Error: ...` and exit with code 1. Nothing is written.
- Revoking admin takes effect on the person's very next request. They do not need to log in
  again to lose access.

## Tests

`tests/scripts/test_admin_manager.py` covers every command, that grant and revoke reach the notification feed, including the last-admin guard,
the non-admin refusal on `reset-pin`, and that a granted or revoked admin changes on the next
request.
