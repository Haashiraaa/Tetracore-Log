"""visitor and staff logs: fields match the paper log, sign-out signature

Revision ID: 9b1d3e5c7a21
Revises: 4adf8c908da2
Create Date: 2026-11-11 04:20:00.000000

* every log (trucks, visitors, staff) gets signature_out, next to signature_in.
* visitor_entries: organization -> company, new items_received; the guessed
  person_visited / id_type / id_number columns are dropped.
* staff_entries: the entry carries the name itself (full_name, filled from the staff
  register for existing rows); the staff register table and staff_id are dropped.
  Downgrade rebuilds a register from the distinct names per facility.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9b1d3e5c7a21'
down_revision: Union[str, None] = '4adf8c908da2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOGS = ("truck_entries", "visitor_entries", "staff_entries")


def upgrade() -> None:
    for table in LOGS:
        op.add_column(table, sa.Column("signature_out", sa.LargeBinary(), nullable=True))

    op.alter_column("visitor_entries", "organization", new_column_name="company")
    op.add_column("visitor_entries",
                  sa.Column("items_received", sa.String(length=500), nullable=True))
    for column in ("person_visited", "id_type", "id_number"):
        op.drop_column("visitor_entries", column)

    op.add_column("staff_entries",
                  sa.Column("full_name", sa.String(length=150), nullable=True))
    op.execute("""
        UPDATE staff_entries e SET full_name = s.full_name
        FROM staff s WHERE s.id = e.staff_id AND s.facility_id = e.facility_id
    """)
    op.alter_column("staff_entries", "full_name", nullable=False)
    op.drop_constraint("fk_staff_entries_facility_staff", "staff_entries", type_="foreignkey")
    op.drop_column("staff_entries", "staff_id")
    op.drop_table("staff")


def downgrade() -> None:
    op.create_table(
        "staff",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("staff_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], name=op.f("fk_staff_facility_id_facilities"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff")),
        sa.UniqueConstraint("facility_id", "id", name="uq_staff_facility_id_id"),
        sa.UniqueConstraint("facility_id", "staff_code", name="uq_staff_facility_id_staff_code"),
    )
    op.execute("""
        INSERT INTO staff (id, facility_id, staff_code, full_name)
        SELECT gen_random_uuid(), facility_id, 'S-' || row_number() OVER (PARTITION BY facility_id ORDER BY full_name), full_name
        FROM (SELECT DISTINCT facility_id, full_name FROM staff_entries) names
    """)
    op.add_column("staff_entries", sa.Column("staff_id", sa.Uuid(), nullable=True))
    op.execute("""
        UPDATE staff_entries e SET staff_id = s.id
        FROM staff s WHERE s.facility_id = e.facility_id AND s.full_name = e.full_name
    """)
    op.alter_column("staff_entries", "staff_id", nullable=False)
    op.create_foreign_key(
        "fk_staff_entries_facility_staff", "staff_entries", "staff",
        ["facility_id", "staff_id"], ["facility_id", "id"], ondelete="RESTRICT")
    op.drop_column("staff_entries", "full_name")

    for column, kind in (("id_number", sa.String(64)), ("id_type", sa.String(40)),
                         ("person_visited", sa.String(150))):
        op.add_column("visitor_entries", sa.Column(column, kind, nullable=True))
    op.drop_column("visitor_entries", "items_received")
    op.alter_column("visitor_entries", "company", new_column_name="organization")

    for table in LOGS:
        op.drop_column(table, "signature_out")
