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
JWT_ALGORITHMS = ("HS256", "EdDSA")
MQTT_MODES = ("off", "state", "commands")

#: The language-file key of the label of each switch of the machine bridges (`bridge.option`), and of the words of a choice.
BRIDGE_OPTION_TEXT = {
    "droids.globalStop": "LBL_SECURITY_BRIDGES_OPT_DROIDS_GLOBAL_STOP",
    "droids.cutOnGlobalStop": "LBL_SECURITY_BRIDGES_OPT_DROIDS_CUT",
    "uav.missionUploadEnabled": "LBL_SECURITY_BRIDGES_OPT_UAV_MISSION",
    "amr.publishState": "LBL_SECURITY_BRIDGES_OPT_AMR_STATE",
    "amr.publishOpcua": "LBL_SECURITY_BRIDGES_OPT_AMR_OPCUA",
    "amr.zoneInterlock": "LBL_SECURITY_BRIDGES_OPT_AMR_INTERLOCK",
    "amr.zoneUnknown": "LBL_SECURITY_BRIDGES_OPT_AMR_UNKNOWN",
    "openpnp.boardCode": "LBL_SECURITY_BRIDGES_OPT_OPENPNP_BOARD",
}
BRIDGE_CHOICE_TEXT = {
    "pause": "LBL_SECURITY_BRIDGES_CHOICE_PAUSE",
    "ignore": "LBL_SECURITY_BRIDGES_CHOICE_IGNORE",
    "off": "LBL_SECURITY_BRIDGES_CHOICE_OFF",
    "advisory": "LBL_SECURITY_BRIDGES_CHOICE_ADVISORY",
    "required": "LBL_SECURITY_BRIDGES_CHOICE_REQUIRED",
}


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


def _bridge_scalar(value: object) -> bool:
    return isinstance(value, (bool, str))


def _bridges(raw: object) -> dict | None:
    """The switches of the machine bridges as the server reports them; None for a server that predates them or reports one damaged."""
    if not isinstance(raw, dict) or raw.get("delivery") not in ("gateway_on", "gateway_off"):
        return None
    options = []
    for bridge, body in raw.items():
        if bridge == "delivery":
            continue
        if not isinstance(body, dict):
            return None
        for key, entry in body.items():
            if not isinstance(entry, dict):
                return None
            risky, choices = entry.get("risky"), entry.get("choices")
            if (
                not _bridge_scalar(entry.get("value")) or not _bridge_scalar(entry.get("default"))
                or entry.get("source") not in ("config", "default") or not isinstance(risky, list)
                or not all(_bridge_scalar(item) for item in risky) or not isinstance(entry.get("localName"), str)
            ):
                return None
            options.append({
                "id": f"{bridge}.{key}", "bridge": bridge, "key": key, "value": entry["value"], "source": entry["source"],
                "default": entry["default"], "risky": risky, "localName": entry["localName"],
                "choices": choices if isinstance(choices, list) and all(isinstance(c, str) for c in choices) else None,
            })
    return {"delivery": raw["delivery"], "options": options} if options else None


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


#: What came of the last request to the job dispatcher to read its file again. "none": nothing asked yet (no chip).
RELOAD_STATES: tuple[str, ...] = ("none", "pending", "applied", "failed", "not_configured")


def parse_dispatcher_reload(raw: object) -> str:
    """The state the server reports, or "none" when it predates the field or sends something unknown."""
    return raw if isinstance(raw, str) and raw in RELOAD_STATES else "none"


