# backend/src/db/queries/counters.py

"""Locked-row sequences. A number is taken by reading `next_value` and bumping it
inside the caller's transaction; the row stays locked until commit, so two requests
can never get the same number, and a number is never given out twice."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.src.db.orm.tables import Counter


def locked_counter(db: Session, name: str) -> Counter:
    db.execute(pg_insert(Counter).values(name=name, next_value=1)
               .on_conflict_do_nothing(index_elements=["name"]))
    row = db.scalar(
        select(Counter).where(Counter.name == name).with_for_update()
        .execution_options(populate_existing=True))
    assert row is not None
    return row


def take_number(db: Session, name: str) -> int:
    counter = locked_counter(db, name)
    number, counter.next_value = counter.next_value, counter.next_value + 1
    db.flush()  # sessions run with autoflush off: without this a second call re-reads the old value
    return number
