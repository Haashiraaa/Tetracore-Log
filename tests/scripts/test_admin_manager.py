
# tests/scripts/test_admin_manager.py  (scripts/admin_manager.py)

import pytest

from scripts import admin_manager
from tests._helpers import PIN, login, login_response, make_account, make_actor


@pytest.fixture
def run(monkeypatch, capsys):
    """run("create", "--code", "A", pins=["483920", "483920"]) -> (exit code, stdout, stderr)"""
    def _run(*argv, pins=()):
        answers = iter(pins)
        monkeypatch.setattr("getpass.getpass", lambda _prompt="": next(answers))
        code = admin_manager.main(list(argv))
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


def test_create_a_global_admin_who_can_log_in(client, run):
    code, out, _ = run("create", "--code", "adm-01", "--name", "Ada Obi",
                       pins=[PIN, PIN])
    assert code == 0 and "ADM-01" in out
    headers = login(client, "ADM-01", None, PIN)
    me = client.get("/api/auth/me", headers=headers).json()
    assert (me["is_admin"], me["role"], me["must_change_pin"]) == (True, "admin", False)
    assert client.get("/api/admin/facilities", headers=headers).status_code == 200


def test_create_an_admin_inside_a_facility_with_a_custom_role(client, run):
    make_account(code="SEED-1", facility="CNG-A")
    code, _, _ = run("create", "--code", "SUP-01", "--name", "Site Lead",
                     "--facility", "cng-a", "--role", "Supervisor", pins=[PIN, PIN])
    assert code == 0
    me = client.get("/api/auth/me", headers=login(client, "SUP-01", "CNG-A", PIN)).json()
    assert (me["is_admin"], me["role"], me["facility_code"]) == (True, "Supervisor", "CNG-A")
    assert me["can_write_entries"] is True  # an admin that belongs to a facility


def test_mismatched_or_weak_pins_create_nothing(run):
    code, _, err = run("create", "--code", "ADM-01", "--name", "A", pins=[PIN, "000000"])
    assert code == 1 and "do not match" in err
    code, _, err = run("create", "--code", "ADM-01", "--name", "A", pins=["111111", "111111"])
    assert code == 1 and err.startswith("Error:")
    code, out, _ = run("list")
    assert "No admins" in out


def test_duplicate_code_is_an_error(run):
    make_account(code="ADM-01", is_admin=True)
    code, _, err = run("create", "--code", "adm-01", "--name", "Twin", pins=[PIN, PIN])
    assert code == 1 and "already exists" in err


def test_grant_then_revoke(client, run):
    make_account(code="ADM-01", is_admin=True)  # keeps one admin around
    officer = make_actor(client, code="OFF-001", facility="CNG-A")
    assert client.get("/api/admin/facilities", headers=officer.headers).status_code == 403

    code, out, _ = run("grant", "--code", "off-001", "--facility", "cng-a")
    assert code == 0 and "now an admin" in out
    # takes effect on the very next request, no new login needed
    assert client.get("/api/admin/facilities", headers=officer.headers).status_code == 200

    code, out, _ = run("revoke", "--code", "OFF-001", "--facility", "CNG-A")
    assert code == 0 and "unchanged" in out
    assert client.get("/api/admin/facilities", headers=officer.headers).status_code == 403
    assert login_response(client, "OFF-001", "CNG-A").status_code == 200  # account intact


def test_grant_and_revoke_errors(run):
    make_account(code="OFF-001", facility="CNG-A")
    code, _, err = run("revoke", "--code", "OFF-001", "--facility", "CNG-A")
    assert code == 1 and "not an admin" in err
    code, _, err = run("grant", "--code", "NOBODY", "--facility", "CNG-A")
    assert code == 1 and "No such officer" in err


def test_the_last_admin_needs_force(run):
    make_account(code="ADM-01", is_admin=True)
    code, _, err = run("revoke", "--code", "ADM-01")
    assert code == 1 and "LAST" in err
    code, _, _ = run("revoke", "--code", "ADM-01", "--force")
    assert code == 0
    assert "No admins" in run("list")[1]


def test_reset_pin_for_an_admin(client, run):
    admin = make_actor(client, code="ADM-01", role="admin", is_admin=True)
    code, out, _ = run("reset-pin", "--code", "ADM-01", pins=["739150", "739150"])
    assert code == 0 and "sessions revoked" in out
    assert client.get("/api/auth/me", headers=admin.headers).status_code == 401
    assert login_response(client, "ADM-01", None, PIN).status_code == 401
    assert login_response(client, "ADM-01", None, "739150").status_code == 200


def test_reset_pin_refuses_non_admins(run):
    make_account(code="OFF-001", facility="CNG-A")
    code, _, err = run("reset-pin", "--code", "OFF-001", "--facility", "CNG-A",
                       pins=["739150", "739150"])
    assert code == 1 and "admins only" in err


def test_list_shows_only_admins(run):
    make_account(code="ADM-01", role="admin", is_admin=True)
    make_account(code="OFF-001", facility="CNG-A")
    code, out, _ = run("list")
    assert code == 0 and "ADM-01" in out and "OFF-001" not in out


def test_list_all_shows_every_account_and_marks_admins(run):
    make_account(code="ADM-01", role="admin", is_admin=True)
    make_account(code="OFF-001", facility="CNG-A")
    code, out, _ = run("list", "--all")
    lines = {ln.split()[0]: ln for ln in out.splitlines()}
    assert code == 0 and set(lines) == {"ADM-01", "OFF-001"}
    assert "admin" in lines["ADM-01"].split("active")[0].split("facility=")[1]
    assert "facility=CNG-A" in lines["OFF-001"]


def test_list_all_on_an_empty_database(run):
    assert "No accounts" in run("list", "--all")[1]


def test_there_is_no_super_admin_command():
    with pytest.raises(SystemExit):
        admin_manager.main(["promote", "--code", "X"])


def test_admin_changes_from_the_console_reach_the_notification_feed(client, run):
    watcher = make_actor(client, code="ADM-000", role="admin", is_admin=True)
    make_account(code="OFF-003", facility="CNG-A")
    run("grant", "--code", "OFF-003", "--facility", "CNG-A")
    run("revoke", "--code", "OFF-003", "--facility", "CNG-A")
    events = client.get("/api/admin/events", params={"group": "admin"},
                        headers=watcher.headers).json()
    assert [e["kind"] for e in reversed(events)] == ["admin_granted", "admin_revoked"]
    assert events[0]["summary"] == (
        "Test OFF-003 (OFF-003) is no longer an admin (from the server console).")
    assert events[0]["facility_code"] == "CNG-A" and events[0]["actor_name"] is None


def test_the_tetracore_admin_command_is_registered():
    """`tetracore-admin` must point at a real callable, or the command breaks after install."""
    from pathlib import Path

    text = (Path(__file__).parents[2] / "pyproject.toml").read_text()
    assert 'tetracore-admin = "scripts.admin_manager:main"' in text
    assert callable(admin_manager.main)
    assert admin_manager._build_parser().prog == "tetracore-admin"
