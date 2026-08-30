# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ecosystem_telemetry_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own EcosystemTelemetry.tsx -
# same two real modes HYDRA-UMC-DATALAKE's own API actually exposes (raw
# points via GET /api/telemetry/query, bucketed via /aggregate), through
# the active connection's own Server. Nothing invented on top of what the
# server proxy/Datalake itself supports.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

_AGGREGATES = ["avg", "min", "max", "sum"]


class EcosystemTelemetryPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_ECOSYSTEM_TELEMETRY"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        form = QGridLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem(_("TELEMETRY_MODE_QUERY"), "query")
        self._mode_combo.addItem(_("TELEMETRY_MODE_AGGREGATE"), "aggregate")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addWidget(QLabel(_("LBL_TELEMETRY_MODE")), 0, 0)
        form.addWidget(self._mode_combo, 0, 1)

        self._source_id = QLineEdit()
        self._kind = QLineEdit()
        self._field = QLineEdit()
        self._start = QLineEdit()
        self._end = QLineEdit()
        self._bucket_ms = QLineEdit("60000")
        self._agg_combo = QComboBox()
        self._agg_combo.addItems(_AGGREGATES)

        form.addWidget(QLabel(_("LBL_TELEMETRY_SOURCE_ID")), 1, 0)
        form.addWidget(self._source_id, 1, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_KIND")), 2, 0)
        form.addWidget(self._kind, 2, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_FIELD")), 3, 0)
        form.addWidget(self._field, 3, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_START")), 4, 0)
        form.addWidget(self._start, 4, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_END")), 5, 0)
        form.addWidget(self._end, 5, 1)
        self._bucket_label = QLabel(_("LBL_TELEMETRY_BUCKET_MS"))
        form.addWidget(self._bucket_label, 6, 0)
        form.addWidget(self._bucket_ms, 6, 1)
        self._agg_label = QLabel(_("LBL_TELEMETRY_AGG"))
        form.addWidget(self._agg_label, 7, 0)
        form.addWidget(self._agg_combo, 7, 1)
        layout.addLayout(form)

        run_row = QHBoxLayout()
        self._run_btn = QPushButton(_("BTN_RUN_QUERY"))
        self._run_btn.clicked.connect(lambda: asyncio.ensure_future(self._run()))
        run_row.addWidget(self._run_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, 5)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        is_aggregate = self._mode_combo.currentData() == "aggregate"
        self._bucket_label.setVisible(is_aggregate)
        self._bucket_ms.setVisible(is_aggregate)
        self._agg_label.setVisible(is_aggregate)
        self._agg_combo.setVisible(is_aggregate)

    async def _run(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            return
        is_aggregate = self._mode_combo.currentData() == "aggregate"
        params: dict = {}
        if self._source_id.text():
            params["sourceId"] = self._source_id.text()
        if self._kind.text():
            params["kind"] = self._kind.text()
        if self._field.text():
            params["field"] = self._field.text()
        if self._start.text():
            params["start"] = self._start.text()
        if self._end.text():
            params["end"] = self._end.text()

        self._run_btn.setEnabled(False)
        try:
            if is_aggregate:
                if not (self._kind.text() and self._field.text() and self._start.text() and self._end.text()):
                    self._status_label.setText(_("MSG_TELEMETRY_AGGREGATE_MISSING_FIELDS"))
                    return
                params["bucketMs"] = self._bucket_ms.text()
                params["agg"] = self._agg_combo.currentText()
                result = await conn.fetch_telemetry_aggregate(params)
            else:
                result = await conn.fetch_telemetry_query(params)
        finally:
            self._run_btn.setEnabled(True)

        if result is None:
            self._status_label.setText(_("MSG_TELEMETRY_LOAD_ERROR"))
            return
        status, body = result
        if status == 503 and isinstance(body, dict) and body.get("available") is False:
            self._status_label.setText(_("MSG_TELEMETRY_NOT_CONFIGURED"))
            self._table.setRowCount(0)
            return
        if status != 200 or not isinstance(body, list):
            self._status_label.setText(_("MSG_TELEMETRY_LOAD_ERROR"))
            return

        self._status_label.setText("")
        if is_aggregate:
            self._table.setColumnCount(3)
            self._table.setHorizontalHeaderLabels([_("COL_TELEMETRY_BUCKET_START"), _("COL_TELEMETRY_VALUE"), _("COL_TELEMETRY_COUNT")])
            self._table.setRowCount(len(body))
            for row, b in enumerate(body):
                self._table.setItem(row, 0, QTableWidgetItem(str(b.get("bucketStart"))))
                self._table.setItem(row, 1, QTableWidgetItem(str(b.get("value"))))
                self._table.setItem(row, 2, QTableWidgetItem(str(b.get("count"))))
        else:
            self._table.setColumnCount(5)
            self._table.setHorizontalHeaderLabels(
                [_("LBL_TELEMETRY_SOURCE_ID"), _("LBL_TELEMETRY_KIND"), _("LBL_TELEMETRY_FIELD"), _("COL_TELEMETRY_TIMESTAMP"), _("COL_TELEMETRY_VALUE")]
            )
            self._table.setRowCount(len(body))
            for row, p in enumerate(body):
                self._table.setItem(row, 0, QTableWidgetItem(str(p.get("sourceId"))))
                self._table.setItem(row, 1, QTableWidgetItem(str(p.get("kind"))))
                self._table.setItem(row, 2, QTableWidgetItem(str(p.get("field"))))
                self._table.setItem(row, 3, QTableWidgetItem(str(p.get("timestamp"))))
                self._table.setItem(row, 4, QTableWidgetItem(str(p.get("value"))))
        if len(body) == 0:
            self._status_label.setText(_("MSG_TELEMETRY_NO_DATA"))
