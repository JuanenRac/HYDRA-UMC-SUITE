# =============================================================================
# HYDRA-UMC SUITE - tests/verify_catalogs_and_tool_tables.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the plain tables the panels read: the robot catalog (every model has a maker and a degree-of-freedom count that
# the name states), the tool list and its categories, the panel grids, the status words and the AI families. A table
# that drifts (a tool with no category, a status without a sentence in one of the eight languages) is found here.
# =============================================================================
import re
import sys

sys.path.insert(0, ".")

from hydra_suite import i18n
from hydra_suite.panel_logic import ai_family_status, atc_tools, server_browser, tester
from hydra_suite.robot_catalog import REAL_ROBOT_MODELS, ROBOT_MANUFACTURERS, robot_model_dof

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


LANGUAGES = [name for name, _label in i18n.AVAILABLE_LANGUAGES]

# --- the robot catalog -------------------------------------------------------------------------------
check("the model list is the catalog keys in order", REAL_ROBOT_MODELS, list(ROBOT_MANUFACTURERS))
check("no model is listed twice", len(set(REAL_ROBOT_MODELS)), len(REAL_ROBOT_MODELS))
check("every model has a maker", [m for m, maker in ROBOT_MANUFACTURERS.items() if not maker.strip()], [])
check("every model names its degrees of freedom", [m for m in REAL_ROBOT_MODELS if not re.search(r"\(\d+-DOF\)$", m)], [])
check("the count is read from the name", [robot_model_dof(m) for m in ("AR4 (6-DOF)", "SO-ARM100 (5-DOF)", "Koch v1.1 (5-DOF)")], [6, 5, 5])
check("a model without a count is a six-axis arm", (robot_model_dof("Mystery"), robot_model_dof("")), (6, 6))
check("a count is only read inside the brackets", robot_model_dof("7-DOF arm (4-DOF)"), 4)
check("every count is a believable number of joints", sorted({robot_model_dof(m) for m in REAL_ROBOT_MODELS}), [5, 6])

# --- the tool list -----------------------------------------------------------------------------------
tools = atc_tools.URTC_TOOLS
check("the first tool is the empty one", tools[0], "None")
check("no tool is listed twice", len(set(tools)), len(tools))
check("every category belongs to a listed tool", [t for t in tester._TOOL_CATEGORY if t not in tools], [])
check("the categories are the four the panel knows", sorted(set(tester._TOOL_CATEGORY.values())), ["binary", "motor", "thermal", "vacuum"])
check("an unlisted tool is generic", (tester._category_for("Soldering Station (T12)"), tester._category_for("Gimbal Gripper"), tester._category_for("nothing")), ("thermal", "generic", "generic"))
check("a vacuum head is a vacuum tool", [t for t in tools if "vacuum" in t.lower() and tester._category_for(t) != "vacuum"], [])
check("a heater is a thermal tool", [t for t in tools if re.search(r"hotend|soldering|hot air", t, re.I) and tester._category_for(t) != "thermal"], [])

# --- the panel grids and the default position -------------------------------------------------------------
grids = atc_tools.PANEL_GRIDS
check("every grid is columns x rows", [g for g in grids if not re.fullmatch(r"[1-9]x[1-9]", g)], [])
check("no grid is listed twice", len(set(grids)), len(grids))
check("the default grid is one of them", atc_tools._default_atc_config()["panelGrid"] in grids, True)
config = atc_tools._default_atc_config()
check("the default tool changer", (config["type"], config["revolverSlots"], config["tools"]), ("vertical_panel", 8, []))
check("each call gives a new tool list", atc_tools._default_atc_config()["tools"] is config["tools"], False)
position = atc_tools._default_pos()
check("the default position has a field per joint and per table axis", sorted(position), sorted(atc_tools.JOINT_FIELDS + atc_tools.TABLE_FIELDS))
check("the default position is the origin", set(position.values()), {0.0})
check("the ranges are ordered and centred", (atc_tools.JOINT_RANGE_DEG[0] < 0 < atc_tools.JOINT_RANGE_DEG[1], atc_tools.TABLE_RANGE_MM[0] < 0 < atc_tools.TABLE_RANGE_MM[1]), (True, True))

# --- the status words ---------------------------------------------------------------------------------------
check("the five states are the ones the link can be in", sorted(server_browser.STATUS_DISPLAY_KEYS), ["connected", "connecting", "disconnected", "error", "login_failed"])
check("a failed sign-in is not the generic error", server_browser.STATUS_DISPLAY_KEYS["login_failed"] != server_browser.STATUS_DISPLAY_KEYS["error"], True)
for language in LANGUAGES:
    words = i18n.load_language(language)
    check(f"{language}: every status has a sentence", [k for k in server_browser.STATUS_DISPLAY_KEYS.values() if not words.get(k, "").strip()], [])

# --- the AI families -------------------------------------------------------------------------------------------
families = ai_family_status.AI_FAMILIES
check("two AI families", [f[1] for f in families], ["hailo8", "hailo10"])
check("each family has a name, an id and a chip", [f for f in families if len(f) != 3 or not all(f)], [])

print("CATALOGS_AND_TOOL_TABLES=" + ("PASS" if failures == 0 else f"FAIL {failures}"))
sys.exit(1 if failures else 0)
