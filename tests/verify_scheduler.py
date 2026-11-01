# =============================================================================
# HYDRA-UMC SUITE - tests/verify_scheduler.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one scheduler of the pollers (scheduler.py), checked with a clock that is moved by hand, and the shell: every
# poller of the interface is a job of the scheduler of the bridge, driven by one timer, and only the jobs of the
# screen on view are started.
# =============================================================================
import asyncio
import logging
import sys

sys.path.insert(0, ".")

import qasync
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from hydra_suite.scheduler import PollScheduler

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def pure() -> None:
    clock = Clock()
    scheduler = PollScheduler(clock)
    calls: list[str] = []
    fast = scheduler.add("fast", 1000, lambda: calls.append("fast"))
    slow = scheduler.add("slow", 3000, lambda: calls.append("slow"))
    check("scheduler: a job that was not started never runs", (scheduler.tick(), fast.isActive()), ([], False))
    fast.start()
    clock.t += 0.5
    check("scheduler: the first run is one period after the start", scheduler.tick(), [])
    clock.t += 0.6
    check("scheduler: it runs when the period is over", (scheduler.tick(), calls), (["fast"], ["fast"]))
    check("scheduler: and not twice for the same period", scheduler.tick(), [])
    slow.start()
    clock.t += 1.0
    check("scheduler: the jobs of the same tick run in the order they were added", scheduler.tick(), ["fast"])
    clock.t += 2.0
    check("scheduler: both are due", scheduler.tick(), ["fast", "slow"])
    fast.stop()
    clock.t += 5.0
    check("scheduler: a stopped job is left alone", (scheduler.tick(), [j.name for j in scheduler.active_jobs()]), (["slow"], ["slow"]))
    clock.t += 60.0
    check("scheduler: a long pause is one run, not a queue of them", (scheduler.tick(), scheduler.tick()), (["slow"], []))
    fast.setInterval(250)
    check("scheduler: the period can change (the small surface of a QTimer)", fast.interval(), 250)
    fast.start()
    check("scheduler: a restarted job counts its period from the restart", scheduler.tick(), [])

    boom = scheduler.add("boom", 100, lambda: (_ for _ in ()).throw(RuntimeError("no")))
    quiet = scheduler.add("quiet", 100, lambda: calls.append("quiet"))
    boom.start()
    quiet.start()
    clock.t += 1.0
    logging.disable(logging.CRITICAL)  # the failure is expected: no traceback in the report
    try:
        ran = scheduler.tick()
    finally:
        logging.disable(logging.NOTSET)
    check("scheduler: a poller that fails does not stop the others", ("boom" in ran and "quiet" in ran, boom.failures, boom.runs), (True, 1, 1))


def shell() -> None:
    import qt_suite as qs
    from hydra_suite.app import SuiteController

    bridge = qs.SuiteQtBridge(SuiteController())
    check("shell: the bridge has one scheduler and one timer for it", (isinstance(bridge._scheduler, PollScheduler), isinstance(bridge._scheduler_timer, QTimer), bridge._scheduler_timer.isActive()), (True, True, True))
    names = sorted(job.name for job in bridge._scheduler.jobs)
    check(
        "shell: every poller of the interface is a job of it",
        names,
        sorted(["admin_clients", "admin_clients_clock", "admin_logs", "camera_status", "access_robot", "access_clock", "safety_limits", "system_supervisor", "ecosystem_health", "ecosystem_health_clock"]),
    )
    check("shell: none of them runs on the first screen", bridge._scheduler.active_jobs(), [])
    for key, jobs in bridge._poller_gates().items():
        bridge.navigatePanel(key)
        check(f"shell: {key} starts exactly its own jobs", sorted(j.name for j in bridge._scheduler.active_jobs()), sorted(j.name for j in jobs))
    bridge.navigatePanel("overview")
    check("shell: leaving the screen stops them", bridge._scheduler.active_jobs(), [])
    bridge._scheduler_timer.stop()


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    pure()
    shell()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
