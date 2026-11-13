# Waybill and Events

Two logs next to trucks, visitors and staff. **Waybill** is a courier bringing goods; it is a
sign-in log. **Events** is an officer's own notes; it has no sign-out.

## Waybill

A courier visit follows the people-log rules (see [people-logs.md](people-logs.md)): the courier
is found again by **phone**, only one sign-in at a time per phone, sign-out reuses the sign-in
signature, and a returning courier's signature on file is reused (per facility). The code is
`waybill_service.py`, built on `entry_service.py`; the table is `waybill_entries`; the screen is
`PersonInPage kind="waybill"` in the frontend.

| Field | Rule |
|---|---|
| Courier name | Required, at least two words. Stored in `full_name` so the shared code works on it |
| Phone | Required, any country, stored as E.164 (see [people-logs.md](people-logs.md#phone-numbers)) |
| Items | **At least one**, up to 30: name, whole-number quantity (1 to 100,000, sent as a JSON number) and an optional unit. The same shape as a visitor's items |
| Came by vehicle | `came_by_vehicle`, a real `true`/`false` (default `false`). `"yes"` or `1` is a `422` |
| Plate | **Required when `came_by_vehicle` is true, and refused when it is false.** A courier on foot has no plate. Normalised like a truck plate (`LAG 123 ab` becomes `LAG123AB`). The database also enforces it |
| Signature | Drawn, or left out to reuse the one on file for this phone |

- `POST /api/waybill/entries`, `POST /api/waybill/entries/{id}/sign-out`, `GET /api/waybill/entries`
  (same filters as every log), `GET /api/waybill/entries/{id}/signature?side=in|out`.
- `GET /api/waybill/lookup?phone=` and `GET /api/waybill/search?q=`: like visitors, plus the
  vehicle and plate the courier **last** came with, to prefill the form. The items are new each
  visit and are never prefilled.
- Notifications: `waybill_in` and `waybill_out` ("Ngozi Courier signed in."). A courier still inside
  after `LEFT_INSIDE_HOURS` raises the same `left_inside` warning as a visitor.

## Events

An officer writes down what happened or what they noticed: *"Fuel tanker queue reached the main
road."* The code is `occurrence_service.py`; the table is `occurrences`; the screen is the
**Events** page. It is called `occurrences` in the code and API (`/api/occurrences`) so it is not
confused with `/api/events`, the alerts feed in [notifications.md](notifications.md).

| Field | Set by | Rule |
|---|---|---|
| Note | the officer | 3 to 2,000 characters, line breaks kept |
| Time (`logged_at`) | the server | Server time. The app may send a time with a timezone offset; a time without one is a `422` |
| Officer | the server | From the token, never the request. A body that says otherwise is ignored |
| Gate | the server | The gate the officer is on duty at |
| Facility | the server | The officer's facility |
| Signature | see below | |

- **The signature is not drawn on every note.** The server uses the officer's most recent
  signature from **going on duty** (the `signature_in` on their duty entries) and marks the note
  `signature_reused`. An officer who has never signed on duty must draw one on the note
  (`signature` in the request); without either the note is refused with `invalid_signature`.
  `GET /api/occurrences/signature-on-file` tells the app which case it is.
- **On duty is required**, like every other log (`not_on_duty` otherwise).
- **Notes are never edited or deleted.** A retry with the same id returns the stored note
  (`200`, not `201`); an id already used by another facility is a `409`.
- `GET /api/occurrences` lists newest first, scoped to the officer's facility; admins and
  facility-less accounts see every facility (`?facility_code=`). `GET /api/occurrences/{id}/signature`
  returns the PNG.
- Notification: `event_logged`, "Adaeze Okoro logged an event: ..." (the note cut at 140 characters),
  in the **Gate** group.

## Database

Migration `e7b9d1f3a5c6` adds `waybill_entries`, `occurrences` and the truck `cab_number` columns
(see [trucks-and-duty.md](trucks-and-duty.md#cab-number)). It changes nothing that exists. Run
`alembic upgrade head` on the server.
