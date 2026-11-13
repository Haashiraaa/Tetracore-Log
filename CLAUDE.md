# Working in this repo

- Commit messages follow Conventional Commits (`type(scope): summary`). Merge pull requests with
  **squash and merge** only; see `docs/releasing.md`.
- **Documentation is part of the change.** Before finishing any change, check `docs/README.md`
  ("Keeping these docs true"), read the guides for the files you touched, and update them in the
  same pull request. Say in the pull request which docs you reviewed.
- **Where docs live.** How the backend works: `docs/architecture/backend/`. The frontend:
  `docs/architecture/frontend/`. Operator scripts: `docs/architecture/scripts/`. Process and
  operations docs (releasing, deployment) stay directly in `docs/`. Never add a guide at the top
  of `docs/` that belongs in one of those folders, and keep `docs/README.md` indexing every doc.
- Scripts live in `scripts/` with a guide in `docs/architecture/scripts/<name>.md` and a test in
  `tests/scripts/`.
- **Types are enforced at the API.** A number, flag or id must arrive as its real JSON type;
  never accept a string where an integer belongs (see `docs/architecture/backend/README.md`).
- **Phone numbers are stored in E.164** (`+2348031234567`) and validated for their country; the
  default country is Nigeria. Never store or compare phone numbers in another form.
