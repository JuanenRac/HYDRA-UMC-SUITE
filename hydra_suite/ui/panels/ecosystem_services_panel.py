# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ecosystem_services_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own EcosystemServices.tsx -
# same real route (GET /api/ecosystem/status against the ACTIVE
# connection's own Server), same fields, same "view + manual refresh
# only" scope: no process supervisor exists anywhere in the ecosystem
# today (server.ts's only process-control route, POST /api/admin/restart,
# restarts Server itself, not a sibling repo), so this deliberately has
# no start/stop button rather than a fake/disabled one.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

_COLUMNS = ["COL_ES_NAME", "COL_ES_ROLE", "COL_ES_STACK", "COL_ES_FAMILY", "COL_ES_VERSION", "COL_ES_MATURITY", "COL_ES_PORT", "COL_STATUS"]


class EcosystemServicesPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        heading = QLabel(_("HEADING_ECOSYSTEM_SERVICES"))
        heading.setObjectName("panelHeading")
        header_row.addWidget(heading)
        header_row.addStretch(1)
        self._refresh_btn = QPushButton(_("BTN_REFRESH"))
        self._refresh_btn.clicked.connect(lambda: asyncio.ensure_future(self._refresh()))
        header_row.addWidget(self._refresh_btn)
        layout.addLayout(header_row)

        self._status_label = QLabel(_("LBL_ES_NOT_LOADED"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([_(k) for k in _COLUMNS])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        note = QLabel(_("MSG_ES_NO_CONTROL"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #7f8ea1; font-size: 10px;")
        layout.addWidget(note)

    async def _refresh(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            return
        self._refresh_btn.setEnabled(False)
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._refresh_btn.setEnabled(True)
        if result is None:
            self._status_label.setText(_("MSG_ES_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ES_LOAD_ERROR"))
            return
        if not body.get("available"):
            self._status_label.setText(_("MSG_ES_UNAVAILABLE"))
            self._table.setRowCount(0)
            return
        projects = body.get("projects") or []
        self._status_label.setText(_("LBL_ES_SCANNED_AT", time=body.get("scannedAt") or "-"))
        self._table.setRowCount(len(projects))
        for row, p in enumerate(projects):
            self._set_cell(row, 0, str(p.get("name") or "-"))
            self._set_cell(row, 1, str(p.get("role") or "-"))
            self._set_cell(row, 2, str(p.get("stack") or "-"))
            self._set_cell(row, 3, str(p.get("family") or "-"))
            self._set_cell(row, 4, str(p.get("version") or "-"))
            self._set_cell(row, 5, str(p.get("maturity") or "-"))
            self._set_cell(row, 6, str(p.get("servicePort")) if p.get("servicePort") is not None else "-")
            live = p.get("live")
            status_text = _("STATUS_ES_LIVE") if live is True else _("STATUS_ES_DEAD") if live is False else _("STATUS_ES_NA")
            item = QTableWidgetItem(status_text)
            if live is True:
                item.setForeground(Qt.GlobalColor.green)
            elif live is False:
                item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, 7, item)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        self._table.setItem(row, col, QTableWidgetItem(text))
