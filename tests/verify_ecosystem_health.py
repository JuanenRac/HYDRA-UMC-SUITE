# =============================================================================
# HYDRA-UMC SUITE - tests/verify_ecosystem_health.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Ecosystem health screen against a simulated server (a small HTTP server on this machine, no network):
#   - one card per service, the most serious first, filters by state and by another version
#   - the notices: certificate about to expire or expired, a service down or degraded, a version that differs from its manifest
#   - the sentences for 404 (the server does not offer it, also with a plain page as body), 403 (no permission) and a failed
#     read, which keep the last good answer on screen
#   - a port, address or unit that a server sends to an administrator never reaches a card
#   - a damaged entry is dropped, an unknown state is shown as unknown
#   - the switch of the option in the security screen: read, locked by the environment, sent
#   - the section "HYDRA-UMC updates" of the Updates screen (GET /api/admin/self-update): the table of the programs against their newest signed release,
#     a state that is not known shown as not known, applying off until the switch is on and the server allows it, the confirmation, the job followed through
#     a restart of the server (a cut connection, a 502), the long silence, each way the start or the read can fail
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import qt_suite as qs
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.panel_logic import ecosystem_health as eh
from hydra_suite.panel_logic import server_security as sec

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def stamp(seconds_ago):
    return (NOW - timedelta(seconds=seconds_ago)).isoformat().replace("+00:00", "Z")


def service(name, state="ok", **more):
    # port, address and unit as the server sends them to an administrator: the screen must never show them
    return {"name": name, "family": "core", "role": "server", "state": state, "reason": more.pop("reason", "health_ok"), "version_expected": "1.2.3",
            "version_reported": "1.2.3", "drift": False, "last_seen_utc": stamp(30), "latency_ms": 12, "port": 18200, "address": "192.168.7.7", "unit": "eh3d-hidden.service", **more}


ANSWER = {
    "schema_version": "1.0", "generated_at_utc": stamp(0), "available": True,
    "services": [
        service("alpha"),
        service("zulu", "down", reason="unreachable", last_seen_utc=None, latency_ms=None),
        service("bravo", "degraded", reason="health_degraded"),
        service("charlie", drift=True, version_reported="1.2.2"),
        service("delta", "paused-by-a-newer-server", reason="some_future_reason"),
        {"name": ""}, "junk", None, {"state": "ok"},
    ],
    "certificate": {"state": "expiring", "not_after_utc": "2026-01-20T00:00:00Z", "days_left": 19, "warn_days": 30},
    "warnings": [
        {"code": "certificate_expiring"}, {"code": "service_down", "service": "zulu"}, {"code": "service_degraded", "service": "bravo"},
        {"code": "version_drift", "service": "charlie"}, {"code": "from_a_newer_server"}, "junk",
    ],
}


class Behaviour:
    status = 200
    body: bytes = b"{}"
    hang_up = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path.startswith("/api/admin/self-update/"):
            SelfUpdateSim.post(self)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/admin/self-update"):
            SelfUpdateSim.get(self)
            return
        if self.path != "/api/ecosystem/health":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if Behaviour.hang_up:
            self.connection.close()
            return
        self.send_response(Behaviour.status)
        self.send_header("Content-Length", str(len(Behaviour.body)))
        self.end_headers()
        self.wfile.write(Behaviour.body)


def serve(status=200, body=None, raw=None):
    Behaviour.status, Behaviour.hang_up = status, False
    Behaviour.body = raw if raw is not None else json.dumps(body if body is not None else {}).encode()


def pump(loop, seconds=0.05):
    loop.run_until_complete(asyncio.sleep(seconds))


