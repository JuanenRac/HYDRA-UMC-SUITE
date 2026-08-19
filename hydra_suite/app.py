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

from PySide6.QtCore import QObject, Signal

from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection


class SuiteController(QObject):
    connections_changed = Signal()                  # the dict of connections itself changed (added/removed)
    active_connection_changed = Signal(str)          # active connection id changed (may be "")
    active_state_changed = Signal(object)            # HydraState - the active connection's own state changed
    active_status_changed = Signal(str)              # the active connection's own status changed
    active_metrics_changed = Signal(dict)            # the active connection's own GET /api/system/metrics, polled every 5s

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.connections: dict[str, HydraConnection] = {}
        self._active_id: str = ""

    # --- connection management --------------------------------------------

    def add_server(self, info: ServerInfo) -> str:
        conn_id = f"{info.host}:{info.port}"
        if conn_id in self.connections:
            return conn_id
        conn = HydraConnection(info, parent=self)
        conn.state_changed.connect(lambda state, cid=conn_id: self._on_state_changed(cid, state))
        conn.status_changed.connect(lambda status, cid=conn_id: self._on_status_changed(cid, status))
        conn.metrics_changed.connect(lambda metrics, cid=conn_id: self._on_metrics_changed(cid, metrics))
        self.connections[conn_id] = conn
        asyncio.ensure_future(conn.connect())
        self.connections_changed.emit()
        if not self._active_id:
            self.set_active(conn_id)
        return conn_id

    def remove_server(self, conn_id: str) -> None:
        conn = self.connections.pop(conn_id, None)
        if conn is None:
            return
        asyncio.ensure_future(conn.disconnect())
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

    async def shutdown(self) -> None:
        for conn in list(self.connections.values()):
            await conn.disconnect()
