# backend/src/api/schemas/visitors.py

"""Visitor log: full name, company, purpose of visit, items received, phone, time in +
signature, time out + signature (the last four come from the shared base classes)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, field_validator

from backend.src.api.schemas.common import (
    EntryOut,
    EntrySignInRequest,
    LookupOut,
    blank_to_none,
    full_name_field,
    phone_field,
)


class VisitorSignInRequest(EntrySignInRequest):
    full_name: str = Field(min_length=2, max_length=150)
    company: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=300)
    items_received: Optional[str] = Field(default=None, max_length=500)
    phone: str = Field(min_length=1, max_length=32)

    _blank = field_validator("company", "purpose", "items_received")(blank_to_none)
    _name = field_validator("full_name")(full_name_field)
    _phone = field_validator("phone")(phone_field)


class VisitorLookupOut(LookupOut):
    company: Optional[str]


class VisitorEntryOut(EntryOut):
    full_name: str
    company: Optional[str]
    purpose: Optional[str]
    items_received: Optional[str]
    phone: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "VisitorEntryOut":
        e = row[0]
        return cls(
            **cls.common_fields(row), full_name=e.full_name, company=e.company,
            purpose=e.purpose, items_received=e.items_received, phone=e.phone,
        )
