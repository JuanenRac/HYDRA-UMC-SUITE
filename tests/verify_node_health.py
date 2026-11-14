# =============================================================================
# HYDRA-UMC SUITE - tests/verify_node_health.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The panel of the controller boards (the last health frame the brain heard from each, GET /api/ecosystem/node-health), without any window: what is accepted and
# what is refused, each way the route can fail, when the panel is not shown at all, the sentence for a heard frame, a slot never heard, a brain that does not
# answer and a slot with no reading, and the sentences in the eight languages. Nothing is invented.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import node_health as nh

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def heard(slot, **over):
    body = {"online": True, "slot": slot, "heard": True, "ageMs": 2500, "sequence": 7, "flags": 17, "flagNames": ["estop_latched", "application_confirmed"],
            "txErrors": 1, "rxErrors": 2, "stalls": 0, "uptimeS": 48, "source": "brain-health"}
    body.update(over)
    return body


good = nh.parse_slot({**heard(2), "password": "x"}, 2)
check("reads the closed fields of a heard frame and nothing else", (good["ageMs"], good["sequence"], good["flagNames"], good["txErrors"], good["rxErrors"], good["uptimeS"], "password" in good),
      (2500, 7, ["estop_latched", "application_confirmed"], 1, 2, 48, False))
never = nh.parse_slot({"online": True, "slot": 5, "heard": False}, 5)
check("a slot never heard has no numbers", (never["online"], never["heard"], never["ageMs"], never["flagNames"], nh.slot_state(never)), (True, False, None, [], "never"))
silent = nh.parse_slot({"online": False, "slot": 3, "heard": None}, 3)
check("a brain that does not answer", (silent["online"], silent["heard"], nh.slot_state(silent)), (False, None, "silent"))
bad = [None, 5, "x", {}, {"online": "yes", "slot": 2}, heard(3), heard(2, heard="maybe"), heard(2, ageMs=-1), heard(2, ageMs=25401), heard(2, sequence=256), heard(2, flagNames="x"),
       heard(2, flagNames=[1]), heard(2, uptimeS=4081), heard(2, txErrors=1.5), heard(2, txErrors=True)]
check("refuses what is not an answer for that slot", [nh.parse_slot(item, 2) for item in bad], [None] * len(bad))

check("each way the route can fail", [nh.classify(item, 0)[0] for item in (None, (404, None), (401, None), (403, {}), (500, None), (503, {}), (200, {"nonsense": True}), (200, heard(0)))],
      ["network", "unsupported", "forbidden", "forbidden", "http", "http", "malformed", "ok"])
check("the panel is hidden unless the server offers it", (nh.is_hidden(["unsupported"] * 8), nh.is_hidden(["network", "malformed"]), nh.is_hidden([]), nh.is_hidden(["http", "unsupported"]), nh.is_hidden(["ok"] + ["forbidden"] * 7)),
      (True, True, True, False, False))

results = [nh.classify((503, None), 0)] + [nh.classify((200, {"online": True, "slot": s, "heard": False}), s) for s in range(1, 8)]
results[2] = nh.classify((200, heard(2)), 2)
results[3] = nh.classify((200, {"online": False, "slot": 3, "heard": None}), 3)
rows = nh.rows(results)
check("eight rows, one per slot", [r["slot"] for r in rows], list(range(8)))
check("states of the rows", [r["state"] for r in rows], ["unknown", "never", "heard", "silent", "never", "never", "never", "never"])
check("a slot with no reading says so and shows no number", (rows[0]["stateLabel"], rows[0]["detail"], rows[0]["flags"]), (_("NODEHEALTH_STATE_UNKNOWN"), "", ""))
check("a heard frame shows its numbers and its flags", ("2.5" in rows[2]["detail"], "tx 1, rx 2" in rows[2]["detail"], rows[2]["flags"]), (True, True, _("NODEHEALTH_FLAG_ESTOP_LATCHED") + ", " + _("NODEHEALTH_FLAG_APPLICATION_CONFIRMED")))
check("a slot never heard and a silent brain have no numbers", (rows[1]["detail"], rows[3]["detail"], rows[3]["stateLabel"]), ("", "", _("NODEHEALTH_STATE_SILENT")))
check("an unknown flag is shown as it came, none is said", (nh.row("ok", nh.parse_slot(heard(1, flagNames=["new_flag"]), 1), 1)["flags"], nh.row("ok", nh.parse_slot(heard(1, flagNames=[]), 1), 1)["flags"]), ("new_flag", _("NODEHEALTH_FLAGS_NONE")))
check("4080 seconds of uptime or more is said as such", ("4080" in nh.row("ok", nh.parse_slot(heard(1, uptimeS=4080), 1), 1)["detail"], _("NODEHEALTH_UPTIME_MORE", seconds=4080) in nh.row("ok", nh.parse_slot(heard(1, uptimeS=4080), 1), 1)["detail"]), (True, True))
check("no rows when the panel is hidden", nh.rows([nh.classify((404, None), s) for s in range(8)]), [])
check("every sentence exists", all(_(key) != key for key in ["NODEHEALTH_" + k for k in (
    "TITLE", "HELP", "SLOT", "STATE_HEARD", "STATE_NEVER", "STATE_SILENT", "STATE_UNKNOWN", "AGE", "SEQUENCE", "ERRORS", "STALLS", "UPTIME", "UPTIME_MORE", "FLAGS_NONE",
    "FLAG_ESTOP_LATCHED", "FLAG_BUS_OFF_SEEN", "FLAG_WATCHDOG_RESET_AT_START", "FLAG_SETUP_FAILED_AT_START", "FLAG_APPLICATION_CONFIRMED", "FLAG_DRIVERS_ENABLED", "FLAG_SETUP_FAILED_SAFE_STATE")]
    + ["LBL_SECURITY_NODEHEALTH", "LBL_SECURITY_NODEHEALTH_ENABLED", "LBL_SECURITY_NODEHEALTH_HELP"]), True)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
