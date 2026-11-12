# =============================================================================
# HYDRA-UMC SUITE - tests/verify_stop_state.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, without any window, the one stop state read through the server (the physical emergency stop together with the global stop): how a message is read, that
# a damaged one is ignored, how several servers are summed up (a stop on any of them wins, an unknown one is never read as ready), the badge in every state, that the
# connection keeps the last state and tells whoever listens, that nothing is ever sent, and that every sentence exists in all eight languages with the same placeholders.
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
from hydra_suite.panel_logic import stop_state as ss

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def message(**over):
    body = {"schema": 1, "state": "STOPPED", "physical": "latched", "software": "ready", "physicalLinkOk": True, "source": "brain-telemetry", "changedAt": 1234}
    body.update(over)
    return {"type": "stop-state", "schema": 2, "state": body}


view = ss.parse_stop_state(message())
check("a complete message is read", view, ss.StopStateView("STOPPED", "latched", "ready", True, 1234))
check("the optional fields default", ss.parse_stop_state(message(physicalLinkOk=None, changedAt="x")), ss.StopStateView("STOPPED", "latched", "ready", None, 0))
check("a boolean is not a time", ss.parse_stop_state(message(changedAt=True)).changed_at, 0)
damaged = [None, 3, "stop-state", [], {}, {"type": "claims"}, {"type": "stop-state"}, {"type": "stop-state", "state": "STOPPED"}, {"type": "stop-state", "state": None},
           message(state="PAUSED"), message(physical="maybe"), message(software="on"), message(state=7), message(physical=None)]
check("every damaged or foreign message is ignored", [d for d in damaged if ss.parse_stop_state(d) is not None], [])

stopped = ss.StopStateView("STOPPED", "latched", "ready")
ready = ss.StopStateView("READY", "ready", "ready")
unknown = ss.StopStateView("UNKNOWN", "unknown", "ready")
check("nothing is drawn before a server has spoken", (ss.sum_up([]), ss.badge_text(None), ss.badge_tooltip(None), ss.severity(None)), (None, "", "", ""))
check("a stop on any server wins", ss.sum_up([ready, unknown, stopped]), stopped)
check("an unknown server is never read as ready", ss.sum_up([ready, unknown]), unknown)
check("ready only when every server that spoke is ready", ss.sum_up([ready, ready]), ready)
check("severities", (ss.severity(stopped), ss.severity(ready), ss.severity(unknown)), ("error", "ok", "muted"))
check("the words of the badge", (ss.badge_text(stopped), ss.badge_text(ready), ss.badge_text(unknown)), (_("STOP_STATE_STOPPED"), _("STOP_STATE_READY"), _("STOP_STATE_UNKNOWN")))
check("the three words are different", len({ss.badge_text(stopped), ss.badge_text(ready), ss.badge_text(unknown)}), 3)
tooltip = ss.badge_tooltip(ss.StopStateView("STOPPED", "unknown", "stopped"))
check("the tooltip names both stops", tooltip, _("STOP_STATE_TOOLTIP", physical=_("STOP_STATE_PHYSICAL_UNKNOWN"), software=_("STOP_STATE_SOFTWARE_STOPPED")))
check("the tooltip has no hole left", "{" in tooltip, False)

# the connection keeps the last state and tells whoever listens
connection = client_module.HydraConnection(ServerInfo(host="192.0.2.7", port=3000, use_tls=False))
heard = []
connection.stop_state_changed.connect(lambda: heard.append(1))
check("before the first message there is no state", connection.stop_state, None)
connection._handle_message(json.dumps(message()))
check("the connection keeps the state and tells", (connection.stop_state, len(heard)), (view, 1))
connection._handle_message(json.dumps(message(state="PAUSED")))
check("a damaged message leaves the last state and tells nobody", (connection.stop_state, len(heard)), (view, 1))
connection._handle_message(json.dumps(message(state="READY", physical="ready")))
check("the next one replaces it", (connection.stop_state.state, len(heard)), ("READY", 2))
source = inspect.getsource(ss)
check("the logic never sends anything", any(token in source for token in (".send(", "post(", "requests", "httpx")), False)

KEYS = ["STOPPED", "READY", "UNKNOWN", "TOOLTIP", "PHYSICAL_LATCHED", "PHYSICAL_READY", "PHYSICAL_UNKNOWN", "SOFTWARE_STOPPED", "SOFTWARE_READY"]
holes = lambda text: sorted(re.findall(r"\{\w+\}", text))
english = {}
files = sorted(Path("language").glob("*.lng"), key=lambda p: (p.name != "english.lng", p.name))
check("eight languages", len(files), 8)
for path in files:
    text = path.read_text(encoding="utf-8")
    values = {}
    for key in KEYS:
        found = re.search(rf"^STOP_STATE_{key}=(.*)$", text, re.M)
        values[key] = found.group(1).strip() if found else None
    check(f"{path.name} has every sentence", [k for k, v in values.items() if not v], [])
    if path.name == "english.lng":
        english = values
    else:
        check(f"{path.name} keeps the placeholders of English", [k for k in KEYS if values[k] and holes(values[k]) != holes(english.get(k) or "")], [])
        check(f"{path.name} translates the tooltip", values["TOOLTIP"] != english.get("TOOLTIP"), True)

qml = Path("assets/qml/Main.qml").read_text(encoding="utf-8")
check("the header has the badge, drawn only when there is a text, and it reads the backend", all(token in qml for token in ('objectName: "stopStateBadge"', 'visible: suiteBackend.stopStateText !== ""', "suiteBackend.stopStateSeverity", "suiteBackend.stopStateDetail")), True)
bridge = Path("qt_suite.py").read_text(encoding="utf-8")
check("the backend exposes the three properties", all(token in bridge for token in ("def stopStateText", "def stopStateDetail", "def stopStateSeverity")), True)

print(f"FAILURES: {failures}")
sys.exit(1 if failures else 0)
