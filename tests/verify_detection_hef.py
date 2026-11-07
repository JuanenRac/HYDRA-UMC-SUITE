# =============================================================================
# HYDRA-UMC SUITE - tests/verify_detection_hef.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the switch of the loaded-model reports of the DETECTION-HEF service in Server Admin: it is off by default, how
# the answer of the server is read, what a change sends (confirm only when turning it on), when the screen asks first, a switch fixed by the
# environment, a server that predates the setting, and that every sentence exists in all eight languages with the same placeholders.
# =============================================================================
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import detection_hef as dh

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def answer(value, source="default"):
    return {"detectionHef": {"acceptLoadedReports": {"value": value, "source": source}}}


check("reads the switch off by default", dh.parse_state(answer(False)), {"enabled": False, "locked": False})
check("reads the switch on from the configuration", dh.parse_state(answer(True, "config")), {"enabled": True, "locked": False})
check("a switch fixed by the environment is locked", dh.parse_state(answer(True, "env")), {"enabled": True, "locked": True})
for label, body in {
    "a server that predates the block": {}, "an empty block": {"detectionHef": {}}, "a block that is a list": {"detectionHef": []},
    "a value that is not a boolean": answer("yes"), "a value that is a number": answer(1), "an unknown source": answer(True, "nowhere"), "not an object": None,
}.items():
    check(f"nothing from {label}", dh.parse_state(body), None)
check("confirm only when turning it on", (dh.body_for(True), dh.body_for(False)), ({"detectionHef": {"acceptLoadedReports": True, "confirm": True}}, {"detectionHef": {"acceptLoadedReports": False}}))
check("asks only before turning it on", [dh.needs_confirmation(c, w) for c, w in ((False, True), (True, True), (True, False), (False, False))], [True, False, False, False])
locked = dh.parse_state(answer(True, "env"))
free = dh.parse_state(answer(False))
check("a locked switch offers no change", (dh.change_allowed(locked, False), dh.change_allowed(locked, True), dh.change_allowed(free, True)), (False, True, True))
check("each result has its own sentence", (dh.status_for(None), dh.status_for((403, {})), dh.status_for((401, {})), dh.status_for((200, {"success": True})), dh.status_for((400, {"error": "confirm is needed"})), dh.status_for((500, {}))),
      (_("DETHEF_LOAD_ERROR"), _("DETHEF_FORBIDDEN"), _("DETHEF_FORBIDDEN"), "", _("DETHEF_SAVE_ERROR", reason="confirm is needed"), _("DETHEF_LOAD_ERROR")))
check("the reason of a refusal is cut at 300 characters", len(dh.status_for((409, {"error": "x" * 400}))) - len(_("DETHEF_SAVE_ERROR", reason="")), 300)

view = dh.view(free)
check("off by default in the view", (view["available"], view["enabled"], view["locked"], view["lockedText"]), (True, False, False, ""))
check("a locked switch says why", dh.view(locked)["lockedText"], _("DETHEF_LOCKED"))
none = dh.view(None)
check("no view without the block, but every key is there for the screen to bind to", (none["available"], sorted(none) == sorted(view)), (False, True))

KEYS = ["TITLE", "DESC", "LABEL", "HINT", "LOCKED", "SAVED", "SAVE_ERROR", "FORBIDDEN", "LOAD_ERROR", "CONFIRM_TITLE", "CONFIRM_MESSAGE", "CONFIRM_BUTTON"]
for key in KEYS:
    check(f"sentence DETHEF_{key} exists", _(f"DETHEF_{key}") != f"DETHEF_{key}", True)

holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = {}
for path in sorted(Path("language").glob("*.lng"), key=lambda p: (p.name != "english.lng", p.name)):
    text = path.read_text(encoding="utf-8")
    values = {}
    for key in KEYS:
        found = re.search(rf"^DETHEF_{key}=(.*)$", text, re.M)
        values[key] = found.group(1).strip() if found else None
    check(f"{path.name} has every sentence", [k for k, v in values.items() if not v], [])
    if path.name == "english.lng":
        english = values
    else:
        check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if values[k] and holes(values[k]) != holes(english.get(k) or "")], [])
        check(f"{path.name} translates the confirmation", [k for k in ("CONFIRM_TITLE", "CONFIRM_MESSAGE", "DESC") if values[k] == english.get(k)], [])

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
