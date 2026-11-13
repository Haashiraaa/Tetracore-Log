# backend/src/db/queries/occurrences.py

"""SQL for the events log (officer notes). SQL only: no commits, no rules (those live in
api/occurrence_service.py).

Rows come back as (note, facility_code, officer_name, has_signature). The signature blob
stays deferred."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import DutyEntry, Facility, OccurrenceEntry, Officer


def _select() -> Select[Any]:
    return (
        select(OccurrenceEntry, Facility.code, Officer.full_name,
               OccurrenceEntry.signature.is_not(None))
        .join(Facility, Facility.id == OccurrenceEntry.facility_id)
        .join(Officer, Officer.id == OccurrenceEntry.officer_id)
        .execution_options(populate_existing=True))


def _in_scope(stmt: Select[Any], scope: uuid.UUID | None) -> Select[Any]:
    return stmt if scope is None else stmt.where(OccurrenceEntry.facility_id == scope)


def get(db: Session, note_id: uuid.UUID, scope: uuid.UUID | None) -> Any | None:
    return db.execute(_in_scope(_select().where(OccurrenceEntry.id == note_id), scope)).first()


def get_signature(db: Session, note_id: uuid.UUID, scope: uuid.UUID | None) -> Any | None:
    """Row (bytes | None,) or None if the note is not visible."""
    stmt = select(OccurrenceEntry.signature).where(OccurrenceEntry.id == note_id)
    if scope is not None:
        stmt = stmt.where(OccurrenceEntry.facility_id == scope)
    return db.execute(stmt).first()


def duty_signature(db: Session, officer_id: uuid.UUID) -> bytes | None:
    """The signature this officer most recently drew when going on duty, or None."""
    return db.scalar(
        select(DutyEntry.signature_in)
        .where(DutyEntry.officer_id == officer_id, DutyEntry.signature_in.is_not(None))
        .order_by(DutyEntry.on_duty_at.desc(), DutyEntry.id)
        .limit(1))


def has_duty_signature(db: Session, officer_id: uuid.UUID) -> bool:
    return db.scalar(
        select(DutyEntry.id)
        .where(DutyEntry.officer_id == officer_id, DutyEntry.signature_in.is_not(None))
        .limit(1)) is not None


def insert(db: Session, **values: Any) -> bool:
    """True if inserted, False if that id already existed (a retry). Never overwrites."""
    stmt = (pg_insert(OccurrenceEntry).values(**values)
            .on_conflict_do_nothing(index_elements=["id"]).returning(OccurrenceEntry.id))
    return db.execute(stmt).scalar_one_or_none() is not None


def list_entries(
    db: Session, *, scope: uuid.UUID | None, facility_code: Optional[str] = None,
    open_only: bool = False, date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None, limit: int = 50, offset: int = 0,
) -> list[Any]:
    """Newest first. facility_code is honoured only when scope is None. date_to is
    exclusive. `open_only` means nothing for notes and is ignored."""
    del open_only
    stmt = _in_scope(_select(), scope)
    if scope is None and facility_code:
        stmt = stmt.where(Facility.code == normalize_code(facility_code))
    if date_from is not None:
        stmt = stmt.where(OccurrenceEntry.logged_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(OccurrenceEntry.logged_at < date_to)
    stmt = stmt.order_by(OccurrenceEntry.logged_at.desc(), OccurrenceEntry.id)
    return list(db.execute(stmt.limit(limit).offset(offset)).all())
