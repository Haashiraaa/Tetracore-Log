# backend/src/api/schemas/__init__.py

"""Request/response shapes, one module per area. Import from here:
`from backend.src.api.schemas import TruckEntryOut`."""

from backend.src.api.schemas.admin import (
    AdminOfficerOut,
    CreateFacilityRequest,
    CreateOfficerRequest,
    CreateOfficerResponse,
    FacilityOut,
    ResetPinResponse,
)
from backend.src.api.schemas.auth import (
    ChangePinRequest,
    CurrentOfficer,
    LoginRequest,
    LoginResponse,
    LoginResult,
    LogoutRequest,
    OfficerProfile,
    RefreshRequest,
    RefreshResponse,
    RefreshResult,
)
from backend.src.api.schemas.common import EntryOut
from backend.src.api.schemas.staff import StaffEntryOut
from backend.src.api.schemas.trucks import (
    TruckEntryOut,
    TruckLookupOut,
    TruckSignInRequest,
    TruckSignOutRequest,
)
from backend.src.api.schemas.visitors import VisitorEntryOut

__all__ = [
    "AdminOfficerOut", "ChangePinRequest", "CreateFacilityRequest",
    "CreateOfficerRequest", "CreateOfficerResponse", "CurrentOfficer",
    "EntryOut", "FacilityOut", "LoginRequest", "LoginResponse", "LoginResult",
    "LogoutRequest", "OfficerProfile", "RefreshRequest", "RefreshResponse",
    "RefreshResult", "ResetPinResponse", "StaffEntryOut", "TruckEntryOut",
    "TruckLookupOut", "TruckSignInRequest", "TruckSignOutRequest",
    "VisitorEntryOut",
]
