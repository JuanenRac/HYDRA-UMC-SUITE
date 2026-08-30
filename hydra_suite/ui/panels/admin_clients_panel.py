# =============================================================================
# HYDRA-UMC SUITE - ui/panels/admin_clients_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own AdminClients.tsx and
# HYDRA-UMC-SERVER's own admin-ui/src/tabs/DevicesTab.tsx - same route
# (GET /api/admin/clients, admin-only), same fields, same 5s poll.
# Purely informational: every live WebSocket connection to the ACTIVE
# connection's own Server right now (STUDIO tabs, mobile apps, this same
# app's OTHER connections included if they point at the same server) -
# not the robot roster itself. Admin-first sort and a live "Xm ago"
# duration (ticking every second, independent of the 5s data poll) in
# place of a raw ISO timestamp, matching STUDIO's own 0.2.9 redesign.
# =============================================================================
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

POLL_MS = 5000


def _stat_box(label_text: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(10, 6, 10, 6)
    box.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
    caption = QLabel(label_text)
    caption.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
    layout.addWidget(caption)
    value = QLabel("-")
    value.setStyleSheet("color: #e6e6e6; font-size: 20px; font-weight: 800;")
    layout.addWidget(value)
    return box, value


def _relative_duration(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    seconds = max(0, int((datetime.now(timezone.utc) - then).total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"


class AdminClientsPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._clients: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        heading = QLabel(_("HEADING_ADMIN_CLIENTS"))
        heading.setObjectName("panelHeading")
        outer.addWidget(heading)

        self._status_label = QLabel(_("MSG_ADMIN_ONLY"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        outer.addWidget(self._status_label)

        stats_row = QHBoxLayout()
        self._stat_connected_box, self._stat_connected = _stat_box(_("LBL_CLIENTS_STAT_CONNECTED"))
        self._stat_admins_box, self._stat_admins = _stat_box(_("LBL_CLIENTS_STAT_ADMINS"))
        for box in (self._stat_connected_box, self._stat_admins_box):
            stats_row.addWidget(box)
            box.setVisible(False)
        outer.addLayout(stats_row)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch(1)
        outer.addLayout(self._list_layout, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh()))
        self._timer.start()

        # Ticks the "Xm ago" durations forward once a second, independent
        # of the 5s data poll - same reasoning as STUDIO's own redesign.
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._rebuild)
        self._tick_timer.start()

        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh()))
        asyncio.ensure_future(self._refresh())

    async def _refresh(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            self._clients = []
            self._rebuild()
            return
        if not conn.is_admin:
            self._status_label.setText(_("MSG_ADMIN_ONLY"))
            self._clients = []
            self._rebuild()
            return
        result = await conn.fetch_admin_clients()
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        self._clients = body.get("clients") or []
        self._status_label.setText(_("LBL_CLIENTS_REFRESH_NOTE", seconds=POLL_MS // 1000))
        self._rebuild()

    def _rebuild(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sorted_clients = sorted(
            self._clients,
            key=lambda c: (c.get("role") != "admin", str(c.get("username") or "")),
        )
        admin_count = sum(1 for c in sorted_clients if c.get("role") == "admin")
        for box in (self._stat_connected_box, self._stat_admins_box):
            box.setVisible(len(sorted_clients) > 0)
        if sorted_clients:
            self._stat_connected.setText(str(len(sorted_clients)))
            self._stat_admins.setText(str(admin_count))

        if not sorted_clients:
            empty = QLabel(_("MSG_CLIENTS_NONE"))
            empty.setStyleSheet("color: #556070; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for c in sorted_clients:
            row = QWidget()
            row.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)

            is_admin = c.get("role") == "admin"
            badge = QLabel("A" if is_admin else "U")
            badge_color = "#4caf50" if is_admin else "#38bdf8"
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"background: {badge_color}22; color: {badge_color}; border-radius: 12px; font-weight: 800; font-size: 10px;")
            row_layout.addWidget(badge)

            text_col = QVBoxLayout()
            name_label = QLabel(str(c.get("username") or _("LBL_CLIENT_UNKNOWN")))
            name_label.setStyleSheet("color: #e6e6e6; font-size: 11px; font-weight: 700;")
            text_col.addWidget(name_label)
            addr_label = QLabel(str(c.get("remoteAddress") or "-"))
            addr_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
            text_col.addWidget(addr_label)
            row_layout.addLayout(text_col)
            row_layout.addStretch(1)

            role_label = QLabel(str(c.get("role") or "?").upper())
            role_label.setStyleSheet(f"color: {badge_color}; font-size: 9px; font-weight: 800;")
            row_layout.addWidget(role_label)

            duration_label = QLabel(_relative_duration(c.get("connectedAt")))
            duration_label.setStyleSheet("color: #7f8ea1; font-size: 9px; font-family: Consolas, monospace;")
            row_layout.addWidget(duration_label)

            dot = QLabel("●")
            dot_color = "#4caf50" if c.get("connected") else "#e05050"
            dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
            row_layout.addWidget(dot)

            self._list_layout.insertWidget(self._list_layout.count() - 1, row)
