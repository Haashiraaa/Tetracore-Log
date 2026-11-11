# backend/src/api/schemas/admin.py

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.src.api.schemas.auth import OfficerProfile
from backend.src.db.orm.tables import Facility, Officer
from backend.src.facility_codes import canonical_state
from backend.src.models import DEFAULT_ROLE, MAX_GATES, clean_full_name, clean_role


class CreateFacilityRequest(BaseModel):
    """No code here: the server issues it from the state (CNG-LAG-01)."""

    state: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)
    gate_count: int = Field(default=1, ge=1, le=MAX_GATES)

    @field_validator("state")
    @classmethod
    def _known_state(cls, value: str) -> str:
        state = canonical_state(value)
        if state is None:
            raise ValueError("Choose one of the listed states.")
        return state


class SetGatesRequest(BaseModel):
    gate_count: int = Field(ge=1, le=MAX_GATES)


class StateOut(BaseModel):
    name: str
    abbrev: str


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    state: str | None
    name: str
    is_active: bool
    gate_count: int


class CreateOfficerRequest(BaseModel):
    facility_code: str = Field(min_length=2, max_length=32)
    full_name: str = Field(min_length=2, max_length=150)
    role: str = DEFAULT_ROLE

    _name = field_validator("full_name")(clean_full_name)

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
