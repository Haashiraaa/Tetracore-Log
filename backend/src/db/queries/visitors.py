# backend/src/db/queries/visitors.py

"""Visitor log SQL. SPACE ONLY: what every log shares comes from _entries.py. Add the
queries that are specific to visitors here once the details are decided."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.src.db.orm.tables import VisitorEntry
from backend.src.db.queries import _entries


def get_entry(db: Session, entry_id: uuid.UUID, scope: uuid.UUID | None) -> Any | None:
    return _entries.get_entry(db, VisitorEntry, entry_id, scope)


def get_signature(
    db: Session, entry_id: uuid.UUID, scope: uuid.UUID | None
) -> Any | None:
    return _entries.get_signature(db, VisitorEntry, entry_id, scope)


def list_entries(db: Session, **filters: Any) -> list[Any]:
    return _entries.list_entries(db, VisitorEntry, **filters)
