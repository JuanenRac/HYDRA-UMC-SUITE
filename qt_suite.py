# =============================================================================
# HYDRA-UMC SUITE - qt_suite.py (Qt Quick command-deck entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick interface of HYDRA-UMC SUITE: a standalone ApplicationWindow with a navigation sidebar (the same
root menu and Industrial / URTC / HYDRA-UMC submenus as HYDRA-UMC-STUDIO) and a single content area that shows one
panel at a time. This module is the bridge between that QML and the rest of the program.

hydra_suite.app.SuiteController is a plain QObject with Qt signals and no widget code, so it serves this interface
directly (the global STOP is one of its methods). SuiteQtBridge below only owns what has no meaning outside a screen:
which panel is open, the display state of each panel, the notices shown to the operator, and the translated texts.
Everything about the servers themselves (state, commands, reservations, limits) stays in SuiteController and
HydraConnection, so a check can exercise it without a window.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import json
import os
import random
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
import qasync
from PySide6.QtCore import Property, QDateTime, QObject, QSize, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickControls2 import QQuickStyle

from hydra_suite import __version__, access, logging_handler, robot_edits
from hydra_suite.scheduler import TICK_MS as SCHEDULER_TICK_MS, PollScheduler
from hydra_suite.app import StopAllSummary, SuiteController, describe_stop_all
from hydra_suite.panel_logic import stop_state as stop_state_logic
from hydra_suite.extras_bridge import SuiteExtras
from hydra_suite.can_ota import (
    GITHUB_FIRMWARE_REPO,
    CanOtaTarget,
    FlashOptions,
    chip_name_for,
    crc32,
    download_github_firmware,
    fetch_github_firmware_releases,
    hardware_fram_operation,
    FramOperationResult,
    fram_erase_word_matches,
    FRAM_ERASE_WORD,
    hardware_query_version,
    flash_preflight,
    flash_signing_options,
    hardware_start_flash,
    normalize_signature,
    has_advanced_expansion,
    hop_description,
    parse_version_tag,
    mock_bus_monitor,
    mock_flash,
    mock_query_version,
    mock_self_test,
    resolve_hardware_target,
    slot_label,
)
from hydra_suite.credentials import CredentialStore, keyring_backend
from hydra_suite.diagnostics import build_bundle
from hydra_suite.i18n import AVAILABLE_LANGUAGES, CONFIG_FILE_PATH, _, current_language, load_config, save_config
from hydra_suite import firmware_signature, reach
from hydra_suite.net import tls_pin
from hydra_suite import i18n as i18n_module
from hydra_suite.joint_limits import joint_range_deg
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
from hydra_suite.panel_logic.admin_clients import _relative_duration
from hydra_suite.panel_logic.admin_logs import _extract_tag
from hydra_suite.panel_logic.admin_server import _format_uptime
from hydra_suite.panel_logic import audit_record
from hydra_suite.panel_logic import flasher as flasher_logic
from hydra_suite.panel_logic import connection_history, connector_hub_gate, developer_node_status, ecosystem_health, ecosystem_map, hil_bridge, ops_proposals, planner_identity, planning, server_security, service_identity, setup_screens, detection_hef, help_levels, live_activity, preferences, tool_arms, twin_feed
from hydra_suite.panel_logic import submitted_models
from hydra_suite.panel_logic import totp as totp_panel
from hydra_suite.panel_logic import users as users_panel
from hydra_suite.panel_logic.ai_family_status import AI_FAMILIES
from hydra_suite.panel_logic.atc_tools import (
    JOINT_FIELDS as _ATC_JOINT_FIELDS,
    JOINT_RANGE_DEG as _ATC_JOINT_RANGE_DEG,
    PANEL_GRIDS,
    TABLE_FIELDS as _ATC_TABLE_FIELDS,
    TABLE_RANGE_MM as _ATC_TABLE_RANGE_MM,
    URTC_TOOLS,
    _default_atc_config,
    _default_pos,
)
from hydra_suite.panel_logic.camera_media import parse_mjpeg_frames
from hydra_suite.panel_logic.cameras import (
    GRID_COLUMNS as _CAM_GRID_COLUMNS,
    _STATUS_COLORS as _CAM_STATUS_COLORS,
    _THERMAL_TYPE_OPTIONS as _CAM_THERMAL_TYPE_OPTIONS,
    _USB_TYPE_OPTIONS as _CAM_USB_TYPE_OPTIONS,
    iter_mjpeg_frames,
)
from hydra_suite.panel_logic.ecosystem_services import _HEALTH_COLOR, _STACK_COLOR, _badge_label, _health
from hydra_suite.panel_logic.ecosystem_telemetry import _AGGREGATES, _RANGE_PRESETS
from hydra_suite.panel_logic.downsample_plan import (
    CELLS as DOWNSAMPLE_CELLS,
    draft_to_plan as draft_to_downsample_plan,
    empty_tier as empty_downsample_tier,
    failure_details as downsample_failure_details,
    failure_for as downsample_failure,
    read_effects as read_downsample_effects,
    read_plan as read_downsample_plan,
    validate_plan as validate_downsample_plan,
)
from hydra_suite.panel_logic.flasher import HYDRA_BRAIN_TIERS, URTC_TIERS, _TIER_LABEL_KEYS
from hydra_suite.panel_logic.heated_bed import DEFAULT_AMBIENT_TEMP_C as _HB_DEFAULT_AMBIENT_TEMP_C, DEFAULT_TARGET_TEMP_C as _HB_DEFAULT_TARGET_TEMP_C
from hydra_suite.panel_logic.kinematic_brain_stage import AXIS_KEYS as _KBS_AXIS_KEYS, ENDSTOP_ENTRIES, JOG_STEPS_MM as _KBS_JOG_STEPS_MM, _clamp, complete_stage
from hydra_suite.panel_logic.module_config import DEFAULT_SIZE_MM
from hydra_suite.panel_logic.pick_and_place import MACHINE_LABELS, MACHINE_TYPES, PNP_AXES
from hydra_suite.panel_logic.tester import _category_for
from hydra_suite.vacuum_tables import VACUUM_TABLE_MODELS, vacuum_table_model, select_vacuum_table, vacuum_table_size, resize_vacuum_table
from hydra_suite.heated_beds import HEATED_BED_MODELS, heated_bed_model, heated_bed_size, select_heated_bed, resize_heated_bed
from hydra_suite.racks import rack_geometry, valid_dimension, valid_color
from hydra_suite.panel_logic.viewport import SUPPORTED_MODELS as _VIEWPORT_SUPPORTED_MODELS
from hydra_suite.panel_logic.xy_table import (
    _DISPLAY_DEFAULT_SIZE_MM as _XY_DISPLAY_DEFAULT_SIZE_MM,
    JOG_STEPS_MM as _XY_JOG_STEPS_MM,
    _default_xy_table,
)
from hydra_suite.panel_logic.server_browser import STATUS_DISPLAY_KEYS
from hydra_suite.panel_logic import system_supervisor as supervisor_logic
from hydra_suite.robot_catalog import REAL_ROBOT_MODELS, ROBOT_MANUFACTURERS, robot_model_dof

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).resolve().parent / "images"
QML_PATH = Path(__file__).resolve().parent / "assets" / "qml" / "Main.qml"

# The navigation (root menu and the three submenus) lives in hydra_suite/nav_items.py; the bridge offers exactly those panels
# (tests/verify_qt_suite_shell.py checks it).
from hydra_suite.nav_items import (
    HYDRAUMC_ECOSYSTEM_ITEMS,
    HYDRAUMC_ITEMS,
    INDUSTRIAL_ITEMS,
    ROOT_ITEMS,
    URTC_ITEMS,
)

# Each of the two flasher screens has its own tier set (URTC_TIERS or HYDRA_BRAIN_TIERS, imported, never redeclared).
_FLASHER_TIERS: dict[str, tuple] = {"urtc_flasher": URTC_TIERS, "hydra_flasher": HYDRA_BRAIN_TIERS}
# The two tester screens use the same tier sets as the flashers and, like STUDIO's Tester and Flasher, keep their own
# target selection instead of sharing it.
_TESTER_TIERS: dict[str, tuple] = {"urtc_tester": URTC_TIERS, "hydra_tester": HYDRA_BRAIN_TIERS}
_ATC_TYPE_KEYS: tuple[str, ...] = ("vertical_panel", "horizontal_panel", "revolver")

# Shared shape behind CNC/Laser/HeatedBed/VacuumTable: one parameterization (module key, heading key, machine name) covers all four
# panels instead of repeating the robot selector, enable/disable, size and reset four times. "extra" names which of the two extensions
# (if any) a nav key adds on top (the heated bed's temperature controls, the vacuum table's model list); one shared QML component with
# an `extra` gate does the same job as four subclasses would.
_MODULE_CONFIGS: dict[str, dict[str, object]] = {
    "cnc": {"module_key": "juanenCNC", "machine": "JuanenCNC", "heading": "HEADING_CNC", "reset_size": (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM), "extra": ""},
    "laser": {"module_key": "juanenLaser", "machine": "JuanenLaser", "heading": "HEADING_LASER", "reset_size": (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM), "extra": ""},
    "heated_bed": {"module_key": "heatedBed", "machine": "Heated Bed", "heading": "HEADING_HEATED_BED", "reset_size": (200, 200), "extra": "heated_bed"},
    # Fixed STL dimensions; the first catalog model is also the reset default.
    "vacuum_table": {"module_key": "vacuumTable", "machine": "Vacuum Table", "heading": "HEADING_VACUUM_TABLE", "reset_size": (160, 120), "extra": "vacuum_table"},
}
_RACK_POS_FIELDS = ("j1", "j2", "j3", "j4", "j5", "j6", "tx", "ty")
_ADMIN_CLIENTS_POLL_MS = 5000
# The screens whose controls change global settings (the settings tree, which the server takes from an administrator only).
_SETTINGS_PANELS = frozenset({"xy_table", "rack", "pick_and_place", "kinematic_brain_stage", "cnc", "laser", "heated_bed", "vacuum_table", "atc", "cameras", "robots_catalog", "setup_remote"})
# While the dispatcher has not answered the request to read its file again: seconds between two questions to the server, and how many times at most.
_RELOAD_POLL_S = 2.0
_RELOAD_POLL_TRIES = 8
_ACCESS_POLL_MS = 10000
#: A reservation of this program is renewed when it has less than this left.
_CLAIM_RENEW_BELOW_S = 90
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
    new real frame (the function of panel_logic/camera_media.py, imported
    directly, never duplicated). QML re-fetches on every frame by requesting
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


