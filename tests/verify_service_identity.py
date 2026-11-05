# =============================================================================
# HYDRA-UMC SUITE - tests/verify_service_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the section "Identity of the services" of Server Admin: how the answer of the server is read, what a change
# sends (confirm only when turning it on), when the screen asks first, when the section is hidden, who is shown as taking the identity,
# and that every sentence exists in all eight languages.
# =============================================================================
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import service_identity as si

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


OFF = {
    "enabled": False, "source": "default", "locked": False, "key": "usable", "state": "off",
    "services": [
        {"name": "datalake", "support": "accepts"}, {"name": "twin", "support": "accepts"},
        {"name": "connector-hub", "support": "own_verifier"}, {"name": "voice-ui", "support": "not_yet"},
        {"name": "odd", "support": "weird"}, {"support": "accepts"},
    ],
    "order": ["server_first"],
}
status = si.parse_status(OFF)
check("reads the state and drops what it does not know", (status["enabled"], status["state"], [s["name"] for s in status["services"]]), (False, "off", ["datalake", "twin", "connector-hub", "voice-ui"]))
check("nothing from a damaged answer", (si.parse_status({"enabled": "yes"}), si.parse_status(None), si.parse_status([]), si.parse_status(dict(OFF, state="weird"))), (None, None, None, None))
check("confirm only when turning it on", (si.body_for(True), si.body_for(False)), ({"auth": {"serviceIdentity": {"enabled": True, "confirm": True}}}, {"auth": {"serviceIdentity": {"enabled": False}}}))
check("asks only before turning it on", (si.needs_confirmation(False, True), si.needs_confirmation(True, False), si.needs_confirmation(False, False)), (True, False, False))
check("a locked switch offers no change", (si.change_allowed(status, True), si.change_allowed(dict(status, locked=True), True), si.change_allowed(dict(status, locked=True), False)), (True, False, True))
check("hidden only when the server has no such route", (si.hidden_for((404, {})), si.hidden_for((200, OFF)), si.hidden_for((403, {})), si.hidden_for(None)), (True, False, False, False))
check("a refused account and a network failure have their own sentence", (si.status_for((403, {})), si.status_for(None), si.status_for((200, OFF)), si.status_for((200, {"success": True}))), (_("SERVICEID_FORBIDDEN"), _("SERVICEID_LOAD_ERROR"), "", ""))
check("a refusal of the server shows its reason", si.status_for((409, {"error": "locked"})), _("SERVICEID_SAVE_ERROR", reason="locked"))
view = si.view(status)
check("off by default in the view", (view["available"], view["enabled"], view["state"]), (True, False, _("SERVICEID_STATE_OFF")))
check("the services are listed by how they take the identity", (view["accepts"].endswith("(2): datalake, twin"), "connector-hub" in view["ownVerifier"], "voice-ui" in view["notYet"]), (True, True, True))
check("a level with no service says none", si.view(si.parse_status(dict(OFF, services=[])))["accepts"].endswith(_("SERVICEID_NONE")), True)
check("the three states have their own sentence", len({si.view(si.parse_status(dict(OFF, state=s, enabled=s != "off")))["state"] for s in si.STATES}), 3)
check("a locked switch says why", si.view(dict(status, locked=True))["lockedText"], _("SERVICEID_LOCKED"))
check("no view without the route", si.view(None), {"available": False})

KEYS = [
    "TITLE", "DESC", "LABEL", "STATE_PRESENTING", "STATE_OFF", "STATE_IDLE_NO_KEY", "LOCKED", "SERVICES_TITLE", "ACCEPTS", "OWN_VERIFIER", "NOT_YET", "NONE",
    "ORDER_TITLE", "ORDER_1", "ORDER_2", "ORDER_3", "SAVED", "SAVE_ERROR", "UNSUPPORTED", "FORBIDDEN", "LOAD_ERROR", "OFF_WARNING", "CONFIRM_TITLE", "CONFIRM_MESSAGE",
]
for key in KEYS:
    check(f"sentence SERVICEID_{key} exists", _(f"SERVICEID_{key}") != f"SERVICEID_{key}", True)

for path in sorted(Path("language").glob("*.lng")):
    text = path.read_text(encoding="utf-8")
    missing = [key for key in KEYS if f"\nSERVICEID_{key}=" not in text]
    check(f"{path.name} has every sentence", missing, [])

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
