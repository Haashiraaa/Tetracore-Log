# backend/src/api/schemas/visitors.py

"""Visitor log: full name, company, purpose of visit, items brought (name + quantity), phone,
time in + signature, time out + signature (the last four come from the shared base classes)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from backend.src.api.schemas.common import (
    EntryOut,
    LookupOut,
    PersonSignInRequest,
    blank_to_none,
    full_name_field,
    phone_field,
)

MAX_ITEMS = 30
MAX_QUANTITY = 100_000


class VisitorItem(BaseModel):
    """One thing the visitor brought: a name, a whole-number quantity, and an optional unit
    ("cartons", "litres"). The quantity must arrive as a JSON integer, never as text."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    quantity: StrictInt = Field(ge=1, le=MAX_QUANTITY)
    unit: Optional[str] = Field(default=None, max_length=20)

    _unit = field_validator("unit")(blank_to_none)


class VisitorSignInRequest(PersonSignInRequest):
    full_name: str = Field(min_length=2, max_length=150)
    company: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=300)
    items: list[VisitorItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    phone: str = Field(min_length=1, max_length=32)

    _blank = field_validator("company", "purpose")(blank_to_none)
    _name = field_validator("full_name")(full_name_field)
    _phone = field_validator("phone")(phone_field)


class VisitorLookupOut(LookupOut):
    company: Optional[str]


class VisitorEntryOut(EntryOut):
    full_name: str
    company: Optional[str]
    purpose: Optional[str]
    items: list[VisitorItem]
    items_received: Optional[str]  # old free text, only on lines from before `items`
    phone: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "VisitorEntryOut":
        e = row[0]
        return cls(
            **cls.common_fields(row), full_name=e.full_name, company=e.company,
            purpose=e.purpose, items=e.items or [], items_received=e.items_received,
            phone=e.phone,
        )
