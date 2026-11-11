# backend/src/api/schemas/staff.py

"""Staff log: name, time in + signature, time out + signature (the last three come from
the shared base classes)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from backend.src.api.schemas.common import EntryOut, EntrySignInRequest


class StaffSignInRequest(EntrySignInRequest):
    full_name: str = Field(min_length=2, max_length=150)


class StaffEntryOut(EntryOut):
    full_name: str

    @classmethod
    def from_row(cls, row: Any) -> "StaffEntryOut":
        return cls(**cls.common_fields(row), full_name=row[0].full_name)
