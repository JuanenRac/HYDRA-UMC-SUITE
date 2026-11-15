# =============================================================================
# HYDRA-UMC SUITE - tests/steady_qasync_loop.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The event loop of the verifiers that talk to a simulated server.

qasync ends `run_until_complete` with one last pass over the pending events AFTER it has left the running loop. A task that is stepped in that pass
(a request that starts or goes on there) finds no running loop: anyio, under httpx, then raises `NoEventLoopError`, the screen reads that as a damaged
answer and the check fails, but only on the runs in which a timer happens to fall in that pass. The program never meets this (its loop runs until it
quits). This loop keeps itself current while that last pass runs, so every step of every task sees the loop, whatever the timers do."""
from __future__ import annotations

import asyncio

import qasync


class SteadyLoop(qasync.QEventLoop):
    def _after_run_forever(self) -> None:
        super()._after_run_forever()
        asyncio.events._set_running_loop(self)  # the last pass of run_until_complete still runs with this loop current

    def run_until_complete(self, future):
        try:
            return super().run_until_complete(future)
        finally:
            asyncio.events._set_running_loop(None)
