# =============================================================================
# HYDRA-UMC SUITE - tests/verify_bridge_access.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# What the Qt Quick interface shows and does about access and safety, with a fake connection (no network):
#   - Live or Sim of the selected robot, kept in the configuration, and the browser-wide default
#   - where the selected robot stands (free, mine, mine elsewhere, someone else's), the buttons that apply, the list
#     of reservations, the renewal of a reservation of this program
#   - every refusal reaches the operator as a notice with its own sentence, and nothing is silent
#   - the arming of the jog, only offered when the administrator requires it
#   - the safety limits screen: only for administrators, the form shows what the server holds, a wrong value is
#     refused before anything is sent, a good one is sent and confirmed
#   - the joint sliders follow the range of the model, and a heated bed target follows the ceiling of the server
#   - the Robots Catalog and the System Supervisor, now Qt Quick panels
#   - the application menu: language, About
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import sys
import time

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import qt_suite as qs
from hydra_suite import access
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import AccessResult, HydraConnection

failures = 0
SAVED_CONFIG: list = []


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def make(role="operator"):
    access.reset_controller_id("suite-here")
    access.MODES.modes.clear()
    access.MODES.default_mode = "live"
    SAVED_CONFIG.clear()
    qs.save_config = lambda updates: (SAVED_CONFIG.append(updates), True)[1]
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    conn = HydraConnection(ServerInfo(host="10.0.0.9", port=3000, username="ana", password="pw"))
    conn.login_ok = True
    conn.role = role
    conn.state = HydraState({
        "activeControllerId": "c1",
        "settings": {},
        "controllers": [{"id": "c1", "robots": [
            {"id": 1, "name": "Parol", "model": "Parol6 (6-DOF)", "role": "Idle"},
            {"id": 2, "name": "Zed", "model": "Z1 (6-DOF)", "role": "Idle"},
        ]}],
    })
    controller.connections["10.0.0.9:3000"] = conn
    controller._active_id = "10.0.0.9:3000"
    controller.active_state_changed.emit(conn.state)
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()
    bridge.selectRobot("1")
    return controller, bridge, conn


async def nothing_to_refresh(*args, **kwargs):
    return True


def claim(robot_id, user, controller_id, seconds=120):
    now = time.time() * 1000
    return access.ClaimEntry(robot_id, robot_name="Parol", owner_username=user, controller_id=controller_id, claimed_at=now, expires_at=now + seconds * 1000)


def pump(loop, seconds=0.05):
    loop.run_until_complete(asyncio.sleep(seconds))


def live_and_sim(loop):
    controller, bridge, conn = make()
    check("mode: Live by default", (bridge.selectedRobotMode, bridge.defaultRobotModeSim), ("live", False))
    bridge.setSelectedRobotMode("sim")
    check("mode: Sim for the selected robot", bridge.selectedRobotMode, "sim")
    check("mode: and it is kept in the configuration", SAVED_CONFIG[-1]["robotModes"], {"10.0.0.9:3000#1": "sim"})
    bridge.selectRobot("2")
    check("mode: another robot is still Live", bridge.selectedRobotMode, "live")
    bridge.setDefaultRobotModeSim(True)
    check("mode: a browser can start the rest in Sim", (bridge.selectedRobotMode, SAVED_CONFIG[-1]["defaultRobotMode"]), ("sim", "sim"))
    bridge.setSelectedRobotMode("live")
    check("mode: an explicit Live wins over that default", bridge.selectedRobotMode, "live")
    bridge.setSelectedRobotMode("nonsense")
    check("mode: an unknown mode changes nothing", bridge.selectedRobotMode, "live")
    return controller


