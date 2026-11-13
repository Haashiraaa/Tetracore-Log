

# backend/src/db/orm/tables.py

"""
Gate-log database models (SQLAlchemy 2.0 style, PostgreSQL).

Design rules baked in here:

* Every row that belongs to a station carries `facility_id`. The API must set it
  from the logged-in officer's token, NEVER from the request body.
* Entry tables (truck / visitor / staff) use UUID primary keys that the PHONE
  generates, so offline records can never collide and a retried sync push is
  an idempotent upsert, not a duplicate.
* `signed_in_at` / `signed_out_at` are the real-world event times (from the
  phone). `created_at` / `updated_at` are SERVER times and drive sync pulls.
* All timestamps are timezone-aware and stored in UTC. Convert to Lagos time
  (UTC+1) only for display.
* Entries are never deleted. A security log that can lose rows is not a log.
* Truck / staff references on an entry are composite foreign keys that include
  facility_id, so the database itself refuses an entry that points at another
  facility's truck or staff member.

Access model (officers table), see backend/src/models.py:

* role        -> a free-form label. Nothing checks it.
* facility_id -> set: scoped to that facility, may write entries there.
                 NULL: a global account, reads every facility, writes none.
* is_admin    -> adds the admin API (manage facilities/officers, reset PINs,
                 revoke sessions) and reads every facility. Set it ONLY from
                 the admin CLI (scripts/admin_manager.py), never from an API
                 request body.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from backend.src.db.orm._helpers import normalize_code, normalize_plate
from backend.src.db.orm._mixins import EntryMixin, TimestampMixin
from backend.src.db.orm.base import Base
from backend.src.models import (
    DEFAULT_ROLE,
    ROLE_MAX_LENGTH,
    clean_role,
    may_write_entries,
    sees_every_facility,
)

# --------------------------------------------------------------------------
# Facilities, officers, sessions
# --------------------------------------------------------------------------


class Facility(TimestampMixin, Base):
    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(
        String(32), nullable=False)  # issued by the server, e.g. CNG-LAG-01
    # Empty only for a facility created before codes were issued from a state.
    state: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"), nullable=False
    )
    # Gates are numbered 1..gate_count. Officers pick theirs when they go on duty.
    gate_count: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default=text("1"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_facilities_code"),
        CheckConstraint("gate_count BETWEEN 1 AND 20", name="gate_count_range"),
    )

    @validates("code")
    def _normalize_code(self, _key: str, value: str) -> str:
        return normalize_code(value)


class Officer(TimestampMixin, Base):
    """Anyone who logs in: a gate officer, a manager, an admin, anybody.

    Login = (facility.code, officer_code, PIN). The pair (facility_id,
    officer_code) is unique, so an officer code only means something inside
    its own facility. A row with facility_id NULL is a "global" account; its
    code is unique among the other global accounts.
    """

    __tablename__ = "officers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=True
    )
    officer_code: Mapped[str] = mapped_column(
        String(32), nullable=False)  # e.g. OFF-014
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(ROLE_MAX_LENGTH),
        default=DEFAULT_ROLE,
        server_default=DEFAULT_ROLE,
        nullable=False,
    )
    # Only ever set from the CLI (scripts/admin_manager.py). No API route may
    # set or clear it, and admin routes never act on an account where it is true.
    is_admin: Mapped[bool] = mapped_column(
        default=False, server_default=text("false"), nullable=False
    )
    must_change_pin: Mapped[bool] = mapped_column(
        default=False, server_default=text("false"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"), nullable=False
    )
    failed_pin_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "facility_id", "officer_code", name="uq_officers_facility_id_officer_code"
        ),
        Index(
            "uq_officers_global_officer_code",
            "officer_code",
            unique=True,
            postgresql_where=text("facility_id IS NULL"),
        ),
        CheckConstraint("length(btrim(role)) > 0", name="role_not_blank"),
    )

    @validates("officer_code")
    def _normalize_code(self, _key: str, value: str) -> str:
        return normalize_code(value)

    @validates("role")
    def _clean_role(self, _key: str, value: str) -> str:
        return clean_role(value)

    @property
    def sees_all_facilities(self) -> bool:
        return sees_every_facility(
            is_admin=self.is_admin, facility_id=self.facility_id)

    @property
    def can_write_entries(self) -> bool:
        return may_write_entries(facility_id=self.facility_id)


class OfficerSession(Base):
    """One row per logged-in phone. Store only a HASH of the refresh token.
    Revoking a lost phone = set revoked_at."""

    __tablename__ = "officer_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    officer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False)
    device_label: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "refresh_token_hash", name="uq_officer_sessions_refresh_token_hash"
        ),
        Index("ix_officer_sessions_officer_id", "officer_id"),
    )


class Counter(Base):
    """Locked-row sequences for issuing codes, one row each: officer codes per
    facility ('officer_code:<facility id>:OFF') and facility codes per state
    ('facility_code:LAG'). Row is locked FOR UPDATE while issuing; numbers only go up."""

    __tablename__ = "counters"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    next_value: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )

# --------------------------------------------------------------------------
# Events (the global admin's notification feed)
# --------------------------------------------------------------------------


class Event(Base):
    """One thing that happened: a gate sign-in or sign-out, an admin change, or a warning.
    Written in the SAME transaction as the thing itself, so nothing is announced that did not
    happen and nothing that happened is missed. Ordered by id (it only goes up), which is what
    the app polls on. Rows are never edited or deleted."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(8), default="info", server_default=text("'info'"), nullable=False
    )
    facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=True
    )
    # Who did it (the officer or admin). None for things nobody did, like "left inside".
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="RESTRICT"), nullable=True
    )
    # The log entry it is about, when there is one (no FK: three different tables).
    entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)

    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning')", name="event_severity"),
        Index("ix_events_facility_id_id", "facility_id", "id"),
        # A warning the server raises by itself comes once per entry, even if two servers
        # notice at once. (kind, entry_id): a truck can be both queued-too-long and, later,
        # left-inside.
        Index(
            "uq_events_raised_once",
            "kind",
            "entry_id",
            unique=True,
            postgresql_where=text(
                "kind IN ('left_inside', 'queued_too_long', 'on_duty_too_long', 'gate_unmanned')"),
        ),
    )


