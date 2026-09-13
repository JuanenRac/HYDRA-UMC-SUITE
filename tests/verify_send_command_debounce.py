# =============================================================================
# HYDRA-UMC SUITE - tests/verify_send_command_debounce.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# net/client.py's HydraConnection.send_command() gained a real debounce_ms
# parameter this session (robot_control.py's own joint knob and speed/
# acceleration sliders all emit continuously during a drag - without this,
# every single mouse-move tick fired its own real POST
# /api/robot/:id/command). This verifies the real cancel-and-reschedule
# state machine directly against HydraConnection itself - no real network,
# no real server: httpx.AsyncClient.post is monkeypatched to record calls
# instead of hitting the wire.
# =============================================================================
import asyncio
import sys
sys.path.insert(0, ".")

import httpx

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


class _FakeResponse:
    status_code = 200

    def raise_for_status(self):
        pass


async def run():
    posts: list[dict] = []

    async def fake_post(self, url, json=None, headers=None, timeout=None):
        posts.append({"url": url, **json})
        return _FakeResponse()

    original_post = httpx.AsyncClient.post
    httpx.AsyncClient.post = fake_post
    try:
        conn = HydraConnection(ServerInfo(host="127.0.0.1", port=3000))
        conn.state = HydraState({"controllers": [], "activeControllerId": ""})

        # A burst of 5 rapid calls for the SAME command should collapse
        # into exactly 1 real POST, carrying only the LAST value.
        for value in (10, 20, 30, 40, 50):
            await conn.send_command(1, "jog", {"value": value}, debounce_ms=50)
        check("burst before debounce settles: no POST sent yet", len(posts), 0)
        await asyncio.sleep(0.1)
        check("burst after debounce settles: exactly 1 real POST", len(posts), 1)
        check("that POST carries the LAST value, not an earlier one", posts[0]["params"]["value"], 50)

        # Two DIFFERENT command names must never coalesce into each other -
        # both must still reach the server independently.
        posts.clear()
        await conn.send_command(1, "jog", {"value": 1}, debounce_ms=50)
        await conn.send_command(1, "speed", {"value": 2}, debounce_ms=50)
        await asyncio.sleep(0.1)
        check("two different command names both send independently", len(posts), 2)
        sent_commands = sorted(p["command"] for p in posts)
        check("both real command names present", sent_commands, ["jog", "speed"])

        # debounce_ms=0 (the default) must still send immediately, like
        # before this change - speed/acceleration/jog callers that pass no
        # debounce_ms (or 0) must see zero behavior change.
        posts.clear()
        await conn.send_command(1, "stop", debounce_ms=0)
        check("debounce_ms=0 sends immediately, no delay needed", len(posts), 1)

        # H034: the SAME command name for TWO DIFFERENT robots must never
        # share a throttle slot - before this fix, _throttle_tasks/
        # _throttle_latest_send were keyed by command name alone, so
        # robot 2's "jog" during robot 1's own "jog" throttle window would
        # silently overwrite robot 1's pending send, dropping it entirely.
        # A real "two robots, two controls" scenario: robot 1 jogs, robot 2
        # jogs, robot 1 also adjusts speed - all 3 must independently reach
        # the server with their own last value, none dropped. robot_id
        # isn't in the JSON body (it's in the URL path, /api/robot/:id/
        # command) - read it back from each recorded POST's own url.
        posts.clear()
        for value in (1, 2, 3):
            await conn.send_command(1, "jog", {"value": value}, debounce_ms=50)
        for value in (10, 20):
            await conn.send_command(2, "jog", {"value": value}, debounce_ms=50)
        await conn.send_command(1, "speed", {"value": 99}, debounce_ms=50)
        await asyncio.sleep(0.1)
        check("robot1-jog + robot2-jog + robot1-speed: none dropped, 3 real POSTs", len(posts), 3)
        by_key = {(p["url"].split("/")[-2], p["command"]): p["params"]["value"] for p in posts}
        check("robot 1's own last jog value (3) reached the server", by_key.get(("1", "jog")), 3)
        check("robot 2's own last jog value (20) reached the server, not dropped for sharing 'jog'", by_key.get(("2", "jog")), 20)
        check("robot 1's speed reached the server independently of its own jog", by_key.get(("1", "speed")), 99)
    finally:
        httpx.AsyncClient.post = original_post


asyncio.run(run())

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
else:
    print("ALL SEND_COMMAND DEBOUNCE CHECKS PASSED")
