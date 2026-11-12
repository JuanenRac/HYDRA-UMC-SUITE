# =============================================================================
# HYDRA-UMC SUITE - tests/verify_canota_progress.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The server relays every progress line of a CAN flash cycle to admin sessions as a WebSocket message of type
# `canota_progress`. The connection keeps the latest line and announces each one; a message without a payload
# object changes nothing, and it never reaches the settings mirror. No network and no event loop needed.
# =============================================================================
import json
import sys

sys.path.insert(0, ".")

from hydra_suite.models import ServerInfo
from hydra_suite.net.client import HydraConnection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


conn = HydraConnection(ServerInfo(host="127.0.0.1", port=1))
seen = []
conn.canota_progress.connect(seen.append)
check("nothing before the first line", conn.last_canota_progress, None)
state_before = conn.state

line = {"phase": "write", "page": 3, "pages": 40, "percent": 7.5}
conn._handle_message(json.dumps({"type": "canota_progress", "payload": line}))
check("the line is kept", conn.last_canota_progress, line)
check("and announced once", seen, [line])

conn._handle_message(json.dumps({"type": "canota_progress", "payload": {"phase": "done"}}))
check("the next line replaces it", conn.last_canota_progress, {"phase": "done"})
check("and is announced too", len(seen), 2)

conn._handle_message(json.dumps({"type": "canota_progress"}))
conn._handle_message(json.dumps({"type": "canota_progress", "payload": "text"}))
conn._handle_message(json.dumps({"type": "canota_progress", "payload": [1, 2]}))
check("a message without a payload object changes nothing", (conn.last_canota_progress, len(seen)), ({"phase": "done"}, 2))
check("the settings mirror is untouched", conn.state is state_before, True)

# what the flasher shows of a live line of the cycle
from hydra_suite.panel_logic.flasher import progress_line

check("a page in the middle of the transfer shows its counts but is not worth a log line", progress_line({"phase": "transferring", "pages_sent": 3, "pages_total": 40, "percent": 7.5}),
      {"phase": "transferring", "percent": 8, "pages": (3, 40), "reason": None, "log": False})
check("every fifth page and the last one are logged", [progress_line({"phase": "transferring", "pages_sent": n, "pages_total": 12, "percent": 1})["log"] for n in (5, 10, 12, 11)], [True, True, True, False])
check("an error carries the reason the bootloader client reports", progress_line({"phase": "error", "error": "page 7 was never acknowledged", "percent": 20}),
      {"phase": "error", "percent": 20, "pages": None, "reason": "page 7 was never acknowledged", "log": True})
check("the percent stays between 0 and 100", [progress_line({"phase": "done", "percent": p})["percent"] for p in (-5, 100.4, 250)], [0, 100, 100])
check("a percent that is not a number is none", [progress_line({"phase": "verifying", "percent": p})["percent"] for p in ("50", None, True)], [None, None, None])
check("page counts that are not whole numbers are none", [progress_line({"phase": "transferring", "pages_sent": a, "pages_total": b})["pages"] for a, b in ((1.5, 4), (-1, 4), ("1", 4), (None, None))], [None, None, None, None])
for label, payload in {"no phase": {"percent": 5}, "an unknown phase": {"phase": "dancing"}, "a text": "done", "a list": [1], "none": None}.items():
    check(f"nothing from {label}", progress_line(payload), None)
for phase in ("connecting", "entering_bootloader", "erasing_fram", "transferring", "verifying", "rebooting", "done", "error"):
    check(f"phase {phase} has its sentence in every language file", all(f"FLASHER_PROGRESS_{phase.upper()}=" in path.read_text(encoding="utf-8") for path in __import__("pathlib").Path("language").glob("*.lng")), True)

if failures:
    print(f"{failures} check(s) failed")
    sys.exit(1)
print("ALL CHECKS PASSED")
