# =============================================================================
# HYDRA-UMC SUITE - tests/verify_downsample_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The editor of the tier plan of the data lake (Telemetry screen, administrators):
#   - the durations, the shape rules, the coherence rules and the kinds, strict like the data lake's own
#   - the document sent and the reading of the answers (by the code of the data lake, never its text)
#   - the screen against a simulated server: the plan is shown, a bad plan is refused next to its cell and cannot be saved, a save
#     asks the data lake first (a preview), shows the effects, asks for a confirmation and sends the hash it read; a plan changed
#     by somebody else, a 404, a 403 and a failed read have their own sentences; deletion stays off unless the operator allowed it
#   - every sentence exists in the eight languages
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import downsample_plan as dp

try:  # the screen needs Qt; the rules above do not, so they are still checked on a machine without it
    import qasync
    from PySide6.QtGui import QGuiApplication

    import qt_suite as qs
    from hydra_suite.app import SuiteController
    from hydra_suite.models import ServerInfo
    from hydra_suite.net.client import HydraConnection

    HAVE_QT = True
except ImportError as error:
    print(f"skip the screen checks: {error}")
    HAVE_QT = False

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def tier(**over):
    return {**dp.empty_tier(), "kind": "motor_temp", "raw": "2d", "bucket": "1h", **over}


def codes(rows, kinds=("motor_temp", "vibration")):
    return [i["code"] for i in dp.validate_plan(rows, None if kinds is None else list(kinds))]


