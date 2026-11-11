

# scripts/admin_manager.py

"""The ONLY place admins are set or dropped. No API route can do it.

    python -m scripts.admin_manager create --code ADM-01 --name "Ada Obi"
    python -m scripts.admin_manager grant  --code OFF-003 --facility CNG-A
    python -m scripts.admin_manager revoke --code ADM-01
    python -m scripts.admin_manager reset-pin --code ADM-01
    python -m scripts.admin_manager list

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


def cmd_create(db: Session, args: argparse.Namespace) -> int:
    pin = _prompt_pin()
    if pin is None:
        return 1
    officer = accounts.create_officer(
        db, officer_code=args.code, full_name=args.name, pin=pin,
        role=args.role, is_admin=True, facility_code=args.facility)
    db.commit()
    print(f"Admin {officer.officer_code} created (role={officer.role}). id={officer.id}")
    return 0


def cmd_grant(db: Session, args: argparse.Namespace) -> int:
    officer = _target(db, args)
    accounts.grant_admin(officer)
    db.commit()
    print(f"{officer.officer_code} is now an admin.")
    return 0


def cmd_revoke(db: Session, args: argparse.Namespace) -> int:
    officer = _target(db, args)
    accounts.revoke_admin(db, officer, force=args.force)
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


def cmd_list(db: Session, _args: argparse.Namespace) -> int:
    rows = db.execute(
        select(Officer, Facility.code)
        .outerjoin(Facility, Facility.id == Officer.facility_id)
        .where(Officer.is_admin.is_(True))
        .order_by(Officer.officer_code)
    ).all()
    if not rows:
        print("No admins.")
    for officer, facility_code in rows:
        state = "active" if officer.is_active else "DISABLED"
        print(f"{officer.officer_code:<10} {officer.full_name:<28} "
              f"role={officer.role:<16} facility={facility_code or '-':<12} {state}")
    return 0


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
    "list": ("list admins", cmd_list, lambda _p: None),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Tetracore Log admins.")
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
