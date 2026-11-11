# Releasing

Changelog, version numbers and tags are automated. You never edit `CHANGELOG.md`, bump a
version or run `git tag` by hand. What drives it all is the **commit message**.

> Status: adapted from the Kairon repository's setup. Lint, types, migrations and tests were
> run locally against Postgres 16 and pass, but none of this has run on GitHub yet. The first
> release pull request is the real test.

## How it works

Releases happen **only from `main`**. The Release workflow (`.github/workflows/release.yml`)
triggers on pushes to `main` and its job refuses to run on any other ref.

1. Merge work into `main`. Commit messages follow
   [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`.
2. On every push to `main`, [release-please](https://github.com/googleapis/release-please)
   reads the commits since the last release and keeps **one** pull request open, titled
   `chore(main): release X.Y.Z`.
3. That pull request contains only the new `CHANGELOG.md` section and the version bump
   (`pyproject.toml`, `frontend/package.json`, `.release-please-manifest.json`).
4. **A person merges that pull request when they want to ship.** Merging creates the tag
   `vX.Y.Z` and a GitHub Release. Until then nothing is tagged.
5. The server deploys a *tag*, never a branch tip.

## What each commit type does

| Commit type | In changelog | Version effect (before 1.0) |
|---|---|---|
| `feat:` | Features | minor bump (0.1.0 → 0.2.0) |
| `fix:` | Bug fixes | patch bump (0.1.0 → 0.1.1) |
| `perf:` | Performance | patch bump |
| `refactor:`, `docs:` | Refactoring, Documentation | no release on their own |
| `test:`, `chore:`, `ci:`, `build:`, `style:` | hidden | no release on their own |
| `feat!:` or a `BREAKING CHANGE:` footer | Features, flagged | minor bump before 1.0, major after |

To go to 1.0.0 deliberately, put `Release-As: 1.0.0` as a footer line of a commit on `main`.
The CI job "Commit messages (advisory)" warns about subjects that would be left out of the
changelog. It never fails the build.

## One-time setup (in GitHub, not in code)

1. **Allow Actions to open pull requests:** repository Settings → Actions → General →
   Workflow permissions → tick "Allow GitHub Actions to create and approve pull requests".
2. **Create the token `RELEASE_PLEASE_TOKEN`:** a fine-grained personal access token for this
   repository only, with *Contents: read and write* and *Pull requests: read and write*. Save
   it as a repository secret with that exact name. Pull requests opened by the default token do
   not trigger CI, so the required `ci-ok` check would never run on the release pull request.
3. **Protect `main`:** require a pull request, require the status check `ci-ok`, block force
   pushes and deletion. (On a private repository on GitHub's Free plan these rules may be
   greyed out. The tag-only deploy rule above still protects the server.)

## The starting point (`bootstrap-sha`)

`release-please-config.json` has a `bootstrap-sha`: history is counted from that commit, so
the changelog starts clean instead of listing every early commit. It is the last commit of the
original `feat/db-schema-setup` work (`ae09b27`). The hand-written `0.1.0` section in
`CHANGELOG.md` is the baseline and `.release-please-manifest.json` says the current version is
`0.1.0`.

**The pull request that brought that work (and this automation) into `main` must be merged
with "Create a merge commit", not squashed or rebased.** Squashing or rebasing creates new
commits, so `ae09b27` would not be in `main`'s history and the bootstrap point would be lost.
If that ever happens, delete the `bootstrap-sha` line (or point it at a commit that is on
`main`). From then on, feature branches can be squash-merged freely: use one conventional
title, for example `feat(trucks): add visitor sign-in`, because that title becomes the
changelog line.

## Deploying a release

```bash
git fetch --tags
git checkout v0.2.0
```

A tag exists only after the release pull request, and therefore `ci-ok`, was green and a
person merged it, so a failing test can never produce a tag.

## If something goes wrong

- **Wrong version in the release pull request:** add a `Release-As: X.Y.Z` footer commit on
  `main`; release-please recomputes on the next push.
- **A release was tagged by mistake:** delete the GitHub Release and the tag, then fix
  `.release-please-manifest.json` by hand in a normal pull request.
- **The Release workflow fails with a permissions error:** setup step 1 or 2 was missed.
- **A change is missing from the changelog:** its commit message was not in conventional form,
  or its type is hidden (`chore`, `test`, ...).
- **A squash-merged pull request had a non-conventional title:** edit the merged pull request's
  description and add the block below, then push anything to `main` so release-please re-reads it:

  ```
  BEGIN_COMMIT_OVERRIDE
  feat(trucks): add visitor sign-in
  END_COMMIT_OVERRIDE
  ```
