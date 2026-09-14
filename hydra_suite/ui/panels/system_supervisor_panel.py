# =============================================================================
# HYDRA-UMC SUITE - ui/panels/system_supervisor_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own SystemSupervisor.tsx - same
# GET /api/system/supervisor (server.ts's own getSupervisorSnapshot(), no
# auth required server-side - same trust tier as /api/system/metrics, see
# that route's own registration comment) polled every 2s. The server keeps
# no history of its own (a background 1s sampler always has the LATEST
# cpu/mem/etc. ready, but nothing older - see getSupervisorSnapshot()'s own
# header comment); this panel keeps its own rolling client-side window of
# the last HISTORY_LEN samples so the charts below have something to draw a
# line through, same tradeoff STUDIO's own component makes. Every number
# here is real - a field this host genuinely cannot supply (a non-Linux
# box, a CM5 kernel without cpufreq exposed, `ps`/`df` missing) renders as
# an honest "-"/empty state, never a placeholder number.
#
# No `conn.is_admin` gate here (unlike AdminClientsPanel/AdminLogsPanel/
# AdminServerPanel right next to it in the nav) - the real route this
# panel calls needs no auth at all server-side, so gating it here would be
# inventing a permission requirement that doesn't actually exist, same
# reasoning nav_sidebar.py's own header comment already gives for why this
# app's ecosystem-wide panels stay ungated. Placed in the same
# "HYDRA-UMC Ecosystem" nav section STUDIO buries it in (under its own
# admin menu) purely for discoverability parity, not because it needs it.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import QDateTime, QMargins, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _

# 2 minutes of history at 2s polling - same window STUDIO's own
# SystemSupervisor.tsx keeps (long enough for the shape of a real
# spike/settle to read clearly without the chart becoming unreadably dense).
HISTORY_LEN = 60
POLL_MS = 2000

_CYAN = QColor("#22d3ee")
_AMBER = QColor("#fbbf24")
_ROSE = QColor("#fb7185")
_PINK = QColor("#f472b6")
_SKY = QColor("#38bdf8")
_GRAY = QColor("#94a3b8")
_GRID = QColor("#1e293b")
_AXIS = QColor("#64748b")


def _format_bytes(n: float | None) -> str:
    if n is None:
        return "-"
    if n < 1024:
        return f"{n:.0f} B"
    units = ["KB", "MB", "GB", "TB"]
    value = n / 1024
    i = 0
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.0f} {units[i]}" if value >= 100 else f"{value:.1f} {units[i]}"


def _format_bytes_per_sec(n: float | None) -> str:
    if n is None:
        return "-"
    return f"{_format_bytes(n)}/s"


def _format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def network_rate(prev: dict | None, cur: dict | None, dt_sec: float, key: str) -> float | None:
    """The real live throughput between two polls: the delta in one
    cumulative sysfs byte counter (rx/txBytes - see HYDRA-UMC-SERVER's own
    readNetworkTraffic()) divided by the elapsed time - matches STUDIO's
    own SystemSupervisor.tsx netThroughputData computation exactly,
    including its guard against a negative delta (the interface's own
    counter reset/wrapped between the two samples - e.g. a real
    ifdown/ifup, or this host's network stack restarting) - reported as
    None (skipped, never a false negative rate) rather than clamped to 0,
    so a caller can tell "genuinely zero traffic" apart from "this sample
    pair can't answer that"."""
    if prev is None or cur is None or dt_sec <= 0:
        return None
    delta = cur.get(key, 0) - prev.get(key, 0)
    if delta < 0:
        return None
    return delta / dt_sec


def _stat_tile(label_text: str) -> tuple[QWidget, QLabel, QLabel]:
    box = QWidget()
    box.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(2)
    caption = QLabel(label_text)
    caption.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
    layout.addWidget(caption)
    value = QLabel("-")
    value.setStyleSheet("color: #e6e6e6; font-size: 18px; font-weight: 800; font-family: Consolas, monospace;")
    layout.addWidget(value)
    sub = QLabel("")
    sub.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
    layout.addWidget(sub)
    return box, value, sub


def _net_badge(label_text: str) -> QLabel:
    badge = QLabel(label_text)
    badge.setStyleSheet("color: #3a4250; font-size: 9px; font-weight: 800; text-transform: uppercase;")
    return badge


