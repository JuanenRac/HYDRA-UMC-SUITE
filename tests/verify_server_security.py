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
from hydra_suite.panel_logic import developer_node_status as dev
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

ROBOTS = {**raw, "robots": {"allowEnable": {"value": False, "source": "default"}}}
rb = sec.parse_state(ROBOTS)
check("reads the safe mode option of the robots", rb["robots"], {"allowEnable": {"value": False, "source": "default"}})
check("a server without it shows no section", (plain["robots"], sec.view(plain)["robotsAvailable"], sec.view(rb)["robotsAvailable"]), (None, False, True))
check("a damaged option is dropped, not the rest", (sec.parse_state({**ROBOTS, "robots": {"allowEnable": {"value": "yes", "source": "default"}}})["robots"], sec.parse_state({**ROBOTS, "robots": {"allowEnable": {"value": True, "source": "nowhere"}}})["robots"], sec.parse_state({**ROBOTS, "robots": 3})["tls"]["enabled"]), (None, None, False))
check("the robots view", (sec.view(rb)["robotsAllowEnable"], sec.view(rb)["robotsAllowEnableLocked"], sec.view(sec.parse_state({**ROBOTS, "robots": {"allowEnable": {"value": True, "source": "env"}}}))["robotsAllowEnableLocked"]), (False, False, True))
check("the robots request", (sec.robots_patch(True), sec.robots_patch(False)), ({"robots": {"allowEnable": True}}, {"robots": {"allowEnable": False}}))
check("only allowing it asks", [sec.robots_needs_confirmation(a, b) for a, b in ((False, True), (True, False), (True, True), (False, False))], [True, False, False, False])
check("the warning of allowing it", sec.known_warning(["robot_enable_allowed"]), _("SECURITY_ROBOTS_WARNING"))
check("every key of the view exists without a server (robots included)", set(sec.view(None)) == set(sec.view(rb)), True)

HEALTH = {**raw, "health": {"open": {"value": False, "source": "default"}}, "safety": {"publishGlobalStop": {"value": True, "source": "env"}}}
hs = sec.parse_state(HEALTH)
check("reads the health route and the stop announcement options", (hs["health"], hs["safety"]), ({"open": {"value": False, "source": "default"}}, {"publishGlobalStop": {"value": True, "source": "env"}}))
check("a server without them shows no section", (plain["health"], plain["safety"], sec.view(plain)["healthAvailable"], sec.view(plain)["safetyAvailable"], sec.view(hs)["healthAvailable"], sec.view(hs)["safetyAvailable"]), (None, None, False, False, True, True))
check("a damaged option is dropped, not the rest", (sec.parse_state({**HEALTH, "health": {"open": {"value": "yes", "source": "default"}}})["health"], sec.parse_state({**HEALTH, "safety": {"publishGlobalStop": {"value": True, "source": "nowhere"}}})["safety"], sec.parse_state({**HEALTH, "safety": 3})["tls"]["enabled"]), (None, None, False))
check("the health and stop views", (sec.view(hs)["healthOpen"], sec.view(hs)["healthOpenLocked"], sec.view(hs)["safetyPublishStop"], sec.view(hs)["safetyPublishStopLocked"]), (False, False, True, True))
check("the health and stop requests", (sec.health_patch(True), sec.safety_patch(False)), ({"health": {"open": True}}, {"safety": {"publishGlobalStop": False}}))
check("only opening the health route asks", [sec.health_needs_confirmation(a, b) for a, b in ((False, True), (True, False), (True, True), (False, False))], [True, False, False, False])
check("the warning of opening it", sec.known_warning(["health_open"]), _("SECURITY_HEALTH_WARNING"))
check("every key of the view exists without a server (health and stop included)", set(sec.view(None)) == set(sec.view(hs)), True)

def _opt(value, source="default"):
    return {"value": value, "source": source}


