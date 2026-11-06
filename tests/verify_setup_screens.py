# =============================================================================
# HYDRA-UMC SUITE - tests/verify_setup_screens.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Setup screens, without a window and without a network:
#   - what could not be read is "not known" and never "to do"; a damaged answer gives nothing instead of a guess
#   - the first-run checklist, its progress and its next step
#   - the sign-in security: the checks, the public state of the signing keys, the rotation guarded by a switch and a confirmation
#   - the remote access: the old combined switch, each kind of app, "close all" and the address a phone can use
#   - the push notifications: off, on without credentials, ready; never more than the state
#   - the history: the audit record only for administrators
#   - every sentence the screens show exists in the eight languages
# Run headless: no Qt is needed.
# =============================================================================
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hydra_suite.i18n import LANGUAGE_FOLDER, _
from hydra_suite.panel_logic import setup_screens as ss

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def reading():
    check("a missing answer is a network failure", ss.failure_text(None), _("SETUP_ERROR_NETWORK"))
    check("200 reads", ss.failure_text((200, {})), "")
    check("404 is an old server", ss.failure_text((404, None)), _("SETUP_ERROR_UNSUPPORTED"))
    check("403 is not allowed", ss.failure_text((403, None)), _("SETUP_ERROR_FORBIDDEN"))
    check("another status is an error of the server", ss.failure_text((500, None)), _("SETUP_ERROR_HTTP"))
    check("an answer that is not an object gives no info", ss.parse_server_info([1]), None)
    info = ss.parse_server_info({"appVersion": " 1.2.3 ", "remoteApiVersion": True, "hostname": "", "controllerCount": -1, "robotCount": 2, "uptimeSeconds": 90061})
    check("the info is cleaned", (info["appVersion"], info["remoteApiVersion"], info["hostname"], info["controllerCount"], info["robotCount"]), ("1.2.3", None, None, 0, 2))
    check("the uptime in days", ss.uptime_text(90061), "1 d 1 h")
    check("the uptime in hours", ss.uptime_text(3 * 3600 + 120), "3 h 2 min")
    check("the uptime in minutes", ss.uptime_text(480), "8 min")
    installed = ss.parse_installed([{"name": "b", "version": "1"}, {"name": "A"}, {"name": ""}, "x", {"family": "core"}])
    check("the programs by name, those without a name dropped", [(p["name"], p["version"]) for p in installed], [("A", None), ("b", "1")])
    check("an answer that is not a list gives no programs", ss.parse_installed({"projects": 1}), [])
    versions = ss.versions_view("0.1", info, installed, "")
    check("the versions screen counts the programs that report", versions["summary"], _("SETUP_VERSIONS_COUNT", with_version=1, total=2))
    check("a program without a version says so", versions["rows"][0][2], _("SETUP_VERSIONS_NO_VERSION"))
    check("the versions screen says it changes nothing", versions["note"], _("SETUP_VERSIONS_NO_SOURCE"))
    check("no programs says so", ss.versions_view("0.1", None, [], "")["summary"], _("SETUP_VERSIONS_NONE"))


def installation():
    unreadable = ss.install_steps(None, None)
    check("a server that cannot be read leaves the steps unknown, never to do", [s["state"] for s in unreadable], ["todo", "unknown", "unknown", "unknown"])
    info = ss.parse_server_info({"controllerCount": 1, "robotCount": 0})
    steps = ss.install_steps(info, False)
    check("the steps in order", [(s["id"], s["state"]) for s in steps], [("server", "done"), ("controller", "done"), ("robot", "todo"), ("second_factor", "todo")])
    check("the next step is the first to do", ss.next_step(steps)["id"], "robot")
    view = ss.installation_view(info, False, "")
    check("the progress", view["summary"], _("SETUP_INSTALLATION_PROGRESS", done=2, total=4))
    check("the next step is told", view["section"], _("SETUP_INSTALLATION_NEXT", step=_("SETUP_INSTALLATION_STEP_ROBOT")))
    check("it says it installs nothing", view["note"], _("SETUP_INSTALLATION_NO_INSTALLER"))
    done = ss.installation_view(ss.parse_server_info({"controllerCount": 1, "robotCount": 1}), True, "")
    check("all done", done["section"], _("SETUP_INSTALLATION_ALL_DONE"))
    unknown = ss.installation_view(ss.parse_server_info({"controllerCount": 1, "robotCount": 1}), None, "")
    check("some steps cannot be told", unknown["section"], _("SETUP_INSTALLATION_CANNOT_TELL"))


