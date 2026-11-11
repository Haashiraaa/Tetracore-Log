"""events feed, read cursors and push subscriptions

Revision ID: e1b5c7d9a3f4
Revises: d7a3f1c9b5e2
Create Date: 2026-11-11 15:00:00

* events: everything the global admin is notified about (gate sign-ins and sign-outs, admin
  changes, warnings). Append-only; ordered by id.
* event_cursors: how far each admin has read.
* push_subscriptions: the browsers an admin turned push on in.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1b5c7d9a3f4"
down_revision = "d7a3f1c9b5e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=8), server_default=sa.text("'info'"), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("entry_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.String(length=300), nullable=False),
        sa.CheckConstraint("severity IN ('info', 'warning')", name="event_severity"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_id"], ["officers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_facility_id_id", "events", ["facility_id", "id"])
    op.create_index(
        "uq_events_left_inside_entry", "events", ["entry_id"], unique=True,
        postgresql_where=sa.text("kind = 'left_inside'"),
    )

    op.create_table(
        "event_cursors",
        sa.Column("officer_id", sa.Uuid(), nullable=False),
        sa.Column("last_read_id", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["officer_id"], ["officers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("officer_id"),
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("officer_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(length=1000), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["officer_id"], ["officers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index("ix_push_subscriptions_officer_id", "push_subscriptions", ["officer_id"])


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_officer_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_table("event_cursors")
    op.drop_index("uq_events_left_inside_entry", table_name="events")
    op.drop_index("ix_events_facility_id_id", table_name="events")
    op.drop_table("events")
