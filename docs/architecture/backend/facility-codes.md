# Facility codes

Every facility has a code that officers type at login. Nobody types it when the facility is
made: the server issues it from the state, so the format is always the same.

```
CNG-LAG-01
 │   │   └── number: counts up per state, never handed out twice
 │   └────── first three letters of the state (FCT for the Federal Capital Territory)
 └────────── fixed prefix
```

| State chosen | Codes issued, in order |
|---|---|
| Lagos | `CNG-LAG-01`, `CNG-LAG-02`, `CNG-LAG-03` |
| Akwa Ibom | `CNG-AKW-01`, `CNG-AKW-02` |
| Federal Capital Territory | `CNG-FCT-01` |

## Making one

Accounts page, **Facilities** tab, **Add a facility**: choose the state, type the name, add. The
new code is shown at once and appears in the table. Under the hood it is
`POST /api/admin/facilities` with `{"state": "Lagos", "name": "Ikeja Station"}`. A `code` in the
request is ignored, so a code cannot be chosen or invented. `GET /api/admin/states` lists the
states for the picker.

## Rules

- **One list of states** in `backend/src/facility_codes.py` (the 36 states and the FCT). Each
  has its own three letters; a test fails if two ever match.
- **Numbers are never reused.** Each state has a counter in the `counters` table
  (`facility_code:LAG`) that only goes up. If a facility is disabled, or even removed from the
  database, its number stays used and the next facility gets the next one.
- **Two digits at least** (`01`), growing past 99 as needed (`CNG-LAG-100`).
- **The state is stored** on the facility (`facilities.state`) in its proper spelling. A facility
  made before this rule has no state and keeps the code it was given.
- **A code that is already taken is skipped.** If one was seeded by hand, the next number is used.
- The code is **not editable** later: officers, logs and logins refer to it.

## Where it lives

| File | What it does |
|---|---|
| `backend/src/facility_codes.py` | The state list, the three-letter rule, the format |
| `backend/src/db/queries/counters.py` | Takes the next number from a locked counter |
| `backend/src/api/admin_service.py` | `create_facility` issues the code |
| `frontend/src/pages/admin/FacilitiesPanel.tsx` | The state picker |
| `tests/test_facility_codes.py`, `tests/api/routes/test_admin.py` | The rules above, tested |
