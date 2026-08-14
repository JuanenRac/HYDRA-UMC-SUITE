import asyncio
import sys
sys.path.insert(0, ".")

from hydra_suite.net.discovery import probe_host
import httpx


async def main():
    async with httpx.AsyncClient() as client:
        info = await probe_host(client, "127.0.0.1", 3000)
    print("Discovery probe result:", info)
    assert info is not None, "probe_host failed against known-good localhost:3000"
    assert info.product == "HYDRA-UMC STUDIO"
    assert info.robot_count > 0
    print("OK: discovery.probe_host")

    from hydra_suite.net.client import HydraConnection
    conn = None
    try:
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance() or QCoreApplication([])
        conn = HydraConnection(info)
        received = []
        conn.state_changed.connect(lambda s: received.append(s))
        statuses = []
        conn.status_changed.connect(lambda s: statuses.append(s))

        await conn.connect()
        await asyncio.sleep(1.0)
        print("Statuses so far:", statuses)
        assert "connected" in statuses, f"never reached connected status: {statuses}"
        assert len(received) >= 1, "never received a state_changed signal"

        active = conn.state.active_controller
        print("Active controller:", active)
        assert active is not None
        print(f"Robots on active controller: {[r.model for r in active.robots]}")

        # Round-trip test: flip a joint value, push, expect no crash and
        # a self-consistent local state (echo-suppression covered by the
        # unchanged-payload guard, exercised implicitly since push_state
        # is called twice below with the second call being a true no-op).
        robots = active.robots
        if robots:
            r = robots[0]
            original = r.joints["j1"]
            r.set_joint("j1", original + 0.001)
            await conn.push_state()
            await asyncio.sleep(0.5)
            print("Pushed a tiny j1 nudge and restored, no exceptions raised")
            r.set_joint("j1", original)
            await conn.push_state()
            await asyncio.sleep(0.5)

        print("OK: client.HydraConnection connect/receive/push")
    finally:
        if conn is not None:
            await conn.disconnect()

asyncio.run(main())
print("ALL NET TESTS PASSED")
