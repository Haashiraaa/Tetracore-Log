
# backend/src/models.py

"""Shared constants and pure rules (and, later, shared pydantic models).

Rules:
* Things used by BOTH the DB tables and the API live here: one source of truth.
* Route-specific request/response schemas live in the api package, not here.
* Keep this file free of imports from backend.src.db and backend.src.api.

`role` is a free-form label, a short string such as "officer". Nothing checks it.
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

DEFAULT_ROLE = "officer"
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
