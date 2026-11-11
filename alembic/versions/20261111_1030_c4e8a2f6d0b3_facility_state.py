"""facility state: codes are issued from a state (CNG-LAG-01)

Revision ID: c4e8a2f6d0b3
Revises: 9b1d3e5c7a21
Create Date: 2026-11-11 10:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4e8a2f6d0b3"
down_revision = "9b1d3e5c7a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: a facility made before codes came from a state keeps its old code.
    op.add_column("facilities", sa.Column("state", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("facilities", "state")