def reservations(loop):
    controller, bridge, conn = make()
    conn.refresh_access = nothing_to_refresh
    check("access: free", (bridge.selectedRobotAccess["standing"], bridge.selectedRobotAccess["canReserve"], bridge.selectedRobotAccess["canRelease"], bridge.selectedRobotAccess["text"]), ("free", True, False, _("ACCESS_FREE")))

    conn.claims = [claim(1, "ana", "suite-here")]
    a = bridge.selectedRobotAccess
    check("access: mine", (a["standing"], a["canReserve"], a["canRelease"], a["canTakeOver"]), ("mine", False, True, False))
    check("access: with the time left", ("1:5" in a["text"] or "1:59" in a["text"] or "2:00" in a["text"]), True)

    conn.claims = [claim(1, "ana", "suite-other")]
    a = bridge.selectedRobotAccess
    check("access: the same account on another controller", (a["standing"], a["text"], a["canReserve"], a["canTakeOver"]), ("other-controller", _("ACCESS_HELD_BY_ME_ELSEWHERE"), False, False))

    conn.claims = [claim(1, "bob", "suite-x")]
    a = bridge.selectedRobotAccess
    check("access: another account", (a["standing"], a["text"], a["canTakeOver"]), ("other-account", _("ACCESS_HELD_BY_OTHER", user="bob"), False))
    conn.role = "admin"
    check("access: an administrator may take over", bridge.selectedRobotAccess["canTakeOver"], True)
    conn.role = "operator"
    conn.login_ok = False
    check("access: nothing to press until signed in", (bridge.selectedRobotAccess["canTakeOver"], bridge.selectedRobotAccess["canRelease"]), (False, False))
    conn.login_ok = True

    conn.claims = [claim(1, "ana", "suite-here"), claim(2, "bob", None)]
    rows = bridge.claimsRows
    check("list: every reservation", [(r["owner"], r["mine"]) for r in rows], [("ana", True), ("bob", False)])
    check("list: a reservation with no controller says so", _("ACCESS_NO_CONTROLLER") in rows[1]["controller"], True)
    check("list: this program is named", _("ACCESS_THIS_PROGRAM") in rows[0]["controller"], True)

    # --- actions reach the connection, and a refusal reaches the operator ---
    calls = []

    async def claim_robot(robot_id, **kwargs):
        calls.append(("claim", robot_id, kwargs))
        return results["claim"]

    async def release_robot(robot_id, reason=""):
        calls.append(("release", robot_id))
        return AccessResult(True, 200)

    results = {"claim": AccessResult(True, 200)}
    conn.claim_robot = claim_robot
    conn.release_robot = release_robot
    conn.claims = []
    bridge.claimSelectedRobot()
    pump(loop)
    check("action: reserve", calls[-1], ("claim", 1, {}))
    check("action: and no notice when it worked", bridge.noticeText, "")
    bridge.releaseSelectedRobot()
    pump(loop)
    check("action: release", calls[-1], ("release", 1))
    for code, key in (("claim_other_account", "MSG_ACCESS_CLAIM_OTHER_ACCOUNT"), ("claim_other_controller", "MSG_ACCESS_CLAIM_OTHER_CONTROLLER"), ("claim_controller_required", "MSG_ACCESS_CLAIM_CONTROLLER_REQUIRED"), ("jog_not_armed", "MSG_ACCESS_JOG_NOT_ARMED"), ("session_expired", "MSG_ACCESS_SESSION_EXPIRED"), ("forbidden", "MSG_ACCESS_FORBIDDEN"), ("network", "MSG_ACCESS_NETWORK"), ("weird_new_code", "MSG_ACCESS_REJECTED")):
        results["claim"] = AccessResult(False, 409, code, "held by x")
        bridge.dismissNotice()
        bridge.claimSelectedRobot()
        pump(loop)
        check(f"refusal {code}: its own sentence", bridge.noticeText, _(key, what=_("ACCESS_WHAT_RESERVE"), detail="held by x"))
    sentences = {_(f"MSG_ACCESS_{c}", what="a", detail="b") for c in ("CLAIM_OTHER_ACCOUNT", "CLAIM_OTHER_CONTROLLER", "CLAIM_CONTROLLER_REQUIRED", "JOG_NOT_ARMED")}
    check("refusal: the four reservation sentences differ", len(sentences), 4)

    calls.clear()
    bridge.takeOverSelectedRobot()
    pump(loop)
    check("action: an operator cannot take over", calls, [])
    conn.role = "admin"
    results["claim"] = AccessResult(True, 200)
    bridge.takeOverSelectedRobot()
    pump(loop)
    check("action: an administrator takes over with force", calls[-1], ("claim", 1, {"force": True}))

    # --- a reservation of this program is renewed before it ends ---
    conn.role = "operator"
    renewals = []

    async def refresh_with_claim(robot_id=None, claims=True):
        conn.claims = [claim(1, "ana", "suite-here", seconds=30)]
        return True

    async def renewing_claim(robot_id, **kwargs):
        renewals.append(robot_id)
        conn.claims = [claim(1, "ana", "suite-here", seconds=300)]
        return AccessResult(True, 200)

    conn.refresh_access = refresh_with_claim
    conn.claim_robot = renewing_claim
    loop.run_until_complete(bridge._refresh_access())
    check("renewal: a reservation of this program about to end is renewed", renewals, [1])
    check("renewal: and shows the new time", bridge.selectedRobotAccess["standing"], "mine")
    renewals.clear()
    conn.claims = []

    async def refresh_other(robot_id=None, claims=True):
        conn.claims = [claim(1, "bob", "suite-x", seconds=30)]
        return True

    conn.refresh_access = refresh_other
    loop.run_until_complete(bridge._refresh_access())
    check("renewal: someone else's reservation is never renewed", renewals, [])