def logic():
    health = eh.parse_health(ANSWER)
    names = [s["name"] for s in health["services"]]
    check("damaged entries are dropped, the rest stays", names, ["alpha", "zulu", "bravo", "charlie", "delta"])
    check("a state or reason this app does not know is shown as unknown", (health["services"][4]["state"], health["services"][4]["reason"]), ("unknown", ""))
    check("an answer that is not the route is refused", [eh.parse_health(x) for x in (None, [], {}, {"schema_version": "2.0", "services": []}, {"schema_version": "1.0"})], [None] * 5)
    check("the unknown warning code is dropped", [w["code"] for w in health["warnings"]], ["certificate_expiring", "service_down", "service_degraded", "version_drift"])
    rows = eh.card_rows(health["services"], "all", NOW)
    check("the most serious first, then by name", [r["name"] for r in rows], ["zulu", "bravo", "delta", "alpha", "charlie"])
    check("a card says state, reason, versions, drift and last answer", (rows[0]["stateLabel"], rows[0]["reason"], rows[0]["seen"], rows[4]["drift"], rows[4]["versions"], rows[3]["seen"]),
          (_("ECOHEALTH_STATE_DOWN"), _("ECOHEALTH_REASON_UNREACHABLE"), _("ECOHEALTH_NEVER_SEEN"), True,
           f"{_('ECOHEALTH_VERSION_EXPECTED')}: 1.2.3 - {_('ECOHEALTH_VERSION_REPORTED')}: 1.2.2",
           _("ECOHEALTH_LAST_SEEN", ago="30s") + " - " + _("ECOHEALTH_LATENCY", ms=12)))
    shown = json.dumps(rows) + json.dumps(eh.notice_rows(health))
    check("no port, address or unit ever reaches a card", [x in shown for x in ("18200", "192.168.7.7", "eh3d-hidden")], [False, False, False])
    check("filters by state and by another version", [[r["name"] for r in eh.card_rows(health["services"], f, NOW)] for f in ("down", "drift", "ok", "bogus")],
          [["zulu"], ["charlie"], ["alpha", "charlie"], ["zulu", "bravo", "delta", "alpha", "charlie"]])
    check("the filter buttons carry the counts", [(f["key"], f["label"].rsplit(" ", 1)[1], f["selected"]) for f in eh.filter_rows(health["services"], "drift")],
          [("all", "(5)", False), ("ok", "(2)", False), ("degraded", "(1)", False), ("down", "(1)", False), ("unknown", "(1)", False), ("drift", "(1)", True)])
    notices = eh.notice_rows(health)
    check("notices: certificate first (amber), then down (red), degraded and drift (amber); the certificate warning is not repeated",
          [(n["level"], n["text"]) for n in notices],
          [("warn", _("ECOHEALTH_CERT_EXPIRING", days=19, date="2026-01-20")), ("error", _("ECOHEALTH_WARNING_SERVICE_DOWN", service="zulu")),
           ("warn", _("ECOHEALTH_WARNING_SERVICE_DEGRADED", service="bravo")), ("warn", _("ECOHEALTH_WARNING_VERSION_DRIFT", service="charlie"))])
    for state, level in (("ok", "ok"), ("expired", "error"), ("unreadable", "error")):
        check(f"certificate {state}", eh.notice_rows({"certificate": {"state": state, "notAfter": "", "daysLeft": None, "warnDays": 30}, "warnings": []})[0]["level"], level)
    check("the sentences for each answer",
          [eh.status_for(r) for r in ((200, ANSWER), (200, {"x": 1}), (404, None), (403, None), (401, {}), (500, {}), None)],
          ["", _("ECOHEALTH_LOAD_ERROR"), _("ECOHEALTH_UNSUPPORTED"), _("ECOHEALTH_FORBIDDEN"), _("ECOHEALTH_FORBIDDEN"), _("ECOHEALTH_LOAD_ERROR"), _("ECOHEALTH_LOAD_ERROR")])
    keys = [f"ECOHEALTH_{x}" for x in ("TITLE", "DESC", "LOADING", "REFRESH", "NOT_AVAILABLE", "NO_SERVICES", "NO_MATCH", "DRIFT_BADGE")]
    keys += [f"ECOHEALTH_FILTER_{f.upper()}" for f in eh.FILTERS] + [f"ECOHEALTH_STATE_{x.upper()}" for x in eh.SERVICE_STATES]
    keys += [f"ECOHEALTH_REASON_{x.upper()}" for x in eh.SERVICE_REASONS] + [f"ECOHEALTH_CERT_{x.upper()}" for x in eh.CERTIFICATE_STATES]
    keys += [f"ECOHEALTH_WARNING_{x.upper()}" for x in eh.WARNING_CODES]
    check("every state, reason, filter, certificate and warning has a sentence", all(_(k) != k for k in keys), True)


def screen(loop, port):
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port, username="ana", password="pw"))
    conn._token = "tok"
    conn.login_ok = True
    conn.role = "operator"
    controller.connections["s"] = conn
    controller._active_id = "s"
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()

    def refresh():
        loop.run_until_complete(bridge._refresh_eco_health())

    serve(body=ANSWER)
    refresh()
    check("screen: cards in order, no problem", (bridge.ecoHealthStatus, [c["name"] for c in bridge.ecoHealthCards], bridge.ecoHealthLoaded), ("", ["zulu", "bravo", "delta", "alpha", "charlie"], True))
    check("screen: notices and filter buttons", (len(bridge.ecoHealthNotices), len(bridge.ecoHealthFilters)), (4, 6))
    bridge.setEcoHealthFilter("drift")
    check("screen: the drift filter keeps one card", [c["name"] for c in bridge.ecoHealthCards], ["charlie"])
    bridge.setEcoHealthFilter("down")
    bridge.setEcoHealthFilter("nonsense")
    check("screen: an unknown filter changes nothing", [c["name"] for c in bridge.ecoHealthCards], ["zulu"])
    bridge.setEcoHealthFilter("unknown")
    serve(body=dict(ANSWER, services=[service("only")]))
    refresh()
    check("screen: a filter that matches nothing says so", (bridge.ecoHealthCards, bridge.ecoHealthEmpty), ([], _("ECOHEALTH_NO_MATCH")))
    bridge.setEcoHealthFilter("all")
    serve(body=dict(ANSWER, services=[]))
    refresh()
    check("screen: no service at all says so", bridge.ecoHealthEmpty, _("ECOHEALTH_NO_SERVICES"))
    serve(body=dict(ANSWER, available=False))
    refresh()
    check("screen: a server that could not scan says so", bridge.ecoHealthUnavailable, True)

    serve(body=ANSWER)
    refresh()
    for label, (status, raw), sentence in (
        ("404 with a plain page: the server does not offer it", (404, b"<html>Not Found</html>"), _("ECOHEALTH_UNSUPPORTED")),
        ("403: no permission", (403, b'{"error":"forbidden"}'), _("ECOHEALTH_FORBIDDEN")),
        ("500: a failed read", (500, b"boom"), _("ECOHEALTH_LOAD_ERROR")),
        ("200 with nonsense", (200, b"not json"), _("ECOHEALTH_LOAD_ERROR")),
    ):
        serve(status, raw=raw)
        refresh()
        check(f"screen: {label}, the last good cards stay", (bridge.ecoHealthStatus, len(bridge.ecoHealthCards)), (sentence, 5))
    Behaviour.hang_up = True
    refresh()
    check("screen: no answer at all keeps the last good cards", (bridge.ecoHealthStatus, len(bridge.ecoHealthCards)), (_("ECOHEALTH_LOAD_ERROR"), 5))
    serve(body=ANSWER)
    refresh()
    check("screen: a good read clears the problem", bridge.ecoHealthStatus, "")
    controller._active_id = None
    refresh()
    check("screen: no server selected", (bridge.ecoHealthStatus, bridge.ecoHealthCards), (_("LBL_ES_NO_ACTIVE_SERVER"), []))
    check("screen: the poller belongs to its own panel", (bridge._eco_health_timer in bridge._poller_gates()["ecosystem_health"], bridge._eco_health_timer.isActive()), (True, False))


