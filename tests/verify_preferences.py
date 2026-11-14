# =============================================================================
# HYDRA-UMC SUITE - tests/verify_preferences.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the Preferences: the scale of the interface (what is offered, what an unknown value in the configuration means,
# the size of a text at each scale), the level the Help opens at, how a choice of the screen is read, that the screen is in the navigation and
# drawn by the generic screen, that no text size of the interface is left outside the scale, and that every sentence exists in all eight
# languages.
# =============================================================================
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite import nav_items
from hydra_suite.i18n import _
from hydra_suite.panel_logic import help_levels
from hydra_suite.panel_logic import preferences as pf
from hydra_suite.panel_logic import setup_screens

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


check("the scales offered include the normal size and bigger ones", (100 in pf.SCALES, max(pf.SCALES) > 100, min(pf.SCALES) < 100, list(pf.SCALES) == sorted(pf.SCALES)), (True, True, True, True))
check("100 percent is the default", pf.DEFAULT_SCALE, 100)
check("a scale is read from the configuration", [pf.scale_from_config({"ui_scale": s}) for s in pf.SCALES], list(pf.SCALES))
check("an unknown value in the configuration means 100 percent", [pf.scale_from_config(c) for c in ({}, {"ui_scale": 90}, {"ui_scale": "115"}, {"ui_scale": 115.0}, {"ui_scale": True}, {"ui_scale": None}, {"ui_scale": -100}, None, [], "130")], [100] * 10)
check("a scale is kept under its own key", (pf.config_update_scale(130), pf.config_update_scale(77)), ({"ui_scale": 130}, {"ui_scale": 100}))
check("the factor of the normal size is one", pf.scale_factor(100), 1.0)
check("the factor of an unknown scale is one", (pf.scale_factor(90), pf.scale_factor(0), pf.scale_factor(-5)), (1.0, 1.0, 1.0))
check("a text size grows and shrinks with the scale", [pf.scaled(10, p) for p in pf.SCALES], [round(10 * p / 100) for p in pf.SCALES])
check("no text size ever goes below one pixel", all(pf.scaled(n, p) >= 1 for n in (0, 1, 2, 8) for p in pf.SCALES), True)
check("the normal scale leaves every size as it is", [pf.scaled(n, 100) for n in (8, 9, 10, 11, 12, 16, 20)], [8, 9, 10, 11, 12, 16, 20])

check("a choice of the screen is read", (pf.parse_choice("scale:115"), pf.parse_choice("level:basic"), pf.parse_choice("level:all")), (("scale", "115"), ("level", "basic"), ("level", "all")))
BAD = ["", "scale", "scale:", "scale:abc", "scale:90", "scale:-100", "scale:115:1", "level:expert", "other:1", ":1", "scale: 100", None, 5, [], "level:basic:x"]
check("anything else is not a choice", [pf.parse_choice(c) for c in BAD], [None] * len(BAD))

base = setup_screens.empty_view("PREFS_TITLE", "PREFS_INTRO")
view = pf.view(115, "basic", base)
check("the view has the scale group and the level group", [len(g["parts"]) for g in view["groups"]], [len(pf.SCALES), len(help_levels.LEVELS), 2])
check("the chosen scale and the chosen level are the selected ones", ([p["id"] for g in view["groups"] for p in g["parts"] if p["selected"]]), ["scale:115", "level:basic", "tours:off"])
check("each choice is a valid choice of the screen", all(pf.parse_choice(p["id"]) is not None for g in view["groups"] for p in g["parts"]), True)
check("an unknown scale or level is shown as the default", [p["id"] for g in pf.view(90, "expert", base)["groups"] for p in g["parts"] if p["selected"]], ["scale:100", "level:all", "tours:off"])
check("the note says there is no animation to reduce", view["note"], _("PREFS_NOTE"))
check("the empty view is not changed", base["groups"], [])
check("the view keeps every part the generic screen draws", set(base) <= set(view), True)

check("the Preferences are in the navigation and drawn by the generic screen", ("setup_preferences" in {k for _l, k in nav_items.SETUP_ITEMS}, "setup_preferences" in setup_screens.SCREEN_KEYS), (True, True))

