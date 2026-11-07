# =============================================================================
# HYDRA-UMC SUITE - tests/verify_live_activity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the setting of the Live Activity on the lock screen in Server Admin: off by default with the level that shows only the state, how
# the answer of the server is read, no level above the maximum the server allows, what a change sends (the confirmation exactly when it shows more), a value fixed
# by the environment, a server that predates the setting, and that every sentence exists in all eight languages with the same placeholders.
# =============================================================================
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import live_activity as la

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def answer(enabled=False, level="status", src="default", level_src="default", maximum="full", push=True):
    return {"push": {"enabled": {"value": push, "source": "config"}, "liveActivity": {"enabled": {"value": enabled, "source": src}, "level": {"value": level, "source": level_src}, "maxLevel": maximum}}}


off = la.parse_state(answer())
check("off by default with the level that shows only the state", (off["enabled"], off["level"], off["max_level"], off["push_on"]), (False, "status", "full", True))
check("the levels are three and in order", la.LEVELS, ("status", "progress", "full"))
for label, body in {
    "a server that predates it": {}, "no push block": {"push": {}}, "no live block": {"push": {"enabled": {"value": True, "source": "config"}}}, "not an object": None,
    "a level that does not exist": answer(level="everything"), "an enabled flag that is not a boolean": answer(enabled="yes"), "an unknown source": answer(src="nowhere"),
}.items():
    check(f"nothing from {label}", la.parse_state(body), None)
check("a maximum that is not a level is the highest", la.parse_state(answer(maximum="weird"))["max_level"], "full")
check("push off is told", la.parse_state(answer(push=False))["push_on"], False)
check("a value fixed by the environment is locked", (la.parse_state(answer(src="env"))["enabled_locked"], la.parse_state(answer(level_src="env"))["level_locked"], off["enabled_locked"]), (True, True, False))

check("no level above the maximum the server allows", [la.allowed_levels(la.parse_state(answer(maximum=m))) for m in la.LEVELS], [["status"], ["status", "progress"], ["status", "progress", "full"]])
check("a change is only what differs", (la.change_for(off, False, "status"), la.change_for(off, True, "status"), la.change_for(off, False, "progress"), la.change_for(off, True, "full")), ({}, {"enabled": True}, {"level": "progress"}, {"enabled": True, "level": "full"}))
check("a level above the maximum is never sent", la.change_for(la.parse_state(answer(maximum="progress")), False, "full"), {})
check("a level that does not exist is never sent", la.change_for(off, False, "everything"), {})
check("a locked value is never sent", (la.change_for(la.parse_state(answer(src="env")), True, "status"), la.change_for(la.parse_state(answer(level_src="env")), False, "full")), ({}, {}))

on_full = la.parse_state(answer(enabled=True, level="full"))
check("the confirmation is for turning it on or raising the level", (la.needs_confirmation(off, {"enabled": True}), la.needs_confirmation(off, {"level": "progress"}), la.needs_confirmation(off, {"level": "full"})), (True, True, True))
check("lowering the level or turning it off never asks", (la.needs_confirmation(on_full, {"enabled": False}), la.needs_confirmation(on_full, {"level": "progress"}), la.needs_confirmation(on_full, {"level": "status"}), la.needs_confirmation(on_full, {})), (False, False, False, False))
check("the body carries only what changes and the confirmation when it is needed", (la.body_for(off, {"enabled": True, "level": "progress"}), la.body_for(on_full, {"level": "status"}), la.body_for(on_full, {"enabled": False})),
      ({"push": {"liveActivity": {"enabled": True, "level": "progress", "confirm": True}}}, {"push": {"liveActivity": {"level": "status"}}}, {"push": {"liveActivity": {"enabled": False}}}))
check("each result has its own sentence", (la.status_for(None), la.status_for((403, {})), la.status_for((401, {})), la.status_for((200, {})), la.status_for((400, {"error": "confirm is needed"})), la.status_for((500, {}))),
      (_("LIVEACT_LOAD_ERROR"), _("LIVEACT_FORBIDDEN"), _("LIVEACT_FORBIDDEN"), "", _("LIVEACT_SAVE_ERROR", reason="confirm is needed"), _("LIVEACT_LOAD_ERROR")))

view = la.view(off)
check("off by default in the view, one choice per allowed level and the saved one selected", (view["available"], view["enabled"], view["level"], [item["id"] for item in view["levels"]], [item["selected"] for item in view["levels"]]), (True, False, "status", ["status", "progress", "full"], [True, False, False]))
check("a wanted value shows as chosen and as a change to save", (la.view(off, True, "progress")["level"], la.view(off, True, "progress")["dirty"], view["dirty"]), ("progress", True, False))
check("push off and a locked value say so", (la.view(la.parse_state(answer(push=False)))["pushOffText"], la.view(la.parse_state(answer(src="env")))["lockedText"]), (_("LIVEACT_PUSH_OFF"), _("LIVEACT_LOCKED")))
none = la.view(None)
check("no view without the block, but every key is there for the screen to bind to", (none["available"], sorted(none) == sorted(view)), (False, True))

KEYS = ["TITLE", "DESC", "LABEL", "PUSH_OFF", "LEVEL_TITLE", "LEVEL_STATUS", "LEVEL_STATUS_HINT", "LEVEL_PROGRESS", "LEVEL_PROGRESS_HINT", "LEVEL_FULL", "LEVEL_FULL_HINT", "LOCK_SCREEN_NOTE",
        "LOCKED", "SAVED", "SAVE_ERROR", "FORBIDDEN", "LOAD_ERROR", "CONFIRM_TITLE", "CONFIRM_MESSAGE_STATUS", "CONFIRM_MESSAGE_PROGRESS", "CONFIRM_MESSAGE_FULL", "CONFIRM_BUTTON"]
for key in KEYS:
    check(f"sentence LIVEACT_{key} exists", _(f"LIVEACT_{key}") != f"LIVEACT_{key}", True)

holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = {}
for path in sorted(Path("language").glob("*.lng"), key=lambda p: (p.name != "english.lng", p.name)):
    text = path.read_text(encoding="utf-8")
    values = {}
    for key in KEYS:
        found = re.search(rf"^LIVEACT_{key}=(.*)$", text, re.M)
        values[key] = found.group(1).strip() if found else None
    check(f"{path.name} has every sentence", [k for k, v in values.items() if not v], [])
    if path.name == "english.lng":
        english = values
    else:
        check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if values[k] and holes(values[k]) != holes(english.get(k) or "")], [])
        check(f"{path.name} translates what the person confirms", [k for k in ("TITLE", "DESC", "CONFIRM_MESSAGE_FULL", "LOCK_SCREEN_NOTE", "LEVEL_FULL_HINT") if values[k] == english.get(k)], [])

# the screen is in Server Admin and the levels are not hard-coded there
qml = Path("assets/qml/Main.qml").read_text(encoding="utf-8")
check("the screen has the switch, a choice per level and a save that asks first", all(token in qml for token in ('objectName: "liveActivityPanel"', 'objectName: "liveActivityBox"', '"liveActivityLevel_"', "liveActivityNeedsConfirmation", "saveLiveActivity")), True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
