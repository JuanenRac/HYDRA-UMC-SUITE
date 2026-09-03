# =============================================================================
# HYDRA-UMC SUITE - ui/panels/tester_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own Tester.tsx (448 lines) - the 11th
# and LAST panel from [[project_suite_studio_parity_gap]]. CAN-OTA runtime
# diagnostics for a Robot Controller Board or (relayed through it) a
# robot's own URTC Tool Head - porting URTC-TESTER's own feature set
# (global LED/OLED controls, F-RAM query/erase, per-tool telemetry, safe
# self-test, raw CAN bus monitor) onto the same multi-hop chain
# flasher_panel.py uses. Target-selection block below deliberately
# duplicates flasher_panel.py's own (Board/Robot Slot/hop description/
# version query) rather than sharing a base class - STUDIO's own
# Tester.tsx does the exact same literal duplication against Flasher.tsx
# (both files import the SAME canOta.ts helpers but never share a target-
# selection component), so mirroring that duplication here is the more
# faithful port, not a shortcut.
#
# UNLIKE Flasher.tsx, only Query Version reaches a real hardware path -
# self-test/F-RAM/LED/bus monitor all need real STM32H745
# APPLICATION-level commands that don't exist in the H745 firmware yet
# (still a FreeRTOS smoke-test stub) - those stay simulated regardless of
# transport setting, with an explicit note in the UI rather than silently
# pretending otherwise. Like URTC-TESTER itself, self-test only ever
# performs SAFE at-rest checks - never actuates anything at meaningful
# power.
#
# Status LED / Ring LED / OLED mode / F-RAM state are real-but-local UI
# state here, matching STUDIO's own plain useState() for all four - none
# of them round-trip through updateRobot()/push_active_state() on
# STUDIO's own side either (no real APPLICATION-level command exists yet
# to actually send them anywhere).
# =============================================================================
from __future__ import annotations

import asyncio
import random
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.can_ota import (
    CanFrame,
    CanOtaTarget,
    CanOtaTier,
    chip_name_for,
    has_advanced_expansion,
    hop_description,
    mock_bus_monitor,
    mock_query_version,
    mock_self_test,
    slot_label,
)
from hydra_suite.i18n import _
from hydra_suite.models import ControllerView, HydraState, RobotView

ALL_TIERS: tuple[CanOtaTier, ...] = ("kinematicBrain", "controllerBoard", "urtcHead", "urtcExpansion")

_TIER_LABEL_KEYS: dict[CanOtaTier, str] = {
    "kinematicBrain": "LBL_TARGET_KINEMATIC_BRAIN",
    "controllerBoard": "LBL_TARGET_CONTROLLER_BOARD",
    "urtcHead": "LBL_TARGET_URTC_HEAD",
    "urtcExpansion": "LBL_TARGET_URTC_EXPANSION",
}

# Matches Tester.tsx's own TOOL_CATEGORY exactly - lives here, not in
# can_ota.py, since STUDIO itself keeps this Tester-only.
_TOOL_CATEGORY: dict[str, str] = {
    "Soldering Station (T12)": "thermal",
    "3D Printing Hotend": "thermal",
    "Hot Air Rework Nozzle": "thermal",
    "Drill (BL4260)": "motor",
    "Smart Electric Screwdriver": "motor",
    "SMT Solder Paste Dispenser": "motor",
    "Thermal Paste / Liquid Dispenser": "motor",
    "Vacuum / Pneumatic Gripper": "vacuum",
    "Large-Format Vacuum Gripper": "vacuum",
    "Heavy-Duty Electromagnet": "binary",
    "Spot Welder Head": "binary",
    "Ultrasonic Welder / Packaging Sealer": "binary",
    "UV Curing Head": "binary",
}


def _category_for(tool: str) -> str:
    return _TOOL_CATEGORY.get(tool, "generic")