EXPO = {
    **raw,
    "camera": {"open": _opt(False)},
    "websocket": {"allowQueryToken": _opt(False, "env")},
    "logging": {"redactSecrets": _opt(True)},
    "voice": {**raw.get("voice", {}), "requireSignature": _opt(False, "config")} if isinstance(raw.get("voice"), dict) else {"requireSignature": _opt(False, "config")},
    "connections": {"recordAddress": _opt(False)},
}
es = sec.parse_state(EXPO)
check("reads the four exposure options", {k: v["value"] for k, v in es["exposure"].items()}, {"cameraOpen": False, "wsQueryToken": False, "logRedaction": True, "voiceSignature": False})
check("a server without them shows no exposure card", (plain["exposure"], sec.view(plain)["exposureAvailable"], sec.view(es)["exposureAvailable"]), (None, False, True))
half = {**EXPO, "camera": {"open": _opt("yes")}}
check("a half-known set of exposure options is not shown", sec.parse_state(half)["exposure"], None)
check("the exposure view keeps the origin and the lock", (sec.view(es)["exposureWsQueryTokenLocked"], sec.view(es)["exposureCameraOpenLocked"], sec.view(es)["exposureWsQueryTokenSource"], sec.view(es)["exposureLogRedaction"]), (True, False, _("SECURITY_SOURCE_ENV"), True))
cur = {"cameraOpen": False, "wsQueryToken": False, "logRedaction": True, "voiceSignature": False}
check("nothing changed sends nothing", sec.exposure_patch(cur, dict(cur)), None)
check("only what changed is sent", sec.exposure_patch(cur, {**cur, "cameraOpen": True, "logRedaction": False}), {"camera": {"open": True}, "logging": {"redactSecrets": False}})
check("the signature goes in the voice section", sec.exposure_patch(cur, {**cur, "voiceSignature": True}), {"voice": {"requireSignature": True}})
check("a missing value sends nothing", sec.exposure_patch(cur, {"cameraOpen": True}), None)
check("only lowering a protection asks", [sec.exposure_needs_confirmation(cur, {**cur, k: v}) for k, v in (("cameraOpen", True), ("wsQueryToken", True), ("logRedaction", False), ("voiceSignature", True))], [True, True, True, False])
check("tightening never asks", sec.exposure_needs_confirmation({"cameraOpen": True, "wsQueryToken": True, "logRedaction": False, "voiceSignature": False}, cur), False)
check("the exposure warnings", [sec.known_warning([w]) for w in ("camera_open", "ws_query_token_allowed", "log_redaction_off")], [_("SECURITY_EXPOSURE_CAMERA_WARNING"), _("SECURITY_EXPOSURE_WS_WARNING"), _("SECURITY_EXPOSURE_LOG_WARNING")])
check("the connections option is read, sent and asks only when turned on", (sec.view(es)["connectionsAvailable"], sec.view(plain)["connectionsAvailable"], sec.connections_patch(True), [sec.connections_needs_confirmation(a, b) for a, b in ((False, True), (True, False), (True, True), (False, False))], sec.known_warning(["connection_address_recorded"])), (True, False, {"connections": {"recordAddress": True}}, [True, False, False, False], _("SECURITY_CONNECTIONS_WARNING")))
check("every key of the view exists without a server (exposure and connections included)", set(sec.view(None)) == set(sec.view(es)), True)
PROD = {**EXPO, "production": {"rdpLevel": _opt(0)}}
ps = sec.parse_state(PROD)
check("the production flash option is read, off by default, sent as 0 or 1 and asks only when turned on", (ps["production"]["rdpLevel"]["value"], sec.view(ps)["productionAvailable"], sec.view(es)["productionAvailable"], sec.view(ps)["productionRdp"], sec.production_patch(True), sec.production_patch(False), [sec.production_needs_confirmation(a, b) for a, b in ((False, True), (True, False), (True, True), (False, False))]), (0, True, False, False, {"production": {"rdpLevel": 1}}, {"production": {"rdpLevel": 0}}, [True, False, False, False]))
check("a level other than 0 or 1 is not shown", (sec.parse_state({**EXPO, "production": {"rdpLevel": _opt(2)}})["production"], sec.parse_state({**EXPO, "production": {"rdpLevel": _opt(True)}})["production"]), (None, None))

