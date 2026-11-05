# =============================================================================
# HYDRA-UMC SUITE - tests/verify_planner_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the switch of the semantic planner that makes the approval of a plan the act of a signed-in person: how the
# answer of the server is read, what a change sends (confirm only when relaxing it), when the screen asks first, when the section is hidden,
# and the sentences.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import planner_identity as planner

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


ON = {"requireIdentity": True, "verifiesTokens": True, "persisted": True}
settings = planner.parse_settings(ON)
check("reads the switch", settings, {"require": True, "verifiesTokens": True, "persisted": True})
check("nothing from a damaged answer", (planner.parse_settings({"requireIdentity": "yes"}), planner.parse_settings(None), planner.parse_settings([])), (None, None, None))
check("confirm only when relaxing it", (planner.body_for(False), planner.body_for(True)), ({"requireIdentity": False, "confirm": True}, {"requireIdentity": True}))
check("asks only before relaxing it", (planner.needs_confirmation(True, False), planner.needs_confirmation(False, True), planner.needs_confirmation(True, True)), (True, False, False))
check("knows what the planner would refuse", (planner.change_allowed(dict(settings, verifiesTokens=False), False), planner.change_allowed(dict(settings, verifiesTokens=False), True), planner.change_allowed(settings, False)), (False, True, True))
check("hidden when there is no such planner", (planner.hidden_for((404, {})), planner.hidden_for((503, {"available": False})), planner.hidden_for((200, ON)), planner.hidden_for((403, {})), planner.hidden_for(None)), (True, True, False, False, False))
check("a refused account and a network failure have their own sentence", (planner.status_for((403, {})), planner.status_for(None), planner.status_for((200, ON))), (_("PLANNERID_FORBIDDEN"), _("PLANNERID_LOAD_ERROR"), ""))
check("a refusal of the planner shows its reason", planner.status_for((409, {"error": "no file"})), _("PLANNERID_SAVE_ERROR", reason="no file"))
view = planner.view(settings)
check("on by default in the view", (view["available"], view["require"], view["state"], view["kept"]), (True, True, _("PLANNERID_STATE_ON"), _("PLANNERID_KEPT_FILE")))
check("memory-only is said", planner.view(dict(settings, persisted=False))["kept"], _("PLANNERID_KEPT_MEMORY"))
check("no view without the planner", planner.view(None), {"available": False})
for key in ("PLANNERID_TITLE", "PLANNERID_DESC", "PLANNERID_LABEL", "PLANNERID_CONFIRM_TITLE", "PLANNERID_CONFIRM_MESSAGE", "PLANNERID_SAVED", "PLANNERID_NEEDS_KEY"):
    check(f"sentence {key} exists", _(key) != key, True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
