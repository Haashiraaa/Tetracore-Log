# backend/src/api/schemas/events.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.src.db.orm.tables import Event


class EventOut(BaseModel):
    id: int
    created_at: datetime
    kind: str
    severity: str
    summary: str
    facility_code: Optional[str]
    actor_name: Optional[str]
    entry_id: Optional[uuid.UUID]

    @classmethod
    def build(cls, e: Event, facility_code: Optional[str], actor_name: Optional[str]) -> "EventOut":
        return cls(
            id=e.id, created_at=e.created_at, kind=e.kind, severity=e.severity,
            summary=e.summary, facility_code=facility_code, actor_name=actor_name,
            entry_id=e.entry_id)


class EventsSummaryOut(BaseModel):
    """What the bell needs: the newest event id (to know if something new arrived), how far
    this admin has read, and how many events are beyond that."""

    latest_id: int
    last_read_id: int
    unread: int


class MarkReadRequest(BaseModel):
    up_to_id: Optional[int] = Field(default=None, ge=0)  # None = everything so far


class PushTestOut(BaseModel):
    """What the test notification did: how many of this admin's browsers there are, how many
    took it, and a plain reason for each that did not."""

    subscriptions: int
    sent: int
    failed: list[str]


class PushConfigOut(BaseModel):
    """public_key is None when the server has no push keys: the app then hides the switch."""

    public_key: Optional[str]


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushSubscribeRequest(BaseModel):
    """Exactly what the browser's PushSubscription.toJSON() gives."""

    endpoint: str = Field(min_length=10, max_length=1000)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=1000)