# -- the installation options (password of an IP camera through the environment, TLS of a new installation) --
INSTALL = {**EXPO, "camera": {"open": _opt(False), "credentialsViaEnv": _opt(True)}, "install": {"newInstallTls": _opt(True, "env")}}
isr = sec.parse_state(INSTALL)
check("reads the two installation options and keeps the camera pictures option apart", ({k: v["value"] for k, v in isr["install"].items()}, isr["exposure"]["cameraOpen"]), ({"cameraCredentialsViaEnv": True, "newInstallTls": True}, {"value": False, "source": "default"}))
check("a server without them shows no installation card", (plain["install"], sec.view(plain)["installAvailable"], sec.view(isr)["installAvailable"]), (None, False, True))
check("a half-known set of installation options is not shown", (sec.parse_state({**INSTALL, "install": {"newInstallTls": _opt("yes")}})["install"], sec.parse_state({**INSTALL, "install": None})["install"]), (None, None))
check("the installation view keeps the origin and the lock", (sec.view(isr)["installNewInstallTlsLocked"], sec.view(isr)["installCameraCredentialsViaEnvLocked"], sec.view(isr)["installNewInstallTlsSource"], sec.view(isr)["installCameraCredentialsViaEnv"]), (True, False, _("SECURITY_SOURCE_ENV"), True))
icur = {"cameraCredentialsViaEnv": True, "newInstallTls": True}
check("nothing changed sends nothing (installation)", sec.install_patch(icur, dict(icur)), None)
check("only what changed is sent (installation)", sec.install_patch(icur, {**icur, "cameraCredentialsViaEnv": False}), {"camera": {"credentialsViaEnv": False}})
check("both sections travel when both changed", sec.install_patch(icur, {"cameraCredentialsViaEnv": False, "newInstallTls": False}), {"camera": {"credentialsViaEnv": False}, "install": {"newInstallTls": False}})
check("a missing installation value sends nothing", sec.install_patch(icur, {"newInstallTls": False}), None)
check("only lowering a protection asks (installation)", [sec.install_needs_confirmation(icur, {**icur, k: False}) for k in icur], [True, True])
check("tightening never asks (installation)", sec.install_needs_confirmation({"cameraCredentialsViaEnv": False, "newInstallTls": False}, icur), False)
check("the installation warnings", [sec.known_warning([w]) for w in ("camera_credentials_in_arguments", "new_install_tls_off")], [_("SECURITY_INSTALL_CAMERA_WARNING"), _("SECURITY_INSTALL_TLS_WARNING")])
check("every key of the view exists without a server (installation included)", set(sec.view(None)) == set(sec.view(isr)), True)

# -- the simple history of connections --
from datetime import datetime, timezone

from hydra_suite.panel_logic import connection_history as hist

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
CLIENT = {"id": "0123456789abcdef", "kind": "suite", "user": "ana", "app_version": "0.7.3", "origin": "local", "two_factor": True,
          "first_seen_utc": "2026-01-01T10:00:00Z", "last_seen_utc": "2026-01-01T11:59:30Z", "active_sessions": 2, "logins_ok": 5, "logins_failed": 1, "ip": "10.0.0.2", "agent": "x"}
