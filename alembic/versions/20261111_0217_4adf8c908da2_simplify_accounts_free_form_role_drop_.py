"""simplify accounts: free-form role, drop super admin

Revision ID: 4adf8c908da2
Revises: 61e05cc4a848
Create Date: 2026-11-11 02:17:00.000000

* role becomes a free-form label: the CHECK that limited it to three values is
  dropped, and so is the CHECK that tied "no facility" to the 'cso' role. What an
  account may do now comes from facility_id and is_admin (see backend/src/models.py).
  A new CHECK only refuses a blank role.
* super admin is gone: the is_super_admin column and its CHECK are dropped.
  Existing super admins simply stay ordinary admins.
* facilities.next_officer_seq was never read (the counters table issues codes)
  and is dropped.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4adf8c908da2'
down_revision: Union[str, None] = '61e05cc4a848'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_officers_super_admin_requires_admin"),
                       "officers", type_="check")
    op.drop_constraint(op.f("ck_officers_facility_required_unless_global"),
                       "officers", type_="check")
    op.drop_constraint(op.f("ck_officers_role_valid"), "officers", type_="check")

    op.drop_column("officers", "is_super_admin")
    op.drop_column("facilities", "next_officer_seq")

    op.create_check_constraint(
        op.f("ck_officers_role_not_blank"), "officers", "length(btrim(role)) > 0")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_officers_role_not_blank"), "officers", type_="check")

    op.add_column("facilities", sa.Column(
        "next_officer_seq", sa.Integer(), server_default=sa.text("1"), nullable=False))
    op.add_column("officers", sa.Column(
        "is_super_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # Free-form roles can not satisfy the old rules, so map them first:
    # no facility -> 'cso'; a facility but an unknown label -> 'officer'.
    op.execute("UPDATE officers SET role = 'cso' WHERE facility_id IS NULL")
    op.execute("UPDATE officers SET role = 'officer' WHERE facility_id IS NOT NULL "
               "AND role NOT IN ('officer', 'facility_manager', 'cso')")

    op.create_check_constraint(
        op.f("ck_officers_role_valid"), "officers",
        "role IN ('officer', 'facility_manager', 'cso')")
    op.create_check_constraint(
        op.f("ck_officers_facility_required_unless_global"), "officers",
        "role IN ('cso') OR facility_id IS NOT NULL")
    op.create_check_constraint(
        op.f("ck_officers_super_admin_requires_admin"), "officers",
        "NOT is_super_admin OR is_admin")
