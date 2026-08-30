# =============================================================================
# HYDRA-UMC SUITE - ui/panels/ecosystem_telemetry_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own EcosystemTelemetry.tsx -
# same two real modes HYDRA-UMC-DATALAKE's own API actually exposes (raw
# points via GET /api/telemetry/query, bucketed via /aggregate), through
# the active connection's own Server. Real charts via PySide6.QtCharts
# (already part of the PySide6 dependency this app already ships, unused
# anywhere in this app until now) - a line chart for raw points, a bar
# chart for aggregated buckets - plus quick time-range presets and a
# min/max/avg/count stat row, matching STUDIO's own 0.2.9 redesign.
# =============================================================================
from __future__ import annotations

import asyncio
import time

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QDateTimeAxis, QValueAxis, QBarCategoryAxis,
)
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

_AGGREGATES = ["avg", "min", "max", "sum"]
_SKY = QColor("#38bdf8")
_RANGE_PRESETS = [("5m", 5 * 60 * 1000), ("1h", 60 * 60 * 1000), ("6h", 6 * 60 * 60 * 1000), ("24h", 24 * 60 * 60 * 1000)]


def _stat_box(label_text: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(10, 6, 10, 6)
    box.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
    caption = QLabel(label_text)
    caption.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
    layout.addWidget(caption)
    value = QLabel("-")
    value.setStyleSheet("color: #e6e6e6; font-size: 16px; font-weight: 800; font-family: Consolas, monospace;")
    layout.addWidget(value)
    return box, value


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
        self._bucket_ms = QLineEdit("60000")
        self._agg_combo = QComboBox()
        self._agg_combo.addItems(_AGGREGATES)

        form.addWidget(QLabel(_("LBL_TELEMETRY_SOURCE_ID")), 1, 0)
        form.addWidget(self._source_id, 1, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_KIND")), 2, 0)
        form.addWidget(self._kind, 2, 1)
        form.addWidget(QLabel(_("LBL_TELEMETRY_FIELD")), 3, 0)
        form.addWidget(self._field, 3, 1)
        self._bucket_label = QLabel(_("LBL_TELEMETRY_BUCKET_MS"))
        form.addWidget(self._bucket_label, 6, 0)
        form.addWidget(self._bucket_ms, 6, 1)
        self._agg_label = QLabel(_("LBL_TELEMETRY_AGG"))
        form.addWidget(self._agg_label, 7, 0)
        form.addWidget(self._agg_combo, 7, 1)
        layout.addLayout(form)

        # Quick time-range presets - real, common case ("how has this
        # looked recently") without hand-typing epoch ms every time.
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel(_("LBL_TELEMETRY_RANGE")))
        self._start = QLineEdit()
        self._end = QLineEdit()
        self._start.setPlaceholderText(_("LBL_TELEMETRY_START"))
        self._end.setPlaceholderText(_("LBL_TELEMETRY_END"))
        for label, ms in _RANGE_PRESETS:
            btn = QPushButton(label)
            btn.setFixedWidth(48)
            btn.clicked.connect(lambda _checked=False, m=ms: self._apply_preset(m))
            range_row.addWidget(btn)
        range_row.addWidget(self._start)
        range_row.addWidget(self._end)
        layout.addLayout(range_row)

        run_row = QHBoxLayout()
        self._run_btn = QPushButton(_("BTN_RUN_QUERY"))
        self._run_btn.clicked.connect(lambda: asyncio.ensure_future(self._run()))
        run_row.addWidget(self._run_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._status_label)

        # Real stat row - min/max/avg/count computed from the actual
        # fetched series, same as STUDIO's own redesign.
        stats_row = QHBoxLayout()
        self._stat_min_box, self._stat_min = _stat_box(_("LBL_TELEMETRY_STAT_MIN"))
        self._stat_max_box, self._stat_max = _stat_box(_("LBL_TELEMETRY_STAT_MAX"))
        self._stat_avg_box, self._stat_avg = _stat_box(_("LBL_TELEMETRY_STAT_AVG"))
        self._stat_count_box, self._stat_count = _stat_box(_("LBL_TELEMETRY_STAT_COUNT"))
        for box in (self._stat_min_box, self._stat_max_box, self._stat_avg_box, self._stat_count_box):
            stats_row.addWidget(box)
            box.setVisible(False)
        layout.addLayout(stats_row)

        self._chart = QChart()
        self._chart.setBackgroundBrush(QColor("#0d1117"))
        self._chart.setBackgroundRoundness(0)
        self._chart.legend().setVisible(False)
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(280)
        layout.addWidget(self._chart_view, 1)

        self._on_mode_changed()

    def _apply_preset(self, ms: int) -> None:
        now = int(time.time() * 1000)
        self._start.setText(str(now - ms))
        self._end.setText(str(now))

    def _on_mode_changed(self) -> None:
        is_aggregate = self._mode_combo.currentData() == "aggregate"
        self._bucket_label.setVisible(is_aggregate)
        self._bucket_ms.setVisible(is_aggregate)
        self._agg_label.setVisible(is_aggregate)
        self._agg_combo.setVisible(is_aggregate)

    def _render_empty_chart(self) -> None:
        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

    def _render_line_chart(self, points: list[dict]) -> None:
        self._render_empty_chart()
        series = QLineSeries()
        series.setPen(QPen(_SKY, 2))
        for p in points:
            series.append(float(p.get("timestamp", 0)), float(p.get("value", 0)))
        self._chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("HH:mm:ss")
        axis_x.setLabelsColor(QColor("#64748b"))
        axis_x.setGridLineColor(QColor("#1e293b"))
        if points:
            axis_x.setMin(QDateTime.fromMSecsSinceEpoch(int(points[0]["timestamp"])))
            axis_x.setMax(QDateTime.fromMSecsSinceEpoch(int(points[-1]["timestamp"])))
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#64748b"))
        axis_y.setGridLineColor(QColor("#1e293b"))
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

    def _render_bar_chart(self, buckets: list[dict]) -> None:
        self._render_empty_chart()
        bar_set = QBarSet("")
        bar_set.setColor(_SKY)
        categories = []
        for b in buckets:
            bar_set.append(float(b.get("value", 0)))
            categories.append(QDateTime.fromMSecsSinceEpoch(int(b.get("bucketStart", 0))).toString("HH:mm"))
        series = QBarSeries()
        series.append(bar_set)
        self._chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("#64748b"))
        axis_x.setGridLineColor(QColor("#1e293b"))
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#64748b"))
        axis_y.setGridLineColor(QColor("#1e293b"))
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

    def _update_stats(self, values: list[float]) -> None:
        boxes = (self._stat_min_box, self._stat_max_box, self._stat_avg_box, self._stat_count_box)
        if not values:
            for box in boxes:
                box.setVisible(False)
            return
        for box in boxes:
            box.setVisible(True)
        self._stat_min.setText(f"{min(values):.2f}")
        self._stat_max.setText(f"{max(values):.2f}")
        self._stat_avg.setText(f"{sum(values) / len(values):.2f}")
        self._stat_count.setText(str(len(values)))

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
            self._render_empty_chart()
            self._update_stats([])
            return
        if status != 200 or not isinstance(body, list):
            self._status_label.setText(_("MSG_TELEMETRY_LOAD_ERROR"))
            return

        self._status_label.setText("" if body else _("MSG_TELEMETRY_NO_DATA"))
        if is_aggregate:
            self._render_bar_chart(body)
            self._update_stats([float(b.get("value", 0)) for b in body])
        else:
            self._render_line_chart(body)
            self._update_stats([float(p.get("value", 0)) for p in body])
