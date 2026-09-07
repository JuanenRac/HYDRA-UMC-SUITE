# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ai_family_status_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own AiFamilyStatus.tsx - the
# same real GET /api/ecosystem/status scan EcosystemServicesPanel uses,
# filtered to the two families the ecosystem's own manifests self-report
# as AI ("Vision AI Node" - Hailo-8-facing today, "Cognitive AI Node" - the
# planned separate Hailo-10 8GB accelerator's target).
#
# Real cross-reference with Config > AI/Hailo: HydraState.ai_hailo reads
# the SAME server-persisted settings.aiHailo field HYDRA-UMC STUDIO's own
# Config tab writes (GET/POST /api/settings is the one shared settings
# tree both apps read/write) - a family with real live nodes but its
# configured Hailo device set to "None" is a genuine, actionable
# misconfiguration this app already knows about from its own state, not a
# live device query it never makes.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

AI_FAMILIES = [
    ("Vision AI Node", "hailo8", "Hailo-8"),
    ("Cognitive AI Node", "hailo10", "Hailo-10"),
]


class AiFamilyStatusPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._projects: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header_row = QHBoxLayout()
        heading = QLabel(_("HEADING_AI_FAMILY"))
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

        self._warning_label = QLabel("")
        self._warning_label.setWordWrap(True)
        self._warning_label.setStyleSheet("color: #e0a030; background: rgba(224,160,48,0.1); border: 1px solid rgba(224,160,48,0.3); border-radius: 6px; padding: 8px;")
        self._warning_label.setVisible(False)
        outer.addWidget(self._warning_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch(1)
        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh()))
        asyncio.ensure_future(self._refresh())

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
        if status != 200 or not isinstance(body, dict) or not body.get("available"):
            self._status_label.setText(_("MSG_ES_UNAVAILABLE"))
            return
        self._status_label.setText("")
        families = {f for f, _dev, _label in AI_FAMILIES}
        self._projects = [p for p in (body.get("projects") or []) if p.get("family") in families]
        self._rebuild(conn.state.ai_hailo)

    def _rebuild(self, ai_hailo: dict[str, str]) -> None:
        # Clear everything but the trailing stretch.
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        warnings: list[str] = []
        for family, device_key, device_label in AI_FAMILIES:
            items = [p for p in self._projects if p.get("family") == family]
            live_count = sum(1 for p in items if p.get("live") is True)
            configured = ai_hailo.get("visionDevice" if device_key == "hailo8" else "cognitiveDevice", "none")

            if live_count > 0 and configured == "none":
                warnings.append(_("MSG_AI_FAMILY_DEVICE_MISMATCH", family=family, device=device_label))

            group_header = QHBoxLayout()
            label_text = _("LBL_AI_FAMILY_VISION", device=device_label) if device_key == "hailo8" else _("LBL_AI_FAMILY_COGNITIVE", device=device_label)
            group_label = QLabel(label_text)
            group_label.setStyleSheet("color: #7f8ea1; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;")
            group_header.addWidget(group_label)
            group_header.addStretch(1)
            device_pill = QLabel(_("LBL_NONE_DEVICE") if configured == "none" else device_label)
            device_pill.setStyleSheet(
                "color: #7f8ea1; background: rgba(127,142,161,0.15); border-radius: 10px; padding: 2px 10px; font-size: 10px; font-weight: 700;"
                if configured == "none" else
                "color: #4fc3f7; background: rgba(79,195,247,0.12); border-radius: 10px; padding: 2px 10px; font-size: 10px; font-weight: 700;"
            )
            group_header.addWidget(device_pill)
            group_widget = QWidget()
            group_widget.setLayout(group_header)
            self._content_layout.insertWidget(self._content_layout.count() - 1, group_widget)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(8)
            for i, p in enumerate(items):
                card = self._build_card(p)
                grid.addWidget(card, i // 2, i % 2)
            if not items:
                none_label = QLabel(_("MSG_ES_NONE"))
                none_label.setStyleSheet("color: #556070; font-size: 11px;")
                grid.addWidget(none_label, 0, 0)
            self._content_layout.insertWidget(self._content_layout.count() - 1, grid_widget)

            count_label = QLabel(_("LBL_AI_FAMILY_LIVE_COUNT", live=live_count, total=len(items)))
            count_label.setStyleSheet("color: #556070; font-size: 9px;")
            self._content_layout.insertWidget(self._content_layout.count() - 1, count_label)

        if warnings:
            self._warning_label.setText("\n".join(warnings))
            self._warning_label.setVisible(True)
        else:
            self._warning_label.setVisible(False)

    def _build_card(self, project: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #12161c; border: 1px solid #262b33; border-radius: 8px; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)

        text_col = QVBoxLayout()
        name_label = QLabel(str(project.get("name") or "-"))
        name_label.setStyleSheet("color: #e6e6e6; font-size: 11px; font-weight: 700;")
        text_col.addWidget(name_label)
        meta_label = QLabel(f"{project.get('role') or '-'} · v{project.get('version') or '-'}")
        meta_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
        text_col.addWidget(meta_label)
        layout.addLayout(text_col, 1)

        live = project.get("live")
        status_label = QLabel(_("STATUS_ES_LIVE") if live is True else _("STATUS_ES_DEAD") if live is False else _("STATUS_ES_NA"))
        color = "#4caf50" if live is True else "#e05050" if live is False else "#556070"
        status_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(status_label)
        return card
