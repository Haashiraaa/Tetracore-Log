# Changelog

All notable changes to Tetracore Log. Entries above the baseline are written automatically by
release-please from commit messages when a release pull request is merged (see
[docs/releasing.md](docs/releasing.md)), so do not edit them by hand.

## [0.4.1](https://github.com/Haashiraaa/Tetracore-Log/compare/v0.4.0...v0.4.1) (2026-11-11)


### Documentation

* document scripts and let admin_manager list every account ([#11](https://github.com/Haashiraaa/Tetracore-Log/issues/11)) ([a79b38c](https://github.com/Haashiraaa/Tetracore-Log/commit/a79b38c511e20429a1c69deecde2615f38764c4b))

## [0.4.0](https://github.com/Haashiraaa/Tetracore-Log/compare/v0.3.0...v0.4.0) (2026-11-11)


### Features

* **frontend:** hi-vis redesign with visitor and staff logs ([#9](https://github.com/Haashiraaa/Tetracore-Log/issues/9)) ([6981b51](https://github.com/Haashiraaa/Tetracore-Log/commit/6981b51afdb3334301e1dee4f79c6201b3eaf046))

## [0.3.0](https://github.com/Haashiraaa/Tetracore-Log/compare/v0.2.0...v0.3.0) (2026-11-11)


### Features

* add visitor and staff logs with in and out signatures ([#7](https://github.com/Haashiraaa/Tetracore-Log/issues/7)) ([07f3214](https://github.com/Haashiraaa/Tetracore-Log/commit/07f32148ae73363ad4c0b8323bf458ccde2398cb))

## [0.2.0](https://github.com/Haashiraaa/Tetracore-Log/compare/v0.1.0...v0.2.0) (2026-11-11)


### ⚠ BREAKING CHANGES

* drop super admin and make role a free-form label; admins are managed only from scripts/admin_manager.py

### Features

* add visitor and staff log spaces (read-only for now) ([748e857](https://github.com/Haashiraaa/Tetracore-Log/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))
* drop super admin and make role a free-form label; admins are managed only from scripts/admin_manager.py ([748e857](https://github.com/Haashiraaa/Tetracore-Log/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))
* initialize gate-log backend, database schema and migrations ([748e857](https://github.com/Haashiraaa/Tetracore-Log/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))


### Refactoring

* split long functions, share entry-log queries, split schemas by area and register routers in one list ([748e857](https://github.com/Haashiraaa/Tetracore-Log/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))


### Documentation

* require squash merges so release-please can read commits ([748e857](https://github.com/Haashiraaa/Tetracore-Log/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))

## 0.1.0 (baseline)

Everything built before release automation existed: the gate-log schema and migrations, officer
login with PIN lockout and revocable sessions, admin and super-admin account management, truck
sign-in and sign-out with signatures, and the web frontend.