class EventCursor(Base):
    """How far each admin has read in the feed. Unread = events with a larger id."""

    __tablename__ = "event_cursors"

    officer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="CASCADE"), primary_key=True
    )
    last_read_id: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default=text("0"), nullable=False
    )


class PushSubscription(Base):
    """One browser an admin turned push on in. `endpoint` is the browser's own address
    for it, so it is unique. A subscription the push service reports gone is deleted."""

    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    officer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(200), nullable=False)
    auth: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_push_subscriptions_officer_id", "officer_id"),)


# --------------------------------------------------------------------------
# Duty log (security officers)
# --------------------------------------------------------------------------


class DutyEntry(TimestampMixin, Base):
    """A stretch of an officer's duty at ONE gate. Going on duty opens a row (signature in);
    going off closes it (signature out). Changing gate mid-shift closes the row (no
    signature) and opens a new one at the new gate, so one shift can be several rows that
    share a shift_id. Open = off_duty_at is null. An officer has at most one open row."""

    __tablename__ = "duty_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)  # supplied by the phone on "go on duty"
    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="RESTRICT"), nullable=False
    )
    gate: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # The id of the row that began the shift. Every row of one shift carries it.
    shift_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    on_duty_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    off_duty_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)
    started_how: Mapped[str] = mapped_column(
        String(8), default="on", server_default=text("'on'"), nullable=False)
    ended_how: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    # PNG bytes. Only "on" starts and "off" ends carry one (a move or an admin end does not).
    signature_in: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, deferred=True)
    signature_out: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, deferred=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("gate BETWEEN 1 AND 20", name="duty_gate_range"),
        CheckConstraint("started_how IN ('on', 'moved')", name="duty_started_how"),
        CheckConstraint(
            "ended_how IS NULL OR ended_how IN ('off', 'moved', 'admin')",
            name="duty_ended_how"),
        # One open stretch per officer: the database refuses a second "on duty".
        Index("uq_duty_entries_one_open", "officer_id", unique=True,
              postgresql_where=text("off_duty_at IS NULL")),
        Index("ix_duty_entries_facility_on_duty_at", "facility_id", "on_duty_at"),
        Index("ix_duty_entries_open_gate", "facility_id", "gate",
              postgresql_where=text("off_duty_at IS NULL")),
    )


