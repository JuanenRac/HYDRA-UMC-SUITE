# =============================================================================
# HYDRA-UMC SUITE - qt_suite.py (Qt Quick command-deck entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick front end for HYDRA-UMC SUITE - the real "redesign from zero"
this repo's own CHANGELOG.md documents as necessary after BOTH real ways of
embedding QML inside the established QMainWindow+QDockWidget tree proved
unsafe (QQuickWidget painted solid black; QQuickView+createWindowContainer
rendered correctly in isolation but corrupted sibling widgets' real Z-order
inside this app's actual 26-dock layout - see this session's own memory
note for the full account). This is a STANDALONE pure-QML
ApplicationWindow instead, the same real shape as
HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-UPDATER/URTC-TESTER/URTC-FLASHER (all of
which already render correctly) - not an embed, so the mixing problem
those two failed attempts hit doesn't apply here at all.

Navigation trades QDockWidget's float/split/tab-merge flexibility for
HYDRA-UMC-STUDIO's own simpler nav-sidebar-plus-single-content-pane shape
(nav_sidebar.py's own real taxonomy - ROOT_ITEMS/INDUSTRIAL_ITEMS/
URTC_ITEMS/HYDRA_ITEMS/HYDRA_ECOSYSTEM_ITEMS - is mirrored here item for
item) - a deliberate real design choice per the STUDIO<->SUITE parity
rule, not an oversight: most users never actually float/split these docks,
and a hand-built docking system in QML would be a second, much bigger real
engineering project of its own (see e.g. KDDockWidgets existing as a whole
separate library for exactly this reason).

hydra_suite.app.SuiteController is reused completely unchanged here - it
was already a plain QObject with Qt Signals, never tied to QtWidgets, so
it needs zero changes to serve a QML front end too.

REAL, HONEST STATUS (kept current in this repo's own CHANGELOG.md, the
authoritative source - this docstring is not re-updated per panel to avoid
drifting out of sync with it): only a subset of the 26 real panels
main_window.py docks are ported to actual QML content so far; every other
one shows a real, honest "not yet migrated" placeholder (never a fake,
empty-but-styled panel pretending to be done) pointing back at the
existing classic view, which remains fully functional and is still this
app's own default entry point. Run `python main.py --qtquick` to see this
one instead - exactly the same opt-in convention URTC-TESTER/URTC-FLASHER
used while THEY were mid-migration.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import qasync
from PySide6.QtCore import Property, QDateTime, QObject, QSize, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickControls2 import QQuickStyle

from hydra_suite import __version__, logging_handler
from hydra_suite.app import SuiteController
from hydra_suite.can_ota import (
    GITHUB_FIRMWARE_REPO,
    CanOtaTarget,
    FlashOptions,
    chip_name_for,
    crc32,
    download_github_firmware,
    fetch_github_firmware_releases,
    hardware_query_version,
    hardware_start_flash,
    has_advanced_expansion,
    hop_description,
    mock_bus_monitor,
    mock_flash,
    mock_query_version,
    mock_self_test,
    resolve_hardware_target,
    slot_label,
)
from hydra_suite.i18n import _
from hydra_suite.models import (
    CAMERA_TYPES,
    JOINT_NAMES,
    RACK_MAX_CAPACITY,
    RTSP_DEFAULT_PORT,
    CameraView,
    ControllerView,
    HydraState,
    RobotView,
    ServerInfo,
    default_rack_system,
    ip_stream_labels,
)
from hydra_suite.net.client import HydraConnection
from hydra_suite.net.discovery import DEFAULT_PORT, discover_servers
from hydra_suite.ui.panels.admin_clients_panel import _relative_duration
from hydra_suite.ui.panels.admin_logs_panel import _extract_tag
from hydra_suite.ui.panels.admin_server_panel import _format_uptime
from hydra_suite.ui.panels.ai_family_status_panel import AI_FAMILIES
from hydra_suite.ui.panels.atc_tools_panel import (
    JOINT_FIELDS as _ATC_JOINT_FIELDS,
    JOINT_RANGE_DEG as _ATC_JOINT_RANGE_DEG,
    PANEL_GRIDS,
    TABLE_FIELDS as _ATC_TABLE_FIELDS,
    TABLE_RANGE_MM as _ATC_TABLE_RANGE_MM,
    URTC_TOOLS,
    _default_atc_config,
    _default_pos,
)
from hydra_suite.ui.panels.cameras_panel import (
    GRID_COLUMNS as _CAM_GRID_COLUMNS,
    _STATUS_COLORS as _CAM_STATUS_COLORS,
    _THERMAL_TYPE_OPTIONS as _CAM_THERMAL_TYPE_OPTIONS,
    _USB_TYPE_OPTIONS as _CAM_USB_TYPE_OPTIONS,
    iter_mjpeg_frames,
)
from hydra_suite.ui.panels.ecosystem_services_panel import _HEALTH_COLOR, _STACK_COLOR, _badge_label, _health
from hydra_suite.ui.panels.ecosystem_telemetry_panel import _AGGREGATES, _RANGE_PRESETS
from hydra_suite.ui.panels.flasher_panel import HYDRA_BRAIN_TIERS, URTC_TIERS, _TIER_LABEL_KEYS
from hydra_suite.ui.panels.heated_bed_panel import DEFAULT_AMBIENT_TEMP_C as _HB_DEFAULT_AMBIENT_TEMP_C, DEFAULT_TARGET_TEMP_C as _HB_DEFAULT_TARGET_TEMP_C
from hydra_suite.ui.panels.kinematic_brain_stage_panel import AXIS_KEYS as _KBS_AXIS_KEYS, ENDSTOP_ENTRIES, JOG_STEPS_MM as _KBS_JOG_STEPS_MM, _clamp
from hydra_suite.ui.panels.module_config_panel import DEFAULT_SIZE_MM
from hydra_suite.ui.panels.pick_and_place_panel import MACHINE_LABELS, MACHINE_TYPES, PNP_AXES
from hydra_suite.ui.panels.tester_panel import _category_for
from hydra_suite.ui.panels.vacuum_table_panel import DEFAULT_RESET_SIZE_MM as _VACUUM_RESET_SIZE_MM
from hydra_suite.ui.panels.viewport_panel import SUPPORTED_MODELS as _VIEWPORT_SUPPORTED_MODELS
from hydra_suite.ui.panels.xy_table_panel import (
    _DISPLAY_DEFAULT_SIZE_MM as _XY_DISPLAY_DEFAULT_SIZE_MM,
    JOG_STEPS_MM as _XY_JOG_STEPS_MM,
    _default_xy_table,
)
from hydra_suite.ui.panels.server_browser import STATUS_DISPLAY_KEYS

IMAGES_DIR = Path(__file__).resolve().parent / "images"
QML_PATH = Path(__file__).resolve().parent / "assets" / "qml" / "Main.qml"

# Real taxonomy - kept in exact lockstep with nav_sidebar.py's own
# ROOT_ITEMS/INDUSTRIAL_ITEMS/URTC_ITEMS/HYDRAUMC_ITEMS/
# HYDRAUMC_ECOSYSTEM_ITEMS (that file's own real test,
# tests/test_nav_sidebar.py, already guards against those drifting from
# main_window.py's own dock keys - this constant is a second, independent
# real transcription of the SAME source of truth for the QML nav, not a
# third invented taxonomy).
from hydra_suite.ui.nav_sidebar import (
    HYDRAUMC_ECOSYSTEM_ITEMS,
    HYDRAUMC_ITEMS,
    INDUSTRIAL_ITEMS,
    ROOT_ITEMS,
    URTC_ITEMS,
)

# Real panels actually ported to Qt Quick content so far - every other key
# in the taxonomy above falls back to the honest "not yet migrated"
# placeholder (see NotMigratedPanel in Main.qml). Update this set as more
# real panels are ported; it is the ONE place that decides which content
# the QML content area shows for a given nav key.
MIGRATED_PANELS = frozenset({"logs", "overview", "servers", "robot", "trajectory", "ai_family", "admin_clients", "admin_logs", "admin_server", "ecosystem_services", "ecosystem_telemetry", "xy_table", "rack", "pick_and_place", "kinematic_brain_stage", "cnc", "laser", "heated_bed", "vacuum_table", "atc", "cameras", "urtc_flasher", "hydra_flasher", "urtc_tester", "hydra_tester", "viewport"})

# Real per-instance tier set - matches main_window.py's own two separate
# FlasherPanel(tiers=...) instances exactly (URTC_TIERS/HYDRA_BRAIN_TIERS,
# imported, never redeclared), not one panel switching between both.
_FLASHER_TIERS: dict[str, tuple] = {"urtc_flasher": URTC_TIERS, "hydra_flasher": HYDRA_BRAIN_TIERS}
# main_window.py's own TesterPanel(tiers=...) instances reuse the SAME
# real URTC_TIERS/HYDRA_BRAIN_TIERS constants Flasher does (tester_panel.py's
# own header: it deliberately duplicates the target-selection shape rather
# than sharing a base class with FlasherPanel, matching STUDIO's own
# Tester.tsx/Flasher.tsx - so the Qt Quick bridge duplicates it too).
_TESTER_TIERS: dict[str, tuple] = {"urtc_tester": URTC_TIERS, "hydra_tester": HYDRA_BRAIN_TIERS}
_ATC_TYPE_KEYS: tuple[str, ...] = ("vertical_panel", "horizontal_panel", "revolver")

