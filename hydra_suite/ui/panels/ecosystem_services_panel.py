# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ecosystem_services_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own EcosystemServices.tsx -
# same real routes (GET /api/ecosystem/status, POST /api/ecosystem/
# service/:unit/:action) against the ACTIVE connection's own Server -
# see client.py's own control_service()/fetch_ecosystem_status() and
# server.ts's own route comments for the real security boundary (unit
# re-validated server-side against a fresh scan, admin-only, real
# narrowly-scoped polkit rule required on the host). Grouped by family
# into a real card grid, matching STUDIO's own 0.3.7 - same 5-state
# health color (green=running, red=stopped, amber=real error, slate=N/A),
# version shown large inside the badge, real IP:port/PID chips, and
# admin-only Start/Stop/Restart buttons per card, only for a project that
# opted into service.systemd_unit.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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

# Same 4 health colors STUDIO's own healthColor() computes, from the same
# real signals (a port probe's own `live`, a systemd probe's own
# `activeState`) - see EcosystemServices.tsx's own header comment for the
# full reasoning behind each branch, unchanged here.
_HEALTH_COLOR = {
    "green": "#4caf50",
    "red": "#e05050",
    "amber": "#e0a030",
    "slate": "#556070",
}


def _health(project: dict) -> str:
    active_state = project.get("activeState")
    live = project.get("live")
    if active_state == "failed":
        return "amber"
    if active_state == "active":
        return "amber" if live is False else "green"
    if active_state:
        return "red"  # inactive/deactivating/activating under systemd control, not active
    if live is True:
        return "green"
    if live is False:
        return "red"
    return "slate"


