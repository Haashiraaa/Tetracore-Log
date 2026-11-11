
# tests/test_main.py  (backend/src/main.py)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_super_admin_api_is_gone(client, admin):
    assert client.get("/api/super-admin/admins", headers=admin.headers).status_code == 404
    paths = client.get("/openapi.json").json()["paths"]
    assert not [p for p in paths if "super" in p]
