# backend/src/db/queries/trucks.py

"""Truck-only SQL (the registry and plate search). What every log shares lives in
_entries.py. No commits, no business rules (those live in api/truck_service.py)."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.src.db.orm._helpers import normalize_plate
from backend.src.db.orm.tables import Truck, TruckEntry
from backend.src.db.queries import _entries
from backend.src.models import TRUCK_OPEN_STATUSES


def find_truck(db: Session, facility_id: uuid.UUID, plate: str) -> Truck | None:
    return db.scalar(select(Truck).where(
        Truck.facility_id == facility_id,
        Truck.plate_number == normalize_plate(plate)))


def find_open_entry(
    db: Session, facility_id: uuid.UUID, truck_id: uuid.UUID
) -> tuple[uuid.UUID, str] | None:
    """(id, status) of the visit this truck is in the middle of (queued or on site)."""
    row = db.execute(
        select(TruckEntry.id, TruckEntry.status)
        .where(TruckEntry.facility_id == facility_id,
               TruckEntry.truck_id == truck_id,
               TruckEntry.status.in_(TRUCK_OPEN_STATUSES))
        .order_by(TruckEntry.signed_in_at.desc())
        .limit(1)).first()
    return None if row is None else (row[0], row[1])


def latest_signature(db: Session, facility_id: uuid.UUID, truck_id: uuid.UUID) -> bytes | None:
    """The signature a driver of this truck last gave on the way in at this facility."""
    return _entries.latest_signature(
        db, TruckEntry, facility_id, TruckEntry.truck_id == truck_id)


def has_signature(db: Session, facility_id: uuid.UUID, truck_id: uuid.UUID) -> bool:
    """Is there a signature on file for this truck? (Does not load the image.)"""
    return db.scalar(
        select(TruckEntry.id)
        .where(TruckEntry.facility_id == facility_id, TruckEntry.truck_id == truck_id,
               TruckEntry.signature_in.is_not(None))
        .limit(1)) is not None


def upsert_truck(
    db: Session, *, facility_id: uuid.UUID, plate: str, driver_name: str,
    driver_phone: Optional[str], company: Optional[str],
) -> uuid.UUID:
    """Registry keeps the LATEST confirmed driver details. Core upserts skip
    the model's @validates, so the plate is normalized here."""
    stmt = pg_insert(Truck).values(
        id=uuid.uuid4(), facility_id=facility_id,
        plate_number=normalize_plate(plate), driver_name=driver_name,
        driver_phone=driver_phone, company=company)
    stmt = stmt.on_conflict_do_update(
        index_elements=["facility_id", "plate_number"],
        set_={
            "driver_name": stmt.excluded.driver_name,
            "driver_phone": stmt.excluded.driver_phone,
            "company": stmt.excluded.company,
            "updated_at": func.now(),
        },
    ).returning(Truck.id)
    return db.execute(stmt).scalar_one()


def insert_entry(
    db: Session, *, entry_id: uuid.UUID, plate: str, **values: Any
) -> bool:
    """True if inserted, False if that id already existed (retry)."""
    return _entries.insert_entry(
        db, TruckEntry, id=entry_id, plate_number=normalize_plate(plate), **values)


def update_open_entry(
    db: Session, *, entry_id: uuid.UUID, facility_id: uuid.UUID, from_status: str,
    **values: Any,
) -> bool:
    """Move a visit on from `from_status` (queued -> on site, queued -> left queue).
    True if this call did it; False = not found or it is no longer in that status."""
    stmt = (
        update(TruckEntry)
        .where(TruckEntry.id == entry_id, TruckEntry.facility_id == facility_id,
               TruckEntry.status == from_status)
        .values(**values, updated_at=func.now())
        .returning(TruckEntry.id)
        .execution_options(synchronize_session=False))
    return db.execute(stmt).scalar_one_or_none() is not None


def get_entry(db: Session, entry_id: uuid.UUID, scope: uuid.UUID | None) -> Any | None:
    return _entries.get_entry(db, TruckEntry, entry_id, scope)


def get_signature(
    db: Session, entry_id: uuid.UUID, scope: uuid.UUID | None,
    which: _entries.Which = "in",
) -> Any | None:
    return _entries.get_signature(db, TruckEntry, entry_id, scope, which)


def list_entries(
    db: Session, *, plate: Optional[str] = None, **filters: Any
) -> list[Any]:
    """Shared filters (see _entries.list_entries) plus a plate search."""
    needle = normalize_plate(plate) if plate else ""
    extra = [TruckEntry.plate_number.contains(needle)] if needle else []
    return _entries.list_entries(db, TruckEntry, extra_where=extra, **filters)
