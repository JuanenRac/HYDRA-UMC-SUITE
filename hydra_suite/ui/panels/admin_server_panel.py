# =============================================================================
# HYDRA-UMC SUITE - ui/panels/admin_server_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own AdminServer.tsx - listen
# port (GET/PUT /api/admin/server-config) and a graceful restart
# (POST /api/admin/restart), admin-only, against the ACTIVE connection's
# own Server. Server name stays out of scope here too - same reasoning as
# the STUDIO version (that field belongs to the ordinary settings
# read-modify-write cycle, not this admin-only surface).
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _


class AdminServerPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_port: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_ADMIN_SERVER"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._status_label = QLabel(_("MSG_ADMIN_ONLY"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        form = QGridLayout()
        self._port_label = QLabel(_("LBL_ADMIN_SERVER_PORT"))
        form.addWidget(self._port_label, 0, 0)
        self._port_edit = QLineEdit()
        form.addWidget(self._port_edit, 0, 1)
        self._save_btn = QPushButton(_("BTN_SAVE"))
        self._save_btn.clicked.connect(lambda: asyncio.ensure_future(self._save_port()))
        form.addWidget(self._save_btn, 0, 2)
        layout.addLayout(form)

        note = QLabel(_("MSG_ADMIN_SERVER_PORT_NOTE"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #b08030; font-size: 10px;")
        layout.addWidget(note)

        self._restart_btn = QPushButton(_("BTN_RESTART_SERVER"))
        self._restart_btn.setStyleSheet("color: #e05050;")
        self._restart_btn.clicked.connect(self._confirm_restart)
        layout.addWidget(self._restart_btn)
        layout.addStretch(1)

        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh()))
        asyncio.ensure_future(self._refresh())

    async def _refresh(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            return
        if not conn.is_admin:
            self._status_label.setText(_("MSG_ADMIN_ONLY"))
            return
        result = await conn.fetch_admin_server_config()
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        self._status_label.setText("")
        self._current_port = body.get("port")
        pending = body.get("pendingPort")
        self._port_label.setText(_("LBL_ADMIN_SERVER_PORT_CURRENT", port=self._current_port if self._current_port is not None else "..."))
        self._port_edit.setText(str(pending if pending is not None else self._current_port or ""))

    async def _save_port(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        try:
            port = int(self._port_edit.text())
        except ValueError:
            self._status_label.setText(_("MSG_ADMIN_SERVER_PORT_INVALID"))
            return
        if not (1 <= port <= 65535):
            self._status_label.setText(_("MSG_ADMIN_SERVER_PORT_INVALID"))
            return
        result = await conn.save_admin_server_port(port)
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, _body = result
        if status != 200:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        self._status_label.setText(_("MSG_ADMIN_SERVER_PORT_SAVED"))

    def _confirm_restart(self) -> None:
        answer = QMessageBox.question(
            self,
            _("TITLE_RESTART_SERVER"),
            _("MSG_ADMIN_SERVER_RESTART_CONFIRM"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            asyncio.ensure_future(self._restart())

    async def _restart(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.restart_server()
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, _body = result
        if status != 200:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        self._status_label.setText(_("MSG_ADMIN_SERVER_RESTART_REQUESTED"))
