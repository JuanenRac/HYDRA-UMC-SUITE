# =============================================================================
# HYDRA-UMC SUITE - ui/panels/server_browser.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The swarm control center: scans the local subnet(s) for real HYDRA-UMC
# STUDIO servers (net/discovery.py), lists every server the user has
# added (whether found by scan or typed in manually - the manual path is
# also how a VPN-tunneled HYDRA-UMC on a different physical network gets
# reached, see discovery.py's own header comment for why that needs no
# special VPN-aware code), and lets the user pick which one is "active"
# for every other panel to show/control.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import ServerInfo
from hydra_suite.net.discovery import DEFAULT_PORT, scan_subnets

STATUS_OBJECT_NAMES = {
    "connected": "statusOnline",
    "connecting": "statusConnecting",
    "disconnected": "statusOffline",
    "error": "statusOffline",
}

STATUS_DISPLAY_KEYS = {
    "connected": "STATUS_CONNECTED",
    "connecting": "STATUS_CONNECTING",
    "disconnected": "STATUS_DISCONNECTED",
    "error": "STATUS_ERROR",
}


class ServerBrowserPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._statuses: dict[str, str] = {}
        self._scanning = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_SERVERS"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        scan_row = QHBoxLayout()
        self._scan_button = QPushButton(_("BTN_SCAN_NETWORK"))
        self._scan_button.setObjectName("primaryAction")
        self._scan_button.clicked.connect(self._on_scan_clicked)
        scan_row.addWidget(self._scan_button)
        self._scan_status = QLabel("")
        self._scan_status.setStyleSheet("color: #7f8ea1;")
        scan_row.addWidget(self._scan_status, 1)
        layout.addLayout(scan_row)

        manual_row = QHBoxLayout()
        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText(_("PLACEHOLDER_HOST"))
        manual_row.addWidget(self._host_edit, 1)
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(DEFAULT_PORT)
        manual_row.addWidget(self._port_spin)
        add_button = QPushButton(_("BTN_ADD"))
        add_button.clicked.connect(self._on_add_manual)
        manual_row.addWidget(add_button)
        layout.addLayout(manual_row)

        columns = (_("COL_SERVER"), _("COL_HOST"), _("COL_ROBOTS"), _("COL_STATUS"))
        self._table = QTableWidget(0, len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_row_activated)
        layout.addWidget(self._table, 1)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        self._remove_button = QPushButton(_("BTN_REMOVE_SELECTED"))
        self._remove_button.setObjectName("dangerAction")
        self._remove_button.clicked.connect(self._on_remove_selected)
        remove_row.addWidget(self._remove_button)
        activate_button = QPushButton(_("BTN_SET_ACTIVE"))
        activate_button.setObjectName("primaryAction")
        activate_button.clicked.connect(self._on_activate_selected)
        remove_row.addWidget(activate_button)
        layout.addLayout(remove_row)

        controller.connections_changed.connect(self._refresh_table)
        controller.active_connection_changed.connect(lambda _: self._refresh_table())
        controller.active_status_changed.connect(self._on_active_status)

    # --- scanning -----------------------------------------------------------

    def _on_scan_clicked(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._scan_button.setEnabled(False)
        self._scan_status.setText(_("STATUS_SCANNING"))
        asyncio.ensure_future(self._run_scan())

    async def _run_scan(self) -> None:
        found = 0
        try:
            async for info in scan_subnets():
                found += 1
                self._controller.add_server(info)
                self._scan_status.setText(_("STATUS_SCANNING_PROGRESS", found=found))
        finally:
            self._scanning = False
            self._scan_button.setEnabled(True)
            self._scan_status.setText(_("STATUS_SCAN_COMPLETE", found=found) if found else _("STATUS_SCAN_COMPLETE_NONE"))

    def _on_add_manual(self) -> None:
        host = self._host_edit.text().strip()
        if not host:
            return
        port = self._port_spin.value()
        info = ServerInfo(host=host, port=port, hostname=host)
        conn_id = self._controller.add_server(info)
        # A manually-added server's real identity (hostname, robot count,
        # etc.) arrives once its own GET /api/settings / WebSocket connect
        # completes and state_changed fires - the row shows the typed
        # host immediately, refined automatically once that lands (see
        # _refresh_table, called from connections_changed/active_state_changed).
        self._host_edit.clear()

    # --- table --------------------------------------------------------------

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._controller.connections))
        active_id = self._controller._active_id  # internal, but this panel owns the "which row is bold" concern
        for row, (conn_id, conn) in enumerate(self._controller.connections.items()):
            name_item = QTableWidgetItem(conn.info.display_name)
            if conn_id == active_id:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(f"{conn.info.host}:{conn.info.port}"))
            robot_count = len(conn.state.active_controller.robots) if conn.state.active_controller else conn.info.robot_count
            self._table.setItem(row, 2, QTableWidgetItem(str(robot_count)))
            status = self._statuses.get(conn_id, "connecting")
            self._table.setItem(row, 3, QTableWidgetItem(_(STATUS_DISPLAY_KEYS.get(status, "STATUS_CONNECTING"))))
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, conn_id)

    def _on_active_status(self, status: str) -> None:
        conn = self._controller.active_connection
        if conn is not None:
            conn_id = f"{conn.info.host}:{conn.info.port}"
            self._statuses[conn_id] = status
        self._refresh_table()

    def _selected_conn_id(self) -> str | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_row_activated(self, row: int, _col: int) -> None:
        item = self._table.item(row, 0)
        if item is not None:
            self._controller.set_active(item.data(Qt.ItemDataRole.UserRole))

    def _on_activate_selected(self) -> None:
        conn_id = self._selected_conn_id()
        if conn_id:
            self._controller.set_active(conn_id)

    def _on_remove_selected(self) -> None:
        conn_id = self._selected_conn_id()
        if conn_id:
            self._controller.remove_server(conn_id)