def _make_chart() -> tuple[QChart, QChartView]:
    chart = QChart()
    chart.setBackgroundBrush(QColor("#0d1117"))
    chart.setBackgroundRoundness(0)
    chart.legend().setVisible(False)
    chart.setMargins(QMargins(4, 4, 4, 4))
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(150)
    return chart, view


def _chart_card(title_text: str, view: QChartView) -> QWidget:
    box = QWidget()
    box.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(10, 8, 10, 8)
    title = QLabel(title_text)
    title.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
    layout.addWidget(title)
    layout.addWidget(view)
    return box


class SystemSupervisorPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._history: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header = QHBoxLayout()
        heading = QLabel(_("HEADING_SYSTEM_SUPERVISOR"))
        heading.setObjectName("panelHeading")
        header.addWidget(heading)
        header.addStretch(1)
        self._live_label = QLabel("")
        self._live_label.setStyleSheet("color: #7f8ea1; font-size: 10px;")
        header.addWidget(self._live_label)
        self._uptime_label = QLabel("")
        self._uptime_label.setStyleSheet("color: #7f8ea1; font-size: 10px;")
        header.addWidget(self._uptime_label)
        self._wifi_badge = _net_badge(_("LBL_SUPERVISOR_WIFI"))
        self._bt_badge = _net_badge(_("LBL_SUPERVISOR_BLUETOOTH"))
        self._eth_badge = _net_badge(_("LBL_SUPERVISOR_ETHERNET"))
        for badge in (self._wifi_badge, self._bt_badge, self._eth_badge):
            header.addWidget(badge)
        outer.addLayout(header)

        self._status_label = QLabel(_("LBL_ES_NO_ACTIVE_SERVER"))
        self._status_label.setStyleSheet("color: #7f8ea1;")
        outer.addWidget(self._status_label)

        # Scrolling body - same reasoning as HYDRA-UMC-STUDIO's own
        # SystemSupervisor.tsx (its own header comment: this panel's real
        # content is taller than most docked panels ever get, and this
        # window's other docks already clip anything that doesn't scroll
        # its own body). Only this region scrolls - the header above and
        # the connection status line stay put.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        stats_row = QHBoxLayout()
        self._cpu_box, self._cpu_value, self._cpu_sub = _stat_tile(_("LBL_SUPERVISOR_CPU"))
        self._mem_box, self._mem_value, self._mem_sub = _stat_tile(_("LBL_SUPERVISOR_MEMORY"))
        self._disk_box, self._disk_value, self._disk_sub = _stat_tile(_("LBL_SUPERVISOR_DISK"))
        self._cpu_temp_box, self._cpu_temp_value, _cpu_temp_sub = _stat_tile(_("LBL_SUPERVISOR_CPU_TEMP"))
        self._rp1_temp_box, self._rp1_temp_value, _rp1_temp_sub = _stat_tile(_("LBL_SUPERVISOR_RP1_TEMP"))
        self._load_box, self._load_value, self._load_sub = _stat_tile(_("LBL_SUPERVISOR_LOAD_AVG"))
        for box in (self._cpu_box, self._mem_box, self._disk_box, self._cpu_temp_box, self._rp1_temp_box, self._load_box):
            stats_row.addWidget(box)
        body_layout.addLayout(stats_row)

        charts_row1 = QHBoxLayout()
        self._cpu_chart, self._cpu_chart_view = _make_chart()
        charts_row1.addWidget(_chart_card(_("LBL_SUPERVISOR_CPU_TREND"), self._cpu_chart_view), 1)

        self._cores_box = QWidget()
        self._cores_layout = QVBoxLayout(self._cores_box)
        self._cores_layout.setContentsMargins(0, 0, 0, 0)
        self._cores_layout.setSpacing(3)
        self._core_rows: list[tuple[QLabel, QProgressBar, QLabel]] = []
        cores_card = QWidget()
        cores_card.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
        cores_card_layout = QVBoxLayout(cores_card)
        cores_card_layout.setContentsMargins(10, 8, 10, 8)
        cores_title = QLabel(_("LBL_SUPERVISOR_CPU_CORES"))
        cores_title.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
        cores_card_layout.addWidget(cores_title)
        cores_card_layout.addWidget(self._cores_box)
        charts_row1.addWidget(cores_card, 1)
        body_layout.addLayout(charts_row1)

        charts_row2 = QHBoxLayout()
        self._mem_chart, self._mem_chart_view = _make_chart()
        charts_row2.addWidget(_chart_card(_("LBL_SUPERVISOR_MEMORY_TREND"), self._mem_chart_view), 1)
        self._temp_chart, self._temp_chart_view = _make_chart()
        charts_row2.addWidget(_chart_card(_("LBL_SUPERVISOR_TEMP_TREND"), self._temp_chart_view), 1)
        body_layout.addLayout(charts_row2)

        self._net_section = QWidget()
        net_section_layout = QVBoxLayout(self._net_section)
        net_section_layout.setContentsMargins(0, 0, 0, 0)
        net_section_layout.setSpacing(8)
        net_stats_row = QHBoxLayout()
        self._wifi_total_box, self._wifi_total_value, self._wifi_total_sub = _stat_tile(_("LBL_SUPERVISOR_WIFI_TOTAL"))
        self._eth_total_box, self._eth_total_value, self._eth_total_sub = _stat_tile(_("LBL_SUPERVISOR_ETHERNET_TOTAL"))
        net_stats_row.addWidget(self._wifi_total_box)
        net_stats_row.addWidget(self._eth_total_box)
        net_section_layout.addLayout(net_stats_row)
        self._net_chart, self._net_chart_view = _make_chart()
        net_section_layout.addWidget(_chart_card(_("LBL_SUPERVISOR_NETWORK_THROUGHPUT"), self._net_chart_view))
        self._net_section.setVisible(False)
        body_layout.addWidget(self._net_section)

        self._process_table = QTableWidget(0, 5)
        self._process_table.setHorizontalHeaderLabels((
            _("COL_SUPERVISOR_PID"), _("COL_SUPERVISOR_PROCESS"),
            _("COL_SUPERVISOR_CPU_PERCENT"), _("COL_SUPERVISOR_MEM_PERCENT"), _("COL_SUPERVISOR_RSS"),
        ))
        self._process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._process_table.verticalHeader().setVisible(False)
        self._process_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._process_table.setMinimumHeight(280)
        body_layout.addWidget(self._wrap_table())
        body_layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh()))
        self._timer.start()

        controller.active_connection_changed.connect(self._on_connection_changed)
        self._on_connection_changed(None)

    # The process table needs its own titled card, but _chart_card() above
    # is built around a QChartView specifically - this wraps the table in
    # the exact same visual card shell without forcing a chart-shaped
    # signature onto a widget that isn't one.
    def _wrap_table(self) -> QWidget:
        box = QWidget()
        box.setStyleSheet("background: #12161c; border: 1px solid #262b33; border-radius: 8px;")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel(_("LBL_SUPERVISOR_PROCESSES"))
        title.setStyleSheet("color: #7f8ea1; font-size: 9px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(title)
        layout.addWidget(self._process_table)
        return box

    def _on_connection_changed(self, _connection_id) -> None:
        self._history = []
        asyncio.ensure_future(self._refresh())

    async def _refresh(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._status_label.setText(_("LBL_ES_NO_ACTIVE_SERVER"))
            self._history = []
            return
        result = await conn.fetch_system_supervisor()
        if result is None:
            self._status_label.setText(_("MSG_SUPERVISOR_UNREACHABLE"))
            self._live_label.setText(_("LBL_SUPERVISOR_STALE"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._status_label.setText(_("MSG_SUPERVISOR_UNREACHABLE"))
            self._live_label.setText(_("LBL_SUPERVISOR_STALE"))
            return
        self._status_label.setText("")
        self._live_label.setText(_("LBL_SUPERVISOR_LIVE"))
        self._history = [*self._history[-(HISTORY_LEN - 1):], body]
        self._render(body)

    def _render(self, snapshot: dict) -> None:
        cpu = snapshot.get("cpu") or {}
        memory = snapshot.get("memory")
        disk = snapshot.get("disk")
        temps = snapshot.get("temps") or {}
        processes = snapshot.get("processes") or []
        network = snapshot.get("network") or {}
        traffic = network.get("traffic") or {}

        self._uptime_label.setText(f"{_('LBL_SUPERVISOR_UPTIME')}: {_format_uptime(snapshot.get('uptimeSeconds', 0))}")

        def _net_state(badge: QLabel, state: object, label_text: str) -> None:
            colour = "#43db9b" if state is True else ("#e05050" if state is False else "#3a4250")
            badge.setText(label_text)
            badge.setStyleSheet(f"color: {colour}; font-size: 9px; font-weight: 800; text-transform: uppercase;")

        _net_state(self._wifi_badge, network.get("wifi"), _("LBL_SUPERVISOR_WIFI"))
        _net_state(self._bt_badge, network.get("bluetooth"), _("LBL_SUPERVISOR_BLUETOOTH"))
        _net_state(self._eth_badge, network.get("ethernet"), _("LBL_SUPERVISOR_ETHERNET"))

        overall = cpu.get("overallPercent")
        self._cpu_value.setText(f"{overall:.0f}%" if isinstance(overall, (int, float)) else "-")
        core_count = cpu.get("coreCount")
        self._cpu_sub.setText(f"{core_count} {_('LBL_SUPERVISOR_CORES')}" if core_count else "")

        mem_percent = (memory["usedBytes"] / memory["totalBytes"] * 100) if memory and memory.get("totalBytes") else None
        self._mem_value.setText(f"{mem_percent:.0f}%" if mem_percent is not None else "N/A")
        self._mem_sub.setText(f"{_format_bytes(memory['usedBytes'])} / {_format_bytes(memory['totalBytes'])}" if memory else "")

        disk_percent = (disk["usedBytes"] / disk["totalBytes"] * 100) if disk and disk.get("totalBytes") else None
        self._disk_value.setText(f"{disk_percent:.0f}%" if disk_percent is not None else "N/A")
        self._disk_sub.setText(f"{_format_bytes(disk['usedBytes'])} / {_format_bytes(disk['totalBytes'])}" if disk else "")

        cpu_temp = temps.get("cpu")
        self._cpu_temp_value.setText(f"{cpu_temp:.0f}°C" if isinstance(cpu_temp, (int, float)) else "N/A")
        rp1_temp = temps.get("rp1")
        self._rp1_temp_value.setText(f"{rp1_temp:.0f}°C" if isinstance(rp1_temp, (int, float)) else "N/A")

        load_avg = cpu.get("loadAvg") or []
        self._load_value.setText(f"{load_avg[0]:.2f}" if load_avg else "-")
        self._load_sub.setText(f"{load_avg[1]:.2f} / {load_avg[2]:.2f}" if len(load_avg) >= 3 else "")

        self._render_cpu_chart()
        self._render_cores(cpu)
        self._render_memory_chart()
        self._render_temp_chart()
        self._render_network(traffic)
        self._render_processes(processes)

    # --- charts -----------------------------------------------------------

    def _clear_chart(self, chart: QChart) -> None:
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)

    def _add_time_axis(self, chart: QChart, series_list: list[QLineSeries], points_x: list[int]) -> None:
        axis_x = QDateTimeAxis()
        axis_x.setFormat("HH:mm:ss")
        axis_x.setLabelsColor(_AXIS)
        axis_x.setGridLineColor(_GRID)
        if points_x:
            axis_x.setMin(QDateTime.fromMSecsSinceEpoch(points_x[0]))
            axis_x.setMax(QDateTime.fromMSecsSinceEpoch(points_x[-1]))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        for series in series_list:
            series.attachAxis(axis_x)

    def _add_value_axis(self, chart: QChart, series_list: list[QLineSeries], value_range: tuple[float, float] | None = None) -> None:
        axis_y = QValueAxis()
        axis_y.setLabelsColor(_AXIS)
        axis_y.setGridLineColor(_GRID)
        if value_range is not None:
            axis_y.setRange(*value_range)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in series_list:
            series.attachAxis(axis_y)

    def _render_cpu_chart(self) -> None:
        self._clear_chart(self._cpu_chart)
        series = QLineSeries()
        series.setPen(QPen(_CYAN, 2))
        points_x: list[int] = []
        for s in self._history:
            ts = int(s.get("timestamp", 0))
            points_x.append(ts)
            series.append(ts, float(((s.get("cpu") or {}).get("overallPercent")) or 0))
        self._cpu_chart.addSeries(series)
        self._add_time_axis(self._cpu_chart, [series], points_x)
        self._add_value_axis(self._cpu_chart, [series], (0, 100))

    def _render_cores(self, cpu: dict) -> None:
        per_core = cpu.get("perCorePercent") or []
        per_freq = cpu.get("perCoreFrequencyMHz") or []
        if len(self._core_rows) != len(per_core):
            while self._cores_layout.count():
                item = self._cores_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._core_rows = []
            for i in range(len(per_core)):
                row = QHBoxLayout()
                label = QLabel(f"C{i}")
                label.setStyleSheet("color: #7f8ea1; font-size: 9px;")
                label.setFixedWidth(24)
                row.addWidget(label)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setTextVisible(False)
                bar.setFixedHeight(10)
                row.addWidget(bar, 1)
                freq_label = QLabel("")
                freq_label.setStyleSheet("color: #556070; font-size: 9px; font-family: Consolas, monospace;")
                freq_label.setFixedWidth(60)
                freq_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                row.addWidget(freq_label)
                wrapper = QWidget()
                wrapper.setLayout(row)
                self._cores_layout.addWidget(wrapper)
                self._core_rows.append((label, bar, freq_label))

        for i, pct in enumerate(per_core):
            _label, bar, freq_label = self._core_rows[i]
            bar.setValue(max(0, min(100, round(pct))))
            colour = "#fb7185" if pct > 80 else ("#fbbf24" if pct > 50 else "#22d3ee")
            bar.setStyleSheet(f"QProgressBar {{ background: #1a1f27; border: none; border-radius: 5px; }} "
                               f"QProgressBar::chunk {{ background: {colour}; border-radius: 5px; }}")
            freq = per_freq[i] if i < len(per_freq) else None
            freq_label.setText(f"{freq} MHz" if freq is not None else "")

    def _render_memory_chart(self) -> None:
        self._clear_chart(self._mem_chart)
        has_memory = any(s.get("memory") for s in self._history)
        if not has_memory:
            return
        used_series = QLineSeries()
        used_series.setPen(QPen(_AMBER, 2))
        cached_series = QLineSeries()
        pen = QPen(_GRAY, 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        cached_series.setPen(pen)
        points_x: list[int] = []
        for s in self._history:
            memory = s.get("memory")
            if not memory or not memory.get("totalBytes"):
                continue
            ts = int(s.get("timestamp", 0))
            points_x.append(ts)
            used_series.append(ts, memory["usedBytes"] / memory["totalBytes"] * 100)
            cached_series.append(ts, (memory["cachedBytes"] + memory["buffersBytes"]) / memory["totalBytes"] * 100)
        self._mem_chart.addSeries(used_series)
        self._mem_chart.addSeries(cached_series)
        self._add_time_axis(self._mem_chart, [used_series, cached_series], points_x)
        self._add_value_axis(self._mem_chart, [used_series, cached_series], (0, 100))

    def _render_temp_chart(self) -> None:
        self._clear_chart(self._temp_chart)
        cpu_series = QLineSeries()
        cpu_series.setPen(QPen(_ROSE, 2))
        rp1_series = QLineSeries()
        rp1_series.setPen(QPen(_PINK, 2))
        points_x: list[int] = []
        any_point = False
        for s in self._history:
            temps = s.get("temps") or {}
            ts = int(s.get("timestamp", 0))
            points_x.append(ts)
            cpu_temp, rp1_temp = temps.get("cpu"), temps.get("rp1")
            if isinstance(cpu_temp, (int, float)):
                cpu_series.append(ts, cpu_temp)
                any_point = True
            if isinstance(rp1_temp, (int, float)):
                rp1_series.append(ts, rp1_temp)
                any_point = True
        if not any_point:
            return
        self._temp_chart.addSeries(cpu_series)
        self._temp_chart.addSeries(rp1_series)
        self._add_time_axis(self._temp_chart, [cpu_series, rp1_series], points_x)
        self._add_value_axis(self._temp_chart, [cpu_series, rp1_series])

    def _render_network(self, traffic: dict) -> None:
        has_traffic = bool(traffic.get("wifi") or traffic.get("ethernet"))
        self._net_section.setVisible(has_traffic)
        if not has_traffic:
            return

        # `traffic` is already this render pass's own latest snapshot (see
        # _render()'s own call site) - no need to re-derive it from
        # self._history, which _refresh() has already appended it into.
        wifi_total = traffic.get("wifi")
        self._wifi_total_box.setVisible(wifi_total is not None)
        if wifi_total is not None:
            self._wifi_total_value.setText(_format_bytes(wifi_total["rxBytes"] + wifi_total["txBytes"]))
            self._wifi_total_sub.setText(f"↓ {_format_bytes(wifi_total['rxBytes'])} · ↑ {_format_bytes(wifi_total['txBytes'])}")
        eth_total = traffic.get("ethernet")
        self._eth_total_box.setVisible(eth_total is not None)
        if eth_total is not None:
            self._eth_total_value.setText(_format_bytes(eth_total["rxBytes"] + eth_total["txBytes"]))
            self._eth_total_sub.setText(f"↓ {_format_bytes(eth_total['rxBytes'])} · ↑ {_format_bytes(eth_total['txBytes'])}")

        self._clear_chart(self._net_chart)
        wifi_rx, wifi_tx, eth_rx, eth_tx = QLineSeries(), QLineSeries(), QLineSeries(), QLineSeries()
        wifi_rx.setPen(QPen(_SKY, 2))
        dashed_sky = QPen(_SKY, 1); dashed_sky.setStyle(Qt.PenStyle.DashLine)
        wifi_tx.setPen(dashed_sky)
        eth_rx.setPen(QPen(_AMBER, 2))
        dashed_amber = QPen(_AMBER, 1); dashed_amber.setStyle(Qt.PenStyle.DashLine)
        eth_tx.setPen(dashed_amber)

        points_x: list[int] = []
        for i in range(1, len(self._history)):
            prev_snapshot, cur_snapshot = self._history[i - 1], self._history[i]
            dt_sec = (cur_snapshot.get("timestamp", 0) - prev_snapshot.get("timestamp", 0)) / 1000
            prev_traffic = ((prev_snapshot.get("network") or {}).get("traffic")) or {}
            cur_traffic = ((cur_snapshot.get("network") or {}).get("traffic")) or {}
            ts = int(cur_snapshot.get("timestamp", 0))
            points_x.append(ts)
            rate = network_rate(prev_traffic.get("wifi"), cur_traffic.get("wifi"), dt_sec, "rxBytes")
            if rate is not None:
                wifi_rx.append(ts, rate)
            rate = network_rate(prev_traffic.get("wifi"), cur_traffic.get("wifi"), dt_sec, "txBytes")
            if rate is not None:
                wifi_tx.append(ts, rate)
            rate = network_rate(prev_traffic.get("ethernet"), cur_traffic.get("ethernet"), dt_sec, "rxBytes")
            if rate is not None:
                eth_rx.append(ts, rate)
            rate = network_rate(prev_traffic.get("ethernet"), cur_traffic.get("ethernet"), dt_sec, "txBytes")
            if rate is not None:
                eth_tx.append(ts, rate)

        series_list = []
        if wifi_total is not None:
            series_list += [wifi_rx, wifi_tx]
        if eth_total is not None:
            series_list += [eth_rx, eth_tx]
        for series in series_list:
            self._net_chart.addSeries(series)
        if series_list:
            self._add_time_axis(self._net_chart, series_list, points_x)
            self._add_value_axis(self._net_chart, series_list)

    def _render_processes(self, processes: list[dict]) -> None:
        if self._process_table.rowCount() != len(processes):
            self._process_table.setRowCount(len(processes))
        for row, proc in enumerate(processes):
            self._set_cell(row, 0, str(proc.get("pid", "-")))
            self._set_cell(row, 1, str(proc.get("name", "?")))
            self._set_cell(row, 2, f"{proc.get('cpuPercent', 0):.1f}")
            self._set_cell(row, 3, f"{proc.get('memPercent', 0):.1f}")
            self._set_cell(row, 4, _format_bytes(proc.get("rssBytes")))

    def _set_cell(self, row: int, col: int, text: str) -> None:
        # Same reuse-the-existing-item idiom as overview.py's own
        # _set_cell() - avoids rebuilding all N*5 cells on every 2s poll.
        item = self._process_table.item(row, col)
        if item is None:
            self._process_table.setItem(row, col, QTableWidgetItem(text))
        elif item.text() != text:
            item.setText(text)
