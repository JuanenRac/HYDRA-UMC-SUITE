# =============================================================================
# HYDRA-UMC SUITE - tests/verify_help_levels.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the Help by level: the three levels and "all", what each level shows, the search (case, accents, several words,
# a pasted text), the level kept in the configuration (an unknown value means all), that every guide has its question and its steps in all
# eight languages with the same placeholders, that the steps name only screens that exist in the navigation, and that the screen is in the
# navigation and drawn by the generic screen.
# =============================================================================
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import i18n
from hydra_suite import nav_items
from hydra_suite.i18n import _
from hydra_suite.panel_logic import help_levels as hl
from hydra_suite.panel_logic import setup_screens

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


ids = [t[0] for t in hl.TOPICS]
check("the guide ids are unique", len(ids), len(set(ids)))
check("every guide has a known level other than all", {t[1] for t in hl.TOPICS} <= set(hl.LEVELS) - {"all"}, True)
check("all three levels have guides", {t[1] for t in hl.TOPICS}, {"basic", "advanced", "technical"})
check("there are at least ten guides", len(hl.TOPICS) >= 10, True)
check("all shows every guide", [t["id"] for t in hl.matching_topics("all", "")], ids)
for level in ("basic", "advanced", "technical"):
    check(f"{level} shows only its guides", [t["id"] for t in hl.matching_topics(level, "")], [t[0] for t in hl.TOPICS if t[1] == level])
check("an unknown level means all", len(hl.matching_topics("expert", "")), len(ids))
check("the levels together are all the guides", sum(len(hl.matching_topics(level, "")) for level in ("basic", "advanced", "technical")), len(ids))

# search
check("a word finds the guide", [t["id"] for t in hl.matching_topics("all", "rotation")][:1], ["SECURITY"])
check("the search ignores case", hl.matching_topics("all", "ROTATION"), hl.matching_topics("all", "rotation"))
check("every word must match", [t["id"] for t in hl.matching_topics("all", "rotation overlap")], ["SECURITY"])
check("words that never meet match nothing", hl.matching_topics("all", "rotation qr"), [])
check("the search respects the level", hl.matching_topics("basic", "rotation"), [])
check("blank search shows everything", len(hl.matching_topics("all", "   ")), len(ids))
check("a search of nothing found is an empty list, not an error", hl.matching_topics("all", "zzzzqqqq"), [])
check("a pasted text is cut", len(hl.clean_search("x" * 500)), hl.MAX_SEARCH)
check("a search that is not text is empty", (hl.clean_search(None), hl.clean_search(7)), ("", ""))
check("accents and case are dropped", (hl.normalize("Überlappung ÁÉÍ"), hl.normalize("ACTUALIZAR")), ("uberlappung aei", "actualizar"))

# the level kept in the configuration
check("the level is read from the configuration", [hl.level_from_config({"help_level": lv}) for lv in hl.LEVELS], list(hl.LEVELS))
check("an unknown value in the configuration means all", [hl.level_from_config(c) for c in ({}, {"help_level": "expert"}, {"help_level": 3}, {"help_level": None}, None, [], "basic")], ["all"] * 7)
check("a level is kept under its own key", hl.config_update("basic"), {"help_level": "basic"})
check("an unknown level is kept as all", hl.config_update("expert"), {"help_level": "all"})

# the screen
base = setup_screens.empty_view("HELP_TITLE", "HELP_INTRO")
view = hl.view("basic", "", base)
check("the levels are the parts and the chosen one is selected", [(p["id"], p["selected"]) for p in view["parts"]], [("all", False), ("basic", True), ("advanced", False), ("technical", False)])
check("each guide is a check with a question and numbered steps", (view["checks"][0]["id"], view["checks"][0]["state"], view["checks"][0]["hint"].startswith("1. "), view["checks"][0]["hint"].count("\n")), ("VERSIONS", "info", True, 2))
check("the search box carries what was typed", hl.view("all", "rot ", base)["search"], {"placeholder": _("HELP_SEARCH"), "text": "rot "})
check("no match says so", (hl.view("all", "zzzzqqqq", base)["checks"], hl.view("all", "zzzzqqqq", base)["note"]), ([], _("HELP_NO_MATCH")))
check("the empty view is not changed", base["checks"], [])
check("the view keeps every part the generic screen draws", set(base) <= set(view), True)

# the steps name only screens that exist
names = hl.screen_names()
check("the names of the screens are the labels of the navigation", names["versions"], _("DOCK_SETUP_VERSIONS"))
labels = {label for label, _key in nav_items.SETUP_ITEMS}
check("every screen named by a step is a Setup entry or the server administration", {f"DOCK_SETUP_{k.upper()}" in labels for k in ("versions", "installation", "security", "remote", "notifications", "history")}, {True})
for topic_id, _level, steps in hl.TOPICS:
    question, lines = hl.topic_text(topic_id, steps)
    check(f"guide {topic_id} has its question and {steps} steps", (question != "HELP_" + topic_id + "_Q", len(lines)), (True, steps))
    check(f"guide {topic_id}: no step is left as a key or with a hole", [line for line in lines if line.startswith("HELP_") or re.search(r"\{\w+\}", line)], [])

check("the Help is in the navigation and drawn by the generic screen", ("setup_help" in {k for _l, k in nav_items.SETUP_ITEMS}, "setup_help" in setup_screens.SCREEN_KEYS), (True, True))

# the eight languages
KEYS = ["DOCK_SETUP_HELP", "HELP_TITLE", "HELP_INTRO", "HELP_SEARCH", "HELP_NO_MATCH"] + [f"HELP_LEVEL_{lv.upper()}" for lv in hl.LEVELS]
for topic_id, _level, steps in hl.TOPICS:
    KEYS += [f"HELP_{topic_id}_Q"] + [f"HELP_{topic_id}_S{n}" for n in range(1, steps + 1)]


def read(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, _sep, value = line.partition("=")
            values[key] = value
    return values


holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = read(Path("language/english.lng"))
for path in sorted(Path("language").glob("*.lng")):
    values = read(path)
    check(f"{path.name} has every sentence of the Help", [k for k in KEYS if not values.get(k, "").strip()], [])
    check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if holes(values.get(k, "")) != holes(english[k])], [])
    if path.name != "english.lng":
        untranslated = [k for k in KEYS if values[k] == english[k] and k not in ("HELP_LEVEL_ALL",)]
        check(f"{path.name} translates the Help (no sentence left in English)", [k for k in untranslated if len(english[k]) > 25], [])

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
