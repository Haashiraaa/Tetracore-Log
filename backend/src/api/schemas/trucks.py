# backend/src/api/schemas/trucks.py

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.src.api.schemas.common import (
    EntryOut,
    EntrySignInRequest,
    EntrySignOutRequest,
    blank_to_none,
    full_name_field,
    require_tz,
)
from backend.src.db.orm._helpers import normalize_plate


class TruckLookupOut(BaseModel):
    truck_id: uuid.UUID
    plate_number: str
    driver_name: str
    driver_phone: Optional[str]
    company: Optional[str]
    # Set when this truck is in the middle of a visit (so the app can offer the next step),
    # with that visit's status: "queued" or "on_site".
    open_entry_id: Optional[uuid.UUID]
    open_entry_status: Optional[str]


class TruckSignInRequest(EntrySignInRequest):
    """Register a truck. By default it joins the queue (outside, no signature yet). With
    `enter_now` it is let in on the spot, which needs the driver's signature."""

    signature: Optional[str] = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default=None, max_length=400_000)
    enter_now: bool = False
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

    @model_validator(mode="after")
    def _signature_to_enter(self) -> "TruckSignInRequest":
        if self.enter_now and not (self.signature or "").strip():
            raise ValueError("The driver's signature is needed to let a truck in.")
        return self


class TruckEnterRequest(BaseModel):
    """Let a queued truck in: the driver signs on the way in."""

    entered_at: Optional[datetime] = None  # default: server time
    signature: str = Field(min_length=1, max_length=400_000)

    @field_validator("entered_at")
    @classmethod
    def _tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        return require_tz(v)


class TruckLeaveQueueRequest(BaseModel):
    """A queued truck gave up and left without entering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(min_length=2, max_length=300)
    left_at: Optional[datetime] = None  # default: server time

    @field_validator("left_at")
    @classmethod
    def _tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        return require_tz(v)


class TruckSignOutRequest(EntrySignOutRequest):  # only a truck that is on site
    scm_purchased: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2)


class TruckEntryOut(EntryOut):
    truck_id: uuid.UUID
    plate_number: str
    driver_name: str
    driver_phone: Optional[str]
    company: Optional[str]
    scm_purchased: Optional[Decimal]
    status: str  # queued | on_site | departed | left_queue
    entered_at: Optional[datetime]
    entered_by: Optional[uuid.UUID]
    queued_gate: Optional[int]
    left_queue_reason: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "TruckEntryOut":
        e = row[0]
        return cls(
            **cls.common_fields(row), truck_id=e.truck_id,
            plate_number=e.plate_number, driver_name=e.driver_name,
            driver_phone=e.driver_phone, company=e.company,
            scm_purchased=e.scm_purchased, status=e.status, entered_at=e.entered_at,
            entered_by=e.entered_by,
            queued_gate=e.queued_gate, left_queue_reason=e.left_queue_reason,
        )
