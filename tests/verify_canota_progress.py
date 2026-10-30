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

if failures:
    print(f"{failures} check(s) failed")
    sys.exit(1)
print("ALL CHECKS PASSED")