def arming(loop):
    controller, bridge, conn = make()
    check("arming: not offered when the administrator does not require it", bridge.jogArmRequired, False)
    conn.safety = access.parse_safety_limits({"limits": {"jog": {"armRequired": True}}})
    check("arming: offered when required", bridge.jogArmRequired, True)
    check("arming: can be pressed on a free robot", bridge.selectedRobotArm["canToggle"], True)
    conn.claims = [claim(1, "bob", "suite-x")]
    check("arming: not on a robot someone else holds", bridge.selectedRobotArm["canToggle"], False)
    conn.claims = []
    sent = []

    async def arm_jog(robot_id, armed, ttl_ms=None):
        sent.append((robot_id, armed))
        conn.jog_armed_until[robot_id] = time.time() * 1000 + 30000 if armed else None
        return AccessResult(True, 200)

    async def refresh(robot_id=None, claims=True):
        return True

    conn.arm_jog = arm_jog
    conn.refresh_access = refresh
    bridge.toggleJogArm()
    pump(loop)
    check("arming: pressing arms", (sent, bridge.selectedRobotArm["armed"], 28 <= bridge.selectedRobotArm["seconds"] <= 30), ([(1, True)], True, True))
    bridge.toggleJogArm()
    pump(loop)
    check("arming: pressing again disarms", (sent[-1], bridge.selectedRobotArm["armed"]), ((1, False), False))


def safe_mode(loop):
    controller, bridge, conn = make()
    mode = bridge.selectedRobotSafeMode
    check("safe mode: an enabled robot can be disabled by anyone signed in, not enabled", (mode["disabled"], mode["canDisable"], mode["canEnable"], mode["text"]), (False, True, False, ""))
    conn.state.active_controller.robot_by_id("1").raw["enabled"] = False
    mode = bridge.selectedRobotSafeMode
    check("safe mode: a disabled robot says so and an operator cannot enable it", (mode["disabled"], mode["canDisable"], mode["canEnable"], mode["text"]), (True, False, False, _("ACCESS_SAFE_MODE_BADGE")))
    conn.role = "admin"
    check("safe mode: an administrator is offered the enable", bridge.selectedRobotSafeMode["canEnable"], True)
    conn.login_ok = False
    check("safe mode: nothing to press until signed in", (bridge.selectedRobotSafeMode["canDisable"], bridge.selectedRobotSafeMode["canEnable"]), (False, False))
    conn.login_ok = True
    sent = []

    async def set_robot_enabled(robot_id, enable):
        sent.append((robot_id, enable))
        return AccessResult(True, 200)

    async def refresh(robot_id=None, claims=True):
        return True

    conn.set_robot_enabled = set_robot_enabled
    conn.refresh_access = refresh
    bridge.enableSelectedRobot()
    pump(loop)
    check("safe mode: the enable reaches the connection", sent, [(1, True)])
    conn.role = "operator"
    bridge.enableSelectedRobot()
    pump(loop)
    check("safe mode: an operator's enable is not even sent", sent, [(1, True)])
    conn.state.active_controller.robot_by_id("1").raw["enabled"] = True
    bridge.disableSelectedRobot()
    pump(loop)
    check("safe mode: the disable reaches the connection", sent[-1], (1, False))
    results = {"r": AccessResult(False, 403, "enable_not_allowed", "off")}

    async def refused(robot_id, enable):
        return results["r"]

    conn.set_robot_enabled = refused
    for code, key in (("enable_not_allowed", "MSG_ACCESS_ENABLE_NOT_ALLOWED"), ("admin_required", "MSG_ACCESS_ADMIN_REQUIRED"), ("robot_disabled", "MSG_ACCESS_ROBOT_DISABLED")):
        results["r"] = AccessResult(False, 403, code, "x")
        bridge.disableSelectedRobot()
        pump(loop)
        check(f"safe mode: {code} is said in its own sentence", bridge.noticeText, _(key, what=_("ACCESS_WHAT_DISABLE"), detail="x"))


