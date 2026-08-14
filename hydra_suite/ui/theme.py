# =============================================================================
# HYDRA-UMC SUITE - ui/theme.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

QSS_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "qss" / "industrial_dark.qss"


def apply_theme(app: QApplication) -> None:
    try:
        app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    except OSError:
        # Missing/unreadable QSS shouldn't prevent the app from starting -
        # it just runs with the platform's own default Qt style instead of
        # the industrial theme.
        pass
