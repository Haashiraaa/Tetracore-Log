# backend/src/api/schemas/staff.py

"""Staff log: full name, capacity, phone, time in + signature, time out + signature (the
last two come from the shared base classes)."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from backend.src.api.schemas.common import (
    EntryOut,
    LookupOut,
    PersonSignInRequest,
    full_name_field,
    phone_field,
)


class StaffSignInRequest(PersonSignInRequest):
    full_name: str = Field(min_length=2, max_length=150)
    capacity: str = Field(min_length=2, max_length=100)  # free text
    phone: str = Field(min_length=1, max_length=32)

    _name = field_validator("full_name")(full_name_field)
    _phone = field_validator("phone")(phone_field)


class StaffLookupOut(LookupOut):
    capacity: str | None


class StaffEntryOut(EntryOut):
    full_name: str
    capacity: str | None
    phone: str | None

    @classmethod
    def from_row(cls, row: Any) -> "StaffEntryOut":
        e = row[0]
        return cls(**cls.common_fields(row), full_name=e.full_name,
                   capacity=e.capacity, phone=e.phone)
