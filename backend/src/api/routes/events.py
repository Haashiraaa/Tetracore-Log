# backend/src/api/routes/events.py

"""The global admin's notification feed and browser push switch. Admin-only, like admin.py:
an admin already reads every facility, so the feed shows every facility."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.src.api import event_service, push
from backend.src.api.deps import require_admin
from backend.src.api.schemas import (
    CurrentOfficer,
    EventOut,
    EventsSummaryOut,
    MarkReadRequest,
    PushConfigOut,
    PushSubscribeRequest,
    PushTestOut,
    PushUnsubscribeRequest,
)
from backend.src.config.settings import Settings
from backend.src.db.session import get_db
from backend.src.exceptions.errors import ConflictError

router = APIRouter(
    prefix="/admin/events", tags=["notifications"], dependencies=[Depends(require_admin)]
)
push_router = APIRouter(
    prefix="/admin/push", tags=["notifications"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[EventOut])
def list_events(
    limit: int = Query(50, ge=1, le=200),
    before_id: Optional[int] = Query(None, ge=1, description="older than this event"),
    after_id: Optional[int] = Query(None, ge=0, description="only newer than this event"),
    facility_code: Optional[str] = Query(None, max_length=32),
    group: Optional[Literal["gate", "admin", "warnings"]] = None,
    db: Session = Depends(get_db),
) -> list[EventOut]:
    """Newest first. Page back with before_id; poll forward with after_id."""
    return event_service.list_events(
        db, limit=limit, before_id=before_id, after_id=after_id,
        facility_code=facility_code, group=group)


@router.get("/summary", response_model=EventsSummaryOut)
def events_summary(
    admin: CurrentOfficer = Depends(require_admin), db: Session = Depends(get_db),
) -> EventsSummaryOut:
    """Cheap enough to poll every few seconds: the newest id and this admin's unread count."""
    return event_service.summary(db, admin.officer_id)


@router.post("/read", response_model=EventsSummaryOut)
def mark_read(
    body: MarkReadRequest,
    admin: CurrentOfficer = Depends(require_admin), db: Session = Depends(get_db),
) -> EventsSummaryOut:
    return event_service.mark_read(db, admin.officer_id, body.up_to_id)


@push_router.get("/config", response_model=PushConfigOut)
def push_config() -> PushConfigOut:
    return PushConfigOut(public_key=Settings.VAPID_PUBLIC_KEY if Settings.push_enabled() else None)


@push_router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def push_subscribe(
    body: PushSubscribeRequest,
    admin: CurrentOfficer = Depends(require_admin), db: Session = Depends(get_db),
) -> Response:
    event_service.subscribe(
        db, admin.officer_id, endpoint=body.endpoint,
        p256dh=body.keys.p256dh, auth=body.keys.auth)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@push_router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def push_unsubscribe(
    body: PushUnsubscribeRequest,
    admin: CurrentOfficer = Depends(require_admin), db: Session = Depends(get_db),
) -> Response:
    event_service.unsubscribe(db, admin.officer_id, body.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@push_router.post("/test", response_model=PushTestOut)
def push_test(
    admin: CurrentOfficer = Depends(require_admin), db: Session = Depends(get_db),
) -> PushTestOut:
    """Send a test notification to the calling admin's own browsers and report what happened."""
    if not Settings.push_enabled():
        raise ConflictError("Push is not set up on the server.")
    return PushTestOut(**push.send_test(db, admin.officer_id))
