# Notifications for the global admin

Every event that happens is written down for admins, shown in a live feed, and (if switched on)
pushed to their phone or laptop. Code: `backend/src/api/event_service.py`, `push.py`,
`routes/events.py`; the screen is `pages/notifications/` in the frontend.

## What counts as an event

| Group | Kinds | When |
|---|---|---|
| **Gate** | `truck_queued`, `truck_in`, `truck_out`, `truck_left_queue`, `visitor_in`, `visitor_out`, `staff_in`, `staff_out`, `officer_on_duty`, `officer_off_duty`, `officer_gate_changed` | Every sign-in and sign-out, every change in a truck's queue, and every officer going on duty, off duty or changing gate, in every facility |
| **Admin** | `facility_added`, `gates_changed`, `officer_added`, `officer_pin_reset`, `officer_disabled`, `officer_enabled`, `sessions_revoked`, `admin_granted`, `admin_revoked` | Changes made on the Accounts page, and admin changes made from the server console (`log-book-admin`) |
| **Warnings** | `already_inside`, `left_inside`, `queued_too_long`, `on_duty_too_long`, `gate_unmanned` | Someone is signed in who is still inside, a visitor or truck is still inside many hours after signing in, a truck has queued too long, an officer has been on duty too long, or a gate has nobody on it |

Nothing else is recorded: logins, failed logins and PIN changes are **not** events.

- An event is written in the **same transaction** as the thing it describes. Nothing is announced that
  did not happen, and a sign-in is never recorded without its event.
- Retries are not news: sending the same sign-in again, or signing out twice, records nothing new.
- Events are never edited or deleted.
- Admin changes made from the console are in the feed (marked "from the server console") but are
  **not pushed**: only the running server sends push.

## The warnings

- **`already_inside`**: a truck, visitor or staff member is signed in while they already have an
  open entry. The sign-in is refused (409) as before; the warning is the record that someone tried.
- **`left_inside`**: nobody is acting, so the server notices. Every `LEFT_INSIDE_CHECK_MINUTES`
  minutes it looks for entries still open `LEFT_INSIDE_HOURS` after sign-in and raises **one** warning
  per entry (the database refuses a second, so several servers can run the check safely).
  **Staff are not checked**: a staff member can stay inside for many ordinary reasons, so it would only be noise.
  A truck counts from when it was let in (`entered_at`); a truck still in the queue is never "left inside".
  Set `LEFT_INSIDE_CHECK_MINUTES=0` to turn all the server's checks off.
- **`queued_too_long`**, **`on_duty_too_long`**, **`gate_unmanned`**: raised by the same check, once each. What they
  mean and their settings are in [trucks-and-duty.md](trucks-and-duty.md#warnings-the-server-raises). Their dedupe key
  is the truck entry, the shift, or the last stretch that left the gate.

## Who sees it

Any admin (`is_admin`), like the rest of the admin API. Admins already read every facility, so the
feed shows every facility. Officers and non-admin global accounts get 403.

Each admin has their own read position, so one admin reading does not clear another's bell.
An admin's first look starts at "all read" rather than the whole history as unread.

## In the app

**Alerts** in the menu, with the unread count (also in the tab title). The page lists events newest
first, filtered by group, facility or unread. The app asks the server for the count every
5 seconds and new rows slide in at the top by themselves. **Mark all as read** clears the bell.

## Browser push

Off until the server has keys. Then each admin switches it on **per device** with **Turn on** on the
Alerts page; the browser asks permission once.

1. Make the keys, once: `python -m scripts.vapid_keys` ([guide](scripts/vapid_keys.md)).
2. Put the three lines in the server's `.env` (set `VAPID_SUBJECT` to a real `mailto:`), restart the API.
3. Open the Alerts page on each device and press **Turn on**.

Check it with **Send test notification** (shown when the device is on). It sends to your own devices
and says why it failed. On startup the server logs whether push is on or off.

Things to know:

- Push needs **https** (or `localhost`). Over plain `http://<laptop-ip>` the page says the browser
  cannot do it; the feed still works.
- On iPhone, push works only for a web app **added to the Home Screen**.
- Every event is pushed, to every browser of every active admin. A disabled or demoted admin gets none.
- Push is sent after the request has finished, on a small thread pool. A slow or dead push service can
  never slow the gate down, and a failed push is logged and dropped: the event is in the feed either way.
- A browser the push service reports gone (404/410) is forgotten automatically.
- If you regenerate the VAPID keys, browsers set up under the old keys stop receiving. The app notices
  and switches that device back to **Turn on**; press it once to subscribe under the new key.
- Logging out does not turn push off for that device. Use **Turn off** first if the device is shared.

## API (all admin-only)

| Route | Use |
|---|---|
| `GET /admin/events` | `limit`, `before_id` (page back), `after_id` (poll forward), `facility_code`, `group=gate\|admin\|warnings`. Newest first |
| `GET /admin/events/summary` | `{latest_id, last_read_id, unread}` for the signed-in admin; cheap, polled |
| `POST /admin/events/read` | `{up_to_id}` (omit for "everything"). Only moves forward |
| `GET /admin/push/config` | `{public_key}`, `null` when push is not set up |
| `POST /admin/push/subscribe` | The browser's `PushSubscription` JSON |
| `POST /admin/push/unsubscribe` | `{endpoint}` |
| `POST /admin/push/test` | Sends a test to the caller's own browsers: `{subscriptions, sent, failed[]}`. 409 if push is not set up |

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | unset | Browser push. All three or it stays off |
| `LEFT_INSIDE_HOURS` | 12 | Hours after sign-in before "left inside" |
| `LEFT_INSIDE_CHECK_MINUTES` | 10 | How often the server looks for all the warnings below. 0 = off |
| `QUEUED_WARN_HOURS` | 6 | Hours a truck may wait in the queue before the warning. 0 = off |
| `DUTY_WARN_HOURS` | 14 | Hours a shift may run before the warning. 0 = off |
| `GATE_UNMANNED_MINUTES` | 15 | Minutes a manned gate may be empty before the warning. 0 = off |

## Database

`events` (append-only, ordered by `id`), `event_cursors` (each admin's read position) and
`push_subscriptions` (one row per browser). Migration `e1b5c7d9a3f4`: run `alembic upgrade head`.
Migration `f2c8d4a6b1e7` widens the "once only" rule to every warning the server raises (one per kind and entry).
