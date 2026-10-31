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
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
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

    def do_GET(self):
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

    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    sent = []

    async def save(patch):
        sent.append(patch)

    bridge._save_security = save
    bridge.saveEcosystemHealthOptions(True)
    pump(loop)
    check("switch: nothing is sent before the server showed the option", sent, [])
    bridge._security_state = off
    bridge.saveEcosystemHealthOptions(True)
    pump(loop)
    check("switch: turning it on sends the patch", sent, [{"ecosystemHealth": {"enabled": True}}])


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logic()
    screen(loop, server.server_address[1])
    switch(loop)
    server.shutdown()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
