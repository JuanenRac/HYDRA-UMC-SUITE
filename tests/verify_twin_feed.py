# =============================================================================
# HYDRA-UMC SUITE - tests/verify_twin_feed.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the live state of the twin read through the server: watching is off by default and a damaged configuration never switches it on,
# how a frame is read, a late state is dropped, a simulation is never taken for the real robot, what a close code means, what the screen shows, the address and
# subprotocol of the relay, that nothing is ever sent to the twin, and that every sentence exists in all eight languages with the same placeholders.
# =============================================================================
import inspect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.models import ServerInfo
from hydra_suite.net import client as client_module
from hydra_suite.panel_logic import twin_feed as tf

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def state_frame(**extra):
    state = {"schema_version": "1.0", "source": "real", "robot_id": "r1", "frame": "base", "timestamp_utc": "2026-01-01T00:00:00Z", "sequence": 5,
             "joint_states": [{"name": "j1", "position": 0}, {"name": "j2", "position": 1}]}
    state.update(extra)
    return json.dumps({"type": "twin_state", "state": state})


check("off by default, and for a damaged configuration", (tf.watching_from_config({}), tf.watching_from_config(None), tf.watching_from_config({"twin_feed": "yes"}), tf.watching_from_config({"twin_feed": 1})), (False, False, False, False))
check("only a stored True switches it on", (tf.watching_from_config({"twin_feed": True}), tf.config_update(True), tf.config_update(False)), (True, {"twin_feed": True}, {"twin_feed": False}))

check("a state is read", tf.parse_frame(state_frame()), {"kind": "state", "source": "real", "robot_id": "r1", "joints": 2, "sequence": 5})
check("a notice, a vehicle state and a vehicle notice are read", (
    tf.parse_frame(json.dumps({"type": "status", "code": "incomplete", "message": "x", "missing": ["j2"]})),
    tf.parse_frame(json.dumps({"type": "uav_state", "state": {"robot_id": "u1"}})),
    tf.parse_frame(json.dumps({"type": "uav_status", "robot_id": "u1", "code": "stale"})),
    tf.parse_frame(json.dumps({"error": "Access denied"})),
), ({"kind": "status", "code": "incomplete", "message": "x"}, {"kind": "uav_state", "robot_id": "u1"}, {"kind": "uav_status", "robot_id": "u1", "code": "stale"}, {"kind": "error", "message": "Access denied"}))
for label, raw in {
    "not JSON": "not json", "a list": "[]", "null": "null", "another kind": json.dumps({"type": "other"}),
    "a source that is neither": json.dumps({"type": "twin_state", "state": {"source": "guess", "joint_states": []}}),
    "joints missing": json.dumps({"type": "twin_state", "state": {"source": "real"}}), "a notice with no code": json.dumps({"type": "status"}),
    "a vehicle notice with a number as id": json.dumps({"type": "uav_status", "robot_id": 3, "code": "x"}), "bytes": b"\xff\xfe",
}.items():
    check(f"nothing from {label}", tf.parse_frame(raw), None)
check("a sequence that is not a whole non-negative number is none", (tf.parse_frame(state_frame(sequence=-1))["sequence"], tf.parse_frame(state_frame(sequence=1.5))["sequence"], tf.parse_frame(state_frame(sequence=True))["sequence"]), (None, None, None))

feed = tf.apply_frame(tf.empty_state(), tf.parse_frame(state_frame()))
check("the state is built", (feed["source"], feed["joints"], feed["sequence"], feed["status"], feed["frames"]), ("real", 2, 5, None, 1))
check("a late state is dropped and the state given is not changed", (tf.apply_frame(feed, tf.parse_frame(state_frame(sequence=4))) is feed, feed["sequence"]), (True, 5))
feed2 = tf.apply_frame(feed, tf.parse_frame(state_frame(source="simulated", sequence=6)))
check("a simulation is never taken for the real robot", feed2["source"], "simulated")
feed3 = tf.apply_frame(feed2, {"kind": "status", "code": "incomplete", "message": None})
check("a notice stays until a state arrives", (feed3["status"], tf.apply_frame(feed3, tf.parse_frame(state_frame(sequence=7)))["status"]), ({"code": "incomplete", "message": None}, None))
feed4 = tf.apply_frame(feed3, {"kind": "uav_status", "robot_id": "u1", "code": "stale"})
check("a vehicle is stale until its state arrives", (feed4["vehicles"], tf.apply_frame(feed4, {"kind": "uav_state", "robot_id": "u1"})["vehicles"]), ({"u1": {"stale": True}}, {"u1": {"stale": False}}))
check("an error frame changes nothing", tf.apply_frame(feed, {"kind": "error", "message": "x"}) is feed, True)

