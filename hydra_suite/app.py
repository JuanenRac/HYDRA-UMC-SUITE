# =============================================================================
# HYDRA-UMC SUITE - app.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# SuiteController - the single source of truth every panel talks to,
# instead of panels reaching into each other directly. Owns the swarm of
# HydraConnections (one per server the user has added) and which one is
# "active" (shown in the Overview/Robot/Viewport/Trajectory panels) - the
# Server Browser panel is the only one that manages the dict itself, every
# other panel just reacts to activeStateChanged.
# =============================================================================
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, Signal

from hydra_suite.models import HydraState, RobotView, ServerInfo
from hydra_suite.i18n import _
from hydra_suite.net.client import HydraConnection, StopAllResult

logger = logging.getLogger(__name__)


def spawn(coro) -> "asyncio.Future":
    """Schedules a coroutine and logs whatever it raises, so a failed
    background task never ends as "Task exception was never retrieved"."""
    task = asyncio.ensure_future(coro)

    def _report(done: "asyncio.Future") -> None:
        if done.cancelled():
            return
        error = done.exception()
        if error is not None:
            logger.warning("background task failed: %s", error)

    task.add_done_callback(_report)
    return task


@dataclass
class StopAllSummary:
    """What the last global STOP did across every server of the swarm.

    `state` is "sending" while the calls are on the wire, "done" when every
    server confirmed, and "not_confirmed" when at least one server did not
    (no answer, a refusal): that state stays on screen until a later STOP
    confirms everywhere."""

    state: str
    results: dict[str, StopAllResult] = field(default_factory=dict)
    reason: str = ""

    @property
    def stopped(self) -> int:
        return sum(r.stopped_count for r in self.results.values() if r.confirmed)

    @property
    def failed(self) -> int:
        return sum(r.failed_count for r in self.results.values() if r.confirmed)

    @property
    def is_clean(self) -> bool:
        return self.state == "done" and all(r.is_clean for r in self.results.values())


def describe_stop_all(summary: StopAllSummary) -> tuple[str, list[str], str]:
    """(headline, detail lines, severity) of a STOP summary, in the user's
    language. Severity is "busy", "ok", "warn" or "error" so each shell can
    pick its own colour; anything but "ok" must stay prominent."""
    if summary.state == "sending":
        return _("STOP_ALL_SENDING"), [], "busy"
    details: list[str] = []
    for conn_id, result in summary.results.items():
        if not result.confirmed:
            details.append(_("STOP_ALL_SERVER_FAILED", server=conn_id, reason=result.reason or "-"))
            continue
        if not result.persisted:
            details.append(_("STOP_ALL_NOT_SAVED", server=conn_id))
        if result.via_fallback:
            details.append(_("STOP_ALL_ONE_BY_ONE", server=conn_id))
        for robot in result.failed_robots:
            details.append(
                _("STOP_ALL_ROBOT_FAILED", server=conn_id, name=robot.name or f"#{robot.robot_id}", error=robot.error or "-")
            )
        for robot in result.robots:
            if robot.reserved_by:
                details.append(
                    _("STOP_ALL_ROBOT_RESERVED", server=conn_id, name=robot.name or f"#{robot.robot_id}", user=robot.reserved_by)
                )
    if summary.state == "not_confirmed":
        if summary.reason:
            details.insert(0, summary.reason)
        return _("STOP_ALL_NOT_CONFIRMED"), details, "error"
    if summary.is_clean:
        return _("STOP_ALL_DONE", stopped=summary.stopped), details, "ok"
    return _("STOP_ALL_INCOMPLETE", stopped=summary.stopped, failed=summary.failed), details, "error"