# --------------------------------------------------------------------------
# Trucks
# --------------------------------------------------------------------------


class Truck(TimestampMixin, Base):
    """Registry of trucks per facility. A returning truck is looked up by
    plate and the guard only CONFIRMS the stored driver details."""

    __tablename__ = "trucks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    plate_number: Mapped[str] = mapped_column(
        String(20), nullable=False)  # normalized
    driver_name: Mapped[str] = mapped_column(String(150), nullable=False)
    driver_phone: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # The cab's own number, for trucks that have one. Free text; most trucks have none.
    cab_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "facility_id", "plate_number", name="uq_trucks_facility_id_plate_number"
        ),
        # Target for the composite FK on truck_entries (Postgres requires the
        # referenced column pair to be unique, even though id alone already is).
        UniqueConstraint("facility_id", "id", name="uq_trucks_facility_id_id"),
    )

    @validates("plate_number")
    def _normalize_plate(self, _key: str, value: str) -> str:
        return normalize_plate(value)


class TruckEntry(EntryMixin, TimestampMixin, Base):
    """One visit. Driver/plate/company are SNAPSHOTS: if the registry record
    changes later, the historical log must not."""

    __tablename__ = "truck_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )  # supplied by the phone
    # FK is the composite one in __table_args__ (facility_id + truck_id).
    truck_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(150), nullable=False)
    driver_phone: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cab_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    scm_purchased: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    # Where the truck is in its visit. signed_in_at is when it was FIRST LOGGED (for a
    # queued truck, when it joined the queue); entered_at is when it was let in.
    # A truck that gave up is closed with signed_out_at/by set and status "left_queue".
    status: Mapped[str] = mapped_column(
        String(12), default="queued", nullable=False
    )
    entered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    entered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="RESTRICT"), nullable=True
    )
    queued_gate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    left_queue_reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'on_site', 'departed', 'left_queue')",
            name="truck_entry_status"),
        ForeignKeyConstraint(
            ["facility_id", "truck_id"],
            ["trucks.facility_id", "trucks.id"],
            ondelete="RESTRICT",
            name="fk_truck_entries_facility_truck",
        ),
        CheckConstraint(
            "scm_purchased IS NULL OR scm_purchased >= 0", name="scm_non_negative"
        ),
        Index("ix_truck_entries_facility_signed_in",
              "facility_id", "signed_in_at"),
        Index("ix_truck_entries_facility_updated",
              "facility_id", "updated_at"),
        Index("ix_truck_entries_facility_plate",
              "facility_id", "plate_number"),
        # "Trucks currently inside" stays fast however big the table gets.
        Index(
            "ix_truck_entries_open",
            "facility_id",
            postgresql_where=text("signed_out_at IS NULL"),
        ),
    )

    @validates("plate_number")
    def _normalize_plate(self, _key: str, value: str) -> str:
        return normalize_plate(value)


# --------------------------------------------------------------------------
# Visitors (no registry: visitors rarely repeat, so entries only)
# --------------------------------------------------------------------------


