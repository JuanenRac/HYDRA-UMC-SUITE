# =============================================================================
# HYDRA-UMC SUITE - logging_handler.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Bridges Python's own stdlib `logging` (every module here already does
# `logging.getLogger(__name__)` - models.py, net/client.py, ...) into a Qt
# signal the Logs panel can display live (audit idea: "visor de logs en
# tiempo real con filtros" - SONNET/AUDITORIA_COMPLETA_44_PROYECTOS.txt).
#
# `logging.Handler` isn't a QObject, so it can't emit a Qt signal itself -
# QtLogHandler wraps a plain Handler that forwards each record to a
# QObject's own signal. Cross-thread safe: Qt's own signal/slot queuing
# handles a record logged from a background asyncio task (net/client.py
# runs its own event loop) being delivered to a Qt-thread slot correctly,
# the same guarantee every other cross-thread signal in this app already
# relies on - no manual locking needed here either.
#
# Root logger's own default level is WARNING - every plain `.info()` call
# already scattered through this codebase would otherwise be silently
# dropped before ever reaching this handler. install() sets it to INFO
# (not DEBUG - PySide6/asyncio's own internals log a lot of DEBUG noise
# unrelated to this app's own operation) so those calls actually show up
# without also drowning the panel in library-internal chatter.
# =============================================================================
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class _LogSignalEmitter(QObject):
    record_logged = Signal(str, str, str)  # level_name, logger_name, message


class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = _LogSignalEmitter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:  # noqa: BLE001 - a broken formatter must never crash the logger itself
            message = record.getMessage()
        self.emitter.record_logged.emit(record.levelname, record.name, message)


_installed_handler: QtLogHandler | None = None


def install() -> QtLogHandler:
    """Idempotent - safe to call more than once (e.g. if the Logs panel
    were ever recreated); returns the same handler instance every time
    rather than attaching a second copy to the root logger."""
    global _installed_handler
    if _installed_handler is not None:
        return _installed_handler
    handler = QtLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)
    _installed_handler = handler
    return handler
