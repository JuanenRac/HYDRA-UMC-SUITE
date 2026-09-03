# =============================================================================
# HYDRA-UMC SUITE - ui/panels/flasher_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own Flasher.tsx (425 lines) - the 10th
# of 11 panels from [[project_suite_studio_parity_gap]]. CAN-OTA (and, for
# the Kinematic Brain, SPI-OTA) firmware flashing - see can_ota.py's own
# header for the full 4-tier chain this targets. `tiers` restricts which
# tiers one instance offers, matching STUDIO's own Dashboard.tsx: the
# "URTC" nav gets `URTC_TIERS`, the "HYDRA-UMC" nav gets
# `HYDRA_BRAIN_TIERS` - two separate FlasherPanel instances in
# main_window.py, not one panel switching between both sets.
#
# 'mock' transport (default) simulates the whole protocol client-side via
# can_ota.py's own async generators - fully usable/demoable ahead of real
# hardware. 'hardware' transport (`HydraState.can_ota_transport`) reaches
# a REAL path for kinematicBrain/controllerBoard only (Tier 0-1) via
# HydraConnection.canota_request() - urtcHead/urtcExpansion have no real
# relay tunnel yet regardless of transport setting, matching STUDIO's own
# honest boundary exactly (resolveHardwareTarget() returns None for Tier 3).
#
# Runs on Qt's own event loop via qasync (main.py) - the async GitHub
# fetch/download and the real hardware query/flash calls are plain
# coroutines scheduled with asyncio.ensure_future() from a button click,
# same pattern SuiteController.push_active_state() already uses.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.can_ota import (
    GITHUB_FIRMWARE_REPO,
    CanOtaTarget,
    CanOtaTier,
    FlashOptions,
    GithubFirmwareAsset,
    chip_name_for,
    crc32,
    download_github_firmware,
    fetch_github_firmware_releases,
    has_advanced_expansion,
    hardware_start_flash,
    hop_description,
    mock_flash,
    resolve_hardware_target,
    slot_label,
)
from hydra_suite.i18n import _
from hydra_suite.models import ControllerView, HydraState, RobotView

# Matches HYDRA-UMC-STUDIO's own Dashboard.tsx exactly - two real, separate
# instance configurations, not one panel switching between tier sets.
URTC_TIERS: tuple[CanOtaTier, ...] = ("urtcHead", "urtcExpansion")
HYDRA_BRAIN_TIERS: tuple[CanOtaTier, ...] = ("kinematicBrain", "controllerBoard")
ALL_TIERS: tuple[CanOtaTier, ...] = ("kinematicBrain", "controllerBoard", "urtcHead", "urtcExpansion")

_TIER_LABEL_KEYS: dict[CanOtaTier, str] = {
    "kinematicBrain": "LBL_TARGET_KINEMATIC_BRAIN",
    "controllerBoard": "LBL_TARGET_CONTROLLER_BOARD",
    "urtcHead": "LBL_TARGET_URTC_HEAD",
    "urtcExpansion": "LBL_TARGET_URTC_EXPANSION",
}


