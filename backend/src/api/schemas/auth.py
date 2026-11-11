# backend/src/api/schemas/auth.py

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.src.db.orm.tables import Facility, Officer
from backend.src.models import may_write_entries, sees_every_facility


@dataclass(frozen=True)
class CurrentOfficer:
    officer_id: uuid.UUID
    session_id: uuid.UUID
    facility_id: uuid.UUID | None
    is_admin: bool
    must_change_pin: bool

    @property
    def sees_all_facilities(self) -> bool:
        return sees_every_facility(
            is_admin=self.is_admin, facility_id=self.facility_id)

    @property
    def can_write_entries(self) -> bool:
        return may_write_entries(facility_id=self.facility_id)


@dataclass(frozen=True)
class LoginResult:
    officer: Officer
    facility: Facility | None
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    session_id: uuid.UUID


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class LoginRequest(BaseModel):
    # None/absent = a global account (no facility).
    facility_code: Optional[str] = Field(default=None, max_length=32)
    officer_code: str = Field(min_length=1, max_length=32)
    # Only a length cap here: the PIN *policy* applies to new PINs, not login.
    pin: str = Field(min_length=1, max_length=64)
    device_label: Optional[str] = Field(default=None, max_length=120)


class OfficerProfile(BaseModel):
    id: uuid.UUID
    officer_code: str
    full_name: str
    role: str  # a free-form label, nothing checks it
    is_admin: bool
    sees_all_facilities: bool
    can_write_entries: bool
    must_change_pin: bool
    facility_id: uuid.UUID | None
    facility_code: str | None
    facility_name: str | None

    @classmethod
    def build(cls, officer: Officer, facility: Facility | None) -> OfficerProfile:
        return cls(
            id=officer.id,
            officer_code=officer.officer_code,
            full_name=officer.full_name,
            role=officer.role,
            is_admin=officer.is_admin,
            sees_all_facilities=officer.sees_all_facilities,
            can_write_entries=officer.can_write_entries,
            must_change_pin=officer.must_change_pin,
            facility_id=officer.facility_id,
            facility_code=facility.code if facility else None,
            facility_name=facility.name if facility else None,
        )


class LoginResponse(BaseModel):
    token_type: Literal["bearer"] = "bearer"
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    officer: OfficerProfile


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=256)


class RefreshResponse(BaseModel):
    token_type: Literal["bearer"] = "bearer"
    access_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=256)


class ChangePinRequest(BaseModel):
    current_pin: str = Field(min_length=1, max_length=64)
    # Policy (6-10 digits etc.) is enforced in the service -> weak_pin error.
    new_pin: str = Field(min_length=1, max_length=64)