EVENT = {"id": 7, "at_utc": "2026-01-01T11:00:00Z", "action": "login_failed", "client_kind": "android", "client_id": "0123456789abcdef", "user": "bob"}
check("reads the clients and drops a damaged one", [c["user"] for c in hist.parse_clients({"clients": [CLIENT, {**CLIENT, "id": "zz"}, 5, {**CLIENT, "last_seen_utc": "never"}]})], ["ana"])
check("reads the events and drops a damaged one", [e["id"] for e in hist.parse_events({"events": [EVENT, {**EVENT, "action": "explode"}, {**EVENT, "id": 0}, None]})], [7])
check("nonsense gives an empty list", (hist.parse_clients(None), hist.parse_clients({"clients": "x"}), hist.parse_events([])), ([], [], []))
check("an unknown kind is shown as other", hist.parse_client({**CLIENT, "kind": "toaster"})["kind"], "other")
check("the time since a date", [hist.ago(t, NOW) for t in ("2026-01-01T11:59:55Z", "2026-01-01T11:48:00Z", "2026-01-01T08:56:00Z", "2025-12-29T12:00:00Z", "bad", None)], ["5s", "12m", "3h 4m", "3d", "-", "-"])
rows = hist.client_rows(hist.parse_clients({"clients": [CLIENT]}), NOW)
check("a client row", (rows[0]["who"], rows[0]["twoFactor"], rows[0]["active"], rows[0]["lastSeen"], rows[0]["sessions"]), ("ana", True, True, "30s", _("CONNECTIONS_SESSIONS", open=2)))
check("the address only shows when the server sent it", ("10.0.0.2" in rows[0]["detail"], "10.0.0.2" in hist.client_rows(hist.parse_clients({"clients": [{**CLIENT, "ip": None}]}), NOW)[0]["detail"]), (True, False))
erows = hist.event_rows(hist.parse_events({"events": [EVENT, {**EVENT, "id": 8, "action": "login", "user": None}]}), NOW)
check("a refused sign-in is painted as a failure", [r["failure"] for r in erows], [True, False])
check("an event without a user says so", _("CONNECTIONS_NO_USER") in erows[1]["detail"], True)
check("the sentences for a server that cannot answer", [hist.status_for(r) for r in ((200, {}), (404, None), (403, None), (401, None), (500, None), None)], ["", _("CONNECTIONS_UNSUPPORTED"), _("CONNECTIONS_FORBIDDEN"), _("CONNECTIONS_FORBIDDEN"), _("CONNECTIONS_LOAD_ERROR"), _("CONNECTIONS_LOAD_ERROR")])
check("every kind, origin and action has a sentence", all(_(k) != k for k in [f"CONNECTIONS_KIND_{x.upper()}" for x in hist.CLIENT_KINDS] + ["CONNECTIONS_ORIGIN_LOCAL", "CONNECTIONS_ORIGIN_REMOTE"] + [f"CONNECTIONS_ACTION_{x.upper()}" for x in hist.ACTIONS]), True)

# -- the options of the job dispatcher --
JD = {"stopRelay": {"enabled": {"value": False, "source": "default"}, "robotMap": {"arm-2": 2, "arm-1": 1}, "appliesOnRestart": True},
      "replan": {"allowUnconfirmed": {"value": False, "source": "default"}, "stopAckTimeoutSeconds": {"value": 45, "source": "config"}, "editable": True}}
jd_state = sec.parse_state({**GOOD, "jobDispatcher": JD})
check("reads the options of the job dispatcher", (jd_state["jobDispatcher"]["robotMap"], jd_state["jobDispatcher"]["editable"], jd_state["jobDispatcher"]["timeout"]["value"]), ({"arm-2": 2, "arm-1": 1}, True, 45))
check("a server without them, or with damaged ones, shows no section", (sec.parse_state(GOOD)["jobDispatcher"], sec.parse_state({**GOOD, "jobDispatcher": {**JD, "replan": {**JD["replan"], "stopAckTimeoutSeconds": {"value": "45", "source": "config"}}}})["jobDispatcher"], sec.view(sec.parse_state(GOOD))["jdAvailable"]), (None, None, False))
jv = sec.view(jd_state)
check("the view of the job dispatcher", (jv["jdAvailable"], jv["jdRelay"], jv["jdMapText"], jv["jdTimeout"], jv["jdReplanEditable"], jv["jdReplanNote"] == _("LBL_SECURITY_JD_REPLAN_HELP")), (True, False, "arm-1 = 1\narm-2 = 2", "45", True, True))
check("without the file of the dispatcher the replanning is read only and says why", sec.view(sec.parse_state({**GOOD, "jobDispatcher": {**JD, "replan": {**JD["replan"], "editable": False}}}))["jdReplanNote"], _("LBL_SECURITY_JD_NOT_EDITABLE"))
check("the robot map as text and back", (sec.parse_robot_map_text("arm-1 = 1\n\n arm-2=2 \r\n"), sec.parse_robot_map_text("")), ({"arm-1": 1, "arm-2": 2}, {}))
check("a wrong robot map is refused", [sec.parse_robot_map_text(x) for x in ("arm-1", "arm-1 = x", "arm-1 = -1", "bad id = 1", "= 1", "a = 1\na = 2", "x" * 65 + " = 1")], [None] * 7)
check("the wait is a number from above 0 to 86400", [sec.parse_timeout(x) for x in ("30", "45,5", "86400", "0", "-1", "86401", "", "abc", "1e3")], [30.0, 45.5, 86400.0, None, None, None, None, None, None])
check("builds the request, with the replanning only when the server can write the file",
      (sec.job_dispatcher_patch(True, "arm-1 = 1", True, True, "45"), sec.job_dispatcher_patch(True, "arm-1 = 1", False, True, "nonsense"), sec.job_dispatcher_patch(True, "nonsense", True, True, "45"), sec.job_dispatcher_patch(True, "arm-1 = 1", True, True, "0")),
      ({"jobDispatcher": {"stopRelay": {"enabled": True, "robotMap": {"arm-1": 1}}, "replan": {"allowUnconfirmed": True, "stopAckTimeoutSeconds": 45.0}}}, {"jobDispatcher": {"stopRelay": {"enabled": True, "robotMap": {"arm-1": 1}}}}, None, None))