def logic():
    check("durations", [dp.parse_duration(x) for x in ("90s", " 1H ", "2w", "5y", "1500")], [90_000, 3_600_000, 1_209_600_000, 157_680_000_000, 1500])
    check("durations refused", [dp.parse_duration(x) for x in ("", "x", "1.5h", "-1h", "0", "0d", "1 h", "1hh", "101y", "١٢h")], [None] * 10)
    check("durations shown", [dp.format_duration(x) for x in (3_600_000, 172_800_000, 90_000, 1500)], ["1h", "2d", "90s", "1500"])
    full = [tier(fineBucket="1m", rollupRetention="5y", fineRetention="30d"), tier(kind="*", field="*", raw="30d", bucket="1d")]
    check("a plan that fits together", dp.validate_plan(full, ["motor_temp"]), [])
    check("bucket as long as raw and retention as long as raw are fine", codes([tier(raw="1d", bucket="1d", rollupRetention="1d")]), [])
    check("kinds are not checked until known", codes([tier(kind="anything")], None), [])
    check("no tiers, too many tiers", (codes([]), codes([tier(field=f"f{i}") for i in range(1001)])), (["no_tiers"], ["too_many_tiers"]))
    check("kind and field", (codes([tier(kind="")]), codes([tier(field="")]), codes([tier(kind="*", field="x")])), (["kind_missing"], ["field_missing"], ["default_needs_star_field"]))
    check("a tier twice names the second", dp.validate_plan([tier(), tier()], ["motor_temp"]), [{"tier": 1, "key": "kind", "code": "duplicate", "params": {"kind": "motor_temp", "field": "*"}}])
    check("raw and bucket are required, a duration must be readable", (codes([tier(raw="", bucket="")]), dp.validate_plan([tier(bucket="1.5h")], None)),
          (["required", "required"], [{"tier": 0, "key": "bucket", "code": "bad_duration", "params": {"value": "1.5h"}}]))
    check("narrow width", (codes([tier(fineBucket="1h")]), codes([tier(fineBucket="7m")]), codes([tier(raw="30d", bucket="2d", fineBucket="1s")]), codes([tier(bucket="1d", fineBucket="1m")])),
          (["fine_not_smaller"], ["fine_not_divisor"], ["fine_too_many"], []))
    check("narrow retention", (codes([tier(fineRetention="3d")]), codes([tier(kind="*", field="*", fineBucket="1m", fineRetention="3d")]), codes([tier(fineBucket="1m", rollupRetention="30d", fineRetention="60d")])),
          (["fine_retention_needs_fine"], ["fine_retention_on_default"], ["fine_retention_longer"]))
    check("coherence", (codes([tier(raw="1h", bucket="1d")]), codes([tier(rollupRetention="1d")]), codes([tier(fineBucket="1m", fineRetention="1d")])),
          (["bucket_longer_than_raw"], ["rollup_shorter_than_raw"], ["fine_retention_shorter_than_raw"]))
    check("every incoherent row is listed", [(i["tier"], i["code"]) for i in dp.validate_plan([tier(raw="1h", bucket="1d"), tier(field="b", rollupRetention="1h")], ["motor_temp"])],
          [(0, "bucket_longer_than_raw"), (1, "rollup_shorter_than_raw")])
    check("coherence waits for the shape", codes([tier(raw="1h", bucket="1d"), tier(field="b", raw="")]), ["required"])
    check("an unknown kind, the default tier excepted", codes([tier(kind="ghost"), tier(kind="*", field="*")]), ["unknown_kind"])
    check("the document sent", dp.draft_to_plan([tier(raw="172800000", bucket=" 1H ", fineBucket="1m")], True),
          {"tiers": [{"kind": "motor_temp", "field": "*", "raw": 172800000, "bucket": "1h", "fineBucket": "1m"}], "delete": True})
    rows, delete = dp.plan_to_draft({"tiers": [{"kind": "a", "raw": 172_800_000, "bucket": "1h"}], "delete": True})
    check("the plan read", (rows[0]["raw"], rows[0]["field"], rows[0]["bucket"], delete), ("2d", "*", "1h", True))
    check("a plan that is not one", (dp.plan_to_draft(None), dp.plan_to_draft({"tiers": [{"field": "x"}]})), (None, None))
    check("failures by code", [dp.failure_for(s, b) for s, b in ((409, {"code": "plan_changed"}), (422, {"code": "incoherent_plan"}), (403, {"code": "delete_not_allowed"}), (404, None), (403, {"error": "x"}), (401, None), (503, {}), (418, None))],
          ["plan_changed", "incoherent_plan", "delete_not_allowed", "off", "forbidden", "forbidden", "unreachable", "http"])
    codes_needed = [c.upper() for c in dp.CODED_FAILURES]
    issue_codes = ["NO_TIERS", "TOO_MANY_TIERS", "KIND_MISSING", "FIELD_MISSING", "DEFAULT_NEEDS_STAR_FIELD", "DUPLICATE", "REQUIRED", "BAD_DURATION", "FINE_NOT_SMALLER", "FINE_NOT_DIVISOR",
                   "FINE_TOO_MANY", "FINE_RETENTION_NEEDS_FINE", "FINE_RETENTION_ON_DEFAULT", "FINE_RETENTION_LONGER", "BUCKET_LONGER_THAN_RAW", "ROLLUP_SHORTER_THAN_RAW",
                   "FINE_RETENTION_SHORTER_THAN_RAW", "UNKNOWN_KIND"]
    keys = ["PLAN_ERROR_" + c for c in codes_needed] + ["PLAN_ISSUE_" + c for c in issue_codes]
    keys += ["PLAN_" + k for k in ("TITLE DESC OFF FORBIDDEN UNREACHABLE NETWORK MALFORMED HTTP RELOAD COL_KIND COL_FIELD COL_RAW COL_BUCKET COL_FINE COL_KEEP COL_FINE_KEEP ADD_TIER REMOVE_TIER "
                                  "DURATION_HINT DELETE_LABEL DELETE_DISABLED DELETE_WARNING MODE_DRYRUN MODE_DELETE STRICT_NOTE VALID INVALID_COUNT ROW PREVIEW SAVE SAVED UNCHANGED "
                                  "CONFIRM_TITLE CONFIRM_MESSAGE CONFIRM_DELETE_MESSAGE EFFECTS CHANGES AUDIT_TITLE AUDIT_NONE AUDIT_ENTRY KNOWN_KINDS CONFIRM_SAVE CONFIRM_CANCEL PREVIEWED").split()]
    check("every sentence exists", [k for k in keys if _(k) == k], [])


