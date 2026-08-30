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
#
# Adds a real search box and a tag filter (extracted client-side from
# each line's own leading `[TAG]` - industrialLog()'s own convention:
# [ADMIN], [WS], [VOICE], [job-dispatcher], ... - matching STUDIO's own
# 0.2.9 redesign and the same real, honest filterable dimension that
# actually exists in these lines (the server never sends a structured
# level).
# =============================================================================
from __future__ import annotations

import asyncio
import re

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

POLL_MS = 3000
LINES = 300
_TAG_RE = re.compile(r"\[([A-Za-z0-9_-]+)]")


def _extract_tag(line: str) -> str | None:
    m = _TAG_RE.search(line)
    return m.group(1) if m else None


class AdminLogsPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._live = True
        self._all_lines: list[str] = []
        self._tag_filter: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header_row = QHBoxLayout()
        heading = QLabel(_("HEADING_ADMIN_LOGS"))
        heading.setObjectName("panelHeading")
        header_row.addWidget(heading)
        header_row.addStretch(1)
        self._pause_btn = QPushButton(_("BTN_PAUSE"))
        self._pause_btn.clicked.connect(self._toggle_live)
        header_row.addWidget(self._pause_btn)
        outer.addLayout(header_row)

        self._status_label = QLabel(_("MSG_ADMIN_ONLY"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        outer.addWidget(self._status_label)

        filter_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(_("LOGS_SEARCH_PLACEHOLDER"))
        self._search.textChanged.connect(self._render)
        filter_row.addWidget(self._search, 1)
        self._tag_buttons_row = QHBoxLayout()
        filter_row.addLayout(self._tag_buttons_row)
        outer.addLayout(filter_row)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        outer.addWidget(self._text, 1)

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
            self._all_lines = []
            self._render()
            return
        result = await conn.fetch_admin_logs(LINES)
        if result is None:
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_ADMIN_LOAD_ERROR"))
            return
        self._all_lines = body.get("lines") or []
        self._status_label.setText(_("LBL_LOGS_FOOTER_LIVE", lines=LINES, seconds=POLL_MS // 1000))
        self._rebuild_tag_buttons()
        self._render()

    def _rebuild_tag_buttons(self) -> None:
        while self._tag_buttons_row.count():
            item = self._tag_buttons_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        tags = sorted({tag for line in self._all_lines if (tag := _extract_tag(line))})
        all_btn = QPushButton(_("LOGS_ALL_TAGS"))
        all_btn.setCheckable(True)
        all_btn.setChecked(self._tag_filter is None)
        all_btn.clicked.connect(lambda: self._set_tag_filter(None))
        self._tag_buttons_row.addWidget(all_btn)
        for tag in tags:
            btn = QPushButton(tag)
            btn.setCheckable(True)
            btn.setChecked(self._tag_filter == tag)
            btn.clicked.connect(lambda _checked=False, t=tag: self._set_tag_filter(t))
            self._tag_buttons_row.addWidget(btn)

    def _set_tag_filter(self, tag: str | None) -> None:
        self._tag_filter = tag
        self._rebuild_tag_buttons()
        self._render()

    def _render(self) -> None:
        scrollbar = self._text.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4

        needle = self._search.text().strip().lower()
        filtered = [
            line for line in self._all_lines
            if (self._tag_filter is None or _extract_tag(line) == self._tag_filter)
            and (not needle or needle in line.lower())
        ]

        if not filtered:
            self._text.setPlainText(_("MSG_LOGS_NONE") if not self._all_lines else _("LOGS_NO_MATCH"))
        else:
            self._text.setPlainText("\n".join(filtered))
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
