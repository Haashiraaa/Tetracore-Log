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
from backend.src.db.orm.tables import Event, Facility, TruckEntry, VisitorEntry, WaybillEntry
from backend.src.db.queries import duty as duty_q
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


# ---- warnings nobody triggers, so the server notices ----

# Staff are left out on purpose: staying inside has many ordinary reasons, so it is only noise.
_PEOPLE_LOGS = (
    (VisitorEntry, "{who}", "full_name"),
    (WaybillEntry, "Courier {who}", "full_name"),
)


def _raise(db: Session, new: list[int], *, kind: str, summary: str,
           facility_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    event_id = q.add_raised(
        db, kind=kind, summary=summary, facility_id=facility_id, entry_id=entry_id)
    if event_id is not None:
        new.append(event_id)


def _check_left_inside(db: Session, new: list[int]) -> None:
    hours = Settings.LEFT_INSIDE_HOURS
    cutoff = utcnow() - timedelta(hours=hours)
    for model, template, column in _PEOPLE_LOGS:
        rows = db.execute(
            select(model.id, model.facility_id, getattr(model, column))
            .where(model.signed_out_at.is_(None), model.signed_in_at < cutoff)).all()
        for entry_id, facility_id, who in rows:
            _raise(db, new, kind="left_inside", facility_id=facility_id, entry_id=entry_id,
                   summary=f"{template.format(who=who)} is still inside, "
                           f"{hours}+ hours after signing in.")
    # Trucks count from when they entered. A queued truck is not inside.
    rows = db.execute(
        select(TruckEntry.id, TruckEntry.facility_id, TruckEntry.plate_number)
        .where(TruckEntry.status == "on_site", TruckEntry.entered_at < cutoff)).all()
    for entry_id, facility_id, plate in rows:
        _raise(db, new, kind="left_inside", facility_id=facility_id, entry_id=entry_id,
               summary=f"Truck {plate} is still inside, {hours}+ hours after entering.")


def _check_queued_too_long(db: Session, new: list[int]) -> None:
    hours = Settings.QUEUED_WARN_HOURS
    if hours <= 0:
        return
    cutoff = utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(TruckEntry.id, TruckEntry.facility_id, TruckEntry.plate_number)
        .where(TruckEntry.status == "queued", TruckEntry.signed_in_at < cutoff)).all()
    for entry_id, facility_id, plate in rows:
        _raise(db, new, kind="queued_too_long", facility_id=facility_id, entry_id=entry_id,
               summary=f"Truck {plate} has been in the queue for {hours}+ hours.")


def _check_on_duty_too_long(db: Session, new: list[int]) -> None:
    hours = Settings.DUTY_WARN_HOURS
    if hours <= 0:
        return
    cutoff = utcnow() - timedelta(hours=hours)
    for shift_id, facility_id, name, gate, _started in duty_q.shifts_running_since(db, cutoff):
        _raise(db, new, kind="on_duty_too_long", facility_id=facility_id, entry_id=shift_id,
               summary=f"{name} has been on duty for {hours}+ hours (gate {gate}).")


def _check_gate_unmanned(db: Session, new: list[int]) -> None:
    minutes = Settings.GATE_UNMANNED_MINUTES
    if minutes <= 0:
        return
    now = utcnow()
    for last_id, facility_id, gate, _left in duty_q.vacated_gates(
            db, older_than=now - timedelta(minutes=minutes),
            newer_than=now - timedelta(hours=24)):
        facility = db.get(Facility, facility_id)
        where = f" at {facility.code}" if facility is not None else ""
        _raise(db, new, kind="gate_unmanned", facility_id=facility_id, entry_id=last_id,
               summary=f"Gate {gate}{where} has had nobody on duty for {minutes}+ minutes.")


def check_warnings(db: Session) -> list[int]:
    """Raise every warning that is due. Safe to run from several servers at once: the
    database lets only one of them raise each one. Returns the new event ids (already
    committed and announced)."""
    new: list[int] = []
    _check_left_inside(db, new)
    _check_queued_too_long(db, new)
    _check_on_duty_too_long(db, new)
    _check_gate_unmanned(db, new)
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

