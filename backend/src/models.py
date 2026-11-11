
# backend/src/models.py

"""Shared constants and pure rules (and, later, shared pydantic models).

Rules:
* Things used by BOTH the DB tables and the API live here: one source of truth.
* Route-specific request/response schemas live in the api package, not here.
* Keep this file free of imports from backend.src.db and backend.src.api.

`role` is a free-form label, a short string such as "Officer". Nothing checks it.
What an account may do comes from two facts about it instead:

* facility_id: set, and it belongs to that facility, reads only that facility and
  can write log entries there. None, and it is a "global" account: it reads every
  facility and writes none (there is no facility to write into).
* is_admin: adds the admin API (facilities, officers) and reads every facility.
  Only the admin CLI (scripts/admin_manager.py) can set or clear it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

DEFAULT_ROLE = "Officer"
ROLE_MAX_LENGTH = 32

# Auto-issued account codes: OFF-001, OFF-002 ... (counted per facility).
ACCOUNT_CODE_PREFIX = "OFF"


def clean_role(raw: str) -> str:
    """Trim a role label. It may be anything, but not blank or over-long."""
    role = raw.strip()
    if not role:
        raise ValueError("Role cannot be blank.")
    if len(role) > ROLE_MAX_LENGTH:
        raise ValueError(f"Role must be at most {ROLE_MAX_LENGTH} characters.")
    return role


def clean_full_name(raw: str) -> str:
    """A person's full name: at least two words (first and last name), spaces tidied.
    Used everywhere a person is named, so the column is always a *full* name."""
    name = " ".join(raw.split())
    if len(name.split(" ")) < 2:
        raise ValueError("Enter the full name: first name and last name.")
    return name


def phone_search_digits(raw: str) -> str:
    """A phone number typed so far, for search-as-you-type: digits only (at least 3), and a
    leading 234 written as 0 so it matches the stored form. Not a full-number check."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("234"):
        digits = "0" + digits[3:]
    if len(digits) < 3:
        raise ValueError("Type at least 3 digits of the phone number.")
    return digits


def clean_phone(raw: str) -> str:
    """One canonical form for a phone number, so the same person is found again however
    it was typed: digits only, and +234 / 234 written as a leading 0
    ("+234 803 123 4567" and "0803-123-4567" both become "08031234567")."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("234") and len(digits) == 13:
        digits = "0" + digits[3:]
    if not 7 <= len(digits) <= 15:
        raise ValueError("Enter a valid phone number.")
    return digits


def sees_every_facility(*, is_admin: bool, facility_id: uuid.UUID | None) -> bool:
    """Admins and global (facility-less) accounts are not scoped to one facility."""
    return is_admin or facility_id is None


def may_write_entries(*, facility_id: uuid.UUID | None) -> bool:
    """Log entries are written INTO a facility, so only its members can write."""
    return facility_id is not None


@dataclass(frozen=True)
class AccessClaims:
    officer_id: uuid.UUID
    session_id: uuid.UUID
    expires_at: datetime


# ---- events: what the global admin is told about ----
# One row per thing that happens. `kind` says what, `severity` says whether it needs a look.

GATE_KINDS = ("truck_in", "truck_out", "visitor_in", "visitor_out", "staff_in", "staff_out")
ADMIN_KINDS = (
    "facility_added", "officer_added", "officer_pin_reset", "officer_disabled",
    "officer_enabled", "sessions_revoked", "admin_granted", "admin_revoked",
)
WARNING_KINDS = ("already_inside", "left_inside")
EVENT_KINDS = GATE_KINDS + ADMIN_KINDS + WARNING_KINDS

# The filter on the Notifications page. "warnings" is by severity, not by kind.
EVENT_GROUPS = ("gate", "admin", "warnings")


def event_severity(kind: str) -> str:
    return "warning" if kind in WARNING_KINDS else "info"
