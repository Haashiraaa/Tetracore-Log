# backend/src/api/routes/_entries.py

"""Route pieces every log shares: the list filters and the signature download."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal, Optional

from fastapi import Query, Response

from backend.src.exceptions.errors import NotFoundError

SignatureSide = Annotated[Literal["in", "out"], Query(description="Which signature")]


@dataclass
class EntryFilters:
    """Query-string filters on a log's entry list. Use as `Depends()`.
    Pass `scope` yourself (from get_facility_scope), then `**filters.as_kwargs()`."""

    open_only: bool = Query(False, alias="open")
    facility_code: Optional[str] = Query(None, max_length=32)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Query(50, ge=1, le=200)
    offset: int = Query(0, ge=0)

    def as_kwargs(self) -> dict[str, Any]:
        return dict(
            open_only=self.open_only, facility_code=self.facility_code,
            date_from=self.date_from, date_to=self.date_to,
            limit=self.limit, offset=self.offset)


def signature_response(row: Any | None) -> Response:
    """PNG response from a get_signature row, 404 when there is none."""
    if row is None or row[0] is None:
        raise NotFoundError("No signature for that entry.")
    return Response(content=row[0], media_type="image/png",
                    headers={"Cache-Control": "private, max-age=3600"})
