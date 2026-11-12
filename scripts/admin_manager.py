

# scripts/admin_manager.py

"""The ONLY place admins are set or dropped. No API route can do it.

    tetracore-admin create --code ADM-01 --name "Ada Obi"
    tetracore-admin grant  --code OFF-003 --facility CNG-LAG-01
    tetracore-admin revoke --code ADM-01
    tetracore-admin reset-pin --code ADM-01
    tetracore-admin list          # admins only
    tetracore-admin list --all    # every account, admin or not

`tetracore-admin` is registered in pyproject.toml (`[project.scripts]`) and appears after
`pip install -e .`. `python -m scripts.admin_manager ...` does the same thing.

Add --facility CODE for accounts that belong to a facility; leave it out for a
global account. PINs are prompted (hidden), never passed as arguments. `revoke`
keeps the account (role, facility, code) and only removes admin powers; disable
it afterwards from the admin page if the person is gone.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.src.db.orm.tables import Facility, Officer
from backend.src.db.queries import events as events_q
from backend.src.db.session import create_session
from backend.src.security import accounts

Handler = Callable[[Session, argparse.Namespace], int]


def _prompt_pin() -> str | None:
    pin = getpass.getpass("PIN (6-10 digits): ")
    if pin != getpass.getpass("Repeat PIN: "):
        print("PINs do not match.", file=sys.stderr)
        return None
    return pin


def _target(db: Session, args: argparse.Namespace) -> Officer:
    return accounts.find_officer(
        db, officer_code=args.code, facility_code=args.facility)


def _record(db: Session, kind: str, officer: Officer, summary: str) -> None:
    """Tell the feed. Same transaction as the change. From the console there is no browser
    push (only the running server sends it); the event is in the feed for the next look."""
    events_q.add_event(
        db, kind=kind, severity="info", summary=f"{summary} (from the server console).",
        facility_id=officer.facility_id, actor_id=None)


def cmd_create(db: Session, args: argparse.Namespace) -> int:
    pin = _prompt_pin()
    if pin is None:
        return 1
    officer = accounts.create_officer(
        db, officer_code=args.code, full_name=args.name, pin=pin,
        role=args.role, is_admin=True, facility_code=args.facility)
    _record(db, "admin_granted", officer,
            f"{officer.full_name} ({officer.officer_code}) was created as an admin")
    db.commit()
    print(f"Admin {officer.officer_code} created (role={officer.role}). id={officer.id}")
    return 0


def cmd_grant(db: Session, args: argparse.Namespace) -> int:
    officer = _target(db, args)
    accounts.grant_admin(officer)
    _record(db, "admin_granted", officer,
            f"{officer.full_name} ({officer.officer_code}) was made an admin")
    db.commit()
    print(f"{officer.officer_code} is now an admin.")
    return 0


def cmd_revoke(db: Session, args: argparse.Namespace) -> int:
    officer = _target(db, args)
    accounts.revoke_admin(db, officer, force=args.force)
    _record(db, "admin_revoked", officer,
            f"{officer.full_name} ({officer.officer_code}) is no longer an admin")
    db.commit()
    print(f"{officer.officer_code} is no longer an admin (the account is unchanged).")
    return 0


def cmd_reset_pin(db: Session, args: argparse.Namespace) -> int:
    officer = _target(db, args)
    pin = _prompt_pin()
    if pin is None:
        return 1
    accounts.reset_admin_pin(db, officer, pin)
    db.commit()
    print(f"PIN reset for {officer.officer_code}; all sessions revoked.")
    return 0


def cmd_list(db: Session, args: argparse.Namespace) -> int:
    stmt = (
        select(Officer, Facility.code)
        .outerjoin(Facility, Facility.id == Officer.facility_id)
        .order_by(Officer.is_admin.desc(), Facility.code, Officer.officer_code)
    )
    if not args.all:
        stmt = stmt.where(Officer.is_admin.is_(True))
    rows = db.execute(stmt).all()
    if not rows:
        print("No accounts." if args.all else "No admins.")
    for officer, facility_code in rows:
        state = "active" if officer.is_active else "DISABLED"
        admin = "admin" if officer.is_admin else "-"
        print(f"{officer.officer_code:<10} {officer.full_name:<28} "
              f"role={officer.role:<16} facility={facility_code or '-':<12} "
              f"{admin:<6} {state}")
    return 0


def _add_list(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true",
                   help="include accounts that are not admins")


def _add_target(p: argparse.ArgumentParser) -> None:
    p.add_argument("--code", required=True, help="officer code")
    p.add_argument("--facility", default=None, help="facility code, if any")


def _add_create(p: argparse.ArgumentParser) -> None:
    _add_target(p)
    p.add_argument("--name", required=True)
    p.add_argument("--role", default="admin", help="free-form label (default: admin)")


def _add_revoke(p: argparse.ArgumentParser) -> None:
    _add_target(p)
    p.add_argument("--force", action="store_true",
                   help="allow dropping the last active admin")


# name -> (help, handler, add arguments)
COMMANDS: dict[str, tuple[str, Handler, Callable[[argparse.ArgumentParser], None]]] = {
    "create": ("create a NEW admin account", cmd_create, _add_create),
    "grant": ("make an existing account an admin", cmd_grant, _add_target),
    "revoke": ("drop admin powers, keep the account", cmd_revoke, _add_revoke),
    "reset-pin": ("set a new PIN for an admin", cmd_reset_pin, _add_target),
    "list": ("list admins (--all: every account)", cmd_list, _add_list),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tetracore-admin", description="Manage Tetracore Log admins.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (help_text, handler, add_args) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text)
        add_args(p)
        p.set_defaults(fn=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    with create_session() as db:
        try:
            return args.fn(db, args)
        except ValueError as exc:
            db.rollback()
            print(f"Error: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