# no text size of the interface is left outside the scale
qml = Path("assets/qml/Main.qml").read_text(encoding="utf-8")
check("every text size goes through the scale", re.findall(r"font\.pixelSize: (?!window\.fs\()[^\n]*", qml), [])
check("the scale is a property of the window, so a text is worked out again only when the scale changes", "readonly property real uiScale: suiteBackend.uiScaleFactor" in qml and "function fs(pixels)" in qml, True)

# the eight languages
KEYS = ["DOCK_SETUP_PREFERENCES", "PREFS_TITLE", "PREFS_INTRO", "PREFS_SCALE_TITLE", "PREFS_SCALE_HINT", "PREFS_LEVEL_TITLE", "PREFS_LEVEL_HINT", "PREFS_NOTE"]


def read(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, _sep, value = line.partition("=")
            values[key] = value
    return values


english = read(Path("language/english.lng"))
for path in sorted(Path("language").glob("*.lng")):
    values = read(path)
    check(f"{path.name} has every sentence of the Preferences", [k for k in KEYS if not values.get(k, "").strip()], [])
    if path.name != "english.lng":
        check(f"{path.name} translates the long sentences", [k for k in KEYS if values[k] == english[k] and len(english[k]) > 25], [])

# ---- the guided tours: the preference (off by default) and the cards
from hydra_suite.panel_logic import tours as tr

check("the tours are off unless the configuration says exactly true", [pf.tours_from_config(c) for c in ({}, {"tours": True}, {"tours": False}, {"tours": 1}, {"tours": "true"}, None, [])], [False, True, False, False, False, False, False])
check("the tours are kept under their own key", (pf.config_update_tours(True), pf.config_update_tours(False)), ({"tours": True}, {"tours": False}))
check("a choice of the tours is read", (pf.parse_choice("tours:on"), pf.parse_choice("tours:off"), pf.parse_choice("tours:maybe"), pf.parse_choice("tours:")), (("tours", "on"), ("tours", "off"), None, None))
tours_view = pf.view(100, "all", base, True)
check("the view says the tours are on", [p["id"] for g in tours_view["groups"] for p in g["parts"] if p["selected"]][-1], "tours:on")
check("the group of the tours has its own title and hint", (tours_view["groups"][2]["title"], tours_view["groups"][2]["hint"]), (_("PREFS_TOURS_TITLE"), _("PREFS_TOURS_HINT")))
check("every tour has a card for every step, with its own sentences", [(tid, i, tr.card(tid, i)["title"] != "", not tr.card(tid, i)["title"].startswith("TOUR_"), not tr.card(tid, i)["body"].startswith("TOUR_")) for tid, n in tr.TOURS.items() for i in range(n)],
      [(tid, i, True, True, True) for tid, n in tr.TOURS.items() for i in range(n)])
welcome = tr.card("welcome", 0)
check("the first card has no Back, the last one says Finish", (welcome["canBack"], welcome["last"], welcome["nextLabel"] == _("TOUR_NEXT"), tr.card("welcome", 4)["last"], tr.card("welcome", 4)["nextLabel"] == _("TOUR_FINISH")), (False, False, True, True, True))
check("the step is counted from one", (welcome["step"], tr.card("health", 1)["step"]), (_("TOUR_STEP", current=1, total=5), _("TOUR_STEP", current=2, total=2)))
check("a step outside the tour is the nearest one, and a tour that does not exist has no card", (tr.card("welcome", 99)["index"], tr.card("welcome", -3)["index"], tr.card("nope", 0)), (4, 0, {}))
check("the tour of a screen is found by its key", (tr.tour_for_screen("ecosystem_health"), tr.tour_for_screen("setup_help")), ("health", None))
check("the start entries have their own labels", (tr.start_label("welcome"), tr.start_label("health")), (_("TOUR_START"), _("TOUR_START_SCREEN")))
check("every sentence of the tours exists", all(_(k) != k for k in ["TOUR_START", "TOUR_START_SCREEN", "TOUR_CLOSE", "TOUR_BACK", "TOUR_NEXT", "TOUR_FINISH", "TOUR_NEVER", "TOUR_STEP", "TOUR_KEYS", "PREFS_TOURS_TITLE", "PREFS_TOURS_HINT"]), True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
