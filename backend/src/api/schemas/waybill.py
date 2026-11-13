# backend/src/api/schemas/waybill.py

"""Waybill log: a courier brings goods. Courier name, phone, the items (name, whole-number
quantity, optional unit), whether they came with a vehicle and its plate, time in + signature,
time out + signature (the last four come from the shared base classes)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, StrictBool, field_validator, model_validator

from backend.src.api.schemas.common import (
    MAX_ITEMS,
    EntryOut,
    Item,
    LookupOut,
    PersonSignInRequest,
    full_name_field,
    phone_field,
)
from backend.src.db.orm._helpers import normalize_plate


class WaybillSignInRequest(PersonSignInRequest):
    """A courier signs in. `came_by_vehicle` says whether they drove here: if so the plate
    is required, if not (on foot) there is none."""

    full_name: str = Field(min_length=2, max_length=150)  # the courier
    phone: str = Field(min_length=1, max_length=32)
    items: list[Item] = Field(min_length=1, max_length=MAX_ITEMS)
    came_by_vehicle: StrictBool = False
    plate_number: Optional[str] = Field(default=None, max_length=40)

    _name = field_validator("full_name")(full_name_field)
    _phone = field_validator("phone")(phone_field)

    @field_validator("plate_number")
    @classmethod
    def _plate(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        plate = normalize_plate(v)
        if not 2 <= len(plate) <= 20:
            raise ValueError("Plate number must be 2-20 letters/digits.")
        return plate

    @model_validator(mode="after")
    def _plate_matches_vehicle(self) -> "WaybillSignInRequest":
        if self.came_by_vehicle and self.plate_number is None:
            raise ValueError("Give the plate number of the vehicle the courier came with.")
        if not self.came_by_vehicle and self.plate_number is not None:
            raise ValueError("A courier who came on foot has no plate number.")
        return self


class WaybillLookupOut(LookupOut):
    """What the courier last came with, to prefill the form (the items are new each visit)."""

    came_by_vehicle: bool
    plate_number: Optional[str]


class WaybillEntryOut(EntryOut):
    full_name: str
    phone: Optional[str]
    items: list[Item]
    came_by_vehicle: bool
    plate_number: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "WaybillEntryOut":
        e = row[0]
        return cls(**cls.common_fields(row), full_name=e.full_name, phone=e.phone,
                   items=e.items or [], came_by_vehicle=e.came_by_vehicle,
                   plate_number=e.plate_number)
