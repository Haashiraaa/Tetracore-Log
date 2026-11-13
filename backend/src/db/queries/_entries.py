# backend/src/db/queries/_entries.py

"""SQL shared by every log (trucks, visitors, staff): anything built on EntryMixin.
SQL only: no commits, no business rules. A log's own module (trucks.py, ...) adds
what is specific to it and passes its model in here.

Rows come back as (entry, facility_code, has_signature_in, signed_in_by_name,
signed_out_by_name, has_signature_out). The signature blobs stay deferred: we only ask
whether they exist."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional, Sequence

from sqlalchemy import ColumnElement, Select, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from backend.src.db.orm._helpers import normalize_code
from backend.src.db.orm.tables import Facility, Officer

Model = Any  # TruckEntry, VisitorEntry or StaffEntry
Which = Literal["in", "out"]  # which signature: coming in or going out


def entry_select(model: Model) -> Select[Any]:
    signed_in, signed_out = aliased(Officer), aliased(Officer)
    return (
        select(
            model,
            Facility.code,
            model.signature_in.is_not(None),
            signed_in.full_name,
            signed_out.full_name,
            model.signature_out.is_not(None),
        )
        .join(Facility, Facility.id == model.facility_id)
        .join(signed_in, signed_in.id == model.signed_in_by)
        .outerjoin(signed_out, signed_out.id == model.signed_out_by)
        .execution_options(populate_existing=True)
    )


def _in_scope(stmt: Select[Any], model: Model, scope: uuid.UUID | None) -> Select[Any]:
    """scope=None: the caller sees every facility."""
    return stmt if scope is None else stmt.where(model.facility_id == scope)


def get_entry(
    db: Session, model: Model, entry_id: uuid.UUID, scope: uuid.UUID | None
) -> Any | None:
    stmt = entry_select(model).where(model.id == entry_id)
    return db.execute(_in_scope(stmt, model, scope)).first()


def get_signature(
    db: Session,
    model: Model,
    entry_id: uuid.UUID,
    scope: uuid.UUID | None,
    which: Which = "in",
) -> Any | None:
    """Row (bytes | None,) or None if the entry is not visible."""
    column = model.signature_in if which == "in" else model.signature_out
    stmt = select(column).where(model.id == entry_id)
    return db.execute(_in_scope(stmt, model, scope)).first()


def insert_entry(db: Session, model: Model, **values: Any) -> bool:
    """True if inserted, False if that id already existed (a retry). Never
    overwrites an existing row."""
    stmt = (
        pg_insert(model)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(model.id)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def sign_out_entry(
    db: Session,
    model: Model,
    *,
    entry_id: uuid.UUID,
    facility_id: uuid.UUID,
    officer_id: uuid.UUID,
    signed_out_at: datetime,
    signature: Optional[bytes] = None,
    extra: Optional[dict[str, Any]] = None,
    require: Sequence[ColumnElement[bool]] = (),
) -> bool:
    """True if this call closed the entry. False = not found OR already out OR one of
    `require` (a log's own conditions, e.g. a truck must be on site) does not hold.
    `extra` carries a log's own columns to set on the way out."""
    values: dict[str, Any] = {
        "signed_out_at": signed_out_at,
        "signed_out_by": officer_id,
        "signature_out": signature,
        "updated_at": func.now(),
        **(extra or {}),
    }
    stmt = (
        update(model)
        .where(
            model.id == entry_id,
            model.facility_id == facility_id,
            model.signed_out_at.is_(None),
            *require,
        )
        .values(**values)
        .returning(model.id)
        .execution_options(synchronize_session=False)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def latest_by_phone(
    db: Session, model: Model, facility_id: uuid.UUID, phone: str
) -> Any | None:
    """The most recent entry in this facility for a (canonical) phone number."""
    return db.scalar(
        select(model)
        .where(model.facility_id == facility_id, model.phone == phone)
        .order_by(model.signed_in_at.desc(), model.id)
        .limit(1))


def latest_signature(
    db: Session, model: Model, facility_id: uuid.UUID, *same_subject: ColumnElement[bool]
) -> bytes | None:
    """The signature most recently given on the way IN by whoever `same_subject` picks out
    (a phone, a truck), or None if there never was one. Always within one facility."""
    return db.scalar(
        select(model.signature_in)
        .where(model.facility_id == facility_id, *same_subject,
               model.signature_in.is_not(None))
        .order_by(model.signed_in_at.desc(), model.id)
        .limit(1))


def latest_signature_by_phone(
    db: Session, model: Model, facility_id: uuid.UUID, phone: str
) -> bytes | None:
    """The signature this person most recently gave on the way IN at this facility, or
    None if they never gave one. Facility-scoped, like everything else about a phone."""
    return latest_signature(db, model, facility_id, model.phone == phone)


def phones_with_signature(
    db: Session, model: Model, facility_id: uuid.UUID, phones: Sequence[str]
) -> set[str]:
    """Which of these (canonical) phones have a signature on file here."""
    if not phones:
        return set()
    return set(db.scalars(
        select(model.phone)
        .where(model.facility_id == facility_id, model.phone.in_(list(phones)),
               model.signature_in.is_not(None))
        .distinct()))


def search_by_phone(
    db: Session, model: Model, facility_id: uuid.UUID, digits: str, limit: int
) -> list[tuple[Any, uuid.UUID | None]]:
    """People in this facility whose phone contains `digits`: one row per phone (their
    latest entry), numbers that START with the digits first, then the most recent.
    Each comes with the id of the entry they are inside on, or None."""
    latest = (
        select(model)
        .where(model.facility_id == facility_id, model.phone.is_not(None),
               model.phone.contains(digits, autoescape=True))
        .distinct(model.phone)
        .order_by(model.phone, model.signed_in_at.desc(), model.id)
        .subquery())
    row = aliased(model, latest)
    rows = list(db.scalars(
        select(row)
        .order_by(row.phone.startswith(digits, autoescape=True).desc(),
                  row.signed_in_at.desc(), row.id)
        .limit(limit)))
    if not rows:
        return []
    inside: dict[str, uuid.UUID] = {}
    for phone, entry_id in db.execute(
        select(model.phone, model.id)
        .where(model.facility_id == facility_id,
               model.phone.in_([r.phone for r in rows]),
               model.signed_out_at.is_(None))):
        inside[phone] = entry_id
    return [(r, inside.get(r.phone)) for r in rows]


def open_id_by_phone(
    db: Session, model: Model, facility_id: uuid.UUID, phone: str
) -> uuid.UUID | None:
    """The entry id if this phone number is inside right now (not signed out yet)."""
    return db.scalar(
        select(model.id)
        .where(model.facility_id == facility_id, model.phone == phone,
               model.signed_out_at.is_(None))
        .limit(1))


def list_entries(
    db: Session,
    model: Model,
    *,
    scope: uuid.UUID | None,
    facility_code: Optional[str] = None,
    open_only: bool = False,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    extra_where: Sequence[ColumnElement[bool]] = (),
) -> list[Any]:
    """Newest first. facility_code is honoured only when scope is None. date_to is
    exclusive. `extra_where` carries a log's own filters (e.g. a plate search)."""
    stmt = _in_scope(entry_select(model), model, scope)
    if scope is None and facility_code:
        stmt = stmt.where(Facility.code == normalize_code(facility_code))
    if open_only:
        stmt = stmt.where(model.signed_out_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(model.signed_in_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(model.signed_in_at < date_to)
    stmt = stmt.where(*extra_where)
    stmt = stmt.order_by(model.signed_in_at.desc(), model.id)
    return list(db.execute(stmt.limit(limit).offset(offset)).all())
