# =============================================================================
# HYDRA-UMC SUITE - ui/panels/admin_logs_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own AdminLogs.tsx and
# HYDRA-UMC-SERVER's own admin-ui/src/tabs/LogsTab.tsx - same route
# (GET /api/admin/logs, admin-only) against the ACTIVE connection's own
# Server. NOT the same thing as this app's own LogsPanel (logs_panel.py),
# which shows SUITE's own local Python logging output - this shows the
# remote Server's own on-disk log file instead.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

POLL_MS = 3000
LINES = 300


class AdminLogsPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._live = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        heading = QLabel(_("HEADING_ADMIN_LOGS"))
        heading.setObjectName("panelHeading")
        header_row.addWidget(heading)
        header_row.addStretch(1)
        self._pause_btn = QPushButton(_("BTN_PAUSE"))
        self._pause_btn.clicked.connect(self._toggle_live)
        header_row.addWidget(self._pause_btn)
        layout.addLayout(header_row)

        self._status_label = QLabel(_("MSG_ADMIN_ONLY"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self._text, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh()))
        self._timer.start()

        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh()))
        asyncio.ensure_future(self._refresh())

    def _toggle_live(self) -> None:
        self._live = not self._live
        self._pause_btn.setText(_("BTN_RESUME") if not self._live else _("BTN_PAUSE"))

    async def _refresh(self) -> None:
        if not self._live:
            return
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            return
        if not conn.is_admin:
            self._status_label.setText(_("MSG_ADMIN_ONLY"))
            self._text.clear()
            return
        result = await conn.fetch_admin_logs(LINES)
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        lines = body.get("lines") or []
        self._status_label.setText(_("LBL_LOGS_FOOTER_LIVE", lines=LINES, seconds=POLL_MS // 1000))
        scrollbar = self._text.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        self._text.setPlainText("\n".join(lines) if lines else _("MSG_LOGS_NONE"))
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