def safety_screen(loop):
    controller, bridge, conn = make()
    check("safety: an operator is told it is for administrators", (bridge.safetyIsAdmin, bridge.safetyHasServer), (False, True))
    bridge.saveSafetyLimits(access.form_from_limits(conn.safety.limits))
    check("safety: and cannot save", bridge.safetyError, _("MSG_ADMIN_ONLY"))
    conn.role = "admin"
    conn.safety = access.parse_safety_limits({"limits": {"jog": {"models": {"parol6": {"maxAmount": 20}}}}, "hardLimits": {"bedMaxC": 250}})
    form = bridge.safetyForm
    check("safety: the form shows what the server holds", (form["defaultMaxAmount"], [r["model"] for r in form["rows"]], form["rows"][0]["maxAmount"]), ("100", ["parol6"], "20"))
    check("safety: and the ceilings", (bridge.safetyHard["bedMaxC"], bridge.safetyHard["jogMaxAmount"]), (250, 1000))
    puts = []

    async def put_safety_limits(patch):
        puts.append(patch)
        conn.safety = access.parse_safety_limits({"limits": {"claims": {"requireControllerId": True}}})
        return AccessResult(True, 200, body={})

    conn.put_safety_limits = put_safety_limits
    wrong = dict(form, defaultMaxAmount="5000")
    bridge.saveSafetyLimits(wrong)
    check("safety: a value over the ceiling is refused before anything is sent", (puts, bridge.safetyError), ([], _("MSG_SAFETY_PROBLEM_RANGE", field="defaultMaxAmount")))
    bridge.saveSafetyLimits(dict(form, defaultMaxAmount="abc"))
    check("safety: a value that is not a number", bridge.safetyError, _("MSG_SAFETY_PROBLEM_NUMBER", field="defaultMaxAmount"))
    bridge.saveSafetyLimits(dict(form, requireControllerId=True, defaultMaxAmount="50"))
    pump(loop)
    check("safety: a good form is sent", (len(puts), puts[0]["claims"]["requireControllerId"], puts[0]["jog"]["default"]["maxAmount"]), (1, True, 50.0))
    check("safety: and confirmed", (bridge.safetyMessage, bridge.safetyError, bridge.safetyForm["requireControllerId"]), (_("MSG_SAFETY_SAVED"), "", True))

    async def refusing_put(patch):
        return AccessResult(False, 400, "rejected", "armTtlMs out of range")

    conn.put_safety_limits = refusing_put
    bridge.saveSafetyLimits(dict(form))
    pump(loop)
    check("safety: a refusal of the server is shown", bridge.safetyError, _("MSG_SAFETY_SAVE_FAILED", detail="armTtlMs out of range"))
    check("safety: the defaults of the server can be loaded into the form", bridge.safetyDefaultsForm()["defaultMaxAmount"], "100")
    check("safety: no server at all", (qs.SuiteQtBridge(SuiteController()).safetyHasServer,), (False,))


