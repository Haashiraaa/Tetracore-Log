# backend/src/db/queries/events.py

"""SQL for the notification feed: events, each admin's read cursor, push subscriptions.
SQL only: no commits, no rules."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import (
    Event,
    EventCursor,
    Facility,
    Officer,
    PushSubscription,
)
from backend.src.models import ADMIN_KINDS, GATE_KINDS

# ---- events ----


def add_event(
    db: Session, *, kind: str, severity: str, summary: str,
    facility_id: Optional[uuid.UUID], actor_id: Optional[uuid.UUID],
    entry_id: Optional[uuid.UUID] = None,
) -> Event:
    """Added to the open transaction; flushed so it has its id. The caller commits."""
    event = Event(kind=kind, severity=severity, summary=summary[:300],
                  facility_id=facility_id, actor_id=actor_id, entry_id=entry_id)
    db.add(event)
    db.flush()
    return event


def add_left_inside(
    db: Session, *, summary: str, facility_id: uuid.UUID, entry_id: uuid.UUID
) -> Optional[int]:
    """The id of the new event, or None if this entry was already reported."""
    stmt = (
        pg_insert(Event)
        .values(kind="left_inside", severity="warning", summary=summary[:300],
                facility_id=facility_id, entry_id=entry_id)
        .on_conflict_do_nothing(
            index_elements=["entry_id"], index_where=text("kind = 'left_inside'"))
        .returning(Event.id))
    return db.execute(stmt).scalar_one_or_none()


def list_events(
    db: Session, *, limit: int, before_id: Optional[int] = None,
    after_id: Optional[int] = None, facility_code: Optional[str] = None,
    group: Optional[str] = None,
) -> list[tuple[Event, Optional[str], Optional[str]]]:
    """(event, facility code, actor's name). Newest first, or with `after_id` everything
    newer than it, still newest first."""
    stmt = (
        select(Event, Facility.code, Officer.full_name)
        .outerjoin(Facility, Facility.id == Event.facility_id)
        .outerjoin(Officer, Officer.id == Event.actor_id)
        .order_by(Event.id.desc())
        .limit(limit))
    if before_id is not None:
        stmt = stmt.where(Event.id < before_id)
    if after_id is not None:
        stmt = stmt.where(Event.id > after_id)
    if facility_code:
        stmt = stmt.where(Facility.code == normalize_code(facility_code))
    if group == "gate":
        stmt = stmt.where(Event.kind.in_(GATE_KINDS))
    elif group == "admin":
        stmt = stmt.where(Event.kind.in_(ADMIN_KINDS))
    elif group == "warnings":
        stmt = stmt.where(Event.severity == "warning")
    return [(e, c, n) for e, c, n in db.execute(stmt).all()]


def latest_id(db: Session) -> int:
    return db.scalar(select(func.coalesce(func.max(Event.id), 0))) or 0


def count_after(db: Session, last_read_id: int) -> int:
    return db.scalar(select(func.count(Event.id)).where(Event.id > last_read_id)) or 0


def event_with_facility(db: Session, event_id: int) -> Optional[tuple[Event, Optional[str]]]:
    row = db.execute(
        select(Event, Facility.code)
        .outerjoin(Facility, Facility.id == Event.facility_id)
        .where(Event.id == event_id)).first()
    return None if row is None else (row[0], row[1])


# ---- read cursor ----


def get_cursor(db: Session, officer_id: uuid.UUID) -> Optional[int]:
    return db.scalar(select(EventCursor.last_read_id).where(EventCursor.officer_id == officer_id))


def set_cursor(db: Session, officer_id: uuid.UUID, last_read_id: int) -> None:
    """Moves forward only: reading an old page never makes newer events unread again."""
    stmt = pg_insert(EventCursor).values(officer_id=officer_id, last_read_id=last_read_id)
    stmt = stmt.on_conflict_do_update(
        index_elements=["officer_id"],
        set_={"last_read_id": func.greatest(EventCursor.last_read_id, last_read_id)})
    db.execute(stmt)


# ---- push ----


def save_subscription(
    db: Session, *, officer_id: uuid.UUID, endpoint: str, p256dh: str, auth: str
) -> None:
    """The same browser turning push on again (maybe as another admin) just re-points it."""
    stmt = pg_insert(PushSubscription).values(
        id=uuid.uuid4(), officer_id=officer_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    stmt = stmt.on_conflict_do_update(
        index_elements=["endpoint"],
        set_={"officer_id": officer_id, "p256dh": p256dh, "auth": auth,
              "created_at": func.now()})
    db.execute(stmt)


def delete_subscription(db: Session, *, officer_id: uuid.UUID, endpoint: str) -> None:
    db.execute(delete(PushSubscription).where(
        PushSubscription.officer_id == officer_id, PushSubscription.endpoint == endpoint))


def delete_subscription_by_endpoint(db: Session, endpoint: str) -> None:
    db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))


def admin_subscriptions(db: Session) -> list[PushSubscription]:
    """Every browser of every active admin."""
    return list(db.scalars(
        select(PushSubscription)
        .join(Officer, Officer.id == PushSubscription.officer_id)
        .where(Officer.is_admin.is_(True), Officer.is_active.is_(True))))