cur = jd_state["jobDispatcher"]
check("asks first when the delivery is switched on or a job may go without a confirmed stop",
      [sec.job_dispatcher_needs_confirmation(cur, sec.job_dispatcher_patch(*args)) for args in ((False, "a = 1", True, False, "30"), (True, "a = 1", True, False, "30"), (False, "a = 1", True, True, "30"), (False, "a = 1", True, False, "60"))],
      [False, True, True, False])
check("knows the two warnings", (sec.known_warning(["job_stop_relay_on"]) == _("SECURITY_JD_WARNING_RELAY"), sec.known_warning(["replan_unconfirmed_allowed"]) == _("SECURITY_JD_WARNING_REPLAN")), (True, True))
check("every sentence exists", all(_(k) != k for k in ("TITLE_SECURITY_JD", "LBL_SECURITY_JD_RELAY", "LBL_SECURITY_JD_MAP", "MSG_SECURITY_JD_MAP_INVALID", "MSG_SECURITY_JD_TIMEOUT_INVALID", "MSG_SECURITY_JD_CONFIRM")), True)

AUTH = {**raw, "auth": {"jwtAlgorithm": {"value": "HS256", "source": "default"}, "acceptHs256": {"value": True, "source": "default"}}}
au = sec.parse_state(AUTH)
check("reads how the sign-in tokens are signed", au["auth"], {"jwtAlgorithm": {"value": "HS256", "source": "default"}, "acceptHs256": {"value": True, "source": "default"}})
check("a server without the option shows no section", (plain["auth"], sec.view(plain)["authAvailable"], sec.view(au)["authAvailable"]), (None, False, True))
check("a damaged option is dropped, not the rest", (sec.parse_state({**AUTH, "auth": {"jwtAlgorithm": {"value": "none", "source": "default"}, "acceptHs256": {"value": True, "source": "default"}}})["auth"], sec.parse_state({**AUTH, "auth": {"jwtAlgorithm": {"value": "EdDSA", "source": "default"}, "acceptHs256": {"value": "yes", "source": "default"}}})["auth"], sec.parse_state({**AUTH, "auth": 3})["tls"]["enabled"]), (None, None, False))
eddsa_env = sec.view(sec.parse_state({**AUTH, "auth": {"jwtAlgorithm": {"value": "EdDSA", "source": "env"}, "acceptHs256": {"value": False, "source": "config"}}}))
check("the view and the lock", (sec.view(au)["authAlgorithm"], sec.view(au)["authAcceptHs256"], eddsa_env["authAlgorithm"], eddsa_env["authAlgorithmLocked"], eddsa_env["authAcceptHs256"], eddsa_env["authAcceptHs256Locked"]), ("HS256", True, "EdDSA", True, False, False))
check("the requests send only what is given", (sec.auth_patch("EdDSA"), sec.auth_patch(None, False), sec.auth_patch("EdDSA", True), sec.auth_patch("RS256"), sec.auth_patch("none", True)), ({"auth": {"jwtAlgorithm": "EdDSA"}}, {"auth": {"acceptHs256": False}}, {"auth": {"jwtAlgorithm": "EdDSA", "acceptHs256": True}}, None, None))
check("only refusing HS256 tokens asks", [sec.auth_needs_confirmation(a, b) for a, b in ((True, False), (False, True), (True, True), (False, False))], [True, False, False, False])
check("the warnings of the change", (sec.known_warning(["jwt_eddsa_on"]), sec.known_warning(["jwt_hs256_refused"])), (_("SECURITY_AUTH_EDDSA_WARNING"), _("SECURITY_AUTH_HS256_REFUSED_WARNING")))
check("every key of the view exists without a server (sign-in tokens included)", set(sec.view(None)) == set(sec.view(au)), True)
check("every sentence exists", all(_(k) != k for k in ("LBL_SECURITY_AUTH", "TITLE_SECURITY_AUTH", "LBL_SECURITY_AUTH_HS256", "LBL_SECURITY_AUTH_EDDSA", "LBL_SECURITY_AUTH_ACCEPT_HS256", "LBL_SECURITY_AUTH_HELP", "MSG_SECURITY_AUTH_CONFIRM", "BTN_SECURITY_AUTH_ROTATE", "MSG_SECURITY_AUTH_ROTATE_CONFIRM", "SECURITY_AUTH_EDDSA_WARNING", "SECURITY_AUTH_HS256_REFUSED_WARNING", "SECURITY_AUTH_ROTATED", "SECURITY_AUTH_ROTATE_ERROR")), True)

