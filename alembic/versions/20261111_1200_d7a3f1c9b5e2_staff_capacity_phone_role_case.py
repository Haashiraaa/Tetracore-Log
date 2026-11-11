"""staff capacity and phone, phone lookup indexes, "Officer" with a capital O

Revision ID: d7a3f1c9b5e2
Revises: c4e8a2f6d0b3
Create Date: 2026-11-11 12:00:00

* staff_entries gets capacity (free text) and phone. Both are nullable because lines
  written before this have neither; the API now requires both.
* (facility_id, phone) indexes on staff and visitor entries: a returning person is
  found by phone.
* visitor phones already stored are rewritten to the canonical form the API now uses:
  digits only, +234 / 234 as a leading 0.
* the default role label is "Officer": accounts still labelled "officer" are renamed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d7a3f1c9b5e2"
down_revision = "c4e8a2f6d0b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff_entries", sa.Column("capacity", sa.String(length=100), nullable=True))
    op.add_column("staff_entries", sa.Column("phone", sa.String(length=32), nullable=True))
    op.create_index("ix_staff_entries_facility_phone", "staff_entries", ["facility_id", "phone"])
    op.create_index("ix_visitor_entries_facility_phone", "visitor_entries", ["facility_id", "phone"])

    op.execute(r"UPDATE visitor_entries SET phone = regexp_replace(phone, '\D', '', 'g') "
               "WHERE phone IS NOT NULL")
    op.execute("UPDATE visitor_entries SET phone = '0' || substr(phone, 4) "
               "WHERE phone LIKE '234%' AND length(phone) = 13")
    op.execute("UPDATE visitor_entries SET phone = NULL WHERE phone = ''")

    op.alter_column("officers", "role", server_default="Officer")
    op.execute("UPDATE officers SET role = 'Officer' WHERE role = 'officer'")


def downgrade() -> None:
    op.execute("UPDATE officers SET role = 'officer' WHERE role = 'Officer'")
    op.alter_column("officers", "role", server_default="officer")
    op.drop_index("ix_visitor_entries_facility_phone", table_name="visitor_entries")
    op.drop_index("ix_staff_entries_facility_phone", table_name="staff_entries")
    op.drop_column("staff_entries", "phone")
    op.drop_column("staff_entries", "capacity")
