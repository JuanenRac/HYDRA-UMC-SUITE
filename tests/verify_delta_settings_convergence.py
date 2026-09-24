# =============================================================================
# HYDRA-UMC SUITE - tests/verify_delta_settings_convergence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# net/client.py's own _last_payload_json echo-guard (settings ==
# _last_payload_json means "our own write echoed back, ignore it") was never
# updated by _apply_robot_delta() - a real targeted delta really does change
# self.state, but left the guard's own baseline pointing at the full-tree
# JSON from BEFORE that delta. A later full "settings"/"delta" message whose
# payload happens to be byte-identical to that stale baseline (e.g. the
# delta's own change gets reverted/superseded and the tree converges back to
# what it was) then matched the stale guard and was silently dropped,
# permanently stranding self.state on the post-delta value the server had
# already moved past. This calls HydraConnection._handle_message() directly
# with real WS message JSON strings - no real network, no real server, no Qt
# event loop needed (matches verify_send_command_debounce.py's own approach).
# =============================================================================
import json
import sys
sys.path.insert(0, ".")

from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def full_settings_payload(j1_robot5: float, j1_robot6: float) -> dict:
    return {
        "settings": {},
        "activeControllerId": "c1",
        "controllers": [{
            "id": "c1",
            "robots": [
                {"id": 5, "joints": {"j1": j1_robot5}},
                {"id": 6, "joints": {"j1": j1_robot6}},
            ],
        }],
    }


def robot_j1(conn: HydraConnection, robot_id: int) -> float:
    for c in conn.state.raw.get("controllers") or []:
        for r in c.get("robots") or []:
            if r.get("id") == robot_id:
                return r["joints"]["j1"]
    raise AssertionError(f"robot {robot_id} not found in state")


def settings_message(payload: dict) -> str:
    return json.dumps({"type": "settings", "payload": payload})


def delta_message(robot_id: int, patch: dict) -> str:
    return json.dumps({"type": "delta", "schema": 2, "controllerId": "c1", "robotId": robot_id, "patch": patch})


def run() -> None:
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=3000))

    # --- core scenario: settings -> delta -> settings (restored) -----
    snapshot_1 = full_settings_payload(j1_robot5=10.0, j1_robot6=0.0)
    conn._handle_message(settings_message(snapshot_1))
    check("snapshot 1 applies: robot 5 at 10.0", robot_j1(conn, 5), 10.0)

    conn._handle_message(delta_message(5, {"joints": {"j1": 20.0}}))
    check("delta applies locally: robot 5 moved to 20.0", robot_j1(conn, 5), 20.0)

    # snapshot 2 is byte-identical to snapshot 1 - the server's own tree
    # converged back to that exact value (the delta's move got superseded).
    # Before the fix, _last_payload_json was still snapshot 1's own
    # JSON, so this matched and was dropped - robot 5 stayed wrongly stuck
    # at 20.0 forever instead of converging back to the server's real 10.0.
    snapshot_2 = full_settings_payload(j1_robot5=10.0, j1_robot6=0.0)
    conn._handle_message(settings_message(snapshot_2))
    check("restored snapshot converges: robot 5 back to 10.0, not stuck at 20.0", robot_j1(conn, 5), 10.0)

    # --- Two deltas for different robots must both apply independently ----
    conn._handle_message(delta_message(5, {"joints": {"j1": 30.0}}))
    conn._handle_message(delta_message(6, {"joints": {"j1": 40.0}}))
    check("delta for robot 5 applied", robot_j1(conn, 5), 30.0)
    check("delta for robot 6 applied independently", robot_j1(conn, 6), 40.0)

    # --- A genuinely different snapshot always applies, delta or not ------
    snapshot_3 = full_settings_payload(j1_robot5=99.0, j1_robot6=99.0)
    conn._handle_message(settings_message(snapshot_3))
    check("a genuinely new snapshot always applies: robot 5", robot_j1(conn, 5), 99.0)
    check("a genuinely new snapshot always applies: robot 6", robot_j1(conn, 6), 99.0)

    # --- Own echo: our own confirmed write must still be suppressed -------
    # push_state()'s own guard (same _last_payload_json field) is exercised
    # directly here since it shares the exact mechanism _handle_message()
    # checks against - after this "send", state.raw IS payload_json's own
    # content, so an echo of it back over the WS must be a no-op, not an
    # unnecessary re-apply.
    own_write = full_settings_payload(j1_robot5=55.0, j1_robot6=55.0)
    conn.state = HydraState(own_write)
    conn._last_payload_json = json.dumps(own_write, sort_keys=True)
    conn._handle_message(settings_message(own_write))  # the server echoing our own write back
    check("our own echoed write is still suppressed (no crash, state unchanged)", robot_j1(conn, 5), 55.0)

    # --- Reconnect: a fresh full snapshot after reconnecting always applies,
    # exactly like the very first connect's own fetch_state()/first WS
    # message - this must keep working after the change to
    # _apply_robot_delta(), which never runs on this path at all.
    reconnect_snapshot = full_settings_payload(j1_robot5=1.0, j1_robot6=2.0)
    conn._handle_message(settings_message(reconnect_snapshot))
    check("reconnect's fresh snapshot applies: robot 5", robot_j1(conn, 5), 1.0)
    check("reconnect's fresh snapshot applies: robot 6", robot_j1(conn, 6), 2.0)


run()

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL DELTA/SETTINGS CONVERGENCE CHECKS PASSED")
