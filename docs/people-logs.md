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

There is no register of people. **Look up** (on the sign-in screens) finds the most recent entry
for that phone **in the same facility** and prefills the name (and the capacity for staff).
No match is fine: fill the form in and sign them in as new.

- `GET /visitors/lookup?phone=...` and `GET /staff/lookup?phone=...`
- The answer says whether the person is **already inside**, so the guard sees it before signing in.

## One sign-in at a time

A phone number can have only one open entry per facility. Signing in a number that is still
inside is refused with `409 already_inside`; sign them out first.

## Sign in and sign out

Both need a signature. Older rows from before this rule may have none, so the database columns stay
nullable; the API does not.

## Inside page

People who are still inside are shown as one long line each (name, capacity or purpose, phone,
time in, Sign out). Trucks use the same list style.

## Trucks

Trucks are found by plate. The driver's name follows the same two-word full-name rule.

## Data migration

`d7a3f1c9b5e2` adds `staff_entries.capacity` and `phone`, cleans old visitor phones to the digits-only
form, and renames stored role `officer` to `Officer`. Run `alembic upgrade head` on the server.
