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
    SetGatesRequest,
    StateOut,
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
from backend.src.api.schemas.common import EntryOut, EntrySignInRequest, EntrySignOutRequest
from backend.src.api.schemas.duty import (
    DutyChangeGateRequest,
    DutyEntryOut,
    DutyOffRequest,
    DutyOnRequest,
    DutyStatusOut,
)
from backend.src.api.schemas.events import (
    EventOut,
    EventsSummaryOut,
    MarkReadRequest,
    PushConfigOut,
    PushSubscribeRequest,
    PushTestOut,
    PushUnsubscribeRequest,
)
from backend.src.api.schemas.staff import StaffEntryOut, StaffLookupOut, StaffSignInRequest
from backend.src.api.schemas.trucks import (
    TruckEnterRequest,
    TruckEntryOut,
    TruckLeaveQueueRequest,
    TruckLookupOut,
    TruckSignInRequest,
    TruckSignOutRequest,
)
from backend.src.api.schemas.visitors import (
    VisitorEntryOut,
    VisitorLookupOut,
    VisitorSignInRequest,
)

__all__ = [
    "DutyChangeGateRequest", "DutyEntryOut", "DutyOffRequest", "DutyOnRequest",
    "DutyStatusOut",
    "AdminOfficerOut", "StateOut", "ChangePinRequest", "CreateFacilityRequest",
    "CreateOfficerRequest", "CreateOfficerResponse", "CurrentOfficer",
    "EventOut", "EventsSummaryOut", "MarkReadRequest", "PushConfigOut", "PushTestOut",
    "PushSubscribeRequest", "PushUnsubscribeRequest",
    "EntryOut", "EntrySignInRequest", "EntrySignOutRequest", "FacilityOut",
    "LoginRequest", "LoginResponse", "LoginResult", "LogoutRequest",
    "OfficerProfile", "RefreshRequest", "RefreshResponse", "RefreshResult",
    "ResetPinResponse", "SetGatesRequest", "StaffEntryOut", "StaffLookupOut",
    "StaffSignInRequest", "TruckEntryOut",
    "TruckLookupOut", "TruckSignInRequest", "TruckSignOutRequest",
    "TruckEnterRequest", "TruckLeaveQueueRequest",
    "VisitorEntryOut", "VisitorLookupOut", "VisitorSignInRequest",
]
