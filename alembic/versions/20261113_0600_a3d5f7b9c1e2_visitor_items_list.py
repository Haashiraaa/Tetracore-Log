"""visitor items as a list of name + quantity

Revision ID: a3d5f7b9c1e2
Revises: f2c8d4a6b1e7
Create Date: 2026-11-13 06:00:00

* visitor_entries.items: a JSON list of {"name", "quantity"}, one per thing the visitor
  brought. Null (not an empty list) when they brought nothing.
* visitor_entries.items_received stays: lines written before this change keep their free
  text there, and the app shows it when `items` is empty. New lines no longer write it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3d5f7b9c1e2"
down_revision = "f2c8d4a6b1e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visitor_entries", sa.Column("items", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("visitor_entries", "items")