def _job_dispatcher(raw: object) -> dict | None:
    """The options of the job dispatcher in the answer of the server; None for a server that predates them or answers nonsense."""
    if not isinstance(raw, dict):
        return None
    relay, replan = raw.get("stopRelay"), raw.get("replan")
    if not isinstance(relay, dict) or not isinstance(replan, dict):
        return None
    enabled = _option(relay.get("enabled"), bool)
    allow = _option(replan.get("allowUnconfirmed"), bool)
    timeout = _option(replan.get("stopAckTimeoutSeconds"), (int, float))
    if enabled is None or allow is None or timeout is None:
        return None
    robot_map: dict[str, int] = {}
    raw_map = relay.get("robotMap")
    if isinstance(raw_map, dict):
        for dispatcher_id, number in raw_map.items():
            if isinstance(dispatcher_id, str) and isinstance(number, int) and not isinstance(number, bool):
                robot_map[dispatcher_id] = number
    return {
        "relay": enabled,
        "robotMap": robot_map,
        "relayAppliesOnRestart": relay.get("appliesOnRestart") is True,
        "allow": allow,
        "timeout": timeout,
        "editable": replan.get("editable") is True,
        "reload": parse_dispatcher_reload(replan.get("reload")),
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
        "auth": None,
        "health": None,
        "ecosystemHealth": None,
        "trustedNetworks": None,
        "rul": None,
        "safety": None,
        "jobDispatcher": None,
        "connections": None,
        "exposure": None,
        "install": None,
        "mavlink": None,
        "bridges": _bridges(body.get("bridges")),
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
    auth = body.get("auth")
    if isinstance(auth, dict):
        algorithm = _option(auth.get("jwtAlgorithm"), str, JWT_ALGORITHMS)
        accept = _option(auth.get("acceptHs256"), bool)
        if algorithm is not None and accept is not None:
            state["auth"] = {"jwtAlgorithm": algorithm, "acceptHs256": accept}
    health = body.get("health")
    if isinstance(health, dict):
        opened = _option(health.get("open"), bool)
        if opened is not None:
            state["health"] = {"open": opened}
    ecosystem_health = body.get("ecosystemHealth")
    if isinstance(ecosystem_health, dict):
        enabled = _option(ecosystem_health.get("enabled"), bool)
        if enabled is not None:
            state["ecosystemHealth"] = {"enabled": enabled}
    trusted = body.get("trustedNetworks")
    if isinstance(trusted, dict):
        trusted_enabled = _option(trusted.get("enabled"), bool)
        if trusted_enabled is not None:
            state["trustedNetworks"] = {"enabled": trusted_enabled}
    rul = body.get("rul")
    if isinstance(rul, dict):
        rul_enabled = _option(rul.get("enabled"), bool)
        if rul_enabled is not None:
            state["rul"] = {"enabled": rul_enabled}
    safety = body.get("safety")
    if isinstance(safety, dict):
        publish = _option(safety.get("publishGlobalStop"), bool)
        if publish is not None:
            state["safety"] = {"publishGlobalStop": publish}
    job_dispatcher = _job_dispatcher(body.get("jobDispatcher"))
    if job_dispatcher is not None:
        state["jobDispatcher"] = job_dispatcher
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


def auth_patch(algorithm: str | None = None, accept_hs256: bool | None = None) -> dict | None:
    """The request body for how the sign-in tokens are signed (HS256 by default) and whether HS256 tokens are still accepted while
    EdDSA is in use (yes by default). Only what is given is sent; None when the algorithm is not one the server offers."""
    if algorithm is not None and algorithm not in JWT_ALGORITHMS:
        return None
    auth: dict = {}
    if algorithm is not None:
        auth["jwtAlgorithm"] = algorithm
    if accept_hs256 is not None:
        auth["acceptHs256"] = bool(accept_hs256)
    return {"auth": auth}


def auth_needs_confirmation(current_accept: bool, new_accept: bool) -> bool:
    """Refusing HS256 tokens signs out every session that still holds one: ask first. Accepting them again never asks."""
    return bool(current_accept) and not new_accept


def health_patch(open_: bool) -> dict:
    """The request body for the option that lets anyone on the network read GET /health without signing in (off by default)."""
    return {"health": {"open": bool(open_)}}


def health_needs_confirmation(current_open: bool, new_open: bool) -> bool:
    """Opening the health route to clients that are not signed in widens what the network can read: ask first. Closing it never asks."""
    return (not current_open) and bool(new_open)


def rul_patch(enabled: bool) -> dict:
    """The request body for the option that lets operators ask the anomaly detector for a remaining-useful-life estimate through the
    relay (off by default: only an administrator may then). Turning it on never asks: only that one request is opened, with a limit on its
    size and time, and every other write to the detector stays for administrators."""
    return {"rul": {"enabled": bool(enabled)}}


def trusted_networks_patch(enabled: bool) -> dict:
    """The request body for the option that refuses to administer the server from outside the house network and the VPN (off by default).
    The ranges, the policy for the outside and the second-factor rule are edited in the configuration file of the server, not here."""
    return {"trustedNetworks": {"enabled": bool(enabled)}}


def ecosystem_health_patch(enabled: bool) -> dict:
    """The request body for the option that lets operators and administrators read GET /api/ecosystem/health (off by default). Turning
    it on never asks: the route is read only and shows no port, address or unit to anyone but an administrator."""
    return {"ecosystemHealth": {"enabled": bool(enabled)}}


MAX_STOP_ACK_TIMEOUT_SECONDS = 86400
_DISPATCHER_ROBOT_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")


def robot_map_text(robot_map: dict) -> str:
    """The robot map as text, one `id = number` per line, in the order of the ids."""
    return "\n".join(f"{dispatcher_id} = {robot_map[dispatcher_id]}" for dispatcher_id in sorted(robot_map))


def parse_robot_map_text(text: str) -> dict | None:
    """The text back to a map; None when a line is not `id = number`, an id is not valid, a number is not a whole number of 0 or more or an id repeats."""
    result: dict[str, int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([^=\s]+)\s*=\s*(\d+)", line)
        if match is None or _DISPATCHER_ROBOT_ID.fullmatch(match.group(1)) is None or match.group(1) in result:
            return None
        result[match.group(1)] = int(match.group(2))
    return result if len(result) <= 1000 else None


def parse_timeout(text: str) -> float | None:
    """What was typed as the wait for the confirmed stop: a number greater than 0 and at most 86400 (a comma counts as the decimal point); None otherwise."""
    cleaned = text.strip().replace(",", ".")
    if not re.fullmatch(r"\d*\.?\d+|\d+\.", cleaned):
        return None
    value = float(cleaned)
    return value if 0 < value <= MAX_STOP_ACK_TIMEOUT_SECONDS else None


def job_dispatcher_patch(relay_enabled: bool, map_text: str, replan_editable: bool, allow_unconfirmed: bool, timeout_text: str) -> dict | None:
    """The request body for the job dispatcher options; None when the robot map or the wait is not valid. The replanning part is left out when the server cannot write the file of the dispatcher."""
    robot_map = parse_robot_map_text(map_text)
    if robot_map is None:
        return None
    body: dict = {"stopRelay": {"enabled": bool(relay_enabled), "robotMap": robot_map}}
    if replan_editable:
        seconds = parse_timeout(timeout_text)
        if seconds is None:
            return None
        body["replan"] = {"allowUnconfirmed": bool(allow_unconfirmed), "stopAckTimeoutSeconds": seconds}
    return {"jobDispatcher": body}


def job_dispatcher_needs_confirmation(current: dict, patch: dict) -> bool:
    """Switching the delivery on, or letting a job go to another robot without a confirmed stop, asks first."""
    new = patch["jobDispatcher"]
    relay_on = not current["relay"]["value"] and new["stopRelay"]["enabled"]
    unconfirmed = "replan" in new and not current["allow"]["value"] and new["replan"]["allowUnconfirmed"]
    return bool(relay_on or unconfirmed)


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
    if "jwt_eddsa_on" in warnings:
        sentence = _("SECURITY_AUTH_EDDSA_WARNING")
    if "jwt_hs256_refused" in warnings:
        sentence = _("SECURITY_AUTH_HS256_REFUSED_WARNING")
    if "trusted_networks_on" in warnings:
        sentence = _("SECURITY_TRUSTED_WARNING")
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
    if "job_stop_relay_on" in warnings:
        sentence = _("SECURITY_JD_WARNING_RELAY")
    if "replan_unconfirmed_allowed" in warnings:
        sentence = _("SECURITY_JD_WARNING_REPLAN")
    if "mavlink_unsigned_allowed" in warnings:
        sentence = _("SECURITY_MAVLINK_UNSIGNED_WARNING")
    if "mavlink_signing_off" in warnings:
        sentence = _("SECURITY_MAVLINK_OFF_WARNING")
    if any(isinstance(item, str) and item.startswith("bridge_") for item in warnings):
        sentence = _("SECURITY_BRIDGES_WARNING")
    return sentence


def _bridge_word(value: object) -> str:
    if isinstance(value, bool):
        return _("SECURITY_BRIDGES_ON") if value else _("SECURITY_BRIDGES_OFF")
    return _(BRIDGE_CHOICE_TEXT.get(str(value), "LBL_SECURITY_BRIDGES_CHOICE_OFF"))


def _bridge_option_view(option: dict) -> dict:
    """One row of the list: its label, the current value, the words to choose from, and the origin, default and local name in plain text."""
    choices = [{"label": _bridge_word(c), "value": c} for c in option["choices"]] if option["choices"] else []
    return {
        "id": option["id"],
        "bridge": "BRIDGE-" + option["bridge"].upper(),
        "label": _(BRIDGE_OPTION_TEXT.get(option["id"], "LBL_SECURITY_BRIDGES")),
        "isChoice": bool(choices),
        "value": option["value"],
        "choices": choices,
        "note": f'{source_text(option["source"])} - {_("LBL_SECURITY_BRIDGES_DEFAULT")}: {_bridge_word(option["default"])} - {_("LBL_SECURITY_BRIDGES_LOCAL")}: {option["localName"]}',
    }


def bridges_patch(state: dict, values: object) -> dict | None:
    """Only what differs from what the server reports; None when nothing does or the values are not the shape of the switches."""
    if not isinstance(values, dict):
        return None
    body: dict = {}
    for option in state["bridges"]["options"]:
        new = values.get(option["id"])
        if new is None or type(new) is not type(option["value"]) or new == option["value"]:
            continue
        if option["choices"] is not None and new not in option["choices"]:
            return None
        body.setdefault(option["bridge"], {})[option["key"]] = new
    return {"bridges": body} if body else None


def bridges_needs_confirmation(state: dict, patch: dict) -> bool:
    """Turning on a function that moves hardware, or taking a protection away, is asked about first."""
    for option in state["bridges"]["options"]:
        new = patch.get("bridges", {}).get(option["bridge"], {}).get(option["key"])
        if new is not None and any(type(new) is type(risky) and new == risky for risky in option["risky"]):
            return True
    return False


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
    "authAvailable": False, "authAlgorithm": "HS256", "authAlgorithmLocked": False, "authAlgorithmSource": "",
    "authAcceptHs256": True, "authAcceptHs256Locked": False, "authAcceptHs256Source": "",
    "healthAvailable": False, "healthOpen": False, "healthOpenLocked": False, "healthOpenSource": "",
    "trustedNetworksAvailable": False, "trustedNetworksEnabled": False, "trustedNetworksEnabledLocked": False, "trustedNetworksEnabledSource": "",
    "ecosystemHealthAvailable": False, "ecosystemHealthEnabled": False, "ecosystemHealthEnabledLocked": False, "ecosystemHealthEnabledSource": "",
    "rulAvailable": False, "rulEnabled": False, "rulEnabledLocked": False, "rulEnabledSource": "",
    "safetyAvailable": False, "safetyPublishStop": False, "safetyPublishStopLocked": False, "safetyPublishStopSource": "",
    "jdAvailable": False, "jdRelay": False, "jdRelayLocked": False, "jdRelaySource": "", "jdMapText": "", "jdAllow": False, "jdTimeout": "30",
    "jdReplanEditable": False, "jdReplanNote": "",
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
    "bridgesAvailable": False, "bridgesDelivery": "", "bridgesOptions": [],
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
    auth = state.get("auth")
    if auth is not None:
        out.update(
            {
                "authAvailable": True,
                "authAlgorithm": auth["jwtAlgorithm"]["value"],
                "authAlgorithmLocked": is_locked(auth["jwtAlgorithm"]["source"]),
                "authAlgorithmSource": source_text(auth["jwtAlgorithm"]["source"]),
                "authAcceptHs256": auth["acceptHs256"]["value"],
                "authAcceptHs256Locked": is_locked(auth["acceptHs256"]["source"]),
                "authAcceptHs256Source": source_text(auth["acceptHs256"]["source"]),
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
    ecosystem_health = state.get("ecosystemHealth")
    if ecosystem_health is not None:
        out.update(
            {
                "ecosystemHealthAvailable": True,
                "ecosystemHealthEnabled": ecosystem_health["enabled"]["value"],
                "ecosystemHealthEnabledLocked": is_locked(ecosystem_health["enabled"]["source"]),
                "ecosystemHealthEnabledSource": source_text(ecosystem_health["enabled"]["source"]),
            }
        )
    bridges = state.get("bridges")
    if bridges is not None:
        out.update(
            {
                "bridgesAvailable": True,
                "bridgesDelivery": _("SECURITY_BRIDGES_DELIVERY_ON") if bridges["delivery"] == "gateway_on" else _("SECURITY_BRIDGES_DELIVERY_OFF"),
                "bridgesOptions": [_bridge_option_view(option) for option in bridges["options"]],
            }
        )
    trusted = state.get("trustedNetworks")
    if trusted is not None:
        out.update(
            {
                "trustedNetworksAvailable": True,
                "trustedNetworksEnabled": trusted["enabled"]["value"],
                "trustedNetworksEnabledLocked": is_locked(trusted["enabled"]["source"]),
                "trustedNetworksEnabledSource": source_text(trusted["enabled"]["source"]),
            }
        )
    rul = state.get("rul")
    if rul is not None:
        out.update(
            {
                "rulAvailable": True,
                "rulEnabled": rul["enabled"]["value"],
                "rulEnabledLocked": is_locked(rul["enabled"]["source"]),
                "rulEnabledSource": source_text(rul["enabled"]["source"]),
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
    job_dispatcher = state.get("jobDispatcher")
    if job_dispatcher is not None:
        out.update(
            {
                "jdAvailable": True,
                "jdRelay": job_dispatcher["relay"]["value"],
                "jdRelayLocked": is_locked(job_dispatcher["relay"]["source"]),
                "jdRelaySource": source_text(job_dispatcher["relay"]["source"]) + (" " + _("SECURITY_RESTART_NOTE") if job_dispatcher["relayAppliesOnRestart"] else ""),
                "jdMapText": robot_map_text(job_dispatcher["robotMap"]),
                "jdAllow": job_dispatcher["allow"]["value"],
                "jdTimeout": f"{job_dispatcher['timeout']['value']:g}",
                "jdReplanEditable": job_dispatcher["editable"],
                "jdReplanNote": _("LBL_SECURITY_JD_REPLAN_HELP") if job_dispatcher["editable"] else _("LBL_SECURITY_JD_NOT_EDITABLE"),
                "jdReloadState": job_dispatcher["reload"],
                "jdReloadText": "" if job_dispatcher["reload"] == "none" else _("LBL_JD_RELOAD") + ": " + _("LBL_JD_RELOAD_" + job_dispatcher["reload"].upper()),
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
