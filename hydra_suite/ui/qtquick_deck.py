# =============================================================================
# HYDRA-UMC SUITE - Qt Quick command-deck bridge
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Bridge Suite's existing dock workspace into the shared Qt Quick shell.

The bridge owns no robot, camera, trajectory or network behaviour.  QML emits
navigation/about intents here and this object forwards them to MainWindow's
already-established dock actions.  Keeping that boundary explicit prevents a
decorative QML shell from becoming a second, divergent control implementation.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class SuiteDeckBridge(QObject):
    """Small live state model consumed by ``assets/qml/CommandDeck.qml``."""

    deckChanged = Signal()
    navigateRequested = Signal(str)
    aboutRequested = Signal()

    def __init__(self, *, title: str, version: str, logo_source: str) -> None:
        super().__init__()
        self._title = title
        self._version = version
        self._logo_source = logo_source
        self._status = "DISCONNECTED"
        self._status_color = "#91a8bd"
        self._target = "NO TARGET"
        self._clock = "--:--:-- UTC"

    @Property(str, constant=True)
    def title(self) -> str:
        return self._title

    @Property(str, constant=True)
    def version(self) -> str:
        return self._version

    @Property(str, constant=True)
    def logoSource(self) -> str:
        return self._logo_source

    @Property(str, notify=deckChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=deckChanged)
    def statusColor(self) -> str:
        return self._status_color

    @Property(str, notify=deckChanged)
    def target(self) -> str:
        return self._target

    @Property(str, notify=deckChanged)
    def clock(self) -> str:
        return self._clock

    def set_status(self, status: str, color: str) -> None:
        if (status, color) != (self._status, self._status_color):
            self._status, self._status_color = status, color
            self.deckChanged.emit()

    def set_target(self, target: str) -> None:
        if target != self._target:
            self._target = target
            self.deckChanged.emit()

    def set_clock(self, clock: str) -> None:
        if clock != self._clock:
            self._clock = clock
            self.deckChanged.emit()

    @Slot(str)
    def navigate(self, key: str) -> None:
        self.navigateRequested.emit(key)

    @Slot()
    def showAbout(self) -> None:
        self.aboutRequested.emit()
