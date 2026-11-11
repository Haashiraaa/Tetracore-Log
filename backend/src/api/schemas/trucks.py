# backend/src/api/schemas/trucks.py

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from backend.src.api.schemas.common import (
    EntryOut,
    EntrySignInRequest,
    EntrySignOutRequest,
    blank_to_none,
    full_name_field,
)
from backend.src.db.orm._helpers import normalize_plate


class TruckLookupOut(BaseModel):
    truck_id: uuid.UUID
    plate_number: str
    driver_name: str
    driver_phone: Optional[str]
    company: Optional[str]
    # Set when this truck is currently inside (so the app can offer sign-out).
    open_entry_id: Optional[uuid.UUID]


class TruckSignInRequest(EntrySignInRequest):
    plate_number: str = Field(min_length=2, max_length=40)
    driver_name: str = Field(min_length=2, max_length=150)
    driver_phone: Optional[str] = Field(default=None, max_length=32)
    company: Optional[str] = Field(default=None, max_length=200)
    scm_purchased: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2)

    @field_validator("plate_number")
    @classmethod
    def _plate(cls, v: str) -> str:
        plate = normalize_plate(v)
        if not 2 <= len(plate) <= 20:
            raise ValueError("Plate number must be 2-20 letters/digits.")
        return plate

    _blank = field_validator("driver_phone", "company")(blank_to_none)
    _name = field_validator("driver_name")(full_name_field)


class TruckSignOutRequest(EntrySignOutRequest):
    scm_purchased: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2)


class TruckEntryOut(EntryOut):
    truck_id: uuid.UUID
    plate_number: str
    driver_name: str
    driver_phone: Optional[str]
    company: Optional[str]
    scm_purchased: Optional[Decimal]

    @classmethod
    def from_row(cls, row: Any) -> "TruckEntryOut":
        e = row[0]
        return cls(
            **cls.common_fields(row), truck_id=e.truck_id,
            plate_number=e.plate_number, driver_name=e.driver_name,
            driver_phone=e.driver_phone, company=e.company,
            scm_purchased=e.scm_purchased,
        )
