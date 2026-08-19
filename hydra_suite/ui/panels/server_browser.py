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
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
    "login_failed": "statusOffline",
}

STATUS_DISPLAY_KEYS = {
    "connected": "STATUS_CONNECTED",
    "connecting": "STATUS_CONNECTING",
    "disconnected": "STATUS_DISCONNECTED",
    "error": "STATUS_ERROR",
    # Distinct from "error" on purpose - a WebSocket link that dropped and a
    # server that flat-out rejected the configured username/password are
    # different problems with different fixes (wait/retry vs. edit
    # credentials), and showing both as the same generic "Error" is exactly
    # how a bad password used to look identical to "still connecting" with
    # no way to tell them apart from this table.
    "login_failed": "STATUS_LOGIN_FAILED",
}


class CredentialsDialog(QDialog):
    """Small modal to view/edit the username+password ServerInfo already
    carries per-server (POST /api/login body) - the only place in the UI
    that lets the user see or change them, since neither the scan nor the
    manual-add row show what credentials a server will actually try."""

    def __init__(self, username: str, password: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(_("TITLE_EDIT_CREDENTIALS"))
        layout = QFormLayout(self)
        self._username_edit = QLineEdit(username)
        self._password_edit = QLineEdit(password)
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow(_("LBL_USERNAME"), self._username_edit)
        layout.addRow(_("LBL_PASSWORD"), self._password_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def credentials(self) -> tuple[str, str]:
        return self._username_edit.text(), self._password_edit.text()


class ServerBrowserPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._statuses: dict[str, str] = {}
        # (ok, detail) from the connection's own last login attempt - None
        # until at least one attempt has actually happened, so a
        # brand-new row shows "Connecting..." rather than a stale/wrong
        # "Login failed" before login() has ever run for it once.
        self._login_status: dict[str, tuple[bool, str]] = {}
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
        # Every real HYDRA-UMC STUDIO server seeds the same default admin/admin
        # account on its own first-ever start (see models.py's own ServerInfo
        # docstring) - these two fields default to it too, editable right here
        # for a server whose admin account was renamed or that uses a
        # dedicated operator account instead, without a separate dialog step
        # for the common case.
        self._username_edit = QLineEdit("admin")
        self._username_edit.setPlaceholderText(_("LBL_USERNAME"))
        self._username_edit.setMaximumWidth(90)
        manual_row.addWidget(self._username_edit)
        self._password_edit = QLineEdit("admin")
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText(_("LBL_PASSWORD"))
        self._password_edit.setMaximumWidth(90)
        manual_row.addWidget(self._password_edit)
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
        credentials_button = QPushButton(_("BTN_EDIT_CREDENTIALS"))
        credentials_button.clicked.connect(self._on_edit_credentials)
        remove_row.addWidget(credentials_button)
        activate_button = QPushButton(_("BTN_SET_ACTIVE"))
        activate_button.setObjectName("primaryAction")
        activate_button.clicked.connect(self._on_activate_selected)
        remove_row.addWidget(activate_button)
        layout.addLayout(remove_row)

        controller.connections_changed.connect(self._refresh_table)
        controller.active_connection_changed.connect(lambda _: self._refresh_table())
        # Per-connection (ALL servers, not just whichever one is active) -
        # see app.py's own comment on these two signals for why the
        # active_* ones alone left every non-active row's status frozen.
        controller.connection_status_changed.connect(self._on_connection_status)
        controller.connection_login_changed.connect(self._on_connection_login)

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
        username = self._username_edit.text().strip() or "admin"
        password = self._password_edit.text()
        info = ServerInfo(host=host, port=port, hostname=host, username=username, password=password)
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
            # A failed login overrides whatever the raw WS status says - the
            # WebSocket itself may simply be "disconnected" (never got far
            # enough to open, since _run() in client.py refuses to even try
            # opening it without a token) which reads exactly like "still
            # connecting" unless the login outcome is checked first here.
            login = self._login_status.get(conn_id)
            if login is not None and not login[0]:
                status = "login_failed"
            else:
                status = self._statuses.get(conn_id, "connecting")
            status_item = QTableWidgetItem(_(STATUS_DISPLAY_KEYS.get(status, "STATUS_CONNECTING")))
            if login is not None and not login[0] and login[1]:
                status_item.setToolTip(login[1])
            self._table.setItem(row, 3, status_item)
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, conn_id)

    def _on_connection_status(self, conn_id: str, status: str) -> None:
        self._statuses[conn_id] = status
        self._refresh_table()

    def _on_connection_login(self, conn_id: str, ok: bool, detail: str) -> None:
        self._login_status[conn_id] = (ok, detail)
        self._refresh_table()

    def _on_edit_credentials(self) -> None:
        conn_id = self._selected_conn_id()
        if not conn_id:
            return
        conn = self._controller.connections.get(conn_id)
        if conn is None:
            return
        dialog = CredentialsDialog(conn.info.username, conn.info.password, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        username, password = dialog.credentials()
        conn.info.username = username or "admin"
        conn.info.password = password
        # Credentials just changed - the running connection may be sitting
        # on a stale/rejected token (or none at all, if the old ones never
        # worked) from BEFORE the edit, so force a clean reconnect rather
        # than waiting for _run()'s own retry loop to eventually notice on
        # its own timer.
        asyncio.ensure_future(self._reconnect(conn))

    @staticmethod
    async def _reconnect(conn) -> None:
        await conn.disconnect()
        await conn.connect()

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