def switch(loop):
    base = {"aiAccess": {"value": "open", "source": "default"}, "infoAuth": {"value": False, "source": "default"}, "tls": {"enabled": False, "source": "default"}}
    plain = sec.parse_state(base)
    check("switch: a server without the option shows no switch", (plain["ecosystemHealth"], sec.view(plain)["ecosystemHealthAvailable"]), (None, False))
    off = sec.parse_state({**base, "ecosystemHealth": {"enabled": {"value": False, "source": "default"}}})
    locked = sec.parse_state({**base, "ecosystemHealth": {"enabled": {"value": True, "source": "env"}}})
    check("switch: off by default, source shown", (sec.view(off)["ecosystemHealthEnabled"], sec.view(off)["ecosystemHealthEnabledLocked"], sec.view(off)["ecosystemHealthEnabledSource"]), (False, False, _("SECURITY_SOURCE_DEFAULT")))
    check("switch: fixed by the environment it is locked", (sec.view(locked)["ecosystemHealthEnabled"], sec.view(locked)["ecosystemHealthEnabledLocked"]), (True, True))
    check("switch: a damaged value shows no switch", sec.parse_state({**base, "ecosystemHealth": {"enabled": {"value": "yes", "source": "default"}}})["ecosystemHealth"], None)
    check("switch: what is sent", (sec.ecosystem_health_patch(True), sec.ecosystem_health_patch(False)), ({"ecosystemHealth": {"enabled": True}}, {"ecosystemHealth": {"enabled": False}}))
    check("switch: every key of the view exists without a server", set(sec.view(None)) == set(sec.view(locked)), True)

    trusted_plain = sec.parse_state(base)
    check("trusted networks: a server without the option shows no switch", (trusted_plain["trustedNetworks"], sec.view(trusted_plain)["trustedNetworksAvailable"]), (None, False))
    trusted_off = sec.parse_state({**base, "trustedNetworks": {"enabled": {"value": False, "source": "default"}}})
    trusted_locked = sec.parse_state({**base, "trustedNetworks": {"enabled": {"value": True, "source": "env"}}})
    check("trusted networks: off by default, source shown", (sec.view(trusted_off)["trustedNetworksEnabled"], sec.view(trusted_off)["trustedNetworksEnabledLocked"], sec.view(trusted_off)["trustedNetworksEnabledSource"]), (False, False, _("SECURITY_SOURCE_DEFAULT")))
    check("trusted networks: fixed by the environment it is locked", (sec.view(trusted_locked)["trustedNetworksEnabled"], sec.view(trusted_locked)["trustedNetworksEnabledLocked"]), (True, True))
    check("trusted networks: a damaged value shows no switch", sec.parse_state({**base, "trustedNetworks": {"enabled": {"value": "yes", "source": "default"}}})["trustedNetworks"], None)
    check("trusted networks: what is sent", (sec.trusted_networks_patch(True), sec.trusted_networks_patch(False)), ({"trustedNetworks": {"enabled": True}}, {"trustedNetworks": {"enabled": False}}))
    check("trusted networks: the warning has its own sentence", (sec.known_warning(["trusted_networks_on"]) != "", sec.known_warning(["trusted_networks_on"]) == _("SECURITY_TRUSTED_WARNING")), (True, True))
    check("trusted networks: every key of the view exists without a server", set(sec.view(None)) == set(sec.view(trusted_locked)), True)

    def opt(value, default, risky, **extra):
        return {"value": value, "source": "default" if value == default else "config", "default": default, "risky": risky, "localName": "LOCAL", **extra}

    bridges_body = {
        "delivery": "gateway_off",
        "droids": {"globalStop": opt(False, False, []), "cutOnGlobalStop": opt(True, True, [False])},
        "uav": {"missionUploadEnabled": opt(False, False, [True])},
        "amr": {"publishState": opt(False, False, []), "zoneUnknown": opt("pause", "pause", ["ignore"], choices=["pause", "ignore"])},
        "openpnp": {"boardCode": opt("off", "off", [], choices=["off", "advisory", "required"])},
    }
    bridges_plain = sec.parse_state(base)
    check("bridges: a server without the switches shows no section", (bridges_plain["bridges"], sec.view(bridges_plain)["bridgesAvailable"]), (None, False))
    bridges_state = sec.parse_state({**base, "bridges": bridges_body})
    bridges_view = sec.view(bridges_state)
    check("bridges: every switch is listed with its label and the gateway state", (bridges_view["bridgesAvailable"], [o["id"] for o in bridges_view["bridgesOptions"]], bridges_view["bridgesDelivery"]), (True, ["droids.globalStop", "droids.cutOnGlobalStop", "uav.missionUploadEnabled", "amr.publishState", "amr.zoneUnknown", "openpnp.boardCode"], _("SECURITY_BRIDGES_DELIVERY_OFF")))
    zone = [o for o in bridges_view["bridgesOptions"] if o["id"] == "amr.zoneUnknown"][0]
    check("bridges: a choice carries its words and the note names origin, default and local name", (zone["isChoice"], [c["value"] for c in zone["choices"]], "LOCAL" in zone["note"], _("SECURITY_SOURCE_DEFAULT") in zone["note"]), (True, ["pause", "ignore"], True, True))
    check("bridges: a damaged switch hides the section", sec.parse_state({**base, "bridges": {**bridges_body, "uav": {"missionUploadEnabled": {"value": "x"}}}})["bridges"], None)
    check("bridges: an unknown gateway state hides the section", sec.parse_state({**base, "bridges": {**bridges_body, "delivery": "maybe"}})["bridges"], None)
    values = {o["id"]: o["value"] for o in bridges_state["bridges"]["options"]}
    check("bridges: nothing changed sends nothing", sec.bridges_patch(bridges_state, values), None)
    check("bridges: only what changed is sent", sec.bridges_patch(bridges_state, {**values, "amr.publishState": True, "openpnp.boardCode": "advisory"}), {"bridges": {"amr": {"publishState": True}, "openpnp": {"boardCode": "advisory"}}})
    check("bridges: a word that is not a choice sends nothing", sec.bridges_patch(bridges_state, {**values, "amr.zoneUnknown": "maybe"}), None)
    ask = lambda change: sec.bridges_needs_confirmation(bridges_state, sec.bridges_patch(bridges_state, {**values, **change}))
    check("bridges: only a risky value asks first", (ask({"uav.missionUploadEnabled": True}), ask({"amr.zoneUnknown": "ignore"}), ask({"droids.cutOnGlobalStop": False}), ask({"amr.publishState": True}), ask({"openpnp.boardCode": "required"})), (True, True, True, False, False))
    signing_body = {
        "droids": {"keyFile": "/keys/droids.key", "key": "present", "lastSignedAt": "1970-01-01T00:00:01.000Z", "seq": 7},
        "amr": {"keyFile": "/keys/amr.key", "key": "missing", "lastSignedAt": None, "seq": 0},
        "uav": {"keyFile": "/keys/uav.key", "key": "broken"},
    }
    signing_state = sec.parse_state({**base, "bridges": bridges_body, "bridgeSigning": signing_body})
    check("bridges: the signing state lists each bridge with a usable entry and only the path of the key", ([item["bridge"] for item in signing_state["bridges"]["signing"]], set(signing_state["bridges"]["signing"][0])), (["droids", "amr"], {"bridge", "keyFile", "key", "lastSignedAt"}))
    signing_text = sec.view(signing_state)["bridgesSigning"]
    check("bridges: the signing text names each bridge, its key state, the last signature and the key file", ("BRIDGE-DROIDS" in signing_text, _("SECURITY_BRIDGES_SIGNING_KEY_PRESENT") in signing_text, _("SECURITY_BRIDGES_SIGNING_KEY_MISSING") in signing_text, _("SECURITY_BRIDGES_SIGNING_NEVER") in signing_text, "/keys/droids.key" in signing_text), (True, True, True, True, True))
    check("bridges: a server that predates the signed settings shows no signing text", (bridges_state["bridges"]["signing"], bridges_view["bridgesSigning"]), ([], ""))
    check("bridges: the warning has its own sentence", sec.known_warning(["bridge_uav_missionUploadEnabled"]) == _("SECURITY_BRIDGES_WARNING") != "", True)
    check("bridges: every key of the view exists without a server", set(sec.view(None)) == set(bridges_view), True)
    flight = ["droids.confirmationRequired", "droids.returnHomeAlways", "uav.envelopeRequired", "uav.confirmationRequired", "uav.chainInFlight", "uav.uploadGeofence"]
    check("bridges: every flight policy switch has its own label", all(key in sec.BRIDGE_OPTION_TEXT and _(sec.BRIDGE_OPTION_TEXT[key]) not in ("", sec.BRIDGE_OPTION_TEXT[key]) for key in flight), True)
    check("bridges: the flight policy labels are all different", len({sec.BRIDGE_OPTION_TEXT[key] for key in flight}), len(flight))

    rul_plain = sec.parse_state(base)
    check("rul: a server without the option shows no switch", (rul_plain["rul"], sec.view(rul_plain)["rulAvailable"]), (None, False))
    rul_off = sec.parse_state({**base, "rul": {"enabled": {"value": False, "source": "default"}}})
    rul_locked = sec.parse_state({**base, "rul": {"enabled": {"value": True, "source": "env"}}})
    check("rul: off by default, source shown", (sec.view(rul_off)["rulAvailable"], sec.view(rul_off)["rulEnabled"], sec.view(rul_off)["rulEnabledLocked"], sec.view(rul_off)["rulEnabledSource"]), (True, False, False, _("SECURITY_SOURCE_DEFAULT")))
    check("rul: fixed by the environment it is locked", (sec.view(rul_locked)["rulEnabled"], sec.view(rul_locked)["rulEnabledLocked"]), (True, True))
    check("rul: a damaged value shows no switch", sec.parse_state({**base, "rul": {"enabled": {"value": "yes", "source": "default"}}})["rul"], None)
    check("rul: what is sent", (sec.rul_patch(True), sec.rul_patch(False)), ({"rul": {"enabled": True}}, {"rul": {"enabled": False}}))
    check("rul: every key of the view exists without a server", set(sec.view(None)) == set(sec.view(rul_locked)), True)

    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    sent = []

    async def save(patch):
        sent.append(patch)

    bridge._save_security = save
    bridge.saveRulOptions(True)
    pump(loop)
    check("rul: nothing is sent before the server showed the option", sent, [])
    bridge._security_state = rul_off
    bridge.saveRulOptions(True)
    pump(loop)
    check("rul: turning it on sends the patch", sent, [{"rul": {"enabled": True}}])
    sent.clear()
    bridge._security_state = None
    bridge.saveEcosystemHealthOptions(True)
    pump(loop)
    check("switch: nothing is sent before the server showed the option", sent, [])
    bridge._security_state = off
    bridge.saveEcosystemHealthOptions(True)
    pump(loop)
    check("switch: turning it on sends the patch", sent, [{"ecosystemHealth": {"enabled": True}}])