class MediaFrameProvider(QQuickImageProvider):
    """Feeds the Camera Media panel's own real snapshot/recording frames
    into QML - same real "decode once, serve from a dict, cache-bust via
    a changing key" shape as CameraFrameProvider above, just keyed by an
    opaque string SuiteQtBridge controls (`<cameraId>:<kind>:<filename>:
    <frameIndex>`) instead of a bare camera id, since this provider has
    to hold more than one real image alive at once (every frame of a
    selected recording, not just one live feed per camera). Real network
    I/O (fetch_camera_media_bytes()) happens beforehand, in
    SuiteQtBridge's own async slot - this provider only ever decodes
    already-downloaded bytes into a QImage, never blocks on the network
    itself from inside requestImage()."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._images: dict[str, QImage] = {}

    def set_image(self, key: str, image: QImage) -> None:
        self._images[key] = image

    def clear(self) -> None:
        self._images.clear()

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: N802 - Qt override signature
        image = self._images.get(id)
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
    # The connection lists of the admin screens ("5m ago" durations advance every second while one is on view). Their properties
    # notify this signal, and `changed` forwards to it (see __init__), so whatever still announces a general change updates them;
    # the one-second clock announces only this one, so the other ~300 properties are not evaluated for a clock tick.
    _adminClientsChanged = Signal()
    # Same idea for the reservations and arming of the Robot Control screen (a one-second clock), the health of the ecosystem (a
    # one-second clock) and the Flasher (every state change of the server): their properties notify these, `changed` forwards
    # to them, and their own clocks and handlers announce only them.
    _accessChanged = Signal()
    _ecoHealthChanged = Signal()
    flasherChanged = Signal()
    # The Rack Manager, Pick and Place and XY Table screens: public names, because the robot pickers and the preview of the vacuum table
    # of the screens listen to them from QML.
    rackChanged = Signal()
    pnpChanged = Signal()
    xyTableChanged = Signal()
    # The Module Config, ATC Tools and Tester screens, with the same reasoning: their pickers and canvases listen to them from QML.
    moduleChanged = Signal()
    atcChanged = Signal()
    testerChanged = Signal()
    # The Kinematic Brain Stage and Overview screens.
    kbsChanged = Signal()
    overviewChanged = Signal()
    # Settings and security: the safety limits, the options of the Server Admin screen, the two-step sign-in, the user accounts, the server
    # settings, the audit record, the identity of the server and the local and global settings by role. The safety form of the screen listens
    # to it from QML.
    securityChanged = Signal()
    # The ecosystem screens: telemetry, the tier plan of the data lake, the services, the map and the AI family status. The telemetry chart
    # listens to it from QML.
    ecosystemChanged = Signal()
    # The server logs screen, and the robots catalog with the models submitted to it.
    adminLogsChanged = Signal()
    catalogChanged = Signal()
    _logsChanged = Signal()
    # The server list and the setup screens, and the switches and read-only states of the Server Admin screen (hub gate, plan identity, model reports,
    # Live Activity, twin feed, URTC arms, HIL bridge, watchdog proposals, access options, developer nodes). Their properties notify these, and
    # `changed` forwards to them.
    serversChanged = Signal()
    adminSwitchesChanged = Signal()
    _trajectoryChanged = Signal()
    # A Work with points out of reach that could be loaded scaled: title, message and the label of the button.
    workScaleOffered = Signal(str, str, str)
    # Own dedicated signal (not the shared `changed` above) - a live MJPEG
    # feed can update several times a SECOND per camera, and `changed` is
    # read by dozens of unrelated Properties across every other panel;
    # firing it that often would re-evaluate all of them for no reason.
    _camerasChanged = Signal()
    # The camera cards (their configuration, discovery and state): a state tick of the server and every edit of a card announce this one, and `changed` forwards to it.
    cameraCardsChanged = Signal()
    # Same real reasoning as _camerasChanged above - a live 3D render can
    # update every real joint tick.
    _viewportChanged = Signal()
    # Own dedicated signal - a real recording's own playback timer can
    # advance several times a second while playing, same reasoning as
    # _camerasChanged/_viewportChanged above.
    _cameraMediaChanged = Signal()

    def __init__(
        self,
        controller: SuiteController,
        frame_provider: "CameraFrameProvider | None" = None,
        viewport_frame_provider: "ViewportFrameProvider | None" = None,
        media_frame_provider: "MediaFrameProvider | None" = None,
        credential_store: "CredentialStore | None" = None,
        catalog_frame_provider: "ViewportFrameProvider | None" = None,
    ) -> None:
        super().__init__()
        self.changed.connect(self._adminClientsChanged)  # a general change still updates the connection lists
        self.changed.connect(self._accessChanged)
        self.changed.connect(self.serversChanged)
        self.changed.connect(self.adminSwitchesChanged)
        self.changed.connect(self._ecoHealthChanged)
        self.changed.connect(self.flasherChanged)
        self.changed.connect(self.rackChanged)
        self.changed.connect(self.pnpChanged)
        self.changed.connect(self.xyTableChanged)
        self.changed.connect(self.moduleChanged)
        self.changed.connect(self.atcChanged)
        self.changed.connect(self.testerChanged)
        self.changed.connect(self.kbsChanged)
        self.changed.connect(self.overviewChanged)
        self.changed.connect(self.securityChanged)
        self.changed.connect(self.ecosystemChanged)
        self.changed.connect(self.adminLogsChanged)
        self.changed.connect(self.catalogChanged)
        self.changed.connect(self.cameraCardsChanged)
        self._controller = controller
        self._credentials = credential_store
        self._catalog_frame_provider = catalog_frame_provider
        self._frame_provider = frame_provider
        self._viewport_frame_provider = viewport_frame_provider
        self._media_frame_provider = media_frame_provider
        self._vacuum_frame_provider = ViewportFrameProvider()
        self._vacuum_renderer = None
        self._vacuum_preview_version = 0
        self._vacuum_preview_error = ""
        self._vacuum_preview_model = None
        self._rack_preview_id = "rack1"

        self._active_key = "overview"
        self._connection_status = "disconnected"

        # -- Logs: an unbounded _all_entries plus a currently-matching-filter _displayed_entries, both appended to in O(1) per new
        # record; only a filter change re-derives _displayed_entries from _all_entries in one O(n) pass. The QML-facing Property caps
        # to the most recent 500 for render performance (a ListView with the full unbounded history would be slow to lay out). --
        self._log_level_filter: str | None = None
        self._log_search_filter = ""
        self._all_log_entries: list[_LogEntry] = []
        self._displayed_log_entries: list[_LogEntry] = []
        handler = logging_handler.install()
        handler.emitter.record_logged.connect(self._on_log_record)

        # -- Overview --
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

        # -- Global STOP (always visible in the header, F12): the same
        # SuiteController.stop_all() the classic window calls, and the same
        # describe_stop_all() text. A clean result hides itself; anything
        # else stays until a later STOP confirms.
        self._stop_all_text = ""
        self._stop_all_detail = ""
        self._stop_all_severity = ""
        self._stop_all_clean_timer = QTimer(self)
        self._stop_all_clean_timer.setSingleShot(True)
        self._stop_all_clean_timer.timeout.connect(self._clear_stop_all_text)
        controller.stop_all_changed.connect(self._on_stop_all_changed)
        controller.connection_stop_state_changed.connect(lambda _cid: self.changed.emit())

        # -- Servers: STATUS_DISPLAY_KEYS is imported from panel_logic/server_browser.py rather than copied, so the status wording
        # is written once. --
        self._server_statuses: dict[str, str] = {}
        self._server_login: dict[str, tuple[bool, str]] = {}
        self._scanning = False
        self._scan_status_text = ""
        controller.connections_changed.connect(self._on_servers_changed)
        controller.active_connection_changed.connect(lambda _cid: self._on_servers_changed())
        controller.connection_status_changed.connect(self._on_server_status)
        controller.connection_login_changed.connect(self._on_server_login)

        # -- Robot Control: a Slider sets the exact value of the joint, so there is no custom-painted dial. --
        self._selected_robot_id: str | None = None
        self._active_robots_cache: list[RobotView] = []
        # Trajectory: a local point recorder that exports and imports STUDIO's WORKS/*.json format. Reset only when the SELECTED
        # ROBOT ITSELF changes (see _select_robot below), never on every swarm tick.
        self._trajectory_points: list[dict[str, object]] = []
        self._work_files: list[str] = []
        self._pending_work_scale: dict[str, object] | None = None
        controller.active_state_changed.connect(self._on_robot_state_changed)

        # -- AI Family Status: AI_FAMILIES is imported from panel_logic/ai_family_status.py, never duplicated. --
        self._ai_family_projects: list[dict] = []
        self._ai_family_ai_hailo: dict[str, str] = {}
        self._ai_family_status_text = _("LBL_ES_NOT_LOADED")
        self._ai_family_refreshing = False
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_ai_family()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_ai_family()))
        asyncio.ensure_future(self._refresh_ai_family())

        # -- Admin Clients: _relative_duration is imported from panel_logic/admin_clients.py, never duplicated. A 5 s data poll and a
        # separate 1 s tick that only re-emits changed, so the "Xm ago" durations advance smoothly between polls. --
        self._admin_clients: list[dict] = []
        self._connection_clients: list[dict] = []
        self._connection_events: list[dict] = []
        self._connection_status_text = ""
        self._admin_clients_status_text = _("MSG_ADMIN_ONLY")
        # One scheduler for every poller (hydra_suite/scheduler.py): a single timer of the interface drives all of them, and
        # only the jobs of the screen on view are started (see _apply_poller_gates).
        self._scheduler = PollScheduler()
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.setInterval(SCHEDULER_TICK_MS)
        self._scheduler_timer.timeout.connect(self._scheduler.tick)
        self._scheduler_timer.start()
        self._admin_clients_timer = self._scheduler.add("admin_clients", _ADMIN_CLIENTS_POLL_MS, lambda: asyncio.ensure_future(self._refresh_admin_clients()))
        self._admin_clients_tick_timer = self._scheduler.add("admin_clients_clock", 1000, self._adminClientsChanged.emit)
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_clients()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_clients()))
        asyncio.ensure_future(self._refresh_admin_clients())

        # -- Admin Logs: _extract_tag is imported from panel_logic/admin_logs.py, never duplicated. "Clear the screen, keep tailing"
        # anchor, live/pause, and tag + search filtering. --
        self._admin_logs_live = True
        self._admin_logs_all_lines: list[str] = []
        self._admin_logs_tag_filter: str | None = None
        self._admin_logs_search = ""
        self._admin_logs_cleared_anchor: str | None = None
        self._admin_logs_cleared_at_empty = False
        self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
        self._admin_logs_timer = self._scheduler.add("admin_logs", _ADMIN_LOGS_POLL_MS, lambda: asyncio.ensure_future(self._refresh_admin_logs()))
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_logs()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_logs()))
        asyncio.ensure_future(self._refresh_admin_logs())

        # -- Admin Server: _format_uptime is imported from panel_logic/admin_server.py, never duplicated. --
        self._admin_server_status_text = _("MSG_ADMIN_ONLY")
        self._admin_server_current_port: int | None = None
        self._admin_server_pending_port_text = ""
        self._admin_server_info: dict[str, object] = {}
        self._security_state: dict | None = None
        self._hub_gate: dict | None = None  # the switch of the connector hub gate that answers a caller without identity (None: no such gate)
        self._hub_gate_message = ""
        self._hub_gate_error = ""
        self._planner_identity: dict | None = None  # the switch of the semantic planner that requires a signed-in person to approve (None: no such planner)
        self._planner_identity_message = ""
        self._planner_identity_error = ""
        self._hil_bridge: dict | None = None  # the switch of the HIL bridge that requires a pass verdict of the twin (None: no such bridge)
        self._hil_bridge_message = ""
        self._hil_bridge_error = ""
        self._ops_proposals: dict | None = None  # the proposals of the node watchdog that wait for a person (None: no channel to the watchdog)
        self._ops_proposals_message = ""
        self._ops_proposals_error = ""
        self._service_identity: dict | None = None  # the identity the server presents to the services (None: a server without the route)
        self._service_identity_message = ""
        self._service_identity_error = ""
        self._detection_hef: dict | None = None  # the switch of the loaded-model reports of DETECTION-HEF (None: a server that predates it)
        self._detection_hef_message = ""
        self._detection_hef_error = ""
        self._live_activity: dict | None = None  # the Live Activity on the lock screen (None: a server that predates it)
        self._live_activity_message = ""
        self._live_activity_error = ""
        self._twin_watching = twin_feed.watching_from_config(load_config())  # whether this computer watches the live state of the twin (off by default, kept in the configuration file)
        self._twin_link = "off"  # connecting, live, or the way the last connection ended (twin_feed.END_*)
        self._twin_state = twin_feed.empty_state()
        self._twin_task: asyncio.Task | None = None
        self._tool_arms: dict | None = None  # the arm state of the URTC tools (None: not read or not available)
        self._tool_arms_error = ""
        self._help_level = help_levels.level_from_config(load_config())  # the level of the Help, kept in the configuration file
        self._help_search = ""
        self._ui_scale = preferences.scale_from_config(load_config())  # the scale of the interface in percent, kept in the configuration file
        self._developer_nodes: dict | None = None  # the latest status of each developer node (None: not read or not available)
        self._developer_nodes_problem = ""
        self._security_message = ""
        self._security_error = ""
        self._planning: dict[str, object] = {}
        self._security_warning = ""
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_server()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_server()))
        asyncio.ensure_future(self._refresh_admin_server())

        # -- Ecosystem Services: _health/_badge_label/_HEALTH_COLOR/_STACK_COLOR are imported from panel_logic/ecosystem_services.py,
        # never duplicated. --
        self._es_projects: list[dict] = []
        self._es_family_filter: str | None = None
        self._es_search = ""
        self._es_actioning_unit: str | None = None
        self._es_action_error: tuple[str, str] | None = None
        self._es_status_text = _("LBL_ES_NOT_LOADED")
        self._es_refreshing = False
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: self.changed.emit())

        # -- Ecosystem Telemetry: _AGGREGATES/_RANGE_PRESETS are imported from panel_logic/ecosystem_telemetry.py, never duplicated.
        # The chart is drawn by hand on a QML Canvas, not with `import QtCharts`: that module crashes on load with PySide6 6.11.1,
        # both offscreen and on screen. --
        self._tel_status_text = ""
        self._tel_running = False
        self._tel_is_aggregate = False
        self._tel_chart_mode = "empty"
        self._tel_line_points: list[dict[str, float]] = []
        self._tel_bars: list[dict[str, object]] = []
        self._tel_stats: dict[str, str] = {}

        # -- Tier plan of the data lake (administrators) --
        self._plan_state: dict | None = None
        self._plan_rows: list[dict[str, str]] = []
        self._plan_delete = False
        self._plan_failure = ""
        self._plan_notice = ""
        self._plan_effects_text = ""
        self._plan_busy = False
        self._plan_confirming = False

        # -- XY Table: _default_xy_table/_DISPLAY_DEFAULT_SIZE_MM/JOG_STEPS_MM are imported from panel_logic/xy_table.py, never
        # duplicated. Its own robot selection, not shared with Robot Control or Trajectory. --
        # Trajectory's own, matching the classic panel's own real
        # independent QComboBox). --
        self._xy_selected_robot_id: str | None = None
        self._xy_jog_step_mm = 10.0
        self._xy_robots_cache: list[RobotView] = []
        controller.active_state_changed.connect(self._on_xy_state_changed)

        # -- Rack Manager: RACK_MAX_CAPACITY/default_rack_system are imported from hydra_suite/models.py, never duplicated. Its own robot
        # selection. --
        self._rack_selected_robot_id: str | None = None
        self._rack_robots_cache: list[RobotView] = []
        controller.active_state_changed.connect(self._on_rack_state_changed)

        # -- Pick and Place: MACHINE_TYPES/MACHINE_LABELS/PNP_AXES are imported from panel_logic/pick_and_place.py, never duplicated.
        # Its own robot selection. The "size-only" branch of STUDIO is not reachable through the Machine combo, so it is not here; a
        # third Machine option would need it on both sides. The 3D live view of the PnP-only mode is not drawn. --
        self._pnp_selected_robot_id: str | None = None
        self._pnp_robots_cache: list[RobotView] = []
        self._pnp_machine_type: str = MACHINE_TYPES[0]
        controller.active_state_changed.connect(self._on_pnp_state_changed)

        # -- Kinematic Brain Stage (AXIS_KEYS/JOG_STEPS_MM/ENDSTOP_ENTRIES/_clamp
        # imported directly from panel_logic/kinematic_brain_stage.py, never duplicated). UNLIKE every other panel ported
        # so far, this is CONTROLLER-level state (one Kinematic Brain per
        # controller) - no robot selector at all, matching that file's
        # own header note. --
        self._kbs_controller: ControllerView | None = None
        self._kbs_jog_step_mm: float = 10.0
        controller.active_state_changed.connect(self._on_kbs_state_changed)

        # -- Module Config (CNC/Laser/HeatedBed/VacuumTable, generic over
        # _MODULE_CONFIGS above). Each of the 4 nav keys keeps its own
        # real, independent robot selection (one selector per panel instance, as in
        # Studio) - one dict entry per
        # key rather than 4 sets of named attributes. Properties/Slots
        # below always operate on whichever key is `self._active_key`
        # right now, since the QML Loader only ever shows one of the 4 at
        # a time. --
        self._module_selected_robot_id: dict[str, str | None] = {k: None for k in _MODULE_CONFIGS}
        self._module_robots_cache: dict[str, list[RobotView]] = {k: [] for k in _MODULE_CONFIGS}
        controller.active_state_changed.connect(self._on_module_state_changed)

        # -- ATC Tools: URTC_TOOLS/PANEL_GRIDS/JOINT_FIELDS/TABLE_FIELDS/*_RANGE_*/_default_atc_config/_default_pos are imported from
        # panel_logic/atc_tools.py, never duplicated. Not built on the generic Module Config shape above: `RobotView.atc` is None or a
        # full ATCConfig (no separate `enabled` flag, 3 layout types). Its own robot selection. `_atc_editing_slot` is None, an int
        # slot index, or the literal string "revolver" for the base pickup position editor. --
        self._atc_selected_robot_id: str | None = None
        self._atc_robots_cache: list[RobotView] = []
        self._atc_editing_slot: int | str | None = None
        self._atc_load_error: str = ""
        controller.active_state_changed.connect(self._on_atc_state_changed)

        # -- Cameras: CAMERA_TYPES/RTSP_DEFAULT_PORT/ip_stream_labels/iter_mjpeg_frames/_USB_TYPE_OPTIONS/_THERMAL_TYPE_OPTIONS/
        # _STATUS_COLORS/GRID_COLUMNS are imported from panel_logic/cameras.py, never duplicated. The live MJPEG feed reaches QML via
        # CameraFrameProvider above, injected here as `frame_provider` (None in an offline or test context, where every frame-touching
        # method below does nothing). The fast-moving per-frame bits use their own `_camerasChanged` signal (not `changed`), so a
        # live video feed never makes every other panel re-evaluate its bindings several times a second. --
        self._camera_stream_tasks: dict[int, asyncio.Task] = {}
        self._camera_stream_urls: dict[int, str | None] = {}
        self._camera_discovery_tasks: dict[int, asyncio.Task] = {}
        self._camera_placeholder: dict[int, tuple[str, str]] = {}
        self._camera_frame_versions: dict[int, int] = {}
        self._camera_status: dict[str, dict] = {}
        self._camera_usb_devices: dict[int, list[dict]] = {}
        self._camera_discovery_status: dict[int, tuple[str, str]] = {}
        self._camera_ptz_error: dict[int, str] = {}
        self._camera_recording_ids: set[int] = set()
        self._camera_capture_error: str = ""
        controller.active_state_changed.connect(self._on_cameras_state_changed)
        self._camera_status_timer = self._scheduler.add("camera_status", 3000, lambda: asyncio.ensure_future(self._poll_camera_status()))
        # -- Camera Media: reuses parse_mjpeg_frames() of panel_logic/camera_media.py (one SOI/EOI marker scan, never a second copy). --
        self._camera_media_items: list[dict] = []
        self._camera_media_filter: int | str = "all"
        self._camera_media_selected: dict | None = None
        self._camera_media_frames: list[bytes] = []
        self._camera_media_frame_index: int = 0
        self._camera_media_frame_interval_ms: int = 100
        self._camera_media_frame_version: int = 0
        self._camera_media_playing: bool = False
        self._camera_media_error: str = ""
        self._camera_media_timer = QTimer(self)
        self._camera_media_timer.timeout.connect(self._advance_camera_media_frame)

        # -- Flasher: can_ota.py's CanOtaTarget/FlashOptions/etc. are imported, never duplicated. Two separate instances
        # (`urtc_flasher`/`hydra_flasher`, keyed by _FLASHER_TIERS above), each with its own tier/robot selection/file/log: one dict per
        # bit of state, keyed by nav key, rather than two sets of named attributes (the same generic-over-nav-key shape as
        # _MODULE_CONFIGS above). `_flasher_is_hardware` is the one exception: a single, GLOBAL deployment setting
        # (HydraState.can_ota_transport), not per instance. --
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
        # what the last version query said about the F-RAM operations (capabilities.fram_erase): None until a query was made
        self._flasher_fram_supported: dict[str, bool | None] = {k: None for k in _FLASHER_TIERS}
        self._flasher_fram_busy: dict[str, bool] = {k: False for k in _FLASHER_TIERS}
        self._flasher_fram_result: dict[str, str] = {k: "" for k in _FLASHER_TIERS}
        controller.active_state_changed.connect(self._on_flasher_state_changed)

        # -- Tester: can_ota.py's mock_self_test()/mock_bus_monitor()/CanFrame/SelfTestStep and _category_for() of panel_logic/tester.py
        # are imported, never duplicated. Its target selection has the shape of the Flasher's but its own _tester_* state dicts. Two
        # instances (`urtc_tester`/`hydra_tester`, _TESTER_TIERS above). The global LED/OLED/F-RAM state is local here: none of it
        # goes through push_active_state(), since no application-level command exists yet to send it anywhere. --
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

        # -- Viewport (3D): uses the same robot selection as Robot Control and Trajectory (_selected_robot_id/_active_robots_cache/
        # _selected_robot() above). Rendering happens through render/viewport.py's OffscreenRobotRenderer, built lazily (the GL setup
        # is not paid for when this panel is never opened) and fed to QML through ViewportFrameProvider, the way CameraFrameProvider
        # feeds live camera frames. --
        self._viewport_renderer = None  # OffscreenRobotRenderer | None, lazy
        self._viewport_render_failed = False
        self._viewport_render_error = ""
        self._viewport_frame_version = 0
        self._viewport_current_model: str | None = None
        controller.active_state_changed.connect(self._on_viewport_state_changed)

        # -- Notices: what the servers report back (a command refused because the robot is reserved by someone
        # else, a jog above the limit, a bed target lowered...) stays on screen until dismissed or 20 seconds pass,
        # so a refusal is never silent. --
        self._shutting_down = False
        self._shutdown_done = False
        self._notice_text = ""
        self._notice_severity = "warn"
        self._notice_timer = QTimer(self)
        self._notice_timer.setSingleShot(True)
        self._notice_timer.setInterval(20000)
        self._notice_timer.timeout.connect(self.dismissNotice)
        controller.connection_error.connect(self._on_connection_error)

        # -- Access: reservations, Live / Sim and the arming of the jog of the selected robot. The reservations and
        # the limits are read from the server every 10 seconds while the Robot Control screen is open. --
        self._access_busy = False
        self._access_robot_timer = self._scheduler.add("access_robot", _ACCESS_POLL_MS, lambda: asyncio.ensure_future(self._refresh_access(poll=True)))
        self._access_tick_timer = self._scheduler.add("access_clock", 1000, self._accessChanged.emit)

        # -- Safety limits (administrators): the form is edited in QML; this keeps what the server holds. --
        self._safety_message = ""
        self._safety_error = ""
        self._safety_loading = False
        self._safety_timer = self._scheduler.add("safety_limits", _ACCESS_POLL_MS, lambda: asyncio.ensure_future(self._refresh_access(poll=True)))
        self._safety_version = 0
        self._safety_form_cache: dict = {}
        # The server pushes the reservations when they change: the screen follows at once.
        controller.connection_claims_changed.connect(lambda _cid: self.changed.emit())

        # -- Audit record (administrators): the lines the server wrote down about the changes that matter, with the
        # chain check. Read when the screen is opened and on demand. --
        self._audit_rows: list[dict[str, object]] = []
        self._audit_chain: list[dict[str, object]] = []
        self._audit_message = ""
        self._audit_error = ""
        self._audit_busy = False
        self._audit_type = ""
        self._audit_robot = ""
        self._audit_limit = audit_record.DEFAULT_LIMIT
        self._audit_last_query: dict = {}
        self._models_rows: list[dict[str, str]] = []
        self._models_list: list[dict[str, str]] = []
        self._models_message = ""
        self._models_error = ""
        self._models_busy = False
        self._users_rows: list[dict[str, object]] = []
        self._users_message = ""
        self._users_error = ""
        self._users_busy = False
        # The second step of the sign-in of the account this window is signed in with (Server Admin).
        self._totp_step = "none"  # none | loading | unsupported | off | enrolling | recovery | on
        self._totp_left = 0
        self._totp_key = ""
        self._totp_qr: dict[str, object] = {"tooLong": False, "path": "", "size": 0, "modules": []}
        self._totp_recovery: list[str] = []
        self._totp_error = ""
        self._totp_message = ""
        self._totp_busy = False
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_totp()))
        controller.connection_login_changed.connect(lambda _cid, ok, _detail: asyncio.ensure_future(self._refresh_totp()) if ok else None)
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_access()))
        controller.connection_login_changed.connect(lambda _cid, ok, _detail: asyncio.ensure_future(self._refresh_access()) if ok else None)

        # -- Robots Catalog: every model the ecosystem has kinematics for, filtered by manufacturer and degrees of
        # freedom, with a live 3D preview and a switch per model (settings.enabledRobotModels). --
        self._catalog_manufacturer = "__all__"
        self._catalog_dof = 0
        self._catalog_selected = REAL_ROBOT_MODELS[0]
        self._catalog_renderer = None
        self._catalog_preview_version = 0
        self._catalog_preview_error = ""
        self._catalog_preview_model: str | None = None
        controller.active_state_changed.connect(lambda _state: self.changed.emit() if self._active_key == "robots_catalog" else None)

        # -- System Supervisor: GET /api/system/supervisor every two seconds while its screen is open, with a
        # rolling window of the last samples for the charts. --
        self._supervisor_history: list[dict] = []
        self._supervisor_view: dict = {}
        self._supervisor_status = _("LBL_ES_NO_ACTIVE_SERVER")
        self._supervisor_live = ""
        self._supervisor_version = 0
        self._supervisor_timer = self._scheduler.add("system_supervisor", supervisor_logic.POLL_MS, lambda: asyncio.ensure_future(self._refresh_supervisor()))
        controller.active_connection_changed.connect(self._on_supervisor_connection_changed)
        # -- Ecosystem health (GET /api/ecosystem/health): the last good answer stays on screen while a later read fails. --
        self._eco_health: dict | None = None
        self._eco_health_filter = "all"
        self._eco_health_status = ""
        self._eco_health_timer = self._scheduler.add("ecosystem_health", ecosystem_health.POLL_MS, lambda: asyncio.ensure_future(self._refresh_eco_health()))
        self._eco_health_tick = self._scheduler.add("ecosystem_health_clock", 1000, self._ecoHealthChanged.emit)
        controller.active_connection_changed.connect(self._on_eco_health_connection_changed)
        # -- Map of the ecosystem: the projects of GET /api/ecosystem/status (shared with the services screen) plus the drift of the health; read only. --
        self._map_filter = "all"
        self._map_search = ""
        self._map_evidence = load_config().get("mapShowEvidence") is True
        self._map_timer = self._scheduler.add("ecosystem_map", ecosystem_map.POLL_MS, lambda: asyncio.ensure_future(self._refresh_map()))
        controller.active_connection_changed.connect(self._on_map_connection_changed)
        # -- Setup screens (installed versions, first-run checklist, sign-in security, remote access, push notifications, history). --
        self._setup_info: dict | None = None
        self._setup_installed: list[dict] = []
        self._setup_failure = ""
        self._setup_busy = False
        self._setup_second_factor: bool | None = None
        self._setup_keys: dict | None = None
        self._setup_push: dict | None = None
        self._setup_allow_rotation = False
        self._setup_notice = ""
        self._setup_notice_ok = True
        self._setup_history_part = "connections"
        self._setup_qr: tuple[str, dict] | None = None
        controller.active_connection_changed.connect(self._on_setup_connection_changed)
        self._apply_poller_gates()
        # The swarm view, the combined mode, the path viewer and the check of versions (hydra_suite/extras_bridge.py).
        self._extras = SuiteExtras(self)

    @Property(QObject, constant=True)
    def extras(self) -> QObject:
        return self._extras

    # -- navigation --------------------------------------------------------

    @Property(str, notify=changed)
    def activePanel(self) -> str:
        return self._active_key

    def _poller_gates(self) -> dict[str, list]:
        """The panel each poller belongs to: it only runs while that panel is the
        one on screen, so the server is not asked for what nobody looks at."""
        return {
            "admin_clients": [self._admin_clients_timer, self._admin_clients_tick_timer],
            "admin_logs": [self._admin_logs_timer],
            "cameras": [self._camera_status_timer],
            "robot": [self._access_robot_timer, self._access_tick_timer],
            "safety_limits": [self._safety_timer],
            "system_supervisor": [self._supervisor_timer],
            "ecosystem_health": [self._eco_health_timer, self._eco_health_tick],
            "ecosystem_map": [self._map_timer],
        }

    def _apply_poller_gates(self) -> None:
        for panel_key, timers in self._poller_gates().items():
            for timer in timers:
                if panel_key == self._active_key:
                    if not timer.isActive():
                        timer.start()
                elif timer.isActive():
                    timer.stop()

    @Slot(str)
    def navigatePanel(self, key: str) -> None:
        if key != self._active_key:
            self._active_key = key
            self._apply_poller_gates()
            if key == "admin_clients":
                asyncio.ensure_future(self._refresh_admin_clients())
            elif key == "admin_logs":
                asyncio.ensure_future(self._refresh_admin_logs())
            elif key == "cameras":
                asyncio.ensure_future(self._poll_camera_status())
            elif key in ("robot", "safety_limits"):
                asyncio.ensure_future(self._refresh_access())
            elif key == "audit_record":
                asyncio.ensure_future(self._refresh_audit(False))
            elif key == "users":
                asyncio.ensure_future(self._refresh_users())
            elif key == "submitted_models":
                asyncio.ensure_future(self._refresh_models())
            elif key == "system_supervisor":
                asyncio.ensure_future(self._refresh_supervisor())
            elif key == "ecosystem_health":
                asyncio.ensure_future(self._refresh_eco_health())
            elif key == "ecosystem_map":
                asyncio.ensure_future(self._refresh_map())
            elif key in setup_screens.SCREEN_KEYS:
                self._setup_allow_rotation = False
                self._setup_notice = ""
                asyncio.ensure_future(self._refresh_setup(key))
            elif key == "ecosystem_planning":
                asyncio.ensure_future(self._probe_planning_switches())
            elif key == "robots_catalog":
                self.refreshCatalogPreview()
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
        return [{"label": _(label_key), "key": key} for label_key, key in pairs]

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def iconSource(self) -> str:
        svg = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        return QUrl.fromLocalFile(str(svg)).toString() if svg.is_file() else ""

    @Slot()
    def stopAll(self) -> None:
        """The global STOP: every robot of every connected server."""
        self._controller.stop_all()

    @Property(str, notify=changed)
    def stopAllText(self) -> str:
        return self._stop_all_text

    @Property(str, notify=changed)
    def stopAllDetail(self) -> str:
        return self._stop_all_detail

    @Property(str, notify=changed)
    def stopAllSeverity(self) -> str:
        return self._stop_all_severity

    def _stop_state_view(self):
        """The one stop state of every connected server, summed up (None until one has spoken)."""
        return stop_state_logic.sum_up([conn.stop_state for conn in self._controller.connections.values() if conn.stop_state is not None])

    @Property(str, notify=changed)
    def stopStateText(self) -> str:
        return stop_state_logic.badge_text(self._stop_state_view())

    @Property(str, notify=changed)
    def stopStateDetail(self) -> str:
        return stop_state_logic.badge_tooltip(self._stop_state_view())

    @Property(str, notify=changed)
    def stopStateSeverity(self) -> str:
        return stop_state_logic.severity(self._stop_state_view())

    @Slot(object)
    def _on_stop_all_changed(self, summary: StopAllSummary) -> None:
        headline, details, severity = describe_stop_all(summary)
        self._stop_all_clean_timer.stop()
        self._stop_all_text = headline
        self._stop_all_detail = "\n".join(details)
        self._stop_all_severity = severity
        if severity == "ok":
            self._stop_all_clean_timer.start(6000)
        self.changed.emit()

    def _clear_stop_all_text(self) -> None:
        self._stop_all_text = ""
        self._stop_all_detail = ""
        self._stop_all_severity = ""
        self.changed.emit()

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

    @Property("QVariantList", notify=serversChanged)
    def serverRows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        active_id = self._controller._active_id  # the same field panel_logic/server_browser.py reads
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
                "remembered": self._credentials is not None and self._credentials.is_remembered(conn.info.host, conn.info.port),
            })
        return rows

    @Property(bool, notify=serversChanged)
    def serverScanning(self) -> bool:
        return self._scanning

    @Property(str, notify=serversChanged)
    def serverScanStatus(self) -> str:
        return self._scan_status_text

    @Property(int, constant=True)
    def defaultServerPort(self) -> int:
        return DEFAULT_PORT

    def _on_servers_changed(self) -> None:
        self.changed.emit()

    def _on_server_status(self, conn_id: str, status: str) -> None:
        self._server_statuses[conn_id] = status
        self.serversChanged.emit()

    def _on_server_login(self, conn_id: str, ok: bool, detail: str) -> None:
        self._server_login[conn_id] = (ok, detail)
        self.serversChanged.emit()

    @Slot()
    def scanServers(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._scan_status_text = _("STATUS_SCANNING")
        self.serversChanged.emit()
        asyncio.ensure_future(self._run_server_scan())

    async def _run_server_scan(self) -> None:
        # discover_servers() runs the brute-force subnet scan and real
        # mDNS/Bonjour discovery CONCURRENTLY (net/discovery.py's own
        # header comment) and dedupes between them - same real call
        # the scan of the servers screen makes, unchanged.
        found = 0
        try:
            async for info in discover_servers():
                found += 1
                self._controller.add_server(info)
                self._scan_status_text = _("STATUS_SCANNING_PROGRESS", found=found)
                self.serversChanged.emit()
        finally:
            self._scanning = False
            self._scan_status_text = _("STATUS_SCAN_COMPLETE", found=found) if found else _("STATUS_SCAN_COMPLETE_NONE")
            self.serversChanged.emit()

    @Slot(str, int, str, str, bool)
    def addManualServer(self, host: str, port: int, username: str, password: str, remember: bool) -> None:
        host = host.strip()
        username = username.strip()
        if not host or not username or not password:
            return
        info = ServerInfo(host=host, port=port, hostname=host, username=username, password=password)
        self._controller.add_server(info)
        if remember:
            self._remember_server(f"{host}:{port}")

    def _remember_server(self, conn_id: str) -> None:
        """Remembers a server (address and user name in the configuration, the password in the secure store of the
        computer) and tells the operator when the password could not be stored."""
        conn = self._controller.connections.get(conn_id)
        if self._credentials is None or conn is None:
            return
        stored = self._credentials.remember(conn.info)
        if conn.info.password and not stored:
            self._set_notice(_("MSG_CREDENTIALS_NOT_STORED"), "warn")
        self.changed.emit()

    @Property(bool, constant=True)
    def secureStoreAvailable(self) -> bool:
        return self._credentials is not None and self._credentials.secure_store_available

    @Slot(str, bool)
    def setServerRemembered(self, conn_id: str, remember: bool) -> None:
        conn = self._controller.connections.get(conn_id)
        if self._credentials is None or conn is None:
            return
        if remember:
            self._remember_server(conn_id)
        else:
            self._credentials.forget(conn.info.host, conn.info.port)
            self.changed.emit()

    @Slot(str)
    def setActiveServer(self, conn_id: str) -> None:
        self._controller.set_active(conn_id)

    @Slot(str)
    def removeServer(self, conn_id: str) -> None:
        conn = self._controller.connections.get(conn_id)
        if conn is not None and self._credentials is not None:
            self._credentials.forget(conn.info.host, conn.info.port)
        self._controller.remove_server(conn_id)

    @Slot(str, result="QVariant")
    def serverCredentials(self, conn_id: str) -> dict[str, object]:
        conn = self._controller.connections.get(conn_id)
        if conn is None:
            return {"username": "", "password": "", "remember": False}
        remembered = self._credentials is not None and self._credentials.is_remembered(conn.info.host, conn.info.port)
        return {"username": conn.info.username, "password": conn.info.password, "remember": remembered}

    @Slot(str, str, str, bool, str)
    def saveServerCredentials(self, conn_id: str, username: str, password: str, remember: bool, totp_code: str = "") -> None:
        conn = self._controller.connections.get(conn_id)
        if conn is None or not username or not password:
            return
        conn.info.username = username
        conn.info.password = password
        # The code of the second step is for this sign-in only: it is kept in memory until it is sent and never saved.
        conn.totp_code = totp_code
        if remember:
            self._remember_server(conn_id)
        elif self._credentials is not None:
            self._credentials.forget(conn.info.host, conn.info.port)
        # Credentials just changed - force a clean reconnect rather than
        # waiting for HydraConnection's own retry loop to notice on its
        # own timer.
        asyncio.ensure_future(self._reconnect_server(conn))

    @staticmethod
    async def _reconnect_server(conn) -> None:
        await conn.disconnect()
        await conn.connect()

    # -- Application menu: language, support bundle, shortcuts, About ----------------

    @Property("QVariantList", constant=True)
    def languageOptions(self) -> list[dict[str, object]]:
        return [{"code": code, "label": label, "current": code == current_language()} for code, label in AVAILABLE_LANGUAGES]

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        """Saves the language for the next start (the texts are loaded once, so a restart is needed)."""
        if code not in {c for c, _label in AVAILABLE_LANGUAGES} or code == current_language():
            return
        if save_config({"language": code}):
            self._set_notice(_("MSG_RESTART_NEEDED"), "info")
        else:
            self._set_notice(_("MSG_LANGUAGE_NOT_SAVED", path=CONFIG_FILE_PATH), "warn")

    def _diagnostic_servers(self) -> list[dict]:
        """The servers of the list as the public facts the support bundle may carry (never the user name, the
        password or a token)."""
        servers = []
        for conn in self._controller.connections.values():
            info = conn.info
            servers.append({
                "label": info.nickname or info.hostname, "host": info.host, "port": info.port,
                "status": "connected" if conn.is_connected else "not connected",
                "app_version": info.app_version, "remote_api_version": info.remote_api_version, "role": conn.role,
            })
        return servers

    def export_diagnostics_to(self, path: str) -> None:
        """Writes the support bundle (versions, servers, the lines of the log, with every secret removed); raises
        OSError when the file cannot be written."""
        lines = [f"[{e.level}] {e.logger_name}: {e.message}" for e in self._all_log_entries]
        with open(path, "wb") as f:
            f.write(build_bundle(self._diagnostic_servers(), lines))

    @Slot(str)
    def exportDiagnostics(self, file_url: str) -> None:
        if not file_url:
            return
        path = QUrl(file_url).toLocalFile() or file_url
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            self.export_diagnostics_to(path)
        except OSError as error:
            self._set_notice(_("MSG_DIAGNOSTICS_FAILED", error=str(error)), "warn")
            return
        self._set_notice(_("MSG_DIAGNOSTICS_SAVED", path=path), "info")

    @Property("QVariantMap", notify=changed)
    def aboutInfo(self) -> dict[str, str]:
        conn = self._controller.active_connection
        return {
            "version": __version__,
            "serverVersion": (conn.info.app_version if conn is not None else "") or "-",
            "author": "JuanenRac (Electro Hobby 3D)",
            "email": "electrohobby3d@gmail.com",
            "license": "GNU General Public License v3.0 (GPL-3.0)",
        }

    # -- Closing ------------------------------------------------------------

    @Property(bool, notify=changed)
    def shutdownDone(self) -> bool:
        return self._shutdown_done

    @Slot()
    def shutdownAndQuit(self) -> None:
        """Called by the window when it is asked to close: the writes that are still waiting are sent and every
        connection is closed first, then the program quits (the window stays open until then)."""
        asyncio.ensure_future(self._shutdown_and_quit())

    async def _shutdown_and_quit(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            await asyncio.wait_for(self._controller.shutdown(), timeout=5)
        except Exception as error:  # a stuck server must not keep the program open
            logger.warning("closing the connections failed: %s", error)
        self._shutdown_done = True
        self.changed.emit()
        QGuiApplication.quit()

    # -- Notices -----------------------------------------------------------

    @Property(str, notify=changed)
    def noticeText(self) -> str:
        return self._notice_text

    @Property(str, notify=changed)
    def noticeSeverity(self) -> str:
        return self._notice_severity

    def _set_notice(self, text: str, severity: str = "warn") -> None:
        self._notice_text = text
        self._notice_severity = severity
        self._notice_timer.start()
        self.changed.emit()

    @Slot()
    def dismissNotice(self) -> None:
        self._notice_timer.stop()
        if self._notice_text:
            self._notice_text = ""
            self.changed.emit()

    def _on_connection_error(self, conn_id: str, message: str) -> None:
        prefix = f"[{conn_id}] " if len(self._controller.connections) > 1 else ""
        self._set_notice(prefix + message, "warn")

    # -- Access: reservations, Live / Sim, arming of the jog ---------------------

    def _access_target(self) -> tuple["HydraConnection | None", int | None]:
        """The active connection and the numeric id the server knows the selected robot by."""
        conn = self._controller.active_connection
        robot = self._selected_robot()
        if conn is None or robot is None:
            return conn, None
        try:
            return conn, int(robot.id)
        except (TypeError, ValueError):
            return conn, None

    @staticmethod
    def _scope(conn: "HydraConnection") -> str:
        return f"{conn.info.host}:{conn.info.port}"

    @Property(str, constant=True)
    def controllerId(self) -> str:
        return access.get_controller_id()

    @Property(bool, notify=_accessChanged)
    def accessBusy(self) -> bool:
        return self._access_busy

    @Property(str, notify=_accessChanged)
    def selectedRobotMode(self) -> str:
        conn, robot_id = self._access_target()
        if conn is None or robot_id is None:
            return access.MODES.default_mode
        return access.MODES.mode_of(self._scope(conn), robot_id)

    @Slot(str)
    def setSelectedRobotMode(self, mode: str) -> None:
        conn, robot_id = self._access_target()
        if conn is None or robot_id is None:
            return
        access.MODES.set_mode(self._scope(conn), robot_id, mode)
        save_config(access.MODES.to_config())
        self.changed.emit()

    @Property(bool, notify=_accessChanged)
    def listenOnly(self) -> bool:
        return access.LISTEN_ONLY.enabled

    @Property(bool, notify=_accessChanged)
    def listenOnlyServer(self) -> bool:
        """Whether listen only holds for the server of the selected robot by its own switch (not by the general one)."""
        conn, _robot_id = self._access_target()
        return conn is not None and self._scope(conn) in access.LISTEN_ONLY.servers

    @Property(bool, notify=_accessChanged)
    def canSetListenOnlyServer(self) -> bool:
        conn, _robot_id = self._access_target()
        return conn is not None and not access.LISTEN_ONLY.enabled

    @Slot(bool)
    def setListenOnlyServer(self, on: bool) -> None:
        conn, _robot_id = self._access_target()
        if conn is None:
            return
        access.LISTEN_ONLY.set_server(self._scope(conn), on)
        save_config(access.LISTEN_ONLY.to_config())
        self.changed.emit()

    @Slot(bool)
    def setListenOnly(self, on: bool) -> None:
        access.LISTEN_ONLY.set(on)
        save_config(access.LISTEN_ONLY.to_config())
        self.changed.emit()

    @Property(bool, notify=_accessChanged)
    def defaultRobotModeSim(self) -> bool:
        return access.MODES.default_mode == "sim"

    @Slot(bool)
    def setDefaultRobotModeSim(self, on: bool) -> None:
        access.MODES.set_default("sim" if on else "live")
        save_config(access.MODES.to_config())
        self.changed.emit()

    def _selected_claim(self) -> "access.ClaimEntry | None":
        conn, robot_id = self._access_target()
        if conn is None or robot_id is None:
            return None
        return next((c for c in conn.claims if c.robot_id == robot_id), None)

    def _standing(self) -> str:
        conn, _robot_id = self._access_target()
        return access.claim_standing(self._selected_claim(), access.get_controller_id(), (conn.info.username or None) if conn is not None else None)

    @staticmethod
    def _clock(seconds: int | None) -> str:
        return "" if seconds is None else f"{seconds // 60}:{seconds % 60:02d}"

    @Property("QVariantMap", notify=_accessChanged)
    def selectedRobotAccess(self) -> dict[str, object]:
        """Where the selected robot stands for this program, the sentence that says it, and which buttons apply."""
        conn, robot_id = self._access_target()
        claim = self._selected_claim()
        standing = self._standing()
        signed_in = conn is not None and robot_id is not None and conn.login_ok is True
        left = claim.seconds_left() if claim is not None else None
        text = {
            "mine": _("ACCESS_HELD_BY_ME", time=self._clock(left)),
            "other-controller": _("ACCESS_HELD_BY_ME_ELSEWHERE"),
            "other-account": _("ACCESS_HELD_BY_OTHER", user=claim.owner_username if claim is not None else "?"),
        }.get(standing, _("ACCESS_FREE"))
        return {
            "standing": standing,
            "text": text,
            "canReserve": signed_in and standing == "free",
            "canRelease": signed_in and standing == "mine",
            "canTakeOver": signed_in and standing in ("other-controller", "other-account") and conn is not None and conn.is_admin,
        }

    @Property("QVariantList", notify=_accessChanged)
    def claimsRows(self) -> list[dict[str, object]]:
        conn = self._controller.active_connection
        if conn is None:
            return []
        mine_id = access.get_controller_id()
        user = conn.info.username or None
        return [
            {
                "robot": claim.robot_name or f"#{claim.robot_id}",
                "owner": claim.owner_username,
                "controller": (claim.controller_id or _("ACCESS_NO_CONTROLLER")) + (f" ({_('ACCESS_THIS_PROGRAM')})" if access.claim_standing(claim, mine_id, user) == "mine" else ""),
                "left": self._clock(claim.seconds_left()),
                "mine": access.claim_standing(claim, mine_id, user) == "mine",
            }
            for claim in conn.claims
        ]

    @Property("QVariantMap", notify=_accessChanged)
    def selectedRobotSafeMode(self) -> dict[str, object]:
        """Whether the selected robot is in safe mode and which of the two buttons applies: anyone signed in can
        disable a robot (like a stop); only an administrator is offered the enable."""
        conn, robot_id = self._access_target()
        robot = self._selected_robot()
        signed_in = conn is not None and robot_id is not None and conn.login_ok is True
        disabled = robot is not None and not robot.enabled
        return {
            "disabled": disabled,
            "text": _("ACCESS_SAFE_MODE_BADGE") if disabled else "",
            "canDisable": signed_in and not disabled,
            "canEnable": signed_in and disabled and conn is not None and conn.is_admin,
        }

    @Slot()
    def disableSelectedRobot(self) -> None:
        conn, robot_id = self._access_target()
        if conn is not None and robot_id is not None:
            asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_DISABLE"), lambda: conn.set_robot_enabled(robot_id, False)))

    @Slot()
    def enableSelectedRobot(self) -> None:
        conn, robot_id = self._access_target()
        if conn is not None and robot_id is not None and conn.is_admin:
            asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_ENABLE"), lambda: conn.set_robot_enabled(robot_id, True)))

    @Property(bool, notify=_accessChanged)
    def jogArmRequired(self) -> bool:
        conn = self._controller.active_connection
        return conn is not None and conn.safety.limits.arm_required

    @Property("QVariantMap", notify=_accessChanged)
    def selectedRobotArm(self) -> dict[str, object]:
        conn, robot_id = self._access_target()
        until = conn.jog_armed_until.get(robot_id) if conn is not None and robot_id is not None else None
        armed = access.is_armed(until)
        seconds = max(0, round((until - time.time() * 1000) / 1000)) if armed and until is not None else 0
        standing = self._standing()
        return {
            "armed": armed,
            "seconds": seconds,
            "canToggle": conn is not None and robot_id is not None and conn.login_ok is True and standing in ("free", "mine"),
        }

    async def _run_access(self, label: str, action) -> None:
        """Runs one reservation or arming request, says why when the server refused it, and refreshes."""
        if self._access_busy:
            return
        self._access_busy = True
        self.changed.emit()
        try:
            result = await action()
            if not result.ok:
                self._set_notice(self._describe_access_failure(label, result), "warn")
            await self._refresh_access()
        finally:
            self._access_busy = False
            self.changed.emit()

    @staticmethod
    def _describe_access_failure(label: str, result) -> str:
        key = f"MSG_ACCESS_{result.code.upper()}"
        text = _(key, what=label, detail=result.detail)
        if text == key:
            text = _("MSG_ACCESS_REJECTED", what=label, detail=result.detail)
        return text

    @Slot()
    def claimSelectedRobot(self) -> None:
        conn, robot_id = self._access_target()
        if conn is not None and robot_id is not None:
            asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_RESERVE"), lambda: conn.claim_robot(robot_id)))

    @Slot()
    def releaseSelectedRobot(self) -> None:
        conn, robot_id = self._access_target()
        if conn is not None and robot_id is not None:
            asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_RELEASE"), lambda: conn.release_robot(robot_id)))

    @Slot()
    def takeOverSelectedRobot(self) -> None:
        conn, robot_id = self._access_target()
        if conn is not None and robot_id is not None and conn.is_admin:
            asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_TAKE_OVER"), lambda: conn.claim_robot(robot_id, force=True)))

    @Slot()
    def toggleJogArm(self) -> None:
        conn, robot_id = self._access_target()
        if conn is None or robot_id is None:
            return
        armed = access.is_armed(conn.jog_armed_until.get(robot_id))
        asyncio.ensure_future(self._run_access(_("ACCESS_WHAT_ARM"), lambda: conn.arm_jog(robot_id, not armed)))

    async def _refresh_access(self, poll: bool = False) -> None:
        conn, robot_id = self._access_target()
        if conn is None:
            conn = self._controller.active_connection
        if conn is None or conn.login_ok is not True:
            return
        # The server pushes the reservations when they change: while a push is fresh the poll does not ask for them.
        await conn.refresh_access(robot_id, claims=not (poll and conn.claims_are_pushed()))
        # A reservation of this program is renewed while it is kept (re-claiming one's own robot refreshes it).
        claim = self._selected_claim()
        if robot_id is not None and claim is not None and self._standing() == "mine":
            left = claim.seconds_left()
            if left is not None and left <= _CLAIM_RENEW_BELOW_S:
                renewed = await conn.claim_robot(robot_id, unconditional=True)
                if renewed.ok:
                    await conn.refresh_access(robot_id)
        self._safety_version += 1
        self.changed.emit()

    # -- Local and global settings by role -------------------------------------------

    @Property(bool, notify=securityChanged)
    def canEditSettings(self) -> bool:
        """Whether the account of the active server may change the global settings. Without a server there is nothing to refuse."""
        conn = self._controller.active_connection
        return conn is None or conn.may_edit_settings

    @Property(bool, notify=securityChanged)
    def settingsLocked(self) -> bool:
        """True on a screen that changes global settings (modules, racks, cameras, models of the catalog...) for an account that may not."""
        return self._active_key in _SETTINGS_PANELS and not self.canEditSettings

    # -- Safety limits (administrators) ----------------------------------------------

    @Property(bool, notify=securityChanged)
    def safetyIsAdmin(self) -> bool:
        conn = self._controller.active_connection
        return conn is not None and conn.is_admin

    @Property(bool, notify=securityChanged)
    def safetyHasServer(self) -> bool:
        return self._controller.active_connection is not None

    @Property("QVariantMap", notify=securityChanged)
    def safetyForm(self) -> dict[str, object]:
        conn = self._controller.active_connection
        return access.form_from_limits(conn.safety.limits if conn is not None else access.SafetyLimits())

    @Property("QVariantMap", notify=securityChanged)
    def safetyHard(self) -> dict[str, object]:
        conn = self._controller.active_connection
        hard = conn.safety.hard if conn is not None else access.HardLimits()
        return {
            "jogMaxAmount": hard.jog_max_amount,
            "jogMaxAbsolute": hard.jog_max_absolute,
            "armTtlMinS": hard.arm_ttl_min_ms / 1000,
            "armTtlMaxS": hard.arm_ttl_max_ms / 1000,
            "bedMaxC": hard.bed_max_c,
            "auditMotionMinS": hard.audit_motion_min_s,
            "auditMotionMaxS": hard.audit_motion_max_s,
        }

    @Property(int, notify=securityChanged)
    def safetyVersion(self) -> int:
        return self._safety_version

    @Property(str, notify=securityChanged)
    def safetyMessage(self) -> str:
        return self._safety_message

    @Property(str, notify=securityChanged)
    def safetyError(self) -> str:
        return self._safety_error

    @Slot(result="QVariant")
    def safetyDefaultsForm(self) -> dict[str, object]:
        conn = self._controller.active_connection
        return access.form_from_limits(conn.safety.defaults if conn is not None else access.SafetyLimits())

    @Slot("QVariant")
    def saveSafetyLimits(self, form) -> None:
        conn = self._controller.active_connection
        self._safety_message = ""
        self._safety_error = ""
        if conn is None or not conn.is_admin:
            self._safety_error = _("MSG_ADMIN_ONLY")
            self.securityChanged.emit()
            return
        # From QML the form arrives as a JavaScript value; from Python (a check) as a dict.
        values = form.toVariant() if hasattr(form, "toVariant") else form
        built = access.build_patch(dict(values), conn.safety.hard)
        if not built["ok"]:
            self._safety_error = _(f"MSG_SAFETY_PROBLEM_{str(built['problem']).upper()}", field=built.get("field", ""))
            self.securityChanged.emit()
            return
        asyncio.ensure_future(self._save_safety(conn, built["patch"]))

    async def _save_safety(self, conn, patch: dict) -> None:
        result = await conn.put_safety_limits(patch)
        if result.ok:
            self._safety_message = _("MSG_SAFETY_SAVED")
            self._safety_version += 1
        else:
            self._safety_error = _("MSG_SAFETY_SAVE_FAILED", detail=result.detail or f"HTTP {result.status}")
        self.changed.emit()

    def _bed_ceiling(self) -> float:
        conn = self._controller.active_connection
        return access.highest_bed_max(conn.safety.limits) if conn is not None else access.SafetyLimits().bed_default_c

    # -- Conditional writes: whether a write checks that the robot has not changed (this program) --------------------

    @Property(str, notify=changed)
    def conditionalMode(self) -> str:
        return access.CONDITIONAL.mode

    @Property("QVariantList", constant=True)
    def conditionalModeOptions(self) -> list[dict[str, str]]:
        return [
            {"value": "standard", "label": _("ACCESS_CONDITIONAL_STANDARD")},
            {"value": "strict", "label": _("ACCESS_CONDITIONAL_STRICT")},
            {"value": "off", "label": _("ACCESS_CONDITIONAL_OFF")},
        ]

    @Slot(str)
    def setConditionalMode(self, mode: str) -> None:
        access.CONDITIONAL.set(mode)
        save_config(access.CONDITIONAL.to_config())
        self.changed.emit()

    # -- Audit record (administrators) -------------------------------------------------------------------------------

    @Property(bool, notify=securityChanged)
    def auditIsAdmin(self) -> bool:
        return self.safetyIsAdmin

    @Property(bool, notify=securityChanged)
    def auditHasServer(self) -> bool:
        return self._controller.active_connection is not None

    @Property("QVariantList", notify=securityChanged)
    def auditRows(self) -> list[dict[str, object]]:
        return self._audit_rows

    @Property("QVariantList", notify=securityChanged)
    def auditChain(self) -> list[dict[str, object]]:
        return self._audit_chain

    @Property(str, notify=securityChanged)
    def auditMessage(self) -> str:
        return self._audit_message

    @Property(str, notify=securityChanged)
    def auditError(self) -> str:
        return self._audit_error

    @Property(bool, notify=securityChanged)
    def auditBusy(self) -> bool:
        return self._audit_busy

    @Property("QVariantList", constant=True)
    def auditTypeOptions(self) -> list[dict[str, str]]:
        return audit_record.type_options()

    @Property("QVariantList", constant=True)
    def auditLimits(self) -> list[int]:
        return list(audit_record.LIMITS)

    @Property("QVariantList", notify=securityChanged)
    def auditRobotOptions(self) -> list[dict[str, str]]:
        return [{"value": "", "label": _("AUDIT_ALL_ROBOTS")}] + [
            {"value": str(robot_id), "label": name} for robot_id, name in self._audit_robot_names().items()
        ]

    @Property(str, notify=securityChanged)
    def auditType(self) -> str:
        return self._audit_type

    @Property(str, notify=securityChanged)
    def auditRobot(self) -> str:
        return self._audit_robot

    @Property(int, notify=securityChanged)
    def auditLimit(self) -> int:
        return self._audit_limit

    def _audit_robot_names(self) -> dict[int, str]:
        state = self._controller.active_state
        controller = state.active_controller if state is not None else None
        names: dict[int, str] = {}
        for robot in controller.robots if controller is not None else []:
            try:
                names[int(robot.id)] = str(robot.raw.get("name") or f"#{robot.id}")
            except (TypeError, ValueError):
                continue
        return names

    def _audit_query(self) -> dict:
        query: dict = {"limit": self._audit_limit}
        if self._audit_type:
            query["type"] = self._audit_type
        if self._audit_robot:
            try:
                query["robot_id"] = int(self._audit_robot)
            except ValueError:
                pass
        return query

    @Slot(str)
    def setAuditType(self, kind: str) -> None:
        self._audit_type = kind
        self.securityChanged.emit()
        asyncio.ensure_future(self._refresh_audit(False))

    @Slot(str)
    def setAuditRobot(self, robot_id: str) -> None:
        self._audit_robot = robot_id
        self.securityChanged.emit()
        asyncio.ensure_future(self._refresh_audit(False))

    @Slot(int)
    def setAuditLimit(self, limit: int) -> None:
        if limit in audit_record.LIMITS:
            self._audit_limit = limit
            self.securityChanged.emit()
            asyncio.ensure_future(self._refresh_audit(False))

    @Slot()
    def refreshAudit(self) -> None:
        asyncio.ensure_future(self._refresh_audit(False))

    @Slot()
    def verifyAudit(self) -> None:
        asyncio.ensure_future(self._refresh_audit(True))

    async def _refresh_audit(self, verify: bool) -> None:
        conn = self._controller.active_connection
        self._audit_message = ""
        self._audit_error = ""
        if conn is None or not conn.is_admin or conn.login_ok is not True:
            self._audit_rows = []
            self._audit_chain = []
            self.changed.emit()
            return
        self._audit_busy = True
        self.changed.emit()
        try:
            query = self._audit_query()
            result, read = await conn.fetch_audit(verify=verify, **query)
            if read is None:
                self._audit_rows = []
                self._audit_chain = []
                self._audit_error = audit_record.failure_text(result.status, result.code)
                return
            self._audit_last_query = query
            self._audit_rows = audit_record.rows(read.entries, self._audit_robot_names())
            self._audit_chain = audit_record.chain_lines(read) if verify else []
            if not read.enabled:
                self._audit_message = _("AUDIT_LOCKED_OFF") if read.locked_off else _("AUDIT_SWITCHED_OFF")
            elif not read.entries:
                self._audit_message = _("AUDIT_EMPTY")
        finally:
            self._audit_busy = False
            self.changed.emit()

    @Slot(str)
    def exportAudit(self, path: str) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        asyncio.ensure_future(self._export_audit(conn, path))

    async def _export_audit(self, conn, path: str) -> None:
        text = await conn.fetch_audit_jsonl(**self._audit_query())
        if text is None:
            self._audit_error = _("AUDIT_FAILURE_OTHER")
            self.changed.emit()
            return
        local_path = QUrl(path).toLocalFile() or path
        try:
            with open(local_path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except OSError as error:
            self._audit_error = _("AUDIT_EXPORT_FAILED", error=error)
        else:
            self._audit_message = _("AUDIT_EXPORTED", path=local_path)
        self.changed.emit()

    # -- Submitted models -----------------------------------------------------------------

    @Property(bool, notify=catalogChanged)
    def modelsHasServer(self) -> bool:
        return self._controller.active_connection is not None

    @Property("QVariantList", notify=catalogChanged)
    def modelsRows(self) -> list[dict[str, str]]:
        return self._models_rows

    @Property(str, notify=catalogChanged)
    def modelsMessage(self) -> str:
        return self._models_message

    @Property(str, notify=catalogChanged)
    def modelsError(self) -> str:
        return self._models_error

    @Property(bool, notify=catalogChanged)
    def modelsBusy(self) -> bool:
        return self._models_busy

    @Slot()
    def refreshModels(self) -> None:
        asyncio.ensure_future(self._refresh_models())

    async def _refresh_models(self) -> None:
        conn = self._controller.active_connection
        self._models_message = ""
        self._models_error = ""
        if conn is None or conn.login_ok is not True:
            self._models_rows = []
            self._models_list = []
            self.catalogChanged.emit()
            return
        self._models_busy = True
        self.catalogChanged.emit()
        try:
            result = await conn.fetch_submitted_models()
            status = 0 if result is None else result[0]
            if result is None or status != 200:
                self._models_rows = []
                self._models_list = []
                self._models_error = submitted_models.failure_text(status)
                return
            self._models_list = submitted_models.parse_models(result[1])
            self._models_rows = submitted_models.rows(self._models_list)
        finally:
            self._models_busy = False
            self.catalogChanged.emit()

    @Slot(str, str, str)
    def saveModelUrdf(self, category: str, slug: str, path: str) -> None:
        asyncio.ensure_future(self._save_model_urdf(category, slug, path))

    async def _save_model_urdf(self, category: str, slug: str, path: str) -> None:
        conn = self._controller.active_connection
        self._models_message = ""
        self._models_error = ""
        if conn is None:
            return
        known = next((m for m in self._models_list if m["category"] == category and m["slug"] == slug), None)
        name = known["name"] if known else slug
        result = await conn.fetch_model_download(category, slug)
        answer = result[1] if result is not None and result[0] == 200 else None
        xml = submitted_models.urdf_text(answer)
        if xml is None:
            self._models_error = _("MODELS_SAVE_FAILED", name=name)
            self.catalogChanged.emit()
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path.lower().endswith(".urdf"):
            local_path += ".urdf"
        try:
            with open(local_path, "w", encoding="utf-8", newline="") as f:
                f.write(xml)
        except OSError as error:
            self._models_error = _("MODELS_SAVE_WRITE_FAILED", error=error)
        else:
            self._models_message = _("MODELS_SAVED", path=local_path)
        self.catalogChanged.emit()

    # -- User accounts (administrators only) -------------------------------------------

    @Property(bool, notify=securityChanged)
    def usersIsAdmin(self) -> bool:
        return self.safetyIsAdmin

    @Property(bool, notify=securityChanged)
    def usersHasServer(self) -> bool:
        return self._controller.active_connection is not None

    @Property("QVariantList", notify=securityChanged)
    def usersRows(self) -> list[dict[str, object]]:
        return self._users_rows

    @Property("QVariantList", constant=True)
    def usersRoleOptions(self) -> list[dict[str, str]]:
        return users_panel.role_options()

    @Property(str, notify=securityChanged)
    def usersMessage(self) -> str:
        return self._users_message

    @Property(str, notify=securityChanged)
    def usersError(self) -> str:
        return self._users_error

    @Property(bool, notify=securityChanged)
    def usersBusy(self) -> bool:
        return self._users_busy

    @Slot()
    def refreshUsers(self) -> None:
        asyncio.ensure_future(self._refresh_users())

    def _users_conn(self):
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin or conn.login_ok is not True:
            return None
        return conn

    async def _refresh_users(self, keep_message: bool = False) -> None:
        conn = self._users_conn()
        if not keep_message:
            self._users_message = ""
            self._users_error = ""
        if conn is None:
            self._users_rows = []
            self.securityChanged.emit()
            return
        self._users_busy = True
        self.securityChanged.emit()
        try:
            result = await conn.fetch_users()
            if not result.ok:
                self._users_rows = []
                self._users_error = users_panel.failure_text(result.status, result.code, result.detail)
                return
            self._users_rows = users_panel.rows(users_panel.parse_users(result.body), conn.info.username or "")
        finally:
            self._users_busy = False
            self.securityChanged.emit()

    @Slot(str, str, str)
    def createUser(self, username: str, password: str, role: str) -> None:
        self._users_error = users_panel.check_new(username, password)
        self._users_message = ""
        if self._users_error or self._users_conn() is None:
            self.securityChanged.emit()
            return
        asyncio.ensure_future(self._users_write("create", username.strip(), password, role if role in users_panel.ROLES else users_panel.DEFAULT_ROLE))

    @Slot(str, str, str, str)
    def updateUser(self, username: str, new_username: str, password: str, role: str) -> None:
        self._users_message = ""
        role = role if role in users_panel.ROLES else ""
        self._users_error = users_panel.check_change(username, new_username, password, role)
        if self._users_error or self._users_conn() is None:
            self.securityChanged.emit()
            return
        asyncio.ensure_future(self._users_write("update", username, password, role, new_username))

    @Slot(str)
    def deleteUser(self, username: str) -> None:
        self._users_error = ""
        self._users_message = ""
        if not username or self._users_conn() is None:
            self._users_error = _("USERS_ERR_SELECT_ACCOUNT") if not username else ""
            self.securityChanged.emit()
            return
        asyncio.ensure_future(self._users_write("delete", username))

    async def _users_write(self, action: str, username: str, password: str = "", role: str = "", new_username: str = "") -> None:
        conn = self._users_conn()
        if conn is None:
            return
        self._users_busy = True
        self.securityChanged.emit()
        try:
            if action == "create":
                result = await conn.create_user(username, password, role)
                done = _("USERS_CREATED", username=username)
            elif action == "update":
                result = await conn.update_user(username, new_username, password, role)
                done = _("USERS_UPDATED", username=username)
            else:
                result = await conn.delete_user(username)
                done = _("USERS_DELETED", username=username)
        finally:
            self._users_busy = False
        if result.ok:
            self._users_message = done
            self._users_error = ""
        else:
            self._users_message = ""
            self._users_error = users_panel.failure_text(result.status, result.code, result.detail)
        await self._refresh_users(keep_message=True)

    # -- Two-step sign-in of the signed-in account (Server Admin) -------------------------

    @Property(str, notify=securityChanged)
    def totpStep(self) -> str:
        return self._totp_step

    @Property(str, notify=securityChanged)
    def totpStatusText(self) -> str:
        return _("TOTP_STATUS_ON", count=self._totp_left) if self._totp_step == "on" else _("TOTP_STATUS_OFF")

    @Property(str, notify=securityChanged)
    def totpKey(self) -> str:
        return totp_panel.grouped_key(self._totp_key) if self._totp_key else ""

    @Property("QVariant", notify=securityChanged)
    def totpQr(self) -> dict[str, object]:
        return self._totp_qr

    @Property("QVariantList", notify=securityChanged)
    def totpRecovery(self) -> list[str]:
        return self._totp_recovery

    @Property(str, notify=securityChanged)
    def totpError(self) -> str:
        return self._totp_error

    @Property(str, notify=securityChanged)
    def totpMessage(self) -> str:
        return self._totp_message

    @Property(bool, notify=securityChanged)
    def totpBusy(self) -> bool:
        return self._totp_busy

    def _totp_conn(self):
        conn = self._controller.active_connection
        return conn if conn is not None and conn.login_ok is True else None

    async def _refresh_totp(self) -> None:
        conn = self._totp_conn()
        if conn is None:
            self._totp_step = "none"
            self.securityChanged.emit()
            return
        if self._totp_step in ("enrolling", "recovery"):
            return
        status, body, retry = await conn.totp_call("GET", "/api/totp/status")
        parsed = totp_panel.parse_status(body) if status == 200 else None
        if parsed is None:
            self._totp_step = "unsupported" if status == 404 else "off"
            self._totp_error = "" if status == 404 else totp_panel.failure_text(status or 0, body, retry, password_call=False)
        else:
            self._totp_step = "on" if parsed[0] else "off"
            self._totp_left = parsed[1]
        self.securityChanged.emit()

    @Slot()
    def refreshTotp(self) -> None:
        self._totp_error = ""
        asyncio.ensure_future(self._refresh_totp())

    @Slot(str)
    def startTotp(self, password: str) -> None:
        asyncio.ensure_future(self._start_totp(password))

    async def _start_totp(self, password: str) -> None:
        conn = self._totp_conn()
        if conn is None or not password:
            return
        self._totp_busy, self._totp_error, self._totp_message = True, "", ""
        self.securityChanged.emit()
        status, body, retry = await conn.totp_call("POST", "/api/totp/begin", {"password": password})
        self._totp_busy = False
        enrolment = totp_panel.parse_enrolment(body) if status == 200 else None
        if enrolment is None:
            self._totp_error = totp_panel.failure_text(status or 0, body, retry)
        else:
            self._totp_key = enrolment[0]
            self._totp_qr = totp_panel.qr_view(enrolment[1])
            self._totp_step = "enrolling"
        self.securityChanged.emit()

    @Slot(str)
    def confirmTotp(self, code: str) -> None:
        asyncio.ensure_future(self._confirm_totp(code))

    async def _confirm_totp(self, code: str) -> None:
        conn = self._totp_conn()
        if conn is None or not code.strip():
            return
        self._totp_busy, self._totp_error = True, ""
        self.securityChanged.emit()
        status, body, retry = await conn.totp_call("POST", "/api/totp/confirm", {"code": totp_panel.normalize_code(code)})
        self._totp_busy = False
        codes = totp_panel.parse_recovery_codes(body) if status == 200 else None
        if codes is None:
            self._totp_error = totp_panel.failure_text(status or 0, body, retry, password_call=False)
        else:
            self._totp_key, self._totp_recovery, self._totp_step = "", codes, "recovery"
            self._totp_qr = {"tooLong": False, "path": "", "size": 0, "modules": []}
        self.securityChanged.emit()

    @Slot()
    def cancelTotp(self) -> None:
        self._totp_key, self._totp_error, self._totp_step = "", "", "off"
        self._totp_qr = {"tooLong": False, "path": "", "size": 0, "modules": []}
        self.securityChanged.emit()

    @Slot()
    def finishTotp(self) -> None:
        self._totp_recovery = []
        self._totp_step = "loading"
        self._totp_message = _("TOTP_DONE_ON")
        asyncio.ensure_future(self._refresh_totp())

    @Slot()
    def copyTotpKey(self) -> None:
        if self._totp_key:
            QGuiApplication.clipboard().setText(self._totp_key)
            self._totp_message = _("TOTP_COPIED")
            self.securityChanged.emit()

    @Slot(str, str)
    def disableTotp(self, password: str, code: str) -> None:
        asyncio.ensure_future(self._disable_totp(password, code))

    async def _disable_totp(self, password: str, code: str) -> None:
        conn = self._totp_conn()
        if conn is None or not password or not code.strip():
            return
        self._totp_busy, self._totp_error, self._totp_message = True, "", ""
        self.securityChanged.emit()
        status, body, retry = await conn.totp_call("POST", "/api/totp/disable", {"password": password, "code": totp_panel.normalize_code(code)})
        self._totp_busy = False
        if status == 200:
            self._totp_message = _("TOTP_DONE_OFF")
            self._totp_step = "loading"
            await self._refresh_totp()
            return
        self._totp_error = totp_panel.failure_text(status or 0, body, retry)
        self.securityChanged.emit()

    @Slot(str)
    def resetUserTotp(self, username: str) -> None:
        asyncio.ensure_future(self._reset_user_totp(username))

    async def _reset_user_totp(self, username: str) -> None:
        conn = self._users_conn()
        if conn is None or not username:
            return
        status, _body, _retry = await conn.reset_user_totp(username)
        if status == 200:
            self._users_message, self._users_error = _("TOTP_RESET_DONE", username=username), ""
        else:
            self._users_message, self._users_error = "", _("TOTP_RESET_ERROR")
        self.securityChanged.emit()

    # -- Robots Catalog -------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def catalogManufacturers(self) -> list[dict[str, str]]:
        return [{"value": "__all__", "label": _("OPT_ALL_MANUFACTURERS")}] + [
            {"value": m, "label": m} for m in sorted(set(ROBOT_MANUFACTURERS.values()))
        ]

    @Property(str, notify=catalogChanged)
    def catalogManufacturer(self) -> str:
        return self._catalog_manufacturer

    @Property(int, notify=catalogChanged)
    def catalogDof(self) -> int:
        return self._catalog_dof

    @Property(str, notify=catalogChanged)
    def catalogSelected(self) -> str:
        return self._catalog_selected

    @Property("QVariantList", notify=catalogChanged)
    def catalogRows(self) -> list[dict[str, object]]:
        state = self._controller.active_state
        models = REAL_ROBOT_MODELS
        if self._catalog_manufacturer != "__all__":
            models = [m for m in models if ROBOT_MANUFACTURERS[m] == self._catalog_manufacturer]
        if self._catalog_dof:
            models = [m for m in models if robot_model_dof(m) == self._catalog_dof]
        return [
            {
                "model": m,
                "manufacturer": ROBOT_MANUFACTURERS[m],
                "enabled": state.is_robot_model_enabled(m) if state is not None else True,
                "selected": m == self._catalog_selected,
            }
            for m in models
        ]

    @Slot(str)
    def setCatalogManufacturer(self, value: str) -> None:
        self._catalog_manufacturer = value or "__all__"
        self.catalogChanged.emit()

    @Slot(int)
    def setCatalogDof(self, value: int) -> None:
        self._catalog_dof = value if value in (5, 6) else 0
        self.catalogChanged.emit()

    @Slot(str)
    def selectCatalogModel(self, model: str) -> None:
        if model in REAL_ROBOT_MODELS:
            self._catalog_selected = model
            self.refreshCatalogPreview()
            self.catalogChanged.emit()

    @Slot(str, bool)
    def setCatalogModelEnabled(self, model: str, enabled: bool) -> None:
        state = self._controller.active_state
        if state is None or model not in REAL_ROBOT_MODELS:
            return
        state.set_robot_model_enabled(model, enabled)
        self._controller.push_active_state()
        self.changed.emit()

    @Property(int, notify=_viewportChanged)
    def catalogPreviewVersion(self) -> int:
        return self._catalog_preview_version

    @Property(str, notify=_viewportChanged)
    def catalogPreviewError(self) -> str:
        return self._catalog_preview_error

    @Slot()
    def refreshCatalogPreview(self) -> None:
        if self._catalog_frame_provider is None or self._active_key != "robots_catalog":
            return
        if self._catalog_preview_model == self._catalog_selected and not self._catalog_preview_error:
            return
        try:
            if self._catalog_renderer is None:
                from hydra_suite.render.viewport import OffscreenRobotRenderer

                self._catalog_renderer = OffscreenRobotRenderer()
                self._catalog_renderer.resize(640, 480)
            self._catalog_renderer.set_robot_model(self._catalog_selected)
            self._catalog_frame_provider.set_image(self._catalog_renderer.render())
            self._catalog_preview_error = ""
            self._catalog_preview_model = self._catalog_selected
            self._catalog_preview_version += 1
        except Exception as error:
            self._catalog_preview_error = _("LBL_CATALOG_PREVIEW_ERROR", error=error)
        self._viewportChanged.emit()

    @Slot(float, float)
    def catalogPreviewOrbit(self, dx: float, dy: float) -> None:
        if self._catalog_renderer is not None:
            self._catalog_renderer.orbit(dx, dy)
            self._catalog_preview_model = None
            self.refreshCatalogPreview()

    @Slot(float)
    def catalogPreviewZoom(self, factor: float) -> None:
        if self._catalog_renderer is not None:
            self._catalog_renderer.zoom(factor)
            self._catalog_preview_model = None
            self.refreshCatalogPreview()

    # -- System Supervisor -----------------------------------------------------------

    _supervisorChanged = Signal()

    @Property(str, notify=_supervisorChanged)
    def supervisorStatus(self) -> str:
        return self._supervisor_status

    @Property(str, notify=_supervisorChanged)
    def supervisorLive(self) -> str:
        return self._supervisor_live

    @Property("QVariantMap", notify=_supervisorChanged)
    def supervisorView(self) -> dict[str, object]:
        return self._supervisor_view

    @Property(int, notify=_supervisorChanged)
    def supervisorVersion(self) -> int:
        return self._supervisor_version

    def _on_supervisor_connection_changed(self, _conn_id: str) -> None:
        self._supervisor_history = []
        self._supervisor_view = {}
        if self._active_key == "system_supervisor":
            asyncio.ensure_future(self._refresh_supervisor())

    async def _refresh_supervisor(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._supervisor_status = _("LBL_ES_NO_ACTIVE_SERVER")
            self._supervisor_history = []
            self._supervisor_view = {}
            self._supervisor_version += 1
            self._supervisorChanged.emit()
            return
        result = await conn.fetch_system_supervisor()
        if result is None or result[0] != 200 or not isinstance(result[1], dict):
            self._supervisor_status = _("MSG_SUPERVISOR_UNREACHABLE")
            self._supervisor_live = _("LBL_SUPERVISOR_STALE")
            self._supervisorChanged.emit()
            return
        self._supervisor_status = ""
        self._supervisor_live = _("LBL_SUPERVISOR_LIVE")
        self._supervisor_history = supervisor_logic.append_history(self._supervisor_history, result[1])
        self._supervisor_view = supervisor_logic.build_view(self._supervisor_history)
        self._supervisor_version += 1
        self._supervisorChanged.emit()

    # -- Ecosystem health ----------------------------------------------------

    @Property(str, notify=_ecoHealthChanged)
    def ecoHealthStatus(self) -> str:
        return self._eco_health_status

    @Property(bool, notify=_ecoHealthChanged)
    def ecoHealthLoaded(self) -> bool:
        return self._eco_health is not None

    @Property(bool, notify=_ecoHealthChanged)
    def ecoHealthUnavailable(self) -> bool:
        return self._eco_health is not None and not self._eco_health["available"]

    @Property(str, notify=_ecoHealthChanged)
    def ecoHealthEmpty(self) -> str:
        """The sentence for an empty list: no service at all, or none that matches the filter."""
        if self._eco_health is None or self._eco_health["services"] and self.ecoHealthCards:
            return ""
        return _("ECOHEALTH_NO_SERVICES") if not self._eco_health["services"] else _("ECOHEALTH_NO_MATCH")

    @Property("QVariantList", notify=_ecoHealthChanged)
    def ecoHealthFilters(self) -> list[dict[str, object]]:
        return ecosystem_health.filter_rows(self._eco_health["services"], self._eco_health_filter) if self._eco_health else []

    @Property("QVariantList", notify=_ecoHealthChanged)
    def ecoHealthNotices(self) -> list[dict[str, object]]:
        return ecosystem_health.notice_rows(self._eco_health) if self._eco_health else []

    @Property("QVariantList", notify=_ecoHealthChanged)
    def ecoHealthCards(self) -> list[dict[str, object]]:
        return ecosystem_health.card_rows(self._eco_health["services"], self._eco_health_filter) if self._eco_health else []

    @Slot(str)
    def setEcoHealthFilter(self, key: str) -> None:
        if key in ecosystem_health.FILTERS and key != self._eco_health_filter:
            self._eco_health_filter = key
            self.changed.emit()

    @Slot()
    def refreshEcoHealth(self) -> None:
        asyncio.ensure_future(self._refresh_eco_health())

    def _on_eco_health_connection_changed(self, _conn_id: str) -> None:
        # another server: nothing of the old one stays on screen
        self._eco_health, self._eco_health_status = None, ""
        if self._active_key == "ecosystem_health":
            asyncio.ensure_future(self._refresh_eco_health())

    async def _refresh_eco_health(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._eco_health, self._eco_health_status = None, _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        try:
            result = await conn.fetch_ecosystem_health()
            problem = ecosystem_health.status_for(result)
            if not problem:
                self._eco_health = ecosystem_health.parse_health(result[1])  # type: ignore[index]
        except Exception as error:  # a damaged answer must not stop the screen
            logger.warning("reading the health of the ecosystem failed: %s", error)
            problem = _("ECOHEALTH_LOAD_ERROR")
        self._eco_health_status = problem
        self.changed.emit()

    # -- Map of the ecosystem ------------------------------------------------

    @Property("QVariantMap", notify=ecosystemChanged)
    def mapView(self) -> dict[str, object]:
        """What the Map screen shows; every part already carries the sentences in the language of the interface."""
        projects = ecosystem_map.parse_projects(self._es_projects)
        drifting = ecosystem_map.drifting_names(self._eco_health)
        families = ecosystem_map.family_rows(projects, self._map_filter, self._map_search, drifting, self._map_evidence, current_language())
        if not projects:
            empty = self._es_status_text
        elif not families:
            empty = _("ECOMAP_EMPTY")
        else:
            empty = ""
        return {
            "filters": ecosystem_map.filter_rows(projects, self._map_filter),
            "families": families,
            "empty": empty,
            "showEvidence": self._map_evidence,
            "search": self._map_search,
            "scanned": self._es_status_text if projects else "",
        }

    @Slot(str)
    def setMapFilter(self, key: str) -> None:
        key = "all" if key == self._map_filter else key
        if key in ecosystem_map.FILTERS and key != self._map_filter:
            self._map_filter = key
            self.ecosystemChanged.emit()

    @Slot(str)
    def setMapSearch(self, text: str) -> None:
        self._map_search = text
        self.ecosystemChanged.emit()

    @Slot(bool)
    def setMapEvidence(self, show: bool) -> None:
        """The switch that adds to each tile what the project has been tried on; kept in the configuration file, off until turned on."""
        self._map_evidence = bool(show)
        save_config({"mapShowEvidence": self._map_evidence})
        self.ecosystemChanged.emit()

    @Slot()
    def refreshMap(self) -> None:
        asyncio.ensure_future(self._refresh_map())

    def _on_map_connection_changed(self, _conn_id: str) -> None:
        # another server: nothing of the old one stays on screen
        self._es_projects, self._eco_health = [], None
        self._es_status_text = _("LBL_ES_NOT_LOADED")
        if self._active_key == "ecosystem_map":
            asyncio.ensure_future(self._refresh_map())
        else:
            self.changed.emit()

    async def _refresh_map(self) -> None:
        await self._refresh_ecosystem_services()
        # the drift comes from the health of the ecosystem; where that is off or not allowed the map just shows no drift
        await self._refresh_eco_health()

    # -- Setup screens -----------------------------------------------------------

    @Property("QVariantMap", notify=serversChanged)
    def setupView(self) -> dict[str, object]:
        """What the active Setup screen shows; every part already carries the sentences in the language of the interface."""
        conn = self._controller.active_connection
        key = self._active_key
        if key not in setup_screens.SCREEN_KEYS:
            return {}
        if key == "setup_preferences":
            # personal preferences need no server
            return preferences.view(self._ui_scale, self._help_level, setup_screens.empty_view("PREFS_TITLE", "PREFS_INTRO"))
        if key == "setup_help":
            # the guides need no server
            return help_levels.view(self._help_level, self._help_search, setup_screens.empty_view("HELP_TITLE", "HELP_INTRO"))
        if conn is None:
            return setup_screens.no_server_view(key, _("LBL_ES_NO_ACTIVE_SERVER"))
        admin = conn.is_admin is True and conn.login_ok is True
        if key == "setup_versions":
            return setup_screens.versions_view(__version__, self._setup_info, self._setup_installed, self._setup_failure)
        if key == "setup_installation":
            return setup_screens.installation_view(self._setup_info, self._setup_second_factor, self._setup_failure)
        if key == "setup_security":
            view = setup_screens.security_view(self._setup_second_factor, self._setup_keys, admin, self._setup_failure, self._setup_allow_rotation, self._setup_notice, self._setup_notice_ok)
            return view
        if key == "setup_remote":
            address = str(conn.info.base_url).rstrip("/")
            if self._setup_qr is None or self._setup_qr[0] != address:
                self._setup_qr = (address, totp_panel.qr_view(address))
            state = self._controller.active_state
            setting = ((state.raw.get("settings") or {}).get("remoteAccess") if state is not None else None)
            view = setup_screens.remote_view(address, setting, self._setup_qr[1], self.canEditSettings)
            view["notice"], view["noticeOk"] = self._setup_notice, self._setup_notice_ok
            return view
        if key == "setup_notifications":
            return setup_screens.notifications_view(self._setup_push, admin, self._setup_failure)
        return setup_screens.history_view(
            self._setup_history_part, admin, connection_history.client_rows(self._connection_clients), connection_history.event_rows(self._connection_events),
            self._audit_rows, self._connection_status_text or self._audit_error,
        )

    @Property(float, notify=serversChanged)
    def uiScaleFactor(self) -> float:
        """What every text size of the interface is multiplied by (the scale chosen in the Preferences)."""
        return preferences.scale_factor(self._ui_scale)

    @Property(bool, notify=serversChanged)
    def setupBusy(self) -> bool:
        return self._setup_busy

    @Slot(str)
    def setupButton(self, button_id: str) -> None:
        """A button of the active Setup screen. The key rotation and "close all" are confirmed by the screen before they get here."""
        if self._active_key not in setup_screens.SCREEN_KEYS:
            return
        if button_id == "refresh":
            asyncio.ensure_future(self._refresh_setup(self._active_key))
        elif button_id == "rotate" and self._active_key == "setup_security" and self._setup_allow_rotation:
            asyncio.ensure_future(self._rotate_setup_key())
        elif button_id == "close_all" and self._active_key == "setup_remote":
            self._set_remote_access(setup_screens.close_all_setting)

    @Slot(str)
    def setupSearch(self, text: str) -> None:
        """The words typed in the search box of the Help."""
        if self._active_key != "setup_help":
            return
        self._help_search = help_levels.clean_search(text)
        self.serversChanged.emit()

    @Slot(str, bool)
    def setupToggle(self, toggle_id: str, checked: bool) -> None:
        if self._active_key == "setup_security" and toggle_id == "allow_rotation":
            self._setup_allow_rotation = bool(checked)
            self.changed.emit()
        elif self._active_key == "setup_remote" and toggle_id.startswith("client_") and toggle_id[len("client_"):] in setup_screens.REMOTE_CLIENTS:
            client = toggle_id[len("client_"):]
            self._set_remote_access(lambda setting: setup_screens.with_client(setting, client, checked))

    @Slot(str)
    def setupPart(self, part: str) -> None:
        if self._active_key == "setup_preferences":
            choice = preferences.parse_choice(part)
            if choice is None:
                return
            group, value = choice
            if group == "scale":
                self._ui_scale = int(value)
                save_config(preferences.config_update_scale(self._ui_scale))
            else:
                self._help_level = value
                save_config(help_levels.config_update(value))
            self.changed.emit()
            return
        if self._active_key == "setup_help":
            if part in help_levels.LEVELS:
                self._help_level = part
                save_config(help_levels.config_update(part))
                self.changed.emit()
            return
        if self._active_key != "setup_history" or part not in ("connections", "audit"):
            return
        self._setup_history_part = part
        if part == "audit":
            asyncio.ensure_future(self._refresh_audit(False))
        self.changed.emit()

    def _set_remote_access(self, change) -> None:
        """Changes settings.remoteAccess the way the settings screens do (the tree is sent back with the ETag read last). An account that may not
        change the global settings is refused here as well as by the screen."""
        state = self._controller.active_state
        if state is None or not self.canEditSettings:
            return
        settings = state.raw.setdefault("settings", {})
        settings["remoteAccess"] = change(settings.get("remoteAccess"))
        self._controller.push_active_state()
        self.changed.emit()

    def _on_setup_connection_changed(self, _conn_id: str) -> None:
        # another server: nothing of the old one stays on screen
        self._setup_info, self._setup_installed, self._setup_failure = None, [], ""
        self._setup_second_factor, self._setup_keys, self._setup_push = None, None, None
        self._setup_allow_rotation, self._setup_notice = False, ""
        if self._active_key in setup_screens.SCREEN_KEYS:
            asyncio.ensure_future(self._refresh_setup(self._active_key))
        else:
            self.changed.emit()

    async def _refresh_setup_second_factor(self, conn) -> None:
        """Whether the signed-in account has its second step on; None when it cannot be read (never "off" by guess)."""
        self._setup_second_factor = None
        if conn.login_ok is not True:
            return
        status, body, _retry = await conn.totp_call("GET", "/api/totp/status")
        parsed = totp_panel.parse_status(body) if status == 200 else None
        self._setup_second_factor = parsed[0] if parsed is not None else None

    async def _refresh_setup(self, key: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self.changed.emit()
            return
        self._setup_busy = True
        self._setup_failure = ""
        self.changed.emit()
        try:
            if key in ("setup_versions", "setup_installation"):
                result = await conn.fetch_hydra_info()
                self._setup_failure = setup_screens.failure_text(result)
                self._setup_info = setup_screens.parse_server_info(result[1]) if not self._setup_failure and result is not None else None
                if key == "setup_versions":
                    eco = await conn.fetch_ecosystem_status()
                    body = eco[1] if eco is not None and eco[0] == 200 and isinstance(eco[1], dict) else {}
                    self._setup_installed = setup_screens.parse_installed(body.get("projects"))
                else:
                    await self._refresh_setup_second_factor(conn)
            elif key == "setup_security":
                await self._refresh_setup_second_factor(conn)
                self._setup_keys = None
                if conn.is_admin is True and conn.login_ok is True:
                    result = await conn.fetch_admin_jwt_keys()
                    self._setup_failure = setup_screens.failure_text(result)
                    self._setup_keys = setup_screens.parse_keys(result[1]) if not self._setup_failure and result is not None else None
            elif key == "setup_notifications":
                self._setup_push = None
                if conn.is_admin is True and conn.login_ok is True:
                    result = await conn.fetch_admin_push()
                    self._setup_failure = setup_screens.failure_text(result)
                    self._setup_push = setup_screens.parse_push(result[1]) if not self._setup_failure and result is not None else None
            elif key == "setup_history":
                await self._refresh_connection_history()
                if conn.is_admin is True and conn.login_ok is True:
                    await self._refresh_audit(False)
        except Exception as error:  # a damaged answer must not stop the screen
            logger.warning("reading the setup screen %s failed: %s", key, error)
            self._setup_failure = _("SETUP_ERROR_HTTP")
        finally:
            self._setup_busy = False
            self.changed.emit()

    async def _rotate_setup_key(self) -> None:
        conn = self._controller.active_connection
        if conn is None or conn.is_admin is not True or not self._setup_allow_rotation:
            return
        self._setup_allow_rotation = False
        result = await conn.rotate_admin_jwt_key()
        if result is not None and result[0] == 200:
            kid = result[1].get("kid") if isinstance(result[1], dict) else None
            self._setup_notice, self._setup_notice_ok = _("SETUP_SECURITY_ROTATED", kid=kid if isinstance(kid, str) else ""), True
            keys = await conn.fetch_admin_jwt_keys()
            if keys is not None and keys[0] == 200:
                self._setup_keys = setup_screens.parse_keys(keys[1])
        else:
            self._setup_notice, self._setup_notice_ok = setup_screens.rotate_failure_text(result), False
        self.changed.emit()

    # -- Planning and operation (read only views and dry runs) ---------------

    @Property("QVariantMap", notify=changed)
    def planningView(self) -> dict[str, object]:
        """What the Planning screen shows; every part already carries the sentences in the language of the interface."""
        return {
            "simulation": self._planning.get("simulation"), "simulationError": self._planning.get("simulationError", ""),
            "eta": self._planning.get("eta"), "etaError": self._planning.get("etaError", ""),
            "rul": self._planning.get("rul", ""), "rulError": self._planning.get("rulError", ""),
            "train": self._planning.get("train"), "trainError": self._planning.get("trainError", ""),
            "windows": planning.switch_text(self._planning.get("windows", "unknown")),
            "busy": self._planning.get("busy", ""),
        }

    def _planning_set(self, **values: object) -> None:
        self._planning.update(values)
        self.changed.emit()

    @Slot(str)
    def simulatePlan(self, text: str) -> None:
        request = planning.parse_plan_request(text)
        if request is None:
            self._planning_set(simulation=None, simulationError=_("PLANNING_SIM_INVALID_REQUEST"))
            return
        self._planning_set(simulation=None, simulationError="", busy="sim")
        asyncio.ensure_future(self._planning_call("sim", "semantic-planner", "POST", "/plan/simulate", request))

    @Slot(str)
    def checkPlanTrajectory(self, text: str) -> None:
        """The kinematic check of the same plan: its verdict can be `unchecked`, which the screen never paints as an acceptance."""
        request = planning.parse_plan_request(text)
        if request is None:
            self._planning_set(simulation=None, simulationError=_("PLANNING_SIM_INVALID_REQUEST"))
            return
        self._planning_set(simulation=None, simulationError="", busy="traj")
        asyncio.ensure_future(self._planning_call("traj", "semantic-planner", "POST", "/plan/trajectory-check", request))

    @Slot()
    def loadPlanningEta(self) -> None:
        self._planning_set(eta=None, etaError="", busy="eta")
        asyncio.ensure_future(self._planning_call("eta", "job-dispatcher", "GET", "/dispatch/eta", None))

    @Slot(str, str)
    def estimateRul(self, points_text: str, limit_text: str) -> None:
        points, limit = planning.parse_rul_points(points_text), planning.parse_limit(limit_text)
        if points is None or limit is None:
            self._planning_set(rul="", rulError=_("PLANNING_RUL_INVALID"))
            return
        self._planning_set(rul="", rulError="", busy="rul")
        asyncio.ensure_future(self._planning_call("rul", "anomaly-detector", "POST", "/rul", {"points": points, "limit": limit}))

    @Slot(str)
    def openTrainPlan(self, path: str) -> None:
        """Reads the file written by `train plan --json`. It is only shown; nothing is installed from here."""
        self._planning_set(train=None, trainError="")
        local_path = QUrl(path).toLocalFile() or path
        try:
            with open(local_path, "rb") as handle:
                data = handle.read(planning.MAX_TRAIN_FILE_BYTES + 1)
            parsed = planning.parse_train_plan(data.decode("utf-8")) if len(data) <= planning.MAX_TRAIN_FILE_BYTES else None
        except (OSError, UnicodeDecodeError):
            parsed = None
        if parsed is None:
            self._planning_set(trainError=_("PLANNING_TRAIN_INVALID"))
        else:
            self._planning_set(train=planning.train_view(parsed))

    async def _probe_planning_switches(self) -> None:
        conn = self._controller.active_connection
        state = "unknown"
        if conn is not None:
            try:
                result = await conn.relay_request("datalake", "GET", "/windows")
                state = planning.switch_from_status(result[0] if result else None)
            except Exception as error:  # a damaged answer must not stop the screen
                logger.warning("reading the switches of the data lake failed: %s", error)
        self._planning_set(windows=state)

    async def _planning_call(self, which: str, service: str, method: str, path: str, body: dict | None) -> None:
        conn = self._controller.active_connection
        result = None
        if conn is not None:
            try:
                result = await conn.relay_request(service, method, path, body)
            except Exception as error:  # a damaged answer must not stop the screen
                logger.warning("the %s request of the Planning screen failed: %s", which, error)
        status, answer = (result if result is not None else (None, None))
        problem = planning.failure_text(status, answer)
        values: dict[str, object] = {"busy": ""}
        if which in ("sim", "traj"):
            parsed = planning.parse_simulation(answer) if not problem else None
            values.update(simulation=planning.simulation_view(parsed) if parsed else None, simulationError=problem or ("" if parsed else _("PLANNING_MALFORMED")))
        elif which == "eta":
            parsed = planning.parse_eta(answer) if not problem else None
            values.update(eta=planning.eta_view(parsed) if parsed else None, etaError=problem or ("" if parsed else _("PLANNING_MALFORMED")))
        elif which == "rul":
            parsed = planning.parse_rul(answer) if not problem else None
            values.update(rul=planning.rul_view(parsed) if parsed else "", rulError=problem or ("" if parsed else _("PLANNING_MALFORMED")))
        self._planning_set(**values)

    # -- Robot Control -----------------------------------------------------

    def _active_robots(self) -> list[RobotView]:
        # Cached from the last real active_state_changed delivery (see
        # _on_robot_state_changed below) rather than re-derived from
        # self._controller.active_state on every call: the cache holds the
        # state PARAMETER a signal handler received, which avoids a real
        # staleness risk (re-deriving here would only coincidentally agree
        # with what the signal just carried).
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
        model = robot.model if robot is not None else None
        rows = []
        for name in JOINT_NAMES:
            low, high = joint_range_deg(model, name)
            rows.append({"name": name, "value": joints.get(name, 0.0), "min": low, "max": high})
        return rows

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
        the recorded trajectory points (only on an actual robot-identity
        change, never on every swarm tick: a continuing selection would
        otherwise wipe recordings within moments of making them). Also the
        one real place that forces an immediate Viewport re-render on a
        selection change: the selection reaches both the viewport and the
        trajectory right away, it does not wait for the next real state
        tick's own set_joints_deg() call to happen to redraw it."""
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
        # A joint is never asked for more than the robot can turn: the range of its model (the generic -180..180 for
        # a model with no published range).
        new_joints[joint_name] = min(joint_range_deg(robot.model, joint_name)[1], max(joint_range_deg(robot.model, joint_name)[0], value))

        def local_mutate(r: RobotView, joints=new_joints) -> None:
            for name, joint_value in joints.items():
                r.set_joint(name, joint_value)

        # The atomic 'jog' command with a 50 ms debounce: a full 6-joint
        # override, debounced, is safe here.
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

    # -- Robot Control: playback, tool, valves and pumps -------------------------------

    @Property("QVariantMap", notify=changed)
    def selectedRobotTransport(self) -> dict[str, object]:
        """Which of Play, Pause/Continue and Stop apply: Play needs recorded points to replay and nothing playing."""
        robot = self._selected_robot()
        enabled = robot is not None
        playing = bool(robot and robot.is_playing)
        return {
            "canPlay": enabled and not playing and bool(robot and robot.recorded_point_count > 0),
            "canPause": enabled and playing,
            "paused": bool(robot and robot.is_paused),
            "canStop": enabled and playing,
        }

    @Slot()
    def playSelectedRobot(self) -> None:
        robot = self._selected_robot()
        if robot is not None:
            self._controller.send_robot_command(robot.id, "play", None, lambda r: r.start_playing())

    @Slot()
    def pauseSelectedRobot(self) -> None:
        robot = self._selected_robot()
        if robot is not None:
            paused = not robot.is_paused
            self._controller.send_robot_command(robot.id, "pause", {"paused": paused}, lambda r: r.set_paused(paused))

    @Slot()
    def stopSelectedRobot(self) -> None:
        robot = self._selected_robot()
        if robot is not None:
            self._controller.send_robot_command(robot.id, "stop", None, lambda r: r.stop_playing())

    @Property("QVariantList", constant=True)
    def toolOptions(self) -> list[str]:
        return list(URTC_TOOLS)

    @Property(str, notify=changed)
    def selectedRobotTool(self) -> str:
        robot = self._selected_robot()
        return robot.tool if robot is not None else "None"

    @Slot(str)
    def setSelectedRobotTool(self, tool: str) -> None:
        """The tool decides what the robot does with the following moves; the screen asks before calling this."""
        robot = self._selected_robot()
        if robot is not None and tool in URTC_TOOLS and tool != robot.tool:
            self._controller.send_robot_command(robot.id, "tool", {"tool": tool}, lambda r: r.set_tool(tool))

    @Property("QVariantList", notify=changed)
    def selectedRobotValves(self) -> list[bool]:
        robot = self._selected_robot()
        return robot.valves if robot is not None else [False, False]

    @Property("QVariantList", notify=changed)
    def selectedRobotPumps(self) -> list[bool]:
        robot = self._selected_robot()
        return robot.pumps if robot is not None else [False, False]

    @Slot(int, bool)
    def setSelectedValve(self, index: int, state: bool) -> None:
        robot = self._selected_robot()
        if robot is not None and index in (0, 1):
            self._controller.send_robot_command(robot.id, "valve", {"index": index, "state": state}, lambda r: r.set_valve(index, state))

    @Slot(int, bool)
    def setSelectedPump(self, index: int, state: bool) -> None:
        robot = self._selected_robot()
        if robot is not None and index in (0, 1):
            self._controller.send_robot_command(robot.id, "pump", {"index": index, "state": state}, lambda r: r.set_pump(index, state))

    # -- Works (trajectory files shared with HYDRA-UMC-STUDIO) ------------------------

    def _works_folder_path(self, robot: RobotView) -> str:
        """The folder STUDIO uses for this robot: `settings.worksPaths[robot.id]` when the operator set one, else
        WORKS/<name of the robot without blanks>, so this program reads and writes the same files a browser does."""
        state = self._controller.active_state
        works_paths = ((state.raw.get("settings") or {}).get("worksPaths") or {}) if state is not None else {}
        configured = works_paths.get(robot.id)
        if configured:
            return str(configured)
        name = str(robot.raw.get("name") or robot.id)
        return "WORKS/" + "".join(name.split())

    @Property("QVariantList", notify=_trajectoryChanged)
    def workFiles(self) -> list[str]:
        return self._work_files

    @Slot()
    def refreshWorkFiles(self) -> None:
        asyncio.ensure_future(self._refresh_work_files())

    async def _refresh_work_files(self) -> None:
        conn, robot = self._controller.active_connection, self._selected_robot()
        self._work_files = []
        if conn is None or robot is None:
            self._set_notice(_("LBL_ES_NO_ACTIVE_SERVER"), "warn")
        else:
            result = await conn.fetch_works_index(self._works_folder_path(robot))
            files = [f for f in result[1] if isinstance(f, str)] if result is not None and result[0] == 200 and isinstance(result[1], list) else []
            self._work_files = files
            if not files:
                self._set_notice(_("MSG_WORK_IMPORT_FAILED", error=_("MSG_WORK_ERR_NO_WORKS")), "warn")
        self._trajectoryChanged.emit()

    @Slot(str)
    def exportWork(self, name: str) -> None:
        asyncio.ensure_future(self._export_work(name))

    async def _export_work(self, name: str) -> None:
        conn, robot = self._controller.active_connection, self._selected_robot()
        name = name.strip()
        if robot is None or not self._trajectory_points or not name:
            return
        if conn is None:
            self._set_notice(_("LBL_ES_NO_ACTIVE_SERVER"), "warn")
            return
        if not name.endswith(".json"):
            name += ".json"
        # The local "_time" column is not part of a Work: STUDIO's files never carry it.
        # The joints are this robot's own, so STUDIO must not read them as the portable joints of the generic arm.
        content = [{"motionType": "model-joints", **{joint: point[joint] for joint in JOINT_NAMES}} for point in self._trajectory_points]
        folder = self._works_folder_path(robot)
        result = await conn.save_work_file(folder, name, content)
        if result is None:
            self._set_notice(_("MSG_WORK_EXPORT_FAILED", error=_("MSG_WORK_ERR_NETWORK")), "warn")
        elif result[0] != 200:
            error = result[1].get("error") if isinstance(result[1], dict) else str(result[1])
            self._set_notice(_("MSG_WORK_EXPORT_FAILED", error=error), "warn")
        else:
            self._set_notice(_("MSG_WORK_EXPORTED", file=f"{folder}/{name}"), "info")

    @Slot(str)
    def importWork(self, name: str) -> None:
        asyncio.ensure_future(self._import_work(name))

    async def _import_work(self, name: str, scale: float | None = None) -> None:
        conn, robot = self._controller.active_connection, self._selected_robot()
        if conn is None or robot is None or not name:
            return
        result = await conn.fetch_work_file(self._works_folder_path(robot), name)
        if result is None or result[0] != 200 or not isinstance(result[1], list):
            self._set_notice(_("MSG_WORK_IMPORT_FAILED", error=_("MSG_WORK_ERR_READ", file=name)), "warn")
            return
        model = robot.model
        # native points (motionType "model-joints") are taken as they are; portable ones (no motionType, like STUDIO's) are
        # turned into joints of this model by its inverse kinematics: reach.read_work_points tells them apart
        reading = reach.read_work_points(model, result[1])
        entries, skipped, outside = reading.entries, reading.skipped, reading.outside
        if outside:
            # A Work made for another robot: refused as a whole, with the list of the points this model cannot reach.
            listed = ", ".join(str(n) for n in outside[:12]) + (f" (+{len(outside) - 12})" if len(outside) > 12 else "")
            self._set_notice(_("MSG_WORK_OUT_OF_RANGE", file=name, model=model, count=len(outside), points=listed), "warn")
            return
        if not entries:
            self._set_notice(_("MSG_WORK_IMPORT_FAILED", error=_("MSG_WORK_ERR_NO_JOINTS", file=name)), "warn")
            return
        loop = asyncio.get_running_loop()
        tolerance = reach.tolerance_from_config(load_config())  # 5 mm unless hydra_suite_config.json says otherwise
        factor = 1.0 if scale is None else scale
        solved = await loop.run_in_executor(None, self._solve_work_entries, model, entries, factor, tolerance)
        over = [(e["number"], mm) for e, mm in solved["residuals"] if mm > tolerance]
        if over and scale is None:
            # Points the arm cannot reach: the Work is refused as a whole, with those points and how far they are, and
            # the operator is offered the same Work scaled about the base to the reach of the model.
            listed = ", ".join(str(n) for n, _mm in over[:12]) + (f" (+{len(over) - 12})" if len(over) > 12 else "")
            worst = max(mm for _n, mm in over)
            self._set_notice(_("MSG_WORK_OUT_OF_REACH", file=name, model=model, count=len(over), tolerance=f"{tolerance:g}", worst=f"{worst:.0f}", points=listed), "warn")
            poses = [e["pose"] for e in entries if "pose" in e]
            fit = await loop.run_in_executor(None, reach.find_scale, model, poses, tolerance)
            if fit.scale < 1.0 and fit.remaining < len(over):
                self._pending_work_scale = {"robot": robot.id, "file": name, "scale": fit.scale}
                key = "MSG_WORK_SCALE_OFFER" if fit.fits else "MSG_WORK_SCALE_OFFER_PARTIAL"
                self.workScaleOffered.emit(_("TITLE_WORK_SCALE"), _(key, file=name, model=model, percent=f"{fit.scale * 100:.0f}", remaining=fit.remaining), _("BTN_WORK_SCALE"))
            return
        imported = solved["points"]
        migrated = reading.migrated  # portable points (no motionType) solved into joints of this model
        for point in imported:
            point["_time"] = time.strftime("%H:%M:%S")
        self._trajectory_points = imported
        self._trajectoryChanged.emit()
        if scale is not None:
            self._set_notice(_("MSG_WORK_SCALED", file=name, percent=f"{scale * 100:.0f}", imported=len(imported)), "info")
        elif skipped:
            self._set_notice(_("MSG_WORK_IMPORT_PARTIAL", imported=len(imported), skipped=skipped), "info")
        elif migrated:
            # a Work with no motionType is portable authoring data: its points were turned into joints of this robot, which is what is kept and exported
            self._set_notice(_("MSG_WORK_MIGRATED", file=name, model=model, count=migrated), "info")

    @staticmethod
    def _solve_work_entries(model: str, entries: list[dict[str, object]], factor: float, tolerance: float) -> dict:
        """Turns the entries of a Work into points of this robot (runs off the interface thread)."""
        points: list[dict[str, object]] = []
        residuals: list[tuple[dict[str, object], float]] = []
        seed = None
        for entry in entries:
            if "joints" in entry:
                points.append(dict(entry["joints"]))  # type: ignore[arg-type]
                continue
            joints, residual = reach.solve_pose(model, reach.scaled(entry["pose"], factor), seed)  # type: ignore[arg-type]
            seed = (joints["j1"], joints["j2"], joints["j3"])
            residuals.append((entry, residual))
            points.append({name: float(value) for name, value in joints.items()})
        return {"points": points, "residuals": residuals}

    @Slot()
    def applyWorkScale(self) -> None:
        pending, self._pending_work_scale = self._pending_work_scale, None
        robot = self._selected_robot()
        if pending is None or robot is None or robot.id != pending["robot"]:
            return
        asyncio.ensure_future(self._import_work(str(pending["file"]), float(pending["scale"])))

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
        """Moves the robot to a recorded point as a jog command (so Sim, the limits and the arming apply, and the
        joints stay inside the range of the model), not as a write of the whole settings tree."""
        robot = self._selected_robot()
        if robot is None or not 0 <= index < len(self._trajectory_points):
            return
        point = self._trajectory_points[index]
        joints = {name: min(joint_range_deg(robot.model, name)[1], max(joint_range_deg(robot.model, name)[0], float(point[name]))) for name in JOINT_NAMES}

        def local_mutate(r: RobotView, values=joints) -> None:
            for name, value in values.items():
                r.set_joint(name, value)

        self._controller.send_robot_command(
            robot.id, "jog", {"axis": "x", "amount": 0, "target": "robot", "joints": joints}, local_mutate
        )
        self.changed.emit()

    @Slot(int)
    def deleteTrajectoryPoint(self, index: int) -> None:
        if 0 <= index < len(self._trajectory_points):
            del self._trajectory_points[index]
            self._trajectoryChanged.emit()

    # -- AI Family Status --------------------------------------------------

    @Property(str, notify=ecosystemChanged)
    def aiFamilyStatusText(self) -> str:
        return self._ai_family_status_text

    @Property(bool, notify=ecosystemChanged)
    def aiFamilyRefreshing(self) -> bool:
        return self._ai_family_refreshing

    @Property("QVariantList", notify=ecosystemChanged)
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
            self.ecosystemChanged.emit()
            return
        self._ai_family_refreshing = True
        self.ecosystemChanged.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._ai_family_refreshing = False
        if result is None:
            self._ai_family_status_text = _("MSG_ES_LOAD_ERROR")
            self.ecosystemChanged.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict) or not body.get("available"):
            self._ai_family_status_text = _("MSG_ES_UNAVAILABLE")
            self.ecosystemChanged.emit()
            return
        self._ai_family_status_text = ""
        families = {f for f, _dev, _label in AI_FAMILIES}
        self._ai_family_projects = [p for p in (body.get("projects") or []) if p.get("family") in families]
        self._ai_family_ai_hailo = conn.state.ai_hailo
        self.ecosystemChanged.emit()

    # -- Admin Clients -----------------------------------------------------

    @Property(str, notify=_adminClientsChanged)
    def adminClientsStatusText(self) -> str:
        return self._admin_clients_status_text

    @Property(bool, notify=_adminClientsChanged)
    def adminClientsShowStats(self) -> bool:
        return len(self._admin_clients) > 0

    @Property(int, notify=_adminClientsChanged)
    def adminClientsConnectedCount(self) -> int:
        return len(self._admin_clients)

    @Property(int, notify=_adminClientsChanged)
    def adminClientsAdminCount(self) -> int:
        return sum(1 for c in self._admin_clients if c.get("role") == "admin")

    @Property("QVariantList", notify=_adminClientsChanged)
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

    # -- Connection history (any signed-in account) --------------------------

    @Property(str, notify=_adminClientsChanged)
    def connectionHistoryStatus(self) -> str:
        return self._connection_status_text

    @Property("QVariantList", notify=_adminClientsChanged)
    def connectionClientRows(self) -> list[dict[str, object]]:
        return connection_history.client_rows(self._connection_clients)

    @Property("QVariantList", notify=_adminClientsChanged)
    def connectionEventRows(self) -> list[dict[str, object]]:
        return connection_history.event_rows(self._connection_events)

    async def _refresh_connection_history(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._connection_clients, self._connection_events, self._connection_status_text = [], [], ""
            return
        clients = await conn.fetch_connection_clients()
        events = await conn.fetch_connection_events(30)
        problem = connection_history.status_for(clients) or connection_history.status_for(events)
        self._connection_status_text = problem
        if problem:
            self._connection_clients, self._connection_events = [], []
        else:
            self._connection_clients = connection_history.parse_clients(clients[1])  # type: ignore[index]
            self._connection_events = connection_history.parse_events(events[1])  # type: ignore[index]

    async def _refresh_admin_clients(self) -> None:
        try:
            await self._refresh_connection_history()
        except Exception as error:  # a damaged answer must not stop the clients list
            logger.warning("reading the connection history failed: %s", error)
            self._connection_status_text = _("CONNECTIONS_LOAD_ERROR")
        await self._refresh_admin_clients_list()

    async def _refresh_admin_clients_list(self) -> None:
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

    @Property(str, notify=adminLogsChanged)
    def adminLogsStatusText(self) -> str:
        return self._admin_logs_status_text

    @Property(bool, notify=adminLogsChanged)
    def adminLogsLive(self) -> bool:
        return self._admin_logs_live

    @Property(str, notify=adminLogsChanged)
    def adminLogsTagFilter(self) -> str:
        return self._admin_logs_tag_filter or ""

    @Property("QStringList", notify=adminLogsChanged)
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
            # (panel_logic/admin_logs.py does the same).
            return self._admin_logs_all_lines
        return self._admin_logs_all_lines[idx + 1:]

    @Property("QStringList", notify=adminLogsChanged)
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
        self.adminLogsChanged.emit()

    @Slot()
    def clearAdminLogs(self) -> None:
        if self._admin_logs_all_lines:
            self._admin_logs_cleared_anchor = self._admin_logs_all_lines[-1]
            self._admin_logs_cleared_at_empty = False
        else:
            self._admin_logs_cleared_anchor = None
            self._admin_logs_cleared_at_empty = True
        self.adminLogsChanged.emit()

    @Slot(str)
    def setAdminLogsTagFilter(self, tag: str) -> None:
        self._admin_logs_tag_filter = tag or None
        self.adminLogsChanged.emit()

    @Slot(str)
    def setAdminLogsSearch(self, text: str) -> None:
        self._admin_logs_search = text
        self.adminLogsChanged.emit()

    async def _refresh_admin_logs(self) -> None:
        if not self._admin_logs_live:
            return
        conn = self._controller.active_connection
        if conn is None:
            self._admin_logs_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.adminLogsChanged.emit()
            return
        if not conn.is_admin:
            self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
            self._admin_logs_all_lines = []
            self.adminLogsChanged.emit()
            return
        result = await conn.fetch_admin_logs(_ADMIN_LOGS_LINES)
        if result is None:
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.adminLogsChanged.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.adminLogsChanged.emit()
            return
        self._admin_logs_all_lines = body.get("lines") or []
        self._admin_logs_status_text = _("LBL_LOGS_FOOTER_LIVE", lines=_ADMIN_LOGS_LINES, seconds=_ADMIN_LOGS_POLL_MS // 1000)
        self.adminLogsChanged.emit()

    # -- Admin Server ------------------------------------------------------

    @Property(str, notify=securityChanged)
    def adminServerStatusText(self) -> str:
        return self._admin_server_status_text

    @Property(bool, notify=securityChanged)
    def adminServerInfoVisible(self) -> bool:
        return bool(self._admin_server_info)

    @Property(str, notify=securityChanged)
    def adminServerProduct(self) -> str:
        return str(self._admin_server_info.get("product") or "-")

    @Property(str, notify=securityChanged)
    def adminServerVersion(self) -> str:
        version = self._admin_server_info.get("appVersion")
        return f"v{version}" if version else "-"

    @Property(str, notify=securityChanged)
    def adminServerUptime(self) -> str:
        return _format_uptime(self._admin_server_info.get("uptimeSeconds"))

    @Property(str, notify=securityChanged)
    def adminServerControllerCount(self) -> str:
        return str(self._admin_server_info.get("controllerCount", "-"))

    @Property(str, notify=securityChanged)
    def adminServerRobotCount(self) -> str:
        return str(self._admin_server_info.get("robotCount", "-"))

    @Property(str, notify=securityChanged)
    def adminServerHost(self) -> str:
        return str(self._admin_server_info.get("hostname") or "-")

    @Property(str, notify=securityChanged)
    def adminServerPortLabel(self) -> str:
        port = self._admin_server_current_port if self._admin_server_current_port is not None else "..."
        return _("LBL_ADMIN_SERVER_PORT_CURRENT", port=port)

    @Property(str, notify=securityChanged)
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
        self._security_state = server_security.parse_state(body)
        await self._refresh_hub_gate(conn)
        await self._refresh_planner_identity(conn)
        await self._refresh_ops_proposals(conn)
        await self._refresh_hil_bridge(conn)
        await self._refresh_service_identity(conn)
        self._detection_hef = detection_hef.parse_state(body)
        self._live_activity = live_activity.parse_state(body)
        await self._refresh_tool_arms(conn)
        await self._refresh_developer_nodes(conn, False)
        if self._twin_watching and self._twin_task is None:
            self._restart_twin_feed()

        info_result = await conn.fetch_hydra_info()
        if info_result is not None:
            info_status, info_body = info_result
            if info_status == 200 and isinstance(info_body, dict):
                self._admin_server_info = info_body
        self.changed.emit()

    # -- Switch of the connector hub gate (administrators) -----------------------------

    async def _refresh_hub_gate(self, conn) -> None:
        try:
            result = await conn.fetch_connector_hub_gate_settings()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the connector hub gate settings failed: %s", error)
            result = None
        self._hub_gate_error = ""
        if connector_hub_gate.hidden_for(result):
            self._hub_gate = None
            return
        self._hub_gate_error = connector_hub_gate.status_for(result)
        self._hub_gate = connector_hub_gate.parse_settings(result[1]) if result is not None and not self._hub_gate_error else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def hubGateView(self) -> dict:
        view = connector_hub_gate.view(self._hub_gate)
        view["message"] = self._hub_gate_message
        view["error"] = self._hub_gate_error
        view["visible"] = self._hub_gate is not None or bool(self._hub_gate_error)
        return view

    @Slot(bool, result=bool)
    def hubGateNeedsConfirmation(self, wanted: bool) -> bool:
        return self._hub_gate is not None and connector_hub_gate.needs_confirmation(self._hub_gate["allow"], wanted)

    @Slot(bool)
    def saveHubGate(self, wanted: bool) -> None:
        if self._hub_gate is None or not connector_hub_gate.change_allowed(self._hub_gate, wanted):
            return
        asyncio.ensure_future(self._save_hub_gate(wanted))

    async def _save_hub_gate(self, wanted: bool) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._hub_gate_message = ""
        result = await conn.put_connector_hub_gate_settings(connector_hub_gate.body_for(wanted))
        problem = connector_hub_gate.status_for(result)
        if problem:
            self._hub_gate_error = problem
        else:
            self._hub_gate_error = ""
            self._hub_gate = connector_hub_gate.parse_settings(result[1])  # type: ignore[index]
            self._hub_gate_message = _("HUBGATE_SAVED")
        self.adminSwitchesChanged.emit()

    # -- Switch of the identity of the approval of a plan (administrators) ---------------

    async def _refresh_planner_identity(self, conn) -> None:
        try:
            result = await conn.fetch_semantic_planner_settings()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the semantic planner settings failed: %s", error)
            result = None
        self._planner_identity_error = ""
        if planner_identity.hidden_for(result):
            self._planner_identity = None
            return
        self._planner_identity_error = planner_identity.status_for(result)
        self._planner_identity = planner_identity.parse_settings(result[1]) if result is not None and not self._planner_identity_error else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def plannerIdentityView(self) -> dict:
        view = planner_identity.view(self._planner_identity)
        view["message"] = self._planner_identity_message
        view["error"] = self._planner_identity_error
        view["visible"] = self._planner_identity is not None or bool(self._planner_identity_error)
        return view

    @Slot(bool, result=bool)
    def plannerIdentityNeedsConfirmation(self, wanted: bool) -> bool:
        return self._planner_identity is not None and planner_identity.needs_confirmation(self._planner_identity["require"], wanted)

    @Slot(bool)
    def savePlannerIdentity(self, wanted: bool) -> None:
        if self._planner_identity is None or not planner_identity.change_allowed(self._planner_identity, wanted):
            return
        asyncio.ensure_future(self._save_planner_identity(wanted))

    async def _save_planner_identity(self, wanted: bool) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._planner_identity_message = ""
        result = await conn.put_semantic_planner_settings(planner_identity.body_for(wanted))
        problem = planner_identity.status_for(result)
        if problem:
            self._planner_identity_error = problem
        else:
            self._planner_identity_error = ""
            self._planner_identity = planner_identity.parse_settings(result[1])  # type: ignore[index]
            self._planner_identity_message = _("PLANNERID_SAVED")
        self.adminSwitchesChanged.emit()

    # -- Identity of the server in its calls to the services (administrators) ----------------

    async def _refresh_service_identity(self, conn) -> None:
        try:
            result = await conn.fetch_service_identity()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the identity of the services failed: %s", error)
            result = None
        self._service_identity_error = ""
        if service_identity.hidden_for(result):
            self._service_identity = None
            return
        self._service_identity_error = service_identity.status_for(result)
        self._service_identity = service_identity.parse_status(result[1]) if result is not None and not self._service_identity_error else None

    @Property("QVariantMap", notify=securityChanged)
    def serviceIdentityView(self) -> dict:
        view = service_identity.view(self._service_identity)
        view["message"] = self._service_identity_message
        view["error"] = self._service_identity_error
        view["visible"] = self._service_identity is not None or bool(self._service_identity_error)
        return view

    @Slot(bool, result=bool)
    def serviceIdentityNeedsConfirmation(self, wanted: bool) -> bool:
        return self._service_identity is not None and service_identity.needs_confirmation(self._service_identity["enabled"], wanted)

    @Slot(bool)
    def saveServiceIdentity(self, wanted: bool) -> None:
        if self._service_identity is None or not service_identity.change_allowed(self._service_identity, wanted):
            return
        asyncio.ensure_future(self._save_service_identity(wanted))

    async def _save_service_identity(self, wanted: bool) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._service_identity_message = ""
        result = await conn.put_service_identity(service_identity.body_for(wanted))
        problem = service_identity.status_for(result)
        if problem:
            self._service_identity_error = problem
        else:
            self._service_identity_error = ""
            await self._refresh_service_identity(conn)
            self._service_identity_message = _("SERVICEID_SAVED") + ((" " + _("SERVICEID_OFF_WARNING")) if not wanted else "")
        self.securityChanged.emit()

    # -- Switch of the loaded-model reports of DETECTION-HEF (administrators) ------------------

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def detectionHefView(self) -> dict:
        view = detection_hef.view(self._detection_hef)
        view["message"] = self._detection_hef_message
        view["error"] = self._detection_hef_error
        view["visible"] = self._detection_hef is not None
        return view

    @Slot(bool, result=bool)
    def detectionHefNeedsConfirmation(self, wanted: bool) -> bool:
        return self._detection_hef is not None and detection_hef.needs_confirmation(self._detection_hef["enabled"], wanted)

    @Slot(bool)
    def saveDetectionHef(self, wanted: bool) -> None:
        if self._detection_hef is None or not detection_hef.change_allowed(self._detection_hef, wanted):
            return
        asyncio.ensure_future(self._save_detection_hef(wanted))

    async def _save_detection_hef(self, wanted: bool) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._detection_hef_message = ""
        try:
            result = await conn.put_detection_hef(detection_hef.body_for(wanted))
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("saving the switch of the DETECTION-HEF reports failed: %s", error)
            result = None
        problem = detection_hef.status_for(result)
        if problem:
            self._detection_hef_error = problem
        else:
            self._detection_hef_error = ""
            self._detection_hef = {"enabled": wanted, "locked": False}
            self._detection_hef_message = _("DETHEF_SAVED")
        self.adminSwitchesChanged.emit()

    # -- Live Activity on the lock screen (administrators) -------------------------------------

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def liveActivityView(self) -> dict:
        view = live_activity.view(self._live_activity)
        view["message"] = self._live_activity_message
        view["error"] = self._live_activity_error
        view["visible"] = self._live_activity is not None
        return view

    @Slot(bool, str, result=bool)
    def liveActivityNeedsConfirmation(self, enabled: bool, level: str) -> bool:
        if self._live_activity is None:
            return False
        return live_activity.needs_confirmation(self._live_activity, live_activity.change_for(self._live_activity, enabled, level))

    @Slot(bool, str)
    def saveLiveActivity(self, enabled: bool, level: str) -> None:
        if self._live_activity is None:
            return
        change = live_activity.change_for(self._live_activity, enabled, level)
        if not change:
            return
        asyncio.ensure_future(self._save_live_activity(change))

    async def _save_live_activity(self, change: dict) -> None:
        conn = self._controller.active_connection
        state = self._live_activity
        if conn is None or not conn.is_admin or state is None:
            return
        self._live_activity_message = ""
        try:
            result = await conn.put_live_activity(live_activity.body_for(state, change))
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("saving the Live Activity setting failed: %s", error)
            result = None
        problem = live_activity.status_for(result)
        if problem:
            self._live_activity_error = problem
        else:
            self._live_activity_error = ""
            self._live_activity = dict(state, enabled=change.get("enabled", state["enabled"]), level=change.get("level", state["level"]))
            self._live_activity_message = _("LIVEACT_SAVED")
        self.adminSwitchesChanged.emit()

    # -- Live state of the twin through the server (any signed-in account, read only) ---------------

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def twinFeedView(self) -> dict:
        return twin_feed.view(self._twin_watching, self._twin_link, self._twin_state)

    @Slot(bool)
    def setTwinFeedWatching(self, on: bool) -> None:
        self._twin_watching = bool(on)
        save_config(twin_feed.config_update(self._twin_watching))
        self._twin_state = twin_feed.empty_state()
        self._restart_twin_feed()
        self.adminSwitchesChanged.emit()

    def _restart_twin_feed(self) -> None:
        task, self._twin_task = self._twin_task, None
        if task is not None:
            task.cancel()
        if not self._twin_watching:
            self._twin_link = "off"
            return
        self._twin_link = "connecting"
        self._twin_task = asyncio.ensure_future(self._run_twin_feed())

    def _on_twin_frame(self, raw: str) -> None:
        frame = twin_feed.parse_frame(raw)
        if frame is None:
            return
        self._twin_state = twin_feed.apply_frame(self._twin_state, frame)
        self.adminSwitchesChanged.emit()

    def _on_twin_open(self) -> None:
        self._twin_link = "live"
        self.adminSwitchesChanged.emit()

    async def _run_twin_feed(self) -> None:
        while self._twin_watching:
            conn = self._controller.active_connection
            if conn is None:
                await asyncio.sleep(twin_feed.RECONNECT_S)
                continue
            self._twin_link = "connecting"
            self.adminSwitchesChanged.emit()
            try:
                code = await conn.watch_twin_feed(self._on_twin_frame, self._on_twin_open)
            except asyncio.CancelledError:
                raise
            except Exception as error:  # a damaged frame or link must not stop the screen
                logger.warning("the twin feed failed: %s", error)
                code = None
            end = twin_feed.end_for_close_code(code)
            self._twin_link = end
            self.adminSwitchesChanged.emit()
            if not twin_feed.retries(end):
                return
            await asyncio.sleep(twin_feed.RECONNECT_S)

    # -- Arm state of the URTC tools (read only) -------------------------------------------

    async def _refresh_tool_arms(self, conn) -> None:
        try:
            result = await conn.fetch_tool_arms()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the arm state of the tools failed: %s", error)
            result = None
        self._tool_arms_error = tool_arms.status_for(result)
        self._tool_arms = tool_arms.parse_report(result[1]) if result is not None and not self._tool_arms_error else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def toolArmsView(self) -> dict:
        view = tool_arms.view(self._tool_arms)
        view["error"] = self._tool_arms_error
        return view

    @Slot()
    def refreshToolArms(self) -> None:
        asyncio.ensure_future(self._reload_tool_arms())

    async def _reload_tool_arms(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        await self._refresh_tool_arms(conn)
        self.changed.emit()

    # -- Switch of the pass verdict of the twin on the HIL bridge (administrators) ---------------

    async def _refresh_hil_bridge(self, conn) -> None:
        try:
            result = await conn.fetch_hil_bridge_settings()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the HIL bridge settings failed: %s", error)
            result = None
        self._hil_bridge_error = ""
        if hil_bridge.hidden_for(result):
            self._hil_bridge = None
            return
        self._hil_bridge_error = hil_bridge.status_for(result)
        self._hil_bridge = hil_bridge.parse_settings(result[1]) if result is not None and not self._hil_bridge_error else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def hilBridgeView(self) -> dict:
        view = hil_bridge.view(self._hil_bridge)
        view["message"] = self._hil_bridge_message
        view["error"] = self._hil_bridge_error
        view["visible"] = self._hil_bridge is not None or bool(self._hil_bridge_error)
        view["blocked"] = ""
        return view

    @Slot(bool, result=str)
    def hilBridgeBlockedText(self, wanted: bool) -> str:
        """The sentence for what the bridge would refuse for this wish, empty when it would accept it."""
        if self._hil_bridge is None:
            return ""
        reason = hil_bridge.blocked_reason(self._hil_bridge, wanted)
        return _("HILBRIDGE_" + reason.upper()) if reason else ""

    @Slot(bool, result=bool)
    def hilBridgeNeedsConfirmation(self, wanted: bool) -> bool:
        return self._hil_bridge is not None and hil_bridge.needs_confirmation(self._hil_bridge["require"], wanted)

    @Slot(bool)
    def saveHilBridge(self, wanted: bool) -> None:
        if self._hil_bridge is None or hil_bridge.blocked_reason(self._hil_bridge, wanted):
            return
        asyncio.ensure_future(self._save_hil_bridge(wanted))

    async def _save_hil_bridge(self, wanted: bool) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._hil_bridge_message = ""
        result = await conn.put_hil_bridge_settings(hil_bridge.body_for(wanted))
        problem = hil_bridge.status_for(result)
        if problem:
            self._hil_bridge_error = problem
        else:
            self._hil_bridge_error = ""
            self._hil_bridge = hil_bridge.parse_settings(result[1])  # type: ignore[index]
            self._hil_bridge_message = _("HILBRIDGE_SAVED")
        self.adminSwitchesChanged.emit()

    # -- Proposals of the node watchdog that wait for a person (administrators) ---------------

    async def _refresh_ops_proposals(self, conn) -> None:
        try:
            result = await conn.fetch_ops_agent_proposals()
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the proposals of the node watchdog failed: %s", error)
            result = None
        self._ops_proposals_error = ""
        if ops_proposals.hidden_for(result):
            self._ops_proposals = None
            return
        self._ops_proposals_error = ops_proposals.status_for(result)
        self._ops_proposals = ops_proposals.parse_lists(result[1]) if result is not None and not self._ops_proposals_error else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def opsProposalsView(self) -> dict:
        view = ops_proposals.view(self._ops_proposals)
        view["message"] = self._ops_proposals_message
        view["error"] = self._ops_proposals_error
        view["visible"] = self._ops_proposals is not None or bool(self._ops_proposals_error)
        return view

    @Slot(str, result=str)
    def opsProposalConfirmMessage(self, incident_id: str) -> str:
        return _("OPSPROP_CONFIRM_MESSAGE", id=incident_id)

    @Slot()
    def refreshOpsProposals(self) -> None:
        asyncio.ensure_future(self._reload_ops_proposals())

    async def _reload_ops_proposals(self) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._ops_proposals_message = ""
        await self._refresh_ops_proposals(conn)
        self.adminSwitchesChanged.emit()

    @Slot(str, str)
    def decideOpsProposal(self, incident_id: str, decision: str) -> None:
        if self._ops_proposals is None or decision not in ops_proposals.DECISIONS or not incident_id:
            return
        asyncio.ensure_future(self._decide_ops_proposal(incident_id, decision))

    async def _decide_ops_proposal(self, incident_id: str, decision: str) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._ops_proposals_message = ""
        result = await conn.decide_ops_agent_proposal(ops_proposals.body_for(incident_id, decision))
        problem = "" if ops_proposals.decision_ok(result, decision) else ops_proposals.status_for(result) or _("OPSPROP_LOAD_ERROR")
        await self._refresh_ops_proposals(conn)
        if problem:
            self._ops_proposals_error = problem
        else:
            self._ops_proposals_message = _("OPSPROP_APPROVED" if decision == "approved" else "OPSPROP_REJECTED", id=incident_id)
        self.adminSwitchesChanged.emit()

    # -- Access options of the Server Admin screen -----------------------------------

    @Property("QVariantMap", notify=securityChanged)
    def securityView(self) -> dict:
        return server_security.view(self._security_state)

    @Property("QVariantList", constant=True)
    def securityAiOptions(self) -> list[dict[str, str]]:
        return server_security.ai_options()

    @Property("QVariantList", constant=True)
    def securityBleModes(self) -> list[dict[str, str]]:
        return server_security.ble_mode_options()

    @Property("QVariantList", constant=True)
    def securityMqttModes(self) -> list[dict[str, str]]:
        return server_security.mqtt_mode_options()

    @Property(str, notify=securityChanged)
    def securityMessage(self) -> str:
        return self._security_message

    @Property(str, notify=securityChanged)
    def securityError(self) -> str:
        return self._security_error

    @Property(str, notify=securityChanged)
    def securityWarning(self) -> str:
        return self._security_warning

    # --- signature check of firmware on this computer (configuration file, not the server) ---

    def _firmware_signing_settings(self) -> firmware_signature.SigningSettings:
        return firmware_signature.read_settings(i18n_module.load_config(), i18n_module.CONFIG_FILE_PATH)

    @Property("QVariantMap", notify=changed)
    def firmwareSigningView(self) -> dict:
        settings = self._firmware_signing_settings()
        key, problem = firmware_signature.load_public_key(settings.key_file)
        return {
            "verify": settings.verify,
            "keyFile": str(settings.key_file),
            "keyOk": key is not None,
            "keyStatus": _("FW_SIG_KEY_LOADED") if key is not None else _(problem),
            "fingerprint": firmware_signature.key_fingerprint(key) if key is not None else "",
            "configFile": str(i18n_module.CONFIG_FILE_PATH),
            "warning": "" if settings.verify else _("FW_SIG_WARNING_OFF"),
        }

    @Slot(bool, result=bool)
    def firmwareSigningNeedsConfirmation(self, verify: bool) -> bool:
        """Turning the check off lowers a protection, so the page asks first."""
        return not verify and self._firmware_signing_settings().verify

    @Slot(bool)
    def setFirmwareSigningVerify(self, verify: bool) -> None:
        self._save_firmware_signing(verify=verify)

    @Slot(str)
    def setFirmwareSigningKeyFile(self, path: str) -> None:
        self._save_firmware_signing(key_file=path.strip())

    def _save_firmware_signing(self, verify: bool | None = None, key_file: str | None = None) -> None:
        section = i18n_module.load_config().get(firmware_signature.CONFIG_KEY)
        section = dict(section) if isinstance(section, dict) else {}
        if verify is not None:
            section["verify"] = bool(verify)
        if key_file is not None:
            section["publicKeyFile"] = key_file
        if i18n_module.save_config({firmware_signature.CONFIG_KEY: section}):
            self._set_notice(_("FW_SIG_SAVED"), "info")
        else:
            self._set_notice(_("MSG_LANGUAGE_NOT_SAVED", path=i18n_module.CONFIG_FILE_PATH), "warn")
        self.changed.emit()

    # --- pinning of the certificate of a server (configuration file; off unless the person turns it on) ---

    @Property("QVariantMap", notify=changed)
    def tlsPinningView(self) -> dict:
        enabled, pins = tls_pin.read_settings(load_config())
        return {
            "enabled": enabled,
            "servers": [{"address": address, "fingerprint": entry["fingerprint"]} for address, entry in sorted(pins.items())],
            "configFile": str(CONFIG_FILE_PATH),
        }

    def _save_tls_pinning(self, section: dict) -> None:
        if save_config({tls_pin.CONFIG_KEY: section}):
            self._set_notice(_("TLS_PIN_SAVED"), "info")
        else:
            self._set_notice(_("MSG_LANGUAGE_NOT_SAVED", path=CONFIG_FILE_PATH), "warn")
        self.changed.emit()

    @Slot(bool)
    def setTlsPinningEnabled(self, enabled: bool) -> None:
        self._save_tls_pinning(tls_pin.with_enabled(load_config(), enabled))

    @Slot(str, str)
    def pinServerCertificate(self, address: str, fingerprint: str) -> None:
        """Reads the certificate the server at `address` (host or host:port) shows and pins it; with a fingerprint typed, only if it matches."""
        host, port = self._split_server_address(address)
        if not host:
            self._set_notice(_("TLS_PIN_BAD_ADDRESS"), "warn")
            return
        asyncio.ensure_future(self._pin_server_certificate(host, port, fingerprint.strip()))

    async def _pin_server_certificate(self, host: str, port: int, fingerprint: str) -> None:
        loop = asyncio.get_running_loop()
        try:
            pem, _shown = await loop.run_in_executor(None, tls_pin.fetch_certificate, host, port)
            section = tls_pin.pin_entry(load_config(), host, port, pem, expected_fingerprint=fingerprint)
        except tls_pin.PinError as error:
            self._set_notice(_("TLS_PIN_FAILED", reason=str(error)), "warn")
            return
        self._save_tls_pinning(section)

    @Slot(str)
    def unpinServer(self, address: str) -> None:
        host, port = self._split_server_address(address)
        if not host:
            self._set_notice(_("TLS_PIN_BAD_ADDRESS"), "warn")
            return
        self._save_tls_pinning(tls_pin.unpin_entry(load_config(), host, port))

    @staticmethod
    def _split_server_address(address: str) -> tuple[str, int]:
        text = address.strip()
        host, _sep, port_text = text.rpartition(":")
        if not _sep or not port_text.isdigit():
            host, port_text = text, "3000"
        port = int(port_text)
        return (host.strip(), port) if host.strip() and 0 < port < 65536 else ("", 0)

    @Slot(bool, result=bool)
    def infoAuthNeedsConfirmation(self, new_value: bool) -> bool:
        state = self._security_state
        return state is not None and server_security.info_auth_needs_confirmation(state["info"]["value"], new_value)

    @Slot(str, bool, result=bool)
    def bleNeedsConfirmation(self, mode: str, require_encryption: bool) -> bool:
        return server_security.ble_needs_confirmation(mode, require_encryption)

    @Slot(str, result=bool)
    def mqttNeedsConfirmation(self, new_mode: str) -> bool:
        state = self._security_state
        current = state["mqtt"]["mode"]["value"] if state is not None and state.get("mqtt") else "off"
        return server_security.mqtt_needs_confirmation(current, new_mode)

    @Slot(str, str, str, str, str)
    def saveMqttOptions(self, mode: str, url: str, prefix: str, username: str, command_user: str) -> None:
        patch = server_security.mqtt_patch(mode, url, prefix, username, command_user)
        if patch is None:
            self._security_message = ""
            self._security_warning = ""
            self._security_error = _("SECURITY_MQTT_INVALID")
            self.changed.emit()
            return
        asyncio.ensure_future(self._save_security(patch))

    @Slot(bool, str, result=bool)
    def voiceNeedsConfirmation(self, include_heard_text: bool, min_confidence: str) -> bool:
        state = self._security_state
        patch = server_security.voice_patch(include_heard_text, min_confidence)
        if state is None or not state.get("voice") or patch is None:
            return False
        return server_security.voice_needs_confirmation(state["voice"]["heard"]["value"], state["voice"]["confidence"]["value"], patch)

    @Slot(bool, str)
    def saveVoiceOptions(self, include_heard_text: bool, min_confidence: str) -> None:
        patch = server_security.voice_patch(include_heard_text, min_confidence)
        if patch is None:
            self._security_message = ""
            self._security_warning = ""
            self._security_error = _("SECURITY_VOICE_INVALID")
            self.changed.emit()
            return
        asyncio.ensure_future(self._save_security(patch))

    @Slot(bool, result=bool)
    def robotsNeedsConfirmation(self, allow_enable: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("robots"):
            return False
        return server_security.robots_needs_confirmation(state["robots"]["allowEnable"]["value"], allow_enable)

    @Slot(bool)
    def saveRobotsOptions(self, allow_enable: bool) -> None:
        asyncio.ensure_future(self._save_security(server_security.robots_patch(allow_enable)))

    @Slot(bool, result=bool)
    def authNeedsConfirmation(self, accept_hs256: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("auth"):
            return False
        return server_security.auth_needs_confirmation(state["auth"]["acceptHs256"]["value"], accept_hs256)

    @Slot(str, bool)
    def saveAuthOptions(self, algorithm: str, accept_hs256: bool) -> None:
        """Sends only what differs from what the server reports (an option fixed by the environment is never sent)."""
        state = self._security_state
        if state is None or not state.get("auth"):
            return
        auth = state["auth"]
        wanted_algorithm = algorithm if algorithm != auth["jwtAlgorithm"]["value"] and auth["jwtAlgorithm"]["source"] != "env" else None
        wanted_accept = accept_hs256 if accept_hs256 != auth["acceptHs256"]["value"] and auth["acceptHs256"]["source"] != "env" else None
        patch = server_security.auth_patch(wanted_algorithm, wanted_accept)
        if patch is None or not patch["auth"]:
            return
        asyncio.ensure_future(self._save_security(patch))

    @Slot()
    def rotateAuthKey(self) -> None:
        asyncio.ensure_future(self._rotate_auth_key())

    async def _rotate_auth_key(self) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._security_message = ""
        self._security_error = ""
        self._security_warning = ""
        result = await conn.rotate_admin_jwt_key()
        if result is not None and result[0] == 200:
            self._security_message = _("SECURITY_AUTH_ROTATED")
        else:
            self._security_error = _("SECURITY_AUTH_ROTATE_ERROR")
        self.changed.emit()

    @Slot(bool, result=bool)
    def healthNeedsConfirmation(self, open_: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("health"):
            return False
        return server_security.health_needs_confirmation(state["health"]["open"]["value"], open_)

    @Slot(bool)
    def saveHealthOptions(self, open_: bool) -> None:
        asyncio.ensure_future(self._save_security(server_security.health_patch(open_)))

    @Slot("QVariantMap", str, result=bool)
    def ingestNeedsConfirmation(self, wanted: dict, keys_file: str) -> bool:
        state = self._security_state
        if state is None or not state.get("ingest"):
            return False
        return server_security.ingest_needs_confirmation(state, wanted, keys_file)

    @Slot("QVariantMap", str, result=bool)
    def ingestKeysFileAcceptable(self, wanted: dict, keys_file: str) -> bool:
        return server_security.valid_keys_file_name(keys_file)

    @Slot("QVariantMap", str)
    def saveIngestOptions(self, wanted: dict, keys_file: str) -> None:
        state = self._security_state
        if state is None or not state.get("ingest"):
            return
        patch = server_security.ingest_patch(state, wanted, keys_file)
        if patch is not None:
            asyncio.ensure_future(self._save_security(patch))

    # -- Status of the developer node (read only; the route answers 404 while the switch is off) ----------------

    async def _refresh_developer_nodes(self, conn, verify: bool) -> None:
        try:
            result = await conn.fetch_developer_node_status(verify)
        except Exception as error:  # a damaged answer must not stop the Server Admin screen
            logger.warning("reading the status of the developer node failed: %s", error)
            result = None
        self._developer_nodes_problem = developer_node_status.status_for(result)
        self._developer_nodes = developer_node_status.parse_status(result[1]) if result is not None and not self._developer_nodes_problem else None

    @Property("QVariantMap", notify=adminSwitchesChanged)
    def developerNodesView(self) -> dict:
        return developer_node_status.view(self._developer_nodes, self._developer_nodes_problem)

    @Slot(bool)
    def refreshDeveloperNodes(self, verify: bool) -> None:
        asyncio.ensure_future(self._reload_developer_nodes(verify))

    async def _reload_developer_nodes(self, verify: bool) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        await self._refresh_developer_nodes(conn, verify)
        self.changed.emit()

    @Slot(bool, result=bool)
    def productionNeedsConfirmation(self, on: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("production"):
            return False
        return server_security.production_needs_confirmation(state["production"]["rdpLevel"]["value"] == 1, on)

    @Slot(bool)
    def saveProductionOptions(self, on: bool) -> None:
        asyncio.ensure_future(self._save_security(server_security.production_patch(on)))

    @Slot(bool, result=bool)
    def connectionsNeedsConfirmation(self, record_address: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("connections"):
            return False
        return server_security.connections_needs_confirmation(state["connections"]["recordAddress"]["value"], record_address)

    @Slot(bool)
    def saveConnectionsOptions(self, record_address: bool) -> None:
        asyncio.ensure_future(self._save_security(server_security.connections_patch(record_address)))

    @Slot(str, result=bool)
    def bridgesNeedsConfirmation(self, values_json: str) -> bool:
        state = self._security_state
        if state is None or not state.get("bridges"):
            return False
        patch = server_security.bridges_patch(state, self._bridge_values(values_json))
        return patch is not None and server_security.bridges_needs_confirmation(state, patch)

    @Slot(str)
    def saveBridgesOptions(self, values_json: str) -> None:
        """Sends only the switches of the machine bridges that differ from what the server reports."""
        state = self._security_state
        if state is None or not state.get("bridges"):
            return
        patch = server_security.bridges_patch(state, self._bridge_values(values_json))
        if patch is not None:
            asyncio.ensure_future(self._save_security(patch))

    @Slot(bool, result=bool)
    def rateLimitsNeedsConfirmation(self, enabled: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("rateLimits"):
            return False
        return server_security.rate_limits_need_confirmation(state, enabled)

    @Slot(str, result=bool)
    def rateLimitsValid(self, values_json: str) -> bool:
        state = self._security_state
        if state is None or not state.get("rateLimits"):
            return False
        return server_security.rate_limit_texts_valid(state, self._bridge_values(values_json))

    @Slot(bool, str)
    def saveRateLimitsOptions(self, enabled: bool, values_json: str) -> None:
        """Sends only the limiter numbers that changed; a number that is not a whole number inside its range sends nothing."""
        state = self._security_state
        if state is None or not state.get("rateLimits"):
            return
        patch = server_security.rate_limits_patch(state, enabled, self._bridge_values(values_json))
        if patch is None:
            if not server_security.rate_limit_texts_valid(state, self._bridge_values(values_json)):
                self._security_message = ""
                self._security_warning = ""
                self._security_error = _("SECURITY_RL_INVALID")
                self.changed.emit()
            return
        asyncio.ensure_future(self._save_security(patch))

    @staticmethod
    def _bridge_values(values_json: str) -> object:
        try:
            return json.loads(values_json)
        except ValueError:
            return None

    @Slot(bool)
    def saveTrustedNetworksOptions(self, enabled: bool) -> None:
        state = self._security_state
        if state is None or not state.get("trustedNetworks"):
            return
        asyncio.ensure_future(self._save_security(server_security.trusted_networks_patch(enabled)))

    @Slot(bool)
    def saveTwinRelayOptions(self, enabled: bool) -> None:
        state = self._security_state
        if state is None or not state.get("twinRelay"):
            return
        asyncio.ensure_future(self._save_security(server_security.twin_relay_patch(enabled)))

    @Slot(bool)
    def saveEcosystemHealthOptions(self, enabled: bool) -> None:
        state = self._security_state
        if state is None or not state.get("ecosystemHealth"):
            return
        asyncio.ensure_future(self._save_security(server_security.ecosystem_health_patch(enabled)))

    @Slot(bool)
    def saveRulOptions(self, enabled: bool) -> None:
        state = self._security_state
        if state is None or not state.get("rul"):
            return
        asyncio.ensure_future(self._save_security(server_security.rul_patch(enabled)))

    def _exposure_values(self, camera_open: bool, ws_query_token: bool, log_redaction: bool, voice_signature: bool) -> tuple[dict, dict] | None:
        state = self._security_state
        if state is None or not state.get("exposure"):
            return None
        current = {name: option["value"] for name, option in state["exposure"].items()}
        new = {"cameraOpen": camera_open, "wsQueryToken": ws_query_token, "logRedaction": log_redaction, "voiceSignature": voice_signature}
        return current, new

    @Slot(bool, bool, bool, bool, result=bool)
    def exposureNeedsConfirmation(self, camera_open: bool, ws_query_token: bool, log_redaction: bool, voice_signature: bool) -> bool:
        values = self._exposure_values(camera_open, ws_query_token, log_redaction, voice_signature)
        return values is not None and server_security.exposure_needs_confirmation(*values)

    @Slot(bool, bool, bool, bool)
    def saveExposureOptions(self, camera_open: bool, ws_query_token: bool, log_redaction: bool, voice_signature: bool) -> None:
        values = self._exposure_values(camera_open, ws_query_token, log_redaction, voice_signature)
        patch = server_security.exposure_patch(*values) if values is not None else None
        if patch is not None:
            asyncio.ensure_future(self._save_security(patch))

    def _install_values(self, camera_via_env: bool, new_install_tls: bool) -> tuple[dict, dict] | None:
        state = self._security_state
        if state is None or not state.get("install"):
            return None
        current = {name: option["value"] for name, option in state["install"].items()}
        new = {"cameraCredentialsViaEnv": camera_via_env, "newInstallTls": new_install_tls}
        return current, new

    @Slot(bool, bool, result=bool)
    def installNeedsConfirmation(self, camera_via_env: bool, new_install_tls: bool) -> bool:
        values = self._install_values(camera_via_env, new_install_tls)
        return values is not None and server_security.install_needs_confirmation(*values)

    @Slot(bool, bool)
    def saveInstallOptions(self, camera_via_env: bool, new_install_tls: bool) -> None:
        values = self._install_values(camera_via_env, new_install_tls)
        patch = server_security.install_patch(*values) if values is not None else None
        if patch is not None:
            asyncio.ensure_future(self._save_security(patch))

    @staticmethod
    def _executor_switches(current: dict, exec_enabled: bool, exec_live: bool) -> dict:
        """The executor switches to send: none for a server without them, and only those that the environment does not lock."""
        executor = current.get("executor")
        if not executor:
            return {}
        return {
            "executor_enabled": None if server_security.is_locked(executor["enabled"]["source"]) else bool(exec_enabled),
            "executor_live": None if server_security.is_locked(executor["live"]["source"]) else bool(exec_live),
        }

    @Slot(bool, str, bool, str, bool, bool, result=bool)
    def jobDispatcherNeedsConfirmation(self, relay_enabled: bool, map_text: str, allow_unconfirmed: bool, timeout_text: str, exec_enabled: bool = False, exec_live: bool = False) -> bool:
        state = self._security_state
        if state is None or not state.get("jobDispatcher"):
            return False
        current = state["jobDispatcher"]
        patch = server_security.job_dispatcher_patch(relay_enabled, map_text, current["editable"], allow_unconfirmed, timeout_text, **self._executor_switches(current, exec_enabled, exec_live))
        return patch is not None and server_security.job_dispatcher_needs_confirmation(current, patch)

    @Slot(bool, str, bool, str, bool, bool, result=bool)
    def jobExecutorGoesLive(self, relay_enabled: bool, map_text: str, allow_unconfirmed: bool, timeout_text: str, exec_enabled: bool = False, exec_live: bool = False) -> bool:
        state = self._security_state
        if state is None or not state.get("jobDispatcher"):
            return False
        current = state["jobDispatcher"]
        patch = server_security.job_dispatcher_patch(relay_enabled, map_text, current["editable"], allow_unconfirmed, timeout_text, **self._executor_switches(current, exec_enabled, exec_live))
        return patch is not None and server_security.job_executor_goes_live(current, patch)

    @Slot(bool, str, bool, str, bool, bool)
    def saveJobDispatcherOptions(self, relay_enabled: bool, map_text: str, allow_unconfirmed: bool, timeout_text: str, exec_enabled: bool = False, exec_live: bool = False) -> None:
        state = self._security_state
        if state is None or not state.get("jobDispatcher"):
            return
        patch = server_security.job_dispatcher_patch(relay_enabled, map_text, state["jobDispatcher"]["editable"], allow_unconfirmed, timeout_text, **self._executor_switches(state["jobDispatcher"], exec_enabled, exec_live))
        if patch is None:
            self._security_message = ""
            self._security_warning = ""
            self._security_error = _("MSG_SECURITY_JD_MAP_INVALID") if server_security.parse_robot_map_text(map_text) is None else _("MSG_SECURITY_JD_TIMEOUT_INVALID")
            self.changed.emit()
            return
        asyncio.ensure_future(self._save_security(patch))

    @Slot(bool, bool, str, result=bool)
    def safetyNeedsConfirmation(self, fram_erase: bool, estop_watch_text: str) -> bool:
        body = self._safety_body(True, fram_erase, estop_watch_text)
        state = self._security_state
        if body is None or state is None or not state.get("safety") or "framErase" not in state["safety"]:
            return False
        new = body["safety"].get("framErase")
        return new is not None and server_security.fram_erase_needs_confirmation(state["safety"]["framErase"]["value"], new)

    def _safety_body(self, publish_global_stop: bool, fram_erase: bool, estop_watch_text: str) -> dict | None:
        """The request for the safety block: only what the server reports and does not have fixed by its environment goes, and the F-RAM erase and the watch
        only when they changed. None when nothing is left to send."""
        state = self._security_state
        safety = state.get("safety") if state else None
        if not safety:
            return None
        publish = None if server_security.is_locked(safety["publishGlobalStop"]["source"]) else publish_global_stop
        fram = None
        if "framErase" in safety and not server_security.is_locked(safety["framErase"]["source"]) and bool(fram_erase) != safety["framErase"]["value"]:
            fram = bool(fram_erase)
        watch = None
        if "estopWatchMs" in safety and not server_security.is_locked(safety["estopWatchMs"]["source"]):
            parsed = server_security.parse_estop_watch_text(estop_watch_text)
            if parsed is not None and parsed != safety["estopWatchMs"]["value"]:
                watch = parsed
        if publish is None and fram is None and watch is None:
            return None
        return server_security.safety_patch(publish, fram, watch)

    @Slot(bool, bool, str)
    def saveSafetyOptions(self, publish_global_stop: bool, fram_erase: bool = False, estop_watch_text: str = "") -> None:
        body = self._safety_body(publish_global_stop, fram_erase, estop_watch_text)
        if body is not None:
            asyncio.ensure_future(self._save_security(body))

    @Slot(str, result=bool)
    def estopWatchTextValid(self, text: str) -> bool:
        return server_security.parse_estop_watch_text(text) is not None

    @Slot(str, bool, result=bool)
    def mavlinkNeedsConfirmation(self, signing_key_file: str, allow_unsigned: bool) -> bool:
        state = self._security_state
        if state is None or not state.get("mavlink"):
            return False
        current = state["mavlink"]
        return server_security.mavlink_needs_confirmation(
            current["key"]["value"] != "", current["unsigned"]["value"], server_security.mavlink_patch(signing_key_file, allow_unsigned)
        )

    @Slot(str, bool)
    def saveMavlinkOptions(self, signing_key_file: str, allow_unsigned: bool) -> None:
        asyncio.ensure_future(self._save_security(server_security.mavlink_patch(signing_key_file, allow_unsigned)))

    @Slot(str)
    def setAiAccess(self, value: str) -> None:
        if value in ("open", "admin"):
            asyncio.ensure_future(self._save_security({"aiAccess": value}))

    @Slot(bool)
    def setInfoAuth(self, value: bool) -> None:
        asyncio.ensure_future(self._save_security({"infoAuth": bool(value)}))

    @Slot(bool, str, str)
    def saveTlsOptions(self, enabled: bool, cert_path: str, key_path: str) -> None:
        patch = server_security.tls_patch(enabled, cert_path, key_path)
        if patch is None:
            self._security_message = ""
            self._security_warning = ""
            self._security_error = _("SECURITY_TLS_PATHS_REQUIRED")
            self.changed.emit()
            return
        asyncio.ensure_future(self._save_security(patch))

    @Slot(str, bool)
    def setBleOptions(self, mode: str, require_encryption: bool) -> None:
        patch = server_security.ble_patch(mode, require_encryption)
        if patch is not None:
            asyncio.ensure_future(self._save_security(patch))

    async def _save_security(self, patch: dict) -> None:
        conn = self._controller.active_connection
        if conn is None or not conn.is_admin:
            return
        self._security_message = ""
        self._security_error = ""
        self._security_warning = ""
        result = await conn.put_admin_server_config(patch)
        if result is None:
            self._security_error = _("MSG_ADMIN_LOAD_ERROR")
        else:
            status, body = result
            if status != 200 or not isinstance(body, dict):
                detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
                self._security_error = detail or _("MSG_ADMIN_LOAD_ERROR")
            else:
                state = server_security.parse_state(body)
                if state is not None:
                    self._security_state = state
                self._security_warning = server_security.known_warning(body.get("warnings"))
                self._security_message = _("SECURITY_SAVED")
                if self._dispatcher_reload_pending():
                    asyncio.ensure_future(self._follow_dispatcher_reload())
        self.changed.emit()

    def _dispatcher_reload_pending(self) -> bool:
        state = self._security_state
        return bool(state and state.get("jobDispatcher") and state["jobDispatcher"].get("reload") == "pending")

    async def _follow_dispatcher_reload(self) -> None:
        """While the dispatcher has not answered the request to read its file again, asks the server again every
        _RELOAD_POLL_S seconds (a few times at most); only the state of the chip changes, not what is being edited."""
        for _attempt in range(_RELOAD_POLL_TRIES):
            await asyncio.sleep(_RELOAD_POLL_S)
            conn = self._controller.active_connection
            if conn is None or not conn.is_admin:
                return
            result = await conn.fetch_admin_server_config()
            if result is None or result[0] != 200 or not isinstance(result[1], dict):
                continue
            state = server_security.parse_state(result[1])
            if state is not None:
                self._security_state = state
                self.changed.emit()
            if not self._dispatcher_reload_pending():
                return

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
            self.adminSwitchesChanged.emit()
            return
        if not (1 <= port <= 65535):
            self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_INVALID")
            self.adminSwitchesChanged.emit()
            return
        result = await conn.save_admin_server_port(port)
        if result is None or result[0] != 200:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.adminSwitchesChanged.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_SAVED")
        self.adminSwitchesChanged.emit()

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
            self.adminSwitchesChanged.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_RESTART_REQUESTED")
        self.adminSwitchesChanged.emit()

    # -- Ecosystem Services --------------------------------------------------

    @Property(str, notify=ecosystemChanged)
    def esStatusText(self) -> str:
        return self._es_status_text

    @Property(bool, notify=ecosystemChanged)
    def esRefreshing(self) -> bool:
        return self._es_refreshing

    @Property(str, notify=ecosystemChanged)
    def esFamilyFilter(self) -> str:
        return self._es_family_filter or ""

    @Property("QStringList", notify=ecosystemChanged)
    def esFamilies(self) -> list[str]:
        return sorted({p.get("family") for p in self._es_projects if p.get("family")})

    @Property(bool, notify=ecosystemChanged)
    def esShowStats(self) -> bool:
        return len(self._es_projects) > 0

    @Property("QVariantMap", notify=ecosystemChanged)
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

    @Property("QVariantList", notify=ecosystemChanged)
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
            self.ecosystemChanged.emit()
            return
        self._es_refreshing = True
        self.ecosystemChanged.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._es_refreshing = False
        if result is None:
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.ecosystemChanged.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.ecosystemChanged.emit()
            return
        if not body.get("available"):
            self._es_status_text = _("MSG_ES_UNAVAILABLE")
            self._es_projects = []
            self.ecosystemChanged.emit()
            return
        self._es_projects = body.get("projects") or []
        self._es_status_text = _("LBL_ES_SCANNED_AT", time=body.get("scannedAt") or "-")
        self.ecosystemChanged.emit()

    @Slot(str)
    def setEsFamilyFilter(self, family: str) -> None:
        self._es_family_filter = family or None
        self.ecosystemChanged.emit()

    @Slot(str)
    def setEsSearch(self, text: str) -> None:
        self._es_search = text
        self.ecosystemChanged.emit()

    @Slot(str, str)
    def runEsServiceAction(self, unit: str, action: str) -> None:
        asyncio.ensure_future(self._run_es_service_action(unit, action))

    async def _run_es_service_action(self, unit: str, action: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        self._es_actioning_unit = unit
        self._es_action_error = None
        self.ecosystemChanged.emit()
        try:
            result = await conn.control_service(unit, action)
        finally:
            self._es_actioning_unit = None
        if result is None:
            self._es_action_error = (unit, _("MSG_SERVICES_ACTION_ERROR"))
            self.ecosystemChanged.emit()
            return
        status, body = result
        if status != 200:
            message = body.get("error") if isinstance(body, dict) else None
            self._es_action_error = (unit, message or f"HTTP {status}")
            self.ecosystemChanged.emit()
            return
        await self._refresh_ecosystem_services()

    # -- Tier plan of the data lake (Ecosystem Telemetry, administrators) ----
    # The editor of HYDRA-UMC-DATALAKE's tier plan, through the server. The checks are those of panel_logic/downsample_plan.py
    # (the same as the data lake's, strict, no way to relax them). Saving first asks the data lake what it would do (a preview),
    # shows the effects and asks for a confirmation; the control that turns real deletion on is disabled unless the operator started
    # the data lake with that option. The rows are read by cell (planCell) so that typing does not rebuild the fields.

    planStructureChanged = Signal()

    @Property(bool, notify=ecosystemChanged)
    def planVisible(self) -> bool:
        conn = self._controller.active_connection
        return conn is not None and conn.role == "admin"

    @Property("QVariantList", notify=planStructureChanged)
    def planStructure(self) -> list[int]:
        return list(range(len(self._plan_rows)))

    @Property(bool, notify=ecosystemChanged)
    def planLoaded(self) -> bool:
        return self._plan_state is not None

    @Property(str, notify=ecosystemChanged)
    def planFailureText(self) -> str:
        return self._plan_failure

    @Property(str, notify=ecosystemChanged)
    def planNoticeText(self) -> str:
        return self._plan_notice

    @Property(str, notify=ecosystemChanged)
    def planEffectsText(self) -> str:
        return self._plan_effects_text

    @Property(bool, notify=ecosystemChanged)
    def planBusy(self) -> bool:
        return self._plan_busy

    @Property(bool, notify=ecosystemChanged)
    def planConfirming(self) -> bool:
        return self._plan_confirming

    @Property(str, notify=ecosystemChanged)
    def planConfirmText(self) -> str:
        return _("PLAN_CONFIRM_DELETE_MESSAGE") if self._plan_turning_delete_on() else _("PLAN_CONFIRM_MESSAGE")

    @Property(bool, notify=ecosystemChanged)
    def planDeleteOn(self) -> bool:
        return self._plan_delete

    @Property(bool, notify=ecosystemChanged)
    def planAllowDelete(self) -> bool:
        return bool(self._plan_state and self._plan_state["allowDelete"])

    @Property(bool, notify=ecosystemChanged)
    def planFineEnabled(self) -> bool:
        return not self._plan_state or self._plan_state["fineRollups"]

    @Property(str, notify=ecosystemChanged)
    def planModeText(self) -> str:
        if not self._plan_state:
            return ""
        return _("PLAN_MODE_DELETE") if self._plan_state["mode"] == "delete" else _("PLAN_MODE_DRYRUN")

    @Property(str, notify=ecosystemChanged)
    def planKnownKindsText(self) -> str:
        kinds = self._plan_state["knownKinds"] if self._plan_state else []
        return _("PLAN_KNOWN_KINDS", kinds=", ".join(kinds)) if kinds else ""

    @Property("QStringList", notify=ecosystemChanged)
    def planIssueLines(self) -> list[str]:
        return [self._plan_issue_line(i) for i in self._plan_issues()]

    @Property(str, notify=ecosystemChanged)
    def planIssueSummary(self) -> str:
        count = len(self._plan_issues())
        return _("PLAN_INVALID_COUNT", count=count) if count else _("PLAN_VALID")

    @Property(bool, notify=ecosystemChanged)
    def planValid(self) -> bool:
        return self._plan_state is not None and not self._plan_issues()

    @Property(bool, notify=ecosystemChanged)
    def planCanSave(self) -> bool:
        return self.planValid and self._plan_changed() and not self._plan_busy

    @Property("QStringList", notify=ecosystemChanged)
    def planAuditLines(self) -> list[str]:
        if not self._plan_state:
            return []
        lines = [
            QDateTime.fromMSecsSinceEpoch(int(a["atMs"])).toString("yyyy-MM-dd HH:mm:ss")
            + " - "
            + _("PLAN_AUDIT_ENTRY", event=a["event"], client=a["client"], tiers=a["tiers"])
            for a in self._plan_state["audit"]
        ]
        return lines or [_("PLAN_AUDIT_NONE")]

    @Slot(int, str, result=str)
    def planCell(self, row: int, key: str) -> str:
        if 0 <= row < len(self._plan_rows):
            return str(self._plan_rows[row].get(key, ""))
        return ""

    @Slot(int, str, result=bool)
    def planCellBad(self, row: int, key: str) -> bool:
        return any(i["tier"] == row and i["key"] == key for i in self._plan_issues())

    def _plan_issues(self) -> list[dict]:
        if self._plan_state is None:
            return []
        return validate_downsample_plan(self._plan_rows, self._plan_state["knownKinds"])

    def _plan_issue_line(self, issue: dict) -> str:
        text = _("PLAN_ISSUE_" + issue["code"].upper(), **issue["params"])
        if issue["tier"] is None:
            return text
        return _("PLAN_ROW", row=issue["tier"] + 1) + ": " + text

    def _plan_changed(self) -> bool:
        state = self._plan_state
        return bool(state) and (self._plan_rows != state["rows"] or self._plan_delete != state["delete"])

    def _plan_turning_delete_on(self) -> bool:
        return bool(self._plan_state) and self._plan_delete and not self._plan_state["delete"]

    def _plan_failure_text(self, kind: str, status: int | None = None, details: list[str] | None = None) -> str:
        if kind == "http":
            text = _("PLAN_HTTP", status=status or 0)
        else:
            known = {
                "off": "PLAN_OFF", "forbidden": "PLAN_FORBIDDEN", "unreachable": "PLAN_UNREACHABLE",
                "network": "PLAN_NETWORK", "malformed": "PLAN_MALFORMED",
            }
            text = _(known.get(kind, "PLAN_ERROR_" + kind.upper()))
        return text + ("\n" + "\n".join(details) if details else "")

    def _plan_touch(self) -> None:
        self._plan_notice = ""
        self._plan_effects_text = ""
        self.ecosystemChanged.emit()

    @Slot()
    def loadDownsamplePlan(self) -> None:
        asyncio.ensure_future(self._load_downsample_plan())

    async def _load_downsample_plan(self) -> None:
        conn = self._controller.active_connection
        if conn is None or conn.role != "admin":
            return
        self._plan_busy = True
        self.ecosystemChanged.emit()
        try:
            result = await conn.fetch_downsample_plan()
        finally:
            self._plan_busy = False
        self._plan_effects_text = ""
        if result is None:
            self._plan_state, self._plan_failure = None, self._plan_failure_text("network")
        else:
            status, body = result
            state = read_downsample_plan(body) if status == 200 else None
            if state is not None:
                self._plan_state, self._plan_failure = state, ""
                self._plan_rows = [dict(r) for r in state["rows"]]
                self._plan_delete = state["delete"]
            else:
                self._plan_state = None
                kind = downsample_failure(status, body) if status != 200 else "malformed"
                self._plan_failure = self._plan_failure_text(kind, status, downsample_failure_details(body))
        self.planStructureChanged.emit()
        self.ecosystemChanged.emit()

    @Slot(int, str, str)
    def setPlanCell(self, row: int, key: str, value: str) -> None:
        if 0 <= row < len(self._plan_rows) and key in DOWNSAMPLE_CELLS:
            self._plan_rows[row][key] = value
            self._plan_touch()

    @Slot()
    def addPlanTier(self) -> None:
        if self._plan_state is not None:
            self._plan_rows.append(empty_downsample_tier())
            self.planStructureChanged.emit()
            self._plan_touch()

    @Slot(int)
    def removePlanTier(self, row: int) -> None:
        if 0 <= row < len(self._plan_rows):
            del self._plan_rows[row]
            self.planStructureChanged.emit()
            self._plan_touch()

    @Slot(bool)
    def setPlanDelete(self, on: bool) -> None:
        if self._plan_state and self._plan_state["allowDelete"]:
            self._plan_delete = on
            self._plan_touch()

    @Slot()
    def previewDownsamplePlan(self) -> None:
        asyncio.ensure_future(self._put_downsample_plan(preview=True, then_confirm=False))

    @Slot()
    def requestSaveDownsamplePlan(self) -> None:
        asyncio.ensure_future(self._put_downsample_plan(preview=True, then_confirm=True))

    @Slot()
    def cancelSaveDownsamplePlan(self) -> None:
        self._plan_confirming = False
        self.ecosystemChanged.emit()

    @Slot()
    def confirmSaveDownsamplePlan(self) -> None:
        self._plan_confirming = False
        asyncio.ensure_future(self._put_downsample_plan(preview=False, then_confirm=False))

    async def _put_downsample_plan(self, *, preview: bool, then_confirm: bool) -> None:
        conn = self._controller.active_connection
        state = self._plan_state
        if conn is None or state is None or self._plan_issues():
            return
        self._plan_busy = True
        self._plan_notice = ""
        self.ecosystemChanged.emit()
        body = {
            "plan": draft_to_downsample_plan(self._plan_rows, self._plan_delete),
            "expectedHash": state["hash"],
            "confirmDelete": self._plan_turning_delete_on(),
        }
        try:
            result = await conn.put_downsample_plan(body, preview=preview)
        finally:
            self._plan_busy = False
        if result is None:
            self._plan_failure = self._plan_failure_text("network")
            self.ecosystemChanged.emit()
            return
        status, answer = result
        effects = read_downsample_effects(answer) if status == 200 else None
        if effects is None:
            kind = downsample_failure(status, answer) if status != 200 else "malformed"
            self._plan_failure = self._plan_failure_text(kind, status, downsample_failure_details(answer))
            self._plan_effects_text = ""
            self.ecosystemChanged.emit()
            return
        self._plan_failure = ""
        if preview:
            lines = [_("PLAN_PREVIEWED"), _("PLAN_CHANGES", count=effects["changes"])]
            if effects["hasTotals"]:
                lines.append(_("PLAN_EFFECTS", raw=effects["raw"], rollups=effects["rollups"], fine=effects["fine"]))
            self._plan_effects_text = "\n".join(lines)
            self._plan_confirming = then_confirm
            self.ecosystemChanged.emit()
            return
        await self._load_downsample_plan()
        self._plan_notice = _("PLAN_SAVED") if effects["saved"] else _("PLAN_UNCHANGED")
        self.ecosystemChanged.emit()

    # -- Ecosystem Telemetry -------------------------------------------------

    @Property(str, notify=ecosystemChanged)
    def telemetryStatusText(self) -> str:
        return self._tel_status_text

    @Property(bool, notify=ecosystemChanged)
    def telemetryRunning(self) -> bool:
        return self._tel_running

    @Property("QStringList", constant=True)
    def telemetryAggregates(self) -> list[str]:
        return list(_AGGREGATES)

    @Property("QVariantList", constant=True)
    def telemetryRangePresets(self) -> list[dict[str, object]]:
        return [{"label": label, "ms": ms} for label, ms in _RANGE_PRESETS]

    @Property(bool, notify=ecosystemChanged)
    def telemetryShowStats(self) -> bool:
        return bool(self._tel_stats)

    @Property("QVariantMap", notify=ecosystemChanged)
    def telemetryStats(self) -> dict[str, str]:
        return self._tel_stats

    @Property(str, notify=ecosystemChanged)
    def telemetryChartMode(self) -> str:
        return self._tel_chart_mode

    @Property("QVariantList", notify=ecosystemChanged)
    def telemetryLinePoints(self) -> list[dict[str, float]]:
        return self._tel_line_points

    @Property("QVariantList", notify=ecosystemChanged)
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
            self.ecosystemChanged.emit()
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
        self.ecosystemChanged.emit()
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
            self.ecosystemChanged.emit()

        if result is None:
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.ecosystemChanged.emit()
            return
        status, body = result
        if status == 503 and isinstance(body, dict) and body.get("available") is False:
            self._tel_status_text = _("MSG_TELEMETRY_NOT_CONFIGURED")
            self._render_empty_telemetry_chart()
            self._update_telemetry_stats([])
            self.ecosystemChanged.emit()
            return
        if status != 200 or not isinstance(body, list):
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.ecosystemChanged.emit()
            return

        self._tel_status_text = "" if body else _("MSG_TELEMETRY_NO_DATA")
        if is_aggregate:
            self._render_telemetry_bar_chart(body)
            self._update_telemetry_stats([float(b.get("value", 0)) for b in body])
        else:
            self._render_telemetry_line_chart(body)
            self._update_telemetry_stats([float(p.get("value", 0)) for p in body])
        self.ecosystemChanged.emit()

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
        self.xyTableChanged.emit()

    def _xy_selected_robot(self) -> RobotView | None:
        for r in self._xy_robots_cache:
            if r.id == self._xy_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=xyTableChanged)
    def xyRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._xy_robots_cache]

    @Property(str, notify=xyTableChanged)
    def xySelectedRobotId(self) -> str:
        return self._xy_selected_robot_id or ""

    @Slot(str)
    def selectXyRobot(self, robot_id: str) -> None:
        if robot_id != self._xy_selected_robot_id:
            self._xy_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property(bool, notify=xyTableChanged)
    def xyHasRobot(self) -> bool:
        return self._xy_selected_robot() is not None

    @Property(bool, notify=xyTableChanged)
    def xyHasTable(self) -> bool:
        robot = self._xy_selected_robot()
        return robot is not None and robot.has_xy_table

    @Property(bool, notify=xyTableChanged)
    def xyCanReset(self) -> bool:
        return self.xyHasRobot and self.xyHasTable

    @Property(bool, notify=xyTableChanged)
    def xyTableControlsEnabled(self) -> bool:
        """The jog and size controls need a stored table: right after the table is enabled there is only the flag,
        and Reset writes the default table that makes them work."""
        robot = self._xy_selected_robot()
        return robot is not None and robot.has_xy_table and robot.xy_table is not None

    @Property(int, notify=xyTableChanged)
    def xyWidth(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("width", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(int, notify=xyTableChanged)
    def xyLength(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("length", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(str, notify=xyTableChanged)
    def xyPosX(self) -> str:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        pos = table["pos"] if table else {"x": 0, "y": 0}
        return f"{float(pos.get('x', 0)):.2f}"

    @Property(str, notify=xyTableChanged)
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

    def _edit_robot(self, robot: RobotView, updates: dict, mutate: Callable[[RobotView], None]) -> None:
        """Changes the data of a robot the way the server takes it: as the commands of hydra_suite/robot_edits.py, carried out
        under the reservation and If-Match rules of every command, and only what no command covers through the settings
        tree. A server that predates the commands, or an edit none of them covers, uses the tree as before."""
        conn = self._controller.active_connection
        plan = robot_edits.plan_robot_edits(robot.raw, updates)
        if conn is None or not conn.has_edit_commands or not plan.commands:
            mutate(robot)
            self._controller.push_active_state()
            return
        for name, params in plan.commands:
            self._controller.send_robot_command(robot.id, name, params, mutate)
        if plan.rest:
            mutate(robot)
            self._controller.push_active_state()

    @Slot()
    def enableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        # Enabling the table also writes the layout it needs when the robot has none, so the size fields and the jog work at once.
        if robot.xy_table:
            self._edit_robot(robot, {"hasXYTable": True}, lambda r: r.set_has_xy_table(True))
        else:
            default_table = _default_xy_table()
            layout = {name: value for name, value in default_table.items() if name != "pos"}  # the position travels with the table command

            def _enable(r) -> None:
                r.set_has_xy_table(True)
                r.set_xy_table(copy.deepcopy(default_table))

            self._edit_robot(robot, {"hasXYTable": True, "xyTable": layout}, _enable)
        self.changed.emit()

    @Slot()
    def disableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        self._edit_robot(robot, {"hasXYTable": False}, lambda r: r.set_has_xy_table(False))
        self.changed.emit()

    @Slot()
    def resetXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        default_table = _default_xy_table()
        self._edit_robot(robot, {"xyTable": default_table}, lambda r: r.set_xy_table(copy.deepcopy(default_table)))
        self.changed.emit()

    @Slot(int)
    def setXyWidth(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return  # no layout yet: nothing to resize
        resized = copy.deepcopy(table)
        resized["tableSize"]["width"] = value
        self._edit_robot(robot, {"xyTable": resized}, lambda r: r.set_xy_table(copy.deepcopy(resized)))
        self.changed.emit()

    @Slot(int)
    def setXyLength(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return
        resized = copy.deepcopy(table)
        resized["tableSize"]["length"] = value
        self._edit_robot(robot, {"xyTable": resized}, lambda r: r.set_xy_table(copy.deepcopy(resized)))
        self.changed.emit()

    @Slot(str, int)
    def jogXyTable(self, axis: str, direction: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None or axis not in ("x", "y"):
            return
        table = robot.xy_table
        if not table:
            return  # no layout yet: nothing to jog
        new_value = table["pos"][axis] + direction * self._xy_jog_step_mm
        bound = table["tableSize"]["width" if axis == "x" else "length"]
        new_value = max(0.0, min(new_value, float(bound)))
        # One atomic "table" move to the position reached (the other axis stays where it is): the server checks the
        # whole move against the limits of the model and applies all of it or none of it, and a robot in Sim does not
        # receive it. The local table follows at once and is put back if the server refuses.
        params = access.table_params(
            new_value if axis == "x" else float(table["pos"].get("x", 0)),
            new_value if axis == "y" else float(table["pos"].get("y", 0)),
            "absolute",
        )
        if params is None:
            return

        def follow(r: RobotView, value: float = new_value, name: str = axis) -> None:
            current = r.xy_table
            if current:
                current["pos"][name] = value
                r.set_xy_table(current)

        self._controller.send_robot_command(robot.id, "table", params, follow)
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
        self.rackChanged.emit()

    def _rack_selected_robot(self) -> RobotView | None:
        for r in self._rack_robots_cache:
            if r.id == self._rack_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=rackChanged)
    def rackRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._rack_robots_cache]

    @Property(str, notify=rackChanged)
    def rackSelectedRobotId(self) -> str:
        return self._rack_selected_robot_id or ""

    @Slot(str)
    def selectRackRobot(self, robot_id: str) -> None:
        if robot_id != self._rack_selected_robot_id:
            self._rack_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property(bool, notify=rackChanged)
    def rackHasRobot(self) -> bool:
        return self._rack_selected_robot() is not None

    @Property(bool, notify=rackChanged)
    def rackEnabled(self) -> bool:
        robot = self._rack_selected_robot()
        return robot is not None and bool(robot.rack_system.get("enabled"))

    @Property("QStringList", constant=True)
    def rackTypeOptions(self) -> list[str]:
        return ["None", "Input", "Output"]

    @Property("QStringList", constant=True)
    def rackTypeLabels(self) -> list[str]:
        return [_("LBL_DISABLED"), _("LBL_INPUT_RACK"), _("LBL_OUTPUT_RACK")]

    @Property("QVariantList", notify=rackChanged)
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
                "width": rack_geometry(rack)["width"],
                "depth": rack_geometry(rack)["depth"],
                "color": rack_geometry(rack)["color"],
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
        # BOTH racks reset, regardless of which rack's own Reset button
        # was clicked: a deliberately preserved behaviour of the rack screen
        # of Studio, not a bug of this one.
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

    @Slot(str, str, float)
    def setRackDimension(self, rack_id, axis, value):
        robot = self._rack_selected_robot()
        if robot is None or rack_id not in ("rack1", "rack2") or axis not in ("width", "depth") or not valid_dimension(value):
            return
        config = robot.rack_system
        config[rack_id][axis] = int(value)
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, str)
    def setRackColor(self, rack_id, color):
        robot = self._rack_selected_robot()
        if robot is None or rack_id not in ("rack1", "rack2") or not valid_color(color):
            return
        config = robot.rack_system
        config[rack_id]["color"] = color
        robot.set_rack_system(config)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str)
    def previewRack(self, rack_id):
        if rack_id not in ("rack1", "rack2"):
            return
        self._rack_preview_id = rack_id
        self._vacuum_preview_model = None
        self.refreshVacuumPreview()

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
        self.pnpChanged.emit()

    def _pnp_selected_robot(self) -> RobotView | None:
        for r in self._pnp_robots_cache:
            if r.id == self._pnp_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=pnpChanged)
    def pnpRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._pnp_robots_cache]

    @Property(str, notify=pnpChanged)
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

    @Property(str, notify=pnpChanged)
    def pnpMachineType(self) -> str:
        return self._pnp_machine_type

    @Property(str, notify=pnpChanged)
    def pnpMachineLabel(self) -> str:
        return MACHINE_LABELS.get(self._pnp_machine_type, self._pnp_machine_type)

    @Slot(str)
    def selectPnpMachine(self, machine_type: str) -> None:
        if machine_type != self._pnp_machine_type and machine_type in MACHINE_TYPES:
            self._pnp_machine_type = machine_type
            self.changed.emit()

    @Property(bool, notify=pnpChanged)
    def pnpHasRobot(self) -> bool:
        return self._pnp_selected_robot() is not None

    @Property(bool, notify=pnpChanged)
    def pnpEnabled(self) -> bool:
        robot = self._pnp_selected_robot()
        return robot is not None and robot.module_enabled(self._pnp_machine_type)

    @Property(bool, notify=pnpChanged)
    def pnpCanReset(self) -> bool:
        return self.pnpHasRobot and self.pnpEnabled

    @Property("QVariantList", notify=pnpChanged)
    def pnpAxisData(self) -> list[dict[str, object]]:
        """One row per PNP_AXES entry, spec + current value fused - same
        real fixed hardware bounds as PNP_AXES of
        panel_logic/pick_and_place.py (never re-declared here)."""
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
        """Resets the pick-and-place data of the robot:
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
        self.kbsChanged.emit()

    def _kbs_stage(self) -> dict:
        """The stage of the controller with whatever the server left out (or sent as another type) read as the
        seed default, so a half-filled record never stops the panel from drawing. A copy: change it, then
        _kbs_patch() it."""
        return complete_stage(self._kbs_controller.kinematic_brain_stage) if self._kbs_controller is not None else {}

    def _kbs_patch(self, updates: dict) -> None:
        """The one real write path for every control in this panel."""
        if self._kbs_controller is None:
            return
        stage = self._kbs_stage()
        stage.update(updates)
        self._kbs_controller.set_kinematic_brain_stage(stage)
        self._controller.push_active_state()
        self.changed.emit()

    @Property(bool, notify=kbsChanged)
    def kbsHasController(self) -> bool:
        return self._kbs_controller is not None

    @Property("QVariantList", notify=kbsChanged)
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
        stage = self._kbs_stage()
        xy = stage["xyTable"]
        next_value = xy[axis] + direction * self._kbs_jog_step_mm
        bound = xy["tableSize"]["height"] if axis == "z" else xy["tableSize"]["width" if axis == "x" else "length"]
        xy[axis] = _clamp(next_value, 0, float(bound))
        self._kbs_patch({"xyTable": xy})

    @Property(int, notify=kbsChanged)
    def kbsTableWidth(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("width", 0))

    @Property(int, notify=kbsChanged)
    def kbsTableLength(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("length", 0))

    @Property(int, notify=kbsChanged)
    def kbsTableHeight(self) -> int:
        return int(self._kbs_stage().get("xyTable", {}).get("tableSize", {}).get("height", 0))

    @Slot(str, int)
    def setKbsTableSize(self, field: str, value: int) -> None:
        bounds = {"width": (100, 5000), "length": (100, 5000), "height": (10, 1000)}
        if self._kbs_controller is None or field not in bounds:
            return
        stage = self._kbs_stage()
        lo, hi = bounds[field]
        stage["xyTable"]["tableSize"][field] = _clamp(value, lo, hi)
        self._kbs_patch({"xyTable": stage["xyTable"]})

    @Property(str, notify=kbsChanged)
    def kbsTherm1(self) -> str:
        return f"{float(self._kbs_stage().get('heatedBed', {}).get('currentTemp1', 0)):.1f}°C"

    @Property(str, notify=kbsChanged)
    def kbsTherm2(self) -> str:
        return f"{float(self._kbs_stage().get('heatedBed', {}).get('currentTemp2', 0)):.1f}°C"

    @Property(int, notify=kbsChanged)
    def kbsTargetTemp(self) -> int:
        return int(self._kbs_stage().get("heatedBed", {}).get("targetTemp", 0))

    @Slot(int)
    def setKbsTargetTemp(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        bed = self._kbs_stage()["heatedBed"]
        bed["targetTemp"] = access.clamp_bed_target(value, self._bed_ceiling())
        self._kbs_patch({"heatedBed": bed})

    @Property(bool, notify=kbsChanged)
    def kbsSsrOn(self) -> bool:
        return bool(self._kbs_stage().get("heatedBed", {}).get("ssrActive"))

    @Slot()
    def toggleKbsSsr(self) -> None:
        if self._kbs_controller is None:
            return
        bed = self._kbs_stage()["heatedBed"]
        bed["ssrActive"] = not bed.get("ssrActive")
        self._kbs_patch({"heatedBed": bed})

    @Property(int, notify=kbsChanged)
    def kbsAtcIndex(self) -> int:
        return int(self._kbs_stage().get("atcRevolver", {}).get("currentIndex", 0)) + 1

    @Property(int, notify=kbsChanged)
    def kbsToolCount(self) -> int:
        return int(self._kbs_stage().get("atcRevolver", {}).get("toolCount", 6))

    @Property(bool, notify=kbsChanged)
    def kbsHomed(self) -> bool:
        return bool(self._kbs_stage().get("atcRevolver", {}).get("homed"))

    @Slot(int)
    def stepKbsAtc(self, direction: int) -> None:
        if self._kbs_controller is None:
            return
        atc = self._kbs_stage()["atcRevolver"]
        n = atc.get("toolCount")
        n = n if isinstance(n, int) and not isinstance(n, bool) and n >= 2 else 8
        target = atc.get("targetIndex")
        target = target if isinstance(target, int) and not isinstance(target, bool) else 0
        next_index = (target + direction) % n
        atc["targetIndex"] = next_index
        atc["currentIndex"] = next_index
        atc["homed"] = True
        self._kbs_patch({"atcRevolver": atc})

    @Slot(int)
    def setKbsToolCount(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        atc = self._kbs_stage()["atcRevolver"]
        atc["toolCount"] = _clamp(value, 2, 16)
        self._kbs_patch({"atcRevolver": atc})

    @Property(bool, notify=kbsChanged)
    def kbsConveyorInstalled(self) -> bool:
        return bool(self._kbs_stage().get("conveyor", {}).get("installed"))

    @Property(bool, notify=kbsChanged)
    def kbsConveyorRunning(self) -> bool:
        return bool(self._kbs_stage().get("conveyor", {}).get("running"))

    @Property(int, notify=kbsChanged)
    def kbsConveyorSpeed(self) -> int:
        return int(self._kbs_stage().get("conveyor", {}).get("speedPercent", 0))

    @Slot()
    def installKbsConveyor(self) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_stage()["conveyor"]
        conveyor["installed"] = True
        self._kbs_patch({"conveyor": conveyor})

    @Slot()
    def toggleKbsConveyorRun(self) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_stage()["conveyor"]
        conveyor["running"] = not conveyor.get("running")
        self._kbs_patch({"conveyor": conveyor})

    @Slot(int)
    def setKbsConveyorSpeed(self, value: int) -> None:
        if self._kbs_controller is None:
            return
        conveyor = self._kbs_stage()["conveyor"]
        conveyor["speedPercent"] = value
        self._kbs_patch({"conveyor": conveyor})

    @Property("QVariantList", notify=kbsChanged)
    def kbsEndstopData(self) -> list[dict[str, object]]:
        endstops = self._kbs_stage().get("endstops", {})
        return [{"key": key, "label": label, "active": bool(endstops.get(key))} for key, label in ENDSTOP_ENTRIES]

    def _kbs_toggle_group(self, group_key: str, index: int) -> None:
        if self._kbs_controller is None:
            return
        group = self._kbs_stage().get(group_key)
        if not isinstance(group, list) or not 0 <= index < len(group):
            return  # a shorter list than the buttons: nothing to toggle
        group[index] = not group[index]
        self._kbs_patch({group_key: group})

    @Property("QVariantList", notify=kbsChanged)
    def kbsFans(self) -> list[bool]:
        return list(self._kbs_stage().get("fans", []))

    @Property("QVariantList", notify=kbsChanged)
    def kbsPumps(self) -> list[bool]:
        return list(self._kbs_stage().get("pumps", []))

    @Property("QVariantList", notify=kbsChanged)
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
        self.moduleChanged.emit()

    def _active_module_key(self) -> str | None:
        return self._active_key if self._active_key in _MODULE_CONFIGS else None

    def _module_selected_robot(self, nav_key: str) -> RobotView | None:
        rid = self._module_selected_robot_id.get(nav_key)
        for r in self._module_robots_cache.get(nav_key, []):
            if r.id == rid:
                return r
        return None

    @Property("QVariantList", notify=moduleChanged)
    def moduleRobotOptions(self) -> list[dict[str, str]]:
        key = self._active_module_key()
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._module_robots_cache.get(key, [])] if key else []

    @Property(str, notify=moduleChanged)
    def moduleSelectedRobotId(self) -> str:
        key = self._active_module_key()
        return (self._module_selected_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectModuleRobot(self, robot_id: str) -> None:
        key = self._active_module_key()
        if key is not None and robot_id != self._module_selected_robot_id.get(key):
            self._module_selected_robot_id[key] = robot_id or None
            self.changed.emit()

    @Property(str, notify=moduleChanged)
    def moduleHeadingKey(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["heading"]) if key else ""

    @Property(str, notify=moduleChanged)
    def moduleMachineName(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["machine"]) if key else ""

    @Property(str, notify=moduleChanged)
    def moduleExtraKind(self) -> str:
        key = self._active_module_key()
        return str(_MODULE_CONFIGS[key]["extra"]) if key else ""

    @Property(bool, notify=moduleChanged)
    def moduleHasRobot(self) -> bool:
        key = self._active_module_key()
        return key is not None and self._module_selected_robot(key) is not None

    @Property(bool, notify=moduleChanged)
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
        if key == "vacuum_table":
            return int(vacuum_table_size(robot.module("vacuumTable"))[field])
        if key == "heated_bed":
            return int(heated_bed_size(robot.module("heatedBed"))[field])
        size = robot.module(_MODULE_CONFIGS[key]["module_key"]).get("size") or {}
        return int(size.get(field, DEFAULT_SIZE_MM))

    @Property(int, notify=moduleChanged)
    def moduleWidth(self) -> int:
        return self._module_size_field("width")

    @Property(int, notify=moduleChanged)
    def moduleLength(self) -> int:
        return self._module_size_field("length")

    def _module_extra_defaults(self, nav_key: str) -> dict:
        """The extra fields of the heated bed and the vacuum table, for a
        default and for a reset: both happen to be the same dict, so
        this one helper covers Enable's setdefault() and Reset's
        overwrite alike (see _MODULE_CONFIGS's own "extra" tag)."""
        extra = _MODULE_CONFIGS[nav_key]["extra"]
        if extra == "heated_bed":
            return {"modelId": "200x200x5", "targetTemp": _HB_DEFAULT_TARGET_TEMP_C, "currentTemp1": _HB_DEFAULT_AMBIENT_TEMP_C, "currentTemp2": _HB_DEFAULT_AMBIENT_TEMP_C, "ssrActive": False}
        if extra == "vacuum_table":
            return {"pumpActive": False, "valveActive": False, "modelId": VACUUM_TABLE_MODELS[0]["id"]}
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
        if key == "vacuum_table" and module.get("customSize") is not True:
            module = select_vacuum_table(module, vacuum_table_model(module.get("modelId"))["id"])
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
        if key == "vacuum_table":
            module = resize_vacuum_table(robot.module(module_key), field, value)
        elif key == "heated_bed":
            module = resize_heated_bed(robot.module(module_key), field, value)
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
    @Property(int, notify=moduleChanged)
    def moduleTargetTemp(self) -> int:
        return int(self._module_extra_value("targetTemp", _HB_DEFAULT_TARGET_TEMP_C))

    @Property(bool, notify=moduleChanged)
    def moduleSsrOn(self) -> bool:
        return bool(self._module_extra_value("ssrActive", False))

    @Property(str, notify=moduleChanged)
    def moduleTherm1(self) -> str:
        return f"{float(self._module_extra_value('currentTemp1', _HB_DEFAULT_AMBIENT_TEMP_C)):.1f} °C"

    @Property(str, notify=moduleChanged)
    def moduleTherm2(self) -> str:
        return f"{float(self._module_extra_value('currentTemp2', _HB_DEFAULT_AMBIENT_TEMP_C)):.1f} °C"

    @Slot(int)
    def setModuleTargetTemp(self, value: int) -> None:
        self._set_module_extra_field("targetTemp", access.clamp_bed_target(value, self.moduleBedCeiling))

    @Property(int, notify=moduleChanged)
    def moduleBedCeiling(self) -> int:
        """The hottest target the server allows for the model of the robot whose heated bed is open."""
        conn = self._controller.active_connection
        key = self._active_module_key()
        robot = self._module_selected_robot(key) if key else None
        if conn is None:
            return int(access.SafetyLimits().bed_default_c)
        return int(access.bed_max_for(conn.safety.limits, robot.model if robot is not None else None))

    @Property(int, notify=moduleChanged)
    def kbsBedCeiling(self) -> int:
        """The hottest target the server allows any model: the Kinematic Brain Stage has no single robot."""
        return int(self._bed_ceiling())

    @Slot()
    def toggleModuleSsr(self) -> None:
        self._set_module_extra_field("ssrActive", not self.moduleSsrOn)

    # Table model selection; the existing preview serves both STL catalogs.
    @Property("QVariantList", constant=True)
    def heatedModelOptions(self):
        return [{"id": m["id"], "label": m["label"]} for m in HEATED_BED_MODELS]

    @Property(str, notify=moduleChanged)
    def heatedModelId(self):
        return heated_bed_model(self._module_extra_value("modelId", None))["id"]

    @Slot(str)
    def selectHeatedModel(self, model_id):
        if self._active_module_key() != "heated_bed":
            return
        robot = self._module_selected_robot("heated_bed")
        if robot is None or not any(m["id"] == model_id for m in HEATED_BED_MODELS):
            return
        robot.set_module("heatedBed", select_heated_bed(robot.module("heatedBed"), model_id))
        self._controller.push_active_state()
        self.changed.emit()

    @Property("QVariantList", constant=True)
    def vacuumModelOptions(self):
        return [{"id": model["id"], "label": model["label"]} for model in VACUUM_TABLE_MODELS]

    @Property(str, notify=moduleChanged)
    def vacuumModelId(self):
        return vacuum_table_model(self._module_extra_value("modelId", None))["id"]

    @Slot(str)
    def selectVacuumModel(self, model_id):
        if self._active_module_key() != "vacuum_table":
            return
        robot = self._module_selected_robot("vacuum_table")
        if robot is None or not any(m["id"] == model_id for m in VACUUM_TABLE_MODELS):
            return
        robot.set_module("vacuumTable", select_vacuum_table(robot.module("vacuumTable"), model_id))
        self._controller.push_active_state()
        self.changed.emit()

    @Property(int, notify=_viewportChanged)
    def vacuumPreviewVersion(self):
        return self._vacuum_preview_version

    @Property(str, notify=_viewportChanged)
    def vacuumPreviewError(self):
        return self._vacuum_preview_error

    @Slot()
    def refreshVacuumPreview(self):
        if self.activePanel == "pick_and_place":
            robot = self._pnp_selected_robot()
            if robot is None or not self.pnpEnabled:
                return
            module = robot.module(self._pnp_machine_type)
            pose = tuple(float(module.get(k, 0) or 0) for k in ("axisX", "axisY", "axisZ", "nozzle1Rotation", "nozzle2Rotation"))
            preview_key = ("pnp", self._pnp_machine_type, pose)
            if self._vacuum_preview_model == preview_key and not self._vacuum_preview_error:
                return
            try:
                if self._vacuum_renderer is None:
                    from hydra_suite.render.viewport import OffscreenRobotRenderer
                    self._vacuum_renderer = OffscreenRobotRenderer()
                    self._vacuum_renderer.resize(640, 400)
                self._vacuum_renderer.set_attached_pnp(self._pnp_machine_type, *pose)
                self._vacuum_frame_provider.set_image(self._vacuum_renderer.render())
                self._vacuum_preview_error = ""
                self._vacuum_preview_model = preview_key
                self._vacuum_preview_version += 1
            except Exception:
                self._vacuum_preview_error = _("LBL_MACHINE_MESH_ERROR")
            self._viewportChanged.emit()
            return
        if self.activePanel == "rack":
            robot = self._rack_selected_robot()
            if robot is None or not self.rackEnabled:
                return
            rack = robot.rack_system[self._rack_preview_id]
            spec = rack_geometry(rack)
            preview_key = ("rack", robot.id, self._rack_preview_id, rack.get("type"),
                           tuple(spec.values()), tuple(rack.get("usableSlots", [])))
            if self._vacuum_preview_model == preview_key and not self._vacuum_preview_error:
                return
            try:
                if self._vacuum_renderer is None:
                    from hydra_suite.render.viewport import OffscreenRobotRenderer
                    self._vacuum_renderer = OffscreenRobotRenderer()
                    self._vacuum_renderer.resize(640, 400)
                self._vacuum_renderer.set_attached_module("rack", rack_config=rack)
                self._vacuum_frame_provider.set_image(self._vacuum_renderer.render())
                self._vacuum_preview_error = ""
                self._vacuum_preview_model = preview_key
                self._vacuum_preview_version += 1
            except Exception:
                self._vacuum_preview_error = _("LBL_RACK_MESH_ERROR")
            self._viewportChanged.emit()
            return
        key = self._active_module_key()
        if key not in ("vacuum_table", "heated_bed", "cnc", "laser") or not self.moduleEnabled:
            return
        machine_type = {"cnc": "juanenCNC", "laser": "juanenLaser"}.get(key)
        heated = key == "heated_bed"
        model = heated_bed_model(self.heatedModelId) if heated else vacuum_table_model(self.vacuumModelId)
        preview_key = (key, model["id"], self.moduleWidth, self.moduleLength)
        if self._vacuum_preview_model == preview_key and not self._vacuum_preview_error:
            return  # Unrelated telemetry must not redraw an unchanged static mesh.
        try:
            if self._vacuum_renderer is None:
                from hydra_suite.render.viewport import OffscreenRobotRenderer
                self._vacuum_renderer = OffscreenRobotRenderer()
                self._vacuum_renderer.resize(640, 400)
            self._vacuum_renderer.set_attached_module(machine_type or ("heatedBed" if heated else "vacuumTable"), self.moduleWidth, self.moduleLength, model["id"])
            self._vacuum_frame_provider.set_image(self._vacuum_renderer.render())
            self._vacuum_preview_error = ""
            self._vacuum_preview_model = preview_key
            self._vacuum_preview_version += 1
        except Exception:
            self._vacuum_preview_error = _("LBL_MACHINE_MESH_ERROR" if machine_type else ("LBL_HEATED_MODEL_ERROR" if heated else "LBL_VACUUM_MODEL_ERROR"))
        self._viewportChanged.emit()

    @Slot(float, float)
    def vacuumPreviewOrbit(self, dx, dy):
        if self._vacuum_renderer is not None:
            self._vacuum_renderer.orbit(dx, dy)
            self._vacuum_preview_model = None
            self.refreshVacuumPreview()

    @Slot(float)
    def vacuumPreviewZoom(self, factor):
        if self._vacuum_renderer is not None:
            self._vacuum_renderer.zoom(factor)
            self._vacuum_preview_model = None
            self.refreshVacuumPreview()

    # Vacuum Table's own extra fields.
    @Property(bool, notify=moduleChanged)
    def modulePumpOn(self) -> bool:
        return bool(self._module_extra_value("pumpActive", False))

    @Property(bool, notify=moduleChanged)
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
        self.atcChanged.emit()

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
            except (ValueError, AttributeError, TypeError):
                rows, cols = 2, 2
            return max(1, rows * cols)
        try:
            return max(1, int(config.get("revolverSlots", 8) or 8))
        except (ValueError, TypeError):
            return 8

    @Property("QVariantList", notify=atcChanged)
    def atcRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._atc_robots_cache]

    @Property(str, notify=atcChanged)
    def atcSelectedRobotId(self) -> str:
        return self._atc_selected_robot_id or ""

    @Slot(str)
    def selectAtcRobot(self, robot_id: str) -> None:
        if robot_id != self._atc_selected_robot_id:
            self._atc_selected_robot_id = robot_id or None
            self._atc_editing_slot = None
            self.changed.emit()

    @Property(bool, notify=atcChanged)
    def atcHasRobot(self) -> bool:
        return self._atc_selected_robot() is not None

    @Property(bool, notify=atcChanged)
    def atcConfigured(self) -> bool:
        robot = self._atc_selected_robot()
        return robot is not None and robot.atc is not None

    @Property(str, notify=atcChanged)
    def atcType(self) -> str:
        return str(self._atc_config().get("type", "vertical_panel"))

    @Property("QVariantList", constant=True)
    def atcTypeOptions(self) -> list[dict[str, str]]:
        labels = {"vertical_panel": "LBL_ATC_VERTICAL", "horizontal_panel": "LBL_ATC_HORIZONTAL", "revolver": "LBL_ATC_REVOLVER"}
        return [{"key": k, "labelKey": labels[k]} for k in _ATC_TYPE_KEYS]

    @Property(bool, notify=atcChanged)
    def atcIsPanel(self) -> bool:
        return self.atcType in ("vertical_panel", "horizontal_panel")

    @Property(str, notify=atcChanged)
    def atcPanelGrid(self) -> str:
        return str(self._atc_config().get("panelGrid", "2x2"))

    @Property("QVariantList", constant=True)
    def atcPanelGridOptions(self) -> list[str]:
        return list(PANEL_GRIDS)

    @Property(int, notify=atcChanged)
    def atcRevolverSlots(self) -> int:
        return int(self._atc_config().get("revolverSlots", 8) or 8)

    @Property("QVariantList", constant=True)
    def atcToolOptions(self) -> list[str]:
        return list(URTC_TOOLS)

    @Property(bool, notify=atcChanged)
    def atcHasXyTable(self) -> bool:
        robot = self._atc_selected_robot()
        return bool(robot is not None and robot.has_xy_table)

    @Property(str, notify=atcChanged)
    def atcEditingSlotKey(self) -> str:
        return "" if self._atc_editing_slot is None else str(self._atc_editing_slot)

    @Property("QVariantList", notify=atcChanged)
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

    @Property("QVariantList", notify=atcChanged)
    def atcBasePos(self) -> list[dict[str, object]]:
        config = self._atc_config()
        return self._atc_pos_fields(config.get("revolverPos") or _default_pos(), self.atcHasXyTable)

    @Property(bool, notify=atcChanged)
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

    @Property(str, notify=atcChanged)
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
        self.cameraCardsChanged.emit()

    def _camera_stream_url(self, camera_id: int) -> str | None:
        conn = self._controller.active_connection
        if conn is None:
            return None
        return f"{conn.info.base_url}/api/camera/{camera_id}/stream"

    def _ensure_camera_stream(self, camera_id: int) -> None:
        task = self._camera_stream_tasks.get(camera_id)
        url = self._camera_stream_url(camera_id)
        if task is not None and not task.done():
            if url == self._camera_stream_urls.get(camera_id):
                return  # already streaming - _on_cameras_state_changed runs on
                # every state broadcast, not just real changes, matching
                # CameraCard._start_stream()'s own real no-op guard.
            self._stop_camera_stream(camera_id)  # the active server changed: this picture is the previous one's
        self._camera_stream_urls[camera_id] = url
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
                conn = self._controller.active_connection
                async for frame in iter_mjpeg_frames(url, conn.auth_headers() if conn is not None else None):
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

    @Property("QVariantList", notify=cameraCardsChanged)
    def cameraRobotOptions(self) -> list[dict[str, str]]:
        state = self._controller.active_state
        active = state.active_controller if state else None
        robots = active.robots if active is not None else []
        options = [{"id": "", "label": _("OPT_NONE_FLOATING")}]
        options += [{"id": str(r.id), "label": f"{r.model} (A{r.id})"} for r in robots]
        return options

    @Property("QVariantList", notify=cameraCardsChanged)
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
        self.cameraCardsChanged.emit()
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
        self.cameraCardsChanged.emit()

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
        self.cameraCardsChanged.emit()

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
        self.cameraCardsChanged.emit()

    @Slot(int, str)
    def setCameraAssignedRobot(self, camera_id: int, robot_id: str) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        camera.set_assigned_robot_id(int(robot_id) if robot_id else None)
        self._controller.push_active_state()
        self.cameraCardsChanged.emit()

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
        self.cameraCardsChanged.emit()

    @Slot(int)
    def discoverUsbDevices(self, camera_id: int) -> None:
        task = self._camera_discovery_tasks.get(camera_id)
        if task is not None and not task.done():
            return
        conn = self._controller.active_connection
        if conn is None:
            self._camera_discovery_status[camera_id] = (_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            self.cameraCardsChanged.emit()
            return
        self._camera_usb_devices[camera_id] = []
        self._camera_discovery_status[camera_id] = (_("LBL_DISCOVERING"), "#8a97a6")
        self.cameraCardsChanged.emit()
        self._camera_discovery_tasks[camera_id] = asyncio.ensure_future(self._run_discover_usb(camera_id, conn))

    async def _run_discover_usb(self, camera_id: int, conn: HydraConnection) -> None:
        result = await conn.discover_usb_devices()
        if result is None:
            self._camera_discovery_status[camera_id] = (_("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            self.cameraCardsChanged.emit()
            return
        status, body = result
        devices = body.get("devices") if status == 200 and isinstance(body, dict) else None
        if status != 200 or not isinstance(devices, list):
            message = body.get("error") if isinstance(body, dict) else None
            self._camera_discovery_status[camera_id] = (str(message) if message else _("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            self.cameraCardsChanged.emit()
            return
        if not devices:
            self._camera_discovery_status[camera_id] = (_("MSG_NO_USB_DEVICES_FOUND"), "#f59e0b")
            self.cameraCardsChanged.emit()
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
        self.cameraCardsChanged.emit()

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
        self.cameraCardsChanged.emit()

    @Slot(int, str, int, str, str)
    def discoverRtspPath(self, camera_id: int, host: str, port: int, username: str, password: str) -> None:
        task = self._camera_discovery_tasks.get(camera_id)
        if task is not None and not task.done():
            return
        conn = self._controller.active_connection
        if conn is None:
            self._camera_discovery_status[camera_id] = (_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            self.cameraCardsChanged.emit()
            return
        if not host.strip():
            self._camera_discovery_status[camera_id] = (_("LBL_IP_HOST"), "#ef4444")
            self.cameraCardsChanged.emit()
            return
        self._camera_discovery_status[camera_id] = (_("LBL_DISCOVERING"), "#8a97a6")
        self.cameraCardsChanged.emit()
        self._camera_discovery_tasks[camera_id] = asyncio.ensure_future(
            self._run_discover_rtsp(camera_id, conn, host, port, username, password)
        )

    async def _run_discover_rtsp(self, camera_id: int, conn: HydraConnection, host: str, port: int, username: str, password: str) -> None:
        result = await conn.discover_rtsp_path(host, port, username, password)
        if result is None:
            self._camera_discovery_status[camera_id] = (_("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")
            self.cameraCardsChanged.emit()
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
            self.cameraCardsChanged.emit()
            return
        if status == 200 and isinstance(body, dict):
            tried = body.get("triedPaths")
            suffix = f" ({', '.join(str(t) for t in tried)})" if isinstance(tried, list) and tried else ""
            self._camera_discovery_status[camera_id] = (_("MSG_RTSP_PATH_NOT_FOUND") + suffix, "#f59e0b")
            self.cameraCardsChanged.emit()
            return
        message = body.get("error") if isinstance(body, dict) else None
        self._camera_discovery_status[camera_id] = (str(message) if message else _("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")
        self.cameraCardsChanged.emit()

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
            self.cameraCardsChanged.emit()
            return
        status, body = result
        if status == 200 and isinstance(body, dict) and body.get("ok") is True:
            self._camera_ptz_error.pop(camera_id, None)
            self.cameraCardsChanged.emit()
            return
        error = body.get("error") if isinstance(body, dict) else None
        self._camera_ptz_error[camera_id] = str(error) if error else _("MSG_PTZ_FAILED")
        self.cameraCardsChanged.emit()

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

    # --- real snapshot/recording capture ---

    @Property("QVariantList", notify=_camerasChanged)
    def cameraRecordingIds(self) -> list[int]:
        return sorted(self._camera_recording_ids)

    @Property(str, notify=_camerasChanged)
    def cameraCaptureError(self) -> str:
        return self._camera_capture_error

    @Slot(int)
    def takeCameraSnapshot(self, camera_id: int) -> None:
        asyncio.ensure_future(self._run_take_snapshot(camera_id))

    async def _run_take_snapshot(self, camera_id: int) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.take_camera_snapshot(camera_id)
        if result is None or result[0] != 200:
            self._camera_capture_error = _("MSG_CAMERA_SNAPSHOT_FAILED")
        else:
            self._camera_capture_error = ""
        self._camerasChanged.emit()

    @Slot(int)
    def toggleCameraRecording(self, camera_id: int) -> None:
        asyncio.ensure_future(self._run_toggle_recording(camera_id))

    async def _run_toggle_recording(self, camera_id: int) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        is_recording = camera_id in self._camera_recording_ids
        result = await (conn.stop_camera_recording(camera_id) if is_recording else conn.start_camera_recording(camera_id))
        if result is None or result[0] != 200:
            self._camera_capture_error = _("MSG_CAMERA_RECORDING_FAILED")
        else:
            self._camera_capture_error = ""
            if is_recording:
                self._camera_recording_ids.discard(camera_id)
            else:
                self._camera_recording_ids.add(camera_id)
        self._camerasChanged.emit()

    # --- real Camera Media panel: browse/play back/delete saved
    # snapshots/recordings. ---

    @Property("QVariantList", notify=_cameraMediaChanged)
    def cameraMediaItems(self) -> list[dict[str, object]]:
        result = []
        for item in self._camera_media_items:
            if self._camera_media_filter != "all" and item.get("cameraId") != self._camera_media_filter:
                continue
            selected = self._camera_media_selected
            result.append({
                "cameraId": item.get("cameraId"),
                "kind": item.get("kind"),
                "filename": item.get("filename"),
                "recording": bool(item.get("recording")),
                "label": f"{_('LBL_CAM')} {item.get('cameraId')} · {item.get('filename')}" + (f" · {_('CAMERA_MEDIA_REC_BADGE')}" if item.get("recording") else ""),
                "isSelected": bool(selected and selected.get("cameraId") == item.get("cameraId") and selected.get("kind") == item.get("kind") and selected.get("filename") == item.get("filename")),
            })
        return result

    @Property("QVariantList", notify=_cameraMediaChanged)
    def cameraMediaCameraIds(self) -> list[int]:
        return sorted({i.get("cameraId") for i in self._camera_media_items if isinstance(i.get("cameraId"), int)})

    @Property(str, notify=_cameraMediaChanged)
    def cameraMediaFilter(self) -> str:
        return str(self._camera_media_filter)

    @Property(bool, notify=_cameraMediaChanged)
    def cameraMediaHasSelection(self) -> bool:
        return self._camera_media_selected is not None

    @Property(bool, notify=_cameraMediaChanged)
    def cameraMediaIsRecording(self) -> bool:
        return bool(self._camera_media_selected) and self._camera_media_selected.get("kind") == "recordings"

    @Property(str, notify=_cameraMediaChanged)
    def cameraMediaError(self) -> str:
        return self._camera_media_error

    @Property(int, notify=_cameraMediaChanged)
    def cameraMediaFrameCount(self) -> int:
        return len(self._camera_media_frames)

    @Property(int, notify=_cameraMediaChanged)
    def cameraMediaFrameIndex(self) -> int:
        return self._camera_media_frame_index

    @Property(bool, notify=_cameraMediaChanged)
    def cameraMediaPlaying(self) -> bool:
        return self._camera_media_playing

    @Property(str, notify=_cameraMediaChanged)
    def cameraMediaImageSource(self) -> str:
        """`image://cameraMedia/<key>` for the current real frame/snapshot -
        `""` when nothing is loaded yet, which QML reads as "show nothing",
        never a broken-image glyph."""
        selected = self._camera_media_selected
        if selected is None:
            return ""
        if selected.get("kind") == "snapshots":
            key = f"{selected['cameraId']}:snapshots:{selected['filename']}:0"
        else:
            if not self._camera_media_frames:
                return ""
            key = f"{selected['cameraId']}:recordings:{selected['filename']}:{self._camera_media_frame_index}"
        return f"image://cameraMedia/{key}?v={self._camera_media_frame_version}"

    @Slot()
    def loadCameraMedia(self) -> None:
        asyncio.ensure_future(self._run_load_camera_media())

    async def _run_load_camera_media(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.list_camera_media()
        if result is None or result[0] != 200 or not isinstance(result[1], dict):
            self._camera_media_error = _("CAMERA_MEDIA_LOAD_FAILED")
            self._cameraMediaChanged.emit()
            return
        self._camera_media_error = ""
        self._camera_media_items = result[1].get("items") or []
        self._cameraMediaChanged.emit()

    @Slot(str)
    def setCameraMediaFilter(self, camera_id: str) -> None:
        self._camera_media_filter = "all" if camera_id == "all" else int(camera_id)
        self._cameraMediaChanged.emit()

    @Slot(str)
    def saveCameraMedia(self, file_url: str) -> None:
        """Saves the selected picture or recording to a file of the computer (streamed in chunks by the connection)."""
        item = self._camera_media_selected
        if not item or not file_url:
            return
        asyncio.ensure_future(self._save_camera_media(QUrl(file_url).toLocalFile() or file_url, item))

    async def _save_camera_media(self, path: str, item: dict) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        saved = await conn.save_camera_media_to(item["cameraId"], item["kind"], item["filename"], path)
        self._camera_media_error = "" if saved else _("CAMERA_MEDIA_SAVE_FAILED")
        self._cameraMediaChanged.emit()

    @Slot(int, str, str)
    def selectCameraMediaItem(self, camera_id: int, kind: str, filename: str) -> None:
        self._stop_camera_media_playback()
        item = next(
            (i for i in self._camera_media_items if i.get("cameraId") == camera_id and i.get("kind") == kind and i.get("filename") == filename),
            None,
        )
        self._camera_media_selected = item
        self._camera_media_frames = []
        self._camera_media_frame_index = 0
        if self._media_frame_provider is not None:
            self._media_frame_provider.clear()
        self._cameraMediaChanged.emit()
        if item is not None:
            asyncio.ensure_future(self._run_load_selected_media(item))

    async def _run_load_selected_media(self, item: dict) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        data = await conn.fetch_camera_media_bytes(item["cameraId"], item["kind"], item["filename"])
        if self._camera_media_selected is not item:
            return  # selection moved on while this was in flight
        if not data:
            self._camera_media_error = _("CAMERA_MEDIA_LOAD_RECORDING_FAILED") if item["kind"] == "recordings" else _("CAMERA_MEDIA_LOAD_FAILED")
            self._cameraMediaChanged.emit()
            return
        self._camera_media_error = ""
        if item["kind"] == "snapshots":
            image = QImage()
            image.loadFromData(data)
            if self._media_frame_provider is not None:
                self._media_frame_provider.set_image(f"{item['cameraId']}:snapshots:{item['filename']}:0", image)
            self._camera_media_frame_version += 1
            self._cameraMediaChanged.emit()
            return
        frames = parse_mjpeg_frames(data)
        if not frames:
            self._camera_media_error = _("CAMERA_MEDIA_EMPTY_RECORDING")
            self._cameraMediaChanged.emit()
            return
        self._camera_media_frames = frames
        self._camera_media_frame_index = 0
        duration_ms = item.get("durationMs")
        frame_count = item.get("frameCount")
        if isinstance(duration_ms, (int, float)) and isinstance(frame_count, int) and frame_count > 1:
            self._camera_media_frame_interval_ms = max(1, int(duration_ms / frame_count))
        else:
            self._camera_media_frame_interval_ms = 100  # honest fallback, never a fabricated frame rate
        self._show_camera_media_frame()

    def _show_camera_media_frame(self) -> None:
        selected = self._camera_media_selected
        if selected is None or not self._camera_media_frames:
            return
        self._camera_media_frame_index = max(0, min(self._camera_media_frame_index, len(self._camera_media_frames) - 1))
        if self._media_frame_provider is not None:
            image = QImage()
            image.loadFromData(self._camera_media_frames[self._camera_media_frame_index])
            key = f"{selected['cameraId']}:recordings:{selected['filename']}:{self._camera_media_frame_index}"
            self._media_frame_provider.set_image(key, image)
        self._camera_media_frame_version += 1
        self._cameraMediaChanged.emit()

    @Slot()
    def toggleCameraMediaPlay(self) -> None:
        if self._camera_media_playing:
            self._pause_camera_media_playback()
        else:
            self._start_camera_media_playback()

    def _start_camera_media_playback(self) -> None:
        if not self._camera_media_frames:
            return
        if self._camera_media_frame_index >= len(self._camera_media_frames) - 1:
            self._camera_media_frame_index = 0
        self._camera_media_playing = True
        self._camera_media_timer.start(self._camera_media_frame_interval_ms)
        self._cameraMediaChanged.emit()

    def _pause_camera_media_playback(self) -> None:
        self._camera_media_timer.stop()
        self._camera_media_playing = False
        self._cameraMediaChanged.emit()

    @Slot()
    def stopCameraMediaPlay(self) -> None:
        self._stop_camera_media_playback()
        self._show_camera_media_frame()

    def _stop_camera_media_playback(self) -> None:
        self._camera_media_timer.stop()
        self._camera_media_playing = False
        self._camera_media_frame_index = 0

    def _advance_camera_media_frame(self) -> None:
        if self._camera_media_frame_index + 1 >= len(self._camera_media_frames):
            self._pause_camera_media_playback()
            return
        self._camera_media_frame_index += 1
        self._show_camera_media_frame()

    @Slot(int)
    def seekCameraMediaFrame(self, index: int) -> None:
        self._pause_camera_media_playback()
        self._camera_media_frame_index = index
        self._show_camera_media_frame()

    @Slot()
    def deleteCameraMediaSelected(self) -> None:
        asyncio.ensure_future(self._run_delete_camera_media())

    async def _run_delete_camera_media(self) -> None:
        item = self._camera_media_selected
        conn = self._controller.active_connection
        if item is None or conn is None:
            return
        result = await conn.delete_camera_media(item["cameraId"], item["kind"], item["filename"])
        if result is None or result[0] != 200:
            self._camera_media_error = _("CAMERA_MEDIA_DELETE_FAILED")
            self._cameraMediaChanged.emit()
            return
        self._camera_media_selected = None
        self._camera_media_frames = []
        if self._media_frame_provider is not None:
            self._media_frame_provider.clear()
        await self._run_load_camera_media()

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
        self.flasherChanged.emit()

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

    @Property("QVariantList", notify=flasherChanged)
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

    @Property(str, notify=flasherChanged)
    def flasherTier(self) -> str:
        key = self._flasher_active_key()
        return self._flasher_tier.get(key, "") if key else ""

    @Slot(str)
    def selectFlasherTier(self, tier: str) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_tier[key] = tier
            self._flasher_fram_supported[key] = None
            self._flasher_fram_result[key] = ""
            self.changed.emit()

    @Property(bool, notify=flasherChanged)
    def flasherNeedsRobotSlot(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self._flasher_tier[key] != "kinematicBrain"

    @Property("QVariantList", notify=flasherChanged)
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

    @Property(str, notify=flasherChanged)
    def flasherSelectedRobotId(self) -> str:
        key = self._flasher_active_key()
        return (self._flasher_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectFlasherRobot(self, robot_id: str) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_robot_id[key] = robot_id or None
            self.changed.emit()

    @Property(str, notify=flasherChanged)
    def flasherHopDescription(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        target = self._flasher_target(key)
        return hop_description(target) if target else ""

    @Property(bool, notify=flasherChanged)
    def flasherUnreachable(self) -> bool:
        key = self._flasher_active_key()
        if key is None or not self._flasher_is_hardware:
            return False
        target = self._flasher_target(key)
        return target is not None and resolve_hardware_target(target) is None

    @Property(str, notify=flasherChanged)
    def flasherVersionLabel(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return _("LBL_NO_VERSION_KNOWN")
        board = self._flasher_board_state(key)
        if board.get("firmwareVersion"):
            return f"{_('LBL_CURRENT_VERSION')}: {board.get('firmwareVersion', '?')} ({_('LBL_BOOTLOADER')} {board.get('bootloaderVersion', '?')})"
        return _("LBL_NO_VERSION_KNOWN")

    @Property(bool, notify=flasherChanged)
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
        self._flasher_fram_supported[key] = result.fram_erase_supported if (self._flasher_is_hardware and result.online) else None
        if not result.online:
            self._flasher_push_log(key, _("LBL_NO_RESPONSE"), "error")
            self.changed.emit()
            return
        self._flasher_push_log(key, f"{_('LBL_VERSION_FOUND')}: {result.firmware_version} / {result.bootloader_version}", "ok")
        patch = {"firmwareVersion": result.firmware_version, "bootloaderVersion": result.bootloader_version, "hardwareId": result.hardware_id}
        if self._flasher_tier[key] == "urtcHead" and result.expansion_board_type is not None:
            patch["expansionBoardType"] = result.expansion_board_type
        self._flasher_apply_patch(key, patch)

    @Property(str, notify=flasherChanged)
    def flasherFileInfo(self) -> str:
        key = self._flasher_active_key()
        file = self._flasher_file.get(key) if key else None
        if not file:
            return _("LBL_NO_FILE")
        return f"{file['name']} - {len(file['bytes']) / 1024:.1f} KB - CRC32 0x{crc32(file['bytes']):08X}"

    @Property(bool, notify=flasherChanged)
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

    @Property(bool, notify=flasherChanged)
    def flasherGithubAvailable(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and GITHUB_FIRMWARE_REPO.get(self._flasher_tier[key]) is not None

    @Property(str, notify=flasherChanged)
    def flasherGithubButtonLabel(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        repo = GITHUB_FIRMWARE_REPO.get(self._flasher_tier[key])
        return f"{_('BTN_DOWNLOAD_GITHUB')} ({repo})" if repo else ""

    @Property(bool, notify=flasherChanged)
    def flasherGithubBusy(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_gh_busy.get(key, False) if key else False

    @Property("QVariantList", notify=flasherChanged)
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
            self._flasher_file[key] = {"name": asset.name, "bytes": data, "hardware_id": asset.hardware_id, "version_tag": asset.release_tag, "signature": asset.signature, "target": asset.target, "min_bootloader": asset.min_bootloader}
            if not asset.signature:
                # the .sig file published next to the image; an image without one is left to the board to judge
                try:
                    async with httpx.AsyncClient() as client:
                        sig = await client.get(f"{asset.url}.sig", timeout=10)
                    if sig.status_code == 200:
                        self._flasher_file[key]["signature"] = normalize_signature(sig.text)
                except Exception:
                    pass
            self._flasher_push_log(key, f"{_('LBL_FILE_LOADED')}: {asset.name} ({len(data)} bytes)", "ok")
        except Exception as exc:
            self._flasher_push_log(key, f"{_('LBL_GITHUB_ERROR')}: {exc}", "error")
        self.changed.emit()

    @Property(bool, notify=flasherChanged)
    def flasherAllowDowngrade(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_allow_downgrade.get(key, False) if key else False

    @Slot(bool)
    def setFlasherAllowDowngrade(self, value: bool) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_allow_downgrade[key] = value

    @Property(bool, notify=flasherChanged)
    def flasherEraseFram(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_erase_fram.get(key, False) if key else False

    @Slot(bool)
    def setFlasherEraseFram(self, value: bool) -> None:
        key = self._flasher_active_key()
        if key is not None:
            self._flasher_erase_fram[key] = value

    @Property(bool, notify=flasherChanged)
    def flasherEraseFramEnabled(self) -> bool:
        """The simulation honours the option as it always did; over the real bus it needs the announcement of the server and the kinematic brain as the target."""
        key = self._flasher_active_key()
        if key is None:
            return False
        if not self._flasher_is_hardware:
            return True
        return self._flasher_fram_supported.get(key) is True and self._flasher_tier.get(key) == "kinematicBrain"

    @Property(bool, notify=flasherChanged)
    def flasherFramVisible(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self._flasher_is_hardware and self._flasher_tier.get(key) == "kinematicBrain"

    @Property(str, notify=flasherChanged)
    def flasherFramNote(self) -> str:
        key = self._flasher_active_key()
        if key is None:
            return ""
        supported = self._flasher_fram_supported.get(key)
        if supported is None:
            return _("LBL_FRAMOP_UNKNOWN")
        return "" if supported else _("LBL_FRAMOP_UNSUPPORTED")

    @Property(bool, notify=flasherChanged)
    def flasherFramReady(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self._flasher_fram_supported.get(key) is True and not self._flasher_fram_busy.get(key, False) and not self._flasher_flashing.get(key, False)

    @Property(bool, notify=flasherChanged)
    def flasherFramBusy(self) -> bool:
        key = self._flasher_active_key()
        return bool(key) and self._flasher_fram_busy.get(key, False)

    @Property(str, notify=flasherChanged)
    def flasherFramResult(self) -> str:
        key = self._flasher_active_key()
        return self._flasher_fram_result.get(key, "") if key else ""

    @Property(str, constant=True)
    def framEraseWord(self) -> str:
        return FRAM_ERASE_WORD

    @Slot(str, result=bool)
    def framWordMatches(self, typed: str) -> bool:
        return fram_erase_word_matches(typed)

    @Slot()
    def flasherFramSelfTest(self) -> None:
        key = self._flasher_active_key()
        if key is not None and self.flasherFramReady:
            asyncio.ensure_future(self._run_fram(key, "selftest"))

    @Slot(str)
    def flasherFramErase(self, typed_word: str) -> None:
        key = self._flasher_active_key()
        if key is not None and self.flasherFramReady and fram_erase_word_matches(typed_word):
            asyncio.ensure_future(self._run_fram(key, "erase", typed_word))

    @staticmethod
    def _fram_status_text(status: str) -> str:
        text_key = "FRAMOP_STATUS_" + status.upper().replace("-", "_")
        text = _(text_key)
        return text if text != text_key else _("FRAMOP_STATUS_UNKNOWN")

    def _fram_result_text(self, operation: str, result: FramOperationResult) -> str:
        if result.ok:
            return _("MSG_FRAMOP_RESULT_ERASE_OK", value=result.value) if operation == "erase" else _("MSG_FRAMOP_RESULT_SELFTEST_OK")
        return _("MSG_FRAMOP_RESULT_FAILED", operation=_("FRAMOP_OPERATION_" + operation.upper()), status=self._fram_status_text(result.status))

    async def _run_fram(self, key: str, operation: str, typed_word: str = "") -> None:
        self._flasher_fram_busy[key] = True
        self._flasher_fram_result[key] = _("LBL_FRAMOP_BUSY")
        self.changed.emit()
        try:
            conn = self._controller.active_connection
            if conn is None:
                result = FramOperationResult(reachable=False, ok=False, status="unreachable")
            else:
                result = await hardware_fram_operation(conn, operation, typed_word)
        finally:
            self._flasher_fram_busy[key] = False
        text = self._fram_result_text(operation, result)
        self._flasher_fram_result[key] = text
        self._flasher_push_log(key, text, "ok" if result.ok else "error")
        self.changed.emit()

    @Property(bool, notify=flasherChanged)
    def flasherFlashing(self) -> bool:
        key = self._flasher_active_key()
        return self._flasher_flashing.get(key, False) if key else False

    @Property(bool, notify=flasherChanged)
    def flasherCanFlash(self) -> bool:
        key = self._flasher_active_key()
        return key is not None and self.flasherHasFile and not self._flasher_flashing.get(key, False) and not self.flasherUnreachable

    @Property(str, notify=flasherChanged)
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
        message = _("MSG_CONFIRM_FLASH", target=_(_TIER_LABEL_KEYS[self._flasher_tier[key]]), robot=robot_label)
        if self._flasher_is_hardware and self._flasher_erase_fram.get(key, False):
            message += " " + _("MSG_CONFIRM_FLASH_ERASE")
        return message

    @Property(str, notify=flasherChanged)
    def flasherProgressLabel(self) -> str:
        key = self._flasher_active_key()
        return self._flasher_progress.get(key, {}).get("label", "") if key else ""

    @Property(int, notify=flasherChanged)
    def flasherProgressPercent(self) -> int:
        key = self._flasher_active_key()
        return self._flasher_progress.get(key, {}).get("percent", 0) if key else 0

    @Property("QVariantList", notify=flasherChanged)
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

    def _flasher_on_progress(self, key: str, payload: object) -> None:
        """One live line of a real flash cycle: only while this panel's own hardware flash runs, so another session's flash never shows here."""
        line = flasher_logic.progress_line(payload)
        if line is None or not self._flasher_flashing.get(key) or not self._flasher_is_hardware:
            return
        label = _(f"FLASHER_PROGRESS_{line['phase'].upper()}")
        if line["pages"] is not None and line["phase"] == "transferring":
            label += f" ({line['pages'][0]}/{line['pages'][1]})"
        self._flasher_progress[key] = {"label": label, "percent": line["percent"] if line["percent"] is not None else self._flasher_progress.get(key, {}).get("percent", 0)}
        if line["phase"] == "error":
            self._flasher_push_log(key, f"{_('LBL_FLASH_HARDWARE_FAILED')}: {line['reason'] or _('FLASHER_PROGRESS_ERROR')}", "error")
        elif line["log"]:
            self._flasher_push_log(key, label, "info")
        self.flasherChanged.emit()

    async def _run_flash(self, key: str, target: CanOtaTarget, file: dict) -> None:
        self._flasher_flashing[key] = True
        self._flasher_push_log(key, f"{_('LBL_FLASH_START')}: {file['name']} - {hop_description(target)}")
        self.flasherChanged.emit()
        try:
            if self._flasher_is_hardware:
                resolved = resolve_hardware_target(target)
                if not resolved:
                    self._flasher_push_log(key, _("LBL_HARDWARE_TARGET_UNREACHABLE"), "error")
                    return
                self._flasher_progress[key] = {"label": _("FLASHER_PROGRESS_CONNECTING"), "percent": 0}
                self.flasherChanged.emit()
                refusal = flash_preflight(
                    file.get("hardware_id"), file.get("version_tag"), self._flasher_board_state(key).get("firmwareVersion"),
                    self._flasher_allow_downgrade.get(key, False), self._flasher_erase_fram.get(key, False),
                    self._flasher_fram_supported.get(key) is True, self._flasher_tier.get(key),
                )
                if refusal:
                    self._flasher_push_log(key, _("FLASHER_PREFLIGHT_" + refusal.upper()), "error")
                    self._flasher_progress[key] = {"label": "", "percent": 0}
                    return
                version_major, version_minor = parse_version_tag(file.get("version_tag"))
                hardware_id_number = int(file["hardware_id"], 0) if file.get("hardware_id") else 0
                # the signature is checked here, on this computer, before a single byte goes to the flashing service
                verdict = firmware_signature.evaluate(
                    self._firmware_signing_settings(), file["bytes"], hardware_id_number or None, file.get("version_tag"), file.get("signature"),
                )
                if not verdict.ok:
                    self._flasher_push_log(key, f"{_('FW_SIG_REFUSED')}: {_(verdict.reason)}", "error")
                    self._flasher_progress[key] = {"label": "", "percent": 0}
                    return
                if verdict.skipped:
                    self._flasher_push_log(key, _("FW_SIG_OFF_LOG"), "error")
                else:
                    self._flasher_push_log(key, _("FW_SIG_OK"), "ok")
                conn = self._controller.active_connection
                if conn is None:
                    self._flasher_push_log(key, _("LBL_NO_RESPONSE"), "error")
                    return
                # the live per-page progress of the cycle arrives over the WebSocket, not through the answer of the request, which comes once at the end
                def on_progress(payload: object, _key: str = key) -> None:
                    self._flasher_on_progress(_key, payload)

                progress_signal = getattr(conn, "canota_progress", None)  # a stand-in connection of a check has none
                if progress_signal is not None:
                    progress_signal.connect(on_progress)
                try:
                    result = await hardware_start_flash(
                        conn, target, file["bytes"],
                        version_major,
                        version_minor,
                        hardware_id_number,
                        flash_signing_options(file.get("version_tag"), self._flasher_board_state(key).get("firmwareVersion"), file.get("signature"), {"target": file.get("target"), "min_bootloader": file.get("min_bootloader")}),
                    )
                finally:
                    if progress_signal is not None:
                        progress_signal.disconnect(on_progress)
                if result.success:
                    self._flasher_progress[key] = {"label": _("FLASHER_PROGRESS_DONE"), "percent": 100}
                    self._flasher_push_log(key, _("LBL_FLASH_DONE"), "ok")
                    self._flasher_apply_patch(key, {"firmwareVersion": file.get("version_tag") or file["name"].removesuffix(".bin")})
                    if self._flasher_erase_fram.get(key, False):
                        # the person ticked the erase and confirmed the flash, whose dialog says it: the word is the one the server and the bridge ask for
                        self._flasher_push_log(key, _("LOG_FRAMOP_AFTER_FLASH"))
                        erased = await hardware_fram_operation(conn, "erase", FRAM_ERASE_WORD)
                        self._flasher_push_log(key, self._fram_result_text("erase", erased), "ok" if erased.ok else "error")
                else:
                    self._flasher_push_log(key, f"{_('LBL_FLASH_HARDWARE_FAILED')}: {result.reason}", "error")
                return

            opts = FlashOptions(allow_downgrade=self._flasher_allow_downgrade.get(key, False), erase_fram=self._flasher_erase_fram.get(key, False))
            last_phase = None
            async for progress in mock_flash(target, file["bytes"], opts):
                last_phase = progress.phase
                suffix = f" ({progress.pages_sent}/{progress.pages_total})" if progress.pages_total > 1 and progress.phase == "transferring" else ""
                self._flasher_progress[key] = {"label": f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')}{suffix} - {progress.percent}%", "percent": progress.percent}
                self.flasherChanged.emit()
                if progress.phase == "transferring" and progress.pages_sent % 5 != 0 and progress.pages_sent != progress.pages_total:
                    continue
                self._flasher_push_log(key, f"{_(f'FLASHER_PROGRESS_{progress.phase.upper()}')} ({progress.pages_sent}/{progress.pages_total})", "error" if progress.phase == "error" else "info")
            if last_phase != "error":
                self._flasher_push_log(key, _("LBL_FLASH_DONE"), "ok")
                self._flasher_apply_patch(key, {"firmwareVersion": file["name"].removesuffix(".bin")})
        finally:
            self._flasher_flashing[key] = False
            self.flasherChanged.emit()

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
        self.testerChanged.emit()
        self.flasherChanged.emit()

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
        """Switching
        tier/robot drops any in-flight self-test/monitor state for the
        PREVIOUS target rather than leaving it displayed against a now-
        different one."""
        self._tester_stop_monitor(key)
        self._tester_fram_state[key] = None
        self._tester_testing[key] = False
        self._tester_self_test_steps[key] = []
        self._tester_frames[key] = []
        self.changed.emit()

    @Property("QVariantList", notify=testerChanged)
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

    @Property(str, notify=testerChanged)
    def testerTier(self) -> str:
        key = self._tester_active_key()
        return self._tester_tier.get(key, "") if key else ""

    @Slot(str)
    def selectTesterTier(self, tier: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_tier[key] = tier
            self._tester_reset_for_new_target(key)

    @Property(bool, notify=testerChanged)
    def testerNeedsRobotSlot(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] != "kinematicBrain"

    @Property("QVariantList", notify=testerChanged)
    def testerRobotOptions(self) -> list[dict[str, str]]:
        key = self._tester_active_key()
        if key is None:
            return []
        ctrl = self._tester_controller.get(key)
        robots = ctrl.robots if ctrl is not None else []
        return [{"id": r.id, "label": f"{slot_label(i)} - {r.model}"} for i, r in enumerate(robots)]

    @Property(str, notify=testerChanged)
    def testerSelectedRobotId(self) -> str:
        key = self._tester_active_key()
        return (self._tester_robot_id.get(key) or "") if key else ""

    @Slot(str)
    def selectTesterRobot(self, robot_id: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_robot_id[key] = robot_id or None
            self._tester_reset_for_new_target(key)

    @Property(str, notify=testerChanged)
    def testerHopDescription(self) -> str:
        key = self._tester_active_key()
        if key is None:
            return ""
        target = self._tester_target(key)
        return hop_description(target) if target else ""

    @Property(bool, notify=testerChanged)
    def testerSimulatedNoteVisible(self) -> bool:
        return self._flasher_is_hardware

    @Property(bool, notify=testerChanged)
    def testerQueryEnabled(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_target(key) is not None

    @Property(str, notify=testerChanged)
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

    @Property(bool, notify=testerChanged)
    def testerShowGlobal(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] == "urtcHead"

    @Property(bool, notify=testerChanged)
    def testerShowFram(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] in ("controllerBoard", "urtcHead")

    @Property(bool, notify=testerChanged)
    def testerShowTelemetry(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_tier[key] == "urtcHead" and self._tester_current_robot(key) is not None

    @Property(str, notify=testerChanged)
    def testerStatusColor(self) -> str:
        key = self._tester_active_key()
        return self._tester_status_color.get(key, "#00ff66") if key else "#00ff66"

    @Slot(str)
    def setTesterStatusColor(self, color: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_status_color[key] = color
            self.changed.emit()

    @Property(bool, notify=testerChanged)
    def testerRingOn(self) -> bool:
        key = self._tester_active_key()
        return self._tester_ring_on.get(key, False) if key else False

    @Slot()
    def toggleTesterRing(self) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_ring_on[key] = not self._tester_ring_on[key]
            self.changed.emit()

    @Property(str, notify=testerChanged)
    def testerOledMode(self) -> str:
        key = self._tester_active_key()
        return self._tester_oled_mode.get(key, "standard") if key else "standard"

    @Slot(str)
    def setTesterOledMode(self, mode: str) -> None:
        key = self._tester_active_key()
        if key is not None:
            self._tester_oled_mode[key] = mode

    @Property(str, notify=testerChanged)
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

    @Property(str, notify=testerChanged)
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

    @Property(str, notify=testerChanged)
    def testerTelemetryTitle(self) -> str:
        key = self._tester_active_key()
        robot = self._tester_current_robot(key) if key else None
        return f"{_('LBL_TOOL_TELEMETRY')} - {robot.tool}" if robot is not None else ""

    @Property(str, notify=testerChanged)
    def testerTelemetryLabel(self) -> str:
        key = self._tester_active_key()
        robot = self._tester_current_robot(key) if key else None
        return _(f"LBL_TELEMETRY_{_category_for(robot.tool).upper()}") if robot is not None else ""

    @Property(bool, notify=testerChanged)
    def testerTesting(self) -> bool:
        key = self._tester_active_key()
        return self._tester_testing.get(key, False) if key else False

    @Property("QVariantList", notify=testerChanged)
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

    @Property(bool, notify=testerChanged)
    def testerMonitorRunning(self) -> bool:
        key = self._tester_active_key()
        return key is not None and self._tester_monitor_task.get(key) is not None

    @Property("QVariantList", notify=testerChanged)
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
                self.testerChanged.emit()
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

    @Property(str, notify=overviewChanged)
    def overviewName(self) -> str:
        return self._overview_name

    @Property(str, notify=overviewChanged)
    def overviewIp(self) -> str:
        return self._overview_ip

    @Property(str, notify=overviewChanged)
    def overviewRobotCount(self) -> str:
        return self._overview_robot_count

    @Property(str, notify=overviewChanged)
    def overviewOnlineCount(self) -> str:
        return self._overview_online_count

    @Property(str, notify=overviewChanged)
    def overviewCpu(self) -> str:
        return self._overview_cpu

    @Property(str, notify=overviewChanged)
    def overviewMem(self) -> str:
        return self._overview_mem

    @Property(str, notify=overviewChanged)
    def overviewTemp(self) -> str:
        return self._overview_temp

    @Property(str, notify=overviewChanged)
    def overviewUptime(self) -> str:
        return self._overview_uptime

    @Property("QVariantList", notify=overviewChanged)
    def overviewRobots(self) -> list[dict[str, object]]:
        return self._overview_robots

    def _on_overview_metrics_changed(self, metrics: dict) -> None:
        cpu = metrics.get("cpu_load")
        mem = metrics.get("memory_usage")
        temp = metrics.get("temp")
        uptime = metrics.get("uptime")
        self._overview_cpu = f"{cpu}%" if cpu is not None else "-"
        self._overview_mem = f"{mem}%" if mem is not None else "-"
        real_temp = metrics.get("temp_is_real") is not False  # false = made-up value from a host with no sensor
        self._overview_temp = f"{temp:.0f}°C" if real_temp and isinstance(temp, (int, float)) else "-"
        if isinstance(uptime, (int, float)):
            hours, rem = divmod(int(uptime), 3600)
            minutes = rem // 60
            self._overview_uptime = f"{hours}h {minutes}m"
        else:
            self._overview_uptime = "-"
        self.overviewChanged.emit()

    def _on_overview_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        if active is None:
            self._overview_name = "-"
            self._overview_ip = "-"
            self._overview_robot_count = "-"
            self._overview_online_count = "-"
            self._overview_robots = []
            self.overviewChanged.emit()
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
                "status": _({"offline": "STATUS_OFFLINE", "simulated": "MOTION_SIMULATED", "live": "MOTION_LIVE"}[r.motion_source]),
                "motionSource": r.motion_source,
                "online": r.online,
                "speedAccel": f"{r.speed:.0f}% / {r.acceleration:.0f}%",
            }
            for r in robots
        ]
        self.overviewChanged.emit()


def run_qtquick() -> int:
    # Qt6's default rounding policy snaps a fractional OS scale factor (125%/150%/175%, common on a 27"-32" 4K
    # monitor) to the nearest whole integer, which reads as slightly blurry or mis-sized fixed-pixel controls.
    # PassThrough applies the OS's exact factor instead - it must be set before the QGuiApplication exists, and
    # so must the default surface format (macOS needs an OpenGL 3.3 core context for the 3D previews).
    from PySide6.QtCore import Qt

    from hydra_suite.render.gl_format import install_default_surface_format

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    install_default_surface_format()
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

    # qasync runs every `async def` of app.py, net/client.py and net/discovery.py on Qt's own event loop.
    import asyncio

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = SuiteController()
    # The Live / Sim choices and the servers the operator asked to remember come back from the configuration file;
    # a remembered password comes from the secure store of the computer (never from the file).
    access.CONDITIONAL.set(access.ConditionalSetting.from_config(load_config()).mode)
    loaded_modes = access.ModeState.from_config(load_config())
    access.MODES.modes.update(loaded_modes.modes)
    access.MODES.default_mode = loaded_modes.default_mode
    _listen_only = access.ListenOnlyState.from_config(load_config())
    access.LISTEN_ONLY.set(_listen_only.enabled)
    access.LISTEN_ONLY.servers = set(_listen_only.servers)
    credential_store = CredentialStore(keyring_backend(), load_config, save_config)
    catalog_frame_provider = ViewportFrameProvider()
    frame_provider = CameraFrameProvider()
    viewport_frame_provider = ViewportFrameProvider()
    media_frame_provider = MediaFrameProvider()
    bridge = SuiteQtBridge(
        controller,
        frame_provider=frame_provider,
        viewport_frame_provider=viewport_frame_provider,
        media_frame_provider=media_frame_provider,
        credential_store=credential_store,
        catalog_frame_provider=catalog_frame_provider,
    )
    for remembered in credential_store.load_servers():
        controller.add_server(remembered)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("catalogFrame", catalog_frame_provider)
    engine.addImageProvider("cameraFrames", frame_provider)
    engine.addImageProvider("viewportFrame", viewport_frame_provider)
    engine.addImageProvider("vacuumFrame", bridge._vacuum_frame_provider)
    engine.addImageProvider("cameraMedia", media_frame_provider)
    engine.rootContext().setContextProperty("suiteBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        return 1

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(run_qtquick())
