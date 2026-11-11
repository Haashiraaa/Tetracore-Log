# backend/src/api/schemas/visitors.py

"""Visitor log schemas. SPACE ONLY: the request/response fields come once the
details to collect from visitors are decided. Until then an entry says only what
every log says (EntryOut)."""

from __future__ import annotations

from typing import Any

from backend.src.api.schemas.common import EntryOut


class VisitorEntryOut(EntryOut):
    # TODO(visitors): add the visitor fields here once decided.

    @classmethod
    def from_row(cls, row: Any) -> "VisitorEntryOut":
        return cls(**cls.common_fields(row))