# ---- the updates of the programs of the machine (GET /api/admin/self-update): the reading, the job, the follower and the screen


class SelfUpdateSim:
    """The routes of /api/admin/self-update of a simulated server: the answer of the table, the answers of the job in order (the last one stays; None cuts the connection)."""

    status = 200
    body: dict = {}
    jobs: list = []
    reads = 0
    posted: list = []
    start: tuple = (202, {})

    @staticmethod
    def send(handler, status, body):
        raw = json.dumps(body).encode()
        handler.send_response(status)
        handler.send_header("Content-Length", str(len(raw)))
        handler.end_headers()
        handler.wfile.write(raw)

    @classmethod
    def get(cls, handler):
        path = handler.path.split("?")[0]
        if path == "/api/admin/self-update":
            cls.send(handler, cls.status, cls.body)
        elif path.startswith("/api/admin/self-update/jobs/"):
            answer = cls.jobs[min(cls.reads, len(cls.jobs) - 1)] if cls.jobs else (404, {})
            cls.reads += 1
            if answer is None:
                handler.connection.close()
                return
            cls.send(handler, *answer)
        else:
            cls.send(handler, 404, {})

    @classmethod
    def post(cls, handler):
        length = int(handler.headers.get("Content-Length") or 0)
        cls.posted.append((handler.path, json.loads(handler.rfile.read(length) or b"{}")))
        cls.send(handler, *cls.start)


