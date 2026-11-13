# Changelog

All notable changes to Log Book. Entries above the baseline are written automatically by
release-please from commit messages when a release pull request is merged (see
[docs/releasing.md](docs/releasing.md)), so do not edit them by hand.

## [0.16.0](https://github.com/Haashiraaa/log-book/compare/v0.15.0...v0.16.0) (2026-11-13)


### Features

* **phones:** per-country phone validation, E.164 storage, strict input types, docs reorg ([#40](https://github.com/Haashiraaa/log-book/issues/40)) ([08c3653](https://github.com/Haashiraaa/log-book/commit/08c3653bebb39c9eb09f4aa5925f2f6ef1f64401))

## [0.15.0](https://github.com/Haashiraaa/log-book/compare/v0.14.0...v0.15.0) (2026-11-13)


### Features

* **trucks:** reuse a returning truck's signature, and record when a signature was reused ([#38](https://github.com/Haashiraaa/log-book/issues/38)) ([6a35775](https://github.com/Haashiraaa/log-book/commit/6a357755d62c618dfb3f5cadf8994e3f072e7270))

## [0.14.0](https://github.com/Haashiraaa/log-book/compare/v0.13.0...v0.14.0) (2026-11-13)


### Features

* **visitors:** add item rows, and keep and reuse signatures for visitors and staff ([#36](https://github.com/Haashiraaa/log-book/issues/36)) ([cf8af86](https://github.com/Haashiraaa/log-book/commit/cf8af86d3cd37def90e432ed206c6de185f02f21))

## [0.13.0](https://github.com/Haashiraaa/log-book/compare/v0.12.0...v0.13.0) (2026-11-13)


### Features

* **frontend:** give the app a logo for notifications, the tab and the home screen ([#33](https://github.com/Haashiraaa/log-book/issues/33)) ([5f00158](https://github.com/Haashiraaa/log-book/commit/5f001585a8c324b7a1c04e9668682ee13d0482f2))

## [0.12.0](https://github.com/Haashiraaa/log-book/compare/v0.11.0...v0.12.0) (2026-11-13)


### Features

* **frontend:** make Gate and Inside live, and add a night theme ([#32](https://github.com/Haashiraaa/log-book/issues/32)) ([abe29ee](https://github.com/Haashiraaa/log-book/commit/abe29ee1949f8799a1b999217fa36b414d881d98))

## [0.11.0](https://github.com/Haashiraaa/log-book/compare/v0.10.2...v0.11.0) (2026-11-13)


### ⚠ BREAKING CHANGES

* the console commands are now `log-book` and `log-book-admin` (were `tetracore-log` and `tetracore-admin`); run `pip install -e .` again after updating. The default JWT issuer is now `log-book`, so access tokens issued before the update are refused once and the app refreshes them on its own.

### Refactoring

* rename the project to Log Book ([#30](https://github.com/Haashiraaa/log-book/issues/30)) ([4dbfec0](https://github.com/Haashiraaa/log-book/commit/4dbfec0a327c6aad23319d4e96286245f1fe09e0))

## [0.10.2](https://github.com/Haashiraaa/log-book/compare/v0.10.1...v0.10.2) (2026-11-13)


### Bug fixes

* **notifications:** give each test notification its own tag ([#28](https://github.com/Haashiraaa/log-book/issues/28)) ([6438176](https://github.com/Haashiraaa/log-book/commit/6438176d1602c83b9300cac6331c8c59c9bc31f3))

## [0.10.1](https://github.com/Haashiraaa/log-book/compare/v0.10.0...v0.10.1) (2026-11-12)


### Bug fixes

* **notifications:** recover from stale push keys, add test push, stop staff left-inside warnings ([#25](https://github.com/Haashiraaa/log-book/issues/25)) ([e0e27a2](https://github.com/Haashiraaa/log-book/commit/e0e27a26c976208d5b67a2c2b3673b730cdfb770))

## [0.10.0](https://github.com/Haashiraaa/log-book/compare/v0.9.0...v0.10.0) (2026-11-12)


### Features

* **scripts:** add the tetracore-admin command ([#23](https://github.com/Haashiraaa/log-book/issues/23)) ([a615934](https://github.com/Haashiraaa/log-book/commit/a615934e7a0443addb3cadc200912e1fef96905a))

## [0.9.0](https://github.com/Haashiraaa/log-book/compare/v0.8.0...v0.9.0) (2026-11-12)


### Features

* **trucks:** truck queue, facility gates and the officers' duty log ([#21](https://github.com/Haashiraaa/log-book/issues/21)) ([76ae068](https://github.com/Haashiraaa/log-book/commit/76ae0683a6ae908be68a5ebf4105649d56fc4637))

## [0.8.0](https://github.com/Haashiraaa/log-book/compare/v0.7.0...v0.8.0) (2026-11-11)


### Features

* **notifications:** live admin feed of every event, warnings and browser push ([#19](https://github.com/Haashiraaa/log-book/issues/19)) ([024b57e](https://github.com/Haashiraaa/log-book/commit/024b57e10e5bea202860f925f38e8c84067373b7))

## [0.7.0](https://github.com/Haashiraaa/log-book/compare/v0.6.0...v0.7.0) (2026-11-11)


### Features

* **logs:** search visitors and staff by phone as the number is typed ([#17](https://github.com/Haashiraaa/log-book/issues/17)) ([564149d](https://github.com/Haashiraaa/log-book/commit/564149d8bc9a0c1802d4c39d57a6ef7fcab3361e))

## [0.6.0](https://github.com/Haashiraaa/log-book/compare/v0.5.0...v0.6.0) (2026-11-11)


### Features

* **logs:** phone lookup, staff capacity, full names and enforced sign-out ([#15](https://github.com/Haashiraaa/log-book/issues/15)) ([edc566d](https://github.com/Haashiraaa/log-book/commit/edc566da5a01fbca3cdc5e5f8b5601fc11550739))

## [0.5.0](https://github.com/Haashiraaa/log-book/compare/v0.4.1...v0.5.0) (2026-11-11)


### Features

* issue facility codes from the state (CNG-LAG-01) ([#13](https://github.com/Haashiraaa/log-book/issues/13)) ([578ae3c](https://github.com/Haashiraaa/log-book/commit/578ae3c9d081f16e2496bb5b5c04b71b68c0582a))

## [0.4.1](https://github.com/Haashiraaa/log-book/compare/v0.4.0...v0.4.1) (2026-11-11)


### Documentation

* document scripts and let admin_manager list every account ([#11](https://github.com/Haashiraaa/log-book/issues/11)) ([a79b38c](https://github.com/Haashiraaa/log-book/commit/a79b38c511e20429a1c69deecde2615f38764c4b))

## [0.4.0](https://github.com/Haashiraaa/log-book/compare/v0.3.0...v0.4.0) (2026-11-11)


### Features

* **frontend:** hi-vis redesign with visitor and staff logs ([#9](https://github.com/Haashiraaa/log-book/issues/9)) ([6981b51](https://github.com/Haashiraaa/log-book/commit/6981b51afdb3334301e1dee4f79c6201b3eaf046))

## [0.3.0](https://github.com/Haashiraaa/log-book/compare/v0.2.0...v0.3.0) (2026-11-11)


### Features

* add visitor and staff logs with in and out signatures ([#7](https://github.com/Haashiraaa/log-book/issues/7)) ([07f3214](https://github.com/Haashiraaa/log-book/commit/07f32148ae73363ad4c0b8323bf458ccde2398cb))

## [0.2.0](https://github.com/Haashiraaa/log-book/compare/v0.1.0...v0.2.0) (2026-11-11)


### ⚠ BREAKING CHANGES

* drop super admin and make role a free-form label; admins are managed only from scripts/admin_manager.py

### Features

* add visitor and staff log spaces (read-only for now) ([748e857](https://github.com/Haashiraaa/log-book/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))
* drop super admin and make role a free-form label; admins are managed only from scripts/admin_manager.py ([748e857](https://github.com/Haashiraaa/log-book/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))
* initialize gate-log backend, database schema and migrations ([748e857](https://github.com/Haashiraaa/log-book/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))


### Refactoring

* split long functions, share entry-log queries, split schemas by area and register routers in one list ([748e857](https://github.com/Haashiraaa/log-book/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))


### Documentation

* require squash merges so release-please can read commits ([748e857](https://github.com/Haashiraaa/log-book/commit/748e857f9ea093a51d8a657fd66ccac813c5613b))

## 0.1.0 (baseline)

Everything built before release automation existed: the gate-log schema and migrations, officer
login with PIN lockout and revocable sessions, admin and super-admin account management, truck
sign-in and sign-out with signatures, and the web frontend.
