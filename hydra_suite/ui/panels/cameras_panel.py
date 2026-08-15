# =============================================================================
# HYDRA-UMC SUITE - ui/panels/cameras_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own CamerasView.tsx. Same
# honesty boundary as that component: NO real camera hardware/video
# stream exists anywhere in this ecosystem yet (see that file's own
# header) - what IS real is the camera METADATA (which cameras a
# controller has, their type, whether they're marked "connected"),
# which lives in the same synced settings blob every other panel here
# already reads/writes, so toggling a camera's connection or type here
# really does round-trip to the server and to any browser tab watching
# the same controller. The "video" area itself is a clearly-labeled
# placeholder (LIVE/NO SIGNAL text), not a fake video feed pretending to
# be real.
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import CAMERA_TYPES, CameraView, HydraState

GRID_COLUMNS = 4


class CameraCard(QFrame):
    def __init__(self, camera: CameraView, on_toggle, on_type_changed, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("cameraCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._camera = camera
        self._on_toggle = on_toggle
        self._on_type_changed = on_type_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel()
        header.setObjectName("cameraCardHeading")
        layout.addWidget(header)
        self._header = header

        self._video_area = QLabel()
        self._video_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_area.setMinimumHeight(120)
        self._video_area.setObjectName("cameraVideoArea")
        layout.addWidget(self._video_area, 1)

        self._type_combo = QComboBox()
        self._type_combo.addItems(CAMERA_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_type_combo_changed)
        layout.addWidget(self._type_combo)

        self._toggle_button = QPushButton()
        self._toggle_button.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_button)

        self.refresh(camera)

    def refresh(self, camera: CameraView) -> None:
        self._camera = camera
        self._header.setText(f"{_('LBL_CAM')} {camera.id}")

        self._type_combo.blockSignals(True)
        idx = self._type_combo.findText(camera.camera_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._type_combo.blockSignals(False)

        if camera.connected:
            self._video_area.setText(_("STATUS_LIVE"))
            self._video_area.setStyleSheet("background: #0a0f14; color: #10b981; font-weight: 700; border: 1px solid #1a2530;")
            self._toggle_button.setText(_("BTN_TOGGLE_CONNECTION") + f" ({_('STATUS_CONNECTED')})")
        else:
            self._video_area.setText(_("STATUS_NO_SIGNAL"))
            self._video_area.setStyleSheet("background: #0a0f14; color: #4a5563; border: 1px dashed #1a2530;")
            self._toggle_button.setText(_("BTN_TOGGLE_CONNECTION") + f" ({_('STATUS_DISCONNECTED')})")

    def _on_toggle_clicked(self) -> None:
        self._on_toggle(self._camera.id)

    def _on_type_combo_changed(self, text: str) -> None:
        if text:
            self._on_type_changed(self._camera.id, text)


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

        seen_ids = set()
        for i, camera in enumerate(cameras):
            seen_ids.add(camera.id)
            row, col = divmod(i, GRID_COLUMNS)
            card = self._cards.get(camera.id)
            if card is None:
                card = CameraCard(camera, self._on_toggle_connection, self._on_type_changed)
                self._cards[camera.id] = card
                self._grid.addWidget(card, row, col)
            else:
                self._grid.removeWidget(card)
                self._grid.addWidget(card, row, col)
                card.refresh(camera)

        # A camera that's no longer in the server's own list (removed
        # controller, or - even though nothing in this ecosystem does
        # this today - a future dynamic camera count) gets its own card
        # removed too, rather than left showing stale data forever.
        for stale_id in set(self._cards) - seen_ids:
            card = self._cards.pop(stale_id)
            self._grid.removeWidget(card)
            card.deleteLater()

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