def su_item(component, installed="1.0.0", previous=None, latest="1.1.0", state="behind", signed=True):
    return {"id": component, "repo": f"JuanenRac/HYDRA-UMC-{component.upper()}", "installed": installed, "previous": previous, "latest": latest, "state": state, "signedPackage": signed}


def su_job(state="downloading", **more):
    return {"id": "j1", "action": "apply", "component": "server", "state": state, "fromVersion": "1.0.0", "targetVersion": "1.1.0", "error": None, "detail": "",
            "log": [{"at": "2026-01-01T12:00:00Z", "step": "checking", "text": "looking"}], "by": "ana", **more}


SU_STATUS = {"checkedAt": "2026-01-01T12:00:00Z", "owner": "JuanenRac", "rateLimited": False, "applyEnabled": True, "job": None,
             "items": [su_item("server", previous="0.9.0"), su_item("studio", state="current", latest="1.0.0"), su_item("os-agent", state="weird", signed=False)]}


def self_update_logic():
    sl = __import__("hydra_suite.panel_logic.self_update", fromlist=["x"])
    status = sl.parse_status(SU_STATUS)
    check("updates: the three programs are read and a state that is not known is shown as not known", ([i["id"] for i in status["items"]], [i["state"] for i in status["items"]]),
          (["server", "studio", "os-agent"], ["behind", "current", "unknown"]))
    check("updates: what is not that answer is refused", [sl.parse_status(x) for x in (None, [], {}, {"items": "x"}, "text")], [None] * 5)
    check("updates: a program this app does not know is dropped", [i["id"] for i in sl.parse_status({"items": [su_item("server"), {"id": "toaster"}, 3]})["items"]], ["server"])
    check("updates: applying is on only when the server says exactly true", [sl.parse_status({"items": [], "applyEnabled": v})["applyEnabled"] for v in (True, False, 1, "true", None)], [True, False, False, False, False])
    check("updates: a job needs an id, a program of the three and a step it knows", [sl.parse_job(j) is not None for j in (su_job(), {**su_job(), "id": ""}, {**su_job(), "component": "x"}, {**su_job(), "state": "x"}, None, [])],
          [True, False, False, False, False, False])
    check("updates: a log line with an unknown step is dropped", len(sl.parse_job(su_job(log=[{"step": "applying", "text": "a"}, {"step": "x", "text": "b"}, {"step": "done"}]))["log"]), 1)
    check("updates: the answers of the table are classified", [sl.classify_read(r)[0] for r in ((200, SU_STATUS), (200, {"x": 1}), (404, None), (403, {}), (401, {}), (500, {}), None)],
          ["ok", "malformed", "unsupported", "forbidden", "forbidden", "http", "network"])
    check("updates: the answers to the start are classified", [sl.classify_start(r)[0] for r in ((202, su_job()), (200, su_job()), (202, {}), (404, {}), (403, {}), (423, {}), (409, {}), (500, {}), None)],
          ["ok", "ok", "refused", "disabled", "forbidden", "forbidden", "busy", "refused", "network"])
    check("updates: a cut connection, a 502 or a body that is not the job mean wait, never failed; only a refused session stops",
          [sl.classify_job_read(r, "j1")[0] for r in (None, (502, None), (503, {}), (200, {}), (200, su_job()), (200, {**su_job(), "id": "other"}), (403, {}), (404, {}))],
          ["wait", "wait", "wait", "wait", "job", "wait", "stop", "wait"])
    check("updates: running and the line of progress", [(sl.running(sl.parse_job(su_job(state=s))), sl.progress_index(sl.parse_job(su_job(state=s)))) for s in ("checking", "applying", "done")],
          [(True, 0), (True, 3), (False, 5)])
    failed = sl.parse_job(su_job(state="failed", error="signature_invalid", log=[{"step": "checking", "text": "a"}, {"step": "verifying", "text": "b"}]))
    check("updates: a failed job marks the step after the last one it reached", [m["mark"] for m in sl.step_marks(failed)], ["done", "done", "done", "failed", "next", "next"])
    check("updates: a job that failed before the first step marks the first", [m["mark"] for m in sl.step_marks(sl.parse_job(su_job(state="failed", log=[])))][:2], ["failed", "next"])
    check("updates: a finished job has every step done", {m["mark"] for m in sl.step_marks(sl.parse_job(su_job(state="done")))}, {"done"})
    check("updates: a reason has its sentence and an unknown reason has the general one", (sl.failure_text("signature_invalid") != sl.failure_text(None), sl.failure_text("nonsense"), sl.failure_text(None)),
          (True, _("SELFUPD_ERR_GENERIC"), _("SELFUPD_ERR_GENERIC")))
    check("updates: every reason has a sentence of its own", all(_("SELFUPD_ERR_" + code.upper()) != "SELFUPD_ERR_" + code.upper() for code in sl.FAILURES), True)
    check("updates: the switch is off unless the configuration says exactly true", [sl.apply_from_config(c) for c in ({}, {"self_update_apply": True}, {"self_update_apply": 1}, {"self_update_apply": "true"}, None)],
          [False, True, False, False, False])
    # the buttons: both switches, no job going on, a program that is behind with a signed package, an earlier release to go back to
    expect = {
        (True, "apply", "server"): "server", (True, "rollback", "server"): "server", (True, "apply", "studio"): None, (True, "rollback", "studio"): None,
        (True, "apply", "os-agent"): None, (False, "apply", "server"): None, (False, "rollback", "server"): None, (True, "apply", "toaster"): None,
    }
    got = {key: (lambda item: item["id"] if item else None)(sl.may_start(key[1], key[2], key[0], status, None)) for key in expect}
    check("updates: the switch, the state, the signed package and the earlier release decide what may start", got, expect)
    check("updates: a server that has applying off allows nothing, and neither does a running job", (sl.may_start("apply", "server", True, {**status, "applyEnabled": False}, None), sl.may_start("apply", "server", True, status, sl.parse_job(su_job()))), (None, None))
    check("updates: an action that is not one of the two starts nothing", sl.may_start("delete", "server", True, status, None), None)
    rows = {r["id"]: r for r in sl.view(status, "", True, None, None, False, None, "", False)["rows"]}
    check("updates: the table says what each button may do", [(r, rows[r]["canUpdate"], rows[r]["canGoBack"]) for r in rows], [("server", True, True), ("studio", False, False), ("os-agent", False, False)])
    check("updates: a program that is behind without a signed package says so; one that is not known says not known", (rows["os-agent"]["note"], rows["os-agent"]["stateLabel"], rows["server"]["note"]), ("", _("SELFUPD_STATE_UNKNOWN"), ""))
    behind_unsigned = sl.view(sl.parse_status({"items": [su_item("server", signed=False)], "applyEnabled": True}), "", True, None, None, False, None, "", False)["rows"][0]
    check("updates: behind without a signed package cannot be updated and says why", (behind_unsigned["canUpdate"], behind_unsigned["note"]), (False, _("SELFUPD_NO_PACKAGE")))
    off = sl.view(status, "", False, None, None, False, None, "", False)
    check("updates: with the switch off nothing can be started and the mode says check only", ([(r["canUpdate"], r["canGoBack"]) for r in off["rows"]], off["mode"]), ([(False, False)] * 3, _("SELFUPD_MODE_CHECK_ONLY")))
    server_off = sl.view(sl.parse_status({**SU_STATUS, "applyEnabled": False, "rateLimited": True}), "", True, None, None, False, None, "", False)
    check("updates: the server with applying off wins over the switch, and the quota is said", (server_off["rows"][0]["canUpdate"], server_off["mode"]), (False, _("SELFUPD_MODE_SERVER_OFF") + " " + _("SELFUPD_RATE_LIMITED")))
    check("updates: the mode with both switches on", sl.view(status, "", True, None, None, False, None, "", False)["mode"], _("SELFUPD_MODE_APPLY"))
    asked = sl.view(status, "", True, None, None, False, {"action": "apply", "component": "server"}, "", False)
    back = sl.view(status, "", True, None, None, False, {"action": "rollback", "component": "server"}, "", False)
    check("updates: the confirmation names the program and the two versions", (asked["confirm"], back["confirm"]),
          (_("SELFUPD_CONFIRM_APPLY", program=_("SELFUPD_COMPONENT_SERVER"), versions="1.0.0 -> 1.1.0"), _("SELFUPD_CONFIRM_ROLLBACK", program=_("SELFUPD_COMPONENT_SERVER"), versions="1.0.0 -> 0.9.0")))
    check("updates: a confirmation for a program that is not in the table shows nothing", sl.view(status, "", True, None, None, False, {"action": "apply", "component": "toaster"}, "", False)["confirm"], "")
    check("updates: no program shown when the read failed, with the sentence of each failure",
          [(sl.view(None, kind, True, None, None, False, None, "", False)["rows"], sl.view(None, kind, True, None, None, False, None, "", False)["failure"]) for kind in ("unsupported", "forbidden", "network", "no_server")],
          [([], _("SELFUPD_UNSUPPORTED")), ([], _("SELFUPD_FORBIDDEN")), ([], _("SELFUPD_LOAD_ERROR")), ([], _("LBL_ES_NO_ACTIVE_SERVER"))])
    waiting = sl.job_view(sl.parse_job(su_job(state="restarting")), 12, False)
    check("updates: the job card says it waits, how long, and that the update goes on without the window", (waiting["waiting"], waiting["running"], waiting["gaveUp"]), (_("SELFUPD_WAITING", seconds=12), True, ""))
    gave = sl.job_view(sl.parse_job(su_job(state="restarting")), 240, True)
    check("updates: after the limit of silence it says so and stops saying it waits", (gave["gaveUp"], gave["waiting"]), (_("SELFUPD_GAVE_UP"), ""))
    done = sl.job_view(sl.parse_job(su_job(state="done")), None, False)
    check("updates: a finished job says the version in use", (done["done"], done["failed"], done["running"]), (_("SELFUPD_DONE_APPLY", version="1.1.0"), "", False))
    back_done = sl.job_view(sl.parse_job(su_job(state="done", action="rollback", targetVersion="0.9.0")), None, False)
    check("updates: a way back says it is back", back_done["done"], _("SELFUPD_DONE_ROLLBACK", version="0.9.0"))
    fail = sl.job_view(failed, None, False)
    check("updates: a failed job says why, in words", (fail["failed"], fail["done"]), (_("SELFUPD_ERR_SIGNATURE_INVALID"), ""))
    check("updates: the start failures have their sentences", [sl.start_failure_text(k) for k in sl.START_FAILURES] == [_("SELFUPD_START_" + k.upper()) for k in sl.START_FAILURES] and len(set(sl.start_failure_text(k) for k in sl.START_FAILURES)) == 5, True)
    keys = ["SELFUPD_" + k for k in ("TITLE", "INTRO", "SWITCH_TITLE", "SWITCH_HINT", "CHECK", "UPDATE", "ROLLBACK", "NO_PACKAGE", "CONFIRM_TITLE", "CONFIRM_NOTE", "LOOK_AGAIN", "GAVE_UP", "WAITING", "RATE_LIMITED")]
    keys += [f"SELFUPD_COL_{x}" for x in ("PROGRAM", "INSTALLED", "PREVIOUS", "LATEST", "STATE")] + [f"SELFUPD_STATE_{x.upper()}" for x in sl.ITEM_STATES]
    keys += [f"SELFUPD_STEP_{x.upper()}" for x in sl.PROGRESS_STEPS] + [f"SELFUPD_COMPONENT_{x.replace('-', '_').upper()}" for x in sl.COMPONENTS] + ["HELP_SELFUPDATE_Q", "HELP_SELFUPDATE_S1", "HELP_SELFUPDATE_S2", "HELP_SELFUPDATE_S3"]
    check("updates: every sentence of the section exists", [k for k in keys if _(k) == k], [])

    # the follower, with a clock that only moves when it sleeps: through a restart (a cut, a 502), to the end, to the limit of silence, stopped
    def scripted(answers):
        left = list(answers)

        async def read(_job_id):
            return left.pop(0) if len(left) > 1 else left[0]

        return read

    def clock():
        state = {"t": 0.0}

        async def sleep(seconds):
            state["t"] += seconds

        return (lambda: state["t"]), sleep

    async def follow(answers, **options):
        now, sleep = clock()
        seen, waits = [], []
        end = await sl.follow_job("j1", scripted(answers), seen.append, waits.append, now=now, sleep=sleep, **options)
        return end, [j["state"] for j in seen], waits

    job = lambda state: ("job", sl.parse_job(su_job(state=state)))  # noqa: E731
    end, seen, waits = asyncio.run(follow([job("checking"), ("wait", None), ("wait", None), job("restarting"), ("wait", None), job("done")]))
    check("follower: it keeps asking through the restart and ends with the job that ends", (end[0], end[1]["state"], seen, waits), ("ended", "done", ["checking", "restarting", "done"], [1, 3, 1]))
    end, seen, waits = asyncio.run(follow([job("applying"), job("failed")]))
    check("follower: a failure the job reports is a result, not a silence", (end[0], end[1]["state"], waits), ("ended", "failed", []))
    end, seen, waits = asyncio.run(follow([("wait", None)], silence_limit=10.0, interval=1.0))
    check("follower: it gives up only after the limit of silence, counted from the first look", (end, waits[-1], len(waits)), (("silent", 10), 10, 11))
    end, seen, waits = asyncio.run(follow([job("checking"), ("wait", None)], silence_limit=5.0, interval=1.0))
    check("follower: the silence is counted from the last answer", (end[0], seen, waits[0]), ("silent", ["checking"], 1))
    end, seen, waits = asyncio.run(follow([("stop", None)]))
    check("follower: a refused session stops it", end, ("stopped", "forbidden"))
    state = {"n": 0}

    def cancelled():
        state["n"] += 1
        return state["n"] > 3

    end, seen, waits = asyncio.run(follow([("wait", None)], cancelled=cancelled))
    check("follower: it stops when it is cancelled", end, ("stopped", "cancelled"))


