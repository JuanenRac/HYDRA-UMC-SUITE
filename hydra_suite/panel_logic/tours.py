# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/panel_logic/tours.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The guided tours of the SUITE, without any window toolkit.

A tour is a list of steps; each step is a card with a title and a body in the language of the interface (`TOUR_<ID>_<N>_T` and `TOUR_<ID>_<N>_B` in the language
files, so a step cannot exist without its sentences: tests/verify_preferences.py checks it). The tours are off until the person turns on "Offer the guided
tours" in the Preferences (off by default); then the application menu offers the welcome tour and the Ecosystem health screen offers the tour of that screen.
Unlike the tours of STUDIO a step does not light up a part of the window: it is a card in the middle that says where to look."""
from __future__ import annotations

from hydra_suite.i18n import _

#: tour id -> number of steps. The screen a tour explains (None: the whole program) is the key the navigation uses.
TOURS: dict[str, int] = {"welcome": 5, "health": 2}
SCREENS: dict[str, str | None] = {"welcome": None, "health": "ecosystem_health"}


def tour_for_screen(screen_key: str) -> str | None:
    """The tour that explains a screen, if there is one."""
    return next((tour_id for tour_id, key in SCREENS.items() if key == screen_key), None)


def clamp(tour_id: str, index: int) -> int:
    """A step number inside the tour (0 for a tour that does not exist)."""
    total = TOURS.get(tour_id, 0)
    return max(0, min(index, total - 1)) if total else 0


def card(tour_id: str, index: int) -> dict:
    """What the card shows for a step; an empty dict for a tour that does not exist."""
    total = TOURS.get(tour_id, 0)
    if not total:
        return {}
    index = clamp(tour_id, index)
    prefix = f"TOUR_{tour_id.upper()}_{index}_"
    return {
        "id": tour_id,
        "index": index,
        "title": _(prefix + "T"),
        "body": _(prefix + "B"),
        "step": _("TOUR_STEP", current=index + 1, total=total),
        "canBack": index > 0,
        "last": index == total - 1,
        "backLabel": _("TOUR_BACK"),
        "nextLabel": _("TOUR_FINISH") if index == total - 1 else _("TOUR_NEXT"),
        "closeLabel": _("TOUR_CLOSE"),
        "neverLabel": _("TOUR_NEVER"),
        "keys": _("TOUR_KEYS"),
    }


def start_label(tour_id: str) -> str:
    return _("TOUR_START") if tour_id == "welcome" else _("TOUR_START_SCREEN")
