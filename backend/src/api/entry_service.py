# backend/src/api/entry_service.py

"""Rules every log (trucks, visitors, staff) shares. A log's own service builds on these."""

from __future__ import annotations

import uuid

from backend.src.api.schemas import CurrentOfficer
from backend.src.exceptions.errors import PermissionDeniedError


def facility_of(officer: CurrentOfficer) -> uuid.UUID:
    """The facility an entry is written to. Always from the token, never the request."""
    if not officer.can_write_entries or officer.facility_id is None:
        raise PermissionDeniedError(
            "Only accounts that belong to a facility can write log entries.")
    return officer.facility_id