def joints_and_bed(loop):
    controller, bridge, conn = make()
    rows = {r["name"]: r for r in bridge.selectedRobotJoints}
    check("joints: a Parol6 base turns -97.4 to 187.4 degrees", (rows["j1"]["min"], rows["j1"]["max"]), (-97.4, 187.4))
    bridge.selectRobot("2")
    rows = {r["name"]: r for r in bridge.selectedRobotJoints}
    check("joints: a model with no published range gets the generic one", (rows["j1"]["min"], rows["j1"]["max"]), (-180.0, 180.0))
    bridge.selectRobot("1")
    sent = []

    async def send_command(robot_id, command, params=None, local_mutate=None, debounce_ms=0):
        sent.append(params)

    conn.send_command = send_command
    bridge.setJoint("j1", 500)
    pump(loop)
    check("joints: a slider value beyond the range is clamped to it", sent[-1]["joints"]["j1"], 187.4)
    bridge.setJoint("j1", -500)
    pump(loop)
    check("joints: and the other end", sent[-1]["joints"]["j1"], -97.4)

    # --- the heated bed follows the ceiling the server reports ---
    conn.safety = access.parse_safety_limits({"limits": {"temperature": {"default": {"bedMaxC": 100}, "models": {"parol6": {"bedMaxC": 80}}}}})
    check("bed: the Kinematic Brain Stage uses the highest ceiling", bridge.kbsBedCeiling, 100)
    check("bed: a target above it is lowered", (access.clamp_bed_target(300, bridge._bed_ceiling()), access.clamp_bed_target(60, bridge._bed_ceiling())), (100, 60))
    bridge.navigatePanel("heated_bed")
    check("bed: the heated bed screen uses the ceiling of its robot's model", bridge.moduleBedCeiling in (80, 100), True)


def catalog_and_supervisor(loop):
    controller, bridge, conn = make()
    pushes = []

    async def push_state():
        pushes.append(1)

    conn.push_state = push_state
    bridge.navigatePanel("robots_catalog")
    rows = bridge.catalogRows
    check("catalog: every model is listed, all enabled", (len(rows), all(r["enabled"] for r in rows)), (len(qs.REAL_ROBOT_MODELS), True))
    bridge.setCatalogManufacturer("Annin Robotics")
    check("catalog: filtered by manufacturer", {r["manufacturer"] for r in bridge.catalogRows}, {"Annin Robotics"})
    bridge.setCatalogDof(5)
    check("catalog: and by degrees of freedom", bridge.catalogRows, [])
    bridge.setCatalogManufacturer("__all__")
    check("catalog: 5-DOF models only", all("5-DOF" in r["model"] for r in bridge.catalogRows), True)
    bridge.setCatalogDof(0)
    bridge.selectCatalogModel("AR3 (6-DOF)")
    check("catalog: selecting a model", (bridge.catalogSelected, [r["selected"] for r in bridge.catalogRows].count(True)), ("AR3 (6-DOF)", 1))
    bridge.selectCatalogModel("Nonexistent")
    check("catalog: an unknown model is ignored", bridge.catalogSelected, "AR3 (6-DOF)")
    bridge.setCatalogModelEnabled("AR3 (6-DOF)", False)
    pump(loop)
    check("catalog: switching a model off disables only that one and pushes", ([r["model"] for r in bridge.catalogRows if not r["enabled"]], len(pushes) >= 1), (["AR3 (6-DOF)"], True))
    check("catalog: the preview needs the provider; without one it stays quiet", bridge.catalogPreviewError, "")

    # --- supervisor ---
    snapshot = {
        "timestamp": 1000, "uptimeSeconds": 3700,
        "cpu": {"overallPercent": 42.4, "coreCount": 4, "perCorePercent": [10, 90, 55, 20], "perCoreFrequencyMHz": [1500, None, 2000, 1000], "loadAvg": [0.5, 0.6, 0.7]},
        "memory": {"usedBytes": 1 << 30, "totalBytes": 4 << 30, "cachedBytes": 1 << 28, "buffersBytes": 1 << 27},
        "disk": {"usedBytes": 10 << 30, "totalBytes": 20 << 30},
        "temps": {"cpu": 55.5, "rp1": None},
        "network": {"wifi": True, "bluetooth": False, "ethernet": None, "traffic": {"wifi": {"rxBytes": 1000, "txBytes": 500}}},
        "processes": [{"pid": 7, "name": "node", "cpuPercent": 3.14, "memPercent": 1.5, "rssBytes": 5 << 20}],
    }
    answers = []

    async def fetch_system_supervisor():
        return answers[0] if answers else None

    conn.fetch_system_supervisor = fetch_system_supervisor
    loop.run_until_complete(bridge._refresh_supervisor())
    check("supervisor: unreachable says so", (bridge.supervisorStatus, bridge.supervisorLive), (_("MSG_SUPERVISOR_UNREACHABLE"), _("LBL_SUPERVISOR_STALE")))
    answers.append((200, snapshot))
    loop.run_until_complete(bridge._refresh_supervisor())
    second = dict(snapshot, timestamp=3000, network={"wifi": True, "bluetooth": False, "ethernet": None, "traffic": {"wifi": {"rxBytes": 5000, "txBytes": 1500}}})
    answers[0] = (200, second)
    loop.run_until_complete(bridge._refresh_supervisor())
    view = bridge.supervisorView
    check("supervisor: live", (bridge.supervisorStatus, bridge.supervisorLive), ("", _("LBL_SUPERVISOR_LIVE")))
    tiles = {t["label"]: t for t in view["tiles"]}
    check("supervisor: tiles", (tiles[_("LBL_SUPERVISOR_CPU")]["value"], tiles[_("LBL_SUPERVISOR_MEMORY")]["value"], tiles[_("LBL_SUPERVISOR_DISK")]["value"], tiles[_("LBL_SUPERVISOR_CPU_TEMP")]["value"], tiles[_("LBL_SUPERVISOR_RP1_TEMP")]["value"]), ("42%", "25%", "50%", "56°C", "N/A"))
    check("supervisor: per-core bars and frequency", ([c["percent"] for c in view["cores"]], view["cores"][1]["frequency"], view["cores"][0]["frequency"]), ([10, 90, 55, 20], "", "1500 MHz"))
    check("supervisor: states of the three links", (view["wifi"], view["bluetooth"], view["ethernet"]), ("on", "off", "unknown"))
    check("supervisor: a window of samples for the charts", (len(view["cpuSeries"]), view["hasMemory"], view["hasTemps"], view["hasTraffic"]), (2, True, True, True))
    check("supervisor: the throughput between the two samples (4000 bytes in 2 s)", (view["rates"]["wifiRx"], view["rates"]["wifiTx"]), ([2000.0], [500.0]))
    check("supervisor: processes", view["processes"], [{"pid": "7", "name": "node", "cpu": "3.1", "mem": "1.5", "rss": "5.0 MB"}])
    check("supervisor: totals", view["wifiTotal"]["total"], "6.3 KB")


