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
from collections.abc import AsyncIterator

import httpx
from PySide6.QtCore import Qt
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
from hydra_suite.models import CAMERA_TYPES, RTSP_DEFAULT_PORT, CameraView, HydraState, RobotView

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
        self._stream_task: asyncio.Task | None = None
        self._streaming_connected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel()
        header.setObjectName("cameraCardHeading")
        layout.addWidget(header)
        self._header = header

        self._video_area = QLabel()
        self._video_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_area.setMinimumHeight(100)
        self._video_area.setObjectName("cameraVideoArea")
        layout.addWidget(self._video_area, 1)

        self._type_combo = QComboBox()
        self._type_combo.addItems(CAMERA_TYPES)
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

        self._toggle_button = QPushButton()
        self._toggle_button.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_button)

        self.refresh(camera, [])

    def refresh(self, camera: CameraView, robots: list[RobotView]) -> None:
        self._camera = camera
        self._header.setText(f"{_('LBL_CAM')} {camera.id}")

        self._type_combo.blockSignals(True)
        idx = self._type_combo.findText(camera.camera_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._type_combo.blockSignals(False)

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

        is_ip = camera.source_type == "ip"
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
        camera left the roster, so an in-flight HTTP stream doesn't keep
        running against a widget that's about to be destroyed."""
        self._stop_stream()

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

    def _on_toggle_clicked(self) -> None:
        self._on_toggle(self._camera.id)

    def _on_type_combo_changed(self, text: str) -> None:
        if text:
            self._on_type_changed(self._camera.id, text)

    def _on_robot_combo_changed(self, index: int) -> None:
        self._on_field_changed(self._camera.id, "assigned_robot_id", self._robot_combo.itemData(index))

    def _on_source_type_clicked(self, value: str) -> None:
        self._on_field_changed(self._camera.id, "source_type", value)

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


class CamerasPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._cards: dict[int, CameraCard] = {}

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
                card = CameraCard(camera, self._on_toggle_connection, self._on_type_changed, self._on_field_changed, self._get_stream_url)
                self._cards[camera.id] = card
                self._grid.addWidget(card, row, col)
            else:
                self._grid.removeWidget(card)
                self._grid.addWidget(card, row, col)
            card.refresh(camera, robots)

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
