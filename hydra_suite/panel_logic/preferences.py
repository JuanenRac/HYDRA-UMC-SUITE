# =============================================================================
# HYDRA-UMC SUITE - panel_logic/preferences.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Preferences screen, without any window toolkit: the scale of the interface and the level the Help opens at, the same two personal
# preferences as the Preferences tab of HYDRA-UMC STUDIO that this program can honour. Both are kept in the configuration file of the program
# (never sent to a server) and applied at once. The scale multiplies every text size of the interface; an unknown value in the configuration
# means 100 %. The third preference of Studio, reduced animations, is not offered here because this interface has no animation to reduce.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _
from hydra_suite.panel_logic import help_levels

#: The scales offered, in percent of the normal size.
SCALES = (85, 100, 115, 130, 150)
DEFAULT_SCALE = 100
CONFIG_KEY = "ui_scale"
TOURS_KEY = "tours"


def tours_from_config(config: object) -> bool:
    """Whether the guided tours are offered (the preference "Offer the guided tours"): off unless the configuration says exactly true."""
    return isinstance(config, dict) and config.get(TOURS_KEY) is True


def config_update_tours(on: bool) -> dict:
    return {TOURS_KEY: bool(on)}


def scale_from_config(config: object) -> int:
    """The scale kept in the configuration (whole percent from the list); anything else means 100 %."""
    value = config.get(CONFIG_KEY) if isinstance(config, dict) else None
    return value if type(value) is int and value in SCALES else DEFAULT_SCALE


def scale_factor(percent: int) -> float:
    """The factor the text sizes are multiplied by."""
    return (percent if percent in SCALES else DEFAULT_SCALE) / 100.0


def scaled(pixels: int, percent: int) -> int:
    """A text size at a scale, never below 1 pixel."""
    return max(1, round(pixels * scale_factor(percent)))


def config_update_scale(percent: int) -> dict:
    return {CONFIG_KEY: percent if percent in SCALES else DEFAULT_SCALE}


def parse_choice(choice: object) -> tuple[str, str] | None:
    """A choice of the screen is "scale:115" or "level:basic"; anything else is not a choice."""
    if not isinstance(choice, str) or choice.count(":") != 1:
        return None
    group, _sep, value = choice.partition(":")
    if group == "scale" and value.isdigit() and int(value) in SCALES:
        return group, value
    if group == "level" and value in help_levels.LEVELS:
        return group, value
    if group == "tours" and value in ("on", "off"):
        return group, value
    return None


def view(percent: int, level: str, empty_view: dict, tours_on: bool = False) -> dict:
    """What the screen shows."""
    percent = percent if percent in SCALES else DEFAULT_SCALE
    level = level if level in help_levels.LEVELS else "all"
    result = dict(empty_view)
    result["groups"] = [
        {
            "title": _("PREFS_SCALE_TITLE"),
            "hint": _("PREFS_SCALE_HINT"),
            "parts": [{"id": f"scale:{item}", "label": f"{item} %", "selected": item == percent} for item in SCALES],
        },
        {
            "title": _("PREFS_LEVEL_TITLE"),
            "hint": _("PREFS_LEVEL_HINT"),
            "parts": [{"id": f"level:{item}", "label": _("HELP_LEVEL_" + item.upper()), "selected": item == level} for item in help_levels.LEVELS],
        },
        {
            "title": _("PREFS_TOURS_TITLE"),
            "hint": _("PREFS_TOURS_HINT"),
            "parts": [{"id": "tours:on", "label": _("COMMON_YES"), "selected": tours_on}, {"id": "tours:off", "label": _("COMMON_NO"), "selected": not tours_on}],
        },
    ]
    result["note"] = _("PREFS_NOTE")
    return result
