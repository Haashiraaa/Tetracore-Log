# backend/src/api/routes/__init__.py

"""Every router the app serves, in one list. A new log or area plugs in by adding
its module here; main.py needs no change."""

from fastapi import APIRouter

from backend.src.api.routes import admin, auth, staff, trucks, visitors

ROUTERS: tuple[APIRouter, ...] = (
    auth.router,
    admin.router,
    trucks.router,
    visitors.router,
    staff.router,
)
