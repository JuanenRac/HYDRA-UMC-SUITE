#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC SUITE - main.py (entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Starts MAXIMIZED (not true OS-level fullscreen) at a 1920x1080 minimum,
# per the project owner's own spec ("se ejecutara a pantalla completa con
# una resolución mínima de 1920x1080") while keeping the native title bar
# and its minimize/maximize/close buttons visible - true showFullScreen()
# hides that title bar entirely on Windows, which read as "missing window
# controls" rather than "running fullscreen". F11 still toggles into real
# borderless fullscreen for whoever wants that, and back out again.
#
# qasync's QEventLoop is what lets every `async def` elsewhere in this
# app (net/client.py, net/discovery.py, app.py) run on the SAME event
# loop Qt's own GUI thread uses - no separate worker thread, no manual
# thread-safe signal bridging needed to get network results back onto
# the GUI thread safely.
# =============================================================================
import asyncio
import sys

import qasync
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication

from hydra_suite.ui.main_window import MainWindow
from hydra_suite.ui.theme import apply_theme


def main() -> int:
    # Qt6 auto-scales by physical DPI by default (no AA_EnableHighDpiScaling
    # flag needed anymore, unlike Qt5), but its DEFAULT rounding policy snaps
    # a fractional OS scale factor (125%/150%/175% - Windows's own recommended
    # setting for most 27"-32" 4K monitors, not just 100%/200%) to the nearest
    # whole integer before applying it. That mismatch between the requested
    # and applied factor is exactly what makes fixed-pixel controls (the jog
    # knobs/sliders in ui/panels/robot_control.py, sized in logical px) read
    # as too-small-or-too-large and slightly blurry on a real 4K display set
    # to one of those in-between scales, which is the common case, not the
    # exception. PassThrough applies the OS's exact factor instead of
    # rounding it - must be set before QApplication() exists, Qt reads it
    # once at construction time.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC SUITE")
    app.setOrganizationName("Electro Hobby 3D")
    apply_theme(app)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()

    # Remembers whether the window was maximized (vs. a plain resized/
    # moved "normal" geometry) the moment F11 was pressed to ENTER
    # fullscreen, so leaving fullscreen restores that exact prior state
    # instead of always snapping back to showMaximized() - which used to
    # silently discard any manual resize/move the user had done before
    # their first F11 press (window.showNormal() restores Qt's own
    # tracked normalGeometry() correctly, but only if it's actually
    # called instead of being skipped in favor of always-maximize).
    fullscreen_state = {"was_maximized": True}

    def toggle_fullscreen() -> None:
        if window.isFullScreen():
            if fullscreen_state["was_maximized"]:
                window.showMaximized()
            else:
                window.showNormal()
        else:
            fullscreen_state["was_maximized"] = window.isMaximized()
            window.showFullScreen()

    shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), window)
    shortcut.activated.connect(toggle_fullscreen)

    window.showMaximized()

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(main())
