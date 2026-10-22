# =============================================================================
# HYDRA-UMC SUITE - render/gl_format.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The 3D viewport shaders are "#version 330 core". macOS only gives a context
# that new when a 3.3 core profile is asked for explicitly (the default there
# is 2.1), so the default surface format is set before the application exists.
# Other systems already give a newer context by default and are left alone.
# =============================================================================
from __future__ import annotations

import sys

from PySide6.QtGui import QSurfaceFormat


def default_surface_format(platform: str | None = None) -> QSurfaceFormat | None:
    """The format to install as the application default, or None when the
    platform needs no change."""
    if (platform or sys.platform) != "darwin":
        return None
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    return fmt


def install_default_surface_format(platform: str | None = None) -> bool:
    """Installs it when needed; call before QApplication is created."""
    fmt = default_surface_format(platform)
    if fmt is None:
        return False
    QSurfaceFormat.setDefaultFormat(fmt)
    return True
