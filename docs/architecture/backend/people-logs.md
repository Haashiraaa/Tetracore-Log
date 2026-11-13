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
| Items brought | yes | no | Optional list of **name + quantity** rows. See [Items brought](#items-brought-visitors) |
| Signature | yes | yes | Both a sign-in and a sign-out signature are stored, but nobody has to draw twice. See [Signatures are kept and reused](#signatures-are-kept-and-reused) |

## Items brought (visitors)

A visitor can bring nothing, or several things. On the sign-in form the field is collapsed to a
single **+ Add item** button; each tap adds one **name + quantity** row (the cursor lands in the
name), and **×** removes a row. A row left completely empty is ignored; a half-filled row is refused
("Give each item a name and a quantity, or remove it").

- Stored as `visitor_entries.items`, a JSON list of `{"name", "quantity"}` in the order given.
  Name is up to 100 characters, quantity is free text up to 30 (`"2 boxes"`), at most 30 items.
  Nothing brought is stored as null and comes back as `[]`.
- The detail dialog lists them; the CSV has one **Items brought** column: `Oil filters (2 boxes); Gloves (10)`.
- Lines written before this change keep their free text in `items_received` (the column stays, new
  lines never write it). The API still returns it and the screens show it when `items` is empty.
  `items_received` is no longer accepted on sign-in; an old client that still sends it is ignored.
- Migration `a3d5f7b9c1e2` adds the column. Run `alembic upgrade head` on the server.

## Signatures are kept and reused

Visitors and staff are not made to sign twice or sign again on every visit. The rules (all in
`entry_service.py`, shared by both logs; trucks use them too):

- **Sign-out reuses the sign-in signature.** Leave `signature` out of `POST .../sign-out` and the
  server copies the signature given at sign-in into the sign-out. The sign-out sheet shows that
  signature and a **Sign out** button, so the officer can sign someone out who is no longer at the
  gate. **Let them sign instead** opens the pad; a drawn signature is stored as given.
- **A returning person need not sign in again.** Signatures are stored per entry, and the latest
  sign-in signature for a phone number **in the same facility** is the one on file. Leave `signature`
  out of `POST .../entries` and it is used. Name, company, capacity and the rest are still
  typed or corrected as usual; only the signature carries over. **Sign again instead** replaces it
  (the new one becomes the one on file).
- `GET .../lookup` and `GET .../search` return `has_signature`: whether one is on file for that
  number, which is how the form knows to skip the pad.
- **When there is nothing to reuse** (a number never seen at this facility, or an old line from before
  signatures were required) the request is refused with `422 invalid_signature` and the form shows the
  pad. A signature is never borrowed from another facility.
- A signature that is sent is checked as before (PNG, at most 200 KB).
- **Reused is recorded.** Every entry says whether each signature was drawn or copied:
  `signature_in_reused` (copied from one on file) and `signature_out_reused` (copied from sign-in).
  The detail dialog notes it under the signature and the CSV says `yes (reused)`. Migration
  `b4e6a8c0d2f3` adds the two flags (all existing rows are `false`: they were drawn).
- **Trucks follow the same rules** with the plate as the identity instead of the phone: see
  [trucks-and-duty.md](trucks-and-duty.md#signatures-are-kept-and-reused).

## Phone numbers

A phone number is the closest thing to an ID we have, so it is how we recognise a returning person.
It is stored in **E.164** (`+2348031234567`), country code included, and checked against the real
numbering plan of its country with Google's libphonenumber (`phonenumbers` on the server,
`libphonenumber-js` in the app, so both sides agree).

- A number typed **without** a `+` is read as Nigerian: `0803 123 4567`, `803 123 4567` and
  `2348031234567` all become `+2348031234567`. The default is `DEFAULT_PHONE_REGION` (`"NG"`), set in
  `backend/src/models.py` and `frontend/src/config/env.ts`; change both together.
- A number that starts with `+` is read as that country's, so a foreign visitor is
  `+44 7911 123456` and is stored as `+447911123456`.
- It must be a number that can really exist in that country (right length, valid prefix). Letters,
  extensions and made-up numbers are refused with `422`, and the message says how to type one.
- Screens show it formatted internationally (`+234 803 123 4567`); the CSV keeps E.164.

There is no register of people. The sign-in screens **search as you type**: from 3 digits on, the
people in the same facility whose number contains what was typed are listed under the box (up to 8,
numbers that start with the digits first, then the most recent), each with an **Inside** badge if they
have not signed out. Tap one to prefill their name (and capacity for staff), or go straight to
sign-out if they are inside. No match is fine: finish the number, press **Look up**, and sign them in
as new.

- `GET /visitors/search?q=0803` and `GET /staff/search?q=0803`: the matches, `[]` for none. 422
  under 3 digits. A leading `0` or `00` is dropped and the rest is matched anywhere in the stored
  number, so `0803`, `803` and `+234803` find the same people, and `+44` or `7911` find a foreign one.
  The app's own filter on the Log page does the same on the formatted and national forms.
- `GET /visitors/lookup?phone=...` and `GET /staff/lookup?phone=...`: the one person with exactly
  this number (what **Look up** calls). Their latest entry is used and `open_entry_id` says whether
  they are inside.
- Each person appears once per number, with the details from their latest entry.

## One sign-in at a time

A phone number can have only one open entry per facility. Signing in a number that is still
inside is refused with `409 already_inside`; sign them out first.

## Sign in and sign out

The officer must be **on duty** (see [trucks-and-duty.md](trucks-and-duty.md)); the gate they stand at is recorded as `gate_in` / `gate_out`.
Both need a signature, drawn now or reused (see [above](#signatures-are-kept-and-reused)). Older rows
from before this rule may have none, so the database columns stay nullable; the API does not.

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

`c5f7b9d1e3a4` converts every stored phone (visitor and staff entries, truck entries, trucks) to
E.164, reading old numbers as Nigerian. A value that is not a valid number is left as it was rather
than lost. Downgrading turns `+234…` back into `0…`.
