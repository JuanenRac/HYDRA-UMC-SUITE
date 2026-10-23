#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC SUITE - main.py (entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Starts the Qt Quick interface (qt_suite.py): a maximized window with the native title bar, a sidebar of panels
# and a single content area. qasync's QEventLoop lets every `async def` of net/client.py, net/discovery.py and
# app.py run on the same event loop as Qt's own GUI thread, so network results reach the screen without a worker
# thread or any thread-safe bridging.
# =============================================================================
import sys


def main() -> int:
    try:
        from qt_suite import run_qtquick
    except ImportError as exc:
        print(
            "ERROR: HYDRA-UMC SUITE needs PySide6 and qasync. "
            "Install this repository's requirements.txt first. "
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2
    return run_qtquick()


if __name__ == "__main__":
    sys.exit(main())
