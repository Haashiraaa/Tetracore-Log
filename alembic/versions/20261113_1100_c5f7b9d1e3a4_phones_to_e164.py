"""store phone numbers in E.164

Revision ID: c5f7b9d1e3a4
Revises: b4e6a8c0d2f3
Create Date: 2026-11-13 11:00:00

Phone numbers used to be stored as digits with a Nigerian leading 0 (08031112222). They are now
E.164, "+" then the country code then the number (+2348031112222), so a visitor with a foreign
number works and every number says which country it belongs to.

Converted: visitor_entries.phone, staff_entries.phone, truck_entries.driver_phone and
trucks.driver_phone. A stored number that is not a real number (an old line typed before numbers
were checked) is left exactly as it is: it just will not be matched by a lookup. Numbers without a
country code are read as Nigerian, which is what every old number was.

Downgrade writes +234 numbers back as 0..., and leaves foreign numbers as they are.
"""

from __future__ import annotations

import phonenumbers
import sqlalchemy as sa
from alembic import op

revision = "c5f7b9d1e3a4"
down_revision = "b4e6a8c0d2f3"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("visitor_entries", "phone"),
    ("staff_entries", "phone"),
    ("truck_entries", "driver_phone"),
    ("trucks", "driver_phone"),
)


def _to_e164(raw: str) -> str | None:
    try:
        number = phonenumbers.parse(raw, "NG")
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(number):
        return None
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def _rewrite(convert) -> None:
    bind = op.get_bind()
    for table, column in _COLUMNS:
        stored = bind.execute(sa.text(
            f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")).scalars().all()
        for old in stored:
            new = convert(old)
            if new is not None and new != old:
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old"),
                    {"new": new, "old": old})


def upgrade() -> None:
    _rewrite(_to_e164)


def _to_local(stored: str) -> str | None:
    return "0" + stored[4:] if stored.startswith("+234") else None


def downgrade() -> None:
    _rewrite(_to_local)