def security():
    keys = ss.parse_keys({"algorithm": "EdDSA", "keys": [
        {"kid": "k1", "createdAt": 100, "active": False, "acceptedUntil": 200},
        {"kid": "k2", "createdAt": 300, "active": True},
        {"kid": "", "createdAt": 5}, {"kid": "bad", "createdAt": -1}, "damaged",
    ]})
    check("only the keys with a name and a date stay", [k["kid"] for k in keys["keys"]], ["k1", "k2"])
    check("the active key is the newest not retired", ss.active_key(keys["keys"])["kid"], "k2")
    check("a body that is not an object gives nothing", ss.parse_keys("x"), None)
    check("a private part is never read", set(keys["keys"][0]), {"kid", "createdAt", "retiredAt", "active", "acceptedUntil"})
    check("the checks: not known stays not known", [c["ok"] for c in ss.security_checks(None, None)], [None, None])
    check("the checks: EdDSA is asymmetric", [c["ok"] for c in ss.security_checks(True, "EdDSA")], [True, True])
    check("the checks: HS256 is not", [c["ok"] for c in ss.security_checks(False, "HS256")], [False, False])
    view = ss.security_view(True, keys, True, "", False, "", True)
    rotate = next(b for b in view["buttons"] if b["id"] == "rotate")
    check("the rotation is off until the switch is on", rotate["enabled"], False)
    check("the rotation asks first", rotate["confirm"], _("SETUP_SECURITY_ROTATE_CONFIRM"))
    on = ss.security_view(True, keys, True, "", True, "", True)
    check("the switch enables the rotation", next(b for b in on["buttons"] if b["id"] == "rotate")["enabled"], True)
    check("the table has a row per key", len(view["rows"]), 2)
    plain = ss.security_view(True, keys, False, "", False, "", True)
    check("an account that is not an administrator sees no keys and no rotation", (plain["rows"], plain["buttons"], plain["note"]), ([], [], _("SETUP_SECURITY_ADMIN_ONLY")))
    check("a rotation refused for HS256 says why", ss.rotate_failure_text((409, {})), _("SETUP_SECURITY_ERROR_ASYMMETRIC_OFF"))
    check("a rotation that could not write the file says why", ss.rotate_failure_text((500, {})), _("SETUP_SECURITY_ERROR_FILE"))
    check("a rotation on an old server says so", ss.rotate_failure_text((404, {})), _("SETUP_ERROR_UNSUPPORTED"))


def remote():
    check("nothing set means every kind of app is allowed", ss.allowed_clients(None), list(ss.REMOTE_CLIENTS))
    check("the old combined switch off closes the kinds without a choice", ss.allowed_clients({"enabled": False, "android": True}), ["android"])
    check("a choice of its own wins over the combined switch", ss.client_allowed({"enabled": True, "ios": False}, "ios"), False)
    check("a changed kind keeps the rest", ss.with_client({"enabled": False}, "watch", True), {"enabled": False, "watch": True})
    check("an unknown kind is ignored", ss.with_client({"android": True}, "toaster", False), {"android": True})
    closed = ss.close_all_setting({"enabled": True})
    check("close all closes every kind", ss.allowed_clients(closed), [])
    check("a phone cannot use localhost", ss.address_reachable_from_outside("http://localhost:3000"), False)
    check("a phone can use the address of the machine", ss.address_reachable_from_outside("https://192.168.0.5:3000"), True)
    check("a damaged address is not reachable", ss.address_reachable_from_outside("http://[bad"), False)
    view = ss.remote_view("http://127.0.0.1:3000", {"android": False}, None, True)
    check("localhost warns", view["error"], _("SETUP_REMOTE_LOCAL_WARNING"))
    check("a toggle per kind", [t["id"] for t in view["toggles"]], ["client_" + c for c in ss.REMOTE_CLIENTS])
    check("close all is offered while any kind is open", next(b for b in view["buttons"] if b["id"] == "close_all")["enabled"], True)
    check("close all asks first", next(b for b in view["buttons"] if b["id"] == "close_all")["confirm"], _("SETUP_REMOTE_CLOSE_ALL_CONFIRM"))
    shut = ss.remote_view("http://10.0.0.2", closed, None, True)
    check("nothing to close when all is closed", next(b for b in shut["buttons"] if b["id"] == "close_all")["enabled"], False)
    locked = ss.remote_view("http://10.0.0.2", None, None, False)
    check("an account that may not change settings cannot touch the switches", {t["enabled"] for t in locked["toggles"]}, {False})
    check("the reachable address has no warning", locked["error"], "")


