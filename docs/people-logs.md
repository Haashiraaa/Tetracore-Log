# People logs: visitors and staff

Visitors and staff share one set of rules (the trucks log has its own, see the end).
The code lives in `backend/src/api/entry_service.py` and `backend/src/models.py`;
the screens are `PersonInPage` and `lib/people.ts` in the frontend.

## What gets recorded

| Field | Visitors | Staff | Rule |
|---|---|---|---|
| Full name | yes | yes | At least two words (first and last name). Always labelled **Full name** |
| Phone | yes | yes | Required. See [Phone numbers](#phone-numbers) |
| Capacity | no | yes | Free text, at least 2 characters, e.g. `Cashier`. The role the person works in |
| Signature | yes | yes | Drawn on **sign-in and sign-out**, both required |

## Phone numbers

A phone number is the closest thing to an ID we have, so it is how we recognise a returning person.
It is stored as digits only: `+234 803 123 4567` and `2348031234567` both become `08031234567`.
Valid numbers are 7 to 15 digits after cleaning.

There is no register of people. The sign-in screens **search as you type**: from 3 digits on, the
people in the same facility whose number contains what was typed are listed under the box (up to 8,
numbers that start with the digits first, then the most recent), each with an **Inside** badge if they
have not signed out. Tap one to prefill their name (and capacity for staff), or go straight to
sign-out if they are inside. No match is fine: finish the number, press **Look up**, and sign them in
as new.

- `GET /visitors/search?q=0803` and `GET /staff/search?q=0803`: the matches, `[]` for none. 422
  under 3 digits. A leading `234` is read as `0`, as when a number is saved.
- `GET /visitors/lookup?phone=...` and `GET /staff/lookup?phone=...`: the one person with exactly
  this number (what **Look up** calls). Their latest entry is used and `open_entry_id` says whether
  they are inside.
- Each person appears once per number, with the details from their latest entry.

## One sign-in at a time

A phone number can have only one open entry per facility. Signing in a number that is still
inside is refused with `409 already_inside`; sign them out first.

## Sign in and sign out

The officer must be **on duty** (see [trucks-and-duty.md](trucks-and-duty.md)); the gate they stand at is recorded as `gate_in` / `gate_out`.
Both need a signature. Older rows from before this rule may have none, so the database columns stay
nullable; the API does not.

## Inside page

People who are still inside are shown as one long line each (name, capacity or purpose, phone,
time in, Sign out). Trucks use the same list style.

Each line has a clock that ticks every second, and turns orange after 6 hours. Visitors and trucks
also carry a thin bar along the bottom that fills over 12 hours, warming from grey to orange in the
second half and turning to moving hazard tape past the limit: that is the point where the server
raises `left_inside` (see [notifications.md](notifications.md)). Staff get the clock but no bar,
because staff are never warned about. When a line is signed out a "Signed out" stamp lands on it
for a moment (with a short buzz on phones) before it leaves the list.

## Trucks

Trucks are found by plate. The driver's name follows the same two-word full-name rule.
A truck's visit has a queue and statuses of its own: see [trucks-and-duty.md](trucks-and-duty.md).

## Data migration

`d7a3f1c9b5e2` adds `staff_entries.capacity` and `phone`, cleans old visitor phones to the digits-only
form, and renames stored role `officer` to `Officer`. Run `alembic upgrade head` on the server.
