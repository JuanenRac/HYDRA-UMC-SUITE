# =============================================================================
# HYDRA-UMC-SUITE - hydra_suite/command_sequence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The number this program puts on its motion commands (`seq`).

The server refuses a jog whose number is not above the highest one it has seen from the same account and
controller, and a stop raises that mark, so a jog sent before a stop can never move the robot after it. The
number grows by at least one with every command and follows the clock, so a restarted program starts above
everything an earlier run sent."""
from __future__ import annotations

import threading
import time
from typing import Callable

NUMBERED = frozenset({"jog", "table", "joints", "stop"})


def is_numbered(command: str) -> bool:
    """The commands the server orders by number: the motion commands and the stop that must overtake them."""
    return command in NUMBERED


class CommandSequence:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._last = 0
        self._lock = threading.Lock()

    def next(self) -> int:
        """The next number: above the previous one and not below the clock (milliseconds)."""
        with self._lock:
            self._last = max(self._last + 1, int(self._clock() * 1000))
            return self._last


_default = CommandSequence()


def next_for(command: str) -> dict:
    """`{"seq": n}` for a numbered command, `{}` for any other."""
    return {"seq": _default.next()} if is_numbered(command) else {}