def notifications():
    check("a body that is not an object gives nothing", ss.parse_push([]), None)
    state = ss.parse_push({"enabled": True, "configured": False, "problem": "no key", "devices": 3, "sandbox": True, "events": {"globalStop": True, "other": False, "bad": "x"}})
    check("the events are the booleans, sorted", state["events"], [{"id": "globalStop", "on": True}, {"id": "other", "on": False}])
    check("on without credentials", ss.push_verdict(state), "needs_credentials")
    check("off", ss.push_verdict({"enabled": False, "configured": True}), "off")
    check("ready", ss.push_verdict({"enabled": True, "configured": True}), "ready")
    view = ss.notifications_view(state, True, "")
    check("an event this program does not know is shown by its id", [c["label"] for c in view["checks"]], [_("SETUP_NOTIFICATIONS_EVENT_GLOBALSTOP"), "other"])
    check("the reason is shown while it cannot send", view["facts"][0]["value"], "no key")
    check("it says there are no switches", view["note"], _("SETUP_NOTIFICATIONS_READ_ONLY"))
    plain = ss.notifications_view(state, False, "")
    check("only administrators see the state", (plain["checks"], plain["note"]), ([], _("SETUP_NOTIFICATIONS_ADMIN_ONLY")))


def history():
    clients = [{"who": "a", "detail": "d", "sessions": "1", "logins": "2", "lastSeen": "now"}]
    events = [{"action": "Sign-in", "detail": " - a", "ago": "1 min"}]
    audit = [{"time": "t", "type": "x", "outcome": "ok", "account": "a", "robot": "-"}]
    admin = ss.history_view("audit", True, clients, events, audit, "")
    check("an administrator has both parts", [p["id"] for p in admin["parts"]], ["connections", "audit"])
    check("the audit part lists the record", admin["rows"], [["t", "x", "ok", "a", "-"]])
    plain = ss.history_view("audit", False, clients, events, audit, "")
    check("an account that is not an administrator falls back to the connections", ([p["id"] for p in plain["parts"]], plain["rows"][0][0], plain["note"]), (["connections"], "a", _("SETUP_HISTORY_AUDIT_ADMIN_ONLY")))
    check("the events are listed apart", plain["extraRows"], [["Sign-in - a", "1 min"]])


def sentences():
    source = (ROOT / "hydra_suite" / "panel_logic" / "setup_screens.py").read_text(encoding="utf-8")
    keys = {k for k in re.findall(r"_\(\"(SETUP_[A-Z_]+)\"", source) if not k.endswith("_")}
    # the keys built from an id: one sentence per step, check, client, event, verdict and part
    for step in ("server", "controller", "robot", "second_factor"):
        keys |= {f"SETUP_INSTALLATION_STEP_{step.upper()}", f"SETUP_INSTALLATION_STEP_{step.upper()}_HINT"}
    keys |= {f"SETUP_SECURITY_CHECK_{c.upper()}" for c in ("second_factor", "asymmetric_keys")}
    keys |= {f"SETUP_REMOTE_CLIENT_{c.upper()}" for c in ss.REMOTE_CLIENTS}
    keys |= {f"SETUP_NOTIFICATIONS_EVENT_{e.upper()}" for e in ss.KNOWN_EVENTS}
    keys |= {f"SETUP_NOTIFICATIONS_VERDICT_{v}" for v in ("OFF", "NEEDS_CREDENTIALS", "READY")}
    keys |= {f"SETUP_HISTORY_PART_{p}" for p in ("CONNECTIONS", "AUDIT")}
    keys |= {label for label, _panel in ss.SCREENS}
    qml = (ROOT / "assets" / "qml" / "Main.qml").read_text(encoding="utf-8")
    keys |= set(re.findall(r'uiText\("(SETUP_[A-Z_]+|DOCK_SETUP_[A-Z_]+)"', qml))
    check("the screens use sentences", len(keys) >= 90, True)
    for lng in sorted(LANGUAGE_FOLDER.glob("*.lng")):
        have = {line.split("=", 1)[0] for line in lng.read_text(encoding="utf-8").splitlines() if "=" in line}
        check(f"{lng.name} has every sentence of the setup screens", sorted(keys - have), [])
    from hydra_suite import nav_items
    check("every screen is in the navigation", ss.SCREEN_KEYS <= nav_items.ALL_DOCK_KEYS, True)
    check("the navigation has no screen that is not drawn", {k for _l, k in nav_items.SETUP_ITEMS}, set(ss.SCREEN_KEYS))


def main() -> int:
    reading()
    installation()
    security()
    remote()
    notifications()
    history()
    sentences()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
