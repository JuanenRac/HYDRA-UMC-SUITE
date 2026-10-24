# =============================================================================
# HYDRA-UMC SUITE - tests/verify_server_security.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the access options of the Server Admin screen without any window: how the answer of the server is read
# (tolerant of a server that predates the options or only the Bluetooth service, of damaged values), when the
# screen asks before a change, what is sent, and the sentences about where a value comes from.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import server_security as sec

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


GOOD = {
    "port": 3000,
    "aiAccess": {"value": "admin", "source": "config"},
    "infoAuth": {"value": True, "source": "env"},
    "tls": {"enabled": True, "source": "config", "certPath": "/c.pem", "keyPath": "/k.pem", "fingerprint256": "AA:BB", "active": False, "appliesOnRestart": True},
    "ble": {"mode": {"value": "commands", "source": "config"}, "requireEncryption": {"value": False, "source": "env"}, "activeMode": "state", "appliesOnRestart": True},
}

state = sec.parse_state(GOOD)
check("reads the options of the server", (state["ai"], state["info"]["source"], state["tls"]["fingerprint"], state["ble"]["activeMode"]), ({"value": "admin", "source": "config"}, "env", "AA:BB", "state"))
check("nothing from a server that predates the options", (sec.parse_state({"port": 3000}), sec.parse_state(None), sec.parse_state([])), (None, None, None))
for label, body in (
    ("a value that is not offered", {**GOOD, "aiAccess": {"value": "everyone", "source": "config"}}),
    ("a source that does not exist", {**GOOD, "infoAuth": {"value": True, "source": "nowhere"}}),
    ("a text where a switch is", {**GOOD, "infoAuth": {"value": "yes", "source": "config"}}),
    ("a number where a text is", {**GOOD, "aiAccess": {"value": 1, "source": "config"}}),
    ("TLS without its switch", {**GOOD, "tls": {"source": "config"}}),
):
    check(f"damaged: {label} shows no section", sec.parse_state(body), None)
check("a server without the Bluetooth service keeps the other options", (sec.parse_state({k: v for k, v in GOOD.items() if k != "ble"})["ble"], sec.parse_state({k: v for k, v in GOOD.items() if k != "ble"})["ai"]["value"]), (None, "admin"))
check("a damaged Bluetooth part is dropped, not the rest", (sec.parse_state({**GOOD, "ble": {"mode": {"value": "all", "source": "config"}}})["ble"], sec.parse_state({**GOOD, "ble": 7})["tls"]["enabled"]), (None, True))
check("an unknown running Bluetooth mode is read as off", sec.parse_state({**GOOD, "ble": {**GOOD["ble"], "activeMode": "weird"}})["ble"]["activeMode"], "off")

check("only the environment locks a value", [sec.is_locked(s) for s in ("env", "config", "default")], [True, False, False])
check("turning the sign-in off asks, nothing else does", [sec.info_auth_needs_confirmation(a, b) for a, b in ((True, False), (True, True), (False, False), (False, True))], [True, False, False, False])
check("commands without an encrypted link ask", [sec.ble_needs_confirmation(m, e) for m, e in (("commands", False), ("commands", True), ("state", False), ("off", False))], [True, False, False, False])
check("TLS needs both paths and trims them", (sec.tls_patch(True, "", "/k"), sec.tls_patch(True, "/c", "  "), sec.tls_patch(True, " /c ", " /k "), sec.tls_patch(False, "", "")), (None, None, {"tls": {"enabled": True, "certPath": "/c", "keyPath": "/k"}}, {"tls": {"enabled": False, "certPath": "", "keyPath": ""}}))
check("the Bluetooth request", (sec.ble_patch("state", True), sec.ble_patch("nope", True)), ({"ble": {"mode": "state", "requireEncryption": True}}, None))
check("only the warnings of the screen are said", (sec.known_warning(["something_new"]), sec.known_warning("info_auth_off"), sec.known_warning(None)), ("", "", ""))
check("the sign-in warning", sec.known_warning(["info_auth_off"]), _("SECURITY_INFO_OFF_WARNING"))
check("the Bluetooth warning wins when both come", sec.known_warning(["info_auth_off", "ble_commands_unencrypted"]), _("SECURITY_BLE_UNENCRYPTED_WARNING"))

view = sec.view(state)
check("the view for the screen", (view["available"], view["aiValue"], view["aiLocked"], view["infoLocked"], view["tlsFingerprint"], view["bleMode"], view["bleEncryptionLocked"]), (True, "admin", False, True, "AA:BB", "commands", True))
check("the view says where a value comes from", (view["aiSource"], view["infoSource"]), (_("SECURITY_SOURCE_CONFIG"), _("SECURITY_SOURCE_ENV")))
check("the view says the running Bluetooth mode and that a restart is waiting", view["bleRunning"], _("SECURITY_BLE_RUNNING", mode=_("SECURITY_BLE_STATE")) + " " + _("SECURITY_RESTART_NOTE"))
check("TLS: not running yet, applies on restart", view["tlsStatus"], _("SECURITY_TLS_INACTIVE") + " " + _("SECURITY_RESTART_NOTE"))
empty = sec.view(None)
check("with nothing from the server the view has every key and shows nothing", (empty["available"], set(empty) == set(view)), (False, True))
check("the options of the selectors", ([o["value"] for o in sec.ai_options()], [o["value"] for o in sec.ble_mode_options()]), (["open", "admin"], ["off", "state", "commands"]))

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
