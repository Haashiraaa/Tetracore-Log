# backend/src/db/queries/duty.py

"""SQL for the duty log (security officers). SQL only: no commits, no rules (those live in
api/duty_service.py).

Rows come back as (entry, facility_code, officer_name, officer_code, has_signature_in,
has_signature_out). The signature blobs stay deferred."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import DutyEntry, Facility, Officer

Which = Literal["in", "out"]


def _select() -> Select[Any]:
    return (
        select(
            DutyEntry, Facility.code, Officer.full_name, Officer.officer_code,
            DutyEntry.signature_in.is_not(None), DutyEntry.signature_out.is_not(None))
        .join(Facility, Facility.id == DutyEntry.facility_id)
        .join(Officer, Officer.id == DutyEntry.officer_id)
        .execution_options(populate_existing=True))


def _in_scope(stmt: Select[Any], scope: uuid.UUID | None) -> Select[Any]:
    return stmt if scope is None else stmt.where(DutyEntry.facility_id == scope)


def get(db: Session, duty_id: uuid.UUID, scope: uuid.UUID | None) -> Any | None:
    return db.execute(_in_scope(_select().where(DutyEntry.id == duty_id), scope)).first()


def open_for_officer(db: Session, officer_id: uuid.UUID) -> DutyEntry | None:
    return db.scalar(select(DutyEntry).where(
        DutyEntry.officer_id == officer_id, DutyEntry.off_duty_at.is_(None)))


def open_gate(db: Session, officer_id: uuid.UUID) -> int | None:
    return db.scalar(select(DutyEntry.gate).where(
        DutyEntry.officer_id == officer_id, DutyEntry.off_duty_at.is_(None)))


def insert(db: Session, **values: Any) -> bool:
    """True if inserted, False if that id already existed (a retry)."""
    stmt = (pg_insert(DutyEntry).values(**values)
            .on_conflict_do_nothing(index_elements=["id"]).returning(DutyEntry.id))
    return db.execute(stmt).scalar_one_or_none() is not None


def close(
    db: Session, entry_id: uuid.UUID, *, at: datetime, ended_how: str,
    signature: Optional[bytes] = None,
) -> bool:
    """True if this call closed it. False = not found or already closed."""
    stmt = (
        update(DutyEntry)
        .where(DutyEntry.id == entry_id, DutyEntry.off_duty_at.is_(None))
        .values(off_duty_at=at, ended_how=ended_how, signature_out=signature,
                updated_at=func.now())
        .returning(DutyEntry.id)
        .execution_options(synchronize_session=False))
    return db.execute(stmt).scalar_one_or_none() is not None


def on_duty_now(db: Session, scope: uuid.UUID | None) -> list[Any]:
    stmt = _in_scope(_select().where(DutyEntry.off_duty_at.is_(None)), scope)
    return list(db.execute(stmt.order_by(
        Facility.code, DutyEntry.gate, DutyEntry.on_duty_at)).all())


def highest_open_gate(db: Session, facility_id: uuid.UUID) -> int | None:
    return db.scalar(select(func.max(DutyEntry.gate)).where(
        DutyEntry.facility_id == facility_id, DutyEntry.off_duty_at.is_(None)))


def list_entries(
    db: Session, *, scope: uuid.UUID | None, facility_code: Optional[str] = None,
    open_only: bool = False, date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None, limit: int = 50, offset: int = 0,
) -> list[Any]:
    """Newest first. facility_code is honoured only when scope is None."""
    stmt = _in_scope(_select(), scope)
    if scope is None and facility_code:
        stmt = stmt.where(Facility.code == normalize_code(facility_code))
    if open_only:
        stmt = stmt.where(DutyEntry.off_duty_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DutyEntry.on_duty_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(DutyEntry.on_duty_at < date_to)
    stmt = stmt.order_by(DutyEntry.on_duty_at.desc(), DutyEntry.id)
    return list(db.execute(stmt.limit(limit).offset(offset)).all())


def get_signature(
    db: Session, duty_id: uuid.UUID, scope: uuid.UUID | None, which: Which = "in"
) -> Any | None:
    column = DutyEntry.signature_in if which == "in" else DutyEntry.signature_out
    stmt = select(column).where(DutyEntry.id == duty_id)
    return db.execute(_in_scope(stmt, scope)).first()


# ---- for the warnings the server raises ----


def shifts_running_since(
    db: Session, cutoff: datetime
) -> list[tuple[uuid.UUID, uuid.UUID, str, int, datetime]]:
    """Open rows whose SHIFT began before `cutoff`: (shift_id, facility_id, officer name,
    gate, shift start). The shift start is the first row's on_duty_at."""
    first = aliased(DutyEntry)
    rows = db.execute(
        select(DutyEntry.shift_id, DutyEntry.facility_id, Officer.full_name,
               DutyEntry.gate, first.on_duty_at)
        .join(Officer, Officer.id == DutyEntry.officer_id)
        .join(first, first.id == DutyEntry.shift_id)
        .where(DutyEntry.off_duty_at.is_(None), first.on_duty_at < cutoff)).all()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


def vacated_gates(
    db: Session, *, older_than: datetime, newer_than: datetime
) -> list[tuple[uuid.UUID, uuid.UUID, int, datetime]]:
    """Gates that were manned and are not now: (the last row that left, facility id, gate,
    when it left). Only if that was between `newer_than` and `older_than`, the gate is
    within the facility's gate count, and nobody is on it."""
    last = (
        select(DutyEntry)
        .where(DutyEntry.off_duty_at.is_not(None))
        .distinct(DutyEntry.facility_id, DutyEntry.gate)
        .order_by(DutyEntry.facility_id, DutyEntry.gate, DutyEntry.off_duty_at.desc())
        .subquery())
    row = aliased(DutyEntry, last)
    manned = aliased(DutyEntry)
    nobody_now = ~select(manned.id).where(
        manned.facility_id == row.facility_id, manned.gate == row.gate,
        manned.off_duty_at.is_(None)).exists()
    rows = db.execute(
        select(row.id, row.facility_id, row.gate, row.off_duty_at)
        .join(Facility, Facility.id == row.facility_id)
        .where(Facility.is_active.is_(True), row.gate <= Facility.gate_count,
               row.off_duty_at < older_than, row.off_duty_at > newer_than, nobody_now)
    ).all()
    return [(r[0], r[1], r[2], r[3]) for r in rows]