class VisitorEntry(EntryMixin, TimestampMixin, Base):
    """One visit, like a line on the paper gate log: who, where from, why, what was
    received, phone, time in + signature, time out + signature. A returning visitor is
    found by phone."""

    __tablename__ = "visitor_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # Old free text, kept for lines written before `items`; new lines leave it empty.
    items_received: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True)
    # What they brought: [{"name", "quantity" (int), "unit" (text or null)}, ...]. Null = nothing.
    items: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index("ix_visitor_entries_facility_phone", "facility_id", "phone"),
        Index("ix_visitor_entries_facility_signed_in",
              "facility_id", "signed_in_at"),
        Index("ix_visitor_entries_facility_updated",
              "facility_id", "updated_at"),
        Index(
            "ix_visitor_entries_open",
            "facility_id",
            postgresql_where=text("signed_out_at IS NULL"),
        ),
    )


# --------------------------------------------------------------------------
# Waybill (couriers bringing goods to the station)
# --------------------------------------------------------------------------


class WaybillEntry(EntryMixin, TimestampMixin, Base):
    """One courier visit: who brought what, whether they came with a vehicle (and its plate),
    time in + signature, time out + signature. The courier is found again by phone, like a
    visitor, so their signature can be reused."""

    __tablename__ = "waybill_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    # The courier's name. Called full_name like the other people logs, so the shared code
    # (search, warnings, notifications) works on it unchanged.
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # What was delivered: [{"name", "quantity" (int), "unit" (text or null)}, ...].
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    # Did the courier drive here? A courier on foot has no plate.
    came_by_vehicle: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false())
    plate_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "came_by_vehicle OR plate_number IS NULL", name="waybill_plate_needs_vehicle"),
        Index("ix_waybill_entries_facility_phone", "facility_id", "phone"),
        Index("ix_waybill_entries_facility_signed_in",
              "facility_id", "signed_in_at"),
        Index("ix_waybill_entries_facility_updated",
              "facility_id", "updated_at"),
        Index(
            "ix_waybill_entries_open",
            "facility_id",
            postgresql_where=text("signed_out_at IS NULL"),
        ),
    )

    @validates("plate_number")
    def _normalize_plate(self, _key: str, value: Optional[str]) -> Optional[str]:
        return None if value is None else normalize_plate(value)


# --------------------------------------------------------------------------
# Staff
# --------------------------------------------------------------------------


class StaffEntry(EntryMixin, TimestampMixin, Base):
    """One staff attendance line: full name, capacity, phone, time in + signature, time out
    + signature. Typed per entry; a returning person is found by phone (no register yet)."""

    __tablename__ = "staff_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    # The capacity they work in, free text ("Cashier", "Attendant", "Driver"...).
    # Empty only on lines written before this column existed.
    capacity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Canonical form (models.clean_phone); how a returning person is found again.
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index("ix_staff_entries_facility_phone", "facility_id", "phone"),
        Index("ix_staff_entries_facility_signed_in",
              "facility_id", "signed_in_at"),
        Index("ix_staff_entries_facility_updated",
              "facility_id", "updated_at"),
        Index(
            "ix_staff_entries_open",
            "facility_id",
            postgresql_where=text("signed_out_at IS NULL"),
        ),
    )


# --------------------------------------------------------------------------
# Events (the officer's own notes: "this is what I noticed")
# --------------------------------------------------------------------------


class OccurrenceEntry(TimestampMixin, Base):
    """One note an officer wrote into the log: what happened or what they noticed. The time,
    the officer and the gate are filled in by the server; the officer's signature is the one
    from their latest duty sign-on, unless they had to sign on the spot. Never edited or
    deleted. (Called "occurrence" in code so it is not confused with `events`, the alerts feed;
    the app calls it "Events".)"""

    __tablename__ = "occurrences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4)  # supplied by the phone
    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("officers.id", ondelete="RESTRICT"), nullable=False
    )
    gate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    note: Mapped[str] = mapped_column(String(2000), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signature: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, deferred=True)
    # True when nobody drew it for this note: it is the officer's signature from duty.
    signature_reused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false())
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_occurrences_facility_logged_at", "facility_id", "logged_at"),
        Index("ix_occurrences_facility_updated", "facility_id", "updated_at"),
    )
