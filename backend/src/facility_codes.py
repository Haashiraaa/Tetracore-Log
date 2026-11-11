# backend/src/facility_codes.py

"""Facility codes: CNG-<state>-<number>, e.g. CNG-LAG-01.

The state part is the first three letters of the state (FCT for the Federal Capital
Territory). The number counts up per state and is never handed out twice, even if a
facility is later disabled. Codes are issued by the server, never typed by a person."""

from __future__ import annotations

import re

PREFIX = "CNG"
FCT = "Federal Capital Territory"

STATES: tuple[str, ...] = (
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", FCT, "Gombe", "Imo",
    "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
    "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara",
)

CODE_RE = re.compile(rf"^{PREFIX}-[A-Z]{{3}}-\d{{2,}}$")


def state_abbrev(state: str) -> str:
    """LAG for Lagos, AKW for Akwa Ibom, FCT for the Federal Capital Territory."""
    return "FCT" if state == FCT else state[:3].upper()


def canonical_state(raw: str) -> str | None:
    """The state's proper spelling for any casing or spacing, or None if unknown."""
    wanted = " ".join(raw.split()).casefold()
    return next((s for s in STATES if s.casefold() == wanted), None)


def format_code(state: str, number: int) -> str:
    return f"{PREFIX}-{state_abbrev(state)}-{number:02d}"