class SuiteController(QObject):
    connections_changed = Signal()                  # the dict of connections itself changed (added/removed)
    active_connection_changed = Signal(str)          # active connection id changed (may be "")
    active_state_changed = Signal(object)            # HydraState - the active connection's own state changed
    active_status_changed = Signal(str)              # the active connection's own status changed
    active_metrics_changed = Signal(dict)            # the active connection's own GET /api/system/metrics, polled every 5s
    # Unlike the active_* signals above (only ever fire for whichever ONE
    # connection is currently "active"), these two fire for EVERY connection
    # in the swarm, active or not - the Server Browser panel shows a status
    # per ROW, for every server the user has added, so it needs to know the
    # instant any of them changes, not just whichever one panel selection
    # happens to be pointed at - including a failed login on a server that
    # isn't active, which otherwise has no other visible indicator anywhere
    # in the UI.
    connection_status_changed = Signal(str, str)      # (conn_id, status)
    connection_login_changed = Signal(str, bool, str)  # (conn_id, ok, detail)
    # HydraConnection.error covers real network failures (an initial fetch
    # that raced a server restart, a push_state() that never reached the
    # server) that previously had nowhere to go once emitted - nothing
    # anywhere connected to that signal, so a failed write looked
    # identical to a successful one from the UI's own point of view.
    # Relayed for every connection like the two signals above, not just
    # the active one, for the same reason: a background server in the
    # swarm failing to write is just as real as the active one failing.
    connection_error = Signal(str, str)                # (conn_id, message)
    # The global STOP: emitted with a StopAllSummary when it starts (state
    # "sending") and again when every server has answered or given up.
    stop_all_changed = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.connections: dict[str, HydraConnection] = {}
        self._active_id: str = ""
        self.stop_all_summary: StopAllSummary | None = None

    # --- connection management --------------------------------------------

    def add_server(self, info: ServerInfo) -> str:
        conn_id = f"{info.host}:{info.port}"
        if conn_id in self.connections:
            return conn_id
        conn = HydraConnection(info, parent=self)
        conn.state_changed.connect(lambda state, cid=conn_id: self._on_state_changed(cid, state))
        conn.status_changed.connect(lambda status, cid=conn_id: self._on_status_changed(cid, status))
        conn.metrics_changed.connect(lambda metrics, cid=conn_id: self._on_metrics_changed(cid, metrics))
        conn.login_changed.connect(lambda ok, detail, cid=conn_id: self.connection_login_changed.emit(cid, ok, detail))
        conn.error.connect(lambda message, cid=conn_id: self.connection_error.emit(cid, message))
        self.connections[conn_id] = conn
        spawn(conn.connect())
        self.connections_changed.emit()
        if not self._active_id:
            self.set_active(conn_id)
        return conn_id

    def remove_server(self, conn_id: str) -> None:
        conn = self.connections.pop(conn_id, None)
        if conn is None:
            return
        spawn(conn.disconnect())
        self.connections_changed.emit()
        if self._active_id == conn_id:
            remaining = next(iter(self.connections), "")
            self.set_active(remaining)

    def set_active(self, conn_id: str) -> None:
        if conn_id == self._active_id:
            return
        self._active_id = conn_id
        self.active_connection_changed.emit(conn_id)
        conn = self.connections.get(conn_id)
        if conn is not None:
            self.active_state_changed.emit(conn.state)
            self.active_status_changed.emit("connected" if conn.is_connected else "connecting")

    @property
    def active_connection(self) -> HydraConnection | None:
        return self.connections.get(self._active_id)

    @property
    def active_state(self) -> HydraState | None:
        conn = self.active_connection
        return conn.state if conn is not None else None

    def _on_state_changed(self, conn_id: str, state: HydraState) -> None:
        if conn_id == self._active_id:
            self.active_state_changed.emit(state)

    def _on_status_changed(self, conn_id: str, status: str) -> None:
        self.connection_status_changed.emit(conn_id, status)
        if conn_id == self._active_id:
            self.active_status_changed.emit(status)

    def _on_metrics_changed(self, conn_id: str, metrics: dict) -> None:
        if conn_id == self._active_id:
            self.active_metrics_changed.emit(metrics)

    def push_active_state(self) -> None:
        """Call after mutating the active connection's own HydraState in
        place (e.g. a jog slider changed a joint value) - schedules the
        actual network write."""
        conn = self.active_connection
        if conn is not None:
            asyncio.ensure_future(conn.push_state())

    def send_robot_command(
        self,
        robot_id: int,
        command: str,
        params: dict | None = None,
        local_mutate: Callable[[RobotView], None] | None = None,
        debounce_ms: float = 0,
    ) -> None:
        """Call for a discrete action that already has an atomic
        /api/robot/:id/command case server-side (see HydraConnection.send_command()'s
        own comment) - use instead of mutating state + push_active_state()
        for those, not in addition to it. `local_mutate` is passed straight
        through to send_command() for an optimistic update with
        rollback-on-failure - see that method's own comment. `debounce_ms`
        is passed straight through too - see send_command()'s own comment
        for exactly what it delays (only the network send, never the
        optimistic local mutation)."""
        conn = self.active_connection
        if conn is not None:
            asyncio.ensure_future(conn.send_command(robot_id, command, params, local_mutate, debounce_ms))

    # --- global STOP ----------------------------------------------------------

    def stop_all(self) -> None:
        """The global STOP: stops every robot on every server of the swarm,
        whichever is active, at once (nothing is awaited first). The result
        is published through `stop_all_changed`."""
        asyncio.ensure_future(self._stop_all())

    async def _stop_all(self) -> None:
        connections = dict(self.connections)
        if not connections:
            self._publish_stop_all(StopAllSummary("not_confirmed", reason=_("STOP_ALL_NO_SERVER")))
            return
        self._publish_stop_all(StopAllSummary("sending"))
        outcomes = await asyncio.gather(*(c.stop_all() for c in connections.values()), return_exceptions=True)
        results: dict[str, StopAllResult] = {}
        for conn_id, outcome in zip(connections, outcomes):
            if isinstance(outcome, StopAllResult):
                results[conn_id] = outcome
            else:  # an unexpected failure is still "not confirmed", never a silent success
                results[conn_id] = StopAllResult.not_confirmed(str(outcome) or outcome.__class__.__name__)
        state = "done" if all(r.confirmed for r in results.values()) else "not_confirmed"
        self._publish_stop_all(StopAllSummary(state, results))

    def _publish_stop_all(self, summary: StopAllSummary) -> None:
        self.stop_all_summary = summary
        self.stop_all_changed.emit(summary)

    async def shutdown(self) -> None:
        for conn in list(self.connections.values()):
            try:
                await conn.disconnect()
            except Exception as error:  # one stuck server must not keep the others open
                logger.warning("closing %s failed: %s", conn.info.host, error)
