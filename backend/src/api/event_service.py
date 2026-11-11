# backend/src/api/event_service.py

"""The notification feed for the global admin.

Writing: `record` adds an event to the transaction of whatever just happened (the caller
commits, so the event exists exactly when the thing does), then the caller hands the id to
`announce` for browser push.

    ev = event_service.record(db, kind="visitor_in", summary=..., facility_id=..., actor_id=...)
    db.commit()
    event_service.announce(ev.id)

Reading: the feed, an unread count per admin, and "mark as read"."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.src.api import push
from backend.src.api.schemas import EventOut, EventsSummaryOut
from backend.src.config.settings import Settings
from backend.src.db.orm.tables import Event, StaffEntry, TruckEntry, VisitorEntry
from backend.src.db.queries import events as q
from backend.src.models import event_severity
from backend.src.security.tokens import utcnow

# ---- writing ----


def record(
    db: Session, *, kind: str, summary: str, facility_id: Optional[uuid.UUID],
    actor_id: Optional[uuid.UUID], entry_id: Optional[uuid.UUID] = None,
) -> Event:
    return q.add_event(
        db, kind=kind, severity=event_severity(kind), summary=summary,
        facility_id=facility_id, actor_id=actor_id, entry_id=entry_id)


def announce(*event_ids: int) -> None:
    """Browser push, after the commit. Never raises, never waits."""
    push.dispatch(event_ids)


# ---- "left inside": nobody does it, so the server notices ----

_LOGS = (
    (TruckEntry, "Truck {who}", "plate_number"),
    (VisitorEntry, "{who}", "full_name"),
    (StaffEntry, "{who}", "full_name"),
)


def check_left_inside(db: Session) -> list[int]:
    """Warn once for every entry still open LEFT_INSIDE_HOURS after sign-in. Safe to run
    from several servers at once: the database lets only one of them raise each warning.
    Returns the new event ids (already committed and announced)."""
    cutoff = utcnow() - timedelta(hours=Settings.LEFT_INSIDE_HOURS)
    hours = Settings.LEFT_INSIDE_HOURS
    new: list[int] = []
    for model, template, who_column in _LOGS:
        rows = db.execute(
            select(model.id, model.facility_id, getattr(model, who_column))
            .where(model.signed_out_at.is_(None), model.signed_in_at < cutoff)
        ).all()
        for entry_id, facility_id, who in rows:
            summary = (f"{template.format(who=who)} is still inside, "
                       f"{hours}+ hours after signing in.")
            event_id = q.add_left_inside(
                db, summary=summary, facility_id=facility_id, entry_id=entry_id)
            if event_id is not None:
                new.append(event_id)
    db.commit()
    announce(*new)
    return new


# ---- reading ----


def list_events(
    db: Session, *, limit: int, before_id: Optional[int], after_id: Optional[int],
    facility_code: Optional[str], group: Optional[str],
) -> list[EventOut]:
    rows = q.list_events(
        db, limit=limit, before_id=before_id, after_id=after_id,
        facility_code=facility_code, group=group)
    return [EventOut.build(e, code, name) for e, code, name in rows]


def summary(db: Session, officer_id: uuid.UUID) -> EventsSummaryOut:
    """What the bell shows. An admin's first look starts them at "all read", not at the
    whole history as unread."""
    latest = q.latest_id(db)
    cursor = q.get_cursor(db, officer_id)
    if cursor is None:
        q.set_cursor(db, officer_id, latest)
        db.commit()
        cursor = latest
    return EventsSummaryOut(
        latest_id=latest, last_read_id=cursor, unread=q.count_after(db, cursor))


def mark_read(db: Session, officer_id: uuid.UUID, up_to_id: Optional[int]) -> EventsSummaryOut:
    """Read up to `up_to_id` (default: everything so far)."""
    q.set_cursor(db, officer_id, q.latest_id(db) if up_to_id is None else up_to_id)
    db.commit()
    return summary(db, officer_id)


# ---- push subscriptions ----


def subscribe(db: Session, officer_id: uuid.UUID, *, endpoint: str, p256dh: str, auth: str) -> None:
    q.save_subscription(db, officer_id=officer_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    db.commit()


def unsubscribe(db: Session, officer_id: uuid.UUID, endpoint: str) -> None:
    q.delete_subscription(db, officer_id=officer_id, endpoint=endpoint)
    db.commit()

