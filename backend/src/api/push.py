# backend/src/api/push.py

"""Browser push (Web Push, VAPID). Sends one notification to every browser of every active
admin. It runs on a small thread pool AFTER the request has committed and answered, so a slow
or dead push service can never slow the gate down or undo a sign-in. Every failure is logged
and swallowed: a missed push is not worth failing a request over, the event is in the feed
either way."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from pywebpush import WebPushException, webpush

from backend.src.config.settings import Settings
from backend.src.db.queries import events as q
from backend.src.db.session import create_session

log = logging.getLogger(__name__)

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="push")

# The push service says these mean "that browser is gone": forget it.
_GONE = (404, 410)


def dispatch(event_ids: Iterable[int]) -> None:
    """Queue pushes for these events. Returns at once. Does nothing if push is not set up."""
    ids = list(event_ids)
    if ids and Settings.push_enabled():
        _pool.submit(_send_all, ids)


def _payload(summary: str, facility_code: str | None, warning: bool, event_id: int) -> str:
    where = facility_code or "Log Book"
    return json.dumps({
        "title": f"Warning · {where}" if warning else where,
        "body": summary,
        "tag": f"event-{event_id}",
        "url": "/notifications",
    })


def _send_all(event_ids: list[int]) -> None:
    try:
        with create_session() as db:
            subs = q.admin_subscriptions(db)
            if not subs:
                return
            for event_id in event_ids:
                found = q.event_with_facility(db, event_id)
                if found is None:
                    continue
                event, facility_code = found
                data = _payload(event.summary, facility_code,
                                event.severity == "warning", event.id)
                for sub in subs:
                    _send_one(db, sub.endpoint, sub.p256dh, sub.auth, data)
            db.commit()
    except Exception:  # noqa: BLE001 - see the module docstring
        log.exception("push dispatch failed")


def send_test(db, officer_id) -> dict:
    """Send a test notification to this admin's own browsers, one by one, and say what happened.
    Each test gets its own tag: a repeated tag makes the browser swap the old notification
    silently instead of showing a new one.
    Unlike real pushes this waits for the answer, so a failure is shown, not only logged."""
    subs = [s for s in q.admin_subscriptions(db) if s.officer_id == officer_id]
    data = json.dumps({"title": "Log Book", "body": "Test notification. Push is working.",
                       "tag": f"push-test-{time.time_ns()}", "url": "/notifications"})
    sent, failed = 0, []
    for sub in subs:
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint,
                                   "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=data, vapid_private_key=Settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": Settings.VAPID_SUBJECT}, ttl=60)
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in _GONE:
                q.delete_subscription_by_endpoint(db, sub.endpoint)
                failed.append("The push service forgot this browser. "
                              "Turn notifications off and on again.")
            elif status in (400, 401, 403):
                failed.append("The push service rejected the server's keys. "
                              "Turn notifications off and on again on this device.")
            else:
                failed.append(f"The push service answered {status or 'with an error'}.")
            log.warning("test push failed (%s): %s", status, exc)
        except Exception as exc:  # noqa: BLE001
            failed.append("The server could not send the push.")
            log.warning("test push failed: %s", exc)
    db.commit()
    return {"subscriptions": len(subs), "sent": sent, "failed": failed}


def _send_one(db, endpoint: str, p256dh: str, auth: str, data: str) -> None:
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=data,
            vapid_private_key=Settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": Settings.VAPID_SUBJECT},
            ttl=60 * 60 * 12,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in _GONE:
            q.delete_subscription_by_endpoint(db, endpoint)
        else:
            log.warning("push to one browser failed: %s", exc)
    except Exception:  # noqa: BLE001
        log.exception("push to one browser failed")
