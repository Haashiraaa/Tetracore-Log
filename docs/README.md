# Tetracore Log documentation

Start with the [project README](../README.md). This folder holds the detail.

| Doc | About |
|---|---|
| [releasing.md](releasing.md) | Automated changelog, versions and tags. Squash-merge only, and why |
| [facility-codes.md](facility-codes.md) | How facility codes (`CNG-LAG-01`) are issued and why they never repeat |
| [scripts/README.md](scripts/README.md) | The operator scripts and the rules they follow |
| [scripts/admin_manager.md](scripts/admin_manager.md) | List accounts, create or drop admins, reset an admin's PIN |

## Keeping these docs true

When you change code, update its guide **in the same pull request**:

| You changed | Review |
|---|---|
| `scripts/<name>.py` | `docs/scripts/<name>.md` and the table in `docs/scripts/README.md` |
| Facility codes or the states list | `docs/facility-codes.md` and the hint on the Add a facility form |
| Who can do what (roles, facility scoping, admin) | `docs/scripts/admin_manager.md`, "How access works", and the note on the Accounts page |
| Releases, commit rules, CI | `docs/releasing.md` |
| A new script or doc | The tables in this file and in `docs/scripts/README.md` |

Before opening a pull request, read the guides for the files you touched and check that every
command, option and example output still matches what the code does.