def self_update_screen(loop, port):
    sl = __import__("hydra_suite.panel_logic.self_update", fromlist=["x"])
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port, username="ana", password="pw"))
    conn._token = "tok"
    conn.login_ok = True
    conn.role = "admin"
    controller.connections["s"] = conn
    controller._active_id = "s"
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()
    saved = []
    qs.save_config = lambda update: saved.append(update) or True  # the switch never writes the configuration file of the machine that runs the check
    sl.INTERVAL_S, sl.SILENCE_LIMIT_S = 0.02, 0.4

    def read():
        loop.run_until_complete(bridge._refresh_self_update(True))

    def wait_until(condition, seconds=8.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end and not condition():
            pump(loop, 0.02)
        return condition()

    def server_row(name="server"):
        return next((r for r in bridge.selfUpdateView["rows"] if r["id"] == name), None)

    def ask_and_confirm(action="apply", component="server"):
        SelfUpdateSim.reads = 0
        bridge.requestSelfUpdate(action, component)
        bridge.confirmSelfUpdate()

    SelfUpdateSim.status, SelfUpdateSim.body, SelfUpdateSim.posted = 200, SU_STATUS, []
    read()
    view = bridge.selfUpdateView
    check("updates screen: the three programs, nothing failed, the switch is off", ([r["id"] for r in view["rows"]], view["failure"], view["applyOn"], view["loaded"]), (["server", "studio", "os-agent"], "", False, True))
    check("updates screen: with the switch off no button is on and the mode says check only", ([(r["canUpdate"], r["canGoBack"]) for r in view["rows"]], view["mode"]), ([(False, False)] * 3, _("SELFUPD_MODE_CHECK_ONLY")))
    bridge.requestSelfUpdate("apply", "server")
    check("updates screen: asking with the switch off asks nothing", bridge.selfUpdateView["confirm"], "")
    bridge.setSelfUpdateApply(True)
    check("updates screen: the switch is kept in the configuration and turns the buttons on", (saved, server_row()["canUpdate"], server_row()["canGoBack"], server_row("studio")["canUpdate"]), ([{"self_update_apply": True}], True, True, False))
    bridge.requestSelfUpdate("apply", "studio")
    check("updates screen: a program that is up to date cannot be asked for", bridge.selfUpdateView["confirm"], "")
    bridge.requestSelfUpdate("delete", "server")
    check("updates screen: an action that is not an update or a way back asks nothing", bridge.selfUpdateView["confirm"], "")
    bridge.requestSelfUpdate("apply", "server")
    check("updates screen: the confirmation names the program and the two versions", bridge.selfUpdateView["confirm"], _("SELFUPD_CONFIRM_APPLY", program=_("SELFUPD_COMPONENT_SERVER"), versions="1.0.0 -> 1.1.0"))
    bridge.cancelSelfUpdate()
    pump(loop)
    check("updates screen: cancelling sends nothing", (bridge.selfUpdateView["confirm"], SelfUpdateSim.posted), ("", []))
    bridge.requestSelfUpdate("rollback", "server")
    bridge.setSelfUpdateApply(False)
    check("updates screen: turning the switch off drops a confirmation that waits", (bridge.selfUpdateView["confirm"], saved[-1]), ("", {"self_update_apply": False}))
    bridge.setSelfUpdateApply(True)

    # an update through a restart of the server: a cut connection and a 502 between the answers
    SelfUpdateSim.body = {**SU_STATUS, "items": [su_item("server", installed="1.1.0", previous="1.0.0", latest="1.1.0", state="current"), *SU_STATUS["items"][1:]]}
    SelfUpdateSim.start = (202, su_job(state="checking"))
    SelfUpdateSim.jobs = [(200, su_job("downloading")), None, (502, {}), (200, su_job("restarting")), None, (200, su_job("done"))]
    ask_and_confirm()
    ended = wait_until(lambda: bridge._su_following is None and bridge._su_job is not None and bridge._su_job["state"] == "done" and server_row()["state"] == "current")
    check("updates screen: the confirmation travels with the request", SelfUpdateSim.posted, [("/api/admin/self-update/apply", {"component": "server", "confirm": True})])
    check("updates screen: the job ends done through the restart and the table is read again", (ended, bridge.selfUpdateView["job"].get("done")), (True, _("SELFUPD_DONE_APPLY", version="1.1.0")))
    check("updates screen: every step is done and nothing is said to wait any more", ({s["mark"] for s in bridge.selfUpdateView["job"]["steps"]}, bridge.selfUpdateView["job"]["waiting"]), ({"done"}, ""))
    check("updates screen: an update that has been done cannot be done again", server_row()["canUpdate"], False)

    # a long silence: it says so and offers to look again, which finds the result
    SelfUpdateSim.body = SU_STATUS
    read()
    SelfUpdateSim.start = (202, su_job(state="applying"))
    SelfUpdateSim.jobs = [None]
    ask_and_confirm()
    silent = wait_until(lambda: bridge._su_gave_up)
    view = bridge.selfUpdateView["job"]
    check("updates screen: after the limit of silence it says so and is not stuck", (silent, view["gaveUp"], view["waiting"], view["running"]), (True, _("SELFUPD_GAVE_UP"), "", True))
    SelfUpdateSim.reads, SelfUpdateSim.jobs = 0, [(200, su_job("failed", error="rolled_back", detail="unit did not answer"))]
    bridge.lookAgainSelfUpdate()
    wait_until(lambda: bridge._su_job is not None and bridge._su_job["state"] == "failed" and bridge._su_following is None)
    view = bridge.selfUpdateView["job"]
    check("updates screen: looking again finds the failure and says why and what was put back", (view["failed"], view["detail"], view["gaveUp"]), (_("SELFUPD_ERR_ROLLED_BACK"), "unit did not answer", ""))

    # why it could not start
    for status, reason in ((409, "busy"), (404, "disabled"), (403, "forbidden"), (500, "refused")):
        SelfUpdateSim.start = (status, {})
        SelfUpdateSim.posted = []
        read()
        ask_and_confirm()
        wait_until(lambda: bridge.selfUpdateView["message"] != "")
        check(f"updates screen: a {status} on start says {reason}", (bridge.selfUpdateView["message"], len(SelfUpdateSim.posted)), (_("SELFUPD_START_" + reason.upper()), 1))
        bridge.requestSelfUpdate("apply", "server")
        check(f"updates screen: asking again clears the old message ({status})", bridge.selfUpdateView["message"], "")
        bridge.cancelSelfUpdate()

    # the two switches: the server with applying off wins over the switch of this program
    SelfUpdateSim.body = {**SU_STATUS, "applyEnabled": False}
    read()
    check("updates screen: a server with applying off allows nothing, whatever this program says", ([(r["canUpdate"], r["canGoBack"]) for r in bridge.selfUpdateView["rows"]], bridge.selfUpdateView["mode"]), ([(False, False)] * 3, _("SELFUPD_MODE_SERVER_OFF")))
    # a job that was going on when the screen was opened is picked up
    SelfUpdateSim.reads, SelfUpdateSim.jobs = 0, [(200, su_job("applying")), (200, su_job("done"))]
    SelfUpdateSim.body = {**SU_STATUS, "job": su_job("applying")}
    read()
    check("updates screen: a job that was going on is shown at once", (bridge.selfUpdateView["job"]["running"], bridge.selfUpdateView["canCheck"]), (True, False))
    check("updates screen: it is followed to its end", wait_until(lambda: bridge._su_job["state"] == "done" and bridge._su_following is None), True)

    # what the screen says when the table cannot be read
    for status, kind, sentence in ((404, "unsupported", _("SELFUPD_UNSUPPORTED")), (403, "forbidden", _("SELFUPD_FORBIDDEN")), (500, "http", _("SELFUPD_LOAD_ERROR"))):
        SelfUpdateSim.status, SelfUpdateSim.body = status, {}
        read()
        view = bridge.selfUpdateView
        check(f"updates screen: a {status} says {kind} and shows no program", (view["failure"], view["rows"], view["loaded"]), (sentence, [], False))
    SelfUpdateSim.status, SelfUpdateSim.body = 200, {"items": "x"}
    read()
    check("updates screen: an answer that is not the table says it could not be read", (bridge.selfUpdateView["failure"], bridge.selfUpdateView["rows"]), (_("SELFUPD_LOAD_ERROR"), []))
    SelfUpdateSim.body = SU_STATUS
    bridge._su_status = None
    bridge.navigatePanel("updates")
    check("updates screen: opening the screen reads the table", wait_until(lambda: bridge.selfUpdateView["loaded"]), True)
    controller._active_id = None
    read()
    check("updates screen: no server selected", (bridge.selfUpdateView["failure"], bridge.selfUpdateView["rows"]), (_("LBL_ES_NO_ACTIVE_SERVER"), []))


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logic()
    screen(loop, server.server_address[1])
    switch(loop)
    self_update_logic()
    self_update_screen(loop, server.server_address[1])
    server.shutdown()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
