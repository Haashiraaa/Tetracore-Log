

# tests/_helpers.py

from __future__ import annotations

import uuid
from typing import Optional

from fastapi.testclient import TestClient

from backend.src.db.orm.tables import DutyEntry
from backend.src.db.session import create_session
from backend.src.security.accounts import create_officer, get_or_create_facility
from backend.src.security.tokens import utcnow
from tests._schemas import Actor

PIN = "483920"


def make_account(
    *, code: str, facility: Optional[str] = None, role: str = "Officer",
    is_admin: bool = False, must_change_pin: bool = False, pin: str = PIN,
    on_duty: bool = True,
) -> uuid.UUID:
    """A facility account starts the test ON DUTY at gate 1 (written straight to the table,
    so no event is raised). Nobody can log anything otherwise: pass on_duty=False to test that."""
    with create_session() as db:
        if facility:
            get_or_create_facility(db, facility, f"Station {facility}")
        officer = create_officer(
            db, officer_code=code, full_name=f"Test {code}", pin=pin, role=role,
            is_admin=is_admin, facility_code=facility)
        officer.must_change_pin = must_change_pin
        if on_duty and officer.facility_id is not None:
            duty_id = uuid.uuid4()
            db.add(DutyEntry(
                id=duty_id, shift_id=duty_id, facility_id=officer.facility_id,
                officer_id=officer.id, gate=1, on_duty_at=utcnow()))
        db.commit()
        return officer.id


def login_response(client: TestClient, code: str, facility: Optional[str] = None,
                   pin: str = PIN):
    return client.post("/api/auth/login", json={
        "facility_code": facility, "officer_code": code, "pin": pin})


def login(client: TestClient, code: str, facility: Optional[str] = None,
          pin: str = PIN) -> dict[str, str]:
    r = login_response(client, code, facility, pin)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_actor(client: TestClient, *, code: str, facility: Optional[str] = None,
               role: str = "Officer", is_admin: bool = False,
               must_change_pin: bool = False, on_duty: bool = True) -> Actor:
    oid = make_account(code=code, facility=facility, role=role, is_admin=is_admin,
                       must_change_pin=must_change_pin, on_duty=on_duty)
    return Actor(oid, code, facility, login(client, code, facility))
