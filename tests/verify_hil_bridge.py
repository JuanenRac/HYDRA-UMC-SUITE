# =============================================================================
# HYDRA-UMC SUITE - tests/verify_hil_bridge.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the switch of the HIL bridge that requires a pass verdict of the twin: how the answer of the server is read,
# what a change sends (confirm in both directions), when the screen asks first, what the bridge would refuse, when the section is hidden, and
# the sentences.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import hil_bridge as hil

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


OFF = {"requireTwinPass": False, "locked": False, "persisted": True, "ready": True, "canChange": True}
settings = hil.parse_settings(OFF)
check("reads the switch", settings, {"require": False, "locked": False, "persisted": True, "ready": True, "canChange": True})
check("nothing from a damaged answer", (hil.parse_settings({"requireTwinPass": "yes"}), hil.parse_settings(None), hil.parse_settings([])), (None, None, None))
check("confirm in both directions", (hil.body_for(True), hil.body_for(False)), ({"requireTwinPass": True, "confirm": True}, {"requireTwinPass": False, "confirm": True}))
check("asks before any change", (hil.needs_confirmation(False, True), hil.needs_confirmation(True, False), hil.needs_confirmation(True, True)), (True, True, False))
check("knows what the bridge would refuse", (
    hil.blocked_reason(settings, True),
    hil.blocked_reason(dict(settings, ready=False), True),
    hil.blocked_reason(dict(settings, require=True, locked=True), False),
    hil.blocked_reason(dict(settings, canChange=False), True),
    hil.blocked_reason(dict(settings, ready=False), False),
), ("", "not_ready", "locked", "no_identity", ""))
check("hidden when there is no such bridge", (hil.hidden_for((404, {})), hil.hidden_for((503, {"available": False})), hil.hidden_for((200, OFF)), hil.hidden_for((403, {})), hil.hidden_for(None)), (True, True, False, False, False))
check("a refused account and a network failure have their own sentence", (hil.status_for((403, {})), hil.status_for(None), hil.status_for((200, OFF))), (_("HILBRIDGE_FORBIDDEN"), _("HILBRIDGE_LOAD_ERROR"), ""))
check("a refusal of the bridge shows its reason", hil.status_for((409, {"error": "locked"})), _("HILBRIDGE_SAVE_ERROR", reason="locked"))
view = hil.view(settings)
check("off by default in the view", (view["available"], view["require"], view["state"], view["kept"], view["locked"]), (True, False, _("HILBRIDGE_STATE_OFF"), _("HILBRIDGE_KEPT_FILE"), ""))
check("memory-only and locked are said", (hil.view(dict(settings, persisted=False))["kept"], hil.view(dict(settings, locked=True))["locked"]), (_("HILBRIDGE_KEPT_MEMORY"), _("HILBRIDGE_LOCKED")))
check("no view without the bridge", hil.view(None)["available"], False)
for key in ("TITLE", "DESC", "LABEL", "NOT_READY", "NO_IDENTITY", "SAVED", "CONFIRM_ON_TITLE", "CONFIRM_ON_MESSAGE", "CONFIRM_OFF_TITLE", "CONFIRM_OFF_MESSAGE"):
    check(f"sentence HILBRIDGE_{key} exists", _(f"HILBRIDGE_{key}") != f"HILBRIDGE_{key}", True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
