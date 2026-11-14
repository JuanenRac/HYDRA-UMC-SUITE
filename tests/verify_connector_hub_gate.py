# =============================================================================
# HYDRA-UMC SUITE - tests/verify_connector_hub_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the switch of the connector hub gate that answers a caller without identity: how the answer of the server
# is read, what a change sends (confirm only when turning it on), when the screen asks first, when the section is hidden, and the sentences.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import connector_hub_gate as gate

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


OFF = {"allowLoopbackNoIdentity": False, "loopbackSwitchAllowed": True, "verifiesTokens": True, "persisted": True}
settings = gate.parse_settings(OFF)
check("reads the switch", settings, {"allow": False, "loopbackAllowed": True, "verifiesTokens": True, "persisted": True})
check("nothing from a damaged answer", (gate.parse_settings({"allowLoopbackNoIdentity": "yes"}), gate.parse_settings(None), gate.parse_settings([])), (None, None, None))
check("confirm only when turning it on", (gate.body_for(True), gate.body_for(False)), ({"allowLoopbackNoIdentity": True, "confirm": True}, {"allowLoopbackNoIdentity": False}))
check("asks only before turning it on", (gate.needs_confirmation(False, True), gate.needs_confirmation(True, False), gate.needs_confirmation(False, False)), (True, False, False))
check("knows what the hub would refuse", (gate.change_allowed(dict(settings, loopbackAllowed=False), True), gate.change_allowed(dict(settings, allow=True, verifiesTokens=False), False), gate.change_allowed(settings, True)), (False, False, True))
check("hidden when there is no such gate", (gate.hidden_for((404, {})), gate.hidden_for((503, {"available": False})), gate.hidden_for((200, OFF)), gate.hidden_for((403, {})), gate.hidden_for(None)), (True, True, False, False, False))
check("a refused account and a network failure have their own sentence", (gate.status_for((403, {})), gate.status_for(None), gate.status_for((200, OFF))), (_("HUBGATE_FORBIDDEN"), _("HUBGATE_LOAD_ERROR"), ""))
check("a refusal of the hub shows its reason", gate.status_for((409, {"error": "no key"})), _("HUBGATE_SAVE_ERROR", reason="no key"))
view = gate.view(settings)
check("off by default in the view", (view["available"], view["allow"], view["state"], view["kept"]), (True, False, _("HUBGATE_STATE_OFF"), _("HUBGATE_KEPT_FILE")))
check("memory-only is said", gate.view(dict(settings, persisted=False))["kept"], _("HUBGATE_KEPT_MEMORY"))
check("no view without the gate, and no missing key", (gate.view(None)["available"], gate.view(None)["blockedOn"], gate.view(None)["state"]), (False, "", ""))
for key in ("HUBGATE_TITLE", "HUBGATE_DESC", "HUBGATE_LABEL", "HUBGATE_CONFIRM_TITLE", "HUBGATE_CONFIRM_MESSAGE", "COMMON_SAVED", "HUBGATE_LOOPBACK_ONLY", "HUBGATE_NEEDS_KEY"):
    check(f"sentence {key} exists", _(key) != key, True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
