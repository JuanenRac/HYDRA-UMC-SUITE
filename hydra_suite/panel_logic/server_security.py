# =============================================================================
# HYDRA-UMC SUITE - panel_logic/server_security.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The access options of the Server Admin screen (GET/PUT /api/admin/server-config), without any window toolkit:
# who may use the local AI relay, whether the host information asks for a sign-in, TLS and the Bluetooth LE
# service. Reading is tolerant: a server that predates the options answers without them and the screen shows
# no section; one that predates only the Bluetooth service shows the other three.
# =============================================================================
from __future__ import annotations

import re

from hydra_suite.i18n import _

SOURCES = ("env", "config", "default")
BLE_MODES = ("off", "state", "commands")
MQTT_MODES = ("off", "state", "commands")


def _source(value: object) -> str | None:
    return value if isinstance(value, str) and value in SOURCES else None


def _option(raw: object, kind: type | tuple[type, ...], allowed: tuple[str, ...] | None = None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    value, source = raw.get("value"), _source(raw.get("source"))
    if source is None or isinstance(value, bool) != (kind is bool) or not isinstance(value, kind):
        return None
    if allowed is not None and value not in allowed:
        return None
    return {"value": value, "source": source}


def _confidence_option(raw: object) -> dict | None:
    """A minimum confidence: a number from 0 to 1 (a switch is not a number) and where it comes from."""
    if not isinstance(raw, dict):
        return None
    value, source = raw.get("value"), _source(raw.get("source"))
    if source is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return None
    return {"value": float(value), "source": source}


#: The four exposure options: view name -> (section, key) in the answer of the server.
EXPOSURE_FIELDS = {
    "cameraOpen": ("camera", "open"),
    "wsQueryToken": ("websocket", "allowQueryToken"),
    "logRedaction": ("logging", "redactSecrets"),
    "voiceSignature": ("voice", "requireSignature"),
}


def _exposure(body: dict) -> dict | None:
    """The four exposure options (open camera pictures, a token in the WebSocket address, blanking of secrets in the log,
    signature of a spoken confirmation); None unless the server offers all four, so a half-known set is never shown."""
    found = {}
    for name, (section, key) in EXPOSURE_FIELDS.items():
        raw = body.get(section)
        option = _option(raw.get(key), bool) if isinstance(raw, dict) else None
        if option is None:
            return None
        found[name] = option
    return found


#: The two installation options: view name -> (section, key) in the answer of the server.
INSTALL_FIELDS = {
    "cameraCredentialsViaEnv": ("camera", "credentialsViaEnv"),
    "newInstallTls": ("install", "newInstallTls"),
}


def _install(body: dict) -> dict | None:
    """The two installation options (the password of an IP camera handed over through the environment, TLS switched on by a new
    installation); None unless the server offers both, so a half-known set is never shown."""
    found = {}
    for name, (section, key) in INSTALL_FIELDS.items():
        raw = body.get(section)
        option = _option(raw.get(key), bool) if isinstance(raw, dict) else None
        if option is None:
            return None
        found[name] = option
    return found


def parse_state(body: object) -> dict | None:
    """The options in a GET/PUT answer; None for a server that predates them or answers nonsense."""
    if not isinstance(body, dict):
        return None
    ai = _option(body.get("aiAccess"), str, ("open", "admin"))
    info = _option(body.get("infoAuth"), bool)
    tls = body.get("tls")
    if ai is None or info is None or not isinstance(tls, dict):
        return None
    tls_source = _source(tls.get("source"))
    if tls_source is None or not isinstance(tls.get("enabled"), bool):
        return None
    state = {
        "ai": ai,
        "info": info,
        "tls": {
            "enabled": tls["enabled"],
            "source": tls_source,
            "certPath": tls.get("certPath") if isinstance(tls.get("certPath"), str) else "",
            "keyPath": tls.get("keyPath") if isinstance(tls.get("keyPath"), str) else "",
            "fingerprint": tls.get("fingerprint256") if isinstance(tls.get("fingerprint256"), str) else None,
            "active": tls.get("active") is True,
            "appliesOnRestart": tls.get("appliesOnRestart") is True,
        },
        "ble": None,
        "mqtt": None,
        "voice": None,
        "robots": None,
        "health": None,
        "safety": None,
        "connections": None,
        "exposure": None,
        "install": None,
        "mavlink": None,
    }
    ble = body.get("ble")
    if isinstance(ble, dict):
        mode = _option(ble.get("mode"), str, BLE_MODES)
        encryption = _option(ble.get("requireEncryption"), bool)
        if mode is not None and encryption is not None:
            active = ble.get("activeMode")
            state["ble"] = {
                "mode": mode,
                "encryption": encryption,
                "activeMode": active if active in BLE_MODES else "off",
                "appliesOnRestart": ble.get("appliesOnRestart") is True,
            }
    mqtt = body.get("mqtt")
    if isinstance(mqtt, dict):
        mode = _option(mqtt.get("mode"), str, MQTT_MODES)
        if mode is not None:
            active = mqtt.get("activeMode")

            def text(key: str) -> str:
                return mqtt[key] if isinstance(mqtt.get(key), str) else ""

            state["mqtt"] = {
                "mode": mode,
                "url": text("url"),
                "prefix": text("prefix"),
                "username": text("username"),
                "commandUser": text("commandUser"),
                "activeMode": active if active in MQTT_MODES else "off",
                "appliesOnRestart": mqtt.get("appliesOnRestart") is True,
            }
    voice = body.get("voice")
    if isinstance(voice, dict):
        heard = _option(voice.get("includeHeardText"), bool)
        confidence = _confidence_option(voice.get("minConfidence"))
        if heard is not None and confidence is not None:
            state["voice"] = {"heard": heard, "confidence": confidence}
    robots = body.get("robots")
    if isinstance(robots, dict):
        allow = _option(robots.get("allowEnable"), bool)
        if allow is not None:
            state["robots"] = {"allowEnable": allow}
    health = body.get("health")
    if isinstance(health, dict):
        opened = _option(health.get("open"), bool)
        if opened is not None:
            state["health"] = {"open": opened}
    safety = body.get("safety")
    if isinstance(safety, dict):
        publish = _option(safety.get("publishGlobalStop"), bool)
        if publish is not None:
            state["safety"] = {"publishGlobalStop": publish}
    connections = body.get("connections")
    if isinstance(connections, dict):
        record = _option(connections.get("recordAddress"), bool)
        if record is not None:
            state["connections"] = {"recordAddress": record}
    exposure = _exposure(body)
    if exposure is not None:
        state["exposure"] = exposure
    install = _install(body)
    if install is not None:
        state["install"] = install
    mavlink = body.get("mavlink")
    if isinstance(mavlink, dict):
        key = _option(mavlink.get("signingKeyFile"), str)
        unsigned = _option(mavlink.get("signingAllowUnsigned"), bool)
        if key is not None and unsigned is not None:
            state["mavlink"] = {"key": key, "unsigned": unsigned, "appliesOnRestart": mavlink.get("appliesOnRestart") is True}
    return state


def is_locked(source: str) -> bool:
    """A value fixed by the environment of the server cannot be changed from the screen."""
    return source == "env"


def info_auth_needs_confirmation(current: bool, new: bool) -> bool:
    """Turning the sign-in requirement of the host information off asks first."""
    return current and not new


def ble_needs_confirmation(mode: str, require_encryption: bool) -> bool:
    """Commands over Bluetooth carry the access token of the account in each one: allowing them over a link that
    is not encrypted asks first."""
    return mode == "commands" and not require_encryption


def mqtt_needs_confirmation(current: str, new: str) -> bool:
    """Carrying out the commands that arrive on the broker asks first."""
    return new == "commands" and current != "commands"


def mqtt_patch(mode: str, url: str, prefix: str, username: str, command_user: str) -> dict | None:
    """The request body for the MQTT bridge; None when the mode is unknown, the address is not a broker address or commands
    are asked for without the account that carries them out. The passwords are never part of it: the server reads them from its environment."""
    address = url.strip()
    if mode not in MQTT_MODES:
        return None
    if address and not re.fullmatch(r"(?i)(mqtts?|wss?)://\S+", address):
        return None
    if mode == "commands" and not command_user.strip():
        return None
    return {"mqtt": {"mode": mode, "url": address, "prefix": prefix.strip(), "username": username.strip(), "commandUser": command_user.strip()}}


def parse_confidence(text: str) -> float | None:
    """What was typed as a confidence: a number from 0 to 1 (a comma counts as the decimal point); None otherwise."""
    cleaned = text.strip().replace(",", ".")
    if not re.fullmatch(r"\d*\.?\d+|\d+\.", cleaned):
        return None
    value = float(cleaned)
    return value if 0 <= value <= 1 else None


def voice_patch(include_heard_text: bool, min_confidence: str) -> dict | None:
    """The request body for the voice options; None when the confidence is not a number from 0 to 1 (empty is not 0)."""
    value = parse_confidence(min_confidence)
    if value is None:
        return None
    return {"voice": {"includeHeardText": bool(include_heard_text), "minConfidence": value}}


def voice_needs_confirmation(current_heard: bool, current_confidence: float, patch: dict) -> bool:
    """Showing what was said, or switching the confidence check off, lowers the protection of the voice commands: ask first."""
    new = patch["voice"]
    return (not current_heard and new["includeHeardText"]) or (current_confidence > 0 and new["minConfidence"] == 0)


def robots_patch(allow_enable: bool) -> dict:
    """The request body for the option that lets a client bring a robot in safe mode back (off by default)."""
    return {"robots": {"allowEnable": bool(allow_enable)}}


def health_patch(open_: bool) -> dict:
    """The request body for the option that lets anyone on the network read GET /health without signing in (off by default)."""
    return {"health": {"open": bool(open_)}}


def health_needs_confirmation(current_open: bool, new_open: bool) -> bool:
    """Opening the health route to clients that are not signed in widens what the network can read: ask first. Closing it never asks."""
    return (not current_open) and bool(new_open)


def safety_patch(publish_global_stop: bool) -> dict:
    """The request body for the option that announces a global stop on the MQTT bridge (off by default; announcing a stop never asks)."""
    return {"safety": {"publishGlobalStop": bool(publish_global_stop)}}


def connections_patch(record_address: bool) -> dict:
    """The request body for the option that keeps the address and user agent of each client in the history of connections (off by default)."""
    return {"connections": {"recordAddress": bool(record_address)}}


def connections_needs_confirmation(current: bool, new: bool) -> bool:
    """Keeping the address of the clients stores personal data: ask first. Turning it off never asks."""
    return (not current) and bool(new)


def exposure_patch(current: dict, new: dict) -> dict | None:
    """The request body for the exposure options: only what changed (an option fixed by the server environment must not be sent
    again); None when nothing changed or a value is missing."""
    body: dict = {}
    for name, (section, key) in EXPOSURE_FIELDS.items():
        if name not in current or name not in new:
            return None
        if bool(current[name]) != bool(new[name]):
            body.setdefault(section, {})[key] = bool(new[name])
    return body or None


def exposure_needs_confirmation(current: dict, new: dict) -> bool:
    """Opening the camera pictures, accepting a token in the WebSocket address, writing secrets in the log or dropping the signature
    of a spoken confirmation lowers the protection: ask first. The other direction never asks."""
    return bool(
        (not current["cameraOpen"] and new["cameraOpen"])
        or (not current["wsQueryToken"] and new["wsQueryToken"])
        or (current["logRedaction"] and not new["logRedaction"])
        or (current["voiceSignature"] and not new["voiceSignature"])
    )


def install_patch(current: dict, new: dict) -> dict | None:
    """The request body for the installation options: only what changed (an option fixed by the server environment must not be sent
    again); None when nothing changed or a value is missing."""
    body: dict = {}
    for name, (section, key) in INSTALL_FIELDS.items():
        if name not in current or name not in new:
            return None
        if bool(current[name]) != bool(new[name]):
            body.setdefault(section, {})[key] = bool(new[name])
    return body or None


def install_needs_confirmation(current: dict, new: dict) -> bool:
    """Putting a camera password on a command line, or taking TLS away from a new installation, lowers the protection: ask first.
    The other direction never asks."""
    return bool((current["cameraCredentialsViaEnv"] and not new["cameraCredentialsViaEnv"]) or (current["newInstallTls"] and not new["newInstallTls"]))


def robots_needs_confirmation(current_allow: bool, new_allow: bool) -> bool:
    """Allowing a client to enable a robot lowers the protection of safe mode: ask first. Turning it off never asks."""
    return not current_allow and bool(new_allow)


def mavlink_patch(signing_key_file: str, allow_unsigned: bool) -> dict:
    """The request body for the MAVLink signing options: only the path of the key file travels, never the key."""
    return {"mavlink": {"signingKeyFile": signing_key_file.strip(), "signingAllowUnsigned": bool(allow_unsigned)}}


def mavlink_needs_confirmation(current_signing: bool, current_unsigned: bool, patch: dict) -> bool:
    """Switching signing off, or accepting unsigned messages while it is on, leaves the link to the vehicle open: ask first."""
    new = patch["mavlink"]
    signing = new["signingKeyFile"] != ""
    return (current_signing and not signing) or (signing and new["signingAllowUnsigned"] and not current_unsigned)


def tls_patch(enabled: bool, cert_path: str, key_path: str) -> dict | None:
    cert, key = cert_path.strip(), key_path.strip()
    if enabled and (not cert or not key):
        return None
    return {"tls": {"enabled": enabled, "certPath": cert, "keyPath": key}}


def ble_patch(mode: str, require_encryption: bool) -> dict | None:
    if mode not in BLE_MODES:
        return None
    return {"ble": {"mode": mode, "requireEncryption": bool(require_encryption)}}


def known_warning(warnings: object) -> str:
    """The sentence for the warning of a PUT answer that this screen knows ("" when there is none)."""
    if not isinstance(warnings, list):
        return ""
    sentence = ""
    if "info_auth_off" in warnings:
        sentence = _("SECURITY_INFO_OFF_WARNING")
    if "ble_commands_unencrypted" in warnings:
        sentence = _("SECURITY_BLE_UNENCRYPTED_WARNING")
    if "mqtt_commands_on" in warnings:
        sentence = _("SECURITY_MQTT_COMMANDS_WARNING")
    if "voice_heard_text_on" in warnings:
        sentence = _("SECURITY_VOICE_HEARD_WARNING")
    if "voice_confidence_off" in warnings:
        sentence = _("SECURITY_VOICE_CONFIDENCE_WARNING")
    if "robot_enable_allowed" in warnings:
        sentence = _("SECURITY_ROBOTS_WARNING")
    if "health_open" in warnings:
        sentence = _("SECURITY_HEALTH_WARNING")
    if "connection_address_recorded" in warnings:
        sentence = _("SECURITY_CONNECTIONS_WARNING")
    if "camera_open" in warnings:
        sentence = _("SECURITY_EXPOSURE_CAMERA_WARNING")
    if "ws_query_token_allowed" in warnings:
        sentence = _("SECURITY_EXPOSURE_WS_WARNING")
    if "log_redaction_off" in warnings:
        sentence = _("SECURITY_EXPOSURE_LOG_WARNING")
    if "camera_credentials_in_arguments" in warnings:
        sentence = _("SECURITY_INSTALL_CAMERA_WARNING")
    if "new_install_tls_off" in warnings:
        sentence = _("SECURITY_INSTALL_TLS_WARNING")
    if "mavlink_unsigned_allowed" in warnings:
        sentence = _("SECURITY_MAVLINK_UNSIGNED_WARNING")
    if "mavlink_signing_off" in warnings:
        sentence = _("SECURITY_MAVLINK_OFF_WARNING")
    return sentence


def source_text(source: str) -> str:
    return _("SECURITY_SOURCE_" + source.upper())


#: Every key the screen reads, with a value that shows nothing: the screen binds to all of them before any server answered.
EMPTY_VIEW: dict = {
    "available": False,
    "aiValue": "open", "aiLocked": False, "aiSource": "",
    "infoValue": False, "infoLocked": False, "infoSource": "",
    "tlsEnabled": False, "tlsLocked": False, "tlsSource": "", "tlsCert": "", "tlsKey": "", "tlsFingerprint": "-", "tlsStatus": "",
    "bleAvailable": False, "bleMode": "off", "bleModeLocked": False, "bleModeSource": "",
    "bleEncryption": True, "bleEncryptionLocked": False, "bleEncryptionSource": "", "bleRunning": "",
    "mqttAvailable": False, "mqttMode": "off", "mqttModeLocked": False, "mqttModeSource": "", "mqttUrl": "", "mqttPrefix": "",
    "mqttUser": "", "mqttCommandUser": "", "mqttRunning": "",
    "voiceAvailable": False, "voiceHeard": False, "voiceHeardLocked": False, "voiceHeardSource": "",
    "voiceConfidence": "0.6", "voiceConfidenceLocked": False, "voiceConfidenceSource": "",
    "robotsAvailable": False, "robotsAllowEnable": False, "robotsAllowEnableLocked": False, "robotsAllowEnableSource": "",
    "healthAvailable": False, "healthOpen": False, "healthOpenLocked": False, "healthOpenSource": "",
    "safetyAvailable": False, "safetyPublishStop": False, "safetyPublishStopLocked": False, "safetyPublishStopSource": "",
    "connectionsAvailable": False, "connectionsRecord": False, "connectionsRecordLocked": False, "connectionsRecordSource": "",
    "exposureAvailable": False,
    "exposureCameraOpen": False, "exposureCameraOpenLocked": False, "exposureCameraOpenSource": "",
    "exposureWsQueryToken": False, "exposureWsQueryTokenLocked": False, "exposureWsQueryTokenSource": "",
    "exposureLogRedaction": True, "exposureLogRedactionLocked": False, "exposureLogRedactionSource": "",
    "exposureVoiceSignature": False, "exposureVoiceSignatureLocked": False, "exposureVoiceSignatureSource": "",
    "installAvailable": False,
    "installCameraCredentialsViaEnv": True, "installCameraCredentialsViaEnvLocked": False, "installCameraCredentialsViaEnvSource": "",
    "installNewInstallTls": True, "installNewInstallTlsLocked": False, "installNewInstallTlsSource": "",
    "mavlinkAvailable": False, "mavlinkKey": "", "mavlinkKeyLocked": False, "mavlinkKeySource": "",
    "mavlinkUnsigned": False, "mavlinkUnsignedLocked": False, "mavlinkUnsignedSource": "", "mavlinkStatus": "",
}


def view(state: dict | None) -> dict:
    """What the screen shows, with the sentences already in the language of the interface."""
    if state is None:
        return dict(EMPTY_VIEW)
    tls = state["tls"]
    status = _("SECURITY_TLS_ACTIVE") if tls["active"] else _("SECURITY_TLS_INACTIVE")
    if tls["appliesOnRestart"]:
        status += " " + _("SECURITY_RESTART_NOTE")
    out: dict = {
        **EMPTY_VIEW,
        "available": True,
        "aiValue": state["ai"]["value"],
        "aiLocked": is_locked(state["ai"]["source"]),
        "aiSource": source_text(state["ai"]["source"]),
        "infoValue": state["info"]["value"],
        "infoLocked": is_locked(state["info"]["source"]),
        "infoSource": source_text(state["info"]["source"]),
        "tlsEnabled": tls["enabled"],
        "tlsLocked": is_locked(tls["source"]),
        "tlsSource": source_text(tls["source"]),
        "tlsCert": tls["certPath"],
        "tlsKey": tls["keyPath"],
        "tlsFingerprint": tls["fingerprint"] or "-",
        "tlsStatus": status,
        "bleAvailable": state["ble"] is not None,
    }
    ble = state["ble"]
    if ble is not None:
        running = _("SECURITY_BLE_RUNNING", mode=_("SECURITY_BLE_" + ble["activeMode"].upper()))
        if ble["appliesOnRestart"]:
            running += " " + _("SECURITY_RESTART_NOTE")
        out.update(
            {
                "bleMode": ble["mode"]["value"],
                "bleModeLocked": is_locked(ble["mode"]["source"]),
                "bleModeSource": source_text(ble["mode"]["source"]),
                "bleEncryption": ble["encryption"]["value"],
                "bleEncryptionLocked": is_locked(ble["encryption"]["source"]),
                "bleEncryptionSource": source_text(ble["encryption"]["source"]),
                "bleRunning": running,
            }
        )
    mqtt = state.get("mqtt")
    if mqtt is not None:
        running = _("SECURITY_MQTT_RUNNING", mode=_("SECURITY_MQTT_" + mqtt["activeMode"].upper()))
        if mqtt["appliesOnRestart"]:
            running += " " + _("SECURITY_RESTART_NOTE")
        out.update(
            {
                "mqttAvailable": True,
                "mqttMode": mqtt["mode"]["value"],
                "mqttModeLocked": is_locked(mqtt["mode"]["source"]),
                "mqttModeSource": source_text(mqtt["mode"]["source"]),
                "mqttUrl": mqtt["url"],
                "mqttPrefix": mqtt["prefix"],
                "mqttUser": mqtt["username"],
                "mqttCommandUser": mqtt["commandUser"],
                "mqttRunning": running,
            }
        )
    voice = state.get("voice")
    if voice is not None:
        out.update(
            {
                "voiceAvailable": True,
                "voiceHeard": voice["heard"]["value"],
                "voiceHeardLocked": is_locked(voice["heard"]["source"]),
                "voiceHeardSource": source_text(voice["heard"]["source"]),
                "voiceConfidence": f"{voice['confidence']['value']:g}",
                "voiceConfidenceLocked": is_locked(voice["confidence"]["source"]),
                "voiceConfidenceSource": source_text(voice["confidence"]["source"]),
            }
        )
    robots = state.get("robots")
    if robots is not None:
        out.update(
            {
                "robotsAvailable": True,
                "robotsAllowEnable": robots["allowEnable"]["value"],
                "robotsAllowEnableLocked": is_locked(robots["allowEnable"]["source"]),
                "robotsAllowEnableSource": source_text(robots["allowEnable"]["source"]),
            }
        )
    health = state.get("health")
    if health is not None:
        out.update(
            {
                "healthAvailable": True,
                "healthOpen": health["open"]["value"],
                "healthOpenLocked": is_locked(health["open"]["source"]),
                "healthOpenSource": source_text(health["open"]["source"]),
            }
        )
    safety = state.get("safety")
    if safety is not None:
        out.update(
            {
                "safetyAvailable": True,
                "safetyPublishStop": safety["publishGlobalStop"]["value"],
                "safetyPublishStopLocked": is_locked(safety["publishGlobalStop"]["source"]),
                "safetyPublishStopSource": source_text(safety["publishGlobalStop"]["source"]),
            }
        )
    connections = state.get("connections")
    if connections is not None:
        out.update(
            {
                "connectionsAvailable": True,
                "connectionsRecord": connections["recordAddress"]["value"],
                "connectionsRecordLocked": is_locked(connections["recordAddress"]["source"]),
                "connectionsRecordSource": source_text(connections["recordAddress"]["source"]),
            }
        )
    exposure = state.get("exposure")
    if exposure is not None:
        out["exposureAvailable"] = True
        for name, option in exposure.items():
            suffix = name[0].upper() + name[1:]
            out.update(
                {
                    "exposure" + suffix: option["value"],
                    "exposure" + suffix + "Locked": is_locked(option["source"]),
                    "exposure" + suffix + "Source": source_text(option["source"]),
                }
            )
    install = state.get("install")
    if install is not None:
        out["installAvailable"] = True
        for name, option in install.items():
            suffix = name[0].upper() + name[1:]
            out.update(
                {
                    "install" + suffix: option["value"],
                    "install" + suffix + "Locked": is_locked(option["source"]),
                    "install" + suffix + "Source": source_text(option["source"]),
                }
            )
    mavlink = state.get("mavlink")
    if mavlink is not None:
        status = _("SECURITY_MAVLINK_SIGNING_ON") if mavlink["key"]["value"] else _("SECURITY_MAVLINK_SIGNING_OFF")
        if mavlink["appliesOnRestart"]:
            status += " " + _("SECURITY_RESTART_NOTE")
        out.update(
            {
                "mavlinkAvailable": True,
                "mavlinkKey": mavlink["key"]["value"],
                "mavlinkKeyLocked": is_locked(mavlink["key"]["source"]),
                "mavlinkKeySource": source_text(mavlink["key"]["source"]),
                "mavlinkUnsigned": mavlink["unsigned"]["value"],
                "mavlinkUnsignedLocked": is_locked(mavlink["unsigned"]["source"]),
                "mavlinkUnsignedSource": source_text(mavlink["unsigned"]["source"]),
                "mavlinkStatus": status,
            }
        )
    return out


def mqtt_mode_options() -> list[dict[str, str]]:
    return [{"value": mode, "label": _("SECURITY_MQTT_" + mode.upper())} for mode in MQTT_MODES]


def ble_mode_options() -> list[dict[str, str]]:
    return [{"value": mode, "label": _("SECURITY_BLE_" + mode.upper())} for mode in BLE_MODES]


def ai_options() -> list[dict[str, str]]:
    return [{"value": "open", "label": _("SECURITY_AI_OPEN")}, {"value": "admin", "label": _("SECURITY_AI_ADMIN")}]
