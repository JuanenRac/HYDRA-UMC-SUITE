# =============================================================================
# HYDRA-UMC SUITE - scheduler.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# One scheduler for every poller of the interface. Each screen that asks the server on a timer used to own a QTimer
# of its own (ten of them), started and stopped by the screen that was on view. Now a poller is a job of this
# scheduler: it has a period and a callback, it runs only while it is started (the interface starts the jobs of the
# screen on view and stops the others), and a single QTimer of the interface calls `tick()` a few times a second.
# A job offers the small surface of a QTimer (start, stop, isActive, setInterval), so the code that gated the old
# timers by screen is unchanged. Nothing here needs Qt: the clock is a parameter, so the rules are checked without
# waiting.
# =============================================================================
from __future__ import annotations

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)

#: How often the single timer of the interface calls tick(), in milliseconds. A job never runs more often than this.
TICK_MS = 250


class PollJob:
    """One poller: runs `callback` every `interval_ms` while started."""

    def __init__(self, scheduler: "PollScheduler", name: str, interval_ms: int, callback: Callable[[], None]):
        self._scheduler = scheduler
        self.name = name
        self._interval_s = max(interval_ms, 1) / 1000.0
        self._callback = callback
        self._active = False
        self._next_due = 0.0
        #: How many times it ran and how many times the callback raised; kept for the checks and the diagnostics.
        self.runs = 0
        self.failures = 0

    # -- the small surface of a QTimer ---------------------------------------------------------------

    def start(self) -> None:
        """Starts the job: the first run is one period from now (the screen has just read what it needs)."""
        self._active = True
        self._next_due = self._scheduler.now() + self._interval_s

    def stop(self) -> None:
        self._active = False

    def isActive(self) -> bool:  # noqa: N802 - the name of the QTimer method it stands in for
        return self._active

    def setInterval(self, interval_ms: int) -> None:  # noqa: N802
        self._interval_s = max(interval_ms, 1) / 1000.0

    def interval(self) -> int:
        return round(self._interval_s * 1000)

    # -- the scheduler ---------------------------------------------------------------------------------

    def _due(self, now: float) -> bool:
        return self._active and now >= self._next_due

    def _run(self, now: float) -> None:
        # The next run is a period after this one started, not after the missed ones: a busy interface skips runs, it does not queue them.
        self._next_due = now + self._interval_s
        self.runs += 1
        try:
            self._callback()
        except Exception:  # a poller that fails must not stop the others
            self.failures += 1
            logger.exception("the poller %s failed", self.name)


class PollScheduler:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self.jobs: list[PollJob] = []

    def now(self) -> float:
        return self._clock()

    def add(self, name: str, interval_ms: int, callback: Callable[[], None]) -> PollJob:
        job = PollJob(self, name, interval_ms, callback)
        self.jobs.append(job)
        return job

    def active_jobs(self) -> list[PollJob]:
        return [job for job in self.jobs if job.isActive()]

    def tick(self) -> list[str]:
        """Runs the jobs that are due; returns their names in the order they ran."""
        now = self._clock()
        ran: list[str] = []
        for job in list(self.jobs):
            if job._due(now):
                job._run(now)
                ran.append(job.name)
        return ran
