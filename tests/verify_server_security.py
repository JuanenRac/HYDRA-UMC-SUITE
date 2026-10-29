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

# --- the MQTT bridge options
check("the MQTT request carries no password and trims", sec.mqtt_patch("state", " mqtts://b:8883 ", " plant/a ", " u ", ""), {"mqtt": {"mode": "state", "url": "mqtts://b:8883", "prefix": "plant/a", "username": "u", "commandUser": ""}})
check("the MQTT request is refused for commands without an account, a bad address or an unknown mode", (sec.mqtt_patch("commands", "mqtt://b", "", "", ""), sec.mqtt_patch("state", "http://b", "", "", ""), sec.mqtt_patch("nope", "", "", "", ""), sec.mqtt_patch("commands", "mqtt://b", "", "", "bridge") is not None), (None, None, None, True))
check("turning commands on asks, nothing else does", [sec.mqtt_needs_confirmation(a, b) for a, b in (("off", "commands"), ("state", "commands"), ("commands", "commands"), ("commands", "off"))], [True, True, False, False])
check("the MQTT warning", sec.known_warning(["mqtt_commands_on"]), _("SECURITY_MQTT_COMMANDS_WARNING"))
check("the MQTT modes", [o["value"] for o in sec.mqtt_mode_options()], ["off", "state", "commands"])
raw = {"aiAccess": {"value": "open", "source": "default"}, "infoAuth": {"value": False, "source": "default"}, "tls": {"enabled": False, "source": "default", "active": False}}
check("a server without the bridge shows no MQTT section", sec.view(sec.parse_state(raw))["mqttAvailable"], False)
with_mqtt = sec.view(sec.parse_state({**raw, "mqtt": {"mode": {"value": "state", "source": "config"}, "url": "mqtt://b:1883", "prefix": "hydra/swarm", "username": "u", "commandUser": "", "activeMode": "off", "appliesOnRestart": True}}))
check("the MQTT view", (with_mqtt["mqttAvailable"], with_mqtt["mqttMode"], with_mqtt["mqttUrl"], with_mqtt["mqttRunning"]), (True, "state", "mqtt://b:1883", _("SECURITY_MQTT_RUNNING", mode=_("SECURITY_MQTT_OFF")) + " " + _("SECURITY_RESTART_NOTE")))
check("a damaged MQTT section is ignored", sec.view(sec.parse_state({**raw, "mqtt": {"mode": {"value": "banana", "source": "config"}}}))["mqttAvailable"], False)

# --- the voice and MAVLink signing options
VOICE_MAV = {
    **raw,
    "voice": {"includeHeardText": {"value": False, "source": "default"}, "minConfidence": {"value": 0.6, "source": "env"}},
    "mavlink": {"signingKeyFile": {"value": "/etc/uav.key", "source": "config"}, "signingAllowUnsigned": {"value": False, "source": "default"}, "signing": True, "appliesOnRestart": True},
}
vm = sec.parse_state(VOICE_MAV)
check("reads the voice and MAVLink sections", (vm["voice"]["confidence"], vm["mavlink"]["key"]["value"]), ({"value": 0.6, "source": "env"}, "/etc/uav.key"))
plain = sec.parse_state(raw)
check("a server without them shows no section", (plain["voice"], plain["mavlink"], sec.view(plain)["voiceAvailable"], sec.view(plain)["mavlinkAvailable"]), (None, None, False, False))
for label, body in (
    ("a confidence above 1", {**VOICE_MAV, "voice": {**VOICE_MAV["voice"], "minConfidence": {"value": 3, "source": "env"}}}),
    ("a switch as the confidence", {**VOICE_MAV, "voice": {**VOICE_MAV["voice"], "minConfidence": {"value": True, "source": "env"}}}),
    ("a text as the heard-text switch", {**VOICE_MAV, "voice": {**VOICE_MAV["voice"], "includeHeardText": {"value": "yes", "source": "env"}}}),
):
    check(f"damaged voice part ({label}) is dropped, not the rest", (sec.parse_state(body)["voice"], sec.parse_state(body)["tls"]["enabled"]), (None, False))
check("a number as the key file drops the MAVLink part", sec.parse_state({**VOICE_MAV, "mavlink": {**VOICE_MAV["mavlink"], "signingKeyFile": {"value": 5, "source": "config"}}})["mavlink"], None)
vv = sec.view(vm)
check("the voice view", (vv["voiceAvailable"], vv["voiceHeard"], vv["voiceConfidence"], vv["voiceConfidenceLocked"], vv["voiceHeardLocked"]), (True, False, "0.6", True, False))
check("the MAVLink view", (vv["mavlinkAvailable"], vv["mavlinkKey"], vv["mavlinkUnsigned"], vv["mavlinkStatus"]), (True, "/etc/uav.key", False, _("SECURITY_MAVLINK_SIGNING_ON") + " " + _("SECURITY_RESTART_NOTE")))
check("the key file is not shown as signing when empty", sec.view(sec.parse_state({**VOICE_MAV, "mavlink": {**VOICE_MAV["mavlink"], "signingKeyFile": {"value": "", "source": "default"}, "appliesOnRestart": False}}))["mavlinkStatus"], _("SECURITY_MAVLINK_SIGNING_OFF"))
check("every key of the view exists without a server", set(sec.view(None)) == set(vv), True)
check("what is typed as a confidence", [sec.parse_confidence(t) for t in ("0.8", " 0,75 ", "0", "1", "", "1.1", "-0.1", "abc", "0.5.5", "1e-1", "60%")], [0.8, 0.75, 0.0, 1.0, None, None, None, None, None, None, None])
check("the voice request", (sec.voice_patch(True, "0,9"), sec.voice_patch(False, ""), sec.voice_patch(False, "2")), ({"voice": {"includeHeardText": True, "minConfidence": 0.9}}, None, None))
check("lowering the voice protection asks, nothing else does", [sec.voice_needs_confirmation(h, c, sec.voice_patch(nh, nc)) for h, c, nh, nc in ((False, 0.6, True, "0.6"), (False, 0.6, False, "0"), (False, 0.6, False, "0.2"), (False, 0.6, False, "0.95"), (True, 0.0, True, "0"))], [True, True, False, False, False])
check("the MAVLink request carries only the path of the key file", sec.mavlink_patch("  /etc/uav.key ", False), {"mavlink": {"signingKeyFile": "/etc/uav.key", "signingAllowUnsigned": False}})
check("leaving the vehicle link open asks, nothing else does", [sec.mavlink_needs_confirmation(s, u, sec.mavlink_patch(k, nu)) for s, u, k, nu in ((True, False, "", False), (True, False, "/k", True), (True, False, "/other", False), (False, False, "/k", False), (False, False, "", False), (True, True, "/k", True))], [True, True, False, False, False, False])
check("the new warnings", [sec.known_warning([w]) for w in ("voice_heard_text_on", "voice_confidence_off", "mavlink_unsigned_allowed", "mavlink_signing_off")], [_("SECURITY_VOICE_HEARD_WARNING"), _("SECURITY_VOICE_CONFIDENCE_WARNING"), _("SECURITY_MAVLINK_UNSIGNED_WARNING"), _("SECURITY_MAVLINK_OFF_WARNING")])

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
