# =============================================================================
# HYDRA-UMC SUITE - tests/verify_command_sequence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies the number the program puts on its motion commands (`seq`): only jog,
# table, joints and stop carry one, it always rises (even when the clock stands
# still or goes back), it follows the clock, and a 409 stale-sequence answer is
# told apart from a reservation, in the failure code and in the text.
# =============================================================================
import sys

sys.path.insert(0, ".")

from hydra_suite import access, command_sequence
from hydra_suite.command_sequence import CommandSequence, is_numbered
from hydra_suite.net.client import describe_rejection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


for name in ("jog", "table", "joints", "stop"):
    check(f"{name} is numbered", is_numbered(name), True)
for name in ("home", "speed", "points", ""):
    check(f"{name!r} is not numbered", is_numbered(name), False)

now = [1000.0]
sequence = CommandSequence(clock=lambda: now[0])
check("first number follows the clock", sequence.next(), 1_000_000)
check("same clock still rises", sequence.next(), 1_000_001)
now[0] = 500.0
check("clock going back still rises", sequence.next(), 1_000_002)
now[0] = 2000.0
check("clock ahead wins", sequence.next(), 2_000_000)

check("numbered command gets seq", set(command_sequence.next_for("jog")), {"seq"})
check("other command gets none", command_sequence.next_for("home"), {})

check("failure code", access.failure_code_for(409, "stale-sequence"), "stale_sequence")
check("a plain 409 is still a reservation", access.failure_code_for(409, None), "claimed")
stale = describe_rejection(FakeResponse(409, {"error": "stale", "code": "stale-sequence"}), "Jog")
reserved = describe_rejection(FakeResponse(409, {"error": "taken"}), "Jog")
check("stale text differs from reservation text", stale != reserved, True)

if failures:
    print(f"{failures} check(s) failed")
    sys.exit(1)
print("verify_command_sequence: PASS")
