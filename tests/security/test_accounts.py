
# tests/security/test_accounts.py  (backend/src/security/accounts.py)

import pytest

from backend.src.db.session import create_session
from backend.src.security import accounts
from tests._helpers import login_response, make_account, make_actor


def create(db, code="ADM-01", **over):
    kwargs = {"officer_code": code, "full_name": "Test Person", "pin": "483920", **over}
    return accounts.create_officer(db, **kwargs)


def find(db, code, facility=None):
    return accounts.find_officer(db, officer_code=code, facility_code=facility)


# ---- create_officer ----

def test_create_global_and_facility_accounts():
    make_account(code="SEED-1", facility="CNG-A")  # makes the facility
    with create_session() as db:
        glob = create(db, "G-1")
        member = create(db, "M-1", facility_code="cng-a", role="  Manager ")
        assert glob.facility_id is None and glob.role == "Officer"
        assert member.facility_id is not None and member.role == "Manager"
        assert member.officer_code == "M-1" and not member.is_admin


def test_same_code_is_fine_in_another_scope_but_not_twice_in_one():
    make_account(code="SEED-1", facility="CNG-A")
    make_account(code="SEED-2", facility="CNG-B")
    with create_session() as db:
        create(db, "X-1", facility_code="CNG-A")
        create(db, "X-1", facility_code="CNG-B")   # other facility: fine
        create(db, "X-1")                            # global: fine
        for scope in ("CNG-A", None):
            with pytest.raises(ValueError, match="already exists"):
                create(db, "x-1", facility_code=scope)  # case-insensitive


@pytest.mark.parametrize("over, message", [
    ({"facility_code": "NOPE"}, "does not exist"),
    ({"role": "   "}, "blank"),
    ({"pin": "111111"}, "PIN"),
])
def test_create_officer_rejects_bad_input(over, message):
    with create_session() as db, pytest.raises(ValueError, match=message):
        create(db, **over)


# ---- grant / revoke ----

def test_grant_then_revoke_keeps_the_account():
    make_account(code="OFF-001", facility="CNG-A", role="guard")
    make_account(code="ADM-01", is_admin=True)
    with create_session() as db:
        officer = find(db, "OFF-001", "CNG-A")
        accounts.grant_admin(officer)
        assert officer.is_admin
        accounts.revoke_admin(db, officer)
        assert (officer.is_admin, officer.role, officer.is_active) == (False, "guard", True)


def test_grant_refuses_admins_and_disabled_accounts():
    make_account(code="ADM-01", is_admin=True)
    make_account(code="OFF-001", facility="CNG-A")
    with create_session() as db:
        with pytest.raises(ValueError, match="already"):
            accounts.grant_admin(find(db, "ADM-01"))
        officer = find(db, "OFF-001", "CNG-A")
        officer.is_active = False
        with pytest.raises(ValueError, match="disabled"):
            accounts.grant_admin(officer)


def test_revoke_refuses_a_non_admin():
    make_account(code="OFF-001", facility="CNG-A")
    with create_session() as db, pytest.raises(ValueError, match="not an admin"):
        accounts.revoke_admin(db, find(db, "OFF-001", "CNG-A"))


def test_the_last_active_admin_is_protected():
    make_account(code="ADM-01", is_admin=True)
    with create_session() as db:
        only = find(db, "ADM-01")
        with pytest.raises(ValueError, match="LAST"):
            accounts.revoke_admin(db, only)
        accounts.revoke_admin(db, only, force=True)
        assert accounts.count_active_admins(db) == 0


def test_a_second_admin_means_the_first_can_go():
    make_account(code="ADM-01", is_admin=True)
    make_account(code="ADM-02", is_admin=True)
    with create_session() as db:
        accounts.revoke_admin(db, find(db, "ADM-01"))
        assert accounts.count_active_admins(db) == 1


def test_a_disabled_admin_does_not_count_as_the_last_one():
    make_account(code="ADM-01", is_admin=True)
    make_account(code="ADM-02", is_admin=True)
    with create_session() as db:
        gone = find(db, "ADM-02")
        gone.is_active = False
        accounts.revoke_admin(db, gone)   # not active, so not "the last active admin"
        assert accounts.count_active_admins(db) == 1


# ---- reset_admin_pin ----

def test_reset_admin_pin_sets_the_pin_and_signs_everyone_out(client):
    admin = make_actor(client, code="ADM-01", role="admin", is_admin=True)
    with create_session() as db:
        officer = find(db, "ADM-01")
        officer.failed_pin_attempts = 3
        accounts.reset_admin_pin(db, officer, "739150")
        db.commit()
    assert client.get("/api/auth/me", headers=admin.headers).status_code == 401
    assert login_response(client, "ADM-01", None, "483920").status_code == 401
    assert login_response(client, "ADM-01", None, "739150").status_code == 200


def test_reset_admin_pin_is_for_admins_only():
    make_account(code="OFF-001", facility="CNG-A")
    with create_session() as db, pytest.raises(ValueError, match="admins only"):
        accounts.reset_admin_pin(db, find(db, "OFF-001", "CNG-A"), "739150")