def _badge_label(project: dict) -> str:
    active_state = project.get("activeState")
    live = project.get("live")
    if active_state == "failed" or (active_state == "active" and live is False):
        return _("LBL_SERVICES_ERROR")
    if live is True:
        return _("LBL_SERVICES_LIVE")
    if live is False:
        return _("LBL_SERVICES_DEAD")
    if active_state == "active":
        return _("LBL_SERVICES_RUNNING")
    if active_state:
        return _("LBL_SERVICES_STOPPED")
    return _("LBL_SERVICES_NOT_A_SERVICE")


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
        # Which single card's own action is in flight, if any - only that
        # one card's own 3 buttons disable while it resolves, not the
        # whole panel, same as EcosystemServices.tsx's own actioningUnit.
        self._actioning_unit: str | None = None
        self._action_error: tuple[str, str] | None = None  # (unit, message)

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
        self._stat_running_box, self._stat_running = _stat_box(_("LBL_SERVICES_STAT_RUNNING"))
        self._stat_stopped_box, self._stat_stopped = _stat_box(_("LBL_SERVICES_STAT_STOPPED"))
        self._stat_error_box, self._stat_error = _stat_box(_("LBL_SERVICES_STAT_ERROR"))
        self._stat_na_box, self._stat_na = _stat_box(_("LBL_SERVICES_STAT_NA"))
        self._stat_boxes = (
            self._stat_total_box, self._stat_live_box, self._stat_families_box,
            self._stat_running_box, self._stat_stopped_box, self._stat_error_box, self._stat_na_box,
        )
        for box in self._stat_boxes:
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

        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: self._rebuild())

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
        # Same healthColor() the badges use, so this strip and every
        # card can never disagree about which bucket a project is in.
        running = sum(1 for p in self._projects if _health(p) == "green")
        stopped = sum(1 for p in self._projects if _health(p) == "red")
        errored = sum(1 for p in self._projects if _health(p) == "amber")
        not_applicable = sum(1 for p in self._projects if _health(p) == "slate")
        for box in self._stat_boxes:
            box.setVisible(total > 0)
        if total > 0:
            self._stat_total.setText(str(total))
            self._stat_live.setText(str(live))
            self._stat_families.setText(str(families))
            self._stat_running.setText(str(running))
            self._stat_stopped.setText(str(stopped))
            self._stat_error.setText(str(errored))
            self._stat_na.setText(str(not_applicable))

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

    def _build_badge(self, project: dict) -> QWidget:
        health = _health(project)
        color = _HEALTH_COLOR[health]
        badge = QFrame()
        badge.setStyleSheet(
            f"QFrame {{ background: {color}22; border: 1px solid {color}55; border-radius: 6px; }}"
        )
        layout = QVBoxLayout(badge)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        label = QLabel(f"● {_badge_label(project)}")
        label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 800; text-transform: uppercase;")
        layout.addWidget(label)
        version = project.get("version")
        if version:
            version_label = QLabel(f"v{version}")
            version_label.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 800; font-family: Consolas, monospace;")
            layout.addWidget(version_label)
        return badge

    def _build_card(self, project: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #12161c; border: 1px solid #262b33; border-radius: 8px; }")
        card.setMinimumWidth(220)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        name_label = QLabel(str(project.get("name") or "-"))
        name_label.setStyleSheet("color: #e6e6e6; font-size: 11px; font-weight: 700;")
        name_label.setWordWrap(True)
        top_row.addWidget(name_label, 1)
        top_row.addWidget(self._build_badge(project))
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

        # Real feedback from live testing, matching EcosystemServices.tsx's
        # own comment: a TCP/HTTP probe gives serviceHost/servicePort, an
        # opt-in service.systemd_unit gives pid independently of whether
        # that same project exposes a port at all. Only rendered when at
        # least one is real.
        service_host = project.get("serviceHost")
        pid = project.get("pid")
        if service_host or pid is not None:
            info_row = QHBoxLayout()
            if service_host:
                host_label = QLabel(f"{service_host}:{project.get('servicePort')}")
                host_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
                info_row.addWidget(host_label)
            if pid is not None:
                pid_label = QLabel(f"{_('LBL_SERVICES_PID')} {pid}")
                pid_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
                info_row.addWidget(pid_label)
            info_row.addStretch(1)
            layout.addLayout(info_row)

        # Admin-only, and only for a project that opted into
        # service.systemd_unit at all - a project with neither can't be
        # controlled through this route no matter what. Always shows all
        # 3 rather than trying to predict which makes sense from the
        # last-known state (systemd itself handles a redundant stop/start
        # as a harmless no-op) - same reasoning as EcosystemServices.tsx.
        conn = self._controller.active_connection
        unit = project.get("systemdUnit")
        if conn is not None and conn.is_admin and unit:
            actions_row = QHBoxLayout()
            if self._actioning_unit == unit:
                pending = QLabel(_("LBL_SERVICES_ACTION_PENDING"))
                pending.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
                actions_row.addWidget(pending)
            else:
                start_btn = QPushButton(_("BTN_SERVICES_START"))
                start_btn.setStyleSheet("QPushButton { color: #4caf50; font-size: 9px; padding: 3px 8px; }")
                start_btn.clicked.connect(lambda _c=False, u=unit: asyncio.ensure_future(self._run_action(u, "start")))
                actions_row.addWidget(start_btn)

                stop_btn = QPushButton(_("BTN_SERVICES_STOP"))
                stop_btn.setStyleSheet("QPushButton { color: #e05050; font-size: 9px; padding: 3px 8px; }")
                stop_btn.clicked.connect(lambda _c=False, u=unit, n=project.get("name"): self._confirm_action(u, "stop", n))
                actions_row.addWidget(stop_btn)

                restart_btn = QPushButton(_("BTN_SERVICES_RESTART"))
                restart_btn.setStyleSheet("QPushButton { color: #4fc3f7; font-size: 9px; padding: 3px 8px; }")
                restart_btn.clicked.connect(lambda _c=False, u=unit, n=project.get("name"): self._confirm_action(u, "restart", n))
                actions_row.addWidget(restart_btn)
            actions_row.addStretch(1)
            layout.addLayout(actions_row)

        if self._action_error is not None and self._action_error[0] == unit:
            error_label = QLabel(self._action_error[1])
            error_label.setStyleSheet("color: #e05050; font-size: 9px;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        return card

    def _confirm_action(self, unit: str, action: str, name: str | None) -> None:
        title = _("TITLE_SERVICES_CONFIRM_STOP") if action == "stop" else _("TITLE_SERVICES_CONFIRM_RESTART")
        message_key = "MSG_SERVICES_CONFIRM_STOP" if action == "stop" else "MSG_SERVICES_CONFIRM_RESTART"
        answer = QMessageBox.question(
            self, title, _(message_key, name=name or unit),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            asyncio.ensure_future(self._run_action(unit, action))

    async def _run_action(self, unit: str, action: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        self._actioning_unit = unit
        self._action_error = None
        self._rebuild()
        try:
            result = await conn.control_service(unit, action)
        finally:
            self._actioning_unit = None
        if result is None:
            self._action_error = (unit, _("MSG_SERVICES_ACTION_ERROR"))
            self._rebuild()
            return
        status, body = result
        if status != 200:
            message = body.get("error") if isinstance(body, dict) else None
            self._action_error = (unit, message or f"HTTP {status}")
            self._rebuild()
            return
        await self._refresh()
