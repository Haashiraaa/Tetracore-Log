# Trucks, gates and duty

How a truck's visit moves, how a facility's gates work, and why officers log their own duty.
Code: `backend/src/api/truck_service.py`, `duty_service.py`, `entry_service.py` (`require_gate`),
`routes/trucks.py`, `routes/duty.py`; in the frontend `pages/gate/TruckInPage.tsx`,
`pages/duty/DutyPage.tsx`, `components/entries/TruckQueueSheets.tsx`, `components/duty/`.

## A truck's visit

```
Queued  ──let in (driver signs)──>  On site  ──sign out (driver signs)──>  Departed
   └──gave up, with a reason──>  Left queue
```

| Status | Meaning | Signature |
|---|---|---|
| `queued` | Registered at the gate, still outside | none yet |
| `on_site` | Let in; inside the compound | driver signs **on the way in** (this step) |
| `departed` | Signed out | driver signs on the way out |
| `left_queue` | Gave up before entering | none. A **free-text reason** is required (2 to 300 characters) |

- **Register** (`POST /trucks/entries`): by default the truck joins the queue and needs no signature.
  With `enter_now: true` it is let in on the spot, which needs the driver's signature (drawn, or the
  one on file, see below).
- **Let in** (`POST /trucks/entries/{id}/enter`): `queued` -> `on_site`, signature drawn or on file.
- **Left queue** (`POST /trucks/entries/{id}/leave-queue`): `queued` -> `left_queue`, `reason` required.
- **Sign out** (`POST /trucks/entries/{id}/sign-out`): only from `on_site`. The signature may be left out:
  the one given when it was let in is used. A queued truck gets `409 invalid_truck_state`:
  let it in or mark it as left first. A repeat sign-out returns the stored row.

### Signatures are kept and reused

Trucks come back, so a driver should not have to sign every time. The rules are the same as for
visitors and staff ([people-logs.md](people-logs.md#signatures-are-kept-and-reused)), with the **plate**
(within one facility) as the identity:

- Letting a truck in (`enter_now`, or `/enter`) with no `signature` uses the latest signature given
  at this facility on a visit of the same truck, whoever the driver was this time. The new visit
  stores its own copy and is flagged `signature_in_reused`.
- Signing out with no `signature` copies the sign-in one (`signature_out_reused`).
- `GET /trucks/lookup` returns `has_signature`. With nothing on file (a new plate, or another
  facility's truck) leaving the signature out is refused with `422 invalid_signature`.
- Queuing a truck still needs no signature at all.

- A plate has **one open visit** (queued or on site). Registering it again is refused with `409
  truck_already_inside` and raises the `already_inside` warning. A truck that left the queue or departed can queue again.
- Time columns: `signed_in_at` is when the truck **joined the queue** (kept as the first time it was logged),
  `entered_at` is when it was let in, `signed_out_at` is when it departed **or** left the queue.
  "Inside for" counts from `entered_at`.
- `scm_purchased` is still recorded at sign-out.
- Existing rows were migrated: signed out -> `departed`, still open -> `on_site` (with `entered_at` = `signed_in_at`).

## Cab number

Optional. Some trucks have a number on the cab as well as a plate; most do not. Free text, up to 20
characters, blank means none. It is saved on the truck (so a returning truck is prefilled, and the
latest value wins) and copied onto each visit like the other driver details. It shows in the
Inside and Log lists ("Cab C-12"), the detail dialog and the CSV.

## Driver phone

Optional on a truck sign-in. When given it follows the same rules as a person's phone (E.164, checked
for its country, Nigerian unless it starts with `+`): see
[people-logs.md](people-logs.md#phone-numbers). A blank one is stored as none.

## Gates

Every facility has a number of gates, set when it is created (1 to 20, default 1) and changeable
on the **Accounts** page (`PUT /admin/facilities/{code}/gates`). Gates are numbered 1..N.
Lowering the number is refused while someone is on duty at a gate that would go away; each change
is a `gates_changed` event. **Existing facilities start with 1 gate**: set the real number after migrating.

Every truck, visitor and staff entry records **`gate_in`** and **`gate_out`**: the gate its officer stood
at when they signed it in and out. A truck also keeps `queued_gate` (where it joined the queue).

## Duty

Security officers log **themselves**, from their own login, on the **Duty** page.

- **Go on duty** (`POST /duty/on`): pick a gate from the facility's gates. The signature is **optional**.
- **Change gate** (`POST /duty/change-gate`): mid-shift. It closes the open stretch and opens a new one at the
  new gate; both share a `shift_id`.
- **Go off duty** (`POST /duty/off`): optional signature. Going off when already off changes nothing.
- An officer has **one open stretch at a time** (a unique index refuses a second).
- **Nobody logs anything off duty.** Signing a truck, visitor or staff member in or out, letting a truck in or
  marking it as left needs the officer to be on duty: otherwise `409 not_on_duty` ("Go on duty first").
  Staff do not log themselves; the officer logs staff as before. A **replay** of a request that has already
  happened (the same sign-in id, or a sign-out of someone already out) changes nothing and needs no duty.
- An admin can take someone off duty (`POST /admin/officers/{id}/end-duty`, the **End duty** button), for a
  forgotten sign-off. Disabling an account also ends its duty. Both are recorded as `ended_how = admin`.
- Reads: `GET /duty/now` (who is on duty, scoped like every read), `GET /duty/entries` (the log, same filters as the
  other logs), `GET /duty/entries/{id}/signature?side=in|out`.

On the Inside page, trucks get three counters above the lists: **Queued**, **On site** and **Left today**
(signed out since midnight in Lagos, whichever day the truck arrived; it is counted from the 200 newest
truck entries). The numbers roll as trucks move. A queued line has a bar that fills over 6 hours and an
on-site line one that fills over 12, matching `QUEUED_WARN_HOURS` and `LEFT_INSIDE_HOURS`. Letting a truck in,
signing it out or marking it as having left the queue stamps the line ("In", "Signed out", "Left queue") with
the time the server recorded.

The app shows **On duty, gate N** / **Off duty** in the menu, and sends an off-duty officer who opens a gate
page to the Duty page first. The server is the real check; the app only saves the trip.

## Warnings the server raises

Checked every `LEFT_INSIDE_CHECK_MINUTES`; each is raised **once** (see [notifications.md](notifications.md)).

| Kind | When | Setting |
|---|---|---|
| `queued_too_long` | A truck has been `queued` for `QUEUED_WARN_HOURS` | default 6, 0 = off |
| `on_duty_too_long` | A **shift** has run `DUTY_WARN_HOURS` (a change of gate does not restart it) | default 14, 0 = off |
| `gate_unmanned` | A gate that had an officer has had nobody for `GATE_UNMANNED_MINUTES` | default 15, 0 = off |

`gate_unmanned` is deliberately quiet: only a gate that **had** someone (never one nobody staffed), only after the
grace period (shift handovers do not trip it), only within the last 24 hours, once per vacancy, and only for gates
that still exist. `left_inside` for trucks counts from `entered_at`, so a queued truck is never "left inside".

## New events

`truck_queued`, `truck_left_queue`, `officer_on_duty`, `officer_off_duty`, `officer_gate_changed` (gate group)
and `gates_changed` (admin group).

## Database

Migration `f2c8d4a6b1e7`: `facilities.gate_count`, `gate_in`/`gate_out` on the three entry tables, the truck
status columns (with backfill), and the `duty_entries` table. Run `alembic upgrade head`.
