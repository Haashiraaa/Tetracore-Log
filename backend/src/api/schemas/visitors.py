# backend/src/api/schemas/visitors.py

"""Visitor log: full name, company, purpose of visit, items received, phone, time in +
signature, time out + signature (the last four come from the shared base classes)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, field_validator

from backend.src.api.schemas.common import EntryOut, EntrySignInRequest, blank_to_none


class VisitorSignInRequest(EntrySignInRequest):
    full_name: str = Field(min_length=2, max_length=150)
    company: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=300)
    items_received: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=32)

    _blank = field_validator("company", "purpose", "items_received", "phone")(blank_to_none)


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