# Shared shape behind CNC/Laser/HeatedBed/VacuumTable - mirrors
# module_config_panel.py's own ModuleConfigPanel(module_key, heading_key,
# machine_name) parameterization exactly (see that file's own header for
# why one implementation covers all 4 real panels instead of duplicating
# the robot-selector/enable-disable/size/reset shape 4 times). "extra"
# names which of the two extension shapes (if any) this nav key's own
# classic subclass adds - heated_bed_panel.py's/vacuum_table_panel.py's
# own _build_extra_settings()/_refresh_extra_controls()/
# _extra_default_fields()/_extra_reset_fields() overrides, reproduced
# generically in SuiteQtBridge's own _module_extra_defaults() below
# rather than as 4 separate Python subclasses (QML has no notion of
# those anyway - one shared Component with an `extra` gate does the
# same job).
_MODULE_CONFIGS: dict[str, dict[str, object]] = {
    "cnc": {"module_key": "juanenCNC", "machine": "JuanenCNC", "heading": "HEADING_CNC", "reset_size": (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM), "extra": ""},
    "laser": {"module_key": "juanenLaser", "machine": "JuanenLaser", "heading": "HEADING_LASER", "reset_size": (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM), "extra": ""},
    "heated_bed": {"module_key": "heatedBed", "machine": "Heated Bed", "heading": "HEADING_HEATED_BED", "reset_size": (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM), "extra": "heated_bed"},
    # VacuumTableConfig.tsx's own real, if minor, inconsistency reproduced
    # faithfully: DISPLAYS the same 500mm fallback as the other 3 modules
    # (DEFAULT_SIZE_MM, used by moduleWidth/moduleLength before any real
    # size exists) but Reset actually WRITES 100mm (reset_size below) -
    # see vacuum_table_panel.py's own header for the full reasoning.
    "vacuum_table": {"module_key": "vacuumTable", "machine": "Vacuum Table", "heading": "HEADING_VACUUM_TABLE", "reset_size": (_VACUUM_RESET_SIZE_MM, _VACUUM_RESET_SIZE_MM), "extra": "vacuum_table"},
}
_RACK_POS_FIELDS = ("j1", "j2", "j3", "j4", "j5", "j6", "tx", "ty")
_ADMIN_CLIENTS_POLL_MS = 5000
_ADMIN_LOGS_POLL_MS = 3000
_ADMIN_LOGS_LINES = 300

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _with_alpha(hex_color: str, alpha: float) -> str:
    """'#4caf50' + 0.13 -> 'rgba(76,175,80,0.13)' - QML's own color
    parsing accepts CSS rgba() strings directly, unlike the classic
    panel's own Qt style sheet hex-plus-alpha-suffix trick
    (f"{color}22"), which is a QSS-only convention this Qt Quick deck
    doesn't use anywhere else."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


@dataclass(frozen=True)
class _LogEntry:
    level: str
    logger_name: str
    message: str


class CameraFrameProvider(QQuickImageProvider):
    """Feeds the Cameras panel's own real MJPEG frames into QML - a
    `QImage` per camera id, refreshed by SuiteQtBridge's own real
    `_run_camera_stream()` task every time `iter_mjpeg_frames()` yields a
    new real frame (cameras_panel.py's own function, imported directly,
    never duplicated). QML re-fetches on every frame by requesting
    `image://cameraFrames/<id>/<frameVersion>` - a changing suffix per
    frame, since QQuickImageProvider results are otherwise cached by
    their own request id and would never refresh a live feed."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._frames: dict[str, QImage] = {}

    def set_frame(self, camera_id: int, image: QImage) -> None:
        self._frames[str(camera_id)] = image

    def clear_frame(self, camera_id: int) -> None:
        self._frames.pop(str(camera_id), None)

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: N802 - Qt override signature
        camera_id = id.split("/", 1)[0]
        image = self._frames.get(camera_id)
        if image is None:
            image = QImage(1, 1, QImage.Format.Format_RGB32)
            image.fill(0x0A0F14)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class ViewportFrameProvider(QQuickImageProvider):
    """Feeds the 3D Viewport panel's own real rendered frame into QML -
    one real `QImage` (there's only ever one viewport, unlike Cameras'
    own per-id dict), refreshed by SuiteQtBridge's own real
    `_render_viewport_frame()` every time `render/viewport.py`'s own
    `OffscreenRobotRenderer.render()` produces a new one. QML re-fetches
    on every frame by requesting `image://viewportFrame/<frameVersion>` -
    same real cache-busting reasoning as CameraFrameProvider's own
    docstring."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image: QImage | None = None

    def set_image(self, image: QImage) -> None:
        self._image = image

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: N802 - Qt override signature
        image = self._image
        if image is None:
            image = QImage(1, 1, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFF)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class SuiteQtBridge(QObject):
    """Thin, UI-only bridge - real domain state stays on SuiteController
    (exposed to QML separately, unchanged, as context property
    'controller'). This class only owns things with no meaning outside a
    UI: which nav item is active, the ported panels' own QML-shaped
    display state, and i18n passthrough - the exact same division of
    responsibility URTC-TESTER/URTC-FLASHER's own bridges already use
    (their Property/Slot layer over an unmodified real backend)."""

    changed = Signal()
    _logsChanged = Signal()
    _trajectoryChanged = Signal()
    # Own dedicated signal (not the shared `changed` above) - a live MJPEG
    # feed can update several times a SECOND per camera, and `changed` is
    # read by dozens of unrelated Properties across every other panel;
    # firing it that often would re-evaluate all of them for no reason.
    _camerasChanged = Signal()
    # Same real reasoning as _camerasChanged above - a live 3D render can
    # update every real joint tick.
    _viewportChanged = Signal()

    def __init__(
        self,
        controller: SuiteController,
        frame_provider: "CameraFrameProvider | None" = None,
        viewport_frame_provider: "ViewportFrameProvider | None" = None,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._frame_provider = frame_provider
        self._viewport_frame_provider = viewport_frame_provider
        self._active_key = "overview"
        self._connection_status = "disconnected"

        # -- Logs (ported from logs_panel.py's own LogsPanel - same real
        # algorithmic shape: an unbounded _all_entries plus a
        # currently-matching-filter _displayed_entries, both appended to
        # in O(1) per new record; only a filter change re-derives
        # _displayed_entries from _all_entries in one O(n) pass, exactly
        # matching that file's own _refresh_display). The QML-facing
        # Property caps to the most recent 500 for render performance
        # (a ListView with the full unbounded history would be slow to
        # lay out) - the one real, deliberate deviation from the
        # classic view's QTextEdit, which had no such cap.
        self._log_level_filter: str | None = None
        self._log_search_filter = ""
        self._all_log_entries: list[_LogEntry] = []
        self._displayed_log_entries: list[_LogEntry] = []
        handler = logging_handler.install()
        handler.emitter.record_logged.connect(self._on_log_record)

        # -- Overview (ported from overview.py's own OverviewPanel) --
        self._overview_name = "-"
        self._overview_ip = "-"
        self._overview_robot_count = "-"
        self._overview_online_count = "-"
        self._overview_cpu = "-"
        self._overview_mem = "-"
        self._overview_temp = "-"
        self._overview_uptime = "-"
        self._overview_robots: list[dict[str, object]] = []
        controller.active_state_changed.connect(self._on_overview_state_changed)
        controller.active_metrics_changed.connect(self._on_overview_metrics_changed)
        controller.active_status_changed.connect(self._on_connection_status)

        # -- Servers (ported from server_browser.py's own ServerBrowserPanel -
        # STATUS_DISPLAY_KEYS is imported from there directly rather than
        # copied, so both UIs always agree on the same real status wording). --
        self._server_statuses: dict[str, str] = {}
        self._server_login: dict[str, tuple[bool, str]] = {}
        self._scanning = False
        self._scan_status_text = ""
        controller.connections_changed.connect(self._on_servers_changed)
        controller.active_connection_changed.connect(lambda _cid: self._on_servers_changed())
        controller.connection_status_changed.connect(self._on_server_status)
        controller.connection_login_changed.connect(self._on_server_login)

        # -- Robot Control (ported from robot_control.py's own
        # RobotControlPanel - RotaryKnob's own custom-painted dial is not
        # reproduced here, a Slider alone already sets the exact same
        # real value the classic panel's knob+slider pair redundantly
        # show, so nothing real is lost). --
        self._selected_robot_id: str | None = None
        self._active_robots_cache: list[RobotView] = []
        # Trajectory (ported from trajectory_panel.py's own TrajectoryPanel -
        # a real local-only point recorder, NOT yet HYDRA-UMC-STUDIO's own
        # WORKS/*.json format, same real scope note that file's own header
        # gives). Reset only when the SELECTED ROBOT ITSELF changes (see
        # _select_robot below), never on every swarm tick.
        self._trajectory_points: list[dict[str, object]] = []
        controller.active_state_changed.connect(self._on_robot_state_changed)

        # -- AI Family Status (ported from ai_family_status_panel.py's own
        # AiFamilyStatusPanel - AI_FAMILIES imported directly from there,
        # never duplicated). --
        self._ai_family_projects: list[dict] = []
        self._ai_family_ai_hailo: dict[str, str] = {}
        self._ai_family_status_text = _("LBL_ES_NOT_LOADED")
        self._ai_family_refreshing = False
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_ai_family()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_ai_family()))
        asyncio.ensure_future(self._refresh_ai_family())

        # -- Admin Clients (ported from admin_clients_panel.py's own
        # AdminClientsPanel - _relative_duration imported directly from
        # there, never duplicated). Real 5s data poll + a separate 1s
        # tick that only re-emits changed so the "Xm ago" durations
        # advance smoothly between polls, matching that file's own real
        # two-timer design exactly. --
        self._admin_clients: list[dict] = []
        self._admin_clients_status_text = _("MSG_ADMIN_ONLY")
        self._admin_clients_timer = QTimer(self)
        self._admin_clients_timer.setInterval(_ADMIN_CLIENTS_POLL_MS)
        self._admin_clients_timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh_admin_clients()))
        self._admin_clients_timer.start()
        self._admin_clients_tick_timer = QTimer(self)
        self._admin_clients_tick_timer.setInterval(1000)
        self._admin_clients_tick_timer.timeout.connect(self.changed.emit)
        self._admin_clients_tick_timer.start()
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_clients()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_clients()))
        asyncio.ensure_future(self._refresh_admin_clients())

        # -- Admin Logs (ported from admin_logs_panel.py's own
        # AdminLogsPanel - _extract_tag imported directly from there,
        # never duplicated). Same real "clear the screen, keep tailing"
        # anchor trick, live/pause, and tag+search filtering. --
        self._admin_logs_live = True
        self._admin_logs_all_lines: list[str] = []
        self._admin_logs_tag_filter: str | None = None
        self._admin_logs_search = ""
        self._admin_logs_cleared_anchor: str | None = None
        self._admin_logs_cleared_at_empty = False
        self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
        self._admin_logs_timer = QTimer(self)
        self._admin_logs_timer.setInterval(_ADMIN_LOGS_POLL_MS)
        self._admin_logs_timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh_admin_logs()))
        self._admin_logs_timer.start()
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_logs()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_logs()))
        asyncio.ensure_future(self._refresh_admin_logs())

        # -- Admin Server (ported from admin_server_panel.py's own
        # AdminServerPanel - _format_uptime imported directly from
        # there, never duplicated). --
        self._admin_server_status_text = _("MSG_ADMIN_ONLY")
        self._admin_server_current_port: int | None = None
        self._admin_server_pending_port_text = ""
        self._admin_server_info: dict[str, object] = {}
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_server()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_server()))
        asyncio.ensure_future(self._refresh_admin_server())

        # -- Ecosystem Services (ported from ecosystem_services_panel.py's
        # own EcosystemServicesPanel - _health/_badge_label/_HEALTH_COLOR/
        # _STACK_COLOR imported directly from there, never duplicated). --
        self._es_projects: list[dict] = []
        self._es_family_filter: str | None = None
        self._es_search = ""
        self._es_actioning_unit: str | None = None
        self._es_action_error: tuple[str, str] | None = None
        self._es_status_text = _("LBL_ES_NOT_LOADED")
        self._es_refreshing = False
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: self.changed.emit())

        # -- Ecosystem Telemetry (ported from ecosystem_telemetry_panel.py's
        # own EcosystemTelemetryPanel - _AGGREGATES/_RANGE_PRESETS imported
        # directly from there, never duplicated). Real chart rendering
        # uses a hand-drawn QML Canvas, NOT `import QtCharts` in QML -
        # that module segfaults on load in this real environment (PySide6
        # 6.11.1, confirmed both offscreen and on-screen) - see this
        # session's own memory note. --
        self._tel_status_text = ""
        self._tel_running = False
        self._tel_is_aggregate = False
        self._tel_chart_mode = "empty"
        self._tel_line_points: list[dict[str, float]] = []
        self._tel_bars: list[dict[str, object]] = []
        self._tel_stats: dict[str, str] = {}

        # -- XY Table (ported from xy_table_panel.py's own XYTablePanel -
        # _default_xy_table/_DISPLAY_DEFAULT_SIZE_MM/JOG_STEPS_MM
        # imported directly from there, never duplicated. Own real,
        # independent robot selection - NOT shared with Robot Control/
        # Trajectory's own, matching the classic panel's own real
        # independent QComboBox). --
        self._xy_selected_robot_id: str | None = None
        self._xy_jog_step_mm = 10.0
        self._xy_robots_cache: list[RobotView] = []
        controller.active_state_changed.connect(self._on_xy_state_changed)

        # -- Rack Manager (ported from rack_config_panel.py's own
        # RackConfigPanel - RACK_MAX_CAPACITY/default_rack_system
        # imported directly from there, never duplicated). Own real,
        # independent robot selection, matching that panel's own
        # separate QComboBox. --
        self._rack_selected_robot_id: str | None = None
        self._rack_robots_cache: list[RobotView] = []
        controller.active_state_changed.connect(self._on_rack_state_changed)

        # -- Pick and Place (ported from pick_and_place_panel.py's own
        # PickAndPlacePanel - MACHINE_TYPES/MACHINE_LABELS/PNP_AXES
        # imported directly from there, never duplicated. Own real,
        # independent robot selection, matching that panel's own
        # separate QComboBox. The "size-only" branch that panel's own
        # header documents as real-in-STUDIO-but-unreachable-through-this-
        # Machine-combo is intentionally NOT ported here - it never
        # renders in the classic panel either, so there is nothing a
        # real user could compare this port against; a future 3rd
        # Machine option would need to add it to both sides. The
        # right-hand "3D Live View" (RobotViewport in PnP-only mode) is
        # not ported, same as every other panel in this family. --
        self._pnp_selected_robot_id: str | None = None
        self._pnp_robots_cache: list[RobotView] = []
        self._pnp_machine_type: str = MACHINE_TYPES[0]
        controller.active_state_changed.connect(self._on_pnp_state_changed)

        # -- Kinematic Brain Stage (ported from
        # kinematic_brain_stage_panel.py's own KinematicBrainStagePanel -
        # AXIS_KEYS/JOG_STEPS_MM/ENDSTOP_ENTRIES/_clamp imported directly
        # from there, never duplicated). UNLIKE every other panel ported
        # so far, this is CONTROLLER-level state (one Kinematic Brain per
        # controller) - no robot selector at all, matching that file's
        # own header note. --
        self._kbs_controller: ControllerView | None = None
        self._kbs_jog_step_mm: float = 10.0
        controller.active_state_changed.connect(self._on_kbs_state_changed)

        # -- Module Config (CNC/Laser/HeatedBed/VacuumTable, generic over
        # _MODULE_CONFIGS above). Each of the 4 nav keys keeps its own
        # real, independent robot selection (matching module_config_panel.py's
        # own separate QComboBox per panel instance) - one dict entry per
        # key rather than 4 sets of named attributes. Properties/Slots
        # below always operate on whichever key is `self._active_key`
        # right now, since the QML Loader only ever shows one of the 4 at
        # a time. --
        self._module_selected_robot_id: dict[str, str | None] = {k: None for k in _MODULE_CONFIGS}
        self._module_robots_cache: dict[str, list[RobotView]] = {k: [] for k in _MODULE_CONFIGS}
        controller.active_state_changed.connect(self._on_module_state_changed)

        # -- ATC Tools (ported from atc_tools_panel.py's own AtcToolsPanel -
        # URTC_TOOLS/PANEL_GRIDS/JOINT_FIELDS/TABLE_FIELDS/*_RANGE_*/
        # _default_atc_config/_default_pos imported directly from there,
        # never duplicated). NOT built on the generic Module Config shape
        # above - `RobotView.atc` is a fundamentally different shape
        # (None vs a full ATCConfig, no separate `enabled` flag, 3 layout
        # types), matching that file's own header. Own real, independent
        # robot selection. `_atc_editing_slot` mirrors the classic panel's
        # own field exactly: None, an int slot index, or the literal
        # string "revolver" for the base pickup position editor. --
        self._atc_selected_robot_id: str | None = None
        self._atc_robots_cache: list[RobotView] = []
        self._atc_editing_slot: int | str | None = None
        self._atc_load_error: str = ""
        controller.active_state_changed.connect(self._on_atc_state_changed)

        # -- Cameras (ported from cameras_panel.py's own CamerasPanel/
        # CameraCard - CAMERA_TYPES/RTSP_DEFAULT_PORT/ip_stream_labels/
        # iter_mjpeg_frames/_USB_TYPE_OPTIONS/_THERMAL_TYPE_OPTIONS/
        # _STATUS_COLORS/GRID_COLUMNS imported directly from there, never
        # duplicated). The real live MJPEG feed reaches QML via
        # CameraFrameProvider above, injected here as `frame_provider` -
        # None in this offline/test context, every frame-touching method
        # below already no-ops safely on that. Uses its own dedicated
        # `_camerasChanged` signal (not `changed`) for the fast-moving
        # per-frame bits, so a live video feed never forces every OTHER
        # panel's own Property bindings to re-evaluate several times a
        # second - see that signal's own declaration for why. --
        self._camera_stream_tasks: dict[int, asyncio.Task] = {}
        self._camera_discovery_tasks: dict[int, asyncio.Task] = {}
        self._camera_placeholder: dict[int, tuple[str, str]] = {}
        self._camera_frame_versions: dict[int, int] = {}
        self._camera_status: dict[str, dict] = {}
        self._camera_usb_devices: dict[int, list[dict]] = {}
        self._camera_discovery_status: dict[int, tuple[str, str]] = {}
        self._camera_ptz_error: dict[int, str] = {}
        controller.active_state_changed.connect(self._on_cameras_state_changed)
        self._camera_status_timer = QTimer(self)
        self._camera_status_timer.setInterval(3000)
        self._camera_status_timer.timeout.connect(lambda: asyncio.ensure_future(self._poll_camera_status()))
        self._camera_status_timer.start()

        # -- Flasher (ported from flasher_panel.py's own FlasherPanel -
        # can_ota.py's CanOtaTarget/FlashOptions/etc. imported directly,
        # never duplicated). Two real, separate instances (`urtc_flasher`/
        # `hydra_flasher`, keyed by _FLASHER_TIERS above), each with its
        # own real tier/robot selection/file/log - one dict per bit of
        # state, keyed by nav key, rather than 2 sets of named attributes
        # (same generic-over-nav-key shape as _MODULE_CONFIGS above).
        # `_flasher_is_hardware` is the one real exception - it's a
        # single, GLOBAL deployment setting (HydraState.can_ota_transport),
        # not per-instance. --
        self._flasher_is_hardware = False
        self._flasher_controller: dict[str, ControllerView | None] = {k: None for k in _FLASHER_TIERS}
        self._flasher_robot_id: dict[str, str | None] = {k: None for k in _FLASHER_TIERS}
        self._flasher_tier: dict[str, str] = {k: tiers[0] for k, tiers in _FLASHER_TIERS.items()}
        self._flasher_file: dict[str, dict | None] = {k: None for k in _FLASHER_TIERS}
        self._flasher_gh_assets: dict[str, list] = {k: [] for k in _FLASHER_TIERS}
        self._flasher_gh_busy: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        self._flasher_query_busy: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        self._flasher_flashing: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        self._flasher_progress: dict[str, dict] = {k: {} for k in _FLASHER_TIERS}
        self._flasher_log: dict[str, list[dict]] = {k: [] for k in _FLASHER_TIERS}
        self._flasher_allow_downgrade: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        self._flasher_erase_fram: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        controller.active_state_changed.connect(self._on_flasher_state_changed)

        # -- Tester (ported from tester_panel.py's own TesterPanel -
        # can_ota.py's mock_self_test()/mock_bus_monitor()/CanFrame/
        # SelfTestStep imported directly, never duplicated;
        # _category_for() imported from tester_panel.py itself, same
        # reasoning). Deliberately duplicates the Flasher's own target-
        # selection shape (own _tester_* state dicts, not shared with
        # _flasher_*) - matches that file's own header on why this is a
        # real, faithful duplication rather than a shortcut. Two real
        # instances (`urtc_tester`/`hydra_tester`, _TESTER_TIERS above).
        # Global LED/OLED/F-RAM state is real-but-local here too, same as
        # the classic panel's own plain instance attributes - none of it
        # round-trips through push_active_state() on either side, since
        # no real APPLICATION-level command exists yet to send it
        # anywhere (see that file's own header). --
        self._tester_controller: dict[str, ControllerView | None] = {k: None for k in _TESTER_TIERS}
        self._tester_robot_id: dict[str, str | None] = {k: None for k in _TESTER_TIERS}
        self._tester_tier: dict[str, str] = {k: tiers[0] for k, tiers in _TESTER_TIERS.items()}
        self._tester_status_color: dict[str, str] = {k: "#00ff66" for k in _TESTER_TIERS}
        self._tester_ring_on: dict[str, bool] = {k: False for k in _TESTER_TIERS}
        self._tester_oled_mode: dict[str, str] = {k: "standard" for k in _TESTER_TIERS}
        self._tester_fram_state: dict[str, bool | None] = {k: None for k in _TESTER_TIERS}
        self._tester_testing: dict[str, bool] = {k: False for k in _TESTER_TIERS}
        self._tester_self_test_steps: dict[str, list[dict]] = {k: [] for k in _TESTER_TIERS}
        self._tester_monitor_task: dict[str, asyncio.Task | None] = {k: None for k in _TESTER_TIERS}
        self._tester_frames: dict[str, list] = {k: [] for k in _TESTER_TIERS}
        controller.active_state_changed.connect(self._on_tester_state_changed)

        # -- Viewport (3D, ported from viewport_panel.py's own ViewportPanel)
        # - reuses the SAME real robot selection Robot Control/Trajectory
        # already share (_selected_robot_id/_active_robots_cache/
        # _selected_robot() above) rather than a third independent one -
        # _select_robot()'s own comment already anticipated this. Real
        # rendering happens through render/viewport.py's own
        # OffscreenRobotRenderer, constructed lazily (real GL setup - no
        # reason to pay for it if this panel is never opened), fed to QML
        # through ViewportFrameProvider the same way CameraFrameProvider
        # already feeds live camera frames. --
        self._viewport_renderer = None  # OffscreenRobotRenderer | None, lazy
        self._viewport_render_failed = False
        self._viewport_render_error = ""
        self._viewport_frame_version = 0
        self._viewport_current_model: str | None = None
        controller.active_state_changed.connect(self._on_viewport_state_changed)

    # -- navigation --------------------------------------------------------

    @Property(str, notify=changed)
    def activePanel(self) -> str:
        return self._active_key

    @Property(bool, notify=changed)
    def activePanelMigrated(self) -> bool:
        return self._active_key in MIGRATED_PANELS

    @Slot(str)
    def navigatePanel(self, key: str) -> None:
        if key != self._active_key:
            self._active_key = key
            self.changed.emit()

    @Property("QVariantList", constant=True)
    def rootItems(self) -> list[dict[str, str]]:
        return self._items(ROOT_ITEMS)

    @Property("QVariantList", constant=True)
    def industrialItems(self) -> list[dict[str, str]]:
        return self._items(INDUSTRIAL_ITEMS)

    @Property("QVariantList", constant=True)
    def urtcItems(self) -> list[dict[str, str]]:
        return self._items(URTC_ITEMS)

    @Property("QVariantList", constant=True)
    def hydraumcItems(self) -> list[dict[str, str]]:
        return self._items(HYDRAUMC_ITEMS)

    @Property("QVariantList", constant=True)
    def hydraumcEcosystemItems(self) -> list[dict[str, str]]:
        return self._items(HYDRAUMC_ECOSYSTEM_ITEMS)

    @staticmethod
    def _items(pairs: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
        return [{"label": _(label_key), "key": key, "migrated": key in MIGRATED_PANELS} for label_key, key in pairs]

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def iconSource(self) -> str:
        svg = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        return QUrl.fromLocalFile(str(svg)).toString() if svg.is_file() else ""

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        translated = _(key)
        return translated if translated != key else key

    @Property(str, notify=changed)
    def connectionStatus(self) -> str:
        return self._connection_status

    @Slot(str)
    def _on_connection_status(self, status: str) -> None:
        self._connection_status = status
        self.changed.emit()

    # -- Logs ----------------------------------------------------------

    def _entry_matches_filters(self, entry: _LogEntry) -> bool:
        if self._log_level_filter is not None and entry.level != self._log_level_filter:
            return False
        needle = self._log_search_filter.strip().lower()
        if needle and needle not in entry.message.lower() and needle not in entry.logger_name.lower():
            return False
        return True

    def _on_log_record(self, level: str, logger_name: str, message: str) -> None:
        entry = _LogEntry(level, logger_name, message)
        self._all_log_entries.append(entry)
        if self._entry_matches_filters(entry):
            self._displayed_log_entries.append(entry)
            self._logsChanged.emit()

    @Property("QVariantList", notify=_logsChanged)
    def logEntries(self) -> list[dict[str, str]]:
        return [
            {"level": e.level, "logger": e.logger_name, "message": e.message}
            for e in self._displayed_log_entries[-500:]
        ]

    @Property("QStringList", constant=True)
    def logLevels(self) -> list[str]:
        return [_("LOG_LEVEL_ALL"), *_LOG_LEVELS]

    @Slot(str)
    def setLogLevelFilter(self, level: str) -> None:
        wanted = None if level == _("LOG_LEVEL_ALL") else level
        if wanted != self._log_level_filter:
            self._log_level_filter = wanted
            self._refresh_log_display()

    @Slot(str)
    def setLogSearchFilter(self, text: str) -> None:
        if text != self._log_search_filter:
            self._log_search_filter = text
            self._refresh_log_display()

    def _refresh_log_display(self) -> None:
        self._displayed_log_entries = [e for e in self._all_log_entries if self._entry_matches_filters(e)]
        self._logsChanged.emit()

    @Slot()
    def clearLogs(self) -> None:
        self._all_log_entries.clear()
        self._displayed_log_entries.clear()
        self._logsChanged.emit()

    # -- Servers ---------------------------------------------------------

    @Property("QVariantList", notify=changed)
    def serverRows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        active_id = self._controller._active_id  # same real field server_browser.py's own _refresh_table reads directly
        for conn_id, conn in self._controller.connections.items():
            robot_count = len(conn.state.active_controller.robots) if conn.state.active_controller else conn.info.robot_count
            login = self._server_login.get(conn_id)
            if login is not None and not login[0]:
                status_key = "login_failed"
            else:
                status_key = self._server_statuses.get(conn_id, "connecting")
            rows.append({
                "connId": conn_id,
                "name": conn.info.display_name,
                "hostPort": f"{conn.info.host}:{conn.info.port}",
                "robotCount": robot_count,
                "statusText": _(STATUS_DISPLAY_KEYS.get(status_key, "STATUS_CONNECTING")),
                "loginDetail": login[1] if login is not None and not login[0] else "",
                "active": conn_id == active_id,
            })
        return rows

    @Property(bool, notify=changed)
    def serverScanning(self) -> bool:
        return self._scanning

    @Property(str, notify=changed)
    def serverScanStatus(self) -> str:
        return self._scan_status_text

    @Property(int, constant=True)
    def defaultServerPort(self) -> int:
        return DEFAULT_PORT

    def _on_servers_changed(self) -> None:
        self.changed.emit()

    def _on_server_status(self, conn_id: str, status: str) -> None:
        self._server_statuses[conn_id] = status
        self.changed.emit()

    def _on_server_login(self, conn_id: str, ok: bool, detail: str) -> None:
        self._server_login[conn_id] = (ok, detail)
        self.changed.emit()

    @Slot()
    def scanServers(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._scan_status_text = _("STATUS_SCANNING")
        self.changed.emit()
        asyncio.ensure_future(self._run_server_scan())

    async def _run_server_scan(self) -> None:
        # discover_servers() runs the brute-force subnet scan and real
        # mDNS/Bonjour discovery CONCURRENTLY (net/discovery.py's own
        # header comment) and dedupes between them - same real call
        # server_browser.py's own _run_scan makes, unchanged.
        found = 0
        try:
            async for info in discover_servers():
                found += 1
                self._controller.add_server(info)
                self._scan_status_text = _("STATUS_SCANNING_PROGRESS", found=found)
                self.changed.emit()
        finally:
            self._scanning = False
            self._scan_status_text = _("STATUS_SCAN_COMPLETE", found=found) if found else _("STATUS_SCAN_COMPLETE_NONE")
            self.changed.emit()

    @Slot(str, int, str, str)
    def addManualServer(self, host: str, port: int, username: str, password: str) -> None:
        host = host.strip()
        username = username.strip()
        if not host or not username or not password:
            return
        info = ServerInfo(host=host, port=port, hostname=host, username=username, password=password)
        self._controller.add_server(info)

    @Slot(str)
    def setActiveServer(self, conn_id: str) -> None:
        self._controller.set_active(conn_id)

    @Slot(str)
    def removeServer(self, conn_id: str) -> None:
        self._controller.remove_server(conn_id)

    @Slot(str, result="QVariant")
    def serverCredentials(self, conn_id: str) -> dict[str, str]:
        conn = self._controller.connections.get(conn_id)
        if conn is None:
            return {"username": "", "password": ""}
        return {"username": conn.info.username, "password": conn.info.password}

    @Slot(str, str, str)
    def saveServerCredentials(self, conn_id: str, username: str, password: str) -> None:
        conn = self._controller.connections.get(conn_id)
        if conn is None or not username or not password:
            return
        conn.info.username = username
        conn.info.password = password
        # Credentials just changed - force a clean reconnect rather than
        # waiting for HydraConnection's own retry loop to notice on its
        # own timer, same real reason server_browser.py's own
        # _on_edit_credentials does this.
        asyncio.ensure_future(self._reconnect_server(conn))

    @staticmethod
    async def _reconnect_server(conn) -> None:
        await conn.disconnect()
        await conn.connect()

    # -- Robot Control -----------------------------------------------------

    def _active_robots(self) -> list[RobotView]:
        # Cached from the last real active_state_changed delivery (see
        # _on_robot_state_changed below) rather than re-derived from
        # self._controller.active_state on every call - matches
        # robot_control.py's own real pattern (it caches
        # self._current_robot from the state PARAMETER a signal handler
        # receives, never re-queries the controller independently
        # elsewhere), and avoids a real staleness risk: re-deriving here
        # would only coincidentally agree with what the signal just
        # carried.
        return self._active_robots_cache

    def _selected_robot(self) -> RobotView | None:
        for r in self._active_robots():
            if r.id == self._selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def robotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._active_robots()]

    @Property(str, notify=changed)
    def selectedRobotId(self) -> str:
        return self._selected_robot_id or ""

    @Property(bool, notify=changed)
    def canControlRobot(self) -> bool:
        return self._selected_robot() is not None

    @Property(str, notify=changed)
    def selectedRobotLabel(self) -> str:
        robot = self._selected_robot()
        return _("LBL_ROBOT_SELECTED", id=robot.id, model=robot.model) if robot is not None else _("LBL_NO_ROBOT_SELECTED")

    @Property("QVariantList", notify=changed)
    def selectedRobotJoints(self) -> list[dict[str, object]]:
        robot = self._selected_robot()
        joints = robot.joints if robot is not None else {}
        return [{"name": name, "value": joints.get(name, 0.0)} for name in JOINT_NAMES]

    @Property(int, notify=changed)
    def selectedRobotSpeed(self) -> int:
        robot = self._selected_robot()
        return int(robot.speed) if robot is not None else 100

    @Property(int, notify=changed)
    def selectedRobotAcceleration(self) -> int:
        robot = self._selected_robot()
        return int(robot.acceleration) if robot is not None else 100

    def _on_robot_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._active_robots_cache = robots
        if self._selected_robot_id not in {r.id for r in robots}:
            self._select_robot(robots[0].id if robots else None)
        self.changed.emit()

    @Slot(str)
    def selectRobot(self, robot_id: str) -> None:
        self._select_robot(robot_id or None)
        self.changed.emit()

    def _select_robot(self, new_id: str | None) -> None:
        """The one real place _selected_robot_id ever changes - resets
        the recorded trajectory points exactly like
        trajectory_panel.py's own set_selected_robot does (only on an
        actual robot-identity change, never on every swarm tick a
        continuing selection would otherwise wipe recordings within
        moments of making them). Also the one real place that needs to
        force an immediate Viewport re-render on a selection change -
        matches main_window.py's own real wiring exactly
        (robot_control.robot_selected connects to BOTH
        viewport_panel.set_selected_robot AND
        trajectory_panel.set_selected_robot - a selection change reaches
        the viewport right away, it doesn't wait for the next real state
        tick's own set_joints_deg() call to happen to redraw it)."""
        if new_id == self._selected_robot_id:
            return
        self._selected_robot_id = new_id
        self._trajectory_points = []
        self._trajectoryChanged.emit()
        self._render_viewport_frame()

    @Slot(str, float)
    def setJoint(self, joint_name: str, value: float) -> None:
        robot = self._selected_robot()
        if robot is None or joint_name not in JOINT_NAMES:
            return
        new_joints = dict(robot.joints)
        new_joints[joint_name] = value

        def local_mutate(r: RobotView, joints=new_joints) -> None:
            for name, joint_value in joints.items():
                r.set_joint(name, joint_value)

        # Same real atomic 'jog' command + 50ms debounce as
        # robot_control.py's own _on_joint_changed - see that method's
        # own comment for why a full 6-joint override, debounced, is
        # safe here.
        self._controller.send_robot_command(
            robot.id, "jog",
            {"axis": "x", "amount": 0, "target": "robot", "joints": new_joints},
            local_mutate,
            debounce_ms=50,
        )
        self.changed.emit()

    @Slot(int)
    def setRobotSpeed(self, value: int) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        self._controller.send_robot_command(
            robot.id, "speed", {"speed": value}, lambda r, v=value: r.set_speed(v), debounce_ms=300
        )
        self.changed.emit()

    @Slot(int)
    def setRobotAcceleration(self, value: int) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        self._controller.send_robot_command(
            robot.id, "speed", {"acceleration": value}, lambda r, v=value: r.set_acceleration(v), debounce_ms=300
        )
        self.changed.emit()

    # -- Trajectory --------------------------------------------------------

    @Property("QVariantList", notify=_trajectoryChanged)
    def trajectoryPoints(self) -> list[dict[str, object]]:
        return [
            {"time": p["_time"], "joints": " / ".join(f"{p[name]:.1f}" for name in JOINT_NAMES)}
            for p in self._trajectory_points
        ]

    @Slot()
    def recordTrajectoryPoint(self) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        point: dict[str, object] = dict(robot.joints)
        point["_time"] = time.strftime("%H:%M:%S")
        self._trajectory_points.append(point)
        self._trajectoryChanged.emit()

    @Slot(int)
    def applyTrajectoryPoint(self, index: int) -> None:
        robot = self._selected_robot()
        if robot is None or not 0 <= index < len(self._trajectory_points):
            return
        point = self._trajectory_points[index]
        for name in JOINT_NAMES:
            robot.set_joint(name, point[name])
        self._controller.push_active_state()

    @Slot(int)
    def deleteTrajectoryPoint(self, index: int) -> None:
        if 0 <= index < len(self._trajectory_points):
            del self._trajectory_points[index]
            self._trajectoryChanged.emit()

    # -- AI Family Status --------------------------------------------------

    @Property(str, notify=changed)
    def aiFamilyStatusText(self) -> str:
        return self._ai_family_status_text

    @Property(bool, notify=changed)
    def aiFamilyRefreshing(self) -> bool:
        return self._ai_family_refreshing

    @Property("QVariantList", notify=changed)
    def aiFamilyGroups(self) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        for family, device_key, device_label in AI_FAMILIES:
            items = [p for p in self._ai_family_projects if p.get("family") == family]
            live_count = sum(1 for p in items if p.get("live") is True)
            configured = self._ai_family_ai_hailo.get("visionDevice" if device_key == "hailo8" else "cognitiveDevice", "none")
            title = _("LBL_AI_FAMILY_VISION", device=device_label) if device_key == "hailo8" else _("LBL_AI_FAMILY_COGNITIVE", device=device_label)
            groups.append({
                "title": title,
                "devicePill": _("LBL_NONE_DEVICE") if configured == "none" else device_label,
                "deviceConfigured": configured != "none",
                "countText": _("LBL_AI_FAMILY_LIVE_COUNT", live=live_count, total=len(items)),
                "mismatchWarning": _("MSG_AI_FAMILY_DEVICE_MISMATCH", family=family, device=device_label) if live_count > 0 and configured == "none" else "",
                "projects": [
                    {
                        "name": str(p.get("name") or "-"),
                        "meta": f"{p.get('role') or '-'} · v{p.get('version') or '-'}",
                        "statusText": _("STATUS_ES_LIVE") if p.get("live") is True else (_("STATUS_ES_DEAD") if p.get("live") is False else _("STATUS_ES_NA")),
                        "live": p.get("live"),
                    }
                    for p in items
                ],
            })
        return groups

    @Slot()
    def refreshAiFamily(self) -> None:
        asyncio.ensure_future(self._refresh_ai_family())

    async def _refresh_ai_family(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._ai_family_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        self._ai_family_refreshing = True
        self.changed.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._ai_family_refreshing = False
        if result is None:
            self._ai_family_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict) or not body.get("available"):
            self._ai_family_status_text = _("MSG_ES_UNAVAILABLE")
            self.changed.emit()
            return
        self._ai_family_status_text = ""
        families = {f for f, _dev, _label in AI_FAMILIES}
        self._ai_family_projects = [p for p in (body.get("projects") or []) if p.get("family") in families]
        self._ai_family_ai_hailo = conn.state.ai_hailo
        self.changed.emit()

    # -- Admin Clients -----------------------------------------------------

    @Property(str, notify=changed)
    def adminClientsStatusText(self) -> str:
        return self._admin_clients_status_text

    @Property(bool, notify=changed)
    def adminClientsShowStats(self) -> bool:
        return len(self._admin_clients) > 0

    @Property(int, notify=changed)
    def adminClientsConnectedCount(self) -> int:
        return len(self._admin_clients)

    @Property(int, notify=changed)
    def adminClientsAdminCount(self) -> int:
        return sum(1 for c in self._admin_clients if c.get("role") == "admin")

    @Property("QVariantList", notify=changed)
    def adminClientsRows(self) -> list[dict[str, object]]:
        sorted_clients = sorted(
            self._admin_clients,
            key=lambda c: (c.get("role") != "admin", str(c.get("username") or "")),
        )
        return [
            {
                "username": str(c.get("username") or _("LBL_CLIENT_UNKNOWN")),
                "address": str(c.get("remoteAddress") or "-"),
                "isAdmin": c.get("role") == "admin",
                "roleLabel": str(c.get("role") or "?").upper(),
                "duration": _relative_duration(c.get("connectedAt")),
                "connected": bool(c.get("connected")),
            }
            for c in sorted_clients
        ]

    async def _refresh_admin_clients(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._admin_clients_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self._admin_clients = []
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_clients_status_text = _("MSG_ADMIN_ONLY")
            self._admin_clients = []
            self.changed.emit()
            return
        result = await conn.fetch_admin_clients()
        if result is None:
            self._admin_clients_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_clients_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_clients = body.get("clients") or []
        self._admin_clients_status_text = _("LBL_CLIENTS_REFRESH_NOTE", seconds=_ADMIN_CLIENTS_POLL_MS // 1000)
        self.changed.emit()

    # -- Admin Logs --------------------------------------------------------

    @Property(str, notify=changed)
    def adminLogsStatusText(self) -> str:
        return self._admin_logs_status_text

    @Property(bool, notify=changed)
    def adminLogsLive(self) -> bool:
        return self._admin_logs_live

    @Property(str, notify=changed)
    def adminLogsTagFilter(self) -> str:
        return self._admin_logs_tag_filter or ""

    @Property("QStringList", notify=changed)
    def adminLogsTags(self) -> list[str]:
        return sorted({tag for line in self._admin_logs_all_lines if (tag := _extract_tag(line))})

    def _admin_logs_displayed_lines(self) -> list[str]:
        if not self._admin_logs_cleared_at_empty and self._admin_logs_cleared_anchor is None:
            return self._admin_logs_all_lines
        if self._admin_logs_cleared_at_empty:
            return self._admin_logs_all_lines
        try:
            idx = len(self._admin_logs_all_lines) - 1 - self._admin_logs_all_lines[::-1].index(self._admin_logs_cleared_anchor)
        except ValueError:
            # Anchor scrolled off the server's own LINES-line window - show
            # everything rather than hide real content, same real reason
            # admin_logs_panel.py's own _displayed_lines does.
            return self._admin_logs_all_lines
        return self._admin_logs_all_lines[idx + 1:]

    @Property("QStringList", notify=changed)
    def adminLogsLines(self) -> list[str]:
        displayed = self._admin_logs_displayed_lines()
        needle = self._admin_logs_search.strip().lower()
        filtered = [
            line for line in displayed
            if (self._admin_logs_tag_filter is None or _extract_tag(line) == self._admin_logs_tag_filter)
            and (not needle or needle in line.lower())
        ]
        if not filtered:
            return [_("MSG_LOGS_NONE") if not displayed else _("LOGS_NO_MATCH")]
        return filtered

    @Slot()
    def toggleAdminLogsLive(self) -> None:
        self._admin_logs_live = not self._admin_logs_live
        self.changed.emit()

    @Slot()
    def clearAdminLogs(self) -> None:
        if self._admin_logs_all_lines:
            self._admin_logs_cleared_anchor = self._admin_logs_all_lines[-1]
            self._admin_logs_cleared_at_empty = False
        else:
            self._admin_logs_cleared_anchor = None
            self._admin_logs_cleared_at_empty = True
        self.changed.emit()

    @Slot(str)
    def setAdminLogsTagFilter(self, tag: str) -> None:
        self._admin_logs_tag_filter = tag or None
        self.changed.emit()

    @Slot(str)
    def setAdminLogsSearch(self, text: str) -> None:
        self._admin_logs_search = text
        self.changed.emit()

    async def _refresh_admin_logs(self) -> None:
        if not self._admin_logs_live:
            return
        conn = self._controller.active_connection
        if conn is None:
            self._admin_logs_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
            self._admin_logs_all_lines = []
            self.changed.emit()
            return
        result = await conn.fetch_admin_logs(_ADMIN_LOGS_LINES)
        if result is None:
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_logs_all_lines = body.get("lines") or []
        self._admin_logs_status_text = _("LBL_LOGS_FOOTER_LIVE", lines=_ADMIN_LOGS_LINES, seconds=_ADMIN_LOGS_POLL_MS // 1000)
        self.changed.emit()

    # -- Admin Server ------------------------------------------------------

    @Property(str, notify=changed)
    def adminServerStatusText(self) -> str:
        return self._admin_server_status_text

    @Property(bool, notify=changed)
    def adminServerInfoVisible(self) -> bool:
        return bool(self._admin_server_info)

    @Property(str, notify=changed)
    def adminServerProduct(self) -> str:
        return str(self._admin_server_info.get("product") or "-")

    @Property(str, notify=changed)
    def adminServerVersion(self) -> str:
        version = self._admin_server_info.get("appVersion")
        return f"v{version}" if version else "-"

    @Property(str, notify=changed)
    def adminServerUptime(self) -> str:
        return _format_uptime(self._admin_server_info.get("uptimeSeconds"))

    @Property(str, notify=changed)
    def adminServerControllerCount(self) -> str:
        return str(self._admin_server_info.get("controllerCount", "-"))

    @Property(str, notify=changed)
    def adminServerRobotCount(self) -> str:
        return str(self._admin_server_info.get("robotCount", "-"))

    @Property(str, notify=changed)
    def adminServerHost(self) -> str:
        return str(self._admin_server_info.get("hostname") or "-")

    @Property(str, notify=changed)
    def adminServerPortLabel(self) -> str:
        port = self._admin_server_current_port if self._admin_server_current_port is not None else "..."
        return _("LBL_ADMIN_SERVER_PORT_CURRENT", port=port)

    @Property(str, notify=changed)
    def adminServerPendingPortText(self) -> str:
        return self._admin_server_pending_port_text

    async def _refresh_admin_server(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._admin_server_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_server_status_text = _("MSG_ADMIN_ONLY")
            self.changed.emit()
            return
        result = await conn.fetch_admin_server_config()
        if result is None:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = ""
        self._admin_server_current_port = body.get("port")
        pending = body.get("pendingPort")
        self._admin_server_pending_port_text = str(pending if pending is not None else self._admin_server_current_port or "")

        info_result = await conn.fetch_hydra_info()
        if info_result is not None:
            info_status, info_body = info_result
            if info_status == 200 and isinstance(info_body, dict):
                self._admin_server_info = info_body
        self.changed.emit()

    @Slot(str)
    def saveAdminServerPort(self, text: str) -> None:
        asyncio.ensure_future(self._save_admin_server_port(text))

    async def _save_admin_server_port(self, text: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        try:
            port = int(text)
        except ValueError:
            self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_INVALID")
            self.changed.emit()
            return
        if not (1 <= port <= 65535):
            self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_INVALID")
            self.changed.emit()
            return
        result = await conn.save_admin_server_port(port)
        if result is None or result[0] != 200:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_SAVED")
        self.changed.emit()

    @Slot()
    def restartAdminServer(self) -> None:
        asyncio.ensure_future(self._restart_admin_server())

    async def _restart_admin_server(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.restart_server()
        if result is None or result[0] != 200:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_RESTART_REQUESTED")
        self.changed.emit()

    # -- Ecosystem Services --------------------------------------------------

    @Property(str, notify=changed)
    def esStatusText(self) -> str:
        return self._es_status_text

    @Property(bool, notify=changed)
    def esRefreshing(self) -> bool:
        return self._es_refreshing

    @Property(str, notify=changed)
    def esFamilyFilter(self) -> str:
        return self._es_family_filter or ""

    @Property("QStringList", notify=changed)
    def esFamilies(self) -> list[str]:
        return sorted({p.get("family") for p in self._es_projects if p.get("family")})

    @Property(bool, notify=changed)
    def esShowStats(self) -> bool:
        return len(self._es_projects) > 0

    @Property("QVariantMap", notify=changed)
    def esStats(self) -> dict[str, int]:
        return {
            "total": len(self._es_projects),
            "live": sum(1 for p in self._es_projects if p.get("live") is True),
            "families": len({p.get("family") for p in self._es_projects if p.get("family")}),
            "running": sum(1 for p in self._es_projects if _health(p) == "green"),
            "stopped": sum(1 for p in self._es_projects if _health(p) == "red"),
            "error": sum(1 for p in self._es_projects if _health(p) == "amber"),
            "na": sum(1 for p in self._es_projects if _health(p) == "slate"),
        }

    @Property("QVariantList", notify=changed)
    def esGroups(self) -> list[dict[str, object]]:
        needle = self._es_search.strip().lower()
        filtered = [
            p for p in self._es_projects
            if (self._es_family_filter is None or p.get("family") == self._es_family_filter)
            and (not needle or needle in str(p.get("name", "")).lower())
        ]
        grouped: dict[str, list[dict]] = {}
        for p in filtered:
            key = p.get("family") or _("SERVICES_NO_FAMILY")
            grouped.setdefault(key, []).append(p)

        conn = self._controller.active_connection
        is_admin = conn is not None and conn.is_admin
        groups = []
        for family in sorted(grouped.keys()):
            items = grouped[family]
            cards = []
            for p in items:
                health = _health(p)
                unit = p.get("systemdUnit")
                error = self._es_action_error if self._es_action_error is not None and self._es_action_error[0] == unit else None
                health_color = _HEALTH_COLOR[health]
                cards.append({
                    "name": str(p.get("name") or "-"),
                    "badgeText": _badge_label(p),
                    "healthColor": health_color,
                    "healthColorBg": _with_alpha(health_color, 0.13),
                    "healthColorBorder": _with_alpha(health_color, 0.33),
                    "version": f"v{p.get('version')}" if p.get("version") else "",
                    "stack": p.get("stack") or "",
                    "stackColor": _STACK_COLOR.get(p.get("stack"), "#7f8ea1"),
                    "maturity": p.get("maturity") or "",
                    "hostPort": f"{p.get('serviceHost')}:{p.get('servicePort')}" if p.get("serviceHost") else "",
                    "pidText": f"{_('LBL_SERVICES_PID')} {p.get('pid')}" if p.get("pid") is not None else "",
                    "canControl": bool(is_admin and unit),
                    "unit": unit or "",
                    "actioning": self._es_actioning_unit == unit,
                    "errorText": error[1] if error is not None else "",
                })
            groups.append({"family": family, "count": len(items), "cards": cards})
        return groups

    @Slot()
    def refreshEcosystemServices(self) -> None:
        asyncio.ensure_future(self._refresh_ecosystem_services())

    async def _refresh_ecosystem_services(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._es_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        self._es_refreshing = True
        self.changed.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._es_refreshing = False
        if result is None:
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        if not body.get("available"):
            self._es_status_text = _("MSG_ES_UNAVAILABLE")
            self._es_projects = []
            self.changed.emit()
            return
        self._es_projects = body.get("projects") or []
        self._es_status_text = _("LBL_ES_SCANNED_AT", time=body.get("scannedAt") or "-")
        self.changed.emit()

    @Slot(str)
    def setEsFamilyFilter(self, family: str) -> None:
        self._es_family_filter = family or None
        self.changed.emit()

    @Slot(str)
    def setEsSearch(self, text: str) -> None:
        self._es_search = text
        self.changed.emit()

    @Slot(str, str)
    def runEsServiceAction(self, unit: str, action: str) -> None:
        asyncio.ensure_future(self._run_es_service_action(unit, action))

    async def _run_es_service_action(self, unit: str, action: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        self._es_actioning_unit = unit
        self._es_action_error = None
        self.changed.emit()
        try:
            result = await conn.control_service(unit, action)
        finally:
            self._es_actioning_unit = None
        if result is None:
            self._es_action_error = (unit, _("MSG_SERVICES_ACTION_ERROR"))
            self.changed.emit()
            return
        status, body = result
        if status != 200:
            message = body.get("error") if isinstance(body, dict) else None
            self._es_action_error = (unit, message or f"HTTP {status}")
            self.changed.emit()
            return
        await self._refresh_ecosystem_services()

    # -- Ecosystem Telemetry -------------------------------------------------

    @Property(str, notify=changed)
    def telemetryStatusText(self) -> str:
        return self._tel_status_text

    @Property(bool, notify=changed)
    def telemetryRunning(self) -> bool:
        return self._tel_running

    @Property("QStringList", constant=True)
    def telemetryAggregates(self) -> list[str]:
        return list(_AGGREGATES)

    @Property("QVariantList", constant=True)
    def telemetryRangePresets(self) -> list[dict[str, object]]:
        return [{"label": label, "ms": ms} for label, ms in _RANGE_PRESETS]

    @Property(bool, notify=changed)
    def telemetryShowStats(self) -> bool:
        return bool(self._tel_stats)

    @Property("QVariantMap", notify=changed)
    def telemetryStats(self) -> dict[str, str]:
        return self._tel_stats

    @Property(str, notify=changed)
    def telemetryChartMode(self) -> str:
        return self._tel_chart_mode

    @Property("QVariantList", notify=changed)
    def telemetryLinePoints(self) -> list[dict[str, float]]:
        return self._tel_line_points

    @Property("QVariantList", notify=changed)
    def telemetryBars(self) -> list[dict[str, object]]:
        return self._tel_bars

    @Slot(str, str, str, str, str, str, str, str)
    def runTelemetryQuery(
        self, mode: str, source_id: str, kind: str, field: str,
        start: str, end: str, bucket_ms: str, agg: str,
    ) -> None:
        asyncio.ensure_future(self._run_telemetry_query(mode, source_id, kind, field, start, end, bucket_ms, agg))

    async def _run_telemetry_query(
        self, mode: str, source_id: str, kind: str, field: str,
        start: str, end: str, bucket_ms: str, agg: str,
    ) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._tel_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        is_aggregate = mode == "aggregate"
        params: dict[str, str] = {}
        if source_id:
            params["sourceId"] = source_id
        if kind:
            params["kind"] = kind
        if field:
            params["field"] = field
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        self._tel_running = True
        self.changed.emit()
        try:
            if is_aggregate:
                if not (kind and field and start and end):
                    self._tel_status_text = _("MSG_TELEMETRY_AGGREGATE_MISSING_FIELDS")
                    return
                params["bucketMs"] = bucket_ms
                params["agg"] = agg
                result = await conn.fetch_telemetry_aggregate(params)
            else:
                result = await conn.fetch_telemetry_query(params)
        finally:
            self._tel_running = False
            self.changed.emit()

        if result is None:
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status == 503 and isinstance(body, dict) and body.get("available") is False:
            self._tel_status_text = _("MSG_TELEMETRY_NOT_CONFIGURED")
            self._render_empty_telemetry_chart()
            self._update_telemetry_stats([])
            self.changed.emit()
            return
        if status != 200 or not isinstance(body, list):
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.changed.emit()
            return

        self._tel_status_text = "" if body else _("MSG_TELEMETRY_NO_DATA")
        if is_aggregate:
            self._render_telemetry_bar_chart(body)
            self._update_telemetry_stats([float(b.get("value", 0)) for b in body])
        else:
            self._render_telemetry_line_chart(body)
            self._update_telemetry_stats([float(p.get("value", 0)) for p in body])
        self.changed.emit()

    def _render_empty_telemetry_chart(self) -> None:
        self._tel_chart_mode = "empty"
        self._tel_line_points = []
        self._tel_bars = []

    def _render_telemetry_line_chart(self, points: list[dict]) -> None:
        if not points:
            self._render_empty_telemetry_chart()
            return
        self._tel_chart_mode = "line"
        self._tel_bars = []
        timestamps = [float(p.get("timestamp", 0)) for p in points]
        values = [float(p.get("value", 0)) for p in points]
        t_min, t_max = min(timestamps), max(timestamps)
        v_min, v_max = min(values), max(values)
        t_span = (t_max - t_min) or 1.0
        v_span = (v_max - v_min) or 1.0
        self._tel_line_points = [
            {
                "nx": (t - t_min) / t_span,
                "ny": (v - v_min) / v_span if v_max != v_min else 0.5,
            }
            for t, v in zip(timestamps, values)
        ]

    def _render_telemetry_bar_chart(self, buckets: list[dict]) -> None:
        if not buckets:
            self._render_empty_telemetry_chart()
            return
        self._tel_chart_mode = "bar"
        self._tel_line_points = []
        values = [float(b.get("value", 0)) for b in buckets]
        v_max = max(values) or 1.0
        self._tel_bars = [
            {
                "nh": (v / v_max) if v_max else 0.0,
                "label": QDateTime.fromMSecsSinceEpoch(int(b.get("bucketStart", 0))).toString("HH:mm"),
            }
            for v, b in zip(values, buckets)
        ]

    def _update_telemetry_stats(self, values: list[float]) -> None:
        if not values:
            self._tel_stats = {}
            return
        self._tel_stats = {
            "min": f"{min(values):.2f}",
            "max": f"{max(values):.2f}",
            "avg": f"{sum(values) / len(values):.2f}",
            "count": str(len(values)),
        }

    # -- XY Table ------------------------------------------------------------

    def _on_xy_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._xy_robots_cache = robots
        if self._xy_selected_robot_id not in {r.id for r in robots}:
            self._xy_selected_robot_id = robots[0].id if robots else None
        self.changed.emit()

    def _xy_selected_robot(self) -> RobotView | None:
        for r in self._xy_robots_cache:
            if r.id == self._xy_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def xyRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._xy_robots_cache]

    @Property(str, notify=changed)
    def xySelectedRobotId(self) -> str:
        return self._xy_selected_robot_id or ""

    @Slot(str)
    def selectXyRobot(self, robot_id: str) -> None:
        if robot_id != self._xy_selected_robot_id:
            self._xy_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property(bool, notify=changed)
    def xyHasRobot(self) -> bool:
        return self._xy_selected_robot() is not None

    @Property(bool, notify=changed)
    def xyHasTable(self) -> bool:
        robot = self._xy_selected_robot()
        return robot is not None and robot.has_xy_table

    @Property(bool, notify=changed)
    def xyCanReset(self) -> bool:
        return self.xyHasRobot and self.xyHasTable

    @Property(int, notify=changed)
    def xyWidth(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("width", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(int, notify=changed)
    def xyLength(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("length", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(str, notify=changed)
    def xyPosX(self) -> str:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        pos = table["pos"] if table else {"x": 0, "y": 0}
        return f"{float(pos.get('x', 0)):.2f}"

    @Property(str, notify=changed)
    def xyPosY(self) -> str:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        pos = table["pos"] if table else {"x": 0, "y": 0}
        return f"{float(pos.get('y', 0)):.2f}"

    @Property("QVariantList", constant=True)
    def xyJogSteps(self) -> list[float]:
        return list(_XY_JOG_STEPS_MM)

    @Slot(float)
    def setXyJogStep(self, value: float) -> None:
        self._xy_jog_step_mm = value

    @Slot()
    def enableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        # Matches XYTableConfig.tsx's own handleAddTable() exactly: only
        # the flag, no xyTable block yet - see xy_table_panel.py's own
        # header for why.
        robot.set_has_xy_table(True)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        robot.set_has_xy_table(False)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        robot.set_xy_table(_default_xy_table())
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def setXyWidth(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return  # matches XYTableConfig.tsx's own handleSizeChange() no-op guard
        table["tableSize"]["width"] = value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def setXyLength(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return
        table["tableSize"]["length"] = value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, int)
    def jogXyTable(self, axis: str, direction: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None or axis not in ("x", "y"):
            return
        table = robot.xy_table
        if not table:
            return  # matches XYTableConfig.tsx's own handleJog() no-op guard
        new_value = table["pos"][axis] + direction * self._xy_jog_step_mm
        bound = table["tableSize"]["width" if axis == "x" else "length"]
        new_value = max(0.0, min(new_value, float(bound)))
        table["pos"][axis] = new_value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str)
    def saveXyTableConfig(self, path: str) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path:
            return
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)

    # -- Rack Manager ----------------------------------------------------

    def _on_rack_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._rack_robots_cache = robots
        if self._rack_selected_robot_id not in {r.id for r in robots}:
            self._rack_selected_robot_id = robots[0].id if robots else None
        self.changed.emit()

    def _rack_selected_robot(self) -> RobotView | None:
        for r in self._rack_robots_cache:
            if r.id == self._rack_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def rackRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._rack_robots_cache]

    @Property(str, notify=changed)
    def rackSelectedRobotId(self) -> str:
        return self._rack_selected_robot_id or ""

    @Slot(str)
    def selectRackRobot(self, robot_id: str) -> None:
        if robot_id != self._rack_selected_robot_id:
            self._rack_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property(bool, notify=changed)
    def rackHasRobot(self) -> bool:
        return self._rack_selected_robot() is not None

    @Property(bool, notify=changed)
    def rackEnabled(self) -> bool:
        robot = self._rack_selected_robot()
        return robot is not None and bool(robot.rack_system.get("enabled"))

    @Property("QStringList", constant=True)
    def rackTypeOptions(self) -> list[str]:
        return ["None", "Input", "Output"]

    @Property("QStringList", constant=True)
    def rackTypeLabels(self) -> list[str]:
        return [_("LBL_DISABLED"), _("LBL_INPUT_RACK"), _("LBL_OUTPUT_RACK")]

    @Property("QVariantList", notify=changed)
    def rackData(self) -> list[dict[str, object]]:
        robot = self._rack_selected_robot()
        if robot is None or not robot.rack_system.get("enabled"):
            return []
        config = robot.rack_system
        has_xy_table = robot.has_xy_table
        result = []
        for rack_id, title_key in (("rack1", "LBL_RACK1"), ("rack2", "LBL_RACK2")):
            rack = config[rack_id]
            rack_type = rack.get("type", "None")
            active = rack_type != "None"
            capacity = int(rack.get("capacity", RACK_MAX_CAPACITY))
            usable_slots = rack.get("usableSlots", [])
            pos = rack.get("basePickupPos", {})
            result.append({
                "rackId": rack_id,
                "title": _(title_key),
                "type": rack_type,
                "active": active,
                "capacity": capacity,
                "maxCapacity": RACK_MAX_CAPACITY,
                "slots": [bool(usable_slots[i]) if i < len(usable_slots) else False for i in range(capacity)],
                "pos": {field: float(pos.get(field, 0)) for field in _RACK_POS_FIELDS},
                "showTable": has_xy_table,
            })
        return result

    @Slot()
    def enableRackSystem(self) -> None:
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = robot.rack_system
        config["enabled"] = True
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disableRackSystem(self) -> None:
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = robot.rack_system
        config["enabled"] = False
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetRackSystem(self) -> None:
        # Matches RackConfigView.tsx's own real handleReset() exactly:
        # BOTH racks reset, regardless of which rack's own Reset button
        # was clicked - see rack_config_panel.py's own header for why
        # this is a real, deliberately-preserved quirk, not a bug
        # introduced here.
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = default_rack_system()
        config["enabled"] = True
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, str)
    def setRackType(self, rack_id: str, rack_type: str) -> None:
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = robot.rack_system
        config[rack_id]["type"] = rack_type
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, int)
    def setRackCapacity(self, rack_id: str, value: int) -> None:
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = robot.rack_system
        config[rack_id]["capacity"] = value
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, str, float)
    def setRackPos(self, rack_id: str, field: str, value: float) -> None:
        robot = self._rack_selected_robot()
        if robot is None or field not in _RACK_POS_FIELDS:
            return
        config = robot.rack_system
        config[rack_id].setdefault("basePickupPos", {})[field] = value
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, int)
    def toggleRackSlot(self, rack_id: str, index: int) -> None:
        robot = self._rack_selected_robot()
        if robot is None:
            return
        config = robot.rack_system
        rack = config[rack_id]
        slots = list(rack.get("usableSlots", []))
        while len(slots) <= index:
            slots.append(False)
        slots[index] = not slots[index]
        rack["usableSlots"] = slots
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    # -- Pick and Place ----------------------------------------------------

    def _on_pnp_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._pnp_robots_cache = robots
        if self._pnp_selected_robot_id not in {r.id for r in robots}:
            self._pnp_selected_robot_id = robots[0].id if robots else None
        self.changed.emit()

    def _pnp_selected_robot(self) -> RobotView | None:
        for r in self._pnp_robots_cache:
            if r.id == self._pnp_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def pnpRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._pnp_robots_cache]

    @Property(str, notify=changed)
    def pnpSelectedRobotId(self) -> str:
        return self._pnp_selected_robot_id or ""

    @Slot(str)
    def selectPnpRobot(self, robot_id: str) -> None:
        if robot_id != self._pnp_selected_robot_id:
            self._pnp_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property("QVariantList", constant=True)
    def pnpMachineOptions(self) -> list[dict[str, str]]:
        return [{"key": key, "label": MACHINE_LABELS[key]} for key in MACHINE_TYPES]

    @Property(str, notify=changed)
    def pnpMachineType(self) -> str:
        return self._pnp_machine_type

    @Property(str, notify=changed)
    def pnpMachineLabel(self) -> str:
        return MACHINE_LABELS.get(self._pnp_machine_type, self._pnp_machine_type)

    @Slot(str)
    def selectPnpMachine(self, machine_type: str) -> None:
        if machine_type != self._pnp_machine_type and machine_type in MACHINE_TYPES:
            self._pnp_machine_type = machine_type
            self.changed.emit()

    @Property(bool, notify=changed)
    def pnpHasRobot(self) -> bool:
        return self._pnp_selected_robot() is not None

    @Property(bool, notify=changed)
    def pnpEnabled(self) -> bool:
        robot = self._pnp_selected_robot()
        return robot is not None and robot.module_enabled(self._pnp_machine_type)

    @Property(bool, notify=changed)
    def pnpCanReset(self) -> bool:
        return self.pnpHasRobot and self.pnpEnabled

    @Property("QVariantList", notify=changed)
    def pnpAxisData(self) -> list[dict[str, object]]:
        """One row per PNP_AXES entry, spec + current value fused - same
        real fixed hardware bounds as pick_and_place_panel.py's own
        PNP_AXES (never re-declared here)."""
        robot = self._pnp_selected_robot()
        module = robot.module(self._pnp_machine_type) if robot is not None else {}
        return [
            {"field": field, "label": _(label_key), "min": lo, "max": hi, "value": int(module.get(field, 0) or 0)}
            for field, label_key, lo, hi in PNP_AXES
        ]

    @Slot()
    def enablePnp(self) -> None:
        robot = self._pnp_selected_robot()
        if robot is None:
            return
        module = robot.module(self._pnp_machine_type)
        module["enabled"] = True
        robot.set_module(self._pnp_machine_type, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disablePnp(self) -> None:
        robot = self._pnp_selected_robot()
        if robot is None:
            return
        module = robot.module(self._pnp_machine_type)
        module["enabled"] = False
        robot.set_module(self._pnp_machine_type, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetPnp(self) -> None:
        """Matches pick_and_place_panel.py's own _on_reset() exactly -
        always seeds the real PnP axis fields, since the Machine combo
        only ever offers juanenPnP/lumenPnP (see this class's own
        __init__ comment on the unported size-only branch)."""
        robot = self._pnp_selected_robot()
        if robot is None:
            return
        module = {
            "enabled": True,
            "size": {"width": 500, "length": 500},
            "worldPos": {"x": 0, "y": 0},
            "worldRot": 0,
            "renderScale": 1,
            "axisX": 0, "axisY": 0, "axisZ": 0, "nozzle1Rotation": 0, "nozzle2Rotation": 0,
        }
        robot.set_module(self._pnp_machine_type, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, int)
    def setPnpAxis(self, field: str, value: int) -> None:
        robot = self._pnp_selected_robot()
        if robot is None:
            return
        module = robot.module(self._pnp_machine_type)
        module[field] = value
        robot.set_module(self._pnp_machine_type, module)
        self._controller.push_active_state()
        self.changed.emit()

    # -- Kinematic Brain Stage -----------------------------------------------

    def _on_kbs_state_changed(self, state: HydraState) -> None:
        self._kbs_controller = state.active_controller
        self.changed.emit()

    def _kbs_stage(self) -> dict:
        return self._kbs_controller.kinematic_brain_stage if self._kbs_controller is not None else {}

    def _kbs_patch(self, updates: dict) -> None:
        """Matches kinematic_brain_stage_panel.py's own _patch() exactly -
        one real write path for every control in this panel."""
        if self._kbs_controller is None:
            return
        stage = self._kbs_controller.kinematic_brain_stage
        stage.update(updates)
        self._kbs_controller.set_kinematic_brain_stage(stage)
        self._controller.push_active_state()
        self.changed.emit()

    @Property(bool, notify=changed)
    def kbsHasController(self) -> bool:
        return self._kbs_controller is not None

    @Property("QVariantList", notify=changed)
    def kbsAxisData(self) -> list[dict[str, str]]:
        xy = self._kbs_stage().get("xyTable", {})
        return [{"axis": axis, "label": axis.upper(), "value": f"{float(xy.get(axis, 0)):.2f}"} for axis in _KBS_AXIS_KEYS]

    @Property("QVariantList", constant=True)
    def kbsJogSteps(self) -> list[float]:
        return list(_KBS_JOG_STEPS_MM)

    @Slot(float)
    def setKbsJogStep(self, value: float) -> None:
        self._kbs_jog_step_mm = value

    @Slot(str, int)
    def jogKbsAxis(self, axis: str, direction: int) -> None:
        if self._kbs_controller is None or axis not in _KBS_AXIS_KEYS:
            return
        stage = self._kbs_controller.kinematic_brain_stage
        xy = stage["xyTable"]
        next_value = xy[axis] + direction * self._kbs_jog_step_mm
        bound = xy["tableSize"]["height"] if axis == "z" else xy["tableSize"]["width" if axis == "x" else "length"]
        xy[axis] = _clamp(next_value, 0, float(bound))
        self._kbs_patch({"xyTable": xy})

    @Property(int, notify=changed)
    def kbsTableWidth(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("width", 0))

    @Property(int, notify=changed)
    def kbsTableLength(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("length", 0))

    @Property(int, notify=changed)
    def kbsTableHeight(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("height", 0))

    @Slot(str, int)
    def setKbsTableSize(self, field: str, value: int) -> None:
        bounds = {"width": (100, 5000), "length": (100, 5000), "height": (10, 1000)}
        if self._kbs_controller is None or field not in bounds:
            return
        stage = self._kbs_controller.kinematic_brain_stage
        lo, hi = bounds[field]
        stage["xyTable"]["tableSize"][field] = _clamp(value, lo, hi)
        self._kbs_patch({"xyTable": stage["xyTable"]})

    @Property(str, notify=changed)
    def kbsTherm1(self) -> str:
        return f"{float(self._kbs_stage().get('heatedBed', {}).get('currentTemp1', 0)):.1f}°C"

    @Property(str, notify=changed)
    def kbsTherm2(self) -> str:
        return f"{float(self._kbs_stage().get('heatedBed', {}).get('currentTemp2', 0)):.1f}°C"

    @Property(int, notify=changed)
    def kbsTargetTemp(self) -> int:
        return int(self._kbs_stage().get("heatedBed", {}).get("targetTemp", 0))

    @Slot(int)
    def setKbsTargetTemp(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        bed = self._kbs_controller.kinematic_brain_stage["heatedBed"]
        bed["targetTemp"] = _clamp(value, 0, 150)
        self._kbs_patch({"heatedBed": bed})

    @Property(bool, notify=changed)
    def kbsSsrOn(self) -> bool:
        return bool(self._kbs_stage().get("heatedBed", {}).get("ssrActive"))

    @Slot()
    def toggleKbsSsr(self) -> None:
        if self._kbs_controller is None:
            return
        bed = self._kbs_controller.kinematic_brain_stage["heatedBed"]
        bed["ssrActive"] = not bed.get("ssrActive")
        self._kbs_patch({"heatedBed": bed})

    @Property(int, notify=changed)
    def kbsAtcIndex(self) -> int:
        return int(self._kbs_stage().get("atcRevolver", {}).get("currentIndex", 0)) + 1

    @Property(int, notify=changed)
    def kbsToolCount(self) -> int:
        return int(self._kbs_stage().get("atcRevolver", {}).get("toolCount", 6))

    @Property(bool, notify=changed)
    def kbsHomed(self) -> bool:
        return bool(self._kbs_stage().get("atcRevolver", {}).get("homed"))

    @Slot(int)
    def stepKbsAtc(self, direction: int) -> None:
        if self._kbs_controller is None:
            return
        atc = self._kbs_controller.kinematic_brain_stage["atcRevolver"]
        n = atc["toolCount"]
        next_index = (atc["targetIndex"] + direction) % n
        if next_index < 0:
            next_index += n
        atc["targetIndex"] = next_index
        atc["currentIndex"] = next_index
        atc["homed"] = True
        self._kbs_patch({"atcRevolver": atc})

    @Slot(int)
    def setKbsToolCount(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        atc = self._kbs_controller.kinematic_brain_stage["atcRevolver"]
        atc["toolCount"] = _clamp(value, 2, 16)
        self._kbs_patch({"atcRevolver": atc})

    @Property(bool, notify=changed)
    def kbsConveyorInstalled(self) -> bool:
        return bool(self._kbs_stage().get("conveyor", {}).get("installed"))

    @Property(bool, notify=changed)
    def kbsConveyorRunning(self) -> bool:
        return bool(self._kbs_stage().get("conveyor", {}).get("running"))

    @Property(int, notify=changed)
    def kbsConveyorSpeed(self) -> int:
        return int(self._kbs_stage().get("conveyor", {}).get("speedPercent", 0))

    @Slot()
    def installKbsConveyor(self) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_controller.kinematic_brain_stage["conveyor"]
        conveyor["installed"] = True
        self._kbs_patch({"conveyor": conveyor})

    @Slot()
    def toggleKbsConveyorRun(self) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_controller.kinematic_brain_stage["conveyor"]
        conveyor["running"] = not conveyor.get("running")
        self._kbs_patch({"conveyor": conveyor})

    @Slot(int)
    def setKbsConveyorSpeed(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_controller.kinematic_brain_stage["conveyor"]
        conveyor["speedPercent"] = value
        self._kbs_patch({"conveyor": conveyor})

    @Property("QVariantList", notify=changed)
    def kbsEndstopData(self) -> list[dict[str, object]]:
        endstops = self._kbs_stage().get("endstops", {})
        return [{"key": key, "label": label, "active": bool(endstops.get(key))} for key, label in ENDSTOP_ENTRIES]

    @Slot(str)
    def toggleKbsEndstop(self, key: str) -> None:
        if self._kbs_controller is None:
            return
        endstops = self._kbs_controller.kinematic_brain_stage["endstops"]
        endstops[key] = not endstops.get(key)
        self._kbs_patch({"endstops": endstops})

    def _kbs_toggle_group(self, group_key: str, index: int) -> None:
        if self._kbs_controller is None:
            return
        group = self._kbs_controller.kinematic_brain_stage[group_key]
        if not 0 <= index < len(group):
            return
        group[index] = not group[index]
        self._kbs_patch({group_key: group})

    @Property("QVariantList", notify=changed)
    def kbsFans(self) -> list[bool]:
        return list(self._kbs_stage().get("fans", []))

    @Property("QVariantList", notify=changed)
    def kbsPumps(self) -> list[bool]:
        return list(self._kbs_stage().get("pumps", []))

    @Property("QVariantList", notify=changed)
    def kbsValves(self) -> list[bool]:
        return list(self._kbs_stage().get("valves", []))

    @Slot(int)
    def toggleKbsFan(self, index: int) -> None:
        self._kbs_toggle_group("fans", index)

    @Slot(int)
    def toggleKbsPump(self, index: int) -> None:
        self._kbs_toggle_group("pumps", index)

    @Slot(int)
    def toggleKbsValve(self, index: int) -> None:
        self._kbs_toggle_group("valves", index)

    # -- Module Config (CNC/Laser/HeatedBed/VacuumTable) --------------------

    def _on_module_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        ids = {r.id for r in robots}
        for key in _MODULE_CONFIGS:
            self._module_robots_cache[key] = robots
            if self._module_selected_robot_id[key] not in ids:
                self._module_selected_robot_id[key] = robots[0].id if robots else None
        self.changed.emit()

    def _active_module_key(self) -> str | None:
        return self._active_key if self._active_key in _MODULE_CONFIGS else None

    def _module_selected_robot(self, nav_key: str) -> RobotView | None:
        rid = self._module_selected_robot_id.get(nav_key)
        for r in self._module_robots_cache.get(nav_key, []):
            if r.id == rid:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def moduleRobotOptions(self) -> list[dict[str, str]]:
        key = self._active_module_key()
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._module_robots_cache.get(key, [])] if key else []

    @Property(str, notify=changed)
    def moduleSelectedRobotId(self) -> str:
        key = self._active_module_key()
        return (self._module_selected_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectModuleRobot(self, robot_id: str) -> None:
        key = self._active_module_key()
        if key is not None and robot_id != self._module_selected_robot_id.get(key):
            self._module_selected_robot_id[key] = robot_id or None
            self.changed.emit()

    @Property(str, notify=changed)
    def moduleHeadingKey(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["heading"]) if key else ""

    @Property(str, notify=changed)
    def moduleMachineName(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["machine"]) if key else ""

    @Property(str, notify=changed)
    def moduleExtraKind(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["extra"]) if key else ""

    @Property(bool, notify=changed)
    def moduleHasRobot(self) -> bool:
        key = self._active_module_key()
        return key is not None and self._module_selected_robot(key) is not None

    @Property(bool, notify=changed)
    def moduleEnabled(self) -> bool:
        key = self._active_module_key()
        if key is None:
            return False
        robot = self._module_selected_robot(key)
        return robot is not None and robot.module_enabled(_MODULE_CONFIGS[key]["module_key"])

    def _module_size_field(self, field: str) -> int:
        key = self._active_module_key()
        if key is None:
            return DEFAULT_SIZE_MM
        robot = self._module_selected_robot(key)
        if robot is None:
            return DEFAULT_SIZE_MM
        size = robot.module(_MODULE_CONFIGS[key]["module_key"]).get("size") or {}
        return int(size.get(field, DEFAULT_SIZE_MM))

    @Property(int, notify=changed)
    def moduleWidth(self) -> int:
        return self._module_size_field("width")

    @Property(int, notify=changed)
    def moduleLength(self) -> int:
        return self._module_size_field("length")

    def _module_extra_defaults(self, nav_key: str) -> dict:
        """Matches heated_bed_panel.py's/vacuum_table_panel.py's own
        _extra_default_fields() AND _extra_reset_fields() - both real
        subclasses happen to return the exact same dict from both, so
        this one helper covers Enable's setdefault() and Reset's
        overwrite alike (see _MODULE_CONFIGS's own "extra" tag)."""
        extra = _MODULE_CONFIGS[nav_key]["extra"]
        if extra == "heated_bed":
            return {"targetTemp": _HB_DEFAULT_TARGET_TEMP_C, "currentTemp1": _HB_DEFAULT_AMBIENT_TEMP_C, "currentTemp2": _HB_DEFAULT_AMBIENT_TEMP_C, "ssrActive": False}
        if extra == "vacuum_table":
            return {"pumpActive": False, "valveActive": False}
        return {}

    @Slot()
    def enableModuleConfig(self) -> None:
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return
        module_key = _MODULE_CONFIGS[key]["module_key"]
        module = dict(robot.module(module_key))
        module["enabled"] = True
        for field, default in self._module_extra_defaults(key).items():
            module.setdefault(field, default)
        robot.set_module(module_key, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disableModuleConfig(self) -> None:
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return
        module_key = _MODULE_CONFIGS[key]["module_key"]
        module = dict(robot.module(module_key))
        module["enabled"] = False
        robot.set_module(module_key, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetModuleConfig(self) -> None:
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return
        module_key = _MODULE_CONFIGS[key]["module_key"]
        reset_w, reset_l = _MODULE_CONFIGS[key]["reset_size"]
        payload = {
            "enabled": True,
            "size": {"width": reset_w, "length": reset_l},
            "worldPos": {"x": 0, "y": 0},
            "worldRot": 0,
            "renderScale": 1,
        }
        payload.update(self._module_extra_defaults(key))
        robot.set_module(module_key, payload)
        self._controller.push_active_state()
        self.changed.emit()

    def _set_module_size(self, field: str, value: int) -> None:
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return
        module_key = _MODULE_CONFIGS[key]["module_key"]
        module = dict(robot.module(module_key))
        size = dict(module.get("size") or {})
        size[field] = value
        module["size"] = size
        robot.set_module(module_key, module)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def setModuleWidth(self, value: int) -> None:
        self._set_module_size("width", value)

    @Slot(int)
    def setModuleLength(self, value: int) -> None:
        self._set_module_size("length", value)

    def _module_extra_value(self, field: str, default):
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return default
        return robot.module(_MODULE_CONFIGS[key]["module_key"]).get(field, default)

    def _set_module_extra_field(self, field: str, value) -> None:
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if key is None or robot is None:
            return
        module_key = _MODULE_CONFIGS[key]["module_key"]
        module = dict(robot.module(module_key))
        module[field] = value
        robot.set_module(module_key, module)
        self._controller.push_active_state()
        self.changed.emit()

    # Heated Bed's own extra fields.
    @Property(int, notify=changed)
    def moduleTargetTemp(self) -> int:
        return int(self._module_extra_value("targetTemp", _HB_DEFAULT_TARGET_TEMP_C))

    @Property(bool, notify=changed)
    def moduleSsrOn(self) -> bool:
        return bool(self._module_extra_value("ssrActive", False))

    @Property(str, notify=changed)
    def moduleTherm1(self) -> str:
        return f"{float(self._module_extra_value('currentTemp1', _HB_DEFAULT_AMBIENT_TEMP_C)):.1f} °C"

    @Property(str, notify=changed)
    def moduleTherm2(self) -> str:
        return f"{float(self._module_extra_value('currentTemp2', _HB_DEFAULT_AMBIENT_TEMP_C)):.1f} °C"

    @Slot(int)
    def setModuleTargetTemp(self, value: int) -> None:
        self._set_module_extra_field("targetTemp", value)

    @Slot()
    def toggleModuleSsr(self) -> None:
        self._set_module_extra_field("ssrActive", not self.moduleSsrOn)

    # Vacuum Table's own extra fields.
    @Property(bool, notify=changed)
    def modulePumpOn(self) -> bool:
        return bool(self._module_extra_value("pumpActive", False))

    @Property(bool, notify=changed)
    def moduleValveOn(self) -> bool:
        return bool(self._module_extra_value("valveActive", False))

    @Slot()
    def toggleModulePump(self) -> None:
        self._set_module_extra_field("pumpActive", not self.modulePumpOn)

    @Slot()
    def toggleModuleValve(self) -> None:
        self._set_module_extra_field("valveActive", not self.moduleValveOn)

    # -- ATC Tools -----------------------------------------------------------

    def _on_atc_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._atc_robots_cache = robots
        if self._atc_selected_robot_id not in {r.id for r in robots}:
            self._atc_selected_robot_id = robots[0].id if robots else None
        self.changed.emit()

    def _atc_selected_robot(self) -> RobotView | None:
        for r in self._atc_robots_cache:
            if r.id == self._atc_selected_robot_id:
                return r
        return None

    def _atc_config(self) -> dict:
        robot = self._atc_selected_robot()
        return (robot.atc if robot is not None else None) or _default_atc_config()

    def _atc_pos_fields(self, pos: dict, has_xy_table: bool) -> list[dict[str, object]]:
        fields = [
            {"field": f, "label": f"{f.upper()} (°)", "value": float(pos.get(f, 0) or 0), "min": _ATC_JOINT_RANGE_DEG[0], "max": _ATC_JOINT_RANGE_DEG[1]}
            for f in _ATC_JOINT_FIELDS
        ]
        if has_xy_table:
            fields += [
                {"field": f, "label": f"Table {f[1].upper()} (mm)", "value": float(pos.get(f, 0) or 0), "min": _ATC_TABLE_RANGE_MM[0], "max": _ATC_TABLE_RANGE_MM[1]}
                for f in _ATC_TABLE_FIELDS
            ]
        return fields

    def _atc_slot_count(self, config: dict) -> int:
        if config.get("type") in ("vertical_panel", "horizontal_panel"):
            grid = config.get("panelGrid", "2x2")
            try:
                rows, cols = (int(x) for x in grid.split("x"))
            except ValueError:
                rows, cols = 2, 2
            return rows * cols
        return max(1, int(config.get("revolverSlots", 8) or 8))

    @Property("QVariantList", notify=changed)
    def atcRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._atc_robots_cache]

    @Property(str, notify=changed)
    def atcSelectedRobotId(self) -> str:
        return self._atc_selected_robot_id or ""

    @Slot(str)
    def selectAtcRobot(self, robot_id: str) -> None:
        if robot_id != self._atc_selected_robot_id:
            self._atc_selected_robot_id = robot_id or None
            self._atc_editing_slot = None
            self.changed.emit()

    @Property(bool, notify=changed)
    def atcHasRobot(self) -> bool:
        return self._atc_selected_robot() is not None

    @Property(bool, notify=changed)
    def atcConfigured(self) -> bool:
        robot = self._atc_selected_robot()
        return robot is not None and robot.atc is not None

    @Property(str, notify=changed)
    def atcType(self) -> str:
        return str(self._atc_config().get("type", "vertical_panel"))

    @Property("QVariantList", constant=True)
    def atcTypeOptions(self) -> list[dict[str, str]]:
        labels = {"vertical_panel": "LBL_ATC_VERTICAL", "horizontal_panel": "LBL_ATC_HORIZONTAL", "revolver": "LBL_ATC_REVOLVER"}
        return [{"key": k, "labelKey": labels[k]} for k in _ATC_TYPE_KEYS]

    @Property(bool, notify=changed)
    def atcIsPanel(self) -> bool:
        return self.atcType in ("vertical_panel", "horizontal_panel")

    @Property(str, notify=changed)
    def atcPanelGrid(self) -> str:
        return str(self._atc_config().get("panelGrid", "2x2"))

    @Property("QVariantList", constant=True)
    def atcPanelGridOptions(self) -> list[str]:
        return list(PANEL_GRIDS)

    @Property(int, notify=changed)
    def atcRevolverSlots(self) -> int:
        return int(self._atc_config().get("revolverSlots", 8) or 8)

    @Property("QVariantList", constant=True)
    def atcToolOptions(self) -> list[str]:
        return list(URTC_TOOLS)

    @Property(bool, notify=changed)
    def atcHasXyTable(self) -> bool:
        robot = self._atc_selected_robot()
        return bool(robot is not None and robot.has_xy_table)

    @Property(str, notify=changed)
    def atcEditingSlotKey(self) -> str:
        return "" if self._atc_editing_slot is None else str(self._atc_editing_slot)

    @Property("QVariantList", notify=changed)
    def atcSlotsData(self) -> list[dict[str, object]]:
        if not self.atcConfigured:
            return []  # matches _refresh_controls()'s own real early-return before any config exists
        config = self._atc_config()
        is_panel = self.atcIsPanel
        has_xy_table = self.atcHasXyTable
        tools_by_slot = {t.get("slot"): t for t in config.get("tools", []) if isinstance(t, dict)}
        result = []
        for i in range(self._atc_slot_count(config)):
            entry = tools_by_slot.get(i, {})
            tool = entry.get("tool", "None")
            editing = is_panel and self._atc_editing_slot == i
            result.append({
                "slot": i,
                "tool": tool,
                "toolIndex": URTC_TOOLS.index(tool) if tool in URTC_TOOLS else 0,
                "showPosButton": is_panel,
                "editing": editing,
                "pos": self._atc_pos_fields(entry.get("pos") or _default_pos(), has_xy_table) if editing else [],
            })
        return result

    @Property("QVariantList", notify=changed)
    def atcBasePos(self) -> list[dict[str, object]]:
        config = self._atc_config()
        return self._atc_pos_fields(config.get("revolverPos") or _default_pos(), self.atcHasXyTable)

    @Property(bool, notify=changed)
    def atcBaseEditing(self) -> bool:
        return self._atc_editing_slot == "revolver"

    def _atc_push(self, config: dict) -> None:
        robot = self._atc_selected_robot()
        if robot is None:
            return
        robot.set_atc(config)
        self._controller.push_active_state()
        self.changed.emit()

    def _atc_update(self, updates: dict) -> None:
        self._atc_push({**self._atc_config(), **updates})

    @Slot()
    def enableAtc(self) -> None:
        robot = self._atc_selected_robot()
        if robot is None:
            return
        robot.set_atc(_default_atc_config())
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disableAtc(self) -> None:
        robot = self._atc_selected_robot()
        if robot is None:
            return
        robot.set_atc(None)
        self._atc_editing_slot = None
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetAtc(self) -> None:
        robot = self._atc_selected_robot()
        if robot is None:
            return
        robot.set_atc(_default_atc_config())
        self._atc_editing_slot = None
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str)
    def setAtcType(self, type_key: str) -> None:
        if type_key in _ATC_TYPE_KEYS:
            self._atc_update({"type": type_key})

    @Slot(str)
    def setAtcPanelGrid(self, grid: str) -> None:
        if grid in PANEL_GRIDS:
            self._atc_update({"panelGrid": grid, "tools": []})

    @Slot(int)
    def setAtcRevolverSlots(self, value: int) -> None:
        self._atc_update({"revolverSlots": value, "tools": []})

    @Slot(int, str)
    def setAtcTool(self, slot: int, tool: str) -> None:
        if self._atc_selected_robot() is None:
            return
        config = dict(self._atc_config())
        tools = [dict(t) for t in config.get("tools", [])]
        idx = next((i for i, t in enumerate(tools) if t.get("slot") == slot), None)
        if idx is not None:
            tools[idx]["tool"] = tool
        else:
            tools.append({"slot": slot, "tool": tool, "pos": _default_pos()})
        self._atc_update({"tools": tools})

    @Slot(str, str, float)
    def setAtcPosField(self, slot_key: str, field: str, value: float) -> None:
        if self._atc_selected_robot() is None:
            return
        config = dict(self._atc_config())
        if slot_key == "revolver":
            pos = dict(config.get("revolverPos") or _default_pos())
            pos[field] = value
            self._atc_update({"revolverPos": pos})
            return
        slot = int(slot_key)
        tools = [dict(t) for t in config.get("tools", [])]
        idx = next((i for i, t in enumerate(tools) if t.get("slot") == slot), None)
        if idx is None:
            tools.append({"slot": slot, "tool": "None", "pos": _default_pos()})
            idx = len(tools) - 1
        pos = dict(tools[idx].get("pos") or _default_pos())
        pos[field] = value
        tools[idx]["pos"] = pos
        self._atc_update({"tools": tools})

    @Slot(int)
    def toggleAtcSlotPos(self, slot: int) -> None:
        self._atc_editing_slot = None if self._atc_editing_slot == slot else slot
        self.changed.emit()

    @Slot()
    def toggleAtcBasePos(self) -> None:
        self._atc_editing_slot = None if self._atc_editing_slot == "revolver" else "revolver"
        self.changed.emit()

    @Slot(str)
    def saveAtcConfig(self, path: str) -> None:
        if self._atc_selected_robot() is None or not self.atcConfigured:
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path:
            return
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(self._atc_config(), f, indent=2)

    @Property(str, notify=changed)
    def atcLoadError(self) -> str:
        return self._atc_load_error

    @Slot(str)
    def loadAtcConfig(self, path: str) -> None:
        """Sets atcLoadError to "" on success, a real error message
        otherwise - matches _on_load_config()'s own QMessageBox.warning()
        real validation (a non-dict payload, or one missing the required
        "type" key, is rejected rather than accepted and silently
        producing a broken ATC graphic). A real Property (not a Slot
        return value) so the global FileDialog below - which has no
        access to the per-instance panel's own ids - can still get the
        result to the visible Text some other way, same reasoning
        saveXyTableConfig's own global dialog never needed since it has
        nothing to report back."""
        if self._atc_selected_robot() is None:
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path:
            return
        try:
            with open(local_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            self._atc_load_error = str(exc)
            self.changed.emit()
            return
        if not isinstance(data, dict) or "type" not in data:
            self._atc_load_error = _("MSG_ATC_INVALID_CONFIG")
            self.changed.emit()
            return
        self._atc_load_error = ""
        self._atc_editing_slot = None
        self._atc_update(data)

    # -- Cameras ---------------------------------------------------------

    def _current_camera(self, camera_id: int) -> CameraView | None:
        state = self._controller.active_state
        active = state.active_controller if state else None
        if active is None:
            return None
        for cam in active.cameras:
            if cam.id == camera_id:
                return cam
        return None

    def _on_cameras_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        cameras = active.cameras if active is not None else []
        seen_ids = {c.id for c in cameras}
        for stale_id in set(self._camera_stream_tasks) - seen_ids:
            self._stop_camera_stream(stale_id)
        for camera in cameras:
            if camera.connected:
                self._ensure_camera_stream(camera.id)
            else:
                self._stop_camera_stream(camera.id)
        self.changed.emit()

    def _camera_stream_url(self, camera_id: int) -> str | None:
        conn = self._controller.active_connection
        if conn is None:
            return None
        return f"{conn.info.base_url}/api/camera/{camera_id}/stream"

    def _ensure_camera_stream(self, camera_id: int) -> None:
        task = self._camera_stream_tasks.get(camera_id)
        if task is not None and not task.done():
            return  # already streaming - _on_cameras_state_changed runs on
            # every state broadcast, not just real changes, matching
            # CameraCard._start_stream()'s own real no-op guard.
        url = self._camera_stream_url(camera_id)
        if not url:
            self._camera_placeholder[camera_id] = (_("STATUS_LIVE"), "#10b981")
            return
        self._camera_stream_tasks[camera_id] = asyncio.ensure_future(self._run_camera_stream(camera_id, url))

    def _stop_camera_stream(self, camera_id: int) -> None:
        task = self._camera_stream_tasks.pop(camera_id, None)
        if task is not None:
            task.cancel()
        self._camera_frame_versions.pop(camera_id, None)
        self._camera_placeholder.pop(camera_id, None)
        if self._frame_provider is not None:
            self._frame_provider.clear_frame(camera_id)

    async def _run_camera_stream(self, camera_id: int, url: str) -> None:
        """Matches CameraCard._run_stream() exactly - a real reconnect
        loop (capped exponential backoff, reset the instant a real frame
        arrives again), not a one-shot, for the same real reason that
        file's own header documents (the server's own camera-process
        supervisor can take up to ~30s to respawn a hung capture)."""
        self._camera_placeholder[camera_id] = (_("LBL_CONNECTING_STREAM"), "#38bdf8")
        self._camerasChanged.emit()
        attempt = 0
        try:
            while True:
                got_a_frame = False
                async for frame in iter_mjpeg_frames(url):
                    if not got_a_frame:
                        got_a_frame = True
                        attempt = 0
                    image = QImage()
                    if image.loadFromData(frame, "JPG"):
                        if self._frame_provider is not None:
                            self._frame_provider.set_frame(camera_id, image)
                        self._camera_frame_versions[camera_id] = self._camera_frame_versions.get(camera_id, 0) + 1
                        self._camera_placeholder.pop(camera_id, None)
                        self._camerasChanged.emit()
                self._camera_placeholder[camera_id] = (_("STATUS_NO_SIGNAL"), "#4a5563")
                self._camerasChanged.emit()
                attempt += 1
                await asyncio.sleep(min(1.5 * attempt, 15.0))
        except asyncio.CancelledError:
            return

    def _camera_status_display(self, status: dict | None) -> tuple[str, str]:
        if not status:
            return "", ""
        state = str(status.get("status", ""))
        color = _CAM_STATUS_COLORS.get(state, "#8a97a6")
        label_keys = {"running": "STATUS_STREAM_RUNNING", "starting": "STATUS_STREAM_STARTING", "error": "STATUS_STREAM_ERROR", "stopped": "STATUS_STREAM_STOPPED"}
        label = _(label_keys[state]) if state in label_keys else state.upper()
        return f"● {label}", color

    @Property("QVariantList", notify=changed)
    def cameraRobotOptions(self) -> list[dict[str, str]]:
        state = self._controller.active_state
        active = state.active_controller if state else None
        robots = active.robots if active is not None else []
        options = [{"id": "", "label": _("OPT_NONE_FLOATING")}]
        options += [{"id": str(r.id), "label": f"{r.model} (A{r.id})"} for r in robots]
        return options

    @Property("QVariantList", notify=changed)
    def camerasData(self) -> list[dict[str, object]]:
        state = self._controller.active_state
        active = state.active_controller if state else None
        cameras = active.cameras if active is not None else []
        result = []
        for camera in cameras:
            is_ip = camera.source_type == "ip"
            type_options = list((ip_stream_labels(camera.discovered_stream_paths) if is_ip else _CAM_USB_TYPE_OPTIONS) + _CAM_THERMAL_TYPE_OPTIONS)
            type_index = type_options.index(camera.camera_type) if camera.camera_type in type_options else 0
            paths = camera.discovered_stream_paths
            labels = ip_stream_labels(paths)
            extra_paths = [
                {"label": labels[i] if i < len(labels) else f"{_('LBL_RTSP_PATH')} {i + 1}", "value": paths[i], "index": i}
                for i in range(1, min(len(paths), 4))
            ]
            disc_text, disc_color = self._camera_discovery_status.get(camera.id, ("", "#8a97a6"))
            result.append({
                "id": camera.id,
                "connected": camera.connected,
                "sourceType": camera.source_type,
                "isIp": is_ip,
                "cameraType": camera.camera_type,
                "typeOptions": type_options,
                "typeIndex": type_index,
                "assignedRobotId": str(camera.assigned_robot_id) if camera.assigned_robot_id is not None else "",
                "hardwareSource": camera.hardware_source,
                "ipHost": camera.ip_host,
                "rtspPort": camera.rtsp_port,
                "rtspPath": camera.rtsp_path,
                "extraPaths": extra_paths,
                "ipUsername": camera.ip_username,
                "ipPassword": camera.ip_password,
                "usbDevices": self._camera_usb_devices.get(camera.id, []),
                "discoveryStatusText": disc_text,
                "discoveryStatusColor": disc_color,
                "ptzError": self._camera_ptz_error.get(camera.id, ""),
            })
        return result

    @Property("QVariantList", notify=_camerasChanged)
    def cameraFrameVersions(self) -> list[dict[str, object]]:
        """Deliberately separate from camerasData above (own dedicated
        `_camerasChanged` notify, not `changed`) - this is the one
        Property that both the real 3s status poll AND every real video
        frame touch, so it's the one place a background update could hit
        while a user is mid-edit in some OTHER camera's own text field.
        Isolating the fast-moving bits here means neither the status poll
        nor a live frame ever forces camerasData's own Repeater to tear
        down and rebuild every card - only a real config/state change
        does that. A real, honestly-scoped limitation still applies: any
        OTHER panel's own background poll still shares the general
        `changed` signal camerasData listens on too (see this class's own
        docstring) - fully isolating every timer in this app is real,
        separate future work, not done here."""
        state = self._controller.active_state
        active = state.active_controller if state else None
        cameras = active.cameras if active is not None else []
        result = []
        for camera in cameras:
            if not camera.connected:
                text, color = _("STATUS_NO_SIGNAL"), "#4a5563"
            else:
                text, color = self._camera_placeholder.get(camera.id, ("", ""))
            status = self._camera_status.get(f"{active.id}:{camera.id}") if active is not None else None
            status_text, status_color = self._camera_status_display(status)
            result.append({
                "id": camera.id,
                "version": self._camera_frame_versions.get(camera.id, 0),
                "placeholderText": text,
                "placeholderColor": color,
                "statusText": status_text,
                "statusColor": status_color,
            })
        return result

    @Slot(int)
    def toggleCameraConnection(self, camera_id: int) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        camera.set_connected(not camera.connected)
        self._controller.push_active_state()
        if camera.connected:
            self._ensure_camera_stream(camera_id)
        else:
            self._stop_camera_stream(camera_id)
        self.changed.emit()
        self._camerasChanged.emit()

    @Slot(int, str)
    def setCameraType(self, camera_id: int, camera_type: str) -> None:
        camera = self._current_camera(camera_id)
        if camera is None or camera.camera_type == camera_type:
            return
        if camera.source_type == "ip":
            labels = ip_stream_labels(camera.discovered_stream_paths)
            if camera_type in labels:
                idx = labels.index(camera_type)
                paths = camera.discovered_stream_paths
                if idx < len(paths) and paths[idx] != camera.rtsp_path:
                    camera.set_rtsp_path(paths[idx])
                    # Real reconnect now - matches _on_type_combo_changed()'s
                    # own reasoning: the server's own supervisor is about to
                    # respawn the real capture process (rtsp_path is part of
                    # its fingerprint), so the old MJPEG connection this
                    # task holds is about to die anyway.
                    if camera.connected:
                        self._stop_camera_stream(camera_id)
        camera.set_camera_type(camera_type)
        self._controller.push_active_state()
        if camera.connected:
            self._ensure_camera_stream(camera_id)
        self.changed.emit()

    @Slot(int, str, "QVariant")
    def setCameraField(self, camera_id: int, field: str, value) -> None:
        """Generic dispatch, matching _on_field_changed()'s own real
        getattr(camera, f"set_{field}") - never a per-field Slot, same
        reasoning that file's own single handler already uses for every
        plain text/number field this card has."""
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        setter = getattr(camera, f"set_{field}", None)
        if setter is None:
            return
        setter(value)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int, str)
    def setCameraSourceType(self, camera_id: int, value: str) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        camera.set_source_type(value)
        current_type = camera.camera_type
        if current_type not in _CAM_THERMAL_TYPE_OPTIONS:
            new_type = ip_stream_labels(camera.discovered_stream_paths)[0] if value == "ip" else _CAM_USB_TYPE_OPTIONS[0]
            if current_type != new_type:
                camera.set_camera_type(new_type)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int, str)
    def setCameraAssignedRobot(self, camera_id: int, robot_id: str) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        camera.set_assigned_robot_id(int(robot_id) if robot_id else None)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int, int, str)
    def setCameraExtraPath(self, camera_id: int, index: int, value: str) -> None:
        """`index` is 1-based (0 is the primary rtsp_path field, already
        handled by setCameraField) - matches _on_extra_path_edited()'s
        own real bounds/active-index logic."""
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        paths = list(camera.discovered_stream_paths)
        if index >= len(paths) or paths[index] == value:
            return
        paths[index] = value
        camera.set_discovered_stream_paths(paths)
        labels = ip_stream_labels(paths)
        active_index = labels.index(camera.camera_type) if camera.camera_type in labels else 0
        if index == active_index:
            camera.set_rtsp_path(value)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def discoverUsbDevices(self, camera_id: int) -> None:
        task = self._camera_discovery_tasks.get(camera_id)
        if task is not None and not task.done():
            return
        conn = self._controller.active_connection
        if conn is None:
            self._camera_discovery_status[camera_id] = (_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            self.changed.emit()
            return
        self._camera_usb_devices[camera_id] = []
        self._camera_discovery_status[camera_id] = (_("LBL_DISCOVERING"), "#8a97a6")
        self.changed.emit()
        self._camera_discovery_tasks[camera_id] = asyncio.ensure_future(self._run_discover_usb(camera_id, conn))

    async def _run_discover_usb(self, camera_id: int, conn: HydraConnection) -> None:
        result = await conn.discover_usb_devices()
        if result is None:
            self._camera_discovery_status[camera_id] = (_("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            self.changed.emit()
            return
        status, body = result
        devices = body.get("devices") if status == 200 and isinstance(body, dict) else None
        if status != 200 or not isinstance(devices, list):
            message = body.get("error") if isinstance(body, dict) else None
            self._camera_discovery_status[camera_id] = (str(message) if message else _("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            self.changed.emit()
            return
        if not devices:
            self._camera_discovery_status[camera_id] = (_("MSG_NO_USB_DEVICES_FOUND"), "#f59e0b")
            self.changed.emit()
            return
        options = []
        for device in devices:
            if not isinstance(device, dict):
                continue
            index = device.get("index")
            width, height = device.get("width"), device.get("height")
            label = f"/dev/video{index}" if index is not None else "?"
            if width and height:
                label += f" ({width}x{height})"
            options.append({"label": label, "value": index})
        self._camera_usb_devices[camera_id] = options
        self._camera_discovery_status[camera_id] = ("", "#8a97a6")
        self.changed.emit()

    @Slot(int, int)
    def pickUsbDevice(self, camera_id: int, index: int) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        # Windows/OpenCV opens by bare numeric index; Linux/V4L2 opens by
        # /dev/videoN path - matches _on_usb_device_picked()'s own real
        # platform split.
        value = str(index) if sys.platform == "win32" else f"/dev/video{index}"
        camera.set_hardware_source(value)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int, str, int, str, str)
    def discoverRtspPath(self, camera_id: int, host: str, port: int, username: str, password: str) -> None:
        task = self._camera_discovery_tasks.get(camera_id)
        if task is not None and not task.done():
            return
        conn = self._controller.active_connection
        if conn is None:
            self._camera_discovery_status[camera_id] = (_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            self.changed.emit()
            return
        if not host.strip():
            self._camera_discovery_status[camera_id] = (_("LBL_IP_HOST"), "#ef4444")
            self.changed.emit()
            return
        self._camera_discovery_status[camera_id] = (_("LBL_DISCOVERING"), "#8a97a6")
        self.changed.emit()
        self._camera_discovery_tasks[camera_id] = asyncio.ensure_future(
            self._run_discover_rtsp(camera_id, conn, host, port, username, password)
        )

    async def _run_discover_rtsp(self, camera_id: int, conn: HydraConnection, host: str, port: int, username: str, password: str) -> None:
        result = await conn.discover_rtsp_path(host, port, username, password)
        if result is None:
            self._camera_discovery_status[camera_id] = (_("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")
            self.changed.emit()
            return
        status, body = result
        found_paths = body.get("paths") if isinstance(body, dict) else None
        camera = self._current_camera(camera_id)
        if status == 200 and isinstance(body, dict) and body.get("ok") and isinstance(found_paths, list) and found_paths and camera is not None:
            paths = [str(p) for p in found_paths]
            camera.set_discovered_stream_paths(paths)
            camera.set_rtsp_path(paths[0])
            camera.set_camera_type(ip_stream_labels(paths)[0])
            self._controller.push_active_state()
            self._camera_discovery_status[camera_id] = (_("MSG_RTSP_PATH_FOUND") + f": {', '.join(paths)}", "#10b981")
            self.changed.emit()
            return
        if status == 200 and isinstance(body, dict):
            tried = body.get("triedPaths")
            suffix = f" ({', '.join(str(t) for t in tried)})" if isinstance(tried, list) and tried else ""
            self._camera_discovery_status[camera_id] = (_("MSG_RTSP_PATH_NOT_FOUND") + suffix, "#f59e0b")
            self.changed.emit()
            return
        message = body.get("error") if isinstance(body, dict) else None
        self._camera_discovery_status[camera_id] = (str(message) if message else _("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")
        self.changed.emit()

    @Slot(int, int, int, int)
    def sendCameraPtz(self, camera_id: int, pan: int, tilt: int, zoom: int) -> None:
        asyncio.ensure_future(self._run_ptz(camera_id, pan, tilt, zoom))

    async def _run_ptz(self, camera_id: int, pan: int, tilt: int, zoom: int) -> None:
        camera = self._current_camera(camera_id)
        conn = self._controller.active_connection
        if camera is None or conn is None or not camera.ip_host:
            return
        result = await conn.send_ptz(camera_id, camera.ip_host, camera.ip_username, camera.ip_password, pan, tilt, zoom)
        if result is None:
            self._camera_ptz_error[camera_id] = _("MSG_PTZ_FAILED")
            self.changed.emit()
            return
        status, body = result
        if status == 200 and isinstance(body, dict) and body.get("ok") is True:
            self._camera_ptz_error.pop(camera_id, None)
            self.changed.emit()
            return
        error = body.get("error") if isinstance(body, dict) else None
        self._camera_ptz_error[camera_id] = str(error) if error else _("MSG_PTZ_FAILED")
        self.changed.emit()

    async def _poll_camera_status(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.fetch_camera_status()
        if result is None:
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            return
        self._camera_status = body
        self._camerasChanged.emit()

    # -- Flasher -----------------------------------------------------------

    def _flasher_active_key(self) -> str | None:
        return self._active_key if self._active_key in _FLASHER_TIERS else None

    def _on_flasher_state_changed(self, state: HydraState) -> None:
        self._flasher_is_hardware = state.can_ota_transport == "hardware"
        for key in _FLASHER_TIERS:
            ctrl = state.active_controller
            self._flasher_controller[key] = ctrl
            robots = ctrl.robots if ctrl is not None else []
            ids = {r.id for r in robots}
            if self._flasher_robot_id[key] not in ids:
                self._flasher_robot_id[key] = robots[0].id if robots else None
        self.changed.emit()

    def _flasher_current_robot(self, key: str) -> RobotView | None:
        ctrl = self._flasher_controller.get(key)
        rid = self._flasher_robot_id.get(key)
        if ctrl is None or rid is None:
            return None
        for r in ctrl.robots:
            if r.id == rid:
                return r
        return None

    def _flasher_target(self, key: str) -> CanOtaTarget | None:
        ctrl = self._flasher_controller.get(key)
        if ctrl is None:
            return None
        tier = self._flasher_tier[key]
        if tier == "kinematicBrain":
            return CanOtaTarget(controller_name=ctrl.name, tier=tier)
        robot = self._flasher_current_robot(key)
        if robot is None:
            return None
        robots = ctrl.robots
        index0 = next((i for i, r in enumerate(robots) if r.id == robot.id), -1)
        if index0 < 0:
            return None
        return CanOtaTarget(controller_name=ctrl.name, tier=tier, robot_id=robot.id, robot_name=robot.model, robot_index0=index0)

    def _flasher_board_state(self, key: str) -> dict:
        ctrl = self._flasher_controller.get(key)
        tier = self._flasher_tier[key]
        if tier == "kinematicBrain":
            return ctrl.kinematic_brain if ctrl is not None else {}
        robot = self._flasher_current_robot(key)
        return robot.module(tier) if robot is not None else {}

    def _flasher_push_log(self, key: str, text: str, level: str = "info") -> None:
        log = self._flasher_log.setdefault(key, [])
        log.append({"text": text, "level": level})
        if len(log) > 300:
            del log[: len(log) - 300]

    def _flasher_apply_patch(self, key: str, patch: dict) -> None:
        ctrl = self._flasher_controller.get(key)
        if ctrl is None:
            return
        tier = self._flasher_tier[key]
        if tier == "kinematicBrain":
            ctrl.set_kinematic_brain(patch)
        else:
            robot = self._flasher_current_robot(key)
            if robot is None:
                return
            if tier == "urtcHead":
                merged = {**robot.module("urtcHead"), **patch}
                robot.set_module("urtcHead", merged)
            else:
                robot.set_module(tier, patch)
        self._controller.push_active_state()
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def flasherTierOptions(self) -> list[dict[str, object]]:
        key = self._flasher_active_key()
        if key is None:
            return []
        robot = self._flasher_current_robot(key)
        expansion_available = has_advanced_expansion((robot.module("urtcHead") if robot else {}).get("expansionBoardType"))
        result = []
        for t in _FLASHER_TIERS[key]:
            enabled = True
            if t == "urtcHead":
                enabled = bool(robot and robot.urtc_connected)
            elif t == "urtcExpansion":
                enabled = expansion_available
            result.append({"key": t, "label": f"{_(_TIER_LABEL_KEYS[t])} ({chip_name_for(t)})", "enabled": enabled})
        return result

    @Property(str, notify=changed)
    def flasherTier(self) -> str:
        key = self._flasher_active_key()
        return self._flasher_tier.get(key, "") if key else ""

    @Slot(str)
    def selectFlasherTier(self, tier: str) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_tier[key] = tier
            self.changed.emit()

    @Property(bool, notify=changed)
    def flasherNeedsRobotSlot(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self._flasher_tier[key] != "kinematicBrain"

    @Property("QVariantList", notify=changed)
    def flasherRobotOptions(self) -> list[dict[str, str]]:
        key = self._flasher_active_key()
        if key is None:
            return []
        ctrl = self._flasher_controller.get(key)
        robots = ctrl.robots if ctrl is not None else []
        result = []
        for i, r in enumerate(robots):
            unreachable = "" if r.urtc_connected else f" ({_('LBL_URTC_UNREACHABLE')})"
            result.append({"id": r.id, "label": f"{slot_label(i)} - {r.model}{unreachable}"})
        return result

    @Property(str, notify=changed)
    def flasherSelectedRobotId(self) -> str:
        key = self._flasher_active_key()
        return (self._flasher_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectFlasherRobot(self, robot_id: str) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_robot_id[key] = robot_id or None
            self.changed.emit()

    @Property(str, notify=changed)
    def flasherHopDescription(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        target = self._flasher_target(key)
        return hop_description(target) if target else ""

    @Property(bool, notify=changed)
    def flasherUnreachable(self) -> bool:
        key = self._flasher_active_key()
        if key is None or not self._flasher_is_hardware:
            return False
        target = self._flasher_target(key)
        return target is not None and resolve_hardware_target(target) is None

    @Property(str, notify=changed)
    def flasherVersionLabel(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return _("LBL_NO_VERSION_KNOWN")
        board = self._flasher_board_state(key)
        if board.get("firmwareVersion"):
            return f"{_('LBL_CURRENT_VERSION')}: {board.get('firmwareVersion', '?')} ({_('LBL_BOOTLOADER')} {board.get('bootloaderVersion', '?')})"
        return _("LBL_NO_VERSION_KNOWN")

    @Property(bool, notify=changed)
    def flasherQueryBusy(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_query_busy.get(key, False) if key else False

    @Slot()
    def flasherQueryVersion(self) -> None:
        key = self._flasher_active_key()
        if key is None or self._flasher_query_busy.get(key) or self._flasher_controller.get(key) is None:
            return
        target = self._flasher_target(key)
        if target is None:
            return
        self._flasher_query_busy[key] = True
        self._flasher_push_log(key, f"{_('LBL_QUERYING')}: {hop_description(target)}")
        self.changed.emit()
        asyncio.ensure_future(self._run_flasher_query(key, target))

    async def _run_flasher_query(self, key: str, target: CanOtaTarget) -> None:
        try:
            if self._flasher_is_hardware:
                conn = self._controller.active_connection
                if conn is None:
                    self._flasher_push_log(key, _("LBL_NO_RESPONSE"), "error")
                    return
                result = await hardware_query_version(conn, target)
            else:
                result = await mock_query_version(target)
        finally:
            self._flasher_query_busy[key] = False
            self.changed.emit()
        if not result.online:
            self._flasher_push_log(key, _("LBL_NO_RESPONSE"), "error")
            self.changed.emit()
            return
        self._flasher_push_log(key, f"{_('LBL_VERSION_FOUND')}: {result.firmware_version} / {result.bootloader_version}", "ok")
        patch = {"firmwareVersion": result.firmware_version, "bootloaderVersion": result.bootloader_version, "hardwareId": result.hardware_id}
        if self._flasher_tier[key] == "urtcHead" and result.expansion_board_type is not None:
            patch["expansionBoardType"] = result.expansion_board_type
        self._flasher_apply_patch(key, patch)

    @Property(str, notify=changed)
    def flasherFileInfo(self) -> str:
        key = self._flasher_active_key()
        file = self._flasher_file.get(key) if key else None
        if not file:
            return _("LBL_NO_FILE")
        return f"{file['name']} - {len(file['bytes']) / 1024:.1f} KB - CRC32 0x{crc32(file['bytes']):08X}"

    @Property(bool, notify=changed)
    def flasherHasFile(self) -> bool:
        key = self._flasher_active_key()
        return bool(self._flasher_file.get(key)) if key else False

    @Slot(str)
    def browseFlasherFile(self, path: str) -> None:
        key = self._flasher_active_key()
        if key is None:
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path:
            return
        with open(local_path, "rb") as f:
            data = f.read()
        name = os.path.basename(local_path)
        self._flasher_file[key] = {"name": name, "bytes": data, "hardware_id": None, "version_tag": None}
        self._flasher_push_log(key, f"{_('LBL_FILE_LOADED')}: {name} ({len(data)} bytes)")
        self.changed.emit()

    @Property(bool, notify=changed)
    def flasherGithubAvailable(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and GITHUB_FIRMWARE_REPO.get(self._flasher_tier[key]) is not None

    @Property(str, notify=changed)
    def flasherGithubButtonLabel(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        repo = GITHUB_FIRMWARE_REPO.get(self._flasher_tier[key])
        return f"{_('BTN_DOWNLOAD_GITHUB')} ({repo})" if repo else ""

    @Property(bool, notify=changed)
    def flasherGithubBusy(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_gh_busy.get(key, False) if key else False

    @Property("QVariantList", notify=changed)
    def flasherGithubAssets(self) -> list[dict[str, object]]:
        key = self._flasher_active_key()
        if key is None:
            return []
        assets = self._flasher_gh_assets.get(key, [])
        return [
            {"index": i, "label": f"{a.display_name or a.name} v{a.release_tag}{f' - {a.chip}' if a.chip else ''} ({a.size / 1024:.1f} KB)"}
            for i, a in enumerate(assets)
        ]

    @Slot()
    def fetchFlasherGithub(self) -> None:
        key = self._flasher_active_key()
        if key is None:
            return
        tier = self._flasher_tier[key]
        repo = GITHUB_FIRMWARE_REPO.get(tier)
        if not repo:
            return
        self._flasher_gh_busy[key] = True
        self._flasher_gh_assets[key] = []
        self.changed.emit()
        asyncio.ensure_future(self._run_flasher_github(key, repo, tier))

    async def _run_flasher_github(self, key: str, repo: str, tier: str) -> None:
        try:
            assets = await fetch_github_firmware_releases(repo, tier)
            self._flasher_gh_assets[key] = assets
            self._flasher_push_log(key, f"{_('LBL_GITHUB_FOUND')}: {len(assets)} ({repo})")
        except Exception as exc:
            self._flasher_push_log(key, f"{_('LBL_GITHUB_ERROR')}: {exc}", "error")
        finally:
            self._flasher_gh_busy[key] = False
            self.changed.emit()

    @Slot(int)
    def useFlasherGithubAsset(self, index: int) -> None:
        key = self._flasher_active_key()
        if key is None:
            return
        assets = self._flasher_gh_assets.get(key, [])
        if not 0 <= index < len(assets):
            return
        asyncio.ensure_future(self._run_use_github_asset(key, assets[index]))

    async def _run_use_github_asset(self, key: str, asset) -> None:
        self._flasher_push_log(key, f"{_('LBL_GITHUB_DOWNLOADING')}: {asset.name}")
        self.changed.emit()
        try:
            data = await download_github_firmware(asset)
            self._flasher_file[key] = {"name": asset.name, "bytes": data, "hardware_id": asset.hardware_id, "version_tag": asset.release_tag}
            self._flasher_push_log(key, f"{_('LBL_FILE_LOADED')}: {asset.name} ({len(data)} bytes)", "ok")
        except Exception as exc:
            self._flasher_push_log(key, f"{_('LBL_GITHUB_ERROR')}: {exc}", "error")
        self.changed.emit()

    @Property(bool, notify=changed)
    def flasherAllowDowngrade(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_allow_downgrade.get(key, False) if key else False

    @Slot(bool)
    def setFlasherAllowDowngrade(self, value: bool) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_allow_downgrade[key] = value

    @Property(bool, notify=changed)
    def flasherEraseFram(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_erase_fram.get(key, False) if key else False

    @Slot(bool)
    def setFlasherEraseFram(self, value: bool) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_erase_fram[key] = value

    @Property(bool, notify=changed)
    def flasherFlashing(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_flashing.get(key, False) if key else False

    @Property(bool, notify=changed)
    def flasherCanFlash(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self.flasherHasFile and not self._flasher_flashing.get(key, False) and not self.flasherUnreachable

    @Property(str, notify=changed)
    def flasherConfirmMessage(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        target = self._flasher_target(key)
        if target is None:
            return ""
        robot = self._flasher_current_robot(key)
        ctrl = self._flasher_controller.get(key)
        robot_label = robot.model if robot is not None else (ctrl.name if ctrl is not None else "")
        return _("MSG_CONFIRM_FLASH", target=_(_TIER_LABEL_KEYS[self._flasher_tier[key]]), robot=robot_label)

    @Property(str, notify=changed)
    def flasherProgressLabel(self) -> str:
        key = self._flasher_active_key()
        return self._flasher_progress.get(key, {}).get("label", "") if key else ""

    @Property(int, notify=changed)
    def flasherProgressPercent(self) -> int:
        key = self._flasher_active_key()
        return self._flasher_progress.get(key, {}).get("percent", 0) if key else 0

    @Property("QVariantList", notify=changed)
    def flasherLog(self) -> list[dict[str, str]]:
        key = self._flasher_active_key()
        return self._flasher_log.get(key, []) if key else []

    @Slot()
    def startFlasherFlash(self) -> None:
        key = self._flasher_active_key()
        if key is None:
            return
        target = self._flasher_target(key)
        file = self._flasher_file.get(key)
        if target is None or not file:
            return
        asyncio.ensure_future(self._run_flash(key, target, file))

    async def _run_flash(self, key: str, target: CanOtaTarget, file: dict) -> None:
        self._flasher_flashing[key] = True
        self._flasher_push_log(key, f"{_('LBL_FLASH_START')}: {file['name']} - {hop_description(target)}")
        self.changed.emit()
        try:
            if self._flasher_is_hardware:
                resolved = resolve_hardware_target(target)
                if not resolved:
                    self._flasher_push_log(key, _("LBL_HARDWARE_TARGET_UNREACHABLE"), "error")
                    return
                self._flasher_progress[key] = {"label": _("FLASHER_PROGRESS_CONNECTING"), "percent": 0}
                self.changed.emit()
                version_major, _sep, version_minor = (file.get("version_tag") or "0.0").partition(".")
                hardware_id_number = int(file["hardware_id"], 0) if file.get("hardware_id") else 0
                conn = self._controller.active_connection
                if conn is None:
                    self._flasher_push_log(key, _("LBL_NO_RESPONSE"), "error")
                    return
                result = await hardware_start_flash(
                    conn, target, file["bytes"],
                    int(version_major) if version_major.isdigit() else 0,
                    int(version_minor) if version_minor.isdigit() else 0,
                    hardware_id_number,
                )
                if result.success:
                    self._flasher_progress[key] = {"label": _("FLASHER_PROGRESS_DONE"), "percent": 100}
                    self._flasher_push_log(key, _("LBL_FLASH_DONE"), "ok")
                    self._flasher_apply_patch(key, {"firmwareVersion": file["name"].removesuffix(".bin")})
                else:
                    self._flasher_push_log(key, f"{_('LBL_FLASH_HARDWARE_FAILED')}: {result.reason}", "error")
                return

            opts = FlashOptions(allow_downgrade=self._flasher_allow_downgrade.get(key, False), erase_fram=self._flasher_erase_fram.get(key, False))
            last_phase = None
            async for progress in mock_flash(target, file["bytes"], opts):
                last_phase = progress.phase
                suffix = f" ({progress.pages_sent}/{progress.pages_total})" if progress.pages_total > 1 and progress.phase == "transferring" else ""
                self._flasher_progress[key] = {"label": f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')}{suffix} - {progress.percent}%", "percent": progress.percent}
                self.changed.emit()
                if progress.phase == "transferring" and progress.pages_sent % 5 != 0 and progress.pages_sent != progress.pages_total:
                    continue
                self._flasher_push_log(key, f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')} ({progress.pages_sent}/{progress.pages_total})", "error" if progress.phase == "error" else "info")
            if last_phase != "error":
                self._flasher_push_log(key, _("LBL_FLASH_DONE"), "ok")
                self._flasher_apply_patch(key, {"firmwareVersion": file["name"].removesuffix(".bin")})
        finally:
            self._flasher_flashing[key] = False
            self.changed.emit()

    # -- Tester --------------------------------------------------------------

    def _tester_active_key(self) -> str | None:
        return self._active_key if self._active_key in _TESTER_TIERS else None

    def _on_tester_state_changed(self, state: HydraState) -> None:
        self._flasher_is_hardware = state.can_ota_transport == "hardware"  # one real shared deployment setting, not per-instance
        for key in _TESTER_TIERS:
            ctrl = state.active_controller
            self._tester_controller[key] = ctrl
            robots = ctrl.robots if ctrl is not None else []
            ids = {r.id for r in robots}
            if self._tester_robot_id[key] not in ids:
                self._tester_robot_id[key] = robots[0].id if robots else None
        self.changed.emit()

    def _tester_current_robot(self, key: str) -> RobotView | None:
        ctrl = self._tester_controller.get(key)
        rid = self._tester_robot_id.get(key)
        if ctrl is None or rid is None:
            return None
        for r in ctrl.robots:
            if r.id == rid:
                return r
        return None

    def _tester_target(self, key: str) -> CanOtaTarget | None:
        ctrl = self._tester_controller.get(key)
        if ctrl is None:
            return None
        tier = self._tester_tier[key]
        if tier == "kinematicBrain":
            return CanOtaTarget(controller_name=ctrl.name, tier=tier)
        robot = self._tester_current_robot(key)
        if robot is None:
            return None
        robots = ctrl.robots
        index0 = next((i for i, r in enumerate(robots) if r.id == robot.id), -1)
        if index0 < 0:
            return None
        return CanOtaTarget(controller_name=ctrl.name, tier=tier, robot_id=robot.id, robot_name=robot.model, robot_index0=index0)

    def _tester_board_state(self, key: str) -> dict:
        ctrl = self._tester_controller.get(key)
        tier = self._tester_tier[key]
        if tier == "kinematicBrain":
            return ctrl.kinematic_brain if ctrl is not None else {}
        robot = self._tester_current_robot(key)
        return robot.module(tier) if robot is not None else {}

    def _tester_stop_monitor(self, key: str) -> None:
        task = self._tester_monitor_task.get(key)
        if task is not None:
            task.cancel()
            self._tester_monitor_task[key] = None

    def _tester_reset_for_new_target(self, key: str) -> None:
        """Matches Tester.tsx's own resetForTargetKey effect - switching
        tier/robot drops any in-flight self-test/monitor state for the
        PREVIOUS target rather than leaving it displayed against a now-
        different one."""
        self._tester_stop_monitor(key)
        self._tester_fram_state[key] = None
        self._tester_testing[key] = False
        self._tester_self_test_steps[key] = []
        self._tester_frames[key] = []
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def testerTierOptions(self) -> list[dict[str, object]]:
        key = self._tester_active_key()
        if key is None:
            return []
        robot = self._tester_current_robot(key)
        expansion_available = has_advanced_expansion((robot.module("urtcHead") if robot else {}).get("expansionBoardType"))
        result = []
        for t in _TESTER_TIERS[key]:
            enabled = True
            if t == "urtcHead":
                enabled = bool(robot and robot.urtc_connected)
            elif t == "urtcExpansion":
                enabled = expansion_available
            result.append({"key": t, "label": f"{_(_TIER_LABEL_KEYS[t])} ({chip_name_for(t)})", "enabled": enabled})
        return result

    @Property(str, notify=changed)
    def testerTier(self) -> str:
        key = self._tester_active_key()
        return self._tester_tier.get(key, "") if key else ""

    @Slot(str)
    def selectTesterTier(self, tier: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_tier[key] = tier
            self._tester_reset_for_new_target(key)

    @Property(bool, notify=changed)
    def testerNeedsRobotSlot(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] != "kinematicBrain"

    @Property("QVariantList", notify=changed)
    def testerRobotOptions(self) -> list[dict[str, str]]:
        key = self._tester_active_key()
        if key is None:
            return []
        ctrl = self._tester_controller.get(key)
        robots = ctrl.robots if ctrl is not None else []
        return [{"id": r.id, "label": f"{slot_label(i)} - {r.model}"} for i, r in enumerate(robots)]

    @Property(str, notify=changed)
    def testerSelectedRobotId(self) -> str:
        key = self._tester_active_key()
        return (self._tester_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectTesterRobot(self, robot_id: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_robot_id[key] = robot_id or None
            self._tester_reset_for_new_target(key)

    @Property(str, notify=changed)
    def testerHopDescription(self) -> str:
        key = self._tester_active_key()
        if key is None:
            return ""
        target = self._tester_target(key)
        return hop_description(target) if target else ""

    @Property(bool, notify=changed)
    def testerSimulatedNoteVisible(self) -> bool:
        return self._flasher_is_hardware

    @Property(bool, notify=changed)
    def testerQueryEnabled(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_target(key) is not None

    @Property(str, notify=changed)
    def testerVersionLabel(self) -> str:
        key = self._tester_active_key()
        if key is None:
            return _("LBL_NO_VERSION_KNOWN")
        board = self._tester_board_state(key)
        if board.get("firmwareVersion"):
            return f"{_('LBL_CURRENT_VERSION')}: {board.get('firmwareVersion', '?')}"
        return _("LBL_NO_VERSION_KNOWN")

    @Slot()
    def testerQueryVersion(self) -> None:
        key = self._tester_active_key()
        if key is None:
            return
        target = self._tester_target(key)
        if target is None:
            return
        asyncio.ensure_future(self._run_tester_query(key, target))

    async def _run_tester_query(self, key: str, target: CanOtaTarget) -> None:
        if self._flasher_is_hardware:
            conn = self._controller.active_connection
            if conn is None:
                return
            result = await hardware_query_version(conn, target)
        else:
            result = await mock_query_version(target)
        if not result.online:
            return
        patch = {"firmwareVersion": result.firmware_version, "bootloaderVersion": result.bootloader_version, "hardwareId": result.hardware_id}
        ctrl = self._tester_controller.get(key)
        tier = self._tester_tier[key]
        if tier == "kinematicBrain" and ctrl is not None:
            ctrl.set_kinematic_brain(patch)
        elif tier == "urtcHead":
            robot = self._tester_current_robot(key)
            if robot is not None:
                if result.expansion_board_type is not None:
                    patch["expansionBoardType"] = result.expansion_board_type
                robot.set_module("urtcHead", {**robot.module("urtcHead"), **patch})
        else:
            robot = self._tester_current_robot(key)
            if robot is not None:
                robot.set_module(tier, patch)
        self._controller.push_active_state()
        self.changed.emit()

    @Property(bool, notify=changed)
    def testerShowGlobal(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] == "urtcHead"

    @Property(bool, notify=changed)
    def testerShowFram(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] in ("controllerBoard", "urtcHead")

    @Property(bool, notify=changed)
    def testerShowTelemetry(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] == "urtcHead" and self._tester_current_robot(key) is not None

    @Property(str, notify=changed)
    def testerStatusColor(self) -> str:
        key = self._tester_active_key()
        return self._tester_status_color.get(key, "#00ff66") if key else "#00ff66"

    @Slot(str)
    def setTesterStatusColor(self, color: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_status_color[key] = color
            self.changed.emit()

    @Property(bool, notify=changed)
    def testerRingOn(self) -> bool:
        key = self._tester_active_key()
        return self._tester_ring_on.get(key, False) if key else False

    @Slot()
    def toggleTesterRing(self) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_ring_on[key] = not self._tester_ring_on[key]
            self.changed.emit()

    @Property(str, notify=changed)
    def testerOledMode(self) -> str:
        key = self._tester_active_key()
        return self._tester_oled_mode.get(key, "standard") if key else "standard"

    @Slot(str)
    def setTesterOledMode(self, mode: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_oled_mode[key] = mode

    @Property(str, notify=changed)
    def testerExpansionLabel(self) -> str:
        key = self._tester_active_key()
        if key is None:
            return ""
        robot = self._tester_current_robot(key)
        expansion_type = (robot.module("urtcHead") if robot else {}).get("expansionBoardType")
        if expansion_type is None:
            return ""
        expansion_available = has_advanced_expansion(expansion_type)
        label = _("LBL_EXPANSION_NONE") if expansion_type == 0 else f"#{expansion_type}" + (f" ({_(_TIER_LABEL_KEYS['urtcExpansion'])})" if expansion_available else "")
        return f"{_('LBL_EXPANSION_BOARD')}: {label}"

    @Property(str, notify=changed)
    def testerFramStateLabel(self) -> str:
        key = self._tester_active_key()
        state = self._tester_fram_state.get(key) if key else None
        if state is None:
            return _("LBL_FRAM_UNKNOWN")
        return _("LBL_FRAM_VALID") if state else _("LBL_FRAM_EMPTY")

    @Slot()
    def testerFramQuery(self) -> None:
        key = self._tester_active_key()
        if key is not None:
            asyncio.ensure_future(self._run_tester_fram_query(key))

    async def _run_tester_fram_query(self, key: str) -> None:
        await asyncio.sleep(0.15)
        self._tester_fram_state[key] = random.random() > 0.3
        self.changed.emit()

    @Slot()
    def testerFramErase(self) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_fram_state[key] = False
            self.changed.emit()

    @Property(str, notify=changed)
    def testerTelemetryTitle(self) -> str:
        key = self._tester_active_key()
        robot = self._tester_current_robot(key) if key else None
        return f"{_('LBL_TOOL_TELEMETRY')} - {robot.tool}" if robot is not None else ""

    @Property(str, notify=changed)
    def testerTelemetryLabel(self) -> str:
        key = self._tester_active_key()
        robot = self._tester_current_robot(key) if key else None
        return _(f"LBL_TELEMETRY_{_category_for(robot.tool).upper()}") if robot is not None else ""

    @Property(bool, notify=changed)
    def testerTesting(self) -> bool:
        key = self._tester_active_key()
        return self._tester_testing.get(key, False) if key else False

    @Property("QVariantList", notify=changed)
    def testerSelfTestSteps(self) -> list[dict[str, object]]:
        key = self._tester_active_key()
        return self._tester_self_test_steps.get(key, []) if key else []

    @Slot()
    def runTesterSelfTest(self) -> None:
        key = self._tester_active_key()
        if key is None:
            return
        target = self._tester_target(key)
        if target is None or self._tester_testing.get(key):
            return
        self._tester_testing[key] = True
        self._tester_self_test_steps[key] = []
        self.changed.emit()
        asyncio.ensure_future(self._run_tester_self_test(key, target))

    async def _run_tester_self_test(self, key: str, target: CanOtaTarget) -> None:
        try:
            async for step in mock_self_test(target):
                self._tester_self_test_steps[key] = [
                    *self._tester_self_test_steps[key],
                    {"label": _(f"LBL_SELFTEST_{step.label_key.upper()}"), "passed": step.passed},
                ]
                self.changed.emit()
        finally:
            self._tester_testing[key] = False
            self.changed.emit()

    @Property(bool, notify=changed)
    def testerMonitorRunning(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_monitor_task.get(key) is not None

    @Property("QVariantList", notify=changed)
    def testerFrames(self) -> list[dict[str, object]]:
        key = self._tester_active_key()
        frames = self._tester_frames.get(key, []) if key else []
        return [
            {
                "time": time.strftime("%H:%M:%S", time.localtime(f.timestamp)),
                "id": f"0x{f.id:X}",
                "dlc": f.dlc,
                "data": " ".join(f"{b:02X}" for b in f.data),
            }
            for f in reversed(frames)
        ]

    @Slot()
    def toggleTesterMonitor(self) -> None:
        key = self._tester_active_key()
        if key is None:
            return
        if self._tester_monitor_task.get(key) is not None:
            self._tester_stop_monitor(key)
            self.changed.emit()
            return
        target = self._tester_target(key)
        if target is None:
            return
        self._tester_frames[key] = []
        self._tester_monitor_task[key] = asyncio.ensure_future(self._run_tester_monitor(key, target))
        self.changed.emit()

    async def _run_tester_monitor(self, key: str, target: CanOtaTarget) -> None:
        try:
            async for frame in mock_bus_monitor(target):
                self._tester_frames[key] = [*self._tester_frames[key][-99:], frame]
                self.changed.emit()
        except asyncio.CancelledError:
            return

    # -- Viewport (3D) -----------------------------------------------------

    def _ensure_viewport_renderer(self):
        # Real, honest degradation, not a hypothetical: constructing a
        # genuine QOpenGLContext/QOffscreenSurface can fail for real (no
        # OpenGL 3.3 core profile available at all - confirmed for real
        # under this session's own headless `offscreen` QPA platform,
        # which cannot create a real GL context here regardless of
        # QT_OPENGL/QT_ANGLE_PLATFORM). Letting that exception propagate
        # uncaught out of a real Qt signal handler (this is reached from
        # _select_robot(), itself reached from a real robot_selected-
        # style signal in production) would be a real crash risk for
        # something a user can't do anything about - caught once, reported
        # honestly via viewportUnsupportedMessage, never retried
        # endlessly (a real GL capability failure doesn't fix itself
        # between calls).
        if self._viewport_renderer is None and not self._viewport_render_failed:
            try:
                from hydra_suite.render.viewport import OffscreenRobotRenderer

                self._viewport_renderer = OffscreenRobotRenderer()
            except Exception as exc:
                self._viewport_render_failed = True
                self._viewport_render_error = str(exc)
        return self._viewport_renderer

    def _on_viewport_state_changed(self, _state: HydraState) -> None:
        # _on_robot_state_changed (Robot Control's own real handler,
        # connected to the exact same signal) already refreshed
        # self._active_robots_cache/_selected_robot_id by the time this
        # runs - Qt delivers a signal to every connected slot in connection
        # order, and this one was connected after that one - so
        # _selected_robot() below already reflects the current tick.
        self._render_viewport_frame()

    def _render_viewport_frame(self) -> None:
        robot = self._selected_robot()
        if robot is None or robot.model not in _VIEWPORT_SUPPORTED_MODELS:
            return  # matches ViewportPanel._apply()'s own real gate - nothing to render
        renderer = self._ensure_viewport_renderer()
        if renderer is None:
            self.changed.emit()  # real GL construction just failed - let viewportUnsupportedMessage's own binding pick that up
            return
        if robot.model != self._viewport_current_model:
            renderer.set_robot_model(robot.model)
            self._viewport_current_model = robot.model
        renderer.set_joints_deg(robot.joints)
        self._render_viewport_frame_only(renderer)

    def _render_viewport_frame_only(self, renderer=None) -> None:
        """Re-renders with whatever pose/model/camera state the renderer
        already has - used both by _render_viewport_frame() above (after a
        real model/joint change) and by the orbit/pan/zoom Slots below
        (camera-only changes, no model/joint work needed first)."""
        renderer = renderer or self._viewport_renderer
        if renderer is None:
            return
        image = renderer.render()
        if self._viewport_frame_provider is not None:
            self._viewport_frame_provider.set_image(image)
        self._viewport_frame_version += 1
        self._viewportChanged.emit()

    @Property(bool, notify=changed)
    def viewportHasRobot(self) -> bool:
        return self._selected_robot() is not None

    @Property(bool, notify=changed)
    def viewportSupported(self) -> bool:
        if self._viewport_render_failed:
            return False
        robot = self._selected_robot()
        return robot is not None and robot.model in _VIEWPORT_SUPPORTED_MODELS

    @Property(str, notify=changed)
    def viewportUnsupportedMessage(self) -> str:
        robot = self._selected_robot()
        if robot is None:
            return _("LBL_NO_ROBOT_SELECTED")
        if self._viewport_render_failed:
            return f"3D rendering unavailable on this machine: {self._viewport_render_error}"
        if robot.model not in _VIEWPORT_SUPPORTED_MODELS:
            return _("MSG_UNSUPPORTED_MODEL", model=robot.model, models=", ".join(sorted(_VIEWPORT_SUPPORTED_MODELS)))
        return ""

    @Property(int, notify=_viewportChanged)
    def viewportFrameVersion(self) -> int:
        return self._viewport_frame_version

    @Slot(float, float)
    def viewportOrbit(self, dx: float, dy: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.orbit(dx, dy)
        self._render_viewport_frame_only()

    @Slot(float, float)
    def viewportPan(self, dx: float, dy: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.pan(dx, dy)
        self._render_viewport_frame_only()

    @Slot(float)
    def viewportZoom(self, factor: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.zoom(factor)
        self._render_viewport_frame_only()

    @Slot(int, int)
    def viewportResize(self, width: int, height: int) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.resize(width, height)
        self._render_viewport_frame_only()

    # -- Overview --------------------------------------------------------

    @Property(str, notify=changed)
    def overviewName(self) -> str:
        return self._overview_name

    @Property(str, notify=changed)
    def overviewIp(self) -> str:
        return self._overview_ip

    @Property(str, notify=changed)
    def overviewRobotCount(self) -> str:
        return self._overview_robot_count

    @Property(str, notify=changed)
    def overviewOnlineCount(self) -> str:
        return self._overview_online_count

    @Property(str, notify=changed)
    def overviewCpu(self) -> str:
        return self._overview_cpu

    @Property(str, notify=changed)
    def overviewMem(self) -> str:
        return self._overview_mem

    @Property(str, notify=changed)
    def overviewTemp(self) -> str:
        return self._overview_temp

    @Property(str, notify=changed)
    def overviewUptime(self) -> str:
        return self._overview_uptime

    @Property("QVariantList", notify=changed)
    def overviewRobots(self) -> list[dict[str, object]]:
        return self._overview_robots

    def _on_overview_metrics_changed(self, metrics: dict) -> None:
        cpu = metrics.get("cpu_load")
        mem = metrics.get("memory_usage")
        temp = metrics.get("temp")
        uptime = metrics.get("uptime")
        self._overview_cpu = f"{cpu}%" if cpu is not None else "-"
        self._overview_mem = f"{mem}%" if mem is not None else "-"
        self._overview_temp = f"{temp:.0f}°C" if isinstance(temp, (int, float)) else "-"
        if isinstance(uptime, (int, float)):
            hours, rem = divmod(int(uptime), 3600)
            minutes = rem // 60
            self._overview_uptime = f"{hours}h {minutes}m"
        else:
            self._overview_uptime = "-"
        self.changed.emit()

    def _on_overview_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        if active is None:
            self._overview_name = "-"
            self._overview_ip = "-"
            self._overview_robot_count = "-"
            self._overview_online_count = "-"
            self._overview_robots = []
            self.changed.emit()
            return
        robots = active.robots
        online = sum(1 for r in robots if r.online)
        self._overview_name = active.name
        self._overview_ip = active.ip
        self._overview_robot_count = str(len(robots))
        self._overview_online_count = f"{online} / {len(robots)}"
        self._overview_robots = [
            {
                "id": r.id,
                "model": r.model,
                "role": r.role,
                "status": _("STATUS_ONLINE") if r.online else _("STATUS_OFFLINE"),
                "online": r.online,
                "speedAccel": f"{r.speed:.0f}% / {r.acceleration:.0f}%",
            }
            for r in robots
        ]
        self.changed.emit()


def run_qtquick() -> int:
    # Same real reason main.py's own classic entry point sets this before
    # constructing its QApplication: Qt6's default rounding policy snaps a
    # fractional OS scale factor (125%/150%/175%, common on a 27"-32" 4K
    # monitor) to the nearest whole integer, which reads as slightly
    # blurry/mis-sized fixed-pixel controls. PassThrough applies the OS's
    # exact factor instead - must be set before the QGuiApplication exists.
    from PySide6.QtCore import Qt

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC SUITE")
    app.setApplicationDisplayName("HYDRA-UMC SUITE")
    app.setOrganizationName("Electro Hobby 3D")
    for icon_path in (IMAGES_DIR / "HYDRA_UMC_ICON.ico", IMAGES_DIR / "HYDRA_UMC_ICON.svg"):
        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                app.setWindowIcon(icon)
                break
    QQuickStyle.setStyle("Basic")

    # Same qasync integration main.py's own classic entry point already
    # relies on for every `async def` in app.py/net/client.py/
    # net/discovery.py - a QGuiApplication (no QApplication/QtWidgets)
    # needs the same real event-loop wiring, not a different one.
    import asyncio

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = SuiteController()
    frame_provider = CameraFrameProvider()
    viewport_frame_provider = ViewportFrameProvider()
    bridge = SuiteQtBridge(controller, frame_provider=frame_provider, viewport_frame_provider=viewport_frame_provider)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("cameraFrames", frame_provider)
    engine.addImageProvider("viewportFrame", viewport_frame_provider)
    engine.rootContext().setContextProperty("suiteBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        return 1

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(run_qtquick())