PLAN = {
    "plan": {"tiers": [{"kind": "motor_temp", "field": "*", "raw": 172_800_000, "bucket": 3_600_000}], "delete": False},
    "hash": "h1", "knownKinds": ["motor_temp", "vibration"],
    "switches": {"allowDelete": False, "effectiveMode": "dryRun", "fineRollups": True},
    "audit": [{"atMs": 1_700_000_000_000, "event": "plan_saved", "client": "127.0.0.1", "tiers": 1}],
}


class Server:
    get_status, get_body = 200, PLAN
    put_status, put_body = 200, {"saved": True, "hash": "h2", "changes": [{}], "effects": {"totals": {"rawPointsToRollUp": 7, "rollupsToExpire": 0, "fineRollupsToExpire": 0}}}
    puts: list = []
    hang_up = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlparse(self.path).path != "/api/telemetry/downsample-plan":
            return self._send(404, {})
        if Server.hang_up:
            self.connection.close()
            return
        self._send(Server.get_status, Server.get_body)

    def do_PUT(self):
        parsed = urlparse(self.path)
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        Server.puts.append({"preview": parse_qs(parsed.query).get("preview") == ["1"], "body": json.loads(raw or b"{}")})
        self._send(Server.put_status, Server.put_body)


def pump(loop, seconds=0.05):
    loop.run_until_complete(asyncio.sleep(seconds))


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

    def load():
        loop.run_until_complete(bridge._load_downsample_plan())

    check("screen: not shown to an operator", bridge.planVisible, False)
    conn.role = "admin"
    check("screen: shown to an administrator", bridge.planVisible, True)
    load()
    check("screen: the plan is shown, valid, nothing to save", (bridge.planLoaded, bridge.planStructure, bridge.planCell(0, "raw"), bridge.planValid, bridge.planCanSave), (True, [0], "2d", True, False))
    check("screen: dry run badge, deletion disabled, the audit line", (bridge.planModeText, bridge.planAllowDelete, len(bridge.planAuditLines)), (_("PLAN_MODE_DRYRUN"), False, 1))
    bridge.setPlanDelete(True)
    check("screen: deletion cannot be turned on without the option of the operator", bridge.planDeleteOn, False)

    bridge.setPlanCell(0, "bucket", "30d")
    check("screen: an incoherent plan is refused next to its cell and cannot be saved",
          (bridge.planValid, bridge.planCanSave, bridge.planCellBad(0, "bucket"), bridge.planCellBad(0, "raw"), bridge.planIssueLines),
          (False, False, True, False, [_("PLAN_ROW", row=1) + ": " + _("PLAN_ISSUE_BUCKET_LONGER_THAN_RAW")]))
    Server.puts.clear()
    bridge.requestSaveDownsamplePlan()
    pump(loop)
    check("screen: an invalid plan sends nothing", Server.puts, [])
    bridge.setPlanCell(0, "bucket", "1h")
    check("screen: back to the plan of the data lake, nothing to save", bridge.planCanSave, False)
    bridge.setPlanCell(0, "kind", "ghost")
    check("screen: an unknown kind is refused", bridge.planIssueLines, [_("PLAN_ROW", row=1) + ": " + _("PLAN_ISSUE_UNKNOWN_KIND", kind="ghost")])
    bridge.setPlanCell(0, "kind", "motor_temp")

    bridge.setPlanCell(0, "raw", "3d")
    check("screen: a changed valid plan can be saved", bridge.planCanSave, True)
    loop.run_until_complete(bridge._put_downsample_plan(preview=True, then_confirm=True))
    check("screen: the data lake is asked first (preview), the effects are shown and a confirmation is asked",
          (len(Server.puts), Server.puts[0]["preview"], bridge.planConfirming, _("PLAN_EFFECTS", raw=7, rollups=0, fine=0) in bridge.planEffectsText),
          (1, True, True, True))
    bridge.cancelSaveDownsamplePlan()
    check("screen: cancelling sends nothing more", (bridge.planConfirming, len(Server.puts)), (False, 1))
    loop.run_until_complete(bridge._put_downsample_plan(preview=True, then_confirm=True))
    bridge._plan_confirming = False
    loop.run_until_complete(bridge._put_downsample_plan(preview=False, then_confirm=False))
    save = Server.puts[-1]
    check("screen: the save sends the hash that was read and the plan, without confirmDelete",
          (save["preview"], save["body"]["expectedHash"], save["body"]["confirmDelete"], save["body"]["plan"]["tiers"][0]["raw"]), (False, "h1", False, "3d"))
    check("screen: saved", bridge.planNoticeText, _("PLAN_SAVED"))

    Server.put_status, Server.put_body = 409, {"code": "plan_changed", "error": "x", "details": ["current hash zzz"]}
    bridge.setPlanCell(0, "raw", "4d")
    loop.run_until_complete(bridge._put_downsample_plan(preview=True, then_confirm=True))
    check("screen: a plan changed by somebody else says so, with its details", (bridge.planFailureText, bridge.planConfirming), (_("PLAN_ERROR_PLAN_CHANGED") + "\ncurrent hash zzz", False))
    Server.put_status, Server.put_body = 422, {"code": "incoherent_plan", "details": ["a"]}
    loop.run_until_complete(bridge._put_downsample_plan(preview=True, then_confirm=True))
    check("screen: the data lake refusing the coherence is shown", bridge.planFailureText, _("PLAN_ERROR_INCOHERENT_PLAN") + "\na")

    Server.get_body = {**PLAN, "switches": {"allowDelete": True, "effectiveMode": "dryRun", "fineRollups": True}}
    load()
    bridge.setPlanDelete(True)
    check("screen: with the option of the operator deletion can be asked for, and the confirmation is the red one",
          (bridge.planAllowDelete, bridge.planDeleteOn, bridge.planCanSave, bridge.planConfirmText), (True, True, True, _("PLAN_CONFIRM_DELETE_MESSAGE")))
    Server.put_status, Server.put_body = 200, {"saved": True, "hash": "h3", "changes": [], "effects": {"totals": {}}}
    loop.run_until_complete(bridge._put_downsample_plan(preview=True, then_confirm=True))
    check("screen: turning deletion on sends confirmDelete", Server.puts[-1]["body"]["confirmDelete"], True)

    for label, status, body, sentence in (
        ("404: the data lake does not offer it", 404, {"error": "not found"}, _("PLAN_OFF")),
        ("403: not an administrator", 403, {"error": "admin"}, _("PLAN_FORBIDDEN")),
        ("503: not configured", 503, {"available": False}, _("PLAN_UNREACHABLE")),
        ("500: a failed read", 500, {}, _("PLAN_HTTP", status=500)),
        ("200 with nonsense", 200, {"plan": "x", "hash": 3}, _("PLAN_MALFORMED")),
    ):
        Server.get_status, Server.get_body = status, body
        load()
        check(f"screen: {label}", (bridge.planFailureText, bridge.planLoaded), (sentence, False))
    Server.hang_up = True
    load()
    check("screen: no answer at all", bridge.planFailureText, _("PLAN_NETWORK"))
    Server.hang_up = False


def main():
    if not HAVE_QT:
        logic()
        print("FAILURES:", failures)
        return 1 if failures else 0
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logic()
    screen(loop, server.server_address[1])
    server.shutdown()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
