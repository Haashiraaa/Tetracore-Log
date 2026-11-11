# backend/src/api/schemas/admin.py

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.src.api.schemas.auth import OfficerProfile
from backend.src.db.orm.tables import Facility, Officer
from backend.src.models import DEFAULT_ROLE, clean_role

_CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]*$"


class CreateFacilityRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=_CODE_PATTERN)
    name: str = Field(min_length=2, max_length=200)


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_active: bool


class CreateOfficerRequest(BaseModel):
    facility_code: str = Field(min_length=2, max_length=32)
    full_name: str = Field(min_length=2, max_length=150)
    role: str = DEFAULT_ROLE

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        return clean_role(v)


class CreateOfficerResponse(BaseModel):
    officer: OfficerProfile
    # Shown ONCE. Only the hash is stored; it cannot be fetched again.
    temp_pin: str


class ResetPinResponse(BaseModel):
    officer_code: str
    full_name: str
    temp_pin: str


class AdminOfficerOut(OfficerProfile):
    is_active: bool

    @classmethod
    def from_row(cls, officer: Officer, facility: Facility | None) -> AdminOfficerOut:
        base = OfficerProfile.build(officer, facility)
        return cls(**base.model_dump(), is_active=officer.is_active)
