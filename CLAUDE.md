# Working in this repo

- Commit messages follow Conventional Commits (`type(scope): summary`). Merge pull requests with
  **squash and merge** only; see `docs/releasing.md`.
- **Documentation is part of the change.** Before finishing any change, check `docs/README.md`
  ("Keeping these docs true"), read the guides for the files you touched, and update them in the
  same pull request. Say in the pull request which docs you reviewed.
- Scripts live in `scripts/` with a guide in `docs/scripts/<name>.md` and a test in
  `tests/scripts/`.
