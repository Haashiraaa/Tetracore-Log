# backend/src/api/schemas/staff.py

"""Staff log schemas. SPACE ONLY: the staff fields come once the details to record
are decided. Until then an entry says only what every log says (EntryOut)."""

from __future__ import annotations

import uuid
from typing import Any

from backend.src.api.schemas.common import EntryOut


class StaffEntryOut(EntryOut):
    staff_id: uuid.UUID
    # TODO(staff): add the staff fields here once decided.

    @classmethod
    def from_row(cls, row: Any) -> "StaffEntryOut":
        return cls(**cls.common_fields(row), staff_id=row[0].staff_id)
