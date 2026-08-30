# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ecosystem_services_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own EcosystemServices.tsx -
# same real route (GET /api/ecosystem/status against the ACTIVE
# connection's own Server). Grouped by family (the same grouping the
# manifests themselves already carry) into a real card grid, with a
# search box and family filter chips, matching STUDIO's 0.2.9 redesign -
# deliberately still no start/stop button: no process supervisor exists
# anywhere in the ecosystem today (server.ts's only process-control route,
# POST /api/admin/restart, restarts the Server itself, not a sibling repo).
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

_STACK_COLOR = {
    "python": "#e0c040",
    "node": "#4caf50",
    "rust": "#e08030",
    "go": "#4fc3f7",
    "android": "#4caf50",
    "flutter": "#38bdf8",
    "firmware-c": "#c060e0",
}


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


class EcosystemServicesPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._projects: list[dict] = []
        self._family_filter: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header_row = QHBoxLayout()
        heading = QLabel(_("HEADING_ECOSYSTEM_SERVICES"))
        heading.setObjectName("panelHeading")
        header_row.addWidget(heading)
        header_row.addStretch(1)
        self._refresh_btn = QPushButton(_("BTN_REFRESH"))
        self._refresh_btn.clicked.connect(lambda: asyncio.ensure_future(self._refresh()))
        header_row.addWidget(self._refresh_btn)
        outer.addLayout(header_row)

        self._status_label = QLabel(_("LBL_ES_NOT_LOADED"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        outer.addWidget(self._status_label)

        stats_row = QHBoxLayout()
        self._stat_total_box, self._stat_total = _stat_box(_("LBL_SERVICES_STAT_TOTAL"))
        self._stat_live_box, self._stat_live = _stat_box(_("LBL_SERVICES_STAT_LIVE"))
        self._stat_families_box, self._stat_families = _stat_box(_("LBL_SERVICES_STAT_FAMILIES"))
        for box in (self._stat_total_box, self._stat_live_box, self._stat_families_box):
            stats_row.addWidget(box)
            box.setVisible(False)
        outer.addLayout(stats_row)

        filter_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(_("SERVICES_SEARCH_PLACEHOLDER"))
        self._search.textChanged.connect(self._rebuild)
        filter_row.addWidget(self._search, 1)
        self._family_buttons_row = QHBoxLayout()
        filter_row.addLayout(self._family_buttons_row)
        outer.addLayout(filter_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch(1)
        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

        self._note_label = QLabel(_("MSG_ES_NO_CONTROL"))
        self._note_label.setWordWrap(True)
        self._note_label.setStyleSheet("color: #556070; font-size: 10px;")
        outer.addWidget(self._note_label)

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
            self._projects = []
            self._rebuild()
            return
        self._projects = body.get("projects") or []
        scanned_at = body.get("scannedAt") or "-"
        self._status_label.setText(_("LBL_ES_SCANNED_AT", time=scanned_at))
        self._rebuild_family_buttons()
        self._rebuild()

    def _rebuild_family_buttons(self) -> None:
        while self._family_buttons_row.count():
            item = self._family_buttons_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        families = sorted({p.get("family") for p in self._projects if p.get("family")})
        all_btn = QPushButton(_("SERVICES_ALL_FAMILIES"))
        all_btn.setCheckable(True)
        all_btn.setChecked(self._family_filter is None)
        all_btn.clicked.connect(lambda: self._set_family_filter(None))
        self._family_buttons_row.addWidget(all_btn)
        for family in families:
            btn = QPushButton(family)
            btn.setCheckable(True)
            btn.setChecked(self._family_filter == family)
            btn.clicked.connect(lambda _checked=False, f=family: self._set_family_filter(f))
            self._family_buttons_row.addWidget(btn)

    def _set_family_filter(self, family: str | None) -> None:
        self._family_filter = family
        self._rebuild_family_buttons()
        self._rebuild()

    def _rebuild(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        needle = self._search.text().strip().lower()
        filtered = [
            p for p in self._projects
            if (self._family_filter is None or p.get("family") == self._family_filter)
            and (not needle or needle in str(p.get("name", "")).lower())
        ]

        total = len(self._projects)
        live = sum(1 for p in self._projects if p.get("live") is True)
        families = len({p.get("family") for p in self._projects if p.get("family")})
        for box in (self._stat_total_box, self._stat_live_box, self._stat_families_box):
            box.setVisible(total > 0)
        if total > 0:
            self._stat_total.setText(str(total))
            self._stat_live.setText(str(live))
            self._stat_families.setText(str(families))

        grouped: dict[str, list[dict]] = {}
        for p in filtered:
            key = p.get("family") or _("SERVICES_NO_FAMILY")
            grouped.setdefault(key, []).append(p)

        for family in sorted(grouped.keys()):
            items = grouped[family]
            group_label = QLabel(f"{family}  ({len(items)})")
            group_label.setStyleSheet("color: #7f8ea1; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;")
            self._content_layout.insertWidget(self._content_layout.count() - 1, group_label)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(8)
            for i, p in enumerate(items):
                grid.addWidget(self._build_card(p), i // 3, i % 3)
            self._content_layout.insertWidget(self._content_layout.count() - 1, grid_widget)

        if not grouped:
            empty = QLabel(_("MSG_ES_NONE"))
            empty.setStyleSheet("color: #556070; font-size: 11px;")
            self._content_layout.insertWidget(self._content_layout.count() - 1, empty)

    def _build_card(self, project: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #12161c; border: 1px solid #262b33; border-radius: 8px; }")
        card.setMinimumWidth(200)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        name_label = QLabel(str(project.get("name") or "-"))
        name_label.setStyleSheet("color: #e6e6e6; font-size: 11px; font-weight: 700;")
        name_label.setWordWrap(True)
        top_row.addWidget(name_label, 1)
        live = project.get("live")
        dot_color = "#4caf50" if live is True else "#e05050" if live is False else "#556070"
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 12px;")
        top_row.addWidget(dot)
        layout.addLayout(top_row)

        tags_row = QHBoxLayout()
        stack = project.get("stack")
        if stack:
            stack_label = QLabel(stack)
            color = _STACK_COLOR.get(stack, "#7f8ea1")
            stack_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; text-transform: uppercase;")
            tags_row.addWidget(stack_label)
        maturity = project.get("maturity")
        if maturity:
            maturity_label = QLabel(maturity)
            maturity_label.setStyleSheet("color: #556070; font-size: 9px; font-weight: 700; text-transform: uppercase;")
            tags_row.addWidget(maturity_label)
        tags_row.addStretch(1)
        layout.addLayout(tags_row)

        bottom_row = QHBoxLayout()
        version_label = QLabel(f"v{project.get('version')}" if project.get("version") else "-")
        version_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
        bottom_row.addWidget(version_label)
        bottom_row.addStretch(1)
        port_label = QLabel(f":{project.get('servicePort')}" if project.get("servicePort") else "-")
        port_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
        bottom_row.addWidget(port_label)
        layout.addLayout(bottom_row)

        return card
