# =============================================================================
# HYDRA-UMC SUITE - ui/panels/camera_media_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own CameraMediaView.tsx +
# MjpegRecordingPlayer.tsx - real parity gap closed: SUITE could start/
# stop a recording (cameras_panel.py) but had no way at all to browse,
# play back or delete what actually got saved. A saved recording is raw
# multipart/x-mixed-replace bytes on disk (HYDRA-UMC-SERVER's own
# recording/start handler) - real playback here parses it into individual
# JPEG frame bytes (parse_mjpeg_frames(), the same real JPEG SOI(0xFFD8)/
# EOI(0xFFD9) marker-scan cameras_panel.py's own iter_mjpeg_frames()
# already uses for a live stream, applied here to an already-downloaded,
# static byte blob instead of a live wire) and steps through them under
# a real QTimer, at the server's own real per-frame interval when it
# reported one (durationMs/frameCount, see HYDRA-UMC-SERVER's own
# CHANGELOG), honestly falling back to a fixed step otherwise instead of
# inventing a frame rate nothing on disk actually recorded.
# =============================================================================
from __future__ import annotations

import asyncio

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.net.client import HydraConnection

_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"


def parse_mjpeg_frames(data: bytes) -> list[bytes]:
    """Real, synchronous parse of a fully-downloaded .mjpeg recording's
    own bytes into an ordered list of real JPEG frame byte strings - same
    SOI/EOI marker-scan approach as cameras_panel.py's own
    iter_mjpeg_frames() (proven against this exact real wire format
    already), just over an in-memory blob instead of a live stream.
    Never raises on malformed/truncated input - a partial trailing frame
    with no real EOI yet is simply not included, matching a recording
    that was cut off mid-frame."""
    frames: list[bytes] = []
    offset = 0
    while True:
        start = data.find(_JPEG_SOI, offset)
        if start < 0:
            break
        end = data.find(_JPEG_EOI, start + 2)
        if end < 0:
            break
        frames.append(data[start : end + 2])
        offset = end + 2
    return frames


class CameraMediaPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._items: list[dict] = []
        self._selected: dict | None = None
        self._frames: list[bytes] = []
        self._frame_index = 0
        self._selected_camera_id: int | str = "all"

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._advance_frame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header = QHBoxLayout()
        heading = QLabel(_("CAMERA_MEDIA_TITLE"))
        heading.setObjectName("panelHeading")
        header.addWidget(heading)
        header.addStretch(1)
        self._refresh_btn = QPushButton(_("CAMERA_MEDIA_REFRESH"))
        self._refresh_btn.clicked.connect(lambda: asyncio.ensure_future(self._load_media()))
        header.addWidget(self._refresh_btn)
        outer.addLayout(header)

        self._filter_row = QHBoxLayout()
        outer.addLayout(self._filter_row)

        self._error_label = QLabel("")
        self._error_label.setObjectName("errorLabel")
        self._error_label.setVisible(False)
        outer.addWidget(self._error_label)

        body = QHBoxLayout()
        body.setSpacing(8)
        outer.addLayout(body, 1)

        self._list = QListWidget()
        self._list.setMinimumWidth(260)
        self._list.setMaximumWidth(320)
        self._list.currentItemChanged.connect(self._on_item_selected)
        body.addWidget(self._list)

        viewer_col = QVBoxLayout()
        body.addLayout(viewer_col, 1)

        self._viewer = QLabel(_("CAMERA_MEDIA_SELECT_HINT"))
        self._viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._viewer.setMinimumHeight(320)
        self._viewer.setObjectName("cameraMediaViewer")
        self._viewer.setWordWrap(True)
        viewer_col.addWidget(self._viewer, 1)

        controls = QHBoxLayout()
        self._play_btn = QPushButton(_("CAMERA_MEDIA_PLAY"))
        self._play_btn.clicked.connect(self._toggle_play)
        self._play_btn.setEnabled(False)
        controls.addWidget(self._play_btn)
        self._stop_btn = QPushButton(_("CAMERA_MEDIA_STOP"))
        self._stop_btn.clicked.connect(self._stop_play)
        self._stop_btn.setEnabled(False)
        controls.addWidget(self._stop_btn)
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setEnabled(False)
        self._seek.sliderMoved.connect(self._on_seek)
        controls.addWidget(self._seek, 1)
        self._frame_label = QLabel("")
        controls.addWidget(self._frame_label)
        viewer_col.addLayout(controls)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._save_btn = QPushButton(_("CAMERA_MEDIA_SAVE_AS"))
        self._save_btn.clicked.connect(self._save_as)
        self._save_btn.setEnabled(False)
        actions.addWidget(self._save_btn)
        self._delete_btn = QPushButton(_("CAMERA_MEDIA_DELETE"))
        self._delete_btn.clicked.connect(lambda: asyncio.ensure_future(self._delete_selected()))
        self._delete_btn.setEnabled(False)
        actions.addWidget(self._delete_btn)
        viewer_col.addLayout(actions)

        self._rebuild_filter_row()
        asyncio.ensure_future(self._load_media())

    # --- data loading -----------------------------------------------------

    def _get_connection(self) -> HydraConnection | None:
        return self._controller.active_connection

    async def _load_media(self) -> None:
        conn = self._get_connection()
        if conn is None:
            return
        result = await conn.list_camera_media()
        if result is None:
            self._show_error(_("CAMERA_MEDIA_LOAD_FAILED"))
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._show_error(_("CAMERA_MEDIA_LOAD_FAILED"))
            return
        self._error_label.setVisible(False)
        self._items = body.get("items") or []
        self._rebuild_filter_row()
        self._rebuild_list()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    def _rebuild_filter_row(self) -> None:
        while self._filter_row.count():
            item = self._filter_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        camera_ids = sorted({i.get("cameraId") for i in self._items if isinstance(i.get("cameraId"), int)})

        def make_button(label: str, camera_id) -> QPushButton:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(camera_id == self._selected_camera_id)
            btn.clicked.connect(lambda: self._on_filter_clicked(camera_id))
            return btn

        self._filter_row.addWidget(make_button(_("CAMERA_MEDIA_ALL"), "all"))
        for camera_id in camera_ids:
            self._filter_row.addWidget(make_button(f"{_('LBL_CAM')} {camera_id}", camera_id))
        self._filter_row.addStretch(1)

    def _on_filter_clicked(self, camera_id) -> None:
        self._selected_camera_id = camera_id
        self._rebuild_filter_row()
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        self._list.clear()
        for item in self._items:
            if self._selected_camera_id != "all" and item.get("cameraId") != self._selected_camera_id:
                continue
            rec_marker = f" · {_('CAMERA_MEDIA_REC_BADGE')}" if item.get("recording") else ""
            label = f"{_('LBL_CAM')} {item.get('cameraId')} · {item.get('filename')}{rec_marker}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._list.addItem(list_item)

    # --- selection / viewing ------------------------------------------------

    def _on_item_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        self._stop_play()
        if current is None:
            self._selected = None
            self._save_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._viewer.setText(_("CAMERA_MEDIA_SELECT_HINT"))
            self._viewer.setPixmap(QPixmap())
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        self._selected = item
        self._save_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        if item.get("kind") == "snapshots":
            self._play_btn.setEnabled(False)
            self._seek.setEnabled(False)
            asyncio.ensure_future(self._load_snapshot(item))
        else:
            self._play_btn.setEnabled(True)
            asyncio.ensure_future(self._load_recording(item))

    async def _fetch_selected_bytes(self, item: dict) -> bytes | None:
        conn = self._get_connection()
        if conn is None:
            return None
        return await conn.fetch_camera_media_bytes(item["cameraId"], item["kind"], item["filename"])

    async def _load_snapshot(self, item: dict) -> None:
        data = await self._fetch_selected_bytes(item)
        if not data or self._selected is not item:
            return
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._viewer.setText("")
        self._viewer.setPixmap(pixmap.scaled(self._viewer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    async def _load_recording(self, item: dict) -> None:
        self._viewer.setText(_("CAMERA_MEDIA_LOADING"))
        self._viewer.setPixmap(QPixmap())
        data = await self._fetch_selected_bytes(item)
        if self._selected is not item:
            return  # selection moved on while this was in flight
        if not data:
            self._viewer.setText(_("CAMERA_MEDIA_LOAD_RECORDING_FAILED"))
            self._play_btn.setEnabled(False)
            return
        self._frames = parse_mjpeg_frames(data)
        if not self._frames:
            self._viewer.setText(_("CAMERA_MEDIA_EMPTY_RECORDING"))
            self._play_btn.setEnabled(False)
            return
        self._frame_index = 0
        self._seek.setEnabled(True)
        self._seek.setMinimum(0)
        self._seek.setMaximum(len(self._frames) - 1)
        self._seek.setValue(0)
        self._show_current_frame()

        duration_ms = item.get("durationMs")
        frame_count = item.get("frameCount")
        if isinstance(duration_ms, (int, float)) and isinstance(frame_count, int) and frame_count > 1:
            self._frame_interval_ms = max(1, int(duration_ms / frame_count))
        else:
            # Honest fallback for a recording saved before the server's
            # own metadata sidecar existed - never a fabricated frame
            # rate, just a plain, fixed step (10fps).
            self._frame_interval_ms = 100

    def _show_current_frame(self) -> None:
        if not self._frames:
            return
        self._frame_index = max(0, min(self._frame_index, len(self._frames) - 1))
        pixmap = QPixmap()
        pixmap.loadFromData(self._frames[self._frame_index])
        self._viewer.setPixmap(pixmap.scaled(self._viewer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self._seek.blockSignals(True)
        self._seek.setValue(self._frame_index)
        self._seek.blockSignals(False)
        self._frame_label.setText(f"{self._frame_index + 1} / {len(self._frames)}")

    # --- playback -----------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._play_timer.isActive():
            self._pause_play()
        else:
            self._start_play()

    def _start_play(self) -> None:
        if not self._frames:
            return
        if self._frame_index >= len(self._frames) - 1:
            self._frame_index = 0
        self._play_timer.start(getattr(self, "_frame_interval_ms", 100))
        self._play_btn.setText(_("CAMERA_MEDIA_PAUSE"))
        self._stop_btn.setEnabled(True)

    def _pause_play(self) -> None:
        self._play_timer.stop()
        self._play_btn.setText(_("CAMERA_MEDIA_PLAY"))

    def _stop_play(self) -> None:
        self._play_timer.stop()
        self._play_btn.setText(_("CAMERA_MEDIA_PLAY"))
        self._stop_btn.setEnabled(False)
        self._frame_index = 0
        if self._frames:
            self._show_current_frame()

    def _advance_frame(self) -> None:
        if self._frame_index + 1 >= len(self._frames):
            self._pause_play()
            return
        self._frame_index += 1
        self._show_current_frame()

    def _on_seek(self, value: int) -> None:
        self._pause_play()
        self._frame_index = value
        self._show_current_frame()

    # --- save / delete --------------------------------------------------

    def _save_as(self) -> None:
        if self._selected is None:
            return
        path, _filter = QFileDialog.getSaveFileName(self, _("CAMERA_MEDIA_SAVE_AS"), self._selected["filename"])
        if not path:
            return
        asyncio.ensure_future(self._save_as_real(path, self._selected))

    async def _save_as_real(self, path: str, item: dict) -> None:
        data = await self._fetch_selected_bytes(item)
        if not data:
            return
        with open(path, "wb") as f:
            f.write(data)

    async def _delete_selected(self) -> None:
        if self._selected is None:
            return
        item = self._selected
        confirmed = QMessageBox.question(
            self, _("CAMERA_MEDIA_DELETE"), _("CAMERA_MEDIA_DELETE_CONFIRM"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        conn = self._get_connection()
        if conn is None:
            return
        result = await conn.delete_camera_media(item["cameraId"], item["kind"], item["filename"])
        if result is None or result[0] != 200:
            self._show_error(_("CAMERA_MEDIA_DELETE_FAILED"))
            return
        self._selected = None
        await self._load_media()