# --- the request limits per address ---
def rl_entry(value, low=1, high=100000, source="default"):
    return {"value": value, "min": low, "max": high, "source": source}


RL_RAW = {
    "enabled": {"value": True, "source": "default"},
    "loginMax": rl_entry(10), "loginWindowSeconds": rl_entry(900, 1, 86400), "refreshMax": rl_entry(30), "apiMax": rl_entry(600),
    "sensitiveMax": rl_entry(60), "apiWindowSeconds": rl_entry(60, 1, 3600), "stopAllMax": rl_entry(120), "stopAllWindowSeconds": rl_entry(60, 1, 3600),
}
rl_limits = sec._rate_limits(RL_RAW)
check("reads the switch and the eight numbers", (rl_limits["enabled"]["value"], len(rl_limits["numbers"]), rl_limits["numbers"]["loginMax"]), (True, 8, {"value": 10, "min": 1, "max": 100000, "source": "default"}))
check("a damaged answer shows no section", (sec._rate_limits(None), sec._rate_limits({**RL_RAW, "loginMax": {"value": "x", "min": 1, "max": 2, "source": "env"}}), sec._rate_limits({**RL_RAW, "enabled": {"value": 1, "source": "env"}}), sec._rate_limits({**RL_RAW, "apiMax": rl_entry(True)}), sec._rate_limits({k: v for k, v in RL_RAW.items() if k != "apiMax"})), (None, None, None, None, None))
state = {"rateLimits": rl_limits}
texts = {k: str(v["value"]) for k, v in rl_limits["numbers"].items()}
check("nothing changed sends nothing", sec.rate_limits_patch(state, True, texts), None)
check("only what changed is sent", sec.rate_limits_patch(state, False, {**texts, "apiMax": "900"}), {"rateLimits": {"enabled": False, "apiMax": 900}})
check("a number outside its range, not whole or empty is refused", [sec.rate_limits_patch(state, True, {**texts, "loginMax": bad}) for bad in ("0", "100001", "1.5", "", "-3", "ten")], [None] * 6)
check("a number fixed by the environment is never sent nor required", sec.rate_limits_patch(
    {"rateLimits": sec._rate_limits({**RL_RAW, "apiMax": rl_entry(600, source="env")})}, True, {**texts, "apiMax": "oops"}), None)
