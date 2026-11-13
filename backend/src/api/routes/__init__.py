# backend/src/api/routes/__init__.py

"""Every router the app serves, in one list. A new log or area plugs in by adding
its module here; main.py needs no change."""

from fastapi import APIRouter

from backend.src.api.routes import (
    admin,
    auth,
    duty,
    events,
    occurrences,
    staff,
    trucks,
    visitors,
    waybill,
)

ROUTERS: tuple[APIRouter, ...] = (
    auth.router,
    admin.router,
    events.router,
    events.push_router,
    duty.router,
    trucks.router,
    visitors.router,
    staff.router,
    waybill.router,
    occurrences.router,
)
