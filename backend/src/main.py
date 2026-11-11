

# backend/src/main.py

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.src.api import event_service
from backend.src.api.routes import ROUTERS
from backend.src.config.settings import Settings
from backend.src.db.session import create_session
from backend.src.exceptions.errors import (
    AccountLockedError,
    AuthError,
    ConflictError,
    DomainError,
    InvalidSignatureError,
    MustChangePinError,
    NotFoundError,
    PermissionDeniedError,
    WeakPinError,
)

log = logging.getLogger(__name__)


def _check_left_inside() -> None:
    with create_session() as db:
        event_service.check_left_inside(db)


async def _watch_left_inside(every_minutes: int) -> None:
    """Every few minutes, warn about anyone still inside long after signing in. Several
    servers can run this at once: the database lets one warning through per entry."""
    while True:
        try:
            await asyncio.to_thread(_check_left_inside)
        except Exception:  # noqa: BLE001 - keep watching whatever one pass hit
            log.exception("left-inside check failed")
        await asyncio.sleep(every_minutes * 60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Settings.require_jwt_secret()
    Settings.require_pin_pepper()
    watcher = None
    if Settings.LEFT_INSIDE_CHECK_MINUTES > 0:
        watcher = asyncio.create_task(_watch_left_inside(Settings.LEFT_INSIDE_CHECK_MINUTES))
    try:
        yield
    finally:
        if watcher is not None:
            watcher.cancel()
            with suppress(asyncio.CancelledError):
                await watcher


app = FastAPI(title="Tetracore Log", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for _router in ROUTERS:
    app.include_router(_router, prefix="/api")

STATUS_RULES: tuple[tuple[type[DomainError], int], ...] = (
    (PermissionDeniedError, 403),
    (MustChangePinError, 403),
    (AccountLockedError, 429),
    (AuthError, 401),
    (NotFoundError, 404),
    (ConflictError, 409),          # also covers the AlreadyInside errors
    (WeakPinError, 422),
    (InvalidSignatureError, 422),
)


def _status_for(exc: DomainError) -> int:
    for cls, status_code in STATUS_RULES:
        if isinstance(exc, cls):
            return status_code
    return 400


@app.exception_handler(DomainError)
def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    headers = None
    if isinstance(exc, AccountLockedError):
        headers = {"Retry-After": str(exc.retry_after_seconds)}
    return JSONResponse(
        status_code=_status_for(exc),
        content={"detail": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def serve() -> None:
    """tetracore-log api. Add --reload for development."""
    import sys

    import uvicorn

    uvicorn.run("backend.src.main:app", host="127.0.0.1", port=8000,
                reload="--reload" in sys.argv)
