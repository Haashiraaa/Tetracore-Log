# backend/src/api/schemas/common.py

"""Pieces shared by every schema module."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


def require_tz(v: Optional[datetime]) -> Optional[datetime]:
    if v is not None and v.tzinfo is None:
        raise ValueError(
            "Timestamp must include a timezone offset, e.g. 2026-10-17T19:00:00+01:00")
    return v


class EntryOut(BaseModel):
    """What every log (trucks, visitors, staff) says about a sign-in. A log adds its own
    fields on top. Built from a row of db/queries/_entries.py:
    (entry, facility_code, has_signature, signed_in_by_name, signed_out_by_name)."""

    id: uuid.UUID
    facility_id: uuid.UUID
    facility_code: str
    signed_in_at: datetime
    signed_out_at: Optional[datetime]
    signed_in_by: uuid.UUID
    signed_in_by_name: str
    signed_out_by: Optional[uuid.UUID]
    signed_out_by_name: Optional[str]
    device_id: Optional[str]
    has_signature: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def common_fields(row: Any) -> dict[str, Any]:
        e, facility_code, has_signature, in_name, out_name = row
        return dict(
            id=e.id, facility_id=e.facility_id, facility_code=facility_code,
            signed_in_at=e.signed_in_at, signed_out_at=e.signed_out_at,
            signed_in_by=e.signed_in_by, signed_in_by_name=in_name,
            signed_out_by=e.signed_out_by, signed_out_by_name=out_name,
            device_id=e.device_id, has_signature=bool(has_signature),
            created_at=e.created_at, updated_at=e.updated_at,
        )
