# =============================================================================
# HYDRA-UMC SUITE - ui/panels/cameras_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own CamerasView.tsx +
# Config.tsx "Camera Setup" tab combined into one card (SUITE has no
# separate Config screen for this - one card doing both keeps the same
# real capability without inventing a second panel STUDIO doesn't have
# an equivalent split for). This card's own metadata is real end to end
# (which cameras a controller has, their type, assigned robot, source
# type, and real USB/IP connection settings), and the real MJPEG stream
# now renders here too - iter_mjpeg_frames() below is a real client for
# HYDRA-UMC-VISION-STREAMER's own `stream serve`, proxied through
# HYDRA-UMC-SERVER's own `GET /api/camera/:id/stream`, the same real
# JPEG SOI/EOI marker-scanning approach HYDRA-UMC-ANDROID-CONTROL's own
# MjpegStreamParser.kt already uses, not a placeholder. Editing a camera
# here really does round-trip to the server and to any browser tab
# watching the same controller, the same synced settings blob every
# other panel here already reads/writes.
# =============================================================================
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator

import httpx
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import CAMERA_TYPES, RTSP_DEFAULT_PORT, CameraView, HydraState, RobotView, ip_stream_labels
from hydra_suite.net.client import HydraConnection

# type strings for the USB-only and Thermal option groups, mirroring
# HYDRA-UMC-STUDIO's own CamerasView.tsx combobox split. The IP group is
# NOT a fixed pair here - see ip_stream_labels() in models.py, used
# directly wherever this panel needs the real, per-camera IP option
# list instead.
_USB_TYPE_OPTIONS = (CAMERA_TYPES[0],)
_THERMAL_TYPE_OPTIONS = CAMERA_TYPES[3:]

# Real camera-process status colors, matching HYDRA-UMC-STUDIO's own
# Config.tsx badge coloring for the exact same 3 states HYDRA-UMC-SERVER's
# own GET /api/cameras/status can report (see that route's own comment).
_STATUS_COLORS = {"running": "#10b981", "starting": "#f59e0b", "error": "#ef4444", "stopped": "#8a97a6"}

GRID_COLUMNS = 4
_USB_PAGE = 0
_IP_PAGE = 1

# Max single JPEG frame this reader accepts before treating it as
# corrupt and resyncing to the next SOI - matches
# HYDRA-UMC-ANDROID-CONTROL's own MjpegStreamParser.kt exactly (same
# real 1MB ceiling, same "keep the socket, resync instead of dropping
# the whole connection over one oversized frame" reasoning).
_MJPEG_MAX_FRAME_BYTES = 1024 * 1024
_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"


async def iter_mjpeg_frames(url: str) -> AsyncIterator[bytes]:
    """Real MJPEG multipart/x-mixed-replace client - reads raw bytes off
    the wire and scans for JPEG SOI(0xFFD8)/EOI(0xFFD9) markers directly,
    the same real, proven approach HYDRA-UMC-ANDROID-CONTROL's own
    MjpegStreamParser.kt uses (see that file's own header) - deliberately
    NOT parsing the multipart boundary/Content-Length headers at all,
    since the marker scan already works regardless of exact framing and
    is what the one other real client in this ecosystem already does.
    Yields one complete, real JPEG frame's raw bytes at a time; ends
    (StopAsyncIteration) on a genuine connection close/error - never
    raises out of this generator, so a caller's own `async for` loop
    doesn't need its own try/except around iteration itself."""
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, timeout=httpx.Timeout(10.0, read=None)) as resp:
                if resp.status_code != 200:
                    return
                buffer = bytearray()
                async for chunk in resp.aiter_bytes():
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(_JPEG_SOI)
                        if start < 0:
                            # No SOI at all yet - drop everything except a
                            # possible trailing 0xFF (could be the first
                            # byte of a SOI split across chunks).
                            if buffer and buffer[-1] == 0xFF:
                                del buffer[:-1]
                            else:
                                buffer.clear()
                            break
                        end = buffer.find(_JPEG_EOI, start + 2)
                        if end < 0:
                            # Frame not complete yet. If what we're
                            # accumulating already exceeds the real cap,
                            # drop the leading SOI so a genuinely
                            # oversized/corrupt frame can't grow the
                            # buffer forever - the next chunk's own scan
                            # then looks for a fresh SOI instead.
                            if len(buffer) - start > _MJPEG_MAX_FRAME_BYTES:
                                del buffer[: start + 2]
                                continue
                            del buffer[:start]
                            break
                        frame = bytes(buffer[start : end + 2])
                        del buffer[: end + 2]
                        if len(frame) <= _MJPEG_MAX_FRAME_BYTES:
                            yield frame
                        # else: corrupt/oversized frame, silently skipped -
                        # matches MjpegFrameResult.CorruptFrame's own
                        # "keep reading, don't kill the feed" behavior.
    except (httpx.HTTPError, OSError):
        return
    # asyncio.CancelledError deliberately NOT caught here - swallowing it
    # would break the caller's own task.cancel() contract (cancellation
    # needs to actually propagate, not look like a clean stream end).


