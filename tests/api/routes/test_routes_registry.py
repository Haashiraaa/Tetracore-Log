# tests/api/routes/test_routes_registry.py

from backend.src.api.routes import ROUTERS
from backend.src.main import app


def test_every_router_is_served_under_api():
    paths = set(app.openapi()["paths"])
    assert any(p.startswith("/api/trucks") for p in paths)
    assert any(p.startswith("/api/visitors") for p in paths)
    assert any(p.startswith("/api/staff") for p in paths)


def test_router_prefixes_are_unique():
    prefixes = [r.prefix for r in ROUTERS]
    assert len(prefixes) == len(set(prefixes))