class TesterPanel(QWidget):
    def __init__(self, controller: SuiteController, tiers: tuple[CanOtaTier, ...] = ALL_TIERS, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._tiers = tiers
        self._active_controller: ControllerView | None = None
        self._is_hardware_transport = False
        self._tier: CanOtaTier = tiers[0]
        self._robot_id: str | None = None
        self._status_color = "#00ff66"
        self._ring_on = False
        self._oled_mode = "standard"
        self._fram_state: bool | None = None
        self._testing = False
        self._frames: list[CanFrame] = []
        self._monitor_task: asyncio.Task | None = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(host)
        page_layout.addWidget(scroll)

        heading = QLabel(_("HEADING_TESTER"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        self._simulated_note = QLabel(_("LBL_TESTER_SIMULATED_NOTE"))
        self._simulated_note.setStyleSheet("color: #f59e0b;")
        self._simulated_note.setWordWrap(True)
        self._simulated_note.setVisible(False)
        layout.addWidget(self._simulated_note)

        # --- Target selection (duplicated from FlasherPanel - see this
        # file's own header for why) -------------------------------------
        target_row1 = QHBoxLayout()
        target_row1.addWidget(QLabel(_("LBL_BOARD")))
        self._tier_combo = QComboBox()
        for t in tiers:
            self._tier_combo.addItem(f"{_(_TIER_LABEL_KEYS[t])} ({chip_name_for(t)})", t)
        self._tier_combo.currentIndexChanged.connect(self._on_tier_combo_changed)
        target_row1.addWidget(self._tier_combo, 1)
        layout.addLayout(target_row1)

        target_row2 = QHBoxLayout()
        self._robot_label = QLabel(_("LBL_ROBOT_SLOT"))
        target_row2.addWidget(self._robot_label)
        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        target_row2.addWidget(self._robot_combo, 1)
        layout.addLayout(target_row2)

        self._hop_label = QLabel()
        self._hop_label.setStyleSheet("font-family: monospace; color: #7f8ea1; font-size: 10px;")
        self._hop_label.setWordWrap(True)
        layout.addWidget(self._hop_label)

        version_row = QHBoxLayout()
        self._version_label = QLabel(_("LBL_NO_VERSION_KNOWN"))
        version_row.addWidget(self._version_label, 1)
        self._query_btn = QPushButton(_("BTN_QUERY_VERSION"))
        self._query_btn.clicked.connect(lambda: asyncio.ensure_future(self._do_query_version()))
        version_row.addWidget(self._query_btn)
        layout.addLayout(version_row)

        # --- Global Controls (urtcHead only) ------------------------------
        self._global_box = QWidget()
        global_layout = QVBoxLayout(self._global_box)
        global_layout.addWidget(QLabel(_("LBL_GLOBAL_CONTROLS")))
        led_row = QHBoxLayout()
        led_row.addWidget(QLabel(_("LBL_STATUS_LED")))
        self._status_led_btn = QPushButton()
        self._status_led_btn.clicked.connect(self._on_pick_status_color)
        led_row.addWidget(self._status_led_btn)
        global_layout.addLayout(led_row)
        ring_row = QHBoxLayout()
        ring_row.addWidget(QLabel(_("LBL_RING_LED")))
        self._ring_btn = QPushButton()
        self._ring_btn.clicked.connect(self._on_toggle_ring)
        ring_row.addWidget(self._ring_btn)
        global_layout.addLayout(ring_row)
        oled_row = QHBoxLayout()
        oled_row.addWidget(QLabel(_("LBL_OLED_MODE")))
        self._oled_combo = QComboBox()
        self._oled_combo.addItem(_("LBL_OLED_STANDARD"), "standard")
        self._oled_combo.addItem(_("LBL_OLED_NIGHT"), "night")
        self._oled_combo.addItem(_("LBL_OLED_OFF"), "off")
        self._oled_combo.currentIndexChanged.connect(self._on_oled_combo_changed)
        oled_row.addWidget(self._oled_combo)
        global_layout.addLayout(oled_row)
        self._expansion_label = QLabel()
        global_layout.addWidget(self._expansion_label)
        layout.addWidget(self._global_box)

        # --- F-RAM (controllerBoard/urtcHead) -----------------------------
        self._fram_box = QWidget()
        fram_layout = QVBoxLayout(self._fram_box)
        fram_layout.addWidget(QLabel(_("LBL_FRAM")))
        self._fram_state_label = QLabel(_("LBL_FRAM_UNKNOWN"))
        fram_layout.addWidget(self._fram_state_label)
        fram_btn_row = QHBoxLayout()
        fram_query_btn = QPushButton(_("BTN_FRAM_QUERY"))
        fram_query_btn.clicked.connect(lambda: asyncio.ensure_future(self._do_fram_query()))
        fram_btn_row.addWidget(fram_query_btn)
        fram_erase_btn = QPushButton(_("BTN_FRAM_ERASE"))
        fram_erase_btn.clicked.connect(self._on_fram_erase)
        fram_btn_row.addWidget(fram_erase_btn)
        fram_layout.addLayout(fram_btn_row)
        layout.addWidget(self._fram_box)

        # --- Tool Telemetry (urtcHead only) -------------------------------
        self._telemetry_box = QWidget()
        telemetry_layout = QVBoxLayout(self._telemetry_box)
        self._telemetry_title = QLabel()
        telemetry_layout.addWidget(self._telemetry_title)
        self._telemetry_label = QLabel()
        telemetry_layout.addWidget(self._telemetry_label)
        layout.addWidget(self._telemetry_box)

        # --- Self-Test -------------------------------------------------
        layout.addWidget(QLabel(_("LBL_SELF_TEST")))
        self_test_row = QHBoxLayout()
        self._self_test_note = QLabel(_("LBL_SELF_TEST_NOTE"))
        self._self_test_note.setWordWrap(True)
        self._self_test_note.setStyleSheet("color: #7f8ea1; font-size: 10px;")
        self_test_row.addWidget(self._self_test_note, 1)
        self._self_test_btn = QPushButton(_("BTN_RUN_SELF_TEST"))
        self._self_test_btn.clicked.connect(lambda: asyncio.ensure_future(self._do_self_test()))
        self_test_row.addWidget(self._self_test_btn)
        layout.addLayout(self_test_row)
        self._self_test_grid = QGridLayout()
        self_test_host = QWidget()
        self_test_host.setLayout(self._self_test_grid)
        layout.addWidget(self_test_host)
        self._self_test_labels: list[QLabel] = []

        # --- Raw CAN Bus Monitor -------------------------------------------
        monitor_row = QHBoxLayout()
        monitor_row.addWidget(QLabel(_("LBL_BUS_MONITOR")))
        monitor_row.addStretch(1)
        self._monitor_btn = QPushButton(_("BTN_MONITOR_START"))
        self._monitor_btn.clicked.connect(self._on_toggle_monitor)
        monitor_row.addWidget(self._monitor_btn)
        layout.addLayout(monitor_row)
        self._frames_table = QTableWidget(0, 4)
        self._frames_table.setHorizontalHeaderLabels([_("LBL_COL_TIME"), _("LBL_COL_ID"), "DLC", _("LBL_COL_DATA")])
        self._frames_table.setMaximumHeight(180)
        layout.addWidget(self._frames_table)

        controller.active_state_changed.connect(self._on_state_changed)
        self._refresh_target_controls()

    # --- state sync ----------------------------------------------------

    def _on_state_changed(self, state: HydraState) -> None:
        self._active_controller = state.active_controller
        self._is_hardware_transport = state.can_ota_transport == "hardware"
        self._simulated_note.setVisible(self._is_hardware_transport)

        robots = self._active_controller.robots if self._active_controller is not None else []
        previously_selected = self._robot_id
        self._robot_combo.blockSignals(True)
        self._robot_combo.clear()
        for i, r in enumerate(robots):
            self._robot_combo.addItem(f"{slot_label(i)} - {r.model}", r.id)
        restore_index = 0
        if previously_selected is not None:
            for i in range(self._robot_combo.count()):
                if self._robot_combo.itemData(i) == previously_selected:
                    restore_index = i
                    break
        if self._robot_combo.count() > 0:
            self._robot_combo.setCurrentIndex(restore_index)
        self._robot_combo.blockSignals(False)
        self._robot_id = self._robot_combo.currentData() if self._robot_combo.count() > 0 else None

        self._refresh_target_controls()

    def _on_tier_combo_changed(self, index: int) -> None:
        self._tier = self._tier_combo.itemData(index)
        self._reset_for_new_target()

    def _on_robot_combo_changed(self, index: int) -> None:
        self._robot_id = self._robot_combo.itemData(index)
        self._reset_for_new_target()

    def _reset_for_new_target(self) -> None:
        """Matches Tester.tsx's own resetForTargetKey effect - switching
        tier/robot drops any in-flight self-test/monitor state for the
        PREVIOUS target rather than leaving it displayed against a now-
        different one."""
        self._stop_monitor()
        self._fram_state = None
        self._testing = False
        for lbl in self._self_test_labels:
            lbl.deleteLater()
        self._self_test_labels = []
        self._refresh_target_controls()

    def _current_robot(self) -> RobotView | None:
        if self._active_controller is None or self._robot_id is None:
            return None
        for r in self._active_controller.robots:
            if r.id == self._robot_id:
                return r
        return None

    def _current_target(self) -> CanOtaTarget | None:
        if self._active_controller is None:
            return None
        if self._tier == "kinematicBrain":
            return CanOtaTarget(controller_name=self._active_controller.name, tier=self._tier)
        robot = self._current_robot()
        if robot is None:
            return None
        robots = self._active_controller.robots
        index0 = next((i for i, r in enumerate(robots) if r.id == robot.id), -1)
        if index0 < 0:
            return None
        return CanOtaTarget(
            controller_name=self._active_controller.name, tier=self._tier,
            robot_id=robot.id, robot_name=robot.model, robot_index0=index0,
        )

    def _board_state(self) -> dict:
        if self._tier == "kinematicBrain":
            return self._active_controller.kinematic_brain if self._active_controller else {}
        robot = self._current_robot()
        if robot is None:
            return {}
        return robot.module(self._tier)

    def _refresh_target_controls(self) -> None:
        needs_robot_slot = self._tier != "kinematicBrain"
        self._robot_label.setVisible(needs_robot_slot)
        self._robot_combo.setVisible(needs_robot_slot)

        robot = self._current_robot()
        expansion_available = has_advanced_expansion((robot.module("urtcHead") if robot else {}).get("expansionBoardType"))
        for i in range(self._tier_combo.count()):
            tier_value = self._tier_combo.itemData(i)
            enabled = True
            if tier_value == "urtcHead":
                enabled = bool(robot and robot.urtc_connected)
            elif tier_value == "urtcExpansion":
                enabled = expansion_available
            item = self._tier_combo.model().item(i)
            if item is not None:
                item.setEnabled(enabled)

        target = self._current_target()
        self._hop_label.setText(hop_description(target) if target else "")
        self._query_btn.setEnabled(target is not None)
        self._self_test_btn.setEnabled(target is not None and not self._testing)
        self._monitor_btn.setEnabled(target is not None)

        board = self._board_state()
        if board.get("firmwareVersion"):
            self._version_label.setText(f"{_('LBL_CURRENT_VERSION')}: {board.get('firmwareVersion', '?')}")
        else:
            self._version_label.setText(_("LBL_NO_VERSION_KNOWN"))

        self._global_box.setVisible(self._tier == "urtcHead")
        self._fram_box.setVisible(self._tier in ("controllerBoard", "urtcHead"))
        self._telemetry_box.setVisible(self._tier == "urtcHead" and robot is not None)

        self._status_led_btn.setStyleSheet(f"background-color: {self._status_color};")
        self._ring_btn.setText(_("LBL_ON") if self._ring_on else _("LBL_OFF"))
        expansion_type = (robot.module("urtcHead") if robot else {}).get("expansionBoardType")
        if expansion_type is not None:
            label = _("LBL_EXPANSION_NONE") if expansion_type == 0 else f"#{expansion_type}" + (f" ({_(_TIER_LABEL_KEYS['urtcExpansion'])})" if expansion_available else "")
            self._expansion_label.setText(f"{_('LBL_EXPANSION_BOARD')}: {label}")
        else:
            self._expansion_label.setText("")

        if self._fram_state is None:
            self._fram_state_label.setText(_("LBL_FRAM_UNKNOWN"))
        elif self._fram_state:
            self._fram_state_label.setText(_("LBL_FRAM_VALID"))
        else:
            self._fram_state_label.setText(_("LBL_FRAM_EMPTY"))

        if robot is not None:
            self._telemetry_title.setText(f"{_('LBL_TOOL_TELEMETRY')} - {robot.tool}")
            category = _category_for(robot.tool)
            self._telemetry_label.setText(_(f"LBL_TELEMETRY_{category.upper()}"))

    # --- version query + global controls ---------------------------------

    async def _do_query_version(self) -> None:
        target = self._current_target()
        if target is None:
            return
        self._query_btn.setEnabled(False)
        try:
            if self._is_hardware_transport:
                conn = self._controller.active_connection
                if conn is None:
                    return
                from hydra_suite.can_ota import hardware_query_version
                result = await hardware_query_version(conn, target)
            else:
                result = await mock_query_version(target)
        finally:
            self._query_btn.setEnabled(True)
        if not result.online:
            return
        patch = {"firmwareVersion": result.firmware_version, "bootloaderVersion": result.bootloader_version, "hardwareId": result.hardware_id}
        if self._tier == "kinematicBrain" and self._active_controller is not None:
            self._active_controller.set_kinematic_brain(patch)
        elif self._tier == "urtcHead":
            robot = self._current_robot()
            if robot is not None:
                if result.expansion_board_type is not None:
                    patch["expansionBoardType"] = result.expansion_board_type
                robot.set_module("urtcHead", {**robot.module("urtcHead"), **patch})
        else:
            robot = self._current_robot()
            if robot is not None:
                robot.set_module(self._tier, patch)
        self._controller.push_active_state()
        self._refresh_target_controls()

    def _on_pick_status_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._status_color), self, _("LBL_STATUS_LED"))
        if color.isValid():
            self._status_color = color.name()
            self._refresh_target_controls()

    def _on_toggle_ring(self) -> None:
        self._ring_on = not self._ring_on
        self._refresh_target_controls()

    def _on_oled_combo_changed(self, index: int) -> None:
        self._oled_mode = self._oled_combo.itemData(index)

    # --- F-RAM -------------------------------------------------------

    async def _do_fram_query(self) -> None:
        await asyncio.sleep(0.15)
        self._fram_state = random.random() > 0.3
        self._refresh_target_controls()

    def _on_fram_erase(self) -> None:
        self._fram_state = False
        self._refresh_target_controls()

    # --- self-test ---------------------------------------------------

    async def _do_self_test(self) -> None:
        target = self._current_target()
        if target is None:
            return
        self._testing = True
        for lbl in self._self_test_labels:
            lbl.deleteLater()
        self._self_test_labels = []
        self._refresh_target_controls()
        row = 0
        async for step in mock_self_test(target):
            icon = "✅" if step.passed else "❌"
            label = QLabel(f"{icon} {_(f'LBL_SELFTEST_{step.label_key.upper()}')}")
            label.setStyleSheet("color: #34d399;" if step.passed else "color: #fb7185;")
            self._self_test_grid.addWidget(label, row, 0)
            self._self_test_labels.append(label)
            row += 1
        self._testing = False
        self._refresh_target_controls()

    # --- raw bus monitor -----------------------------------------------

    def _on_toggle_monitor(self) -> None:
        if self._monitor_task is not None:
            self._stop_monitor()
            return
        target = self._current_target()
        if target is None:
            return
        self._frames = []
        self._refresh_frames_table()
        self._monitor_task = asyncio.ensure_future(self._run_monitor(target))
        self._monitor_btn.setText(_("BTN_MONITOR_STOP"))

    def _stop_monitor(self) -> None:
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            self._monitor_task = None
            self._monitor_btn.setText(_("BTN_MONITOR_START"))

    async def _run_monitor(self, target: CanOtaTarget) -> None:
        try:
            async for frame in mock_bus_monitor(target):
                self._frames = [*self._frames[-99:], frame]
                self._refresh_frames_table()
        except asyncio.CancelledError:
            pass

    def _refresh_frames_table(self) -> None:
        frames = list(reversed(self._frames))
        self._frames_table.setRowCount(len(frames))
        for row, f in enumerate(frames):
            self._frames_table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S", time.localtime(f.timestamp))))
            self._frames_table.setItem(row, 1, QTableWidgetItem(f"0x{f.id:X}"))
            self._frames_table.setItem(row, 2, QTableWidgetItem(str(f.dlc)))
            self._frames_table.setItem(row, 3, QTableWidgetItem(" ".join(f"{b:02X}" for b in f.data)))