class FlasherPanel(QWidget):
    def __init__(self, controller: SuiteController, tiers: tuple[CanOtaTier, ...] = ALL_TIERS, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._tiers = tiers
        self._active_controller: ControllerView | None = None
        self._is_hardware_transport = False
        self._tier: CanOtaTier = tiers[0]
        self._robot_id: str | None = None
        self._file_name: str = ""
        self._file_bytes: bytes = b""
        self._file_hardware_id: str | None = None
        self._file_version_tag: str | None = None
        self._gh_assets: list[GithubFirmwareAsset] = []
        self._flashing = False
        self._flash_task: asyncio.Task | None = None

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

        heading = QLabel(_("HEADING_FLASHER"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._unreachable_label = QLabel(_("LBL_HARDWARE_TARGET_UNREACHABLE"))
        self._unreachable_label.setStyleSheet("color: #f59e0b;")
        self._unreachable_label.setVisible(False)
        layout.addWidget(self._unreachable_label)

        # --- Target selection -------------------------------------------
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

        # --- Firmware file -------------------------------------------------
        layout.addWidget(QLabel(_("LBL_FIRMWARE_FILE")))
        file_row = QHBoxLayout()
        self._browse_btn = QPushButton(_("BTN_BROWSE_BIN"))
        self._browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(self._browse_btn)
        self._gh_btn = QPushButton()
        self._gh_btn.clicked.connect(lambda: asyncio.ensure_future(self._do_fetch_github()))
        file_row.addWidget(self._gh_btn)
        layout.addLayout(file_row)
        self._file_info_label = QLabel(_("LBL_NO_FILE"))
        self._file_info_label.setStyleSheet("font-family: monospace; color: #7f8ea1;")
        layout.addWidget(self._file_info_label)

        self._gh_list = QListWidget()
        self._gh_list.setMaximumHeight(120)
        self._gh_list.itemClicked.connect(self._on_gh_item_clicked)
        self._gh_list.setVisible(False)
        layout.addWidget(self._gh_list)

        options_row = QHBoxLayout()
        self._allow_downgrade_check = QCheckBox(_("LBL_ALLOW_DOWNGRADE"))
        options_row.addWidget(self._allow_downgrade_check)
        self._erase_fram_check = QCheckBox(_("LBL_ERASE_FRAM"))
        options_row.addWidget(self._erase_fram_check)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        # --- Flash action + progress -------------------------------------
        self._flash_btn = QPushButton(_("BTN_FLASH_NOW"))
        self._flash_btn.clicked.connect(self._on_flash_clicked)
        layout.addWidget(self._flash_btn)

        self._progress_label = QLabel()
        layout.addWidget(self._progress_label)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        layout.addWidget(self._progress_bar)

        # --- Log -------------------------------------------------------
        layout.addWidget(QLabel(_("LBL_LOG_TITLE")))
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumHeight(160)
        self._log_view.setStyleSheet("font-family: monospace; font-size: 10px; background: #05080c;")
        layout.addWidget(self._log_view)

        controller.active_state_changed.connect(self._on_state_changed)
        self._refresh_target_controls()

    # --- state sync ----------------------------------------------------

    def _on_state_changed(self, state: HydraState) -> None:
        self._active_controller = state.active_controller
        self._is_hardware_transport = state.can_ota_transport == "hardware"

        robots = self._active_controller.robots if self._active_controller is not None else []
        previously_selected = self._robot_id
        self._robot_combo.blockSignals(True)
        self._robot_combo.clear()
        for i, r in enumerate(robots):
            unreachable = "" if r.urtc_connected else f" ({_('LBL_URTC_UNREACHABLE')})"
            self._robot_combo.addItem(f"{slot_label(i)} - {r.model}{unreachable}", r.id)
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
        self._refresh_target_controls()

    def _on_robot_combo_changed(self, index: int) -> None:
        self._robot_id = self._robot_combo.itemData(index)
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

        # Matches STUDIO's own Board <select>: urtcHead disabled when the
        # slot's own URTC head isn't reachable, urtcExpansion disabled
        # when that head has no Advanced Expansion Board at all.
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

        is_hardware = self._is_hardware_transport
        unreachable = is_hardware and target is not None and resolve_hardware_target(target) is None
        self._unreachable_label.setVisible(unreachable)
        self._flash_btn.setEnabled(bool(self._file_bytes) and not self._flashing and not unreachable)

        board = self._board_state()
        if board.get("firmwareVersion"):
            self._version_label.setText(
                f"{_('LBL_CURRENT_VERSION')}: {board.get('firmwareVersion', '?')} ({_('LBL_BOOTLOADER')} {board.get('bootloaderVersion', '?')})"
            )
        else:
            self._version_label.setText(_("LBL_NO_VERSION_KNOWN"))

        github_repo = GITHUB_FIRMWARE_REPO.get(self._tier)
        self._gh_btn.setVisible(github_repo is not None)
        if github_repo:
            self._gh_btn.setText(f"{_('BTN_DOWNLOAD_GITHUB')} ({github_repo})")

    def _push_log(self, text: str, level: str = "info") -> None:
        color = {"ok": "#34d399", "error": "#fb7185"}.get(level, "#94a3b8")
        self._log_view.append(f'<span style="color:{color}">{text}</span>')

    # --- version query ---------------------------------------------------

    async def _do_query_version(self) -> None:
        target = self._current_target()
        if target is None or self._active_controller is None:
            return
        self._query_btn.setEnabled(False)
        self._push_log(f"{_('LBL_QUERYING')}: {hop_description(target)}")
        try:
            if self._is_hardware_transport:
                conn = self._controller.active_connection
                if conn is None:
                    self._push_log(_("LBL_NO_RESPONSE"), "error")
                    return
                from hydra_suite.can_ota import hardware_query_version
                result = await hardware_query_version(conn, target)
            else:
                from hydra_suite.can_ota import mock_query_version
                result = await mock_query_version(target)
        finally:
            self._query_btn.setEnabled(True)

        if not result.online:
            self._push_log(_("LBL_NO_RESPONSE"), "error")
            return
        self._push_log(f"{_('LBL_VERSION_FOUND')}: {result.firmware_version} / {result.bootloader_version}", "ok")
        patch = {
            "firmwareVersion": result.firmware_version,
            "bootloaderVersion": result.bootloader_version,
            "hardwareId": result.hardware_id,
        }
        if self._tier == "urtcHead" and result.expansion_board_type is not None:
            patch["expansionBoardType"] = result.expansion_board_type
        self._apply_board_patch(patch)

    def _apply_board_patch(self, patch: dict) -> None:
        if self._active_controller is None:
            return
        if self._tier == "kinematicBrain":
            self._active_controller.set_kinematic_brain(patch)
        else:
            robot = self._current_robot()
            if robot is None:
                return
            if self._tier == "urtcHead":
                merged = {**robot.module("urtcHead"), **patch}
                robot.set_module("urtcHead", merged)
            else:
                robot.set_module(self._tier, patch)
        self._controller.push_active_state()
        self._refresh_target_controls()

    # --- firmware file ---------------------------------------------------

    def _on_browse(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, _("BTN_BROWSE_BIN"), "", "Binary (*.bin)")
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        import os
        self._set_file(os.path.basename(path), data)
        self._push_log(f"{_('LBL_FILE_LOADED')}: {os.path.basename(path)} ({len(data)} bytes)")

    def _set_file(self, name: str, data: bytes, hardware_id: str | None = None, version_tag: str | None = None) -> None:
        self._file_name = name
        self._file_bytes = data
        self._file_hardware_id = hardware_id
        self._file_version_tag = version_tag
        self._file_info_label.setText(f"{name} - {len(data) / 1024:.1f} KB - CRC32 0x{crc32(data):08X}")
        self._refresh_target_controls()

    async def _do_fetch_github(self) -> None:
        repo = GITHUB_FIRMWARE_REPO.get(self._tier)
        if not repo:
            return
        self._gh_btn.setEnabled(False)
        self._gh_list.clear()
        try:
            assets = await fetch_github_firmware_releases(repo, self._tier)
            self._gh_assets = assets
            self._push_log(f"{_('LBL_GITHUB_FOUND')}: {len(assets)} ({repo})")
            if not assets:
                self._gh_list.addItem(_("LBL_NO_RELEASES"))
            for a in assets:
                label = f"{a.display_name or a.name} v{a.release_tag}{f' - {a.chip}' if a.chip else ''} ({a.size / 1024:.1f} KB)"
                item = QListWidgetItem(label)
                self._gh_list.addItem(item)
            self._gh_list.setVisible(True)
        except Exception as exc:
            self._push_log(f"{_('LBL_GITHUB_ERROR')}: {exc}", "error")
        finally:
            self._gh_btn.setEnabled(True)

    def _on_gh_item_clicked(self, item: QListWidgetItem) -> None:
        index = self._gh_list.row(item)
        if index < 0 or index >= len(self._gh_assets):
            return
        asset = self._gh_assets[index]
        asyncio.ensure_future(self._do_use_github_asset(asset))

    async def _do_use_github_asset(self, asset: GithubFirmwareAsset) -> None:
        self._push_log(f"{_('LBL_GITHUB_DOWNLOADING')}: {asset.name}")
        try:
            data = await download_github_firmware(asset)
            self._set_file(asset.name, data, hardware_id=asset.hardware_id, version_tag=asset.release_tag)
            self._push_log(f"{_('LBL_FILE_LOADED')}: {asset.name} ({len(data)} bytes)", "ok")
        except Exception as exc:
            self._push_log(f"{_('LBL_GITHUB_ERROR')}: {exc}", "error")

    # --- flash -------------------------------------------------------

    def _on_flash_clicked(self) -> None:
        target = self._current_target()
        if target is None or not self._file_bytes:
            return
        robot_label = self._current_robot().model if self._current_robot() else (self._active_controller.name if self._active_controller else "")
        reply = QMessageBox.question(
            self, _("BTN_FLASH_NOW"),
            _("MSG_CONFIRM_FLASH", target=_(_TIER_LABEL_KEYS[self._tier]), robot=robot_label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._flash_task = asyncio.ensure_future(self._do_flash())

    async def _do_flash(self) -> None:
        target = self._current_target()
        if target is None or not self._file_bytes:
            return
        self._flashing = True
        self._flash_btn.setEnabled(False)
        self._push_log(f"{_('LBL_FLASH_START')}: {self._file_name} - {hop_description(target)}")
        try:
            if self._is_hardware_transport:
                resolved = resolve_hardware_target(target)
                if not resolved:
                    self._push_log(_("LBL_HARDWARE_TARGET_UNREACHABLE"), "error")
                    return
                self._progress_label.setText(_("FLASHER_PROGRESS_CONNECTING"))
                self._progress_bar.setValue(0)
                version_major, _sep, version_minor = (self._file_version_tag or "0.0").partition(".")
                hardware_id_number = int(self._file_hardware_id, 0) if self._file_hardware_id else 0
                conn = self._controller.active_connection
                if conn is None:
                    self._push_log(_("LBL_NO_RESPONSE"), "error")
                    return
                result = await hardware_start_flash(
                    conn, target, self._file_bytes,
                    int(version_major) if version_major.isdigit() else 0,
                    int(version_minor) if version_minor.isdigit() else 0,
                    hardware_id_number,
                )
                if result.success:
                    self._progress_label.setText(_("FLASHER_PROGRESS_DONE"))
                    self._progress_bar.setValue(100)
                    self._push_log(_("LBL_FLASH_DONE"), "ok")
                    self._apply_board_patch({"firmwareVersion": self._file_name.removesuffix(".bin")})
                else:
                    self._push_log(f"{_('LBL_FLASH_HARDWARE_FAILED')}: {result.reason}", "error")
                return

            opts = FlashOptions(allow_downgrade=self._allow_downgrade_check.isChecked(), erase_fram=self._erase_fram_check.isChecked())
            last_phase = None
            async for progress in mock_flash(target, self._file_bytes, opts):
                last_phase = progress.phase
                self._progress_bar.setValue(progress.percent)
                suffix = f" ({progress.pages_sent}/{progress.pages_total})" if progress.pages_total > 1 and progress.phase == "transferring" else ""
                self._progress_label.setText(f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')}{suffix} - {progress.percent}%")
                if progress.phase == "transferring" and progress.pages_sent % 5 != 0 and progress.pages_sent != progress.pages_total:
                    continue
                self._push_log(f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')} ({progress.pages_sent}/{progress.pages_total})", "error" if progress.phase == "error" else "info")
            if last_phase != "error":
                self._push_log(_("LBL_FLASH_DONE"), "ok")
                self._apply_board_patch({"firmwareVersion": self._file_name.removesuffix(".bin")})
        finally:
            self._flashing = False
            self._refresh_target_controls()