def menu_and_notices(loop):
    controller, bridge, conn = make()
    codes = [o["code"] for o in bridge.languageOptions]
    check("menu: the eight languages, with the current one marked", (len(codes), "portuguese" in codes, sum(1 for o in bridge.languageOptions if o["current"])), (8, True, 1))
    bridge.setLanguage("spanish")
    check("menu: a new language is saved for the next start", (SAVED_CONFIG[-1], bridge.noticeText, bridge.noticeSeverity), ({"language": "spanish"}, _("MSG_RESTART_NEEDED"), "info"))
    SAVED_CONFIG.clear()
    bridge.setLanguage("klingon")
    bridge.setLanguage([o["code"] for o in bridge.languageOptions if o["current"]][0])
    check("menu: an unknown language or the current one changes nothing", SAVED_CONFIG, [])
    about = bridge.aboutInfo
    check("menu: About", (about["version"], about["author"], about["license"].startswith("GNU")), (qs.__version__, "JuanenRac (Electro Hobby 3D)", True))
    conn.info.app_version = "9.9.9"
    check("menu: About names the version of the server", bridge.aboutInfo["serverVersion"], "9.9.9")

    controller.connection_error.emit("10.0.0.9:3000", "a refusal")
    check("notice: what a server reports reaches the operator", (bridge.noticeText, bridge.noticeSeverity), ("a refusal", "warn"))
    bridge.dismissNotice()
    check("notice: and can be dismissed", bridge.noticeText, "")
    controller.connections["other"] = conn
    controller.connection_error.emit("other", "second")
    check("notice: with several servers the message names the one", bridge.noticeText, "[other] second")
    check("notice: it fades by itself", bridge._notice_timer.isActive(), True)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    live_and_sim(loop)
    reservations(loop)
    arming(loop)
    safe_mode(loop)
    safety_screen(loop)
    joints_and_bed(loop)
    catalog_and_supervisor(loop)
    menu_and_notices(loop)
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
