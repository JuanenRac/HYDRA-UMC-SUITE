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
# not the robot roster itself.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

POLL_MS = 5000


class AdminClientsPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_ADMIN_CLIENTS"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._status_label = QLabel(_("MSG_ADMIN_ONLY"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [_("COL_CLIENT_USER"), _("COL_CLIENT_ROLE"), _("COL_CLIENT_ADDRESS"), _("COL_CLIENT_SCHEMA"), _("COL_STATUS")]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh()))
        self._timer.start()

        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh()))
        asyncio.ensure_future(self._refresh())

    async def _refresh(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            self._table.setRowCount(0)
            return
        if not conn.is_admin:
            self._status_label.setText(_("MSG_ADMIN_ONLY"))
            self._table.setRowCount(0)
            return
        result = await conn.fetch_admin_clients()
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        clients = body.get("clients") or []
        self._status_label.setText(_("LBL_CLIENTS_REFRESH_NOTE", seconds=POLL_MS // 1000))
        self._table.setRowCount(len(clients))
        for row, c in enumerate(clients):
            self._table.setItem(row, 0, QTableWidgetItem(str(c.get("username") or _("LBL_CLIENT_UNKNOWN"))))
            self._table.setItem(row, 1, QTableWidgetItem(str(c.get("role") or "?")))
            self._table.setItem(row, 2, QTableWidgetItem(str(c.get("remoteAddress") or "-")))
            self._table.setItem(row, 3, QTableWidgetItem(str(c.get("remoteApiVersion") if c.get("remoteApiVersion") is not None else "?")))
            self._table.setItem(row, 4, QTableWidgetItem(_("CLIENT_OPEN") if c.get("connected") else _("CLIENT_CLOSING")))