locked = {"rateLimits": sec._rate_limits({**RL_RAW, "enabled": {"value": True, "source": "env"}})}
check("a switch fixed by the environment is not sent", sec.rate_limits_patch(locked, False, texts), None)
check("the typed numbers are checked before sending", (sec.rate_limit_texts_valid(state, texts), sec.rate_limit_texts_valid(state, {**texts, "loginMax": "0"}), sec.rate_limit_texts_valid(state, "x")), (True, False, False))
check("only switching the limiters off asks", (sec.rate_limits_need_confirmation(state, False), sec.rate_limits_need_confirmation(state, True), sec.rate_limits_need_confirmation({"rateLimits": sec._rate_limits({**RL_RAW, "enabled": {"value": False, "source": "default"}})}, True)), (True, False, False))
view = sec.view({**sec.parse_state({"aiAccess": {"value": "open", "source": "default"}, "infoAuth": {"value": True, "source": "default"}, "tls": {"enabled": False, "source": "default"}}), "rateLimits": rl_limits})
check("the view has the eight rows with range and source", (view["rlAvailable"], view["rlEnabled"], [r["key"] for r in view["rlRows"]][:2], view["rlRows"][0]["value"], view["rlRows"][0]["note"].startswith("1 - 100000")), (True, True, ["loginMax", "loginWindowSeconds"], "10", True))
check("the keys of the view exist before any server answered", set(sec.view(None)) == set(view), True)
check("the warnings of the server", (sec.known_warning(["rate_limits_off"]), sec.known_warning(["rate_limits_loose"])), (_("SECURITY_RL_OFF_WARNING"), _("SECURITY_RL_LOOSE_WARNING")))
for key in list(sec.RATE_LIMIT_KEYS.values()) + ["LBL_SECURITY_RL", "LBL_SECURITY_RL_ENABLED", "LBL_SECURITY_RL_HELP", "BTN_SECURITY_RL_SAVE", "TITLE_SECURITY_RL", "MSG_SECURITY_RL_CONFIRM", "SECURITY_RL_OFF_WARNING", "SECURITY_RL_LOOSE_WARNING", "SECURITY_RL_INVALID"]:
    check(f"sentence {key} exists", _(key) != key, True)

# -- what the services hand to the server (the ingest switches) --
ING = {**EXPO, "ingest": {**{k: _opt(False) for k in sec.INGEST_KEYS}, "proposalKeysFile": _opt(""), "appliesOnRestart": False}}
ins = sec.parse_state(ING)
check("the ingest block is read, every switch off by default", ([ins["ingest"]["switches"][k]["value"] for k in sec.INGEST_KEYS], ins["ingest"]["keysFile"]["value"], sec.view(ins)["ingestAvailable"], sec.view(es)["ingestAvailable"]), ([False] * 7, "", True, False))
check("a damaged or missing ingest block shows no section", [sec.parse_state({**EXPO, "ingest": body})["ingest"] for body in ({}, {**ING["ingest"], "voiceChain": _opt("yes")}, {**ING["ingest"], "faultFeed": _opt(True, "nowhere")}, {**ING["ingest"], "proposalKeysFile": _opt(3)}, 5)], [None] * 5)
check("the view has a row per switch with its label, hint and lock", ([r["key"] for r in sec.view(ins)["ingestRows"]], all(r["label"] and not r["label"].startswith("LBL_") and r["hint"] and not r["hint"].startswith("LBL_") for r in sec.view(ins)["ingestRows"])), (list(sec.INGEST_KEYS), True))
locked = sec.parse_state({**EXPO, "ingest": {**ING["ingest"], "faultFeed": _opt(True, "env"), "proposalKeysFile": _opt("/etc/k.json", "env"), "appliesOnRestart": True}})
check("a switch and a keys file fixed by the environment are locked, and a restart is told", (sec.view(locked)["ingestRows"][0]["locked"], sec.view(locked)["ingestRows"][1]["locked"], sec.view(locked)["ingestKeysLocked"], bool(sec.view(locked)["ingestRestart"])), (True, False, True, True))
check("only a switch turned on, or another keys file, asks", [sec.ingest_needs_confirmation(ins, w, k) for w, k in (({"scenario": True}, None), ({"scenario": False}, None), ({}, "operators.json"), ({}, ""), ({}, None))], [True, False, True, False, False])
check("the request has only what changes and confirm exactly when it asks", (sec.ingest_patch(ins, {"scenario": True, "voiceChain": False}, ""), sec.ingest_patch(ins, {}, "operators.json"), sec.ingest_patch(ins, {}, ""), sec.ingest_patch(ins, {"scenario": "yes"}, None)), ({"ingest": {"scenario": True, "confirm": True}}, {"ingest": {"proposalKeysFile": "operators.json", "confirm": True}}, None, None))
on = sec.parse_state({**EXPO, "ingest": {**ING["ingest"], "voiceChain": _opt(True, "config")}})
check("turning one off sends no confirmation", sec.ingest_patch(on, {"voiceChain": False}, None), {"ingest": {"voiceChain": False}})
check("a locked switch is never sent", (sec.ingest_patch(locked, {"faultFeed": False}, "other.json"), sec.ingest_needs_confirmation(locked, {"faultFeed": True}, "other.json")), (None, False))
check("the keys file name follows the rule of the server", ([sec.valid_keys_file_name(n) for n in ("", "operators.json", "a_b-c.2.json")], [sec.valid_keys_file_name(n) for n in ("../k.json", "a/b", ".hidden", "a..b", "x" * 65, "a b", "ñ.json")]), ([True] * 3, [False] * 7))
check("an invalid keys file is not sent", sec.ingest_patch(ins, {}, "../k.json"), None)
check("every key of the view exists without a server (ingest included)", set(sec.view(None)) == set(sec.view(ins)), True)

