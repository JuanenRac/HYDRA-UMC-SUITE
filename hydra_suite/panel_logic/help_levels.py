# =============================================================================
# HYDRA-UMC SUITE - panel_logic/help_levels.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Help by level, without any window toolkit: step-by-step guides for the Setup screens and the administration of the server, in three
# levels (basic, advanced, technical) like the Help of HYDRA-UMC STUDIO, with a search box. The texts live in the language files
# (HELP_<ID>_Q for the question and HELP_<ID>_S1..Sn for the steps); the names of the screens inside the steps come from the navigation, so
# a guide never names a menu entry that is called something else. The level a person chooses is kept in the configuration file of the
# program, and an unknown value there means "all levels". Every view is a plain dict that the one generic screen of the interface draws.
# =============================================================================
from __future__ import annotations

import unicodedata

from hydra_suite.i18n import _

LEVELS = ("all", "basic", "advanced", "technical")
CONFIG_KEY = "help_level"
MAX_SEARCH = 80

#: The guides: (id, level, number of steps). The question and the steps are in the language files.
TOPICS: tuple[tuple[str, str, int], ...] = (
    ("VERSIONS", "basic", 3),
    ("CHECKLIST", "basic", 3),
    ("REMOTE", "basic", 3),
    ("HISTORY", "basic", 3),
    ("SECURITY", "advanced", 3),
    ("PUSH", "advanced", 3),
    ("TOOLARMS", "advanced", 3),
    ("IDENTITY", "technical", 3),
    ("DETECTIONHEF", "technical", 3),
    ("UNKNOWN", "technical", 3),
)


def level_from_config(config: object) -> str:
    """The level kept in the configuration; anything that is not one of the levels means all of them."""
    value = config.get(CONFIG_KEY) if isinstance(config, dict) else None
    return value if isinstance(value, str) and value in LEVELS else "all"


def config_update(level: str) -> dict:
    """What to merge into the configuration to keep a level; None is never written (an unknown level is turned into all)."""
    return {CONFIG_KEY: level if level in LEVELS else "all"}


def clean_search(text: object) -> str:
    """The words typed in the search box, cut so a pasted text cannot grow without end (spaces are kept: the box shows what was typed)."""
    return text[:MAX_SEARCH] if isinstance(text, str) else ""


def normalize(text: str) -> str:
    """Lower case without accents, so "Actualizar" is found by "actualizar" and "Überlappung" by "uberlappung"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def screen_names() -> dict[str, str]:
    """The names of the screens the steps mention, in the language of the interface."""
    return {
        "eco": _("NAV_SECTION_ECOSYSTEM"),
        "versions": _("DOCK_SETUP_VERSIONS"),
        "installation": _("DOCK_SETUP_INSTALLATION"),
        "security": _("DOCK_SETUP_SECURITY"),
        "remote": _("DOCK_SETUP_REMOTE"),
        "notifications": _("DOCK_SETUP_NOTIFICATIONS"),
        "history": _("DOCK_SETUP_HISTORY"),
        "admin": _("DOCK_ADMIN_SERVER"),
    }


def topic_text(topic_id: str, steps: int) -> tuple[str, list[str]]:
    """The question and the steps of a guide in the language of the interface."""
    names = screen_names()
    question = _("HELP_" + topic_id + "_Q")
    return question, [_("HELP_" + topic_id + f"_S{n}", **names) for n in range(1, steps + 1)]


def matching_topics(level: str, search: str) -> list[dict]:
    """The guides of a level (all of them for "all") whose question or steps contain every word of the search."""
    level = level if level in LEVELS else "all"
    words = [normalize(word) for word in clean_search(search).split()]
    found = []
    for topic_id, topic_level, steps in TOPICS:
        if level != "all" and topic_level != level:
            continue
        question, lines = topic_text(topic_id, steps)
        haystack = normalize(question + " " + " ".join(lines))
        if all(word in haystack for word in words):
            found.append({"id": topic_id, "level": topic_level, "question": question, "steps": lines})
    return found


def view(level: str, search: str, empty_view: dict) -> dict:
    """What the screen shows; `empty_view` is the generic view with every part the screen can draw."""
    level = level if level in LEVELS else "all"
    shown = matching_topics(level, search)
    result = dict(empty_view)
    result["parts"] = [{"id": item, "label": _("HELP_LEVEL_" + item.upper()), "selected": item == level} for item in LEVELS]
    result["search"] = {"placeholder": _("HELP_SEARCH"), "text": clean_search(search)}
    result["checks"] = [
        {
            "id": topic["id"],
            "state": "info",
            "label": f"{topic['question']}  [{_('HELP_LEVEL_' + topic['level'].upper())}]",
            "hint": "\n".join(f"{n}. {line}" for n, line in enumerate(topic["steps"], 1)),
        }
        for topic in shown
    ]
    if not shown:
        result["note"] = _("HELP_NO_MATCH")
    return result
