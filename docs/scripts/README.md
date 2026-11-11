# Scripts (`scripts/`)

Operator tools. They are **not** part of the running product and nothing in `backend/` imports
them. Run them from the repository root as modules:

```bash
python -m scripts.<name> [options]
```

They load `.env` the same way the backend does, so `DATABASE_URL` (and the JWT and PIN secrets)
must be set. Whatever database `DATABASE_URL` points at is the one the script changes: on the
server that is the real one.

| Script | Talks to | Changes data? | Use it to |
|---|---|---|---|
| [vapid_keys.py](vapid_keys.md) | nothing | no | Make the key pair browser push needs |
| [admin_manager.py](admin_manager.md) | your real database | yes (one transaction per command, except `list`) | List accounts, create admins, grant or drop admin powers, reset an admin's PIN |

## Rules for scripts

- Secrets (PINs) are prompted with hidden input. Never take them as arguments, so they never
  land in shell history or a process list.
- A command that changes data does it in one transaction and rolls back on any error.
- Every script has its own guide in this folder and its own test in `tests/scripts/`.
- Adding or changing a script means updating its guide and the table above in the same pull
  request.