check("a close code means what to do next", [tf.end_for_close_code(c) for c in (1008, 1013, 1011, 1006, 1000, None)], ["denied", "not_available", "unavailable", "closed", "closed", "closed"])
check("only an unreachable twin or an ordinary close is retried", [tf.retries(e) for e in ("denied", "not_available", "unavailable", "closed")], [False, False, True, True])

off = tf.view(False, "off", tf.empty_state())
check("off: nothing but the link line, every key present", (off["watching"], off["link"], off["state"], off["status"], off["vehicles"]), (False, _("TWINLIVE_OFF"), "", "", ""))
check("connecting and live say so", (tf.view(True, "connecting", feed)["link"], tf.view(True, "live", feed)["link"]), (_("TWINLIVE_CONNECTING"), _("TWINLIVE_LIVE")))
check("live: the real robot, a simulation and no state yet", (tf.view(True, "live", feed)["state"], tf.view(True, "live", feed2)["state"], tf.view(True, "live", tf.empty_state())["state"]),
      (_("TWINLIVE_STATE_REAL", joints=2), _("TWINLIVE_STATE_SIMULATED", joints=2), _("TWINLIVE_NO_STATE")))
check("live: the notice and the vehicles", (tf.view(True, "live", feed3)["status"], tf.view(True, "live", feed4)["vehicles"]), (_("TWINLIVE_STATUS", code="incomplete"), _("TWINLIVE_VEHICLES", count=1, stale=1)))
check("not live: no state, notice or vehicles are shown", [tf.view(True, "denied", feed4)[k] for k in ("state", "status", "vehicles")], ["", "", ""])
check("each end has its own sentence", len({tf.view(True, e, feed)["link"] for e in ("denied", "not_available", "unavailable", "closed")}), 4)

info = ServerInfo(host="192.0.2.7", port=3000, use_tls=False)
check("the relay is on the same host and port, with the token only as a subprotocol", (info.twin_ws_url(), "token" in info.twin_ws_url(), ServerInfo.ws_subprotocols("abc")), ("ws://192.0.2.7:3000/api/twin/ws", False, ["hydra.bearer", "abc"]))
check("with TLS the relay is wss", ServerInfo(host="h", port=443, use_tls=True).twin_ws_url(), "wss://h:443/api/twin/ws")
source = inspect.getsource(client_module.HydraConnection.watch_twin_feed)
check("the client never sends anything to the twin", ".send(" in source, False)

KEYS = ["TITLE", "DESC", "LABEL", "OFF", "CONNECTING", "LIVE", "DENIED", "NOT_AVAILABLE", "UNAVAILABLE", "CLOSED", "STATE_REAL", "STATE_SIMULATED", "NO_STATE", "STATUS", "VEHICLES"]
for key in KEYS:
    check(f"sentence TWINLIVE_{key} exists", _(f"TWINLIVE_{key}") != f"TWINLIVE_{key}", True)

holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = {}
for path in sorted(Path("language").glob("*.lng"), key=lambda p: (p.name != "english.lng", p.name)):
    text = path.read_text(encoding="utf-8")
    values = {}
    for key in KEYS:
        found = re.search(rf"^TWINLIVE_{key}=(.*)$", text, re.M)
        values[key] = found.group(1).strip() if found else None
    check(f"{path.name} has every sentence", [k for k, v in values.items() if not v], [])
    if path.name == "english.lng":
        english = values
    else:
        check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if values[k] and holes(values[k]) != holes(english.get(k) or "")], [])
        check(f"{path.name} translates the description", values["DESC"] != english.get("DESC"), True)

qml = Path("assets/qml/Main.qml").read_text(encoding="utf-8")
check("the screen has the box, the link line and the state, and the box calls the backend", all(token in qml for token in ('objectName: "twinFeedPanel"', 'objectName: "twinFeedBox"', 'objectName: "twinFeedLink"', "setTwinFeedWatching")), True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
