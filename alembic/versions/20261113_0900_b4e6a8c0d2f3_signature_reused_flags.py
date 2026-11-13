"""mark signatures that were reused instead of drawn

Revision ID: b4e6a8c0d2f3
Revises: a3d5f7b9c1e2
Create Date: 2026-11-13 09:00:00

signature_in_reused / signature_out_reused on all three entry tables. True when the
signature was copied from one already on file (see docs/people-logs.md) rather than drawn
at the gate. Every existing row was drawn, so they start false.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b4e6a8c0d2f3"
down_revision = "a3d5f7b9c1e2"
branch_labels = None
depends_on = None

_TABLES = ("truck_entries", "visitor_entries", "staff_entries")


def upgrade() -> None:
    for table in _TABLES:
        for column in ("signature_in_reused", "signature_out_reused"):
            op.add_column(table, sa.Column(
                column, sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    for table in _TABLES:
        for column in ("signature_in_reused", "signature_out_reused"):
            op.drop_column(table, column)
