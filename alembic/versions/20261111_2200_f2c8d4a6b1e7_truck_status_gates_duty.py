"""truck statuses, gates, the duty log, and warnings the server raises

Revision ID: f2c8d4a6b1e7
Revises: e1b5c7d9a3f4
Create Date: 2026-11-11 22:00:00

* facilities.gate_count (existing facilities start at 1: an admin sets the real number).
* truck_entries: status (queued / on_site / departed / left_queue), entered_at/by, queued_gate,
  left_queue_reason. Existing rows: signed out -> departed, otherwise on_site; entered_at is
  their signed_in_at.
* gate_in / gate_out on all three entry tables (null for old rows).
* duty_entries: the security officers' log.
* events: the "raised once" unique index now covers more warning kinds and is per (kind, entry).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2c8d4a6b1e7"
down_revision = "e1b5c7d9a3f4"
branch_labels = None
depends_on = None

_ENTRY_TABLES = ("truck_entries", "visitor_entries", "staff_entries")
_RAISED = "kind IN ('left_inside', 'queued_too_long', 'on_duty_too_long', 'gate_unmanned')"


def upgrade() -> None:
    op.add_column("facilities", sa.Column(
        "gate_count", sa.SmallInteger(), server_default=sa.text("1"), nullable=False))
    op.create_check_constraint("gate_count_range", "facilities", "gate_count BETWEEN 1 AND 20")

    for table in _ENTRY_TABLES:
        op.add_column(table, sa.Column("gate_in", sa.SmallInteger(), nullable=True))
        op.add_column(table, sa.Column("gate_out", sa.SmallInteger(), nullable=True))

    op.add_column("truck_entries", sa.Column(
        "status", sa.String(length=12), server_default=sa.text("'on_site'"), nullable=False))
    op.add_column("truck_entries", sa.Column("entered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("truck_entries", sa.Column("entered_by", sa.Uuid(), nullable=True))
    op.add_column("truck_entries", sa.Column("queued_gate", sa.SmallInteger(), nullable=True))
    op.add_column("truck_entries", sa.Column("left_queue_reason", sa.String(length=300), nullable=True))
    op.create_foreign_key(
        "fk_truck_entries_entered_by", "truck_entries", "officers",
        ["entered_by"], ["id"], ondelete="RESTRICT")
    op.execute("UPDATE truck_entries SET status = 'departed' WHERE signed_out_at IS NOT NULL")
    op.execute("UPDATE truck_entries SET entered_at = signed_in_at, entered_by = signed_in_by")
    op.alter_column("truck_entries", "status", server_default=None)  # the app always says it
    op.create_check_constraint(
        "truck_entry_status", "truck_entries",
        "status IN ('queued', 'on_site', 'departed', 'left_queue')")

    op.create_table(
        "duty_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("officer_id", sa.Uuid(), nullable=False),
        sa.Column("gate", sa.SmallInteger(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("on_duty_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("off_duty_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_how", sa.String(length=8), server_default=sa.text("'on'"), nullable=False),
        sa.Column("ended_how", sa.String(length=8), nullable=True),
        sa.Column("signature_in", sa.LargeBinary(), nullable=True),
        sa.Column("signature_out", sa.LargeBinary(), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("gate BETWEEN 1 AND 20", name="duty_gate_range"),
        sa.CheckConstraint("started_how IN ('on', 'moved')", name="duty_started_how"),
        sa.CheckConstraint(
            "ended_how IS NULL OR ended_how IN ('off', 'moved', 'admin')", name="duty_ended_how"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["officer_id"], ["officers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_duty_entries_one_open", "duty_entries", ["officer_id"], unique=True,
        postgresql_where=sa.text("off_duty_at IS NULL"))
    op.create_index("ix_duty_entries_facility_on_duty_at", "duty_entries", ["facility_id", "on_duty_at"])
    op.create_index(
        "ix_duty_entries_open_gate", "duty_entries", ["facility_id", "gate"],
        postgresql_where=sa.text("off_duty_at IS NULL"))

    op.drop_index("uq_events_left_inside_entry", table_name="events")
    op.create_index(
        "uq_events_raised_once", "events", ["kind", "entry_id"], unique=True,
        postgresql_where=sa.text(_RAISED))


def downgrade() -> None:
    op.drop_index("uq_events_raised_once", table_name="events")
    op.create_index(
        "uq_events_left_inside_entry", "events", ["entry_id"], unique=True,
        postgresql_where=sa.text("kind = 'left_inside'"))
    op.drop_table("duty_entries")
    op.drop_constraint("truck_entry_status", "truck_entries", type_="check")
    op.drop_constraint("fk_truck_entries_entered_by", "truck_entries", type_="foreignkey")
    for column in ("left_queue_reason", "queued_gate", "entered_by", "entered_at", "status"):
        op.drop_column("truck_entries", column)
    for table in _ENTRY_TABLES:
        op.drop_column(table, "gate_out")
        op.drop_column(table, "gate_in")
    op.drop_constraint("gate_count_range", "facilities", type_="check")
    op.drop_column("facilities", "gate_count")
