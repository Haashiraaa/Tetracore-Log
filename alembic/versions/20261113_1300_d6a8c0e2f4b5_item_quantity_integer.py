"""visitor item quantities become whole numbers, with an optional unit

Revision ID: d6a8c0e2f4b5
Revises: c5f7b9d1e3a4
Create Date: 2026-11-13 13:00:00

An item in visitor_entries.items used to be {"name", "quantity"} with the quantity as free text
("2 boxes"). It is now {"name", "quantity", "unit"}: the quantity is an integer of 1 or more and
the unit is optional text.

Converted: a quantity that starts with a whole number keeps it, and the rest becomes the unit
("2 boxes" -> 2, "boxes"; "10" -> 10, no unit). Text with no usable leading number ("a few", "0",
"1,000") becomes quantity 1 and the old text moves into the name so nothing is lost
("Gloves (a few)"). Nothing is dropped.

Downgrade writes the quantity and unit back as one text ("2 boxes").
"""

from __future__ import annotations

import json
import re

import sqlalchemy as sa
from alembic import op

revision = "d6a8c0e2f4b5"
down_revision = "c5f7b9d1e3a4"
branch_labels = None
depends_on = None

_MAX_QUANTITY = 100_000
_LEADING_NUMBER = re.compile(r"^\s*(\d{1,6})(?!\d)\s*(.*?)\s*$")


def _convert(item: dict) -> dict:
    name = str(item.get("name", ""))
    old = item.get("quantity")
    if isinstance(old, int) and not isinstance(old, bool):
        return {"name": name, "quantity": old, "unit": item.get("unit")}
    text = "" if old is None else str(old).strip()
    match = _LEADING_NUMBER.match(text)
    if match and 1 <= int(match.group(1)) <= _MAX_QUANTITY and len(match.group(2)) <= 20:
        return {"name": name, "quantity": int(match.group(1)), "unit": match.group(2) or None}
    kept = f"{name} ({text})" if text else name
    if len(kept) > 100:
        kept = kept[:100]
    return {"name": kept, "quantity": 1, "unit": None}


def _restore(item: dict) -> dict:
    unit = item.get("unit")
    text = f"{item['quantity']} {unit}" if unit else str(item["quantity"])
    return {"name": item["name"], "quantity": text[:30]}


def _rewrite(convert) -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, items FROM visitor_entries WHERE items IS NOT NULL")).all()
    for row_id, items in rows:
        if not items:  # SQL NULL is filtered out above; this is a JSON null or an empty list
            continue
        new = [convert(i) for i in items]
        if new != items:
            bind.execute(
                sa.text("UPDATE visitor_entries SET items = CAST(:items AS jsonb) WHERE id = :id"),
                {"items": json.dumps(new), "id": row_id})


def upgrade() -> None:
    _rewrite(_convert)


def downgrade() -> None:
    _rewrite(_restore)