# -- the status of the developer node (read only) --
DEV_BODY = {
    "nodes": {
        "dev-b": {"at": 1700000000000, "seq": 4, "status": {"version": "1.2.3", "ok": True, "count": 7, "nested": {"a": 1}, "list": [1]}},
        "dev-a": {"at": 1700000001000, "seq": 9, "status": {}},
    },
    "chain": {"ok": True},
}
parsed = dev.parse_status(DEV_BODY)
check("the nodes are sorted by id", [n["nodeId"] for n in parsed["nodes"]], ["dev-a", "dev-b"])
check("only plain values are kept", parsed["nodes"][1]["fields"], [{"name": "version", "value": "1.2.3"}, {"name": "ok", "value": "true"}, {"name": "count", "value": "7"}])
check("the chain result is read", parsed["chain"], {"ok": True})
check("an answer without nodes is refused", (dev.parse_status({}), dev.parse_status({"nodes": []}), dev.parse_status(None)), (None, None, None))
check("a node without a time or an entry number is dropped", dev.parse_status({"nodes": {"x": {"at": "now", "seq": 1}, "y": {"at": 1, "seq": True}, "z": 5}})["nodes"], [])
check("a damaged chain result is ignored", dev.parse_status({"nodes": {}, "chain": {"ok": "yes"}})["chain"], None)
check("the fields are limited", len(dev.parse_status({"nodes": {"x": {"at": 1, "seq": 1, "status": {f"k{i}": i for i in range(100)}}}})["nodes"][0]["fields"]), dev.MAX_FIELDS)
check("a long text is cut", len(dev.parse_status({"nodes": {"x": {"at": 1, "seq": 1, "status": {"k": "a" * 1000}}}})["nodes"][0]["fields"][0]["value"]), dev.MAX_TEXT)

check("a switch that is off, a refused account and a failure have their sentence", (dev.status_for((404, {})), dev.status_for((403, {})), dev.status_for(None), dev.status_for((200, {"x": 1})), dev.status_for((200, DEV_BODY))), (_("DEVNODE_OFF"), _("DEVNODE_FORBIDDEN"), _("DEVNODE_LOAD_ERROR"), _("DEVNODE_LOAD_ERROR"), ""))
dev_view = dev.view(parsed)
check("the view has a row per node with its time and fields", ([r["title"] for r in dev_view["rows"]], dev_view["rows"][1]["fields"].splitlines()[:2], _("DEVNODE_ENTRY") in dev_view["rows"][0]["received"]), (["dev-a", "dev-b"], ["version: 1.2.3", "ok: true"], True))
check("the chain is said intact or broken", (dev_view["chain"], dev_view["chainOk"], dev.view({"nodes": [], "chain": {"ok": False}})["chain"]), (_("DEVNODE_CHAIN_OK"), True, _("DEVNODE_CHAIN_BROKEN")))
check("no node yet is told, and no answer shows only the problem", (dev.view({"nodes": [], "chain": None})["none"], dev.view(None, "x")), (True, {"problem": "x", "rows": [], "none": False, "chain": "", "chainOk": False}))
for key in ("DEVNODE_TITLE", "DEVNODE_DESC", "DEVNODE_REFRESH", "DEVNODE_VERIFY", "DEVNODE_CHAIN_OK", "DEVNODE_CHAIN_BROKEN", "DEVNODE_NONE", "DEVNODE_OFF", "DEVNODE_LOAD_ERROR", "DEVNODE_FORBIDDEN", "DEVNODE_RECEIVED", "DEVNODE_ENTRY"):
    check(f"sentence {key} exists", _(key) != key, True)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