class CameraCard(QFrame):
    def __init__(
        self,
        camera: CameraView,
        on_toggle,
        on_type_changed,
        on_field_changed,
        get_stream_url,
        get_connection,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("cameraCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._camera = camera
        self._on_toggle = on_toggle
        self._on_type_changed = on_type_changed
        self._on_field_changed = on_field_changed
        # Callable[[int], str | None] - resolves this camera's own real
        # GET /api/camera/:id/stream URL against whichever server is
        # currently active (None if no server is connected right now) -
        # a plain callback rather than a fixed URL since the active
        # connection can change while this card is alive.
        self._get_stream_url = get_stream_url
        # Callable[[], HydraConnection | None] - same "resolve against
        # whatever's active right now" reasoning as get_stream_url, used
        # by the discovery buttons below (POST/GET calls, not the
        # streaming GET get_stream_url resolves).
        self._get_connection = get_connection
        self._stream_task: asyncio.Task | None = None
        self._streaming_connected = False
        self._discovery_task: asyncio.Task | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header = QLabel()
        header.setObjectName("cameraCardHeading")
        header_row.addWidget(header, 1)
        self._header = header
        self._status_badge = QLabel()
        self._status_badge.setStyleSheet("font-size: 10px; font-weight: 700;")
        header_row.addWidget(self._status_badge)
        layout.addLayout(header_row)

        self._video_area = QLabel()
        self._video_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_area.setMinimumHeight(100)
        self._video_area.setObjectName("cameraVideoArea")
        layout.addWidget(self._video_area, 1)

        self._type_combo = QComboBox()
        self._type_combo.currentTextChanged.connect(self._on_type_combo_changed)
        layout.addWidget(self._type_combo)

        robot_row = QHBoxLayout()
        robot_row.addWidget(QLabel(_("LBL_ASSIGNED_ROBOT")))
        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        robot_row.addWidget(self._robot_combo, 1)
        layout.addLayout(robot_row)

        # Source Type toggle (USB / IP Camera) - real, generic RTSP
        # support alongside USB, matching HYDRA-UMC-STUDIO's own
        # Config.tsx "Camera Setup" tab one-to-one (see that file's own
        # header comment).
        source_row = QHBoxLayout()
        self._usb_button = QPushButton(_("BTN_SOURCE_USB"))
        self._usb_button.setCheckable(True)
        self._usb_button.clicked.connect(lambda: self._on_source_type_clicked("usb"))
        self._ip_button = QPushButton(_("BTN_SOURCE_IP"))
        self._ip_button.setCheckable(True)
        self._ip_button.clicked.connect(lambda: self._on_source_type_clicked("ip"))
        source_row.addWidget(self._usb_button)
        source_row.addWidget(self._ip_button)
        layout.addLayout(source_row)

        self._source_stack = QStackedWidget()

        usb_page = QWidget()
        usb_layout = QVBoxLayout(usb_page)
        usb_layout.setContentsMargins(0, 0, 0, 0)
        usb_layout.addWidget(QLabel(_("LBL_HARDWARE_SOURCE")))
        self._hardware_source_edit = QLineEdit()
        self._hardware_source_edit.setPlaceholderText("/dev/video0")
        self._hardware_source_edit.editingFinished.connect(self._on_hardware_source_edited)
        usb_layout.addWidget(self._hardware_source_edit)

        self._discover_usb_btn = QPushButton(_("BTN_DISCOVER_USB"))
        self._discover_usb_btn.clicked.connect(lambda: asyncio.ensure_future(self._discover_usb()))
        usb_layout.addWidget(self._discover_usb_btn)
        self._usb_devices_combo = QComboBox()
        self._usb_devices_combo.setVisible(False)
        self._usb_devices_combo.activated.connect(self._on_usb_device_picked)
        usb_layout.addWidget(self._usb_devices_combo)
        self._source_stack.addWidget(usb_page)

        ip_page = QWidget()
        ip_layout = QVBoxLayout(ip_page)
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.setSpacing(3)
        ip_layout.addWidget(QLabel(_("LBL_IP_HOST")))
        self._ip_host_edit = QLineEdit()
        self._ip_host_edit.setPlaceholderText("192.168.0.210")
        self._ip_host_edit.editingFinished.connect(self._on_ip_host_edited)
        ip_layout.addWidget(self._ip_host_edit)

        port_path_row = QHBoxLayout()
        port_col = QVBoxLayout()
        port_col.addWidget(QLabel(_("LBL_RTSP_PORT")))
        self._rtsp_port_spin = QSpinBox()
        self._rtsp_port_spin.setRange(1, 65535)
        self._rtsp_port_spin.setValue(RTSP_DEFAULT_PORT)
        self._rtsp_port_spin.editingFinished.connect(self._on_rtsp_port_edited)
        port_col.addWidget(self._rtsp_port_spin)
        port_path_row.addLayout(port_col, 1)

        path_col = QVBoxLayout()
        path_col.addWidget(QLabel(_("LBL_RTSP_PATH")))
        self._rtsp_path_edit = QLineEdit()
        self._rtsp_path_edit.setPlaceholderText("/11")
        self._rtsp_path_edit.editingFinished.connect(self._on_rtsp_path_edited)
        path_col.addWidget(self._rtsp_path_edit)
        port_path_row.addLayout(path_col, 2)
        ip_layout.addLayout(port_path_row)

        self._discover_rtsp_btn = QPushButton(_("BTN_DISCOVER_RTSP"))
        self._discover_rtsp_btn.clicked.connect(lambda: asyncio.ensure_future(self._discover_rtsp()))
        ip_layout.addWidget(self._discover_rtsp_btn)

        cred_row = QHBoxLayout()
        user_col = QVBoxLayout()
        user_col.addWidget(QLabel(_("LBL_IP_USERNAME")))
        self._ip_username_edit = QLineEdit()
        self._ip_username_edit.setPlaceholderText("admin")
        self._ip_username_edit.editingFinished.connect(self._on_ip_username_edited)
        user_col.addWidget(self._ip_username_edit)
        cred_row.addLayout(user_col)

        pass_col = QVBoxLayout()
        pass_col.addWidget(QLabel(_("LBL_IP_PASSWORD")))
        self._ip_password_edit = QLineEdit()
        self._ip_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._ip_password_edit.editingFinished.connect(self._on_ip_password_edited)
        pass_col.addWidget(self._ip_password_edit)
        cred_row.addLayout(pass_col)
        ip_layout.addLayout(cred_row)

        self._source_stack.addWidget(ip_page)
        layout.addWidget(self._source_stack)

        self._discovery_status_label = QLabel()
        self._discovery_status_label.setWordWrap(True)
        self._discovery_status_label.setStyleSheet("font-size: 10px; color: #8a97a6;")
        self._discovery_status_label.setVisible(False)
        layout.addWidget(self._discovery_status_label)

        self._toggle_button = QPushButton()
        self._toggle_button.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_button)

        self.refresh(camera, [])

    def refresh(self, camera: CameraView, robots: list[RobotView]) -> None:
        self._camera = camera
        self._header.setText(f"{_('LBL_CAM')} {camera.id}")

        is_ip = camera.source_type == "ip"
        self._sync_type_options(is_ip, camera.camera_type)

        self._robot_combo.blockSignals(True)
        self._robot_combo.clear()
        self._robot_combo.addItem(_("OPT_NONE_FLOATING"), None)
        for robot in robots:
            self._robot_combo.addItem(f"{robot.model} (A{robot.id})", int(robot.id))
        restore_index = 0
        if camera.assigned_robot_id is not None:
            for i in range(self._robot_combo.count()):
                if self._robot_combo.itemData(i) == camera.assigned_robot_id:
                    restore_index = i
                    break
        self._robot_combo.setCurrentIndex(restore_index)
        self._robot_combo.blockSignals(False)

        self._usb_button.setChecked(not is_ip)
        self._ip_button.setChecked(is_ip)
        self._source_stack.setCurrentIndex(_IP_PAGE if is_ip else _USB_PAGE)

        if self._hardware_source_edit.text() != camera.hardware_source:
            self._hardware_source_edit.setText(camera.hardware_source)
        if self._ip_host_edit.text() != camera.ip_host:
            self._ip_host_edit.setText(camera.ip_host)
        if self._rtsp_port_spin.value() != camera.rtsp_port:
            self._rtsp_port_spin.setValue(camera.rtsp_port)
        if self._rtsp_path_edit.text() != camera.rtsp_path:
            self._rtsp_path_edit.setText(camera.rtsp_path)
        if self._ip_username_edit.text() != camera.ip_username:
            self._ip_username_edit.setText(camera.ip_username)
        if self._ip_password_edit.text() != camera.ip_password:
            self._ip_password_edit.setText(camera.ip_password)

        if camera.connected:
            self._toggle_button.setText(_("BTN_TOGGLE_CONNECTION") + f" ({_('STATUS_CONNECTED')})")
            self._start_stream()
        else:
            self._stop_stream()
            self._video_area.setPixmap(QPixmap())
            self._video_area.setText(_("STATUS_NO_SIGNAL"))
            self._video_area.setStyleSheet("background: #0a0f14; color: #4a5563; border: 1px dashed #1a2530;")
            self._toggle_button.setText(_("BTN_TOGGLE_CONNECTION") + f" ({_('STATUS_DISCONNECTED')})")

    # --- real MJPEG stream ------------------------------------------------

    def _start_stream(self) -> None:
        if self._stream_task is not None and not self._stream_task.done():
            return  # already streaming - refresh() runs on every state
            # broadcast, not just real changes, so this must be a no-op
            # for "still connected, nothing changed" the common case.
        url = self._get_stream_url(self._camera.id)
        if not url:
            self._show_stream_placeholder(_("STATUS_LIVE"), "#10b981")
            return
        self._stream_task = asyncio.ensure_future(self._run_stream(url))

    def stop_stream(self) -> None:
        """Public - CamerasPanel calls this before deleting a card whose
        camera left the roster, so an in-flight HTTP stream (or a
        still-running discovery request) doesn't keep touching a widget
        that's about to be destroyed."""
        self._stop_stream()
        if self._discovery_task is not None:
            self._discovery_task.cancel()
            self._discovery_task = None

    def _stop_stream(self) -> None:
        if self._stream_task is not None:
            self._stream_task.cancel()
            self._stream_task = None

    async def _run_stream(self, url: str) -> None:
        self._show_stream_placeholder(_("LBL_CONNECTING_STREAM"), "#38bdf8")
        got_a_frame = False
        try:
            async for frame in iter_mjpeg_frames(url):
                got_a_frame = True
                pixmap = QPixmap()
                if pixmap.loadFromData(frame, "JPG"):
                    scaled = pixmap.scaled(
                        self._video_area.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
                    self._video_area.setPixmap(scaled)
                    self._video_area.setText("")
        except asyncio.CancelledError:
            return
        # Real stream end (server not running mjpeg_server.py for this
        # camera yet, network drop, etc.) - matches CamerasView.tsx's own
        # <img onError> fallback: show the same honest placeholder a
        # never-actually-streaming camera shows, not a broken-image glyph
        # or a frozen last frame pretending to still be live.
        if not got_a_frame:
            self._show_stream_placeholder(_("STATUS_NO_SIGNAL"), "#4a5563")

    def _show_stream_placeholder(self, text: str, color: str) -> None:
        self._video_area.setPixmap(QPixmap())
        self._video_area.setText(text)
        self._video_area.setStyleSheet(f"background: #0a0f14; color: {color}; font-weight: 700; border: 1px solid #1a2530;")

    def _sync_type_options(self, is_ip: bool, camera_type: str) -> None:
        """Rebuilds the type combobox's own option list to match this
        camera's real sourceType - USB gets only "USB Vision Camera", IP
        gets exactly as many Main/Sub/Sub N options as this camera's own
        last real "Discover Path" run actually found
        (ip_stream_labels(self._camera.discovered_stream_paths) - never
        a fixed pair, matching HYDRA-UMC-STUDIO's own CamerasView.tsx
        combobox split). Thermal options stay in both lists
        unconditionally (see CAMERA_TYPES's own comment). A stored
        `camera_type` no longer valid for the current sourceType/
        discovery state (e.g. legacy data, or a mid-flight toggle not
        yet echoed back) falls back to the list's own first entry rather
        than leaving Qt's combobox in the blank/mismatched state a
        `value` with no matching `<option>` produces - same reasoning as
        CamerasView.tsx's own React <select> comment."""
        self._type_combo.blockSignals(True)
        ip_options = ip_stream_labels(self._camera.discovered_stream_paths) if is_ip else _USB_TYPE_OPTIONS
        options = ip_options + _THERMAL_TYPE_OPTIONS
        self._type_combo.clear()
        self._type_combo.addItems(options)
        idx = self._type_combo.findText(camera_type)
        self._type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._type_combo.blockSignals(False)

    def update_status(self, status: dict | None) -> None:
        """Real per-camera process status from HYDRA-UMC-SERVER's own
        GET /api/cameras/status (HYDRA-UMC-SUITE's own CamerasPanel polls
        this on a timer and fans it out to every card) - matches
        HYDRA-UMC-STUDIO's own Config.tsx status badge one-to-one.
        `status` is None when there's no active connection, no entry for
        this camera yet (process not reconciled since server start), or
        the poll itself failed - all 3 show the same neutral "unknown"
        badge rather than a false "error"."""
        if not status:
            self._status_badge.setText("")
            self._status_badge.setToolTip("")
            return
        state = str(status.get("status", ""))
        color = _STATUS_COLORS.get(state, "#8a97a6")
        label = {
            "running": _("STATUS_STREAM_RUNNING"),
            "starting": _("STATUS_STREAM_STARTING"),
            "error": _("STATUS_STREAM_ERROR"),
            # A real, deliberate state (this camera's own connected
            # toggle is off - the server already stopped its real
            # process rather than burning CPU/memory on a feed nothing's
            # asking to see), never an error.
            "stopped": _("STATUS_STREAM_STOPPED"),
        }.get(state, state.upper())
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {color};")
        last_error = status.get("lastError")
        self._status_badge.setToolTip(str(last_error) if last_error else "")

    def _on_toggle_clicked(self) -> None:
        self._on_toggle(self._camera.id)

    def _on_type_combo_changed(self, text: str) -> None:
        if not text:
            return
        # Real behavior, not just a label change: picking a different
        # discovered stream here re-points rtsp_path at that real
        # stream's own path, so this actually switches what the live
        # feed shows - the server's own camera-process supervisor
        # (reconcileCameraProcesses) respawns the real capture the
        # moment this saves, since rtsp_path is part of its fingerprint.
        # Mirrors HYDRA-UMC-STUDIO's own CamerasView.tsx <select> onChange.
        if self._camera.source_type == "ip":
            labels = ip_stream_labels(self._camera.discovered_stream_paths)
            if text in labels:
                idx = labels.index(text)
                paths = self._camera.discovered_stream_paths
                if idx < len(paths):
                    self._on_field_changed(self._camera.id, "rtsp_path", paths[idx])
        self._on_type_changed(self._camera.id, text)

    def _on_robot_combo_changed(self, index: int) -> None:
        self._on_field_changed(self._camera.id, "assigned_robot_id", self._robot_combo.itemData(index))

    def _on_source_type_clicked(self, value: str) -> None:
        self._on_field_changed(self._camera.id, "source_type", value)
        # Auto-normalize `type` on a source-type toggle, same as
        # HYDRA-UMC-STUDIO's own Config.tsx onClick handlers - a camera
        # switched IP -> USB (or vice versa) keeps a stale "IP Vision
        # Camera Main Stream"/"USB Vision Camera" label otherwise, which
        # _sync_type_options() above would then silently fall back away
        # from on the very next refresh(). Thermal selections are left
        # alone either way (see CAMERA_TYPES's own comment).
        current_type = self._camera.camera_type
        if current_type not in _THERMAL_TYPE_OPTIONS:
            new_type = ip_stream_labels(self._camera.discovered_stream_paths)[0] if value == "ip" else _USB_TYPE_OPTIONS[0]
            if current_type != new_type:
                self._on_type_changed(self._camera.id, new_type)

    def _on_hardware_source_edited(self) -> None:
        self._on_field_changed(self._camera.id, "hardware_source", self._hardware_source_edit.text())

    def _on_ip_host_edited(self) -> None:
        self._on_field_changed(self._camera.id, "ip_host", self._ip_host_edit.text())

    def _on_rtsp_port_edited(self) -> None:
        self._on_field_changed(self._camera.id, "rtsp_port", self._rtsp_port_spin.value())

    def _on_rtsp_path_edited(self) -> None:
        self._on_field_changed(self._camera.id, "rtsp_path", self._rtsp_path_edit.text())

    def _on_ip_username_edited(self) -> None:
        self._on_field_changed(self._camera.id, "ip_username", self._ip_username_edit.text())

    def _on_ip_password_edited(self) -> None:
        self._on_field_changed(self._camera.id, "ip_password", self._ip_password_edit.text())

    # --- real discovery (GET /api/camera/discover-usb-devices, POST
    # /api/camera/discover-rtsp-path) - see HydraConnection's own
    # discover_usb_devices()/discover_rtsp_path() header comments for
    # exactly what these round-trip to server-side. Mirrors
    # HYDRA-UMC-STUDIO's own Config.tsx discoverUsbDevices()/
    # discoverRtspPath() one-to-one, adapted to this panel's own
    # button -> asyncio.ensure_future() -> QLabel pattern (same one
    # admin_server_panel.py's own _save_port() already uses).

    def _set_discovery_status(self, text: str, color: str = "#8a97a6") -> None:
        self._discovery_status_label.setVisible(bool(text))
        self._discovery_status_label.setText(text)
        self._discovery_status_label.setStyleSheet(f"font-size: 10px; color: {color};")

    async def _discover_usb(self) -> None:
        if self._discovery_task is not None and not self._discovery_task.done():
            return  # already running - the button click below can't
            # actually reach here twice concurrently since Qt serializes
            # signal delivery on the GUI thread, but a second click while
            # the first request is still in flight is a real possibility.
        conn: HydraConnection | None = self._get_connection()
        if conn is None:
            self._set_discovery_status(_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            return
        self._discover_usb_btn.setEnabled(False)
        self._usb_devices_combo.setVisible(False)
        self._set_discovery_status(_("LBL_DISCOVERING"))
        self._discovery_task = asyncio.ensure_future(self._run_discover_usb(conn))
        await self._discovery_task

    async def _run_discover_usb(self, conn: HydraConnection) -> None:
        try:
            result = await conn.discover_usb_devices()
        finally:
            self._discover_usb_btn.setEnabled(True)
        if result is None:
            self._set_discovery_status(_("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            return
        status, body = result
        devices = body.get("devices") if status == 200 and isinstance(body, dict) else None
        if status != 200 or not isinstance(devices, list):
            message = body.get("error") if isinstance(body, dict) else None
            self._set_discovery_status(str(message) if message else _("MSG_USB_DISCOVERY_FAILED"), "#ef4444")
            return
        if not devices:
            self._set_discovery_status(_("MSG_NO_USB_DEVICES_FOUND"), "#f59e0b")
            return
        self._usb_devices_combo.blockSignals(True)
        self._usb_devices_combo.clear()
        for device in devices:
            if not isinstance(device, dict):
                continue
            index = device.get("index")
            width, height = device.get("width"), device.get("height")
            label = f"/dev/video{index}" if index is not None else "?"
            if width and height:
                label += f" ({width}x{height})"
            self._usb_devices_combo.addItem(label, index)
        self._usb_devices_combo.blockSignals(False)
        self._usb_devices_combo.setVisible(self._usb_devices_combo.count() > 0)
        self._set_discovery_status("")

    def _on_usb_device_picked(self, list_index: int) -> None:
        index = self._usb_devices_combo.itemData(list_index)
        if index is None:
            return
        # Windows/OpenCV opens by bare numeric index; Linux/V4L2 opens by
        # /dev/videoN path - HYDRA-UMC-VISION-STREAMER's own
        # MjpegCaptureSource.start() (and this same discover-usb
        # subcommand) already accept either, so hand it the platform's
        # own real value rather than guessing one format for both.
        value = str(index) if sys.platform == "win32" else f"/dev/video{index}"
        self._hardware_source_edit.setText(value)
        self._on_field_changed(self._camera.id, "hardware_source", value)

    async def _discover_rtsp(self) -> None:
        if self._discovery_task is not None and not self._discovery_task.done():
            return
        conn: HydraConnection | None = self._get_connection()
        if conn is None:
            self._set_discovery_status(_("MSG_ADMIN_LOAD_ERROR"), "#ef4444")
            return
        host = self._ip_host_edit.text().strip()
        if not host:
            self._set_discovery_status(_("LBL_IP_HOST"), "#ef4444")
            return
        self._discover_rtsp_btn.setEnabled(False)
        self._set_discovery_status(_("LBL_DISCOVERING"))
        self._discovery_task = asyncio.ensure_future(
            self._run_discover_rtsp(conn, host, self._rtsp_port_spin.value(), self._ip_username_edit.text(), self._ip_password_edit.text())
        )
        await self._discovery_task

    async def _run_discover_rtsp(self, conn: HydraConnection, host: str, port: int, username: str, password: str) -> None:
        try:
            result = await conn.discover_rtsp_path(host, port, username, password)
        finally:
            self._discover_rtsp_btn.setEnabled(True)
        if result is None:
            self._set_discovery_status(_("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")
            return
        status, body = result
        # discoverRtspPath() always answers HTTP 200 - success/failure is
        # its own `ok` field inside the body (see that route's own
        # RtspDescribeResult), same as HYDRA-UMC-STUDIO's own
        # `res.ok && body.ok` check right above this comment's mirror.
        # `paths` is the FULL list of every real stream this camera
        # answered on, never just the first - see ip_stream_labels()'s
        # own header comment for why this camera never assumes a fixed
        # Main/Sub pair from here on.
        found_paths = body.get("paths") if isinstance(body, dict) else None
        if status == 200 and isinstance(body, dict) and body.get("ok") and isinstance(found_paths, list) and found_paths:
            paths = [str(p) for p in found_paths]
            self._on_field_changed(self._camera.id, "discovered_stream_paths", paths)
            self._rtsp_path_edit.setText(paths[0])
            self._on_field_changed(self._camera.id, "rtsp_path", paths[0])
            # Reset to Main after a fresh discovery - same default
            # CameraCard._sync_type_options() would otherwise silently
            # fall back to anyway if the previously-selected label no
            # longer exists in the new, real option list.
            self._on_type_changed(self._camera.id, ip_stream_labels(paths)[0])
            self._set_discovery_status(_("MSG_RTSP_PATH_FOUND") + f": {', '.join(paths)}", "#10b981")
            return
        if status == 200 and isinstance(body, dict):
            tried = body.get("triedPaths")
            suffix = f" ({', '.join(str(t) for t in tried)})" if isinstance(tried, list) and tried else ""
            self._set_discovery_status(_("MSG_RTSP_PATH_NOT_FOUND") + suffix, "#f59e0b")
            return
        message = body.get("error") if isinstance(body, dict) else None
        self._set_discovery_status(str(message) if message else _("MSG_RTSP_DISCOVERY_FAILED"), "#ef4444")


class CamerasPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._cards: dict[int, CameraCard] = {}
        # keyed "<controllerId>:<cameraId>", same real shape
        # GET /api/cameras/status returns - see CameraCard.update_status()'s
        # own header comment.
        self._camera_status: dict[str, dict] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        heading = QLabel(_("TAB_CAMERAS"))
        heading.setObjectName("panelHeading")
        outer.addWidget(heading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)

        grid_host = QWidget()
        self._grid = QGridLayout(grid_host)
        self._grid.setSpacing(8)
        scroll.setWidget(grid_host)

        controller.active_state_changed.connect(self._on_state_changed)

        # Real per-camera process status, polled the same way
        # admin_server_panel.py polls admin config - a short interval
        # (matches HYDRA-UMC-STUDIO's own Config.tsx 3s poll) since this
        # is cheap, in-memory Map read server-side, not a real hardware
        # touch. Runs unconditionally rather than only-while-tab-visible
        # (this panel has no separate "is my tab active" signal to hook
        # like Config.tsx's own `configTab === 'cameras'` gate does) -
        # acceptable here since there's only ever one CamerasPanel alive.
        self._status_poll_timer = QTimer(self)
        self._status_poll_timer.setInterval(3000)
        self._status_poll_timer.timeout.connect(lambda: asyncio.ensure_future(self._poll_camera_status()))
        self._status_poll_timer.start()

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
        state = self._controller.active_state
        active = state.active_controller if state else None
        if active is None:
            return
        for camera_id, card in self._cards.items():
            card.update_status(self._camera_status.get(f"{active.id}:{camera_id}"))

    def _on_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        cameras = active.cameras if active is not None else []
        robots = active.robots if active is not None else []

        seen_ids = set()
        for i, camera in enumerate(cameras):
            seen_ids.add(camera.id)
            row, col = divmod(i, GRID_COLUMNS)
            card = self._cards.get(camera.id)
            if card is None:
                card = CameraCard(
                    camera, self._on_toggle_connection, self._on_type_changed, self._on_field_changed, self._get_stream_url, self._get_connection
                )
                self._cards[camera.id] = card
                self._grid.addWidget(card, row, col)
            else:
                self._grid.removeWidget(card)
                self._grid.addWidget(card, row, col)
            card.refresh(camera, robots)
            if active is not None:
                card.update_status(self._camera_status.get(f"{active.id}:{camera.id}"))

        # A camera that's no longer in the server's own list (removed
        # controller, or - even though nothing in this ecosystem does
        # this today - a future dynamic camera count) gets its own card
        # removed too, rather than left showing stale data forever.
        for stale_id in set(self._cards) - seen_ids:
            card = self._cards.pop(stale_id)
            card.stop_stream()
            self._grid.removeWidget(card)
            card.deleteLater()

    def _get_stream_url(self, camera_id: int) -> str | None:
        conn = self._controller.active_connection
        if conn is None:
            return None
        return f"{conn.info.base_url}/api/camera/{camera_id}/stream"

    def _get_connection(self) -> HydraConnection | None:
        return self._controller.active_connection

    def _current_camera(self, camera_id: int) -> CameraView | None:
        state = self._controller.active_state
        active = state.active_controller if state else None
        if active is None:
            return None
        for cam in active.cameras:
            if cam.id == camera_id:
                return cam
        return None

    def _on_toggle_connection(self, camera_id: int) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        camera.set_connected(not camera.connected)
        self._controller.push_active_state()

    def _on_type_changed(self, camera_id: int, camera_type: str) -> None:
        camera = self._current_camera(camera_id)
        if camera is None or camera.camera_type == camera_type:
            return
        camera.set_camera_type(camera_type)
        self._controller.push_active_state()

    def _on_field_changed(self, camera_id: int, field: str, value) -> None:
        camera = self._current_camera(camera_id)
        if camera is None:
            return
        setter = getattr(camera, f"set_{field}")
        setter(value)
        self._controller.push_active_state()
